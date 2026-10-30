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
2. **The aggregate is total over what this host can answer.** Any failure makes the verdict a
   failure; any unknown makes it unknown; only an all-OK set is `MEASURED_OK`. There is no path
   by which the estate is reported healthy by omission.
3. **The verdict is about the answer, never the connect.** A path that refuses the connection
   has been measured, and it did not work.

## Scope: a board that can never be green teaches the estate to ignore the board

A laptop cannot answer a cluster question. When the instrument treated that as a failure of the
laptop, every run carried one permanent `UNKNOWN` and the board was red for a reason no work
could fix. So the aggregate is now **scope-aware**:

* a predicate whose scope is not this host's is **out of scope**: it is published by name, with
  the reason, and it does not count against the verdict here;
* the total verdict over **every** predicate is published beside the host verdict as
  `verdict_all`, with `counts_all` beside `counts`, so the split hides nothing;
* an applicable predicate that cannot be measured is still `UNKNOWN`, and still counts.

| field | what it is |
|-------|------------|
| `verdict` | the host's verdict, over the predicates this host can measure |
| `verdict_all` | the total verdict, over every predicate including other scopes |
| `counts` / `counts_all` | the three counts, for the same two sets |
| `out_of_scope` | the predicates this host cannot answer, by id, with the reason |
| `scopes` | the verdict and counts per scope |

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
* `memory.recall` -- the memory door the Mac bridge reads carries a door, at the canonical
  manifest `~/.estate/memory/platform/estate/memory/runtimes.json`;
* `runtime.current` -- the tree the estate actually runs on (`~/.estate/runtime/idp`) is `main`,
  compared against the **remote** `main`, not the mirror's own local ref;
* `host.load` -- this box is not saturated, against the front's own threshold of
  `8 x cpu_count` (`ESTATE_FRONT_LOAD_MAX` overrides it);
* `estate-db.rows` -- estate-db answers a query, so the estate's durable state is reachable
  (cluster scope).

Two of these exist because the first version of the instrument measured the wrong thing:

* **the laptop lane is served as `default`** -- the old probe asked for
  `claude-haiku-4-5-20251001`, a model the front does not carry on that lane, and measured a
  refusal that read like a broken router;
* **the memory manifest has one canonical path** -- the old probe read
  `~/.estate/memory/runtimes.json`, which the estate does not own, and measured the founder's
  recall path as absent while it was present under its real name.

### Credentials, by name only

No predicate may print a credential, a prompt body or a response body. The probe prompt is the
fixed string `Reply with exactly: PONG` and the expected reply is `PONG`, so a passing
predicate is provable from the transcript without leaking anything. Details are redacted before
they are written: a verdict carries a reason, never a key.

The credential each HTTP predicate presents is named, never embedded:

* `auth_env` may name one variable or a list of accepted names; the first that carries a value
  wins. The executor carries the laptop caller key as `LITELLM_API_KEY`, the scheduled job does
  not inherit it;
* `auth_sops` names where the key lives when no environment variable carries it: the sops
  wrapper, the encrypted caller file, the JSON path inside it, and the age key. The instrument
  extracts it into a local variable and never prints, logs or writes it.

A credential that is absent does not stop the measurement: the path is asked anyway, and a
refusal is `MEASURED_FAIL` while a success without the credential is `UNKNOWN` (the endpoint
answers; the founder's credentialed path is not proven).

### The User-Agent is part of the question

The cloud edge refused the caller's own User-Agent with `error code: 1010`. The cloud probe
therefore presents `estate-router-front/1.0`, exactly as the front does, and declares it in the
contract (`headers.User-Agent`) rather than hiding it in the code.

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

## What it measured on 2026-10-30

The repaired instrument, on the laptop, measured in under four seconds:

```
MEASURED_FAIL router.cloud.completion    any      HTTP 530 (expected 200): error code: 1033 (no LITELLM_CLOUD_PROBE_KEY on this host)
MEASURED_FAIL router.laptop.completion   laptop   HTTP 503 (expected 200)
MEASURED_OK router.lanes.accounted     laptop   22 declared lane(s) accounted for: 25 served, 4 refused
MEASURED_OK memory.recall              laptop   the door is at https://mcp.mumchimp.com/estate/mcp
MEASURED_FAIL runtime.current            laptop   the runtime mirror is at 8e892d44c1bf but main on the remote is f2ffe9ecba91 (1 commit(s) behind)
MEASURED_FAIL host.load                  laptop   the 1-minute load average is 212.9, over the front's threshold of 32.0 (8 x 4 cpu); the front refuses traffic on a saturated box
OUT      estate-db.rows             cluster  measurable only from the cluster scope; this host is laptop
TRUTH VERDICT: MEASURED_FAIL  (ok=2 fail=4 unknown=0) host=Roses-MBP scope=laptop  [out of scope here: estate-db.rows]
```

Read it as one story, not six rows. The laptop route answered `503` because the front refuses
traffic on a saturated box -- `host.load` names the cause, so the estate does not go and fix a
router that is not broken. The cloud route is down at the edge (`1033`), not merely
uncredentialed. The lane ledger now reads at all: the refusal records are dictionaries
(`lane`, `reason`, `verdict`), and one unhashable dict once took the whole board down with
`TypeError: unhashable type: 'dict'`. The memory door is found, at its canonical path. And the
running tree is a commit behind `main`, which the runtime sync reconciles when the load gate
admits it.

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

## What the second version fixed

The first version measured the wrong things, and a board that measures the wrong thing is worse
than no board, because it sends the estate to fix the wrong code:

| what the first version did | what it measures now |
|---------------------------|-----------------------|
| asked the laptop front for a model it does not carry | asks the lane the front serves (`default`), `max_tokens: 64` |
| read a memory manifest path the estate does not own | reads the canonical manifest |
| hashed a refusal record and crashed on `dict` | reads both ledger shapes, string and record |
| carried no credential to the laptop front | names the credential and its vault location |
| counted a cluster question as a laptop failure | scope-aware aggregate, `verdict_all` published beside it |
| said nothing about the tree the estate runs | `runtime.current`, remote `main`, both SHAs named |
| reported a saturated box as a broken route | `host.load`, against the front's own threshold |

