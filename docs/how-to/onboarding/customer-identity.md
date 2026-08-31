# Onboarding: Customer sign-in

## What it is

The shop's customers will sign in through one place: a realm named `shop` on
Keycloak. That realm is a file in this repository —
`platform/customer-identity/realm/shop.yaml` — and the file is the truth. A
reconciler applies the file on every change, so the settings that decide who
may sign in are reviewed the same way code is reviewed.

`bin/idp-realm-diff` is the part that keeps that promise honest. It reads the
realm the server is actually running and grades it against the file:

```
bin/idp-realm-diff --export FILE [--realm platform/customer-identity/realm/shop.yaml]
```

It prints one of three verdicts and exits 0, 1 or 2:

- `ok` — every setting and every client the file declares matches the running
  realm.
- `FAIL` — the running realm is not what the file says, and each difference is
  named on its own line.
- `BLIND` — nothing was read back from the server, so nothing was measured.
  Absent evidence is never a pass.

## Why it exists

Because the alternative is a setting nobody can see. A person with the
administrator console open can turn off the lockout that stops password
guessing, stretch a token's life from five minutes to a day, or add a web
address that sign-ins may be sent back to. Every one of those is a way in, and
none of them leaves a trace in a pull request. The check turns a quiet console
change into a red build with the changed setting named.

It also refuses to guess. The file carries placeholders written as
`$(env:NAME)`, so no web address is typed into the repository. Set
`SHOP_ORIGIN` and `SHOP_REDIRECT_URI` before running it. If one of them has
no value, the check reports `BLIND` rather than treating the placeholder as
"anything matches." The `storefront-backend` client's password is never
read at all, so the check never holds a credential.

## How to change a sign-in setting

1. Edit `platform/customer-identity/realm/shop.yaml`.
2. Run the tests:
   `python3 -m pytest -q -p no:xdist -o addopts="" tests/test_the_customer_realm_is_code_and_a_console_change_is_caught.py`
3. Open a pull request. The change is reviewed as a change to who may sign in,
   because that is what it is.

Never change it in the console. A console change is not a shortcut — the check
finds it and the build goes red until the file and the server agree again.

## What the check will not print

The `storefront-backend` client's password. Settings whose names look like a password are
compared by presence only: the check says whether the running realm carries a
value, never what the value is. A test asserts the value never appears in the
output.

## Where it runs

Today: on a laptop and in the tests, against the two realm exports shipped
under `tests/fixtures/`. There is a demo that runs all three verdicts with no
cluster and no cloud key: [Customer sign-in](../../tutorials/demo/customer-identity.md).

Next, once the sign-in service itself is running: as a step that exports the
live realm and grades it on every change, and on a schedule.

## What is not done yet

The sign-in service is not running. The feature switch
`customer-identity` in `platform/features/features.yaml` is off, and the file
records what it will cost when it is turned on. Nothing signs in through
Keycloak until that switch is turned on in a separate, approved change.
