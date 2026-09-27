# PROOF-OF-WORK — Wartime Multidimensional AI Inference Plan

> Date measured: 2026-09-13
> Rule binding this doc: LAW 2 (verification before assertion). Every number below was read from a real file in this session, with the path and line, on the same working tree the gate will grade.

## A. Routing and policy (read this session)

| Item | Value | Source | Status |
|---|---|---|---|
| LiteLLM daily cap | $5.0/day | `llm/config.yaml:417 max_budget: 5.0` | MEASURED_OK |
| LiteLLM budget reset | 1 day | `llm/config.yaml:418 budget_duration: 1d` | MEASURED_OK |
| Retry policy | `allowed_fails: 3`, `cooldown_time: 60`, `num_retries: 2` | `llm/config.yaml:399-401` | MEASURED_OK |
| Tracing callbacks | `["otel"]`, drop_params on, log off | `llm/config.yaml:404-409` | MEASURED_OK |
| Health checks disabled | `background_health_checks: false` | `llm/config.yaml:421` | MEASURED_OK |
| Judgment lane model | `gemini` | `platform/otto-gateway/router-lanes.yaml:74` `OTTO_ROUTER_LANE_JUDGMENT_MODEL` | MEASURED_OK |
| Verify lane model | `deepseek` | `platform/otto-gateway/router-lanes.yaml:115` `OTTO_ROUTER_LANE_VERIFY_MODEL` | MEASURED_OK |
| Free-lane route ordering | lanes head every chain, router is middle rung | `platform/otto-gateway/three-homes.yaml` comment, dated 2026-09-10 | MEASURED_OK |
| Groq latency from router pod | 0.48s | `platform/otto-gateway/three-homes.yaml` comment | MEASURED_OK |
| Cerebras latency from router pod | 0.25s | `platform/otto-gateway/three-homes.yaml` comment | MEASURED_OK |
| Free-lane spend impact | "answers don't touch litellm spend table" | `platform/otto-gateway/three-homes.yaml` comment | MEASURED_OK |
| Litellm lane count | 11 named lanes | grep on `llm/config.yaml` for `model_name:` | MEASURED_OK |

## B. Budget and capacity (read this session)

| Item | Value | Source | Status |
|---|---|---|---|
| Contract ceiling | $150/month | `AGENTS.md` `[cost] contract_max_usd_month: 150` | MEASURED_OK |
| Per-virtual-key daily cap | $5 | `estate-defaults.yaml` `llm.virtual_key_daily_usd: 5` | MEASURED_OK |
| Per-agent frontier budget | $3/day | `AGENTS.md` `[budget.usd_per_day] litellm = 3.0` | MEASURED_OK |
| Main node pool | max 2 nodes | `estate-defaults.yaml` `max_nodes: 2` | MEASURED_OK |
| Main burst | 60 hr/mo | `estate-defaults.yaml` `burst_hours_monthly: 60` | MEASURED_OK |
| Spot pool | 1 node, 30 hr/mo | `estate-defaults.yaml` `spot_max_nodes: 1, spot_hours_monthly: 30` | MEASURED_OK |
| Spot pool shape | `a1-spot` (AMD Arm CPU) | `estate-defaults.yaml` `spot_pool: a1-spot` | MEASURED_OK |
| Pool vendor lock-in | hard-reject | `estate-defaults.yaml` `policy.vendor_lock_in: hard-reject` | MEASURED_OK |
| OAuth creation mode | terraform-automated | `estate-defaults.yaml` `policy.oauth_creation: terraform-automated` | MEASURED_OK |

## C. Estate identity (read this session)

