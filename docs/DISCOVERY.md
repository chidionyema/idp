# Discovery — what already exists, what was rebuilt, and the no-new-code rule

Status: freeze. This document is the inventory and the justification gate. It is not code.

## 1. Evidence

| Measure | Value |
|---|---:|
| idp tools | 507 |
| ~/.estate/bin tools | 131 |
| launchd estate jobs | 31 |
| capability registry rows | 1,493 |
| registry last refreshed | 2026-11-11 13:03 |

Canonical tools that already existed before this session:

| Capability | Existing tool | Purpose |
|---|---|---|
| Session brief | idp/bin/estate-brief | what a session should know before it starts |
| Proof receipt | idp/bin/estate-receipt | machine-generated proof for every report |
| Claim / duplication | idp/bin/claim-gate | refuse a change nobody declared |
| Capability registry | idp/bin/capability-index | one store, one contract, one gate |
| Claude transcript audit | idp/bin/estate-session-audit | what happened in Claude Code sessions |
| Lane receipts | idp/bin/idp-lane-receipts | lane delivery evidence |
| Greenlane | idp/bin/idp-greenlane | the only writer of main |

## 2. What was rebuilt instead

| New (this session) | Existing equivalent | Verdict |
|---|---|---|
| estate-preflight | estate-brief | duplicate; should wrap brief |
| estate-proof | estate-receipt | duplicate; should wrap receipt |
| estate-commit-gate | claim-gate + hooks | duplicate concept |
| estate-pack | capability-index | duplicate registry |
| estate-transcripts | estate-session-audit | duplicate for Claude; DSH gap is real |
| estate-standard | existing gates | duplicate scoring |
| estate-harness | session-start hooks | duplicate wiring |
| estate-bus / founder-gate | no direct equivalent | genuinely new |

The first seven are the failure. The last two may be justified, but only after the registry is queried.

## 3. Root causes

R1. No pre-code inventory check. Agents write before querying capability-index.
R2. The registry is stale: last refreshed 2026-11-11, 1,493 rows, no cadence.
R3. 507 tools with overlapping names; no single ownership map.
R4. Harnesses are wired differently: Codex hooks empty, Claude hooks absent, OpenCode plugin API, DSH AGENTS.
R5. No duplicate detection in the gate; a new file passes even when the capability exists.
R6. Transcript mining existed for Claude only; DSH sessions were not mined.
R7. Policy permitted new code without a justification record.

## 4. Gaps in the existing process (fix these, do not rebuild)

1. Refresh the registry on a schedule and before any build: capability-index census.
2. Add a pre-code check: query capability-index, estate-brief, and duplicate search.
3. Add duplicate detection to claim-gate / commit gate: same behavior under a new name is refused.
4. Unify session-start hooks across DSH, Codex, Claude, Pi, OpenCode using estate-brief.
5. Extend estate-session-audit to DSH transcripts instead of a second miner.
6. Record every new tool in the registry or retire it.

## 5. Policy — no new code without justification

Before any new file, function, or tool, produce a justification record with:

1. capability-index query output showing no existing capability.
2. estate-brief --task <task> excerpt.
3. Duplicate search: name and behavior matches, with paths.
4. Why config, test, documentation, consolidation, or wrapping cannot solve it.
5. Owner, rollback, and the test that will fail if it regresses.

No record, no code. "New code" is a red flag, not progress.

## 6. Focus from now

QA, integration, automated tests, review, consolidation, strengthening the platform.
Not new features. Not new scripts.

Existing suites to run before claiming anything:

    idp/bin/claim-gate
    idp/bin/idp-greenlane status
    idp/bin/capability-index status
    idp/bin/estate-receipt --self-test
    idp/bin/estate-session-audit
    tests/ and platform tests under idp

## 7. Immediate freeze actions

1. No new code.
2. capability-index census to refresh the 1,493 rows.
3. For each new tool from this session: wrap the existing tool or retire it.
4. Add the no-new-code rule to AGENTS.md.
5. Use estate-session-audit for transcripts; fold the DSH miner into it rather than run two.

## 8. What is genuinely new and still needs justification

- estate-bus: shared state over one URL.
- estate-founder-gate: fail-closed founder channel.
- DSH transcript coverage: a gap in estate-session-audit.

These are candidates, not approved. They must be registered and reviewed like everything else.
