# Agent harness assessment, friction register, and MiniMax spec (2026-10-30)

Founder directive: the warship is built and nothing is operational; rank what exists by what RUNS, record every
friction, and hand MiniMax a spec the founder (not infovend) can pass directly. Claimed under #7497.

## 1. Ranking: closest to full operational use (evidence, not line counts)

| Rank | Piece | Evidence 2026-10-30 | Verdict |
|---|---|---|---|
| 1 | NATS JetStream + `estate-fleet` (comms, inbox, atomic ack, voice door) | nats-server pid live on :4222; 8 lanes landed; real-bus tests incl. production ack_wait | OPERATIONAL |
| 2 | FleetView backend (:18790) + `/voice/hear|say` | launchd `ai.estate.fleetview-backend` running, `/healthz` ok, bus reachable | OPERATIONAL, voice loop unproven end to end with real audio |
| 3 | `exec-daemon` | socket listening, ceiling 100s | OPERATIONAL, unused by any dispatcher |
| 4 | LiteLLM `:4001` + `minimax` route | launchd `com.estate.litellm-local-4001` running; settings.json defaultModel minimax_m27 | OPERATIONAL |
| 5 | `idp-linear-dispatch` (issue -> harness run) | runs, `--help` ok; 0 tests, 0 commits in 30d, no launchd job | BUILT, NOT WIRED: **closest gap** |
| 6 | `idp-agent-orchestrator` (provision/submit/poll) | 428 lines, 0 tests, 0 commits in 30d, not scheduled | BUILT, NOT WIRED |
| 7 | `crew-sync-agent`, `idp-agent-event-bus` | 1 test, no recent change | peripheral |

Decision: the nearest full loop is items 1-4 (all live) plus 5-6 (built, unwired). The missing arrow is one daemon
that turns a fleet directive or labelled issue into an orchestrator run executed through exec-daemon on MiniMax,
and reports back through estate-fleet. No new framework is needed.

## 2. Friction register (each found this session, with cause)

| # | Friction | Why discovery still fails | Track |
|---|---|---|---|
| F1 | Read-then-ack replayed voice messages at ack_wait=60 | Tests used ack_wait=1, so the production value was never exercised | FIXED (`inbox --pipe`, test at 60s); standing rule: founder-surface tests run at production timings |
| F2 | Primary checkout is behind origin/main; `bin/idp-estate-db-backup` exits 127 there | Agents run tools from whichever tree they stand in; nothing says the tree is stale | OPEN: bootstrap must warn when HEAD is behind origin/main |
| F3 | No single "who holds what / what is in flight" command; claims only surface via injected memory block | `.claims` dir is empty; claim state lives elsewhere; 67 `lane/*` branches on origin, many dead | OPEN: one `estate-execute where` view: claims + lanes + verdicts |
| F4 | 67 stale lane branches including accidental `lane/--help` | No lane reaper; landed lanes vanish but abandoned ones persist | OPEN |
| F5 | 200+ open issues, no ranking of "unclaimed and highest value" | Triage is by reading; no scored queue | OPEN: scored queue fed to the harness |
| F6 | Lane verdict needs a hand-written `gh api` poll | lane-submit prints the command instead of waiting | OPEN: `lane-submit --wait` |
| F7 | `policy shadow: would hold lane-submit, 513/961 runs not ok` | Advisory only; nobody owns the 53% failure rate | OPEN: root-cause CI failures |
| F8 | Founder voice/comms "works and doesn't work" | No continuous end-to-end probe of the founder surfaces | OPEN: scheduled synthetic probe (below) |

## 3. Spec for MiniMax (founder passes this directly; no infovend step)

Goal: `estate-dispatchd`, a launchd daemon that makes an issue or founder directive start a MiniMax run, unattended.

1. Input: a JetStream fleet message to agent `dispatch` (kind directive) containing an issue number, or `idp-linear-dispatch --json` output.
2. Run: `idp-agent-orchestrator provision|submit|poll` through `exec-daemon`, model `minimax` via LiteLLM :4001. Never `git branch -D`; the orchestrator owns git.
3. Claim: `claim-open` the issue's paths before any edit; abort if `claim-gate` refuses.
4. Report: send progress and the lane verdict back to the originating sender via `estate-fleet send`; speak the result via `estate-fleet-voice` when the directive arrived by voice.
5. Fail loud: unreachable bus, daemon, LiteLLM or FleetView prints `BLIND` and exits 2, never silent success.
6. Acceptance (proof required, in the PR): (a) real-nats-server test drives directive -> orchestrator stub -> reply; (b) test at production ack_wait; (c) launchd plist installed and `launchctl list` shows it; (d) one real labelled issue completed end to end, with the lane verdict quoted; (e) restart the daemon mid-run and show the message is redelivered, not lost.
7. Not in scope: new brokers, new frameworks, tofu/cluster changes (#7387 belongs to pi).

## 4. Founder-surface regression gate (F8)

A scheduled synthetic probe, every 15 min: send a directive founder -> probe agent, read it back via `speak` with a stub player, assert ack, assert `/healthz` bus reachable; any failure raises the freshness alarm used by the backup instrument. Anything below this standard is a tracked claim with proof, per founder directive.
