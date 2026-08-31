# Otto — the complete reference

Everything about Otto, Backstage, and the Telegram pin, in one page, so nothing has to be asked
twice. Every fact names the file it was read from; if a row and its file disagree, the file wins
and this page has drifted — fix the page. Facts verified 2026-08-31.

## 1. What Otto is

Otto is the estate's manager agent (founder, 2026-08-31: "Otto is Manager"). He is the
hermes-agent gateway: the Telegram front door to the estate, and — once his release command
exists — the one hand on the deploy lever, taking over from the founder (R63/R65, crew#755).
Agents never deploy; today the founder deploys, and Otto inherits that job when ready.

## 2. Where Otto runs

- **Cluster:** OKE production, namespace `hermes-agent`. Manifest: `platform/hermes-agent/gateway.yaml`.
- **Image:** `ghcr.io/chidionyema/hermes-agent` (gateway.yaml:234). Built from the
  `hermes-v2` repo (github.com/chidionyema/hermes-v2).
- **Telegram:** long-polling (`getUpdates`), so no public route exists (gateway.yaml:18).
  `TELEGRAM_BOT_TOKEN` is held by exactly one process (crew#284); when the cluster gateway runs,
  the old Mac launchd job (`ai.architect.gateway`) is booted out (gateway.yaml:11-20).
- **State:** PVC `hermes-agent-data` in the same namespace.
- **Backstage identity:** `backstage.io/kubernetes-id: founder-telegram` (gateway.yaml:174).

## 3. Identity vs memory — the soul file is not the memory

- **Identity:** `SOUL.md` (persona), baked into the Docker image at build time
  (hermes-v2 `Dockerfile:66`), alongside `USER.md` and `RITUALS.md`.
- **The repo's `MEMORY.md` is NOT his memory** — it is a stale platform map that declares itself
  stale since 2026-08-27.
- **His real memory is Hindsight**, a database-backed recall service:
  - switched on in hermes-v2 `config.yaml` (`memory_enabled: true`, `provider: hindsight`,
    5,000-character recall budget, lines 26-31);
  - client code in `hermes-agent/agent/memory_manager.py` + `plugins/memory/hindsight/`;
  - the service is a platform layer at `platform/hindsight/` with its own Postgres.
  - **Known issue:** the recall table was measured quiet since 2026-08-28 09:00Z (unconfirmed,
    one session's measurement) — the memory pipe may have stopped recording.
- **Proposal on the table:** crew sessions adopt Hindsight as the one memory layer instead of
  per-directory markdown piles (delivers R2 durable memory). Awaiting the founder's word.

## 4. Logs, traces, metrics — coverage state (ticket: crew#761)

| Signal | How it flows | State (2026-08-31) |
|---|---|---|
| LLM traces | Langfuse plugin → `langfuse-web.observability.svc:3000` (gateway.yaml:254); keys from ExternalSecret `platform/hermes-agent/langfuse-key.yaml` | Wired; landing unproven. Keys mount `optional: true`, so a missing key silently disables tracing — flagged for fix |
| Logs | SigNoz's cluster agent collects every pod's stdout (`platform/observability/values.yaml`) | Should land; unproven while the coverage probe is blind |
| Agent metrics/events | OpenTelemetry exporter ships in Otto's code (`hermes-agent/agent/monitoring/otlp_exporter.py`) | **Dormant** — config.yaml has no `monitoring:` block. Certain gap |
| Coverage proof | `bin/idp-telemetry-coverage` reads the in-cluster LAW 50 receipt (`platform/observability/telemetry-coverage.yaml`) | **BLIND** — receipt unreadable, 2026-08-31. Fixing this is step 1 of crew#761 |

The five-step plan to total coverage, with its Optimised line, lives on
https://github.com/chidionyema/crew/issues/761.

## 5. Rules that bind Otto

- **R60:** nothing merges without the founder's word.
- **R63:** releases become a word in the founder's Telegram chat, machine-executed; his Telegram
  word is the R60 word (crew#755).
- **R64:** all prompt work — Otto included — is DSPy, with proof per pull request (crew#756).
- **R65:** the founder deploys until Otto is ready; agents never trigger a deploy.
- **Bootstrap:** Otto's rebuild-from-scratch plan is approved — 7 phases ending in a one-tap
  client installer (plan file `~/.claude/plans/stateful-coalescing-prism.md`).

## 6. Backstage — the one door

- **URL: https://catalogue.mumchimp.com** — every platform service is `<service>.mumchimp.com`
  (zone set once in `clusters/oke/estate-config.yaml:11`; hostname rule in
  `platform/backstage/overlays/oke/httproute.yaml`).
- **Login:** federated via oauth2-proxy on the same hostname — the estate holds no password for a
  person (decision records 0003 and 0007, `docs/decisions/`).
- **What it shows:** the catalogue of every layer; the Ops dashboard and Tools page (crew#684);
  each layer's page opens its own logs (SigNoz) and, for Otto, traces (Langfuse) — crew#758.
- **The rule:** the founder sees everything from Backstage; a workload with no catalogue entity is
  refused admission (`platform/edge/require-catalogue-entity.yaml`).

## 7. The Telegram pin

- **Audit deliveries (R63 protocol):** a session ending its reply with `AUDIT:` plus one URL has
  that URL sent to the founder's Telegram chat and pinned, by the Stop hook
  (`~/.claude/scripts/founder-deliver.py`, rulings in `~/.claude/scripts/rulings.json`).
- **Release word (being built, crew#755):** the founder's release word in that same chat will
  machine-execute the deploy and reply with the run URL.
- **Hygiene:** the founder's DM is not an alert sink — the cluster alert flood was suspended in
  idp#732; alerts live in SigNoz, deliveries to Telegram are pins he asked for.

## 8. The deploy lever (today, until Otto takes it)

https://github.com/chidionyema/idp/actions/workflows/deploy-when-green.yml — if it reads
disabled, press **Enable workflow** first; then **Run workflow** → branch `main` → **Run
workflow** (the button only exists because the workflow declares `workflow_dispatch`, line 49).
