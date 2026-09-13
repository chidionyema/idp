# Onboarding: the commerce Rails components get a boot window

`platform/commerce/app/lago.yaml`, the `startupProbe` postRenderer patches.

## The failure

Once the commerce rows were switched on (2026-09-13), three pods sat in
`CrashLoopBackOff` with 91+ restarts each:

```
lago-api-7df7476995-dt6q9              0/1   CrashLoopBackOff   93 restarts
lago-billing-worker-5466fbb9b7-bc8gx   0/1   CrashLoopBackOff   91 restarts
lago-clock-worker-7cdbd8f85-n9z2w      0/1   CrashLoopBackOff   91 restarts
commerce/lago: InstallFailed -- Deployment/commerce/lago-api status: 'Failed'
```

The events named the mechanism:

```
Warning  Unhealthy  Readiness probe failed: dial tcp :3000: connect: connection refused
Warning  Unhealthy  Liveness probe failed:  dial tcp :3000: connect: connection refused
Normal   Killing    Container lago-api failed liveness probe, will be restarted
```

The chart's liveness probe has **no `initialDelaySeconds` and there is no
`startupProbe`**: 3 failures × 10s gives `bundle exec` **30 seconds** to boot a
Rails app on a cold image. It does not boot in 30. The kubelet killed every boot,
forever, and `Failed` on the HelmRelease held the whole commerce Kustomization out.

## The database was not the problem

An easy and wrong diagnosis: the app crashed, so the database must be unreachable.
It is reachable. The app's own `DATABASE_URL` authenticated against `estate-rw`
and `select 1` answered:

```
$ kubectl -n estate-db exec estate-1 -c postgres -- psql "<the app's DATABASE_URL>" -c "select 1"
 ?column?
----------
        1
```

And the logs showed only the meilisearch rename warning, because Rails buffers in
production and the process was SIGKILLed before it could say what was wrong. **A
crash with no error message is a probe killing a boot, not an application error.**

## The fix

`startupProbe` is the fence Kubernetes has for exactly this. Liveness does not run
until startup passes, so a cold boot gets **300 seconds** and the steady state pays
nothing. The same fix, for the same reason, is already on `langfuse-web` in
`platform/observability/langfuse.yaml`.

It is a `tcpSocket`, not an HTTP path, and that detail is what makes it work for
all six components rather than just the api: three of them are **Sidekiq**, which
serves no HTTP at all, so a `/health` probe could never pass for them.

| component | runs |
|---|---|
| `lago-api` | Rails, serves HTTP on 3000 |
| `lago-worker` | Sidekiq |
| `lago-clock-worker` | Sidekiq |
| `lago-billing-worker` | Sidekiq |
| `lago-webhook-worker` | Sidekiq |
| `lago-payment-worker` | Sidekiq |

## What must not change

**The liveness probe stays.** It is a gate, not a replacement: removing it would
trade a boot failure for a process that hangs forever and is never restarted — a
worse defect than the one fixed. `test_the_api_keeps_its_health_endpoint...` pins
that.

**`lago-pdf` and `lago-events-worker` get no patch.** They render at zero replicas
by design and this manifest removes them; a patch targeting them would fail the
render or resurrect a component deliberately switched off.

## Why this is a postRenderer

The lago chart exposes no `startupProbe` value. `postRenderers` is already how this
estate bends a chart it does not own — temporal, hindsight, langfuse, traefik,
signoz and several more do the same — so this is the existing pattern, not a new
mechanism.

## Verifying

```bash
python3 -m pytest tests/bdd/test_lago_rails_boot_window.py -q
kubectl -n commerce get pods
```

Twenty scenarios: every Rails component has a startupProbe, each allows at least a
300-second window, each uses `tcpSocket` rather than an HTTP path (with the reason
— Sidekiq), the liveness probe is never removed, and no patch targets a component
this manifest disables.

Once Flux reconciles, `kubectl -n commerce get pods` is the proof: the three
`CrashLoopBackOff` pods become `Running`, and `commerce/lago` reports Ready.
