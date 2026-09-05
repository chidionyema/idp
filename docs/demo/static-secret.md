# Demo: static-secret

`bin/static-secret-gate` walks the places a copyable credential lives on a host: `~/.oci/*.pem`,
the `gh` OAuth token in `~/.config/gh/hosts.yml`, every `.env` under the code tree, vault files
whose name says key, token or password, and the login keychain. Every line is one credential a
person could copy, and the last line is the count against the policy target of 0
(docs/reference/security-policy.md, crew#227). It exists because the 2026-08-25 cluster build
stalled on password prompts: a machine that authenticates with a copyable secret asks a person
to unlock it, and a machine with a workload identity does not.

Run on this checkout:

```
$ bin/static-secret-gate
static   ~/.oci/estate-tofu.pem            OCI API key; replaced by workload identity (crew#227 CP2/CP5)
...
FAIL    static-secret-gate: 30 static credential(s) remain; target 0 (crew#227)
```

Fixtures prove it both ways in `bin/idp-ci`: `tests/fixtures/static-secret/good` (empty) passes
and `tests/fixtures/static-secret/bad` (a key and a `.env`) fails.
