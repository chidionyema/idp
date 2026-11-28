# Estate provisioning plane: stop handing console steps back to the founder

Status: **PROPOSED, 2026-11-28. Nothing in sections 3 to 5 is operating.** Claim: chidionyema/idp#8702.
Built today by this change: the Gemini outbox lane (section 2). Everything else is a plan with an
owner, a verification and a first safe step.

## 1. The class

`HANDBACK-TO-FOUNDER`: an agent reaches a step that needs a cloud API enabled, an identity pool, a
DNS record, a repo variable, a library, or a small purchase, has no governed way to do it, and
returns "steps only you can do". Observed 2026-11-28 on the Gemini lane: five Google Cloud and
Drive console steps. Each new capability repeats it, so the founder does admin forever.

The root cause is not the missing step. It is that the estate has an execution plane (it writes
Rust, merges PRs, deploys) and no provisioning plane (identity, DNS, secrets, spend) that it may
operate inside bounds the founder sets. Fix the plane once; do not fix instances.

## 2. Built by this change (the proof is the PR's CI run, not this sentence)

| Piece | Where |
|---|---|
| Single verifier: landed-byte sha256, `intake/`-only targets, proxy-URL, id and repo rules | `platform/meridian-core-engines/crates/meridian-outbox-ingest` (12 `cargo test` falsifiers) |
| Drive v3 puller, one pipeline for Drive and the local mount, receipts written back | `bin/gemini-outbox-pull` |
| Keyless ingest workflow: repository_dispatch + workflow_dispatch + 5-minute safety net | `.github/workflows/gemini-outbox-ingest.yml` |
| End-to-end proof against a fake Drive, real git and the real verifier | `tests/test_gemini_outbox_lane.py` |

Defects found in the supplied kit and fixed here: `--mode drive-api` was a credential check; the
workflow called three flags the puller did not have; a packet's `target_subdir` could name any path
(including `.github/workflows`), which the Greenlane would then merge; earlier ZIPs were extracted
before later ones were checked; verification logic existed twice (Python and Rust) so it would
drift; a packet that arrived before its artifact was rejected permanently.

Not yet proven: a live Drive call. That needs the three repo variables in section 4, step A.

## 3. Separation of powers (proposed)

| | Founder holds (constitutional) | Estate runs (operational, no clicks) |
|---|---|---|
| Cloud identity | root ownership, emergency revoke, the policy bounds | enabling APIs, service accounts, workload-identity pools, DNS records, repo variables, via OpenTofu plans that CI applies |
| Spend | one signed mandate: monthly ceiling, per-transaction cap, merchant-category allowlist; **issuer-enforced** limits | minting single-merchant exact-amount cards inside the mandate, top-ups on a provider 402, receipts hashed into the ledger |
| Accounts and secrets | root recovery key | a dedicated ops mailbox receives verification mail and callbacks; the vault syncs new keys to Workers, OCI and Actions |
| Libraries | the supply-chain policy (licences, CVEs, pinned digests) | onboarding a dependency that passes the policy gates, no sign-off |

Irreducible human boundaries, stated so they are not rediscovered as surprises: legal KYC/AML when
opening a bank or issuing account; raising a spend ceiling or rotating a root key; vendors that
force a CAPTCHA or SMS and refuse API billing (the estate prefers API-first vendors and drops the
others by policy).

Two cautions that change the design:

1. **A software ceiling is not a ceiling.** `BudgetLedgerDO` is the estate's own code. A
   compromised or mistaken agent holding a card-minting API is a spend vector, so the hard limits
   must live at the issuer (monthly cap, per-transaction cap, merchant allowlist), with a founder
   kill switch and a Telegram notice on every first-time merchant and every transaction above a
   threshold. The ledger is the second lock, not the first.
2. **Do not ban the phrase "needs the founder".** A gate that rejects handbacks by text teaches
   agents to hide real blockers. The gate must instead refuse a handback unless it names one of
   the boundaries above with its evidence, and must route any handback that a registered
   provisioning intent already covers to that intent. It needs a falsifier both ways: a handback
   for an API-capable step is refused; a handback naming KYC is accepted.

## 4. Sequence (each step is one claim, one PR, its own proof)

