# Gemini Web → Drive → GitHub: untrusted transport specification

Canonical issue: https://github.com/chidionyema/idp/issues/7760

The intake workflow is **quarantine-only**. A GitHub repository_dispatch accepted by GitHub is not proof of Gemini origin, authorization, source document integrity, or code promotion. This branch deliberately implements **no privileged actuator**.

## Apps Script installation boundary

The following code is source-controlled, not installed. Deployment requires an authenticated Google Apps Script project with Drive access, a scoped GitHub credential, and an enabled time trigger. Until independently observed, all three are **UNVERIFIED**. The relay must only target the allowlisted idp repository and must never merge PRs, change secrets, or approve workflows.

Create a Drive folder dedicated to the Gemini outbox. Put JSON envelopes (not arbitrary Markdown instructions) in it. Apps Script Properties: `GENESIS_DRIVE_FOLDER_ID`, `GENESIS_GITHUB_TOKEN`. Store the token in Apps Script properties, never the Drive folder or repository. Use a fine-grained token with only the repository dispatch permission required for idp. The cloud script checks its own processed state and records receipts. Source provenance is still not authenticated; the trusted GitHub intake keeps everything quarantined.

## Event contract

```json
{
  "schema_version": 1,
  "event_id": "genesis-20261106-0001",
  "source": "gemini-web-drive",
  "source_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "document_id": "drivefile-12345678",
  "target_repo": "chidionyema/idp",
  "intent": "review-only"
}
```

`source_sha256` must be SHA-256 of the exact underlying Drive source bytes. `event_id` is an immutable ID. GitHub receipts are not signed proof of Gemini origin; that requires an independent, separately provisioned trust key and an attested producer.

## Remaining hard gates

- Authenticate and inspect the existing Google Drive folder, Apps Script project, trigger and property names (not secret values).
- Install only the reviewed script, prove a benign event with a real Drive file and source digest.
- Confirm GitHub Actions run with validated quarantine receipt, and test duplicate delivery and failed dispatch recovery.
- Add independent source authentication, bounded durable idempotency, and a trusted reviewer-to-Greenlane path before any code promotion.
- Check PR CI, Greenlane and deployed revision independently. No claim of release without receipts.
