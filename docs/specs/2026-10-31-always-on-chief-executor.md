# The always-on chief executor (MiniMax M2.7): triage, review, approval, execution

Date: 2026-10-31. Status: proposed; nothing here is built or operating. Author: external contractor.
Founder, 2026-10-31: MiniMax 2.7 is the estate's chief executor, headless, recurring, "always on",
with formal specs and BDD. I could not find an existing spec for that role in this checkout (searched
features/, docs/specs, docs/decisions); if one exists elsewhere this document defers to it and is deleted
in the same change (AGENTS.md section 6). Acceptance: `features/gates/chief-executor.feature`.

## What exists and is reused (read 2026-10-31)

- Lane: `minimax_m27` serves MiniMax-M2.7 (`llm/config.yaml`); pi defaults to it (ADR 2026-10-30
  infrastructure department). ADR 0038 names the MiniMax lane Lead Engineer (a founder judgement).
- Executor: `.github/workflows/agent-sandbox.yml`: runs pi with `SEED_MINIMAX_API_KEY` in a runner with no GitHub
  token, firewall-checks the claims, and a trusted job pushes `lane/agent-pi-<run>` as the estate App with a claim.
- Lander and triage: the Greenlane (`greenlane.yml`, every 15 minutes and on CI completion).
- Queue head: the critical-function incident queue (`estate_health`, ADR 0049; J6).

## What is missing, and the one change for each

| Gap | Change (extends the existing thing) |
|---|---|
| Not always on: agent-sandbox is dispatch-only | A `schedule` trigger on the same workflow, every 15 minutes (placement ladder rung 2, GitHub Actions schedule, ADR 0034; no node, no laptop). "Always on" is the schedule plus the dead-man below, not a process. 24/7 (founder, 2026-10-31) means no gap longer than the 30-minute dead-man bound: GitHub may delay or skip scheduled runs, so a second trigger (a `workflow_run` on the Greenlane's completion) chains the next tick, and a missed schedule is detected, not assumed away. |
| No queue | Task source, in order: (1) the head incident of `estate_health`; (2) open issues carrying the claim label for pi with no live heartbeat. One task per tick, one claim per agent (AGENTS.md section 5). Empty queue: print `idle`, exit 0. |
| `staged/*` has no triage | A promotion step in the trusted job: a `staged/<name>` branch whose head has the commit trailers and whose paths fit a claim is pushed as `lane/<name>`. Otherwise it is left and its reason recorded on the claim issue. |
| No approval gate | Founder-surface or critical-service paths (the forced-review inventory) wait for one founder-door message with a one-tap answer; on timeout the status quo stands, never approval. Everything else lands on green via the Greenlane. Wiring the review gate is its own change with its own receipt (ADR 2026-10-30). |
| Nothing proves it is alive | A dead-man entry in `catalog/critical-functions.json`, `chief-executor`, goal not liveness (J3): green only if the newest scheduled run is under 30 minutes old AND the last 12 ticks produced either `idle` or a lane. Source is the GitHub run history, so it is measurable from the cloud with no Mac. |
| Pinned model | The workflow passes `minimax_m27` explicitly. The run title records harness and model, so Fleet shows which. |

## Who decides what (AGENTS.md section 12)

Which task: machine (queue order). Whether a staged branch is promotable: machine (paths, trailers, claim).
Whether a lane lands: machine (Greenlane). Whether a founder-surface lane lands: judgment, irreducibility
`irreversible` (outward-facing). What the code should be: model (MiniMax), checked by the firewall and CI.

## Honest limits

- Agent-sandbox needs these secrets by name: SEED_MINIMAX_API_KEY, AGENT_TRANSCRIPT_AGE_KEY,
  AGENT_TRANSCRIPT_AGE_RECIPIENT, SEED_GITHUB_APP_ID, SEED_GITHUB_APP_PEM_B64. I did not verify they are set.
- This session has no GitHub credential and no yamllint, so the workflow change is not written or run here.
  Nothing in this document has been dispatched. Proof will be: one scheduled tick that opens a claim and a lane, and the
  Greenlane's verdict on that lane's head.
- M2.7 reads 204,800 tokens (router config); the task packet must fit, which the queue must enforce.

## Spend ceiling (founder, 2026-10-31)

A paid infrastructure lane for redundancy off the Mac is capped at $25 a month in total unless a compelling
reason is written beside the measured cost. One small server (about EUR 5.5 to 6 a month, one third-party
source, not Hetzner's own page) fits with room to spare. Free-tier rungs come first (ADR 0034). The estate
contract of $0 to $150 a month still applies above this.
