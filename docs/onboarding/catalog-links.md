# Onboarding: observability links on catalogue entities

Every platform Component in `backstage/platform/catalog-info.yaml` carries `metadata.links`:
the logs-and-metrics door on all of them, the model-traces door only where traces are really
sent. The file is generated — never edit it. Edit `bin/catalog-platform` and re-run it.

How the generator decides, so you can extend it correctly:

- The two hostnames come from `http_hostnames()` on the observability layer's `spec.path`
  (its HTTPRoute manifests). No hostname is a literal in the generator (LAW 46); the
  `${ESTATE_ZONE}` placeholder rides through and Flux substitutes it at apply time from the
  cluster's `estate-config` ConfigMap.
- A layer gets the traces link when any YAML file in its own path mentions `LANGFUSE_` — the
  same keys its pods self-gate tracing on, so the link and the traces appear together.

The guard is `tests/test_incident_crew758_every_layer_opens_its_logs_and_traces.py`: every
Component must carry the logs door, and the set of layers with a traces link must equal the
set whose manifests project tracing keys, computed independently of the generator. If you add
a new observability backend, give it a hostname in the observability layer's routes and teach
`observability_doors()` its prefix — the test will hold you to the same honesty.
