"""Tests for trace_mitigations.py. Run with:

python3 -m unittest discover -s act/trace-mitigations
"""

import contextlib
import io
import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

import trace_mitigations as tm

# Keep the developer's git config (signing, hooks, and so on) out of test repos.
GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}

BASE_FILES = {
    "molecule/testinfra/app/test_swap.py": """
        import pytest

        @pytest.mark.mitigates("MITIG52")
        def test_swap_disabled(host):
            pass

        @pytest.mark.mitigates("MITIG2")
        def test_apparmor(host):
            pass
        """,
    "securedrop/tests/test_apparmor.py": """
        import pytest

        @pytest.mark.mitigates("MITIG2")
        def test_profile():
            pass
        """,
    "tests/test_dom0_rpm.py": """
        import pytest

        @pytest.mark.mitigates("MITIGQW1")
        def test_rpm_signed():
            pass
        """,
}


def scan(source: str) -> tm.Scan:
    return tm.scan_python("tests/test_x.py", textwrap.dedent(source).encode())


def found(result: tm.Scan) -> list[tuple[str, str, int, str | None]]:
    return [(t.mitigation, t.test, t.line, t.excluded_by) for t in result.tests]


def lost_ids(stdout: str) -> list[str]:
    """Return the IDs named in "lost its last test" annotations."""
    return [
        line.rsplit("::", 1)[1].split()[0]
        for line in stdout.splitlines()
        if line.startswith("::error title=Mitigation lost its last test::")
    ]


class TestPython(unittest.TestCase):
    def test_function_mark_with_several_ids_and_both_series(self):
        result = scan(
            """
            @pytest.mark.parametrize("x", [1, 2])
            @pytest.mark.mitigates("MITIG1", "MITIGQW12", "not-an-id")
            @pytest.mark.mitigates("MITIG2")
            def test_x(x):
                pass

            @pytest.mark.mitigates("MITIG3")
            async def test_async():
                pass

            @mark.mitigates("MITIG4")
            def test_bare_mark_is_ignored():
                pass
            """
        )
        self.assertEqual(
            found(result),
            [
                ("MITIG1", "test_x", 5, None),
                ("MITIGQW12", "test_x", 5, None),
                ("MITIG2", "test_x", 5, None),
                ("MITIG3", "test_async", 9, None),
            ],
        )

    def test_module_and_class_pytestmark(self):
        result = scan(
            """
            pytestmark = [pytest.mark.mitigates("MITIG56"), pytest.mark.slow]

            def test_modules():
                pass

            @pytest.mark.mitigates("MITIG2")
            class TestK:
                pytestmark = pytest.mark.mitigates("MITIG53")

                def helper(self):
                    pass

                class TestNested:
                    def test_k(self):
                        pass
            """
        )
        self.assertEqual(
            [(t.mitigation, t.test) for t in result.tests],
            [
                ("MITIG56", "test_modules"),
                ("MITIG2", "TestK::TestNested::test_k"),
                ("MITIG53", "TestK::TestNested::test_k"),
                ("MITIG56", "TestK::TestNested::test_k"),
            ],
        )

    def test_skip_and_xfail_are_not_covered(self):
        result = scan(
            """
            @pytest.mark.mitigates("MITIG1")
            @pytest.mark.skip(reason="broken")
            def test_skip():
                pass

            @pytest.mark.skip
            @pytest.mark.mitigates("MITIG2")
            def test_bare_skip():
                pass

            @pytest.mark.mitigates("MITIG3")
            @pytest.mark.skipif(IS_CI, reason="Skipping on CI")
            def test_skipif():
                pass

            @pytest.mark.xfail
            @pytest.mark.mitigates("MITIG4")
            def test_xfail():
                pass

            @pytest.mark.skip_in_prod
            @pytest.mark.mitigates("MITIG5")
            def test_skip_in_prod():
                pass
            """
        )
        self.assertEqual(
            {t.mitigation: t.excluded_by for t in result.tests},
            {
                "MITIG1": "skip",
                "MITIG2": "skip",
                "MITIG3": "skipif",
                "MITIG4": "xfail",
                "MITIG5": None,
            },
        )

    def test_skip_on_class_or_module_reaches_tagged_tests(self):
        result = scan(
            """
            pytestmark = pytest.mark.xfail

            @pytest.mark.skip
            class TestA:
                @pytest.mark.mitigates("MITIG1")
                def test_a(self):
                    pass

            @pytest.mark.mitigates("MITIG2")
            def test_b():
                pass
            """
        )
        self.assertEqual(
            {t.mitigation: t.excluded_by for t in result.tests},
            {"MITIG1": "skip", "MITIG2": "xfail"},
        )


