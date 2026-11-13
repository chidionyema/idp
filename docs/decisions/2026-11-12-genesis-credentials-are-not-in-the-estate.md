# The Genesis inbound credentials are not in the estate to sync

Date: 2026-11-12. Founder asked: get the missing `GENESIS_GOOGLE_*` credentials into
Bitwarden sync. This records what was measured, because the request assumed the
credentials exist somewhere and are merely unsynced. They do not exist.

## What the bridge requires

`bin/genesis-inbound-bridge.py` (branch `feat/gemini-inbound-bridge-20261111`, PR #7981)
reads four values and refuses to start without them:

| variable | line | purpose |
|---|---|---|
| `GENESIS_GOOGLE_CLIENT_ID` | 63 | OAuth client |
| `GENESIS_GOOGLE_CLIENT_SECRET` | 64 | OAuth client |
| `GENESIS_GOOGLE_REFRESH_TOKEN` | 65 | the founder's Drive/Gmail grant |
| `GENESIS_DRIVE_FOLDER_ID` | 308 | which Drive folder is the outbox |

## Measured, not assumed

| where the credentials could live | measurement | result |
|---|---|---|
| SOPS vault `estate-secrets/secrets/dev/` | 12 files listed by name | **no Google OAuth entry** (`GEMINI_API_KEY` is an LLM key, not Drive OAuth) |
| SOPS vault, any `*GOOGLE*` name | `grep -rhoE "^[A-Z_]*GOOGLE[A-Z_]*=" secrets/` | **0 matches** |
| GitHub Actions secrets, `chidionyema/idp` | `gh secret list` -> 47 secrets | **0 match `GENESIS` or `GOOGLE`** |
| `vault-seed.yml` entries | read the workflow | each entry is a hardcoded step fed by a **pre-existing** `SEED_*` secret; nothing to seed from |
| Bitwarden CLI | `which bw` | **not installed**, so not a reachable source either |
| the bridge itself | `GENESIS_DRIVE_FOLDER_ID=x GH_TOKEN=... python3 bin/genesis-inbound-bridge.py --repo chidionyema/idp` | `FAILED: Google OAuth credentials are missing; intake NOT ACTIVE` |

The bridge's negative tests do pass (`--self-test` -> `core negative tests PASS`), so the
gate is working; it is the credential that is absent.

## Why this is not a thing an agent can close

An OAuth refresh token is minted by the founder granting a Google account access to a
client. It cannot be derived, guessed, or copied from another surface, and AGENTS.md
section 4 forbids an agent inventing or pasting a credential. There is no path from this
machine to a value that has never existed here.

## The one action that unblocks it

The founder creates a Google Cloud OAuth client for the Drive/Gmail scopes, completes the
grant once locally, and stores the four values. Two supported routes, in the estate's
preferred order:

1. **Vault (preferred, SOPS + age).** Add the four under `estate-secrets/secrets/dev/`
   using `scripts/secret-add`, then `git -C estate-secrets push`. Bitwarden syncs from
   the vault, not the other way round.
2. **GitHub secret -> workflow.** Add `SEED_GENESIS_GOOGLE_CLIENT_ID`,
   `SEED_GENESIS_GOOGLE_CLIENT_SECRET`, `SEED_GENESIS_GOOGLE_REFRESH_TOKEN` and
   `SEED_GENESIS_DRIVE_FOLDER_ID` to the repo, then add a `genesis-inbound` step to
   `vault-seed.yml` matching the `laptop-vendors` shape (a hardcoded step, value from
   the `SEED_*` secret, never printed).

Route 1 is the smaller change and keeps one source of truth.

## Also note: the Google Drive ban

AGENTS.md and the founder's standing order forbid reading Google Drive and
`~/Library/CloudStorage` from this machine. Even with credentials, the bridge reads Drive
through the **API** using the refresh token, which is the approved path; it does not read
the mounted CloudStorage folder. The two are not in conflict, and this ADR does not
relax the mounted-folder ban.

## Verdict

`BLOCKED` on a founder action, not on engineering. The estate-side work (the bridge, its
refusal, its negative tests) is complete and green on PR #7981.

Claim: chidionyema/idp#8000
Agent: estate-agent
