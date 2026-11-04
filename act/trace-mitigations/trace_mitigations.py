"""Find Python tests tagged with ``@pytest.mark.mitigates("MITIG<n>")``, and fail when
a change leaves a threat-model mitigation with no covered test.

It reads source from git objects and never runs the tests. See README.md for the
details.
"""

import argparse
import ast
import dataclasses
import json
import os
import re
import subprocess
import sys
import urllib.parse
from collections import Counter
from collections.abc import Iterable, Iterator

TAG = "mitigates"
EXCEPTIONS_FILE = ".github/mitigation-exceptions.txt"

ID_RE = re.compile(r"MITIG(QW)?(\d+)")

PYTEST_EXCLUDING_MARKS = ("skip", "skipif", "xfail")


@dataclasses.dataclass(frozen=True)
class TaggedTest:
    mitigation: str
    path: str
    test: str
    line: int
    # The skip/xfail marker that keeps this test from counting, if any.
    excluded_by: str | None = None

    @property
    def covered(self) -> bool:
        return self.excluded_by is None


@dataclasses.dataclass(frozen=True)
class Problem:
    path: str
    line: int
    message: str


@dataclasses.dataclass
class Scan:
    commit: str = ""
    tests: list[TaggedTest] = dataclasses.field(default_factory=list)
    errors: list[Problem] = dataclasses.field(default_factory=list)

    def covered_counts(self) -> Counter[str]:
        return Counter(t.mitigation for t in self.tests if t.covered)


# Python


def _pytest_marks(expr: ast.expr) -> Iterator[tuple[str, ast.Call | None]]:
    """Yield (name, call) for each ``pytest.mark.<name>`` in a decorator or pytestmark."""
    if isinstance(expr, (ast.List, ast.Tuple)):
        for element in expr.elts:
            yield from _pytest_marks(element)
        return
    call = expr if isinstance(expr, ast.Call) else None
    dotted = ast.unparse(call.func if call else expr)
    if dotted.startswith("pytest.mark."):
        yield dotted.removeprefix("pytest.mark."), call


def _read_marks(exprs: Iterable[ast.expr]) -> tuple[list[str], str | None]:
    """Return the mitigation IDs and the excluding mark (if any) in these marks."""
    ids: list[str] = []
    excluded_by = None
    for expr in exprs:
        for name, call in _pytest_marks(expr):
            if name == TAG and call is not None:
                ids += [
                    arg.value
                    for arg in call.args
                    if isinstance(arg, ast.Constant)
                    and isinstance(arg.value, str)
                    and ID_RE.fullmatch(arg.value)
                ]
            elif name in PYTEST_EXCLUDING_MARKS and excluded_by is None:
                excluded_by = name
    return ids, excluded_by


def _pytestmark(body: list[ast.stmt]) -> list[ast.expr]:
    return [
        stmt.value
        for stmt in body
        if isinstance(stmt, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in stmt.targets)
    ]


def _walk_python(
    path: str,
    body: list[ast.stmt],
    prefix: str,
    outer_ids: list[str],
    outer_excluded: str | None,
    tests: list[TaggedTest],
) -> None:
    # Marks on a module or class reach every test* function inside it, as they do
    # in pytest. A function's own marks apply to it whatever its name.
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            ids, excluded_by = _read_marks(node.decorator_list)
            if node.name.startswith("test"):
                ids += outer_ids
            for mitigation in dict.fromkeys(ids):
                tests.append(
                    TaggedTest(
                        mitigation,
                        path,
                        prefix + node.name,
                        node.lineno,
                        excluded_by or outer_excluded,
                    )
                )
        elif isinstance(node, ast.ClassDef):
            ids, excluded_by = _read_marks([*node.decorator_list, *_pytestmark(node.body)])
            _walk_python(
                path,
                node.body,
                f"{prefix}{node.name}::",
                ids + outer_ids,
                excluded_by or outer_excluded,
                tests,
            )