def scan_comments(path: str, source: str) -> list[tuple[str, str, int, str | None]]:
    return found(tm.scan_comment_tags(path, textwrap.dedent(source)))


class TestRust(unittest.TestCase):
    def test_tags(self):
        result = scan_comments(
            "proxy/src/main.rs",
            """
            #[cfg(test)]
            mod tests {
                // mitigates: MITIG1, MITIGQW2
                /// Checks the proxy rejects unknown fields.
                // mitigates: MITIG3 not-an-id
                #[test]
                fn test_unknown_fields() {}

                // mitigates: MITIG4
                #[tokio::test]
                #[cfg_attr(
                    not(feature = "qubesdb"),
                    ignore
                )]
                async fn test_qubesdb() {}

                // mitigates: MITIG5
                #[test]
                #[ignore = "flaky"]
                pub fn test_ignored() {}

                // mitigates: MITIG6
                fn helper() {}

                // mitigates: MITIG7

                #[test]
                fn test_after_blank_line() {}

                #[test]
                // mitigates: MITIG8
                fn test_tag_after_attribute() {}

                #[ignore]
                // mitigates: MITIG9
                #[test]
                fn test_ignore_before_tag() {}
            }
            """,
        )
        self.assertEqual(
            result,
            [
                ("MITIG1", "test_unknown_fields", 8, None),
                ("MITIGQW2", "test_unknown_fields", 8, None),
                ("MITIG3", "test_unknown_fields", 8, None),
                ("MITIG4", "test_qubesdb", 16, "ignore"),
                ("MITIG5", "test_ignored", 21, "ignore"),
                ("MITIG8", "test_tag_after_attribute", 33, None),
                ("MITIG9", "test_ignore_before_tag", 38, "ignore"),
            ],
        )


class TestJavaScript(unittest.TestCase):
    def test_tags(self):
        result = scan_comments(
            "app/src/main/proxy.test.ts",
            """
            describe("proxy", () => {
              // mitigates: MITIG1
              it("rejects unknown fields", () => {});

              /* mitigates: MITIG2 */
              it(
                "has a title prettier wrapped onto the next line",
                async () => {},
              );

              /**
               * mitigates: MITIG3
               */
              it.each([
                ["a", 1],
                ["b", (2)],
              ])("handles %s", (name, n) => {});

              // mitigates: MITIG4
              it.skipIf(process.env.CI)(`skips ${"in CI"}`, () => {});

              // mitigates: MITIG5
              test.todo("later");

              // mitigates: MITIG6
              xit('is disabled', () => {});

              // mitigates: MITIG7
              describe.sequential("a group", () => {});

              // A comment that only says mitigates: MITIG8 in passing.
              it("is not tagged", () => {});

              // mitigates: MITIG9
              const notATest = 1;
            });
            """,
        )
        self.assertEqual(
            result,
            [
                ("MITIG1", "rejects unknown fields", 4, None),
                ("MITIG2", "has a title prettier wrapped onto the next line", 7, None),
                ("MITIG3", "handles %s", 15, None),
                ("MITIG4", 'skips ${"in CI"}', 21, "skipIf"),
                ("MITIG5", "later", 24, "todo"),
                ("MITIG6", "is disabled", 27, "xit"),
                ("MITIG7", "a group", 30, None),
            ],
        )