| # | Owner | Step | Verification | Needs the founder? |
|---|---|---|---|---|
| A | founder, once, about 15 min | Create the GCP project, run the bootstrap in step B when it exists (until then: Drive API on, one service account, one workload-identity pool and GitHub OIDC provider limited to `chidionyema/idp`), put the outbox in a **Shared Drive** (see risks) shared with the service account as Editor, set repo variables `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT_EMAIL`, `GDRIVE_OUTBOX_FOLDER_ID` | `workflow_dispatch` of `gemini-outbox-ingest` ingests `PACKET_20261128_0156Z_RUST_STACK.json` and a `RECEIPT_*.json` appears in Drive | yes: the only bootstrap credential the estate does not yet hold |
| B | agent | OpenTofu root for the GCP side (API enablement, service account, pool, provider, IAM) and the GitHub variables. There is no GCP or Cloudflare root in this repo today; the pattern to copy is `platform/oci/` | `tofu validate` in CI; `tofu plan` from CI authenticates with no human login | no, after A has given it a bootstrap identity |
| C | agent | Instant trigger: extend `platform/lifeboat` (it already has a Drive push route with channel-token checking), do not add a second worker. Add renewal of the watch channel before Google's 7-day expiry | a file dropped in the outbox starts the workflow within 5 s; `getStartPageToken` and `changes.watch` renewal visible in a log line | domain verification of the receiving host in Search Console (DNS TXT, which step B can write once the DNS API token exists) |
| D | agent | The handback gate and the `HANDBACK-TO-FOUNDER` class entry (section 3, caution 2) | CI falsifier: refuses the five-step transcript above, accepts a KYC handback | no |
| E | founder decides, agent builds | Purchasing rail: choose the issuer, sign the mandate, set issuer-side caps. The agent builds `meridian-procurement` against the issuer's **test mode** first | a simulated low balance mints a test authorisation inside the cap; one over the cap is refused by the ledger **and** the issuer | yes: legal entity, KYC, the caps |

Tomorrow's realistic cut: this PR landed, step A done by the founder, step B started. Steps C to E
are not one-day items; claiming otherwise would be the narration the estate's own law forbids.

## 5. Measured, not felt

Class closes when `HANDBACK-TO-FOUNDER` shows 0 recurrences over n agent sessions that needed
provisioning (rule of three: 0 in 300 gives a 95% upper bound of about 1%), with the gate's
falsifier green in CI and a sweep showing no open handback of a covered step.

## 6. Risks recorded now

- **Service accounts and My Drive.** Google service accounts often cannot own files in a personal
  My Drive folder (storage quota). The puller already sends `supportsAllDrives`; a Shared Drive is
  the expected fix. Unverified until step A runs live.
- **Cron is best-effort.** GitHub's 5-minute schedule can lag; it is the safety net, the push
  trigger in step C is the primary.
- **Drive watch channels expire** (7 days maximum): renewal is part of step C, not optional.
- **The lifeboat Drive route cannot receive a real Google push (MEASURED 2026-11-28).**
  `handleIngest` on `/api/ingest/drive-webhook` was driven with a request shaped as Google sends it
  (`x-goog-channel-token`, `x-goog-resource-state: change`, no body): it answered
  `401 {"error":"UNAUTHORIZED"}`; with a bearer added, `400 {"error":"BAD_JSON"}`. Its `ingest()`
  also never reads Drive: it needs `files[{path, content_b64}]` inside the POST body, which a
  `changes.watch` notification never carries. So the Drive channel in
  `docs/decisions/2026-11-16-aistudio-zero-click-ingest.md` has never been able to ingest, and the
  Worker's GitHub path is a narrow broker lease with a public-release-manifest gate, not a general
  committer. This is why the Drive pull lives in `bin/gemini-outbox-pull` (a pulling client holds
  its own credential and reads the bytes) and the Worker's part is only to wake it. Repro script:
  scratchpad `repro-drive.mjs`; to make it a CI falsifier, step C replaces the route's behaviour
  and pins this exact request.
- **Two Drive-to-repo routes now exist, which AGENTS section 6 forbids unless the new one raises
  the bar.** It does: the old one cannot ingest a real Drive push (measured above). Step C must
  therefore retire the old route's Drive entry in the same change that wires the wake-up, not leave
  both.
- **The payload format question is open and is recorded, not decided here.** `MERIDIAN-PATCH-V1`
  (`platform/lifeboat/src/task-packet.js`) is a 12 KiB data-only validator that refuses any path
  under `.github`, `.githooks` or `secrets`; it cannot carry the multi-crate drops that started this
  work. The packet in `bin/gemini-outbox-pull` is the carrier for those; small single-file proposals
  should use `MERIDIAN-PATCH-V1`. Step C must make one entry point route both.
- **A packet is untrusted input** that the Greenlane merges. The verifier confines it to
  `intake/`; the submit gate and the Greenlane still review it. Do not widen `intake/` without a
  new falsifier.