def scan_python(path: str, source: bytes) -> Scan:
    result = Scan()
    try:
        tree = ast.parse(source, filename=path)
    except (SyntaxError, ValueError) as e:
        line = getattr(e, "lineno", None) or 1
        result.errors.append(Problem(path, line, f"cannot parse this file: {e}"))
        return result
    ids, excluded_by = _read_marks(_pytestmark(tree.body))
    _walk_python(path, tree.body, "", ids, excluded_by, result.tests)
    return result


# Git


class GitError(Exception):
    pass


def _git(repo: str, *args: str, ok_codes: tuple[int, ...] = (0,)) -> bytes:
    proc = subprocess.run(["git", "-C", repo, *args], capture_output=True, check=False)
    if proc.returncode not in ok_codes:
        stderr = proc.stderr.decode(errors="replace").strip()
        raise GitError(f"git {args[0]} failed ({proc.returncode}): {stderr}")
    return proc.stdout


def read_blob(repo: str, commit: str, path: str) -> bytes | None:
    """Return a file's contents at a commit, or None if it isn't a file there.

    The commit is already verified, so a failure here means the path is missing or
    not a file. Treating that as no exceptions only makes the check stricter.
    """
    try:
        return _git(repo, "cat-file", "blob", f"{commit}:{path}")
    except GitError:
        return None


def scan_commit(repo: str, rev: str) -> Scan:
    out = _git(repo, "rev-parse", "--verify", "--end-of-options", f"{rev}^{{commit}}")
    commit = out.decode().strip()
    # git grep reads the tree directly, so only tracked files are scanned and no
    # checkout of this revision is needed. Matching the mark rather than the bare
    # word keeps prose in a file this Python can't parse from failing the scan.
    # Exit status 1 means no matches.
    out = _git(
        repo,
        "grep",
        "-z",
        "-l",
        "--text",
        "--fixed-strings",
        "-e",
        f"pytest.mark.{TAG}",
        commit,
        "--",
        "*.py",
        ok_codes=(0, 1),
    )
    scan = Scan(commit=commit)
    for entry in out.decode("utf-8", errors="surrogateescape").split("\0"):
        if entry:
            path = entry.removeprefix(f"{commit}:")
            found = scan_python(path, _git(repo, "cat-file", "blob", f"{commit}:{path}"))
            scan.tests += found.tests
            scan.errors += found.errors
    return scan


# Exceptions file

_EXCEPTION_RE = re.compile(r"^(?P<id>[^\s:]+)\s*:\s*(?P<reason>.*?)\s*$")


def parse_exceptions(path: str, text: str) -> tuple[set[str], list[Problem]]:
    """Parse ``ID: reason`` lines, ignoring blank lines and lines starting with #.

    Returns the excepted IDs, and any problems.
    """
    exceptions: set[str] = set()
    errors = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _EXCEPTION_RE.match(line)
        if not match or not ID_RE.fullmatch(match["id"]):
            errors.append(
                Problem(path, number, "expected 'MITIG<n>: reason' or 'MITIGQW<n>: reason'")
            )
        elif not match["reason"]:
            errors.append(Problem(path, number, f"{match['id']} needs a reason after the colon"))
        else:
            exceptions.add(match["id"])
    return exceptions, errors


# Comparison


def compare(base: Scan, head: Scan, exceptions: set[str]) -> list[str]:
    """Return the IDs with covered tests at base, none at head, and no exception."""
    after = head.covered_counts()
    return sorted(m for m in base.covered_counts() if m not in after and m not in exceptions)


# Output
#
# The script reports results three ways:
# - Annotations: lines on stdout in GitHub's workflow command format. GitHub shows
#   them on the run, and inline on the pull request's changed files when it can.
# - A Markdown job summary, appended to the file named by $GITHUB_STEP_SUMMARY.
# - Optionally, JSON for the threat model's coverage report.
#
# File paths, test names, and messages come from the pull request, so they're
# escaped before they go into an annotation or the Markdown.


def _escape_data(value: str) -> str:
    """Escape an annotation's message, where %, CR, and LF have special meaning."""
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_property(value: str) -> str:
    """Escape an annotation property, which also can't contain the : or , that
    separate properties."""
    return _escape_data(value).replace(":", "%3A").replace(",", "%2C")


