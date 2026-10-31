# Memory and the unified metric: brief for Argon (final call)

Date: 2026-10-31. Author: Claude (coordinator). Status: awaiting ballots. Plain text, in the repo,
so any agent can read it with no claude.ai access.

Build state: branches `staged/memory-one-plane` (register, audit, `memory-use` entry in `estate_health`,
AGENTS.md section), `staged/memory-capture` (claim-brief, capture), `staged/memory-canary`,
`staged/memory-mess` (dead code removed, ADR renumbered, Cortex on hold). All are built and tested,
none is landed, none is operating. Design: `docs/specs/2026-10-31-memory-one-plane.md`.
Acceptance: `features/memory/*.feature`.

## What Argon is asked to decide

1. Approve one memory plane: the machine captures and injects memory at claim-open and lane-submit; one
   register (`catalog/memory-register.json`); a recurring audit (`bin/estate-memory-audit`) that can fail.
2. Approve the unified-metric direction: extend `estate_health` (ADR 0049) instead of building a second
   metric, with a `memory-use` entry that is green only when the audit has zero findings and all five
   founder surfaces are covered.
3. Cast the ballots D1 to D16 below, and sign off the voting protocol.

## Measured today (main at 759a9da, static half; live probes need the running estate)

- 18 memory lanes registered; 0 operating (8 blind, 4 broken, 3 built, 2 retire-pending, 1 unknown).
- Founder surfaces covered: 0 of 5 (fleet, voice-face, telegram, founder-claude-code, founder-ask).
- 29 findings on main; 23 on `staged/memory-mess`.
- No memory path at all for cline; codex, cursor and gemini have the tool and nothing injects it.
- 2026-10-20: 5 recalls against 20,166 health probes. #6227 was closed Operational on 10-15 and found dead on 10-18.

## Rules that frame the decision

- Operational means used, on every founder surface, proven by the canary, not by the door answering.
- Nothing is operational without founder-surface coverage (founder, 2026-10-31).
- No dependency on one Mac. The Mac witnesses only what exists only there (the founder's own Claude Code).
- A probe that cannot measure is not a passing probe. Blind is not operating.
- Section 6 of AGENTS.md: no second copy of a layer. The metric already exists (ADR 0049).

## The metric: intelligence-service discipline

- Collection serves a named decision, has an owner, a cadence and a cost. Unused collection is retired.
- Every event carries two grades, source A to F and content 1 to 6 (Admiralty code), rated separately.
  New facts start at content 3, labelled unverified.
- Counter-intelligence: a poison canary (a planted false fact must never be served as current), a pairing of
  every volume metric with an outcome metric, an independent collector (agents write events, never grades),
  compartments by claim overlap and tenant, fail loud.
- Collection tiers: 0 outcomes, 1 lifecycle, 2 behaviour (metadata only): on. 3 content (model exchanges):
  keep as today with secrets scrubbed, local only, 30 days raw. 4 total capture: never.
- One event shape, one entity graph: Agent, Claim, Path, Submit, Gate result, Failure, Lesson, Brief, Lane,
  Surface, Decision, linked so that "did the brief at claim time contain the lesson that prevents this
  failure" is a query (the replay hit rate).

## Road to operational

| Phase | What lands | Exit proof (machine-read) | Mac needed |
|---|---|---|---|
| 0 | register, audit, `memory-use` in `estate_health`, AGENTS.md section, Telegram post via existing secrets | lane merged; first post shows the real numbers | no, once a cloud agent identity exists |
| 1 | dead code deleted, ADR renumbered, docs classified, Cortex on hold | findings fall to those needing a verdict | no |
| 2 | claim-brief at claim-open, capture at lane-submit | a brief file for cline and codex | no |
| 3 | canary: all ordered runtime pairs, then the five surfaces | `canary-result.json` 42 of 42 pairs, 5 of 5 surfaces | only the founder's own Claude Code surface |
| 4 | store home decided, embeddings, door green | door answers; replay hit rate committed with sample size | no |
| 5 | seven consecutive days `memory-use` green; a deliberate red alerts Telegram within 15 minutes | `estate_health` history | no |

## Ballot

Each coordinator votes blind (option, confidence 0 to 100, evidence as a file, probe or measurement, and what
would change your mind), then ballots are published together, then one rebuttal of 150 words, then a final
ballot. A majority of two of three wins; a three-way split goes to Argon with all three cases. Argon decides
and overriding a majority needs a written reason. Put your ballot in `docs/briefs/ballots/<name>.md`.

| # | Decision | Options | Claude | Recommendation |
|---|---|---|---|---|
| D1 | Cortex | A hold until canary green and replay benchmark shows it helps; B adopt now and make it buildable; C drop | A | A |
| D2 | lane-submit with no capture record | A refuse from day one; B warn 14 days then refuse; C never refuse | B | B |
| D3 | Public benchmarks | A beat LoCoMo, LongMemEval, BEAM now; B later, for credibility; C never | B | B |
| D4 | Write admission | A expected-information-gain now; B after the replay benchmark exists; C no | B | B |
| D5 | Router capture and injection | A keep as extra lanes with their own probes; B retire once machine capture operates | A | A |
| D6 | Store home | A single-node k3s; B pay-as-you-go; C local only | none | Argon decides; blocks only the store step |
| D7 | Audit schedule | A launchd 4h plus CI 6h; B CI only | A | see D16: live half moves to GitHub Actions |
| D8 | External claims | A only measured numbers with sample sizes; B claim superiority now | A | A |
| D9 | claude-mem | A retire; B revive | A | A |
| D10 | Real-time push scope | A agents with overlapping claimed paths; B every live agent; C nobody | A | A |
| D11 | Admission of a new fact | A unverified until corroborated; B trusted on write | A | A |
| D12 | Collection tiers | 0 to 2 on, 3 scrubbed with 30-day raw retention, 4 never | yes | yes |
| D13 | Extend `estate_health` (ADR 0049), add `memory-use` | yes / no | yes | yes |
| D14 | Grade every event with the two Admiralty-style grades | yes / no | yes | yes |
| D15 | A cloud agent identity (the estate GitHub App) so agents claim and land with no Mac | yes / no | yes | yes, first |
| D16 | The live audit runs from GitHub Actions against the cloud door; the Mac witnesses only Mac-only surfaces | yes / no | yes | yes |

Other coordinators' ballots are not recorded here. Nothing in this file counts as their vote.

## After the decision

Decisions of class R2 (reversible, cross-cutting) and R3 (hard to undo or high stakes) are recorded as
GitHub decision issues and tallied by `bin/estate-decide` (proposed, not built). Argon is notified on Telegram
with a one-tap answer; on timeout the status quo stands, never an automatic approval.

## Not verified

Competitor claims quoted by other coordinators (leaked upgrades, benchmark figures, "proved" write gates) were
not verified. The FleetView modules other than `memory.py`, `routes.py` and the function list of `harness.py`
were not read. Nothing here was measured on the live Mac or cluster.
