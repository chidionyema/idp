# Demo: owner-account

`bin/owner-account-gate` reads `docs/reference/owner-accounts.yaml`, the inventory of every
external provider the estate depends on, and counts the ones a single person can lock everyone
out of: no second owner, or a recovery route that lands in the same mailbox as the login. It
exists because on 2026-08-25 the founder said the whole estate is tied to one personal Gmail
account and that has to become configurable; the first step is a number.

Run on this checkout:

```
$ bin/owner-account-gate
single   github         no second owner; recovery is the login (founder-gmail)
single   oracle-cloud   no second owner; recovery is the login (founder-gmail)
...
FAIL     owner-account-gate: 9 of 9 providers have a single owner; target 0 (crew#227 CP7)
```

Fixtures prove it both ways in `bin/idp-ci`: `tests/fixtures/owner-accounts/good.yaml` (a
provider with a second owner) passes, `bad.yaml` (none) fails.
