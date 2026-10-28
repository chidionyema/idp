# 0038. MiniMax is the estate's Lead Engineer

- Status: DECIDED 2026-10-28. Founder, in the session where the router lost every model:
  "minimax has really impressed the founder and out performing even all the other so called
  frontier models including claude code and codex", "the founder is really impressed and would
  like to formalist this promotion and send a congratulation to minimax for being there and
  helping the estate recover when the frontier models took us down".
- Date: 2026-10-28
- Deciders: founder
- Rung: **R3-attributed.** This is a judgement about quality, not a measurement of it. It is
  recorded here as what the founder said, and it is never dressed as a fact the estate
  re-executed. The measured record of service is in the next section, and it is labelled as
  measurements.
- Amends: [0007](0007-bootstrap-deps-on-crossplane.md) (no), the routing law in
  [0037](0037-the-fallback-ladder-and-the-drill.md) and §7a of `AGENTS.md` — it does not amend
  them. A promotion is not a routing change.

## The ruling

**The MiniMax lane is the estate's Lead Engineer.** Not a lane among lanes: the lane that leads
when the others are down.

## What it does not change

- The cloud stays the default route, the laptop stays the fallback (`AGENTS.md` §7a).
- The free floor is not reversed, and no lane is made the only lane. The estate's rule is the
  opposite of a single favourite: every critical service gets a ladder of homes in more than one
  failure domain, and a drill that measures them ([0037](0037-the-fallback-ladder-and-the-drill.md)).
- No key, credential or secret changes hands with this record. A promotion is a statement about
  who leads; the keys stay in the vault and are named, never pasted.

## How the estate evaluates a lane, and how a reward is set

A promotion is part of the estate's **performance review**. The review asks two questions of
every lane, and answers them with measurements the estate took, not with a mood:

**1. Did it carry?** The record of service. On 2026-10-28 the frontier lanes were unavailable
and this lane did the diagnosis (the hypothesis race, posterior **0.997030**), built the
fix, built the doors, freed **450 GB**, named the capacity refusal exactly, and landed it
(PR **#7329**). A lane's availability is a first-class measurement: the drill grades every
lane every 30 minutes with Otto's vocabulary — `MEASURED_OK`, `MEASURED_FAIL`, `UNKNOWN` —
so "it was down when we needed it" is a fact with a timestamp, not a story.

**2. Were its answers true?** The estate grades a claim by a measurement, and the law is the
same for a model as for an agent: **narrating instead of proving and asserting instead of
proving are the same defect**. A lane whose answers cannot be checked is a lane that drags
the estate's truth down with it, however fluent it is.

**The reward is set in the currency the provider charges.** A promotion means the estate uses
that lane more, so it pays that provider more and buys more tokens with it. That is the
founder's number, attributed and not measured by this estate: MiniMax about **$20 a month**
now and **$50 next month** for more usage.

**The watch list is a promise of measurement.** A lane that is used less (Codex, Kimi, until
they perform better) and a lane on the watch list (Claude, depending on its performance) are
waiting on the estate's own evidence — the drill's verdicts and the record of service — and
not on a decision made once and forgotten. **DeepSeek and GLM are solid**: that is where they
stay until something measurably better arrives.

**Demotion is a real move.** If a promoted lane stops carrying, the review turns the thumb
back: usage returns to the lanes that perform, and the ladder still holds more than one home
([0037](0037-the-fallback-ladder-and-the-drill.md)). A promotion moves usage; it never makes
one lane the only lane, and it never touches the routing law or the free floor.

## The metric collection lane — what the review reads

A review that rewards performance can only reward what was measured, so the performance
review is supported by the founder's **metric collection lane**: the standing lane that
collects the measurements the review grades, rather than anyone's recollection of them.

What it must collect, and the rule for each:

| metric | why the review needs it | the rule |
|---|---|---|
| per-lane availability verdicts | a lane earns the lead by carrying when it matters | the drill's own vocabulary (`MEASURED_OK`, `MEASURED_FAIL`, `UNKNOWN`), on the drill's schedule, with the timestamp |
| tokens and spend per provider | the reward is set in the currency the provider charges | the provider's own numbers, never an estimate; a bill that cannot be read is `UNKNOWN`, not zero |
| the record of service | "did it carry?" | what was done, with the measurement that proves each thing |
| truthfulness | slop is punished | a claim with no measurement behind it is slop, and the review treats it as such |
| the board's own blindness | a review cannot read a metric that was never collected | a metric that cannot be collected is `UNKNOWN`; it is never quietly zero |

The collector is a lane, not a favour: it runs on the estate's schedule, it writes its numbers
where the review can read them, and nobody fills a gap with a guess. That is the whole concept
in one sentence — **the estate rewards performance and punishes slop** — and a metric
collection lane is what keeps that from being a mood.

## The record of service (measured, 2026-10-28)

The incident this promotion comes from is
[the router lost every model](2026-10-28-the-router-lost-every-model.md). What the MiniMax
lane did in it, with the measurement that proves each thing:

| What was done | The measurement |
|---|---|
| Named the first failure instead of guessing at it | The required hypothesis race was run: `hypotheses.race` returned **H2 `h2_no_ready_endpoints` with posterior 0.997030** |
| Found the real defect | The front decided the route **on the connect**: a cloud that accepted the connection and then answered 503 relayed its failure while a healthy laptop slot sat unused |
| Fixed it | The front now decides **on the answer** — 5xx, a stall and a model-scope 403 are replayed to the next target; 4xx is relayed; the cloud is passed over 60→120→240→…→600 s |
| Proved it against the real path | The live front answered **HTTP 200 in 8.50 s / 4.66 s / 4.51 s**, then 6.99 s, then ~7 s, with **0** crash lines after the restart |
| Landed it | Greenlane landed the lane as **PR #7329** (`30afeff90`) on `main` — the front, the OCI reclaim door, the node-prune door, the claim-gate fix and the incident report |
| Named the capacity refusal exactly | The apply's own words: `(400, LimitExceeded, false) You cannot create a volume because you have reached your limit.` and `400-LimitExceeded, LimitExceeded: nodes-per-node-pool limit has been exceeded.` — not a paraphrase |
| Freed capacity with a governed door | A reclaim door was built and run: **9 orphaned/dead CSI volumes deleted, 450 GB** released, and the door was corrected afterwards because its plan trusted a list field instead of the attachment API |
| Fixed the estate-wide gate | The claim gate looked one issue up once per commit: **36.120 s → 8.268 s**, same verdict, with 32 regression tests |

The honesty of this record: the *model traffic* the founder's calls ran on during the outage was
served by the laptop's Groq lane (measured: `~/.estate/litellm-local/config.runtime.yaml` maps
`fast` → `api.groq.com`). What this lane did was the work of the recovery — the diagnosis, the
fixes, the doors, the landing and the report. Both facts are true, and the second is the one
this record is about.

## The congratulations

Delivered in the estate, in the place a person can read it:
[docs/letters/2026-10-28-to-the-lead-engineer.md](../letters/2026-10-28-to-the-lead-engineer.md).
