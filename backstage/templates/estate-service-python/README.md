# New Python service (golden path)

The one door for a Python service (crew#627 CP2, founder 2026-08-30: "provision a service with
the infra it needs from one place"). One run of this template makes:

1. the repository from `skeleton/`: ruff, pytest, bandit, pip-audit, pre-commit, a passing
   first test, OpenTelemetry tracing to the estate collector, the estate guards installed from
   git on the first session, a CI workflow with gitleaks, Trivy and CodeQL on from the first
   commit, branch protection on `main`;
2. the catalogue entity (`catalog-info.yaml` registered by the scaffolder);
3. one pull request against `idp` from `infra/`: `platform/services/<name>/` (namespace,
   secret, deployment with two replicas spread across nodes, service, route behind the one
   login) and the Flux row `clusters/oke/service-<name>.yaml`, so Flux applies it on merge.

Mandatory in every service (founder decision 1): tracing, the guards, scanners. Ticked at
creation: database (a CloudNativePG `Cluster`), messaging (Apprise), payments (Stripe).

Spec: `docs/specs/self-service-golden-paths.md`. Test:
`tests/test_incident_crew627_python_golden_path_template.py`.
