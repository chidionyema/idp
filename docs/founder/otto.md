# Otto — the complete reference

Everything about Otto, Backstage, and the Telegram pin, in one page, so nothing has to be asked
twice. Every fact names the file it was read from; if a row and its file disagree, the file wins
and this page has drifted — fix the page. Facts verified 2026-08-31.

## 1. What Otto is

Otto is the estate's manager agent (the founder's word, 2026-08-31: "Otto is Manager"). He is the
hermes-agent gateway: the Telegram front door to the estate, and — once his release command
exists — the one hand on the deploy lever, taking over from the founder (rulings recorded on
[the Telegram release ticket](https://github.com/chidionyema/crew/issues/755)). Agents never
deploy; today the founder deploys, and Otto inherits that job when ready.

## 2. Where Otto runs

- **Cluster:** the production cluster, in the `hermes-agent` area. Manifest: `platform/hermes-agent/gateway.yaml`.
- **Image:** `ghcr.io/chidionyema/hermes-agent` (gateway.yaml:234), built from the
  hermes-v2 repository (github.com/chidionyema/hermes-v2).
- **Telegram:** the gateway polls Telegram for messages, so no public route exists
  (gateway.yaml:18). The bot token is held by exactly one process — [the one-holder
  decision](https://github.com/chidionyema/crew/issues/284) — and when the cluster gateway runs,
  the old Mac background job (`ai.architect.gateway`) is booted out (gateway.yaml:11-20).
- **State:** the `hermes-agent-data` disk in the same area of the cluster.
- **Backstage identity:** `backstage.io/kubernetes-id: founder-telegram` (gateway.yaml:174).

## 3. Identity and memory — the soul file is not the memory

- **Identity:** `SOUL.md` (persona), baked into the Docker image at build time
  (hermes-v2 `Dockerfile:66`), alongside `USER.md` and `RITUALS.md`.
- **The repository's `MEMORY.md` is NOT his memory** — it is a stale platform map that declares
  itself stale since 2026-08-27.
- **His real memory is Hindsight**, a database-backed recall service:
  - switched on in hermes-v2 `config.yaml` (`memory_enabled: true`, `provider: hindsight`,
    5,000-character recall budget, lines 26-31);
  - client code in `hermes-v2/hermes-agent/agent/memory_manager.py` + `hermes-v2/hermes-agent/plugins/memory/hindsight/`;
  - the service is a platform layer at `platform/hindsight/` with its own Postgres database.
  - **Known issue:** the recall table was measured quiet since 2026-08-28 09:00Z (unconfirmed,
    one session's measurement) — the memory pipe may have stopped recording.
- **Proposal on the table:** crew sessions adopt Hindsight as the one memory layer instead of
  per-directory markdown piles, delivering the founder's durable-memory order. Awaiting his word.

## 4. Logs, traces, metrics — the coverage state

The ticket and five-step plan: [Otto total
coverage](https://github.com/chidionyema/crew/issues/761).

| Signal | How it flows | State (2026-08-31) |
|---|---|---|
| Model-call traces | Langfuse plugin sends to `langfuse-web.observability.svc:3000` (gateway.yaml:254); keys arrive as a vault-fed secret (`platform/hermes-agent/langfuse-key.yaml`) | Wired; landing unproven. The keys mount `optional: true`, so a missing key silently turns tracing off — flagged for fix |
| Logs | The observability agent collects every pod's output (`platform/observability/values.yaml`) | Should land; unproven while the coverage receipt cannot be read |
| Agent metrics and events | An OpenTelemetry exporter ships in Otto's code (`hermes-v2/hermes-agent/agent/monitoring/otlp_exporter.py`) | **Dormant** — config.yaml has no `monitoring:` block. Certain gap |
| Coverage proof | `bin/idp-telemetry-coverage` reads the in-cluster coverage receipt (`platform/observability/telemetry-coverage.yaml`) | **Cannot answer** — the receipt was unreadable on 2026-08-31. Fixing this is step 1 of the coverage ticket |

## 5. Rules that bind Otto

- Nothing merges without the founder's word — his standing human-in-the-loop order.
- Releases become a word in the founder's Telegram chat, machine-executed; his Telegram word is
  the merge word ([the Telegram release ticket](https://github.com/chidionyema/crew/issues/755)).
- All prompt work — Otto included — uses DSPy, with proof per pull request ([the DSPy
  ticket](https://github.com/chidionyema/crew/issues/756)).
- The founder deploys until Otto is ready; agents never trigger a deploy.
- **Rebuild plan:** Otto's rebuild-from-scratch plan is approved — 7 phases ending in a one-tap
  client installer (plan file `~/.claude/plans/stateful-coalescing-prism.md`).

## 6. Backstage — the one door

- **URL: https://catalogue.mumchimp.com** — every platform service is `<service>.mumchimp.com`
  (zone set once in `clusters/oke/estate-config.yaml:11`; hostname rule in
  `platform/backstage/overlays/oke/httproute.yaml`).
- **Login:** federated, through the login proxy on the same hostname — the estate holds no
  password for a person (decision records 0003 and 0007, `docs/decisions/`).
- **What it shows:** the catalogue of every layer; the Ops dashboard and the Tools page ([the
  everything-visible ticket](https://github.com/chidionyema/crew/issues/684)); each layer's
  catalogue page opens its own logs and, for Otto, model-call traces ([the one-door
  ticket](https://github.com/chidionyema/crew/issues/758)).
- **The rule:** the founder sees everything from Backstage; a workload with no catalogue entity
  is refused admission (`platform/edge/require-catalogue-entity.yaml`).

## 7. The Telegram pin

- **Audit deliveries:** a session ending its reply with `AUDIT:` plus one address has that
  address sent to the founder's Telegram chat and pinned, by the reply hook
  (`~/.claude/scripts/founder-deliver.py`, rulings in `~/.claude/scripts/rulings.json`).
- **Release word (being built, [the Telegram release
  ticket](https://github.com/chidionyema/crew/issues/755)):** the founder's release word in that
  same chat will machine-execute the deploy and reply with the run address.
- **Hygiene:** the founder's chat is not an alert sink — the cluster alert flood was suspended
  ([the quiet-chat change](https://github.com/chidionyema/idp/pull/732)); alerts live in the
  observability service, deliveries to Telegram are pins he asked for.

## 8. The deploy lever (today, until Otto takes it)

https://github.com/chidionyema/idp/actions/workflows/deploy-when-green.yml — if it reads
disabled, press **Enable workflow** first; then **Run workflow**, keep branch `main`, press
**Run workflow** (the button only exists because the workflow declares `workflow_dispatch`,
line 49).