def annotation(level: str, message: str, **properties: object) -> str:
    """Format a GitHub Actions workflow command that annotates the run.

    For example, ``annotation("error", "cannot parse", file="t.py", line=3)`` returns
    ``::error file=t.py,line=3::cannot parse``. The level is "error" or "warning", and
    the properties GitHub uses are file, line, and title.
    """
    joined = ",".join(f"{k}={_escape_property(str(v))}" for k, v in properties.items())
    return f"::{level}{' ' + joined if joined else ''}::{_escape_data(message)}"


def _code(value: str) -> str:
    """Render untrusted text (paths, messages) as code in a table cell.

    Markdown inside backticks is shown as plain text, so a crafted file name can't
    add links or formatting. A backtick in the text would end the code early, a |
    would split the cell, and a newline would end the row, so those are replaced.
    """
    value = value.replace("`", "'").replace("\r", " ").replace("\n", " ")
    return "`" + value.replace("|", "\\|") + "`"


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    """Return a Markdown table as lines, followed by a blank line."""
    return [
        "| " + " | ".join(header) + " |",
        "|" + "---|" * len(header),
        *("| " + " | ".join(row) + " |" for row in rows),
        "",
    ]


def render_summary(
    head: Scan,
    base: Scan | None,
    failing: list[str],
    errors: list[Problem],
) -> str:
    """Return the Markdown job summary.

    In order: the result, which revisions were scanned or compared, how many
    mitigations have tagged and covered tests at head, a table of mitigations with
    fewer covered tests than at base, and, if any lost their last test, how to fix it.
    """
    lines = ["## Threat-model mitigation tests", ""]
    if errors:
        lines += [
            ("**Result: error.** The scan could not read every tagged file, so it can't "
            "tell whether a mitigation lost its tests."),
            "",
            *_table(
                ["File", "Line", "Problem"],
                [[_code(p.path), str(p.line), _code(p.message)] for p in errors],
            ),
        ]
    elif base is None:
        lines += ["**Result: scanned.** No base revision, so nothing was compared.", ""]
    elif failing:
        noun = "mitigation lost its" if len(failing) == 1 else "mitigations lost their"
        lines += [f"**Result: failed.** {len(failing)} {noun} last covered test.", ""]
    else:
        lines += ["**Result: passed.** No mitigation lost its last covered test.", ""]

    if base is None:
        lines += [f"Scanned `{head.commit[:12]}`.", ""]
    else:
        lines += [
            f"Compared base `{base.commit[:12]}` with head `{head.commit[:12]}`.",
            "",
        ]
        if base.errors:
            lines += [
                (f"{len(base.errors)} tagged files at base couldn't be parsed, so their "
                "tests weren't compared. The warnings name them."),
                "",
            ]
    lines += [
        (f"At head, {len({t.mitigation for t in head.tests})} mitigations have tagged tests and "
        f"{len(head.covered_counts())} have covered tests. A tagged test marked skip or "
        "xfail is not covered."),
        "",
    ]

    # One row for each ID with fewer covered tests at head than at base.
    if base is not None and not errors:
        before = base.covered_counts()
        after = head.covered_counts()
        rows = []
        for m in sorted(before):
            if after[m] >= before[m]:
                continue
            if m in failing:
                status = "**lost its last test**"
            elif not after[m]:
                status = "lost its last test, allowed by exception"
            else:
                status = "fewer tests"
            rows.append([m, str(before[m]), str(after[m]), status])
        if rows:
            lines += _table(["Mitigation", "Base", "Head", "Status"], rows)
    if failing:
        lines += [
            ("Tag another test with the ID, or, if the mitigation no longer needs a test "
            f"here, add `ID: reason` to `{EXCEPTIONS_FILE}` in this pull request."),
            "",
        ]
    return "\n".join(lines)


