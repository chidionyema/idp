# Onboarding: a secret that cannot sync is a founder action, not a status

`bin/idp-externalsecret-blockers`, rule `externalsecret-blockers-are-loud`.

## What it is for

`cyrus` sat `HealthCheckFailed` for days. The reason was buried three layers down:

```
cluster:  cyrus    Ready=Unknown   "Reconciliation in progress"
flux:     "health check failed after 10m: timeout waiting for:
           [ExternalSecret/cyrus/cyrus-linear-oauth status: 'InProgress']"
ESO:      "Ready=False / SecretSyncedError -- could not get secret data from provider"
```

The bottom line is not something anyone can fix in code. The vault entries
`cyrus-linear-client-id` and `cyrus-linear-client-secret` are **born in a browser** —
Linear publishes no API to create an OAuth application — so the pair can only be
typed by a person.

R47 says a founder blocker is loud and one action. A blocker that reads
`Reconciliation in progress` is neither: nobody knows it exists, and the person who
could clear it is the one not being told.

## Run it

```bash
bin/idp-externalsecret-blockers
bin/idp-externalsecret-blockers --json | jq .summary
```

```
ok    secret-blockers  138 ExternalSecret(s); 5 blocked, 5 waiting on a value only a
      person can produce, 0 other
      FOUNDER ACTION: backstage/verdict-key-wall needs verdict-hmac-key in estate-vault
      FOUNDER ACTION: concierge/human-card-key needs CONCIERGE_CARD_KEY in human-vault
      FOUNDER ACTION: cyrus/cyrus-linear-oauth needs cyrus-linear-client-id,
                      cyrus-linear-client-secret in human-vault
      FOUNDER ACTION: hermes-agent/human-telegram needs TELEGRAM_HERMES_BOT_TOKEN in human-vault
      FOUNDER ACTION: notify/human-apprise-telegram needs TELEGRAM_ALERTS_BOT_TOKEN,
                      TELEGRAM_ALERTS_CHAT_ID in human-vault
```

That list **is** the founder's work queue, and it is generated, never typed.

## The distinction that matters

`SecretSyncedError` means *the value is not there yet*, which a person produces.
Anything else — an unreachable store, a selector matching nothing, a vault
refusing auth — is an **estate defect** and is reported as one:

```
FOUNDER ACTION   the value does not exist and a person must create it
ESTATE           something is broken and an agent must fix it
```

Dressing an infrastructure failure as "wait for the founder" is how a real defect
waits a week for a human who cannot fix it. The two never share a line.

## What it does not do

**It does not fail on them.** A missing vault entry is a person's step and the
estate has no power to take it; refusing the tree for it would be a guard refusing
work it cannot unblock (R38), and a gate red from day one gets switched off.
`--fail-on-blocker` is the flag a caller uses once the count is zero, to keep it
there.

**A cluster that cannot be read exits `2` with `BLIND`**, never `0` with an empty
report. `--from <file>` reads a `kubectl get -o json` document instead, which is
what makes the rule gradable offline.

## Tests

```bash
python3 -m pytest tests/bdd/test_externalsecret_blockers.py -q
```

Ten scenarios: the cyrus blocker is refused and names its vault keys; the same
secret synced passes; a missing provider entry is marked for a person; a different
failure is **not** dressed as a founder action; every blocker names the key it
needs; a synced one is not a blocker; an empty estate is zero rather than broken;
the default run reports without refusing; an unreadable document is BLIND not
clean; and the store is named beside the key, because a key without its store is
half an instruction.
