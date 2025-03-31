# freedomofpress/actionslib/act/delete-artifact

Github provides actions for
[creating/uploading artifacts](https://github.com/actions/upload-artifact) and
[downloading artifacts](https://github.com/actions/download-artifact) but no way to delete
an artifact. While artifacts do expire (with a configurable lifetime) there is also a
maximum artifact quota that a given repo can create in a given 6 hour period. This makes
it prudent to clean up artifacts after a job run if there is no need for them to persist.

See [the `action.yml` file](action.yml) for details on this action's inputs and outputs.

## Example Usage

Create an artifact as part of a job, run a 2nd job that makes use of the artifact, and
then finally clean up the artifact after the last job completes:

```yaml
jobs:
  setup:
    name: Setup
    steps:
    - name: Create artifact
      uses: actions/upload-artifact@v4
      with:
        name: my-very-cool-artifact
        path: |
          ./path/to/some/blob.data
          ./path/to/some/glob.json
          ./path/to/some/bucket.zip
        retention-days: 1

  process:
    name: Process
    needs: setup
    steps:
    - name: Download artifact
      uses: actions/download-artifact@v4
      with:
        name: my-very-cool-artifact
        path: ./path/to/local/data

  cleanup:
    name: Cleanup
    needs:
    - setup
    - process
    if: ${{ always() }}  # ensures cleanup always runs, even if 'process' fails
    steps:
    - name: Delete artifact
      uses: freedomofpress/actionslib/act/delete-artifact@main
      with:
        name: my-very-cool-artifact
        error-if-absent: false
```
