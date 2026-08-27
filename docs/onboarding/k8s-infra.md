# Onboarding: k8s-infra

Nothing to do per workload. Every pod on the cluster gets metrics and logs collected the moment
it is scheduled; the agent runs on every node and the Deployment watches the API server.

What you get in SigNoz without touching your service:
- Pod and container CPU, memory, restarts, phase (kubeletMetrics, clusterMetrics).
- Node CPU, memory, disk, network (hostMetrics).
- Container stdout and stderr as logs, tagged with namespace, pod, container (logsCollection).
- Kubernetes events (k8sEvents).

- Every network flow, drop and DNS answer per workload (Hubble, crew#539 CP12): Cilium runs
  chained after the cluster's own CNI (`platform/cilium`, generic-veth over flannel) and its
  Hubble metrics (`hubble_flows_processed_total`, `hubble_drop_total`, `hubble_tcp_flags_total`,
  `hubble_dns_*`, labelled `source_workload` / `destination_workload`) land in
  `signoz_metrics` through the annotation scraper below. The telemetry-coverage receipt
  (`bin/idp-telemetry-coverage`) carries `hubble_radio_flows=N`, the last hour's series naming
  a radio-room workload; 0 is a FAIL.

Any pod can add its own Prometheus endpoint with three annotations, no collector change
(`presets.prometheus`, prefix `signoz.io`): `signoz.io/scrape: "true"`, `signoz.io/port`,
`signoz.io/path`. Nothing is scraped without the annotation.

What it does not give you: traces and application metrics. Those come from your own OTLP
exporter to `http://signoz-otel-collector.observability.svc:4318` (see the LiteLLM row in
`platform/llm/litellm.yaml`).

Changing it: edit the `values:` block in `platform/observability/k8s-infra.yaml`, run
`bin/idp-kyverno-render platform/observability`, and open the PR. A change that needs a new
policy waiver fails `tests/test_incident_crew388_k8s_infra_node_agent_waiver.py` until the
exception in `platform/edge/k8s-infra-exception.yaml` names exactly the failing policies.
