# The truth instrument — how the estate knows whether it works

**Founder, 2026-10-29:** *"we are totally out of touch with reality and no sense or awareness of
implications of our decisions"*; *"a claim should have come with proof"*; *"following estate
rules must not be optional"*; *"no urgency given the situation"*.

## The gap this closes

The estate had a process for ownership (claims, heartbeats, the collision check) and a process
for code (gates, CI, Greenlane). It had **no process for truth**: no standing instrument said
whether the founder's own path worked.

The consequence was measured on 2026-10-29. Every gate was green. The founder's router answered
nothing. The cluster's control plane had been deleted at 01:45 that morning and the estate
learned of it hours later, from a symptom. A fix could not be judged, so it was not judged; work
evaporated; and the estate was blind.

Ownership says *who* is doing it. Truth says *whether it works*. Neither substitutes for the
other, and the estate had only one of them.

## What the instrument is

`bin/idp-estate-truth` (the engine: `platform/estate/libexec/estate-truth.py`) asks a declared
set of predicates about the founder's real path and gives each one a verdict:

| verdict | meaning |
|---------|---------|
| `MEASURED_OK` | the predicate was attempted and its expectation was met |
| `MEASURED_FAIL` | the predicate was attempted and its expectation was **not** met |
| `UNKNOWN` | the predicate could not be attempted from here (no credential, wrong host) |

Three rules make it worth having:

1. **UNKNOWN is never OK.** A predicate nobody could measure counts against the verdict exactly
   as a failure does, because "we did not look" and "it works" are not the same statement.
2. **The aggregate is total.** Any failure makes the verdict a failure; any unknown makes it
   unknown; only an all-OK set is `MEASURED_OK`. There is no path by which the estate is
   reported healthy by omission.
3. **The verdict is about the answer, never the connect.** A path that refuses the connection
   has been measured, and it did not work.

## Where the questions live

`catalog/truth-contract.json` declares the predicates and, for each path, which predicate that
path answers. It is data, so the law is auditable in one file and extending it is a one-line
change. Nothing is hard-coded in the instrument.

The predicates are deliberately the founder's *real* path, not proxies:

* `router.cloud.completion` — a real chat completion through `llm.mumchimp.com` answers 200 with
  the token `PONG`;
* `router.laptop.completion` — a real chat completion through the laptop front
  (`127.0.0.1:4000`) answers 200 with the token `PONG`;
* `router.lanes.accounted` — every lane the router declares is accounted for as **served** or
  **refused**, with a reason;
* `memory.recall` — the memory door the Mac bridge reads carries a door;
* `estate-db.rows` — estate-db answers a query, so the estate's durable state is reachable.

No predicate may print a credential, a prompt body or a response body. The probe prompt is the
fixed string `Reply with exactly: PONG` and the expected reply is `PONG`, so a passing
predicate is provable from the transcript without leaking anything. Details are redacted before
they are written: a verdict carries a reason, never a key.

## Where the answers live

| file | what it is |
|------|------------|
| `~/.estate/results/truth/latest.json` | the last measurement on this machine |
| `catalog/truth-verdicts.json` | the machine-generated snapshot, committed like the capability registry, so a gate can verify it |

The snapshot is a **witness**: it is written by the instrument, refreshed on a schedule, and
exempt from the claim requirement (like the capability registry witness). Its freshness is
checked: a measurement older than seven days is not evidence about now, because the instrument
runs every fifteen minutes and a week-old snapshot means the instrument stopped.

## The proof obligation (mechanically enforced)

`bin/claim-gate` now refuses a change that touches a truth path unless the measurement of the
predicate that path answers is present and is not `UNKNOWN`:

* **no measurement** → refused. Unknown is never ok;
* **`UNKNOWN`** → refused. Unknown is never ok;
* **`MEASURED_FAIL`** → the change must **name** it: `Proof: <predicate-id>` in the commit
  message. A change may land while the founder's path is broken — that is often the fix — but
  it cannot land *in silence*;
* **`MEASURED_OK`** → nothing is asked. The measurement already proves it, and a gate that asks
  for more would be ceremony.

**What this gate cannot do, said plainly:** it cannot prove the measurement was true. A witness
in a repository can be written by the person it is about. That is why the measurement is also
published to the claim issue (durable, off the machine, in the founder's eyes) and why a stale
snapshot is refused. The gate enforces **evidence, freshness and acknowledgement**; whether the
change addresses the failure it names stays a human judgement, and pretending otherwise would
be a gate that cannot fail.

## How it runs

* **On the laptop:** `launchd/ai.estate.truth.plist.tmpl`, every 15 minutes, writing
  `~/.estate/results/truth/latest.json`. The laptop measures the laptop-scoped predicates.
* **Off the laptop:** `.github/workflows/estate-truth.yml`, every 15 minutes on a runner. A
  runner measures the cloud route even when the laptop is dead — which is exactly the case the
  laptop's own schedule cannot cover, and the case the estate was in on 2026-10-29.
* **On demand:** `bin/idp-estate-truth`, or the `estate-truth` intent.

## What it measured on 2026-10-29

The first run of the instrument, on the laptop, at 08:30:

```
MEASURED_FAIL router.cloud.completion    any      no answer: urlopen error EOF occurred in violation of protocol (_ssl.c:1129)
MEASURED_FAIL router.laptop.completion   laptop   HTTP 401: Missing Anthropic API Key - a call is being made to anthropic but no key is set
MEASURED_FAIL router.lanes.accounted     laptop   lanes.json does not account for its declared lanes (declared/served/refused missing)
MEASURED_FAIL memory.recall              laptop   ~/.estate/memory/runtimes.json is absent
UNKNOWN     estate-db.rows               cluster  measurable only from the cluster scope; this host is laptop
TRUTH VERDICT: MEASURED_FAIL  (ok=0 fail=4 unknown=1)
```

Four failures and one unknown, measured in thirty seconds, by a door that had never existed
before that morning. That is the estate's position, stated by an instrument rather than by an
opinion — and it is the first honest answer the estate has given about its own state since the
cluster was deleted.
