# Gemini Web → Google Drive → GitHub: authenticated quarantine transport

Canonical claim: https://github.com/chidionyema/idp/issues/7760
Code branch: lane/gemini-drive-relay-7760

This is **Gemini Web as a source environment**, not Argon's Telegram outbox.
It uses a private Google Drive folder as a durable outbox and an Apps Script
trigger as a transport adapter. The GitHub receiver accepts **data only**:
no document text, code, private Drive IDs, merge commands, secret values or
approval requests are eligible for execution by this path.

## Trust and origin

The sender reads named GENESIS_*.md or GENESIS_*.txt Drive files and computes
SHA-256 over its own UTF-8 blob. It submits only structured metadata and an HMAC
using GENESIS_DRIVE_RELAY_HMAC_KEY. The receiver rejects unknown fields, stale
timestamps (>900 seconds), invalid digests, missing/weak keys, altered HMACs,
unrecognised repositories and privileged intents. It creates a quarantine receipt
as a GitHub Actions artifact with 30-day retention. It never merges or deploys.

**An HMAC authenticates the configured Apps Script sender, NOT the human or
Gemini model author of the document**; source provenance still needs independent
review of Drive file history, permissions and content. The payload's source digest
is evidence to compare during review, not a signature of the original author.

## Envelope (generated automatically by Code.gs)

Fields: schema_version=1; event_id; source=gemini-web-drive;
source_sha256 (64 lowercase hex); document_id (Drive file ID);
target_repo=chidionyema/idp; intent=review-only; issued_at (Unix seconds);
signature (HMAC-SHA256, lowercase hex).

Canonical HMAC bytes are the UTF-8 newline-joined strings in this exact order:
schema_version, event_id, source, source_sha256, document_id, target_repo,
intent, issued_at. The signature key must be at least 32 bytes of securely
generated random data and stored independently in Apps Script Properties and
the GitHub Actions secret GENESIS_DRIVE_RELAY_HMAC_KEY.

## Deployment and evidence boundary

The checked-in Apps Script is **source code only**. No installation, Google
OAuth authorization, Drive folder existence, trigger state, Script Properties
or successful Gemini-origin dispatch is implied by this Git commit.

Code.gs requires the private Script Properties GENESIS_DRIVE_FOLDER_ID,
GENESIS_GITHUB_TOKEN and GENESIS_DRIVE_RELAY_HMAC_KEY. The GitHub
repository_dispatch API requires Contents:write authority on its destination;
this is a substantial credential blast radius, so the production preference is
a dedicated low-privilege receiving repository or properly scoped GitHub App.
Do not promote the script into production until that risk has been reviewed.

The sender marks HTTP 204 as DISPATCHED_UNCONFIRMED, then checks GitHub's
actual workflow run by event_id. Only a completed successful intake run changes
that local record to ACKNOWLEDGED; a failed run is a hard stop and queued runs
are retried after a bounded backoff. Its token therefore also needs Actions:read
permission. This is *transport* acknowledgment, not approval/merge/deploy.
There is still **no independently tested live Drive-to-GitHub ACK or durable
cross-system exactly-once guarantee**; Apps Script Properties and the 100-run
GitHub lookback window have bounded retention and require resilience tests.

Operational completion requires, in order:
1. Real authenticated Google Drive + Apps Script configuration and live trigger.
2. A benign Gemini-origin canary with exact source digest.
3. Successful repository_dispatch and independent GitHub Actions receipt.
4. Replay/tamper/refusal coverage, deduplication and durable ACK.
5. A separate approved worker retrieves the actual Drive bytes and submits
   reviewed Git code via the estate's Greenlane.
6. Real deployed revision and external caller-path proof.

A GitHub PR, successful unit test, HTTP 204 or queued runner is never a
deployed system. No founder CLI chores or silent replacement of GitOps law.
