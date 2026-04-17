# freedomofpress/actionslib/act/signed-commit

This action allows changes to be committed to a repository with a GPG signed commit using
a GPG private key. This allows the commit signature to be verifiable and to show up as
`"verified"` in the Github interface.

> [!NOTE]
> To show up as `"verified"` on Github, the GPG public key must be added to an active
> Github account, and that same account must have verified the email associated with the
> GPG key.

See [the `action.yml` file](action.yml) for details on this action's inputs and outputs.

## Example Usage

Make a change to a file and commit the changes to a new branch:

```yaml
steps:
- name: Checkout
  uses: actions/checkout@v4

- name: Make some very important changes
  run: |
    sed -i 's/This/That' README.md

    echo "whatup" >new-file.txt

- name: Commit very important changes
  uses: freedomofpress/actionslib/act/signed-commit@main
  with:
    file: |
      README.md
      new-file.txt
    create-branch: an-amazing-change
    message: |
      This is a cool new commit that will fix all the problems

      For more info on this change see the docs here: https://xkcd.com/1597/
    gpg-key: ${{ secrets.MY_SOOPER_SEEKRET_GPG_PRIVATE_KEY }}
    gpg-email: someone@example.com
    gpg-identity: Infra Structure
```
