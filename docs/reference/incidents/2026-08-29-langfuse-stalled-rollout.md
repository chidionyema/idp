# Incident report: Langfuse sign-in red for 16 hours after an unmeasured CPU cut

Date: 2026-08-29. Author session: a7b41022. Founder words that opened this report, 18:10Z–18:20Z:
"I need trace and audit", "no one is addressing root cause", "we patching like donkey",
"this will happen again, if not the same container then another one", "capacity planning
formalised now", "the only way to fix this is to fix our ways of working, and we need our laws
back", "just admit we are a shambles". This document is the admission, with the data.

Every number below was read from git, GitHub or the cluster runs in the same hour it was written,
and the command that produced it is beside it. Nothing here is from memory.

## What the founder saw

Langfuse (`langfuse.<zone>`) bounced back to its own sign-in page with `error=OAuthCallback`
after the SSO click, from 2026-08-29 morning until at least 18:03Z. Every other door was green.
He read the same error all day while three pull requests claimed to fix it.

## Timeline (UTC)

| When | What | Who | Receipt |
|---|---|---|---|
| 08-28 05:52 | Langfuse web and worker set to 500m, Guaranteed (crew#539 CP9) | session d5ae1960, idp#539 | `git log -L53,53:platform/observability/langfuse-values.yaml` → abdcced8 |
| 08-29 02:50 | Commit 2b250895: "CPU requests 7.64 → 3.54 cores"; 19 files; Langfuse web and worker cut 500m → **50m** under "zealot rule 1: micro CPU request, burst limit". No boot measurement for any of the 19. | session 41fd24d8 | `git show 2b250895 -- platform \| grep '^+.*cpu: 50m'` → 20 lines |
| 08-29 05:52 | idp#687 merged with that commit. Every gate green. | session 41fd24d8 | `gh api repos/chidionyema/idp/commits/2b250895/pulls` |
| 08-29 06:11 | Flux reports the cluster is not running what main says; the bot opens idp#727. From here the issue collects **88 comments**, one per failed reconcile. Nobody reads it. | flux-events bot | `gh issue view 727` |
| 08-29 ~06:00–15:00 | Langfuse web killed by liveness 164 times, worker 163 times, in 9 hours. The 15-hour-old pod keeps serving with the old sign-in env. | — | run 33259031857 (quoted in `langfuse-values.yaml:42`) |
| 08-29 14:23 | login-drill goes red on the Langfuse door and stays red for 26 consecutive runs to 18:03. | — | `gh run list -w login-drill.yml -L40` |
| 08-29 15:25 → 18:14 | flux-events fails **295 times** (70 in the 15:00 hour, 111 in 16:00, 80 in 17:00). | — | `gh run list -w flux-events -L1000 --created ">24h"` |
| 08-29 15:35 | idp#820 "web and worker boot again": 50m → 250m. Still crash-loops. | session 41fd24d8 | run 33262424618 |
| 08-29 17:09 | idp#835: 250m → 1000m, Guaranteed, capacity label. | session 41fd24d8 | `gh pr view 835` |
| 08-29 17:5x | helm-retry 33266882531 dispatched to roll the new pods; still running at 18:20. | session a7b41022 | `gh run view 33266882531` |
| 08-29 18:03 | login-drill 33267215252: Langfuse still `OAuthCallback` (old pod serving). | — | run log |

State at 18:20Z: 6 things failing, 1 blind. login-drill, verdict-langfuse, flux-events (one cause:
the stalled rollout); idp#854, #838, #797 red on their own gates; `bin/idp-cluster-state` BLIND
from a laptop. Over the last 24 hours: idp 75 failed runs of 300 sampled, crew 36 of 300.

## Root cause

**A CPU request was set by a rule, not by a measurement, and nothing in the estate could tell
the difference.** 2b250895 cut 19 workloads to 50m in one pass. For Langfuse's Next.js server,
5% of a core cannot bind a port inside the 50-second liveness window, so every new pod was
killed before it was Ready, and Kubernetes did what it is built to do: it kept the old pod
serving. The sign-in fix (idp#810) therefore never reached a pod that answered a request.

Three more things had to be true for this to last 16 hours, and all three were:

1. **The capacity fence looks one way.** `platform/edge/capacity-policy.yaml` refuses a request
   *over* 250m without a measured label (crew#539's fat-request incident). Nothing refuses a
   request *under* the floor a workload needs to boot. `tests/test_incident_crew584_capacity_requests_need_proof.py:150`
   ("the platform asks for less CPU than the budget") rewarded the cut.
2. **A stalled rollout is a ledger entry, not an alert.** Flux said so from 06:11Z: idp#727 got
   88 bot comments and flux-events failed 295 times. Not one of those runs or comments was read
   by a person or a session until the founder complained. The comment in
   `platform/backstage/overlays/oke/kustomization.yaml` from 2026-08-28 (crew#307) reads
   "Flux said so every ten minutes and nothing read it" — the same sentence, one day earlier,
   for the catalogue. The guard written then was a surge setting, not a page.
3. **The laws' own self-checks are not in front of any session.** The file every session loads
   (`~/.claude/AGENTS.md` → `scripts/laws/AGENTS.md`) is 2,802 words and contains **0** of the
   50 "You are breaking it when" checks. Those live in `AGENTS-FULL.md` (26,216 words), which
   is read by three scripts and loaded into no session. The check for this exact mistake is one
   of the 50: *"a number in your plan came from what sounded tidy instead of from the
   instrument."*

## Laws broken, by whom

| Law | Broken by | How |
|---|---|---|
| LAW 2 proof before action; hard rule 2 no speculative numbers | idp#687 (41fd24d8) | 50m chosen by rule; no boot measurement for any of 19 workloads |
| LAW 3 never the same mistake twice | idp#687, and the estate | the stalled-rollout-old-pod-serving pattern was written up on 08-28 (crew#307); the guard pinned the surge setting, not the class |
| LAW 6 / LAW 29 root cause, attribute before repair | idp#820, idp#835 (41fd24d8); session a7b41022 in chat at 18:09Z | two more numbers tried on the same container; a7b41022 explained the Kubernetes mechanism and got the direction of #835 wrong |
| LAW 28 an instrument nobody reads is not an instrument | the estate | idp#727: 88 comments unread; flux-events: 295 red runs unread |
| LAW 44 a law without a protocol is a wish | the estate | LAW 2 had no protocol for "a request went down"; the gates read the PR's words |
| LAW 45 the class, over every instance | crew#539 and crew#307 closures | each pinned its instance |

## Why the gates said green

The pull-request gates (`operating-model-gate`, `dod`, `pr-evidence`, `python-strict`) check that
the words are there: an `Optimised:` line, a `Drill:` name, four LAW lines, ten DoD rows, a budget
under a ceiling. idp#687 had every word. No gate asks where a number came from.

## The class fix (what changes so this cannot happen on another container)

Tracked as crew#645, "Capacity planning formalised". The four parts, each a gate or a page, none
a paragraph:

1. **Numbers come from the instrument.** Prometheus already runs (`platform/monitoring/kube-prometheus-stack.yaml`).
   KRR (robusta-dev/krr, v1.30.0, released 2026-08-24) reads it and writes a request/limit
   recommendation per container. That output is the capacity register, generated, committed by a
   bot PR the way image tags are (`platform/image-automation/`). No session types a request.
2. **The fence looks both ways.** A request below the register's measured boot floor, or a
   request that changed with no register row, is refused at admission (Kyverno) and in CI.
3. **A stalled rollout pages.** A Flux Kustomization or HelmRelease not Ready for ten minutes is
   an Alertmanager alert to the founder's alert route, not a comment on an issue. flux-events
   posts once per state change, not once per reconcile.
4. **The laws' self-checks are loaded.** The 50 "You are breaking it when" checks go back into
   the file every session reads, and a test pins the count.

Until 1–3 land, every request in git that was cut by 2b250895 is a candidate for the same
failure. The 19 files are the sweep list.

## Corrections to what was said in chat

- a7b41022 at 18:09Z said idp#835 "lowered the request so the new pod can be placed". It raised
  it to 1000m. Corrected at 18:14Z.
- a7b41022 at 18:19Z said flux-events "failed 62 times ... all night". The window was capped at
  300 runs; the real count is 295 failures since 15:25Z, and idp#727 carries the earlier
  evidence from 06:11Z.

## Addendum, 19:4xZ: the blocker is hindsight, not Langfuse

Founder, 18:3xZ: "why are you content waiting for 27 minutes". The answer was in the instrument
this report already cites and nobody read: every one of the 89 bot comments on idp#727 names
`HelmRelease/hindsight/hindsight status: 'InProgress'`, from 06:26:38Z. Hindsight has been in
CrashLoopBackOff since 2026-08-28 12:46Z (crew#573, open P1): `Last State: Terminated Reason:
Error Exit Code: 137`, `Killing ... Container api failed liveness probe, will be restarted`
(x133 over 13h). Not out of memory: the chart's default liveness probe (delay 30s, period 10s,
3 failures) kills the container at about 60 seconds while it loads its embedding model on a 50m
CPU request (the same 2b250895 cut). No startup probe exists, so a slow start and a hang are the
same thing to the kubelet.

Consequence: every Flux reconcile of the platform tree, and every helm-retry playbook, spends its
full 15-minute timeout on hindsight before it reaches Langfuse. That is the 27 minutes, and the
295 red flux-events runs.

What this session got wrong: it dispatched helm-retry 33266882531 and waited on the run instead of
reading idp#727, which had the answer at 06:26Z. The correction is procedural and lands in
crew#645 CP3 (a stalled rollout pages the author once per state change) and in the operating
rule recorded 18:2xZ: the founder approves every infrastructure change, so the one action
proposed to him is `suspend: true` on the hindsight HelmRelease (one line, one-line undo), with
the startup probe and a measured request tracked on crew#573.

helm-retry 33266882531 ended red at 18:2xZ: `Deployment/observability/langfuse-web status:
'Failed'` even at 1000m. The next login drill (33268386892) then read a different Langfuse
error: `No email found in user object`. The new pod is serving; the identity provider's token
carries no email claim. That is a configuration fix, and under the freeze it waits for the
founder's word.
