# 0031 — The Continuous Intent Engine reuses the reactor. No second orchestrator, no model in code.

- Status: DECIDED 2026-09-20
- Deciders: founder
- Extends: 0025 (the Greenlane grows by rows, never a second path), 0023 (the boundary is enforced
  by the infrastructure), 0006 (the platform answers for itself over one MCP)
- Governs: `platform/intent/observer.py`, `bin/observer`, `schema/intent/action-contract.schema.json`,
  `backstage/plugins/fleetview-backend/src/{routes,serve}.py`, and any future work that turns a
  spoken request into a tracked contract.
- Source: the founder's external consultant's blueprint, 2026-09-20, and
  `docs/specs/2026-09-20-fleet-2100-hud-architecture.md` (same day, same consultant), which the
  blueprint contradicts in three places. Where they disagree, THE SPEC WINS: it was written against
  this estate, and the blueprint was written against a generic OKE stack.

## The instruction

The founder asked for a Continuous Intent Engine: a spoken request becomes an Autonomous Action
Contract, drafts its own BDD specs, spawns workers, and broadcasts progress to the HUD.

Three parts of the consultant's blueprint are refused, and the refusal is the decision:

### 1. No LangGraph, no Temporal. The orchestrator already exists.

The blueprint says *"Deploy Temporal.io or LangGraph on OKE"* and *"Instead of full Temporal ...
deploy LangGraph within a FastAPI Python pod."*

The spec says *"it manifests through the existing `requestAnimationFrame` loop"*. The estate also
already runs a reactor (`bin/reactor-standalone`, `backstage/.../FleetReactorApp.tsx`) with a gate
on its CSS. A second orchestrator is a second copy of a layer, and AGENTS.md §6 says a second copy
is stitching and gets deleted. This is ADR 0025's rule about the merge path applied to the
orchestration path: **the estate grows a row in the mechanism it has, never a parallel one.**

The contract is a row. The reactor already knows how to render rows. Nothing is deployed.

### 2. No Redis. The state is in the database that already owns it.

The blueprint says *"Use a lightweight Redis container on OKE to store the real-time state."*

`catalog/estate.db` is described in the estate's own words as THE HEADLINE, extended and never
duplicated (`signals.py`), and the 2100 spec §3 already names the table to extend:
`fleetview_signals`. A Redis container would be a second state store for state that has an owner,
on a free tier where the RAM is the constraint the blueprint itself is trying to respect.

Contracts live in `action_contracts`, beside `fleetview_signals`, in the same file.

### 3. No model named in code. The model is configuration.

The blueprint names Llama-3-8B, GPT-4o-mini, Claude-3.5-Sonnet and GPT-4o as routing targets.

AGENTS.md §0.1: no feature depends on a model, a provider or a vendor. `LITELLM_OBSERVER_MODEL` is
read at call time; an empty value is a REFUSAL (exit 1), never a default. The router is addressed by
name through `LITELLM_URL`, and the key arrives by environment variable name only (AGENTS.md §4).

## What was measured, not assumed

The blueprint's sketch was written against imagined interfaces. Each of these was checked against
the code before any of it was built:

| blueprint says | the estate actually has |
|---|---|
| SSE from `:8770/stream` | a WebSocket at `/voice/stream` (`sovereign/voice/server.py`) |
| insert four columns into `fleetview_signals` | `kind`, `by`, `ok`, `created_at` are all NOT NULL |
| a `latency_ms` field on the transcript frame | `asr_seconds`; latency already lives in `voice_turns` |
| `catalog/sql/patches/*.sql` migrations | no such directory; schema is born in `signals.py` |
| `APIRouter` + `get_db_connection` appended to `signals.py` | `signals.py` has neither; `routes.py` owns paths, `serve.py` mounts them |

The last row matters most: an SSE client against that ingress gets a 404, and the four-column insert
raises on the FIRST spoken request. Both were found by tests that drive a real SQLite file, which is
why the tests exist rather than a manual smoke test.

## The address phrase is not optional

The spec §5 calls *"the illusion of seamless voice control while hiding the raw transcript"* the
single biggest lie, and §3 says addressing agents by loose string match is a broken paradigm. So:

- the trigger is a PREFIX, not a substring — "the agents are all down" is a remark ABOUT the fleet
  and must never fire a contract;
- the heard transcript is echoed BEFORE synthesis, and an unaddressed utterance is still recorded as
  a `transcript` signal, so what was misheard or ignored is visible rather than a black box.

## Consequence for the next person

Adding a workflow engine, a message broker, or a second state store to deliver this feature is a
regression against this decision. The executor for a contract is the estate's existing session/agent
spawn, keyed by `contract_id` — wiring it is a new row in the existing executor, not a new daemon.