class TestExceptions(unittest.TestCase):
    def test_parse(self):
        exceptions, errors = tm.parse_exceptions(
            "x.txt",
            textwrap.dedent(
                """
                # Mitigations allowed to have no tagged tests here.
                MITIG52: superseded by MITIG60, see #1234
                MITIGQW3 :  tested in openQA only

                MITIG7:
                MITIG8 no colon
                mitig9: lowercase
                """
            ),
        )
        self.assertEqual(exceptions, {"MITIG52", "MITIGQW3"})
        self.assertEqual([e.line for e in errors], [6, 7, 8])


class TestCompare(unittest.TestCase):
    @staticmethod
    def fake_scan(*specs: tuple[str, str | None]) -> tm.Scan:
        return tm.Scan(
            tests=[
                tm.TaggedTest(m, "t.py", f"test_{i}", i, x) for i, (m, x) in enumerate(specs)
            ]
        )

    def test_compare(self):
        base = self.fake_scan(
            ("MITIG1", None),
            ("MITIG2", None),
            ("MITIG2", None),
            ("MITIG3", None),
            ("MITIGQW1", None),
            ("MITIG9", "skip"),
        )
        head = self.fake_scan(
            ("MITIG2", None), ("MITIG3", "skip"), ("MITIG5", None), ("MITIG9", "skip")
        )
        self.assertEqual(tm.compare(base, head, {"MITIGQW1"}), ["MITIG1", "MITIG3"])


