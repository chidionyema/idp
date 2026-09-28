# 2026-09-03. hermes-v2 rides the platform's Flux road as the `hermes-agent` row, and there is no second road

Founder, 2026-09-03: "need all conpleted". The five-day capability audit of the same day (crew
repository, `docs/audits/2026-09-03-five-day-capability-audit.md`, section 5) listed "onboard
hermes-v2 and prospector onto the Flux road as catalogued workloads, retiring the launchd/hand
installs" as open work, and said hermes-v2 "still runs as a launchd job on the Mac with 14
uncommitted files". This record is what was measured, what was decided, and the guard that holds it.

## What was measured (2026-09-03, read, not remembered)

- The product's own build is the platform's image: hermes-v2's `Dockerfile` and
  `.github/workflows/build-agent-image.yml` push `ghcr.io/chidionyema/hermes-agent` on every merge
  to its main, tagged `main-<run>-<sha>`.
- The row exists and runs: `clusters/oke/platform.yaml` row `hermes-agent`, path
  `platform/hermes-agent`, prune and wait on, waiting on `scheduling`, `secret-store` and
  `alerts-github`, health-checked on `Deployment hermes-agent-gateway`. Flux reported Ready
  (`Applied revision: main@sha1:bf21ee34`); the pod ran 2/2 on
  `ghcr.io/chidionyema/hermes-agent:main-65-3c2b68b9…`, the newest hermes-v2 main build, moved there
  by `platform/image-automation/hermes-agent.yaml`.
- The catalogue holds it three ways: `backstage/platform/catalog-info.yaml` Component
  `layer-hermes-agent` (annotated with the Flux row and the path), `backstage/founder/catalog-info.yaml`
  card `founder-otto` (bound to the Deployment) and company card `company-hermes`, whose domain
  `bin/catalog-gen` builds with a link to the hermes-v2 repository.
- Telemetry: model calls leave through the router and are traced there (STANDARDS observability
  row); the agent's own traces go to the in-cluster Langfuse with keys the vault projects
  (`platform/hermes-agent/langfuse-key.yaml`); pod logs ride the SigNoz k8s-infra collector like
  every pod (`platform/observability-collector/k8s-infra.yaml`).
- The Mac: `launchctl list | grep -i -E 'architect|hermes'` printed nothing. The launchd job the
  audit named is gone.
- The 14 uncommitted files: two were product code worth keeping (a config note and a test for
  crew#751); the rest were a Fly deploy the repository's own test refuses, Mac-bound scripts,
  symlinks to an absolute path under the founder's home, and runtime state. Landed and dropped on the
  product side; the runtime paths are now ignored there so they cannot read as a wave again.

## The decision

The audit item was already done under another name, and the one thing missing was the rule that
says so. Adding `platform/hermes-v2/` with its own Deployment and Flux row, as the audit's wording
suggests, is refused: it is the same workload twice, and two Telegram pollers on one bot token are
409s on both (`platform/hermes-agent/gateway.yaml` header, crew#284). One workload, one row, one
image built by the product's own repository.

## The guard

`tests/test_hermes_v2_rides_the_hermes_agent_row.py` refuses, both ways: a second Flux row for the
same directory or one named hermes-v2, a `platform/hermes-v2/` directory, a gateway on another
image or a tag Flux does not move, a catalogue that forgets the layer, the founder card or the
company, and a Langfuse key typed into the pod's env. `platform/hermes-agent/README.md` carries the
same statement for a reader.

## Still open, and whose

- Prospector onto the Flux road is the other half of the audit's item 3 and is not touched here.
- The cluster's telemetry-coverage receipt read `FAIL … pods=124 seen=3 missing=121` at 16:45Z
  the same day. That is the observability lane's fire, not this row's: hermes-agent is one of the
  121, and so is nearly every other pod.
