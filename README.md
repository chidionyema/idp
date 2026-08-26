# idp — the estate's platform

One platform, one of each layer, running on OKE and reconciled by Flux from this repository.
Products (`prospector`, `hermes-v2`) run on it; they do not carry copies of it.

Two generated pages describe it and are refreshed by `make diagrams`; a hand-drawn page is refused
by `bin/estate-diagram --check`:

- `docs/architecture/index.md` — the C4 model, rendered from `architecture/workspace.dsl`.
- `docs/architecture/live.md` — what is actually listening, scheduled and guarded, rendered from
  the catalogue that `bin/catalog-gen` generates.

## Layers

Each directory under `platform/` is one layer. `clusters/oke/platform.yaml` is the Flux
Kustomization that applies them; `clusters/oke/estate-config.yaml` holds `ESTATE_ZONE` and the
other substitutions, so no manifest names a zone, a host or an account (LAW 46).

| layer | directory | what runs |
|---|---|---|
| service catalog and portal | `platform/backstage`, `catalog/` | Backstage at `catalogue.<zone>`, the estate's front door |
| identity | `platform/identity`, `platform/spire` | oauth2-proxy in front of every HTTPRoute; SPIRE for workload identity |
| edge and DNS | `platform/edge`, `platform/dns` | the shared Gateway (Traefik) and external-dns |
| secrets | `platform/secrets`, `platform/secret-store` | External Secrets Operator over OCI Vault |
| model routing | `platform/llm` | LiteLLM at `llm.<zone>`, bearer master key, no browser login |
| traces and audit | `platform/observability` | Langfuse |
| scheduling | `scheduler/` | Dagster; every job carries a description |
| CI and supply chain | `.github/`, `platform/github`, `platform/github-app` | pinned actions, Flux image automation, per-lane GitHub App |
| chaos and drills | `platform/chaos`, `drills/` | `oke-check`, `login-drill` and `drill-heartbeat` workflows |
| policy | `policy/`, `AGENTS.md` | Kyverno at admission; Rego and shell gates in `bin/idp-ci` |
| agent interface | `mcp/`, `sovereign/` | the estate MCP server and the Sovereign Bus |

## Proving it

Every gate runs locally and in CI with the same command.

| command | proves |
|---|---|
| `bin/idp-ci` | every rule in `AGENTS.md` refuses its bad fixture and passes its good one, in one run |
| `python -m pytest tests -q` | the property and incident tests under `tests/` |
| `cd sovereign && python -m pytest tests/bdd -q` | every `features/**/*.feature` scenario |
| `bin/idp-verify` | the published catalogue matches the inventory, entity by entity |
| `bin/idp-status` | what is serving, where |
| `bin/pr-report` | a pull request body answers the four architecture laws |

The GitHub workflows: `ci` (the three commands above, security scan, spec gate), `oke-check`
(apply to the live cluster and grade it), `login-drill`, `drill-heartbeat`, `build-multiarch`,
`image-update-pr`, `operating-model-gate`, `stale`.

## Rules

A rule that has no gate is not a rule here. `AGENTS.md` is the table of rules for this repository,
each with a must-fail and a must-pass fixture; `bin/idp-ci` parses that table. Every PR that changes
code also changes an executable spec (a `.feature`, a test, or a generator), or `spec-gate` refuses it.
Architecture decisions are in `docs/decisions/`; the operating model and the definition of done are
in `docs/policy/`.

## Local

`make cluster-up` creates a k3d cluster from `platform/k3d/estate.yaml`; `make catalogue-deploy`
builds and serves the catalogue on `127.0.0.1:3100`; `make cluster-down` removes it. `make bind-audit`
fails if anything but the gateway listens on a non-loopback address.

## Licence

Apache-2.0 (`LICENSE`). Every layer above is open source; `bin/policy-test` refuses a dependency
whose licence would block a sale (LAW 40).
