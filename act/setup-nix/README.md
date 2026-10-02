# freedomofpress/actionslib/act/setup-nix

Installs and configures [Nix](https://nixos.org/) for Github Actions. Optionally supports
leveraging the Github Actions cache, so that nix-built artifacts are fetched from the
cache.

The cache logic is only saved on the default branch, since GH limits cache sizes per repo
to 10GB. That should be sufficient to ensure that tooling via a `flake.nix` file results
in warm cache hits. If the 10GB limit bites, we can always stand up a custom cache
solution, and inject that config in into the action's `nix.conf`.

The action has its own shell script for fetching and verifying SHA256 checksums of the nix
installer, because
[nix-quick-install-action](https://github.com/nixbuild/nix-quick-install-action) fetches
from Github releases without verifying. The manually compiled checksums provides a
sanity-check on integrity, so modification of an already published release object would be
detected, and fail the installation.

See [the `action.yml` file](action.yml) for details on this action's inputs. To bump Nix,
see the header of [`fetch-nix.sh`](fetch-nix.sh).

For jobs that only need to run a script, the
[`setup-nix` reusable workflow](../../.github/workflows/setup-nix.yaml) wraps this action
along with a checkout.

## Example Usage

```yaml
steps:
- name: Checkout
  uses: actions/checkout@<sha>
  with:
    persist-credentials: false

- name: Setup Nix
  uses: freedomofpress/actionslib/act/setup-nix@main

- name: Run integration tests
  run: nix develop --command just integration

- name: Upload logs
  if: failure()
  uses: actions/upload-artifact@<sha>
  with:
    path: target/integration-logs
```
