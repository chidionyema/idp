# Onboarding: k8s-infra

Nothing to do per workload. Every pod on the cluster gets metrics and logs collected the moment
it is scheduled; the agent runs on every node and the Deployment watches the API server.

What you get in SigNoz without touching your service:
- Pod and container CPU, memory, restarts, phase (kubeletMetrics, clusterMetrics).
- Node CPU, memory, disk, network (hostMetrics).
- Container stdout and stderr as logs, tagged with namespace, pod, container (logsCollection).
- Kubernetes events (k8sEvents).

What it does not give you: traces and application metrics. Those come from your own OTLP
exporter to `http://signoz-otel-collector.observability.svc:4318` (see the LiteLLM row in
`platform/llm/litellm.yaml`).

Changing it: edit the `values:` block in `platform/observability-collector/k8s-infra.yaml`, run
`bin/idp-kyverno-render platform/observability`, and open the PR. A change that needs a new
policy waiver fails `tests/test_incident_crew388_k8s_infra_node_agent_waiver.py` until the
exception in `platform/edge/k8s-infra-exception.yaml` names exactly the failing policies.