class TestGit(unittest.TestCase):
    """Run the whole script against a real repository, starting from BASE_FILES."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self.git("init", "-q", "-b", "main")
        self.base = self.commit(BASE_FILES)

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]
            + ["-C", str(self.repo), *args],
            check=True,
            capture_output=True,
            text=True,
            env=GIT_ENV,
        ).stdout.strip()

    def commit(self, files: dict[str, str | None]) -> str:
        for name, content in files.items():
            path = self.repo / name
            if content is None:
                path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(textwrap.dedent(content))
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "change")
        return self.git("rev-parse", "HEAD")

    def run_script(self, *args: str) -> tuple[int, str, str]:
        summary = self.tmp / "summary.md"
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = tm.main(["--path", str(self.repo), "--summary-file", str(summary), *args])
        return code, stdout.getvalue(), summary.read_text()

    def test_losing_tests(self):
        self.commit({"molecule/testinfra/app/test_swap.py": None})
        code, stdout, summary = self.run_script("--base", self.base)
        self.assertEqual(code, 1)
        self.assertEqual(lost_ids(stdout), ["MITIG52"])
        self.assertIn("**Result: failed.**", summary)
        self.assertIn("| MITIG2 | 2 | 1 | fewer tests |", summary)
        self.assertIn("| MITIG52 | 1 | 0 | **lost its last test** |", summary)

    def test_exception_allows_loss(self):
        self.commit(
            {
                "tests/test_dom0_rpm.py": None,
                ".github/mitigation-exceptions.txt": "MITIGQW1: moved to openQA, see #12\n",
            }
        )
        code, stdout, summary = self.run_script("--base", self.base)
        self.assertEqual(code, 0)
        self.assertNotIn("::error", stdout)
        self.assertIn("allowed by exception", summary)

    def test_base_compared_to_merge_commit(self):
        # A tag added on main after the branch point is not "lost" by the PR, as
        # long as head is the merge commit rather than the PR branch tip.
        self.git("checkout", "-q", "-b", "feature")
        self.commit({"README": "x\n"})
        self.git("checkout", "-q", "main")
        self.commit({"tests/test_new.py": '@pytest.mark.mitigates("MITIG99")\ndef test_new(): pass\n'})
        self.git("merge", "-q", "--no-ff", "--no-edit", "feature")
        code, _, _ = self.run_script("--base", "HEAD^1")
        self.assertEqual(code, 0)

    def test_unparsable_files(self):
        # A file that only mentions the word in prose is never parsed.
        self.commit({"scripts/old.py": "print 'this mitigates nothing'\n"})
        code, _, _ = self.run_script("--base", self.base)
        self.assertEqual(code, 0)

        # A tagged file that can't be parsed fails the scan.
        self.commit(
            {"securedrop/tests/test_apparmor.py": '@pytest.mark.mitigates("MITIG2")\ndef test_profile(:\n'}
        )
        broken = self.git("rev-parse", "HEAD")
        code, stdout, summary = self.run_script("--base", self.base)
        self.assertEqual(code, 1)
        self.assertIn("::error file=securedrop/tests/test_apparmor.py", stdout)
        self.assertIn("**Result: error.**", summary)

        # The same file broken at base only warns, so it can't block its own fix.
        self.commit(
            {"securedrop/tests/test_apparmor.py": BASE_FILES["securedrop/tests/test_apparmor.py"]}
        )
        code, stdout, _ = self.run_script("--base", broken)
        self.assertEqual(code, 0)
        self.assertIn("::warning file=securedrop/tests/test_apparmor.py", stdout)

    def test_comment_tags(self):
        self.commit(
            {
                "proxy/src/main.rs": "// mitigates: MITIG60\n#[test]\nfn test_proxy() {}\n",
                "app/src/proxy.test.ts": '// mitigates: MITIG61\nit("works", () => {});\n',
                # Prose that isn't directly above a test, in a file type not scanned.
                "docs/notes.md": "// mitigates: MITIG62\nit('x')\n",
            }
        )
        base = self.git("rev-parse", "HEAD")
        self.commit({"app/src/proxy.test.ts": 'it("works", () => {});\n'})
        code, stdout, summary = self.run_script("--base", base)
        self.assertEqual(code, 1)
        self.assertEqual(lost_ids(stdout), ["MITIG61"])
        self.assertIn("| MITIG61 | 1 | 0 | **lost its last test** |", summary)
        self.assertNotIn("MITIG60 |", summary)
        self.assertNotIn("MITIG62", summary)

    def test_scan_only_writes_json(self):
        commit = self.commit(
            {
                "tests/x test.py": """
                    import pytest

                    @pytest.mark.mitigates("MITIG52")
                    @pytest.mark.skip
                    def test_later():
                        pass

                    @pytest.mark.mitigates("MITIG53")
                    def test_grsecurity():
                        pass
                    """
            }
        )
        json_path = self.tmp / "scan.json"
        code, _, summary = self.run_script(
            "--repo-name", "freedomofpress/securedrop", "--json-output", str(json_path)
        )
        self.assertEqual(code, 0)
        self.assertIn("**Result: scanned.**", summary)
        data = json.loads(json_path.read_text())
        self.assertEqual(data["commit"], commit)
        self.assertEqual(
            list(data["mitigations"]), ["MITIG2", "MITIG52", "MITIG53", "MITIGQW1"]
        )
        # Exact dicts, since ratm's TestRef rejects any key it doesn't expect. The
        # skipped test_later is left out of MITIG52.
        url = f"https://github.com/freedomofpress/securedrop/blob/{commit}/"
        self.assertEqual(
            data["mitigations"]["MITIG52"],
            [
                {
                    "repo": "freedomofpress/securedrop",
                    "path": "molecule/testinfra/app/test_swap.py",
                    "name": "test_swap_disabled",
                    "line": 5,
                    "url": url + "molecule/testinfra/app/test_swap.py#L5",
                }
            ],
        )
        self.assertEqual(
            data["mitigations"]["MITIG53"][0]["url"], url + "tests/x%20test.py#L10"
        )


if __name__ == "__main__":
    unittest.main()
