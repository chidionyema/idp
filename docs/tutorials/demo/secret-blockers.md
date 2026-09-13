# Demo: the founder blocker that read as "Reconciliation in progress"

One minute. The gap between a status and a step.

## Before

```
$ kubectl -n flux-system get kustomization cyrus
cyrus   Unknown   Reconciliation in progress
```

Three layers down, that is:

```
flux:  health check failed after 10m: timeout waiting for:
       [ExternalSecret/cyrus/cyrus-linear-oauth status: 'InProgress']
ESO:   Ready=False / SecretSyncedError -- could not get secret data from provider
```

And the bottom line is: two vault entries that can only be created **in a browser**,
because Linear publishes no API to create an OAuth application.

## Run it

```bash
cd ~/dev/code/idp
bin/idp-externalsecret-blockers
```

## After

```
ok    secret-blockers  138 ExternalSecret(s); 5 blocked, 5 waiting on a value only a
      person can produce, 0 other
      FOUNDER ACTION: backstage/verdict-key-wall needs verdict-hmac-key in estate-vault
      FOUNDER ACTION: cyrus/cyrus-linear-oauth needs cyrus-linear-client-id,
                      cyrus-linear-client-secret in human-vault
      FOUNDER ACTION: hermes-agent/human-telegram needs TELEGRAM_HERMES_BOT_TOKEN
      ...
```

## What to look at

**The key is the actionable half.** `InProgress` is not a step anyone can take.
"the vault has no `cyrus-linear-client-id`" is.

**FOUNDER ACTION and ESTATE are different lines.** `SecretSyncedError` means the
value does not exist and a person produces it. An unreachable store means
something is broken and an agent fixes it. Reporting the second as the first is
how a real defect waits a week for a human who cannot fix it.

**The list is generated.** Five of 138, every one with its key and its store —
never typed, so it cannot go stale.

## Prove it bites

```bash
bin/idp-externalsecret-blockers --from tests/fixtures/secret-blockers/bad/externalsecrets.json --fail-on-blocker
# FAIL  secret-blockers  1 ExternalSecret(s) cannot sync
# rc=1
```

A gate that cannot fail is decoration. This one fails on the exact shape that
held `cyrus`, and the fixture keeps it failing there.
