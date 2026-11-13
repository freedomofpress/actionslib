# freedomofpress/actionslib/act/trace-mitigations

This action looks for Python, Rust, and JS/TS tests that are tagged with SecureDrop
threat-model mitigation IDs (like `MITIG52` or `MITIGQW3`), and fails CI when a mitigation
that used to have tests is left without any. It reads the source straight from git and
never runs the tests. The output only ever mentions mitigation IDs, because the titles
live in the [threat model](https://github.com/freedomofpress/securedrop-threat-model).

See [the `action.yml` file](action.yml) for details on this action's inputs. For pull
requests, the
[`trace-mitigations` reusable workflow](../../.github/workflows/trace-mitigations.yaml)
wraps this action along with a checkout.

## Tagging Tests

### Python

Add the `mitigates` mark to a test function or class, or to a module's or class's
`pytestmark`. If you mark a class or module, every `test*` function inside it is tagged.

```python
@pytest.mark.mitigates("MITIG1", "MITIG2")
def test_apparmor_enforced(host): ...
```

If your repo runs pytest with `--strict-markers`, you'll need to register the marker:
`mitigates(*ids): threat-model mitigations this test verifies`.

### Rust and JS/TS

Put a `mitigates:` comment directly above the test. In Rust that's a `fn` with a `#[test]`
attribute (or one like `#[tokio::test]`). In JS/TS it's an `it`, `test`, `describe`, or
`suite` call, including forms like `it.each(...)`. Other comments, more tags, and Rust
attributes can sit between the tag and the test, but a blank line or code can't. Rust
attributes can also come before the tag.

```rust
// mitigates: MITIG1, MITIG2
#[test]
fn test_rejects_unknown_fields() {}
```

```ts
// mitigates: MITIG3
it("rejects unknown fields", () => {});
```

The scan reads these files line by line, so a tag on a `describe` counts as one test, and
isn't passed to the tests inside it. It also doesn't apply to Rust `mod` blocks.

## Coverage

A tagged test doesn't count if it's skipped or expected to fail:

- **Python:** the test, its class, or its module is marked `skip`, `skipif`, or `xfail`.
  Other marks, like `skip_in_prod`, are ignored.
- **Rust:** the test has `#[ignore]`, or a `#[cfg_attr(..., ignore)]`.
- **JS/TS:** the call is `xit`, `xtest`, or `xdescribe`, or uses `.skip`, `.todo`,
  `.fails`, `.skipIf`, or `.runIf`.

That includes conditional skips, since the scan has no way to evaluate the condition.

The scan won't notice a skip that happens while the test runs, like `pytest.skip()` or
marks passed through `pytest.param`. It also doesn't see a skip on an enclosing
`describe`, so a tagged `it` inside `describe.skip(...)` still counts.

When `base` is set, the action fails if a mitigation had at least one test at base and has
none at head (for example, because its only test was removed). If only some of a
mitigation's tests were removed, it shows up in the job summary but doesn't fail the
check. To remove a mitigation's last test on purpose, add `ID: reason` to
`.github/mitigation-exceptions.txt` in the same pull request.

A tagged file that can't be parsed at head fails the check. At base it only produces a
warning, so it can't block the pull request that fixes it.

If `base` isn't in the checkout, the action fetches it from `origin`. That fetch doesn't
use credentials, so it only works for public repos.

Without `base`, the action just scans for tags. To save the results as JSON, run the
script directly with `--json-output` (and `--repo-name` for the links). Each ID under
`mitigations` lists its tests with the same keys as
[threat-modeling-ssg](https://github.com/freedomofpress/threat-modeling-ssg/)'s `TestRef`
(`repo`, `path`, `name`, `line`, `url`). Skipped tests are left out. The scan only checks
that IDs look right, not that they actually exist in the threat model.

## Example Usage

Check pull requests entries:

```yaml
on:
  pull_request:
  merge_group:

permissions: {}

jobs:
  trace-mitigations:
    permissions:
      contents: read
    uses: freedomofpress/actionslib/.github/workflows/trace-mitigations.yaml@main
```

If your repo's zizmor config restricts unpinned `uses:`, you'll need to allow this
workflow.

Run the script or its tests locally:

```sh
python3 act/trace-mitigations/trace_mitigations.py --path ../securedrop --base origin/develop
python3 act/trace-mitigations/trace_mitigations.py --path ../securedrop \
    --repo-name freedomofpress/securedrop --json-output securedrop.json
python3 -m unittest discover -s act/trace-mitigations
```
