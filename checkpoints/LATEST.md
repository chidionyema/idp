# RESUME HERE — 2026-09-04, session 5f6f4e72, research engine into the store front

## What is in flight

- **idp#1483** (auto-merge armed): the hourly research pass runs `--profile <lane>` on image
  `sha-35bd1962`; the intake is `lane: subject` lines and the questions live in the lane.
- **idp#1486** (auto-merge armed): the read side — CloudNativePG role `research_reader` with
  `inRoles: [research_consumer]`, its password minted by `bin/idp-estate-seed` and copied into
  `prospector-engine-env` as `RESEARCH_PG_PASSWORD`.
- **research-engine#4** (green then merge by hand — private repo, auto-merge unavailable):
  `db/ddl.sql` creates NOLOGIN `research_consumer` and grants it SELECT.
- **prospector, branch `feat/research-grounded-signals`**: `prospector/research_intake.py` reads
  admitted claims and renders a signal; next step is wiring it into
  `prospector/scheduler/run_scheduled.py` where the tick calls `run_signal("")` (~line 1569),
  adding `psycopg[binary]` to requirements, the env in `deploy/k8s/base/scheduler.yaml`, and
  tests with a fake connection.

## Why

crew#659: the factory generates blue-sky because the tick passes an empty signal. The research
engine's admitted claims become that signal. The adapter is in prospector, never in the engine —
research-engine SPEC-v1 §8 (a lane is data, an adapter is code in the consumer's repository).

## Not to touch

The idp working tree holds session 85f840c5's uncommitted `platform/flux-webhook/*` and
`platform/oci/flux-webhook.tf`. Both idp pull requests went through the GitHub API for that
reason; do not check out a branch over them.