def scan_json(scan: Scan, repo_name: str, server_url: str) -> dict:
    """Return the scan as JSON-ready data, for the threat model's coverage report.

    Each ID maps to its covered tests. Skipped and xfail tests are left out, so they
    never count as coverage in the report. Entries have exactly the keys of ratm's
    TestRef(repo, path, name, line, url), since TestRef rejects any other key.
    """
    mitigations: dict[str, list[dict]] = {}
    for test in sorted(scan.tests, key=lambda t: t.mitigation):
        if not test.covered:
            continue
        # A permalink to the test's line at the scanned commit. The path is
        # percent-encoded so spaces and other characters survive in the link.
        url = None
        if repo_name:
            url = (
                f"{server_url}/{repo_name}/blob/{scan.commit}/"
                f"{urllib.parse.quote(test.path)}#L{test.line}"
            )
        mitigations.setdefault(test.mitigation, []).append(
            {
                "repo": repo_name,
                "path": test.path,
                "name": test.test,
                "line": test.line,
                "url": url,
            }
        )
    return {
        "schema": 1,
        "repo": repo_name,
        "commit": scan.commit,
        "mitigations": mitigations,
    }


def main(argv: list[str] | None = None) -> int:
    """Scan HEAD (and --base, if given), compare them, and report.

    Returns 1 if a tagged file at head couldn't be parsed, the exceptions file is
    malformed, or a mitigation lost its last covered test without an exception.
    Otherwise returns 0.
    """
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--path", default=".", help="git repository checkout to scan")
    parser.add_argument("--base", default="", help="revision to compare against")
    parser.add_argument(
        "--repo-name",
        default=os.environ.get("GITHUB_REPOSITORY", ""),
        help="repository name for the JSON output (default: $GITHUB_REPOSITORY)",
    )
    parser.add_argument("--json-output", help="write the head scan as JSON to this file")
    parser.add_argument(
        "--summary-file",
        default=os.environ.get("GITHUB_STEP_SUMMARY"),
        help="append the Markdown summary here (default: $GITHUB_STEP_SUMMARY, else stdout)",
    )
    args = parser.parse_args(argv)

    try:
        # Run git at the repository root so every path is root-relative.
        repo = _git(args.path, "rev-parse", "--show-toplevel").decode().strip()
        head = scan_commit(repo, "HEAD")
        base = scan_commit(repo, args.base) if args.base else None
    except GitError as e:
        print(annotation("error", str(e), title="Mitigation scan failed"))
        return 1

    # The exceptions file only matters when comparing.
    exceptions: set[str] = set()
    exceptions_errors: list[Problem] = []
    if base:
        source = read_blob(repo, head.commit, EXCEPTIONS_FILE) or b""
        exceptions, exceptions_errors = parse_exceptions(
            EXCEPTIONS_FILE, source.decode("utf-8", errors="replace")
        )
    # Problems at base were there before this change, so they only warn. Otherwise
    # they'd block every pull request, including the one that fixes them.
    errors = [*head.errors, *exceptions_errors]

    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as f:
            server_url = os.environ.get("GITHUB_SERVER_URL") or "https://github.com"
            json.dump(scan_json(head, args.repo_name, server_url), f, indent=2)
            f.write("\n")

    # If a tagged file at head has a syntax error, its tags are missing from the
    # counts, and comparing would report false losses. Report the error instead.
    failing = compare(base, head, exceptions) if base and not errors else []

    # Errors and warnings name the file and line, so GitHub can show them inline.
    # Lost mitigations have no single line to point at, so they're named in a title.
    for problem in errors:
        print(annotation("error", problem.message, file=problem.path, line=problem.line))
    for problem in base.errors if base else []:
        print(
            annotation(
                "warning", f"at base: {problem.message}", file=problem.path, line=problem.line
            )
        )
    for mitigation in failing:
        print(
            annotation(
                "error",
                f"{mitigation} had covered tests at base and has none at head",
                title="Mitigation lost its last test",
            )
        )

    # In Actions the summary goes to the job's summary page
    summary = render_summary(head, base, failing, errors)
    if args.summary_file:
        with open(args.summary_file, "a", encoding="utf-8") as f:
            f.write(summary + "\n")
    else:
        print(summary)

    return 1 if errors or failing else 0


if __name__ == "__main__":
    sys.exit(main())
