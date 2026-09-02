# The Bitwarden bootstrap, shown working

The demo is one command and one pull request.

```
gh workflow run vault-bootstrap.yml
gh run watch
```

Expected lines in the run's log:

```
ok    bws     project estate created
ok    config  both identifiers written to clusters/oke/estate-config.yaml (public names, not secrets)
```

and a pull request titled "config: Bitwarden identifiers from the bootstrap run" appears,
touching exactly one file. A second run of the same command reports the project already
exists and opens nothing.

This page carries no run link yet: the first run waits on the machine token being placed in
the vault (see [the onboarding page](../onboarding/vault-bootstrap.md)). The first green
run's link replaces this paragraph.
