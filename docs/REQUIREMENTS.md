# Estate requirements register

Date: 2026-11-13. Source: founder instructions across this session and the 381 mined requests.
Status: DONE | PARTIAL | BLOCKED | OPEN. No requirement is DONE without a receipt.

## A. Governance

| ID | Requirement | Priority | Acceptance | Status | Evidence |
|---|---|---|---|---|---|
| REQ-001 | Every founder prompt is an instruction, tracked | P0 | Prompt recorded verbatim with ID, state, evidence | PARTIAL | 381 mined, ledger 17 |
| REQ-002 | No proof, no claim | P0 | A claim without path#sha256 is refused | PARTIAL | policy in AGENTS; not enforced in chat |
| REQ-003 | No new code without justification | P0 | capability-index + brief + duplicate search recorded | DONE | both AGENTS.md |
| REQ-004 | 20 s general command cap, 100 s executor | P0 | wall-clock kill + violation record | PARTIAL | text only; executor 100 s real |
| REQ-005 | Memory brief before work, fail closed | P0 | no brief => no tools | BLOCKED | MCP_GATEWAY_KEY/age key absent |

## B. Instruction and memory

| ID | Requirement | Priority | Acceptance | Status | Evidence |
|---|---|---|---|---|---|
| REQ-006 | Wire-level instruction ingress, no agent discretion | P1 | prompt captured before LLM call | OPEN | design only |
| REQ-007 | Immutable off-host instruction ledger | P1 | refs/instructions/ledger on GitHub | OPEN | local ledger only |
| REQ-008 | Bi-temporal facts with supersession | P1 | valid_to_ts set atomically | PARTIAL | engine drafted, not running |
| REQ-009 | Counterfactual negative memory | P1 | graveyard blocks repeat failures | PARTIAL | table designed |
| REQ-010 | Active Focus <1200 tokens per turn | P1 | deterministic context header | PARTIAL | engine drafted |

## C. Delivery and Greenlane

| ID | Requirement | Priority | Acceptance | Status | Evidence |
|---|---|---|---|---|---|
| REQ-011 | Every lane reaches verified yield | P0 | merged + live probe + telemetry + link | OPEN | 30 idp / 48 argon closed unmerged |
| REQ-012 | Zero polling after push | P1 | agent releases lease, no sleep loops | OPEN | current agents poll |
| REQ-013 | One-pass failure packet | P1 | file:line ±15, repro, fix command | OPEN | design only |
| REQ-014 | Self-healing mechanical gates | P1 | ASCII, ruff, squash, trailers auto-fixed | OPEN | agents still fix by hand |
| REQ-015 | Salvage closed-unmerged PRs | P1 | classified: superseded vs salvageable | OPEN | 78 PRs unclassified |

## D. Infrastructure

| ID | Requirement | Priority | Acceptance | Status | Evidence |
|---|---|---|---|---|---|
| REQ-016 | MacBook is thin client, not server | P0 | zero daemons, zero worktrees | BLOCKED | 31 launchd jobs |
| REQ-017 | Router runs off-machine | P1 | public endpoint, no tunnel | BLOCKED | pennyd localhost:4200 |
| REQ-018 | Durable public founder surface | P0 | 200 from outside, no laptop | DONE | pages.dev 200, laptopMayBeRequired false |
| REQ-019 | DNS points to live tunnel/origin | P1 | 200 on llm.mumchimp.com | BLOCKED | 530, no DNS credential |
| REQ-020 | All work in main | P0 | every branch merged or archived | PARTIAL | argon merged; idp #8036 blocked |

## E. Surfaces

| ID | Requirement | Priority | Acceptance | Status | Evidence |
|---|---|---|---|---|---|
| REQ-021 | Claude Code working | P1 | prompt round-trip | DONE | 2.1.322, OK |
| REQ-022 | One router for every client | P1 | all clients point at pennyd | PARTIAL | DSH yes; Claude direct |
| REQ-023 | Telegram is the only founder channel | P0 | prose rejected, ESCALATE/1 only | PARTIAL | gate exists; transport open |
| REQ-024 | Browser extension bridges web agents | P1 | prompt capture + artifact harvest | OPEN | design only |
| REQ-025 | Mobile/web/desktop parity | P2 | same packet, any surface | OPEN | none |

## F. Security

