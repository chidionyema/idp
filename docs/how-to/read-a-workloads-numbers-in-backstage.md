# Read a workload's numbers in Backstage

Every Flux row and Helm chart on the cluster has a catalogue page with two tabs of live numbers.
Nothing is copied: the portal reads the cluster's own Prometheus and metrics-server at the moment
you open the page. Founder, 2026-08-29: "i need all metrics exposed ... on backstage ... always
... numbers for everything we collect" (crew#645 CP5; the incident that made it necessary is
the Langfuse incident report (idp#856)).

## Use

1. Open Backstage, search the workload by name (for example `langfuse` or `hindsight`).
2. **Metrics** tab: one graph per number, for every pod in the workload's namespace, last hour:
   - CPU used now (`estate:pod_cpu_cores:rate5m`) and its peak over 30 minutes
     (`estate:pod_cpu_peak_cores:30m`) against what git asked for (`estate:pod_cpu_request_cores`);
   - memory used (`estate:pod_memory_bytes`) against requested (`estate:pod_memory_request_bytes`);
   - container restarts (`estate:pod_restarts_total`).
   Below the graphs, every Prometheus alert firing in that namespace.
3. **Kubernetes** tab: the pods, deployments and services behind the workload with their status,
   and CPU and memory used against requested per container.

## Expect

A workload whose peak CPU is above its request shows the alert `RequestBelowMeasuredPeak` on the
Metrics tab after 30 minutes. That is the number to raise the request to, with the
`idp.platform/capacity-approved` label (`platform/edge/capacity-policy.yaml`).

## How it works

- `bin/catalog-gen` writes `backstage.io/kubernetes-namespace`, `backstage.io/kubernetes-label-selector`,
  `prometheus.io/rule`, `prometheus.io/alert: all` and `prometheus.io/labels` on every cluster
  entity; the test `tests/test_incident_crew645_every_cluster_entity_shows_its_numbers.py` refuses
  a generator that stops.
- The numbers are recording rules in `platform/monitoring/rules/capacity.yaml`, so the annotation
  names a series and never carries a query.
- The portal reaches Prometheus through its own proxy (`/prometheus/api`, GET only, signed-in
  users only) in `backstage/app-config.container.yaml`; the plugin is Roadie's Prometheus plugin,
  brought into the new frontend system by `@backstage/core-compat-api`
  (`backstage/packages/app/src/modules/metrics/index.tsx`).

## Not measured here

The measured boot floor per container comes from the VPA recommender (crew#645 CP2) and lands
beside these rows when it exists. Until then the 30-minute peak is the floor.
