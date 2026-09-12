# Onboarding: the breaker enforcement

## What it is for

The circuit breaker refuses the linear path once three targets carry the same finding. The
`rules.yaml` row proves that logic in CI. This extension is what makes it **enforce**, in the
session, before the fourth tool call runs.

It exists because on 2026-09-12 an agent checked five pull requests one at a time when the third
had already proved the shared cause. A rule in CI would have reported that hours later, on a
different machine, after the session had ended.

## What it costs

Nothing. A TypeScript extension calling a local Python script. No cluster, no network, no spend. It
appends one JSON line per observed finding to `~/.estate/breaker-observations.jsonl`.

## Where it lives

| | |
|---|---|
| the extension | `extensions/breaker/index.ts` in idp, installed at `~/.pi/agent/extensions/breaker/` |
| the decision | `extensions/breaker/decide.mjs` — wires the estate's breaker, holds no logic |
| the logic | `bin/idp-circuit-breaker` (merged, with a rules.yaml row) |
| the record | `~/.estate/breaker-observations.jsonl` |
| the tests | `tests/test_breaker_extension.py`, `tests/test_circuit_breaker.py` |

## How to install it

```bash
mkdir -p ~/.pi/agent/extensions/breaker
cp extensions/breaker/index.ts extensions/breaker/decide.mjs ~/.pi/agent/extensions/breaker/
```

pi auto-discovers `~/.pi/agent/extensions/*/index.ts` (docs/extensions.md line 118). **There is no
`settings.json` entry to add** — an earlier test asserted one and was asserting a mechanism that
does not exist. A `/reload` is enough to pick it up in a running session.

## How to stop it

Delete `~/.pi/agent/extensions/breaker/`, or point `ESTATE_BREAKER_STATE` at a path you then
remove. The extension only reads and appends; nothing else in the estate depends on it.

## What it does not do

- It does not decide whether a finding is real, or whether a target's failure matters. It counts
  and fingerprints.
- It does not block a target or a tool. A different finding on a locked target is allowed, and nine
  findings across nine targets never lock.
- It observes `bash` and `read` only. A write is a change, not a diagnosis, and counting those
  would lock the tool an agent needs in order to fix the thing.

## When it blocks and you think it is wrong

Two genuinely different findings can only collide if their fingerprints collide. Run
`bin/idp-circuit-breaker --finding "<text>"` on both and compare the `fingerprint` field — it is a
pure function, so this is one command. If they match, the fingerprint is too coarse and that is the
bug, not the threshold.
