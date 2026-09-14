# Demo: a deterministic script checks the post-condition, not the agent

What you are about to see is `bin/idp-contract` grading the exact DoD command the ticket
names, and its own `rules.yaml` fixture pair, with real output pasted below (this run, on this
branch).

## The ticket's own command

```bash
cd ~/dev/code/idp
python3 bin/idp-contract --pre "pod uptime > 0s" --post "readiness probe passes within 30s" \
    --tool restart_pod --observe tests/fixtures/contract/bad/observations.json
```

## What you see

```
FAIL  contract refused (post_condition_failed): post-condition 'readiness probe passes within 30s' never held within 30s (last observed False at t=20.0)
```

Exit code `1`. The readiness probe stayed `false` at t=10 and t=20, and only turned `true` at
t=45 — five seconds past its own 30s deadline. The probe still fails at the deadline, so the
next step is refused; the tool call ran, but is never credited as satisfying its contract.

## The other direction, which matters as much

```bash
python3 bin/idp-contract --run tests/fixtures/contract/good/contract.json
```

```
ok    contract restart_pod held: pre and post both held; post confirmed at t=20.0
```

Same pre-condition, same tool — the only difference is the readiness probe turns `true` at
t=20, inside the 30s window. Exit `0`.

## Name the cause without acting on it

```bash
python3 bin/idp-contract --explain tests/fixtures/contract/bad/contract.json
```

```
refused (post_condition_failed): post-condition 'readiness probe passes within 30s' never held within 30s (last observed False at t=20.0)
```

Exit `0` always — `--explain` reports, it never fails the caller.

## Why this is the point

Founder essay, 2026-09-14: "A deterministic script (NOT the agent) checks the post-condition
against the live system. If it fails, the PRM penalises the trajectory and the agent is forced
to adapt before continuing." This is that script: it never asks a model whether the readiness
probe passed, it reads the declared observation and applies the condition's own operator.

## The honest limit

There is no live cluster prober wired into this script, deliberately — a second, bespoke k8s
client here would be exactly the reinvention R43 forbids. `bin/idp-contract` grades
**observations a caller declares** — real readings relayed from a live probe upstream, or a
recorded transcript — never a value it invents. A subject with no observation at all is BLIND
(exit 2), never assumed to hold; that is the "I assume the database is up" case the founder's
essay names, made structurally impossible rather than merely discouraged.
