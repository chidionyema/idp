# Onboarding: the circuit breaker

## What it is for

An agent may diagnose freely. But when three targets return the same finding, the cause is proved
and the next linear action is waste — so the breaker disables the primitive and names the fleet
lever instead. It exists because on 2026-09-12 nine pull requests were red on one cause while an
agent would have fixed them one at a time.

## What it costs

Nothing. A local Python script, no cluster, no cloud spend. With `--store` it appends a JSONL
record; without it, it is in-memory.

## Where it lives

| | |
|---|---|
| the breaker | `bin/idp-circuit-breaker` |
| the tests | `tests/test_circuit_breaker.py` |
| the record | `--store <path>`, append-only, optional |

## How to use it

```bash
# record a finding against the target that produced it
bin/idp-circuit-breaker --finding "the tool's output" --target pr-3253

# ask before acting on the next target
bin/idp-circuit-breaker --check --finding "the tool's output" --target pr-3254
# exit 0 the action may proceed; exit 1 -> 423 Locked, and the JSON carries the lever
```

From Python, for a harness or a hook:

```python
from importlib.machinery import SourceFileLoader
breaker = SourceFileLoader("breaker", "bin/idp-circuit-breaker").load_module()
b = Breaker()
b.observe(log_text, "pr-3253")
v = b.check(log_text, "pr-3254")
if v["locked"]:
    print(v["message"], v["lever"])
```

## How to stop it

It stops when it returns. The lock lives in memory unless `--store` is given; delete the store
file to clear it. `Breaker(n=...)` changes the threshold, and the default 3 is the founder's
number.

## What it is not

- It is **not** a gate in CI. It grades an agent at run time, not a pull request.
- It does **not** decide whether a finding is real, or whether a target's failure matters. It
  counts, fingerprints, and refuses repetition.
- It does **not** block a target or a tool. A different finding on a locked target is allowed, and
  that is deliberate: blocking by tool would refuse correct work (R38).

## When it locks and you think it is wrong

Two causes look the same only if their fingerprints collide. Check `fingerprint()` on both
inputs — it is a pure function, so this is one line. If two genuinely different findings share a
fingerprint, the fingerprint is too coarse and that is the bug, not the threshold.
