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
