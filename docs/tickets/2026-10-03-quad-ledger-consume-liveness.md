---
id: 2026-10-03-quad-ledger-consume-liveness
title: "quad-ledger consume: expose real liveness so the probe can stop being waived"
status: OPEN
priority: P2
owner: unclaimed
created: 2026-10-03
---

# Why

On 2026-10-03 the quad-ledger Deployment reached admission for the first time (it had never been
built -- the row was missing from `clusters/oke/kustomization.yaml` from `390ec4875` until
`3bbd3b2d`, and the depended-on Kustomization was named `secrets` when the row is
`external-secrets`). Kyverno refused it:

```
require-pod-probes:
  'validation failure: Liveness, readiness, or startup probes are required for all containers.'
```

`platform/quad/ledger/exception.yaml` waives that rule for this one workload, with the reasoning
written down. **A waived guard is debt.** This ticket is the payment.

# What is actually wrong

`quad-ledger consume` (`cmd/quad-ledger/main.go:85`) is a long-running JetStream consumer. It:

- listens on **no port** -- `ledger.yaml` declares no `ports:` anywhere, so `httpGet`/`tcpSocket`
  cannot be aimed at it;
- runs in `gcr.io/distroless/static:nonroot` (`cmd/quad-ledger/Dockerfile:13`) -- no shell, no
  coreutils, so a `ps`/`test`/`sh` exec probe is impossible;
- exposes **no liveness signal at all** -- there is nothing an operator can ask "are you still
  consuming?" and get an answer from.

`verify` is the wrong probe: it walks the whole hash chain and reads `merkle_anchors` (a full DB
scan on a timer), and it is already the `quad-ledger-verify` CronJob's job. Liveness and
correctness are different questions and conflating them is how a healthy-but-lagging consumer gets
restarted mid-flight.

# The fix

Give `consume` something real to be probed on. Pick one and implement it:

1. **Heartbeat row** (preferred). `consume` upserts `quad_ledger.consumer_heartbeat(id, ts)` on
   each delivered message or every N seconds; the probe runs
   `exec: ["/quad-ledger", "health", "--max-age", "60"]`, which reads that row and exits nonzero
   when the heartbeat is stale. This distinguishes "process alive" from "consumer stalled", which
   is the thing the policy is actually protecting against.
2. **Unix socket / localhost listener**. `consume` serves `/healthz` on `127.0.0.1:<port>`; the
   probe is an `httpGet` against it. Cheaper, but on a distroless image a loopback HTTP server is
   more moving parts than a heartbeat row.

Whichever is chosen:

- add the `health` subcommand to `cmd/quad-ledger/main.go` (currently `migrate|consume|anchor|verify`);
- add the probe to `platform/quad/ledger/ledger.yaml` with `initialDelaySeconds` generous enough
  for JetStream reconnect;
- **delete the `require-pod-probes` block from `platform/quad/ledger/exception.yaml`**, and delete
  the file entirely if no other rule remains in it.

# Definition of done

The `require-pod-probes` exception is gone, the Deployment carries a probe that fails when
`consume` is genuinely stalled, and a deliberate `kill -STOP` on the consumer produces a restart.
A merged PR is not done; the exception being deleted from git is.

# Acceptance signal

Delete the exception, let Flux reconcile, and read the pod: it is `Ready` with a probe that has a
non-zero `failureThreshold` it could actually reach. Then stop the consumer's progress (pause its
DB writes), and watch the kubelet restart it -- a real production event, not a green check.