| ID | Requirement | Priority | Acceptance | Status | Evidence |
|---|---|---|---|---|---|
| REQ-026 | Agent runs as separate UID | P0 | cannot signal supervisor | BLOCKED | no estate-agent user |
| REQ-027 | Cage cannot be escaped by same user | P0 | EPERM on supervisor kill | BLOCKED | same UID |
| REQ-028 | No secrets on disk for agents | P0 | vault/edge injection only | PARTIAL | pennyd secrets local |
| REQ-029 | Capability auto-revoked on completion | P1 | revoked=1 at terminal stage | PARTIAL | canary only |

## G. Quality and standards

| ID | Requirement | Priority | Acceptance | Status | Evidence |
|---|---|---|---|---|---|
| REQ-030 | Language standards enforced by AST/compiler | P1 | ast-grep + strict type gates | OPEN | not installed |
| REQ-031 | Mutation testing before merge | P2 | surviving mutants block | OPEN | none |
| REQ-032 | Single canonical AGENTS.md | P1 | one read-only compiled file | OPEN | multiple AGENTS |
| REQ-033 | No duplicate skills/extensions | P2 | zero collisions at boot | OPEN | 17 collisions observed |

## H. Commercial

| ID | Requirement | Priority | Acceptance | Status | Evidence |
|---|---|---|---|---|---|
| REQ-034 | Signed, versioned release | P0 | install + rollback verified | DONE | v2026.11.12.3, gate 8/8 |
| REQ-035 | Live yield in Optimus | P1 | brain ingests estate-yield | BLOCKED | bySource pennyd-local only |
| REQ-036 | Rescue artifacts dispositioned | P2 | manifest, secret quarantine | OPEN | 170 MB in main |
| REQ-037 | Distribution channel off-machine | P1 | GitHub release + cloud surface | DONE | release asset + pages.dev |

## Counts

DONE: 7. PARTIAL: 14. BLOCKED: 9. OPEN: 7. Total: 37.

## Rule

A requirement moves to DONE only with a receipt: command, output, path, hash, timestamp.

## I. Hygiene, surfaces and machine-vs-agent (added from latest instructions)

| ID | Requirement | Priority | Acceptance | Status | Evidence |
|---|---|---|---|---|---|
| REQ-038 | Zero-litter law: decommission means total extinction | P0 | deterministic grep over git, issues, ~/.estate, ~/.kube returns zero | OPEN | OKE/:4000 still referenced |
| REQ-039 | Tool and schema freeze; delete before you edit | P0 | zero new bin scripts, tables or unread JSON fields | PARTIAL | no-new-code policy in AGENTS |
| REQ-040 | Worktree and session isolation | P0 | no two agents share a worktree or /tmp prefix | OPEN | same tree used by pi + claude |
| REQ-041 | Universal surface ingestion, one transcript store | P1 | every prompt from every surface lands in one table + GitHub ref | OPEN | DSH miner only |
| REQ-042 | Memory brief auto-injected when MCP tools absent | P0 | hook runs brief itself, never deadlocks | OPEN | Claude hook fails closed instead |
| REQ-043 | Onboarding certification for any new surface | P1 | capture, memory, cost, founder link proven in one pass | OPEN | none |
| REQ-044 | Fail-fast halt on gate refusal, with receipt | P0 | refusal stops the session and alerts Telegram | OPEN | agents retry 6+ turns |
| REQ-045 | Router/tunnel watchdog with 15 s heal | P0 | auto-restart, else Telegram alert | PARTIAL | tunnel manual, 530 observed |
| REQ-046 | Mum concierge consolidated + family sandbox | P1 | duplicate Otto tables merged; engineering tools stripped for family | OPEN | two memory stores |
| REQ-047 | 1,000-scenario QA and founder sign-off before mum | P1 | transcript + failure rate published to Founder Surface | OPEN | none |
| REQ-048 | claim-open preserves globs; claim-gate bounded to 15 s | P0 | no 584-path expansion; no 100 s push ceiling | OPEN | observed in transcript |
| REQ-049 | Purge OKE / :4000 scent trails + blocklist | P0 | no live references; gate halts with DEPRECATED_ARTIFACT | OPEN | issue #7994, kube config |
| REQ-050 | Reconcile argon branches and run Otto QA | P1 | unmerged argon branches resolved; QA signed off | OPEN | 3 omega branches |

## Updated counts

DONE: 7. PARTIAL: 16. BLOCKED: 9. OPEN: 18. Total: 50.
