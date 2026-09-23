# Demo: k8s-infra

`platform/observability/k8s-infra.yaml` installs the SigNoz k8s-infra chart (0.17.0) next to
the SigNoz release. One DaemonSet (otel-agent) collects host and kubelet metrics and container
logs on every node; one Deployment (otel-deployment) collects cluster metrics and Kubernetes
events. Both send OTLP to `signoz-otel-collector.observability.svc:4317`. It exists because the
signoz chart 0.138.0 does not bundle it (crew#388): before this row the cluster had LiteLLM
traces and no pod, node or kubelet metrics.

Judge it offline the way admission will:

```
$ bin/idp-kyverno-render platform/observability
policies  24 ClusterPolicies from tests/fixtures/kyverno/upstream
ok    render   k8s-infra (observability, 0 patches): pass: 54, fail: 0, warn: 0, error: 0, skip: 2
ok    render   langfuse (observability, 5 patches): pass: 134, fail: 0, warn: 0, error: 0, skip: 6
ok    render   signoz (observability, 6 patches): pass: 166, fail: 0, warn: 0, error: 0, skip: 1
```

The two skips are the node agent's hostPath rules, waived for that one DaemonSet by
`platform/edge/k8s-infra-exception.yaml`. Remove the exception and the same command prints
`fail: 3` (disallow-host-path, disallow-host-ports before the ports were turned off,
restrict-volume-types) and exits 1.

On the cluster, after Flux reconciles: SigNoz, Dashboards, "Kubernetes Pod Metrics" shows every
namespace, and Logs shows container logs with `k8s.namespace.name` attributes.