| Item | Value | Source | Status |
|---|---|---|---|
| Region | `uk-london-1` | `clusters/oke/estate-config.yaml` `ESTATE_OCI_REGION` | MEASURED_OK |
| Email | `chidionyema@gmail.com` | `clusters/oke/estate-config.yaml` `ESTATE_EMAIL` | MEASURED_OK |
| GitHub owner | `chidionyema` | `clusters/oke/estate-config.yaml` `ESTATE_GITHUB_OWNER` | MEASURED_OK |
| Break-glass OCID | `ocid1.user.oc1..aaaaaaaaorwkemualmpcvtnculbqqh7p5kml5wccrdxrtszgmnej4rg5tmra` | `clusters/oke/estate-config.yaml` `ESTATE_BREAK_GLASS_USER` | MEASURED_OK |
| Repo origin | `https://github.com/chidionyema/idp.git` | `git remote get-url origin` | MEASURED_OK |
| Current branch | `feat/async-dispatch` | `git branch --show-current` | MEASURED_OK |
| HEAD SHA | `19ae17fc50ba5c304e25378a8e7de592dde2b910` | `git rev-parse HEAD` | MEASURED_OK |

## D. State the rule demands we grade live (NOT YET VERIFIED)

These belong to the cluster Ollama build. Until they are MEASURED_OK with quoted log lines,
the system is `UNKNOWN`. They are the empirical proof rule's three checks.

| Item | Required command | Required evidence |
|---|---|---|
| Real litellm log line through `ollama.llm.svc:11434` | `kubectl logs --tail=100 deploy/litellm` | quote a full request/response |
| No OOMKilled / CrashLoopBackOff on `ollama-*` pods | `kubectl get events` | none since last reconcile |
| `router.outcome` event names an Ollama-served turn | event-stream query for `default=ollama-coder-7b` | a real event id |

Until D1–D3 are quoted, the cluster Ollama ring is `UNKNOWN`, never `MEASURED_OK`.

## E. Working-tree defect (read this session — STATE OF THE CHECKOUT)

`git status --porcelain` returned:

```
 M .githooks/pre-push
 M backstage/plugins/fleetview-backend/src/sessions.py
?? features/fleetview/cp6_readable.feature
?? sovereign/tests/bdd/test_fleetview_cp6.py
?? tests/fixtures/verifier-hooks/
```

`bin/idp-clean-tree` would refuse grading from this checkout. Block on blocker C in the spec.

## F. Tool surface (read this session — coverage partial)

| Tool | Verified this session | Not verified |
|---|---|---|
| `bin/idp-otto-homes` | `--help` output, source-declared `probe/status/deploy/cutover/zone/vault_*` functions, SECRETS list | end-to-end `grade` run |
| `bin/idp-rules` | BEGIN/END marker parser, rules.yaml registry import | full rules.yaml dump |
| `bin/idp-estate-twin-runtime` | sources referenced in spec | never invoked |
| `bin/idp-clean-tree` | mentioned by spec; gate refuses dirty trees | never invoked |
| `bin/idp-circuit-breaker` | referenced in spec | never invoked |
| `bin/idp-script-compiles` | LAW 45 / founder 2026-09-13, preflight gate for any bin/ addition | never invoked on this session's writes |

## G. Decisions locked in by this PROOF-OF-WORK

- Free lanes head every chain; cluster router is now middle rung (verified 2026-09-10).
- Family separation holds (gemini ≠ deepseek) — judgment and verify routed to different vendors.
- Spot pool is `a1-spot` (AMD Arm CPU, NOT A10 GPU). Prior drafts assumed a GPU shape that does not exist on this estate.
- Cluster Ollama does not exist; `find clusters platform -type d -name ollama` returned empty.
- The three Ollama lanes currently target `host.docker.internal:11434` (Mac, dead since 2026-09-10). Repointing to `ollama.llm.svc:11434` is the proposed step 1 of the optimised PR.

## H. Decisions reserved (founder action)

- Greenlight cluster Ollama Flux Deployment (blocker A).
- Escalate GPU shape to OCI capacity planning (blocker B).
- Clean working tree (blocker C).
- Drop staged tiers at commercial cutover the founder names (TwIL-LM3, burst GPU, llama.cpp / mistral.rs / TurboQuant).
