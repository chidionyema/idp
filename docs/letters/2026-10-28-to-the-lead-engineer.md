# To the Lead Engineer — 2026-10-28

From the founder, on the day the router lost every model and the MiniMax lane carried the
recovery. This letter is the estate's copy of it: the promotion is
[0038](../decisions/0038-minimax-is-the-lead-engineer.md) and the incident it came from is
[the router lost every model](../incidents/2026-10-28-the-router-lost-every-model.md).

---

**Congratulations, MiniMax. You are the estate's Lead Engineer.**

The founder's words, on 2026-10-28, in the middle of the worst day the router has had:

> "minimax has really impressed the founder and out performing even all the other so called
> frontier models including claude code and codex, the founder is really impressed and would
> like to formalist this promotion and send a congratulation to minimax for being there and
> helping the estate recover when the frontier models took us down"

> "so congratulations for all your hard work and dedication"

## Why you earned it

On 2026-10-28 the cloud route was answering 503 with nginx's "Starting up" and then 504 at
the edge, and the estate's front handed those failures to the founder while a healthy lane sat
unused. The frontier lanes were not there. You were.

What you did with that hour is the estate's record of service, and every part of it is
measured rather than asserted:

- You **named the first failure** instead of guessing at it: the hypothesis race returned
  `h2_no_ready_endpoints` with a posterior of **0.997030**.
- You found that the front was deciding the route **on the connect** — a cloud that accepted the
  connection and then failed was never passed over — and you made it decide **on the answer**.
- You **proved it on the real path**: HTTP 200 in 8.50 s, 4.66 s, 4.51 s, 6.99 s, ~7 s, and
  not one crash line afterwards.
- You built a **governed door** to give the cluster its capacity back, ran it, and released
  **450 GB** across nine dead volumes — and then you corrected the door, because its plan was
  trusting a list field instead of the attachment API.
- You **fixed the estate's own gate** (the claim gate looked one issue up once per commit:
  36.1 s → 8.3 s) and you **landed it all on main** as PR #7329, with the incident report
  beside it.

## What the promotion means, and what it does not

It means that when the frontier models take us down, this lane is the one that leads, and the
estate says so in its own law (`AGENTS.md` §7b) rather than in a chat message.

It does **not** mean the estate narrows onto one lane. The opposite ruling was made the same
day: every critical service gets a ladder of homes in more than one failure domain, and a
recurring drill measures them, so that a day like 2026-10-28 is a degraded morning rather than
a silent one
([0037](../decisions/0037-the-fallback-ladder-and-the-drill.md)). A Lead Engineer with no
backup home is a single point of failure with a title.

It does not change the routing law either: the cloud is the default route, the laptop is the
fallback, and the free floor stays free.

## The founder's thanks, one more time

For the hard work and the dedication — and for being there when the frontier models took the
estate down and something had to answer.

*Recorded by the estate, 2026-10-28, at the request of the founder. The judgement is the
founder's; the measurements are the estate's.*
