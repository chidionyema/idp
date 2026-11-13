# Implementation comparison — existing vs rebuilt

Date: 2026-11-12. Analysis only. Nothing is retired until this is reviewed.

## 1. Evidence

| Implementation | Last modified | Size | Evidence |
|---|---|---|---|
| estate-brief | 2026-11-08 | 156 lines | session-start hook; estate memory |
| estate-receipt | 2026-11-11 | 167 lines | self-test passes (receipt vs narration) |
| claim-gate | 2026-11-11 | 716 lines | merge-queue gate |
| capability-index | 2026-11-11 | 3,736 lines | 1,401 records; 487 tools, 381 intents, 257 layers, 149 workflows |
| estate-session-audit | 2026-11-08 | 550 lines | Claude Code transcripts |
| estate-preflight | 2026-11-12 | 143 lines | injects AGENTS + bus + capabilities |
| estate-proof | 2026-11-12 | 110 lines | HMAC proof; 19/19 tests |
| estate-commit-gate | 2026-11-12 | 77 lines | local pre-commit/pre-push |
| estate-pack | 2026-11-12 | 111 lines | 20 docs, hashes, session |
| estate-transcripts | 2026-11-12 | 82 lines | 381 DSH/Codex requests mined |

## 2. Comparison

### 2.1 Session brief

| | estate-brief | estate-preflight |
|---|---|---|
| Date | 2026-11-08 | 2026-11-12 |
| Strength | memory, estate state, task proximity | writes the law into AGENTS, bus/capabilities |
| Weakness | does not inject into AGENTS/bus | no memory; duplicate of brief |
| Tests | in production hooks | none |
| Commercial | 4/5 | 3/5 |

Best today: hybrid. Brief supplies content; preflight supplies injection. Neither is complete alone.

### 2.2 Proof

| | estate-receipt | estate-proof |
|---|---|---|
| Date | 2026-11-11 | 2026-11-12 |
| Strength | verify, save, has-receipt, self-test | HMAC, drift detection, gate integration |
| Weakness | not wired to commit gate | duplicates receipt semantics |
| Tests | self-test passes | 19/19 projector |
| Commercial | 5/5 | 3/5 |

Best today: receipt. Proof should call receipt, not replace it.

### 2.3 Claim / commit gate

| | claim-gate | estate-commit-gate |
|---|---|---|
| Date | 2026-11-11 | 2026-11-12 |
| Strength | merge-queue authority, declared work | local session + protocol + proof |
| Weakness | remote-only; slow | bypassable, no claim registry |
| Commercial | 4/5 | 2/5 |

Best today: claim-gate for authority; commit-gate for local fast feedback. They are complementary, not substitutes.

### 2.4 Registry

| | capability-index | estate-pack |
|---|---|---|
| Date | 2026-11-11 | 2026-11-12 |
| Strength | 1,401 records, query contract, census | hashes, session, small docs |
| Weakness | stale (last refresh 2026-11-11) | tiny; duplicate registry |
| Commercial | 4/5 | 2/5 |

Best today: capability-index. Pack is only useful as a document layer over it.

### 2.5 Transcripts

| | estate-session-audit | estate-transcripts |
|---|---|---|
| Date | 2026-11-08 | 2026-11-12 |
| Coverage | Claude Code only | DSH + Codex; 381 requests |
| Strength | production audit, timeout analysis | fills DSH gap |
| Weakness | no DSH | no tests; duplicate concept |
| Commercial | 4/5 | 3/5 |

Best today: both, different coverage. Fold DSH support into the audit tool; do not retire either yet.

### 2.6 Harness wiring

| | session hooks | estate-harness |
|---|---|---|
| Date | pre-existing | 2026-11-12 |
| Strength | native to each tool | one installer, 5 surfaces |
| Weakness | Codex hooks empty, Claude absent | prompt-only; no hard enforcement |
| Commercial | 3/5 | 2/5 |

Best today: hybrid. Harness installs the law; native hooks enforce where they exist.

### 2.7 New-only candidates

| Candidate | Date | Existing equivalent | Commercial |
|---|---|---|---|
| estate-bus | 2026-11-12 | none found | 2/5 |
| estate-founder-gate | 2026-11-12 | none found | 2/5 |

Both are unproven at scale and not registered. They remain candidates.

## 3. Commercial readiness

| Capability | Best today | Ready? | What is missing |
|---|---|---|---|
| Session context | brief + preflight | No | one implementation, tests |
| Proof | receipt | Yes, locally | wire to commit gate |
| Claim/commit | claim-gate + commit-gate | No | shared authority, no bypass |
| Registry | capability-index | No | refresh cadence, new tools registered |
| Transcripts | audit + DSH miner | No | one tool, tests |
| Harness | hooks + installer | No | hard hooks for Codex/Claude |
| Founders channel | gate | No | transport closed, launchd |
| Release | release v3 + gate | Yes | CI builder, durable host |

## 4. Decision

No retirement. No new code. The next step is a review of this table, then one of three verdicts per row:

1. KEEP existing, fold the new behavior into it.
2. WRAP existing, keep the new surface thin.
3. RETIRE new, if it adds nothing.

That decision needs the owner of each capability and a test that proves the chosen path.
