# Ruthless gateway: every agent's model call is constrained and judged before anyone sees it

**Status:** open
**Opened:** 2026-09-26
**Laws:** LAW 0 (one of each layer, AGENTS.md §6), THE EMPIRICAL PROOF RULE, ADR 0034
**Depends on:** the router's callback chain (`efficiency_gateway`, `request_ceiling`)

---

## What this is

The estate is an operating system of agents: headless agents, Hermes agents, the agent
workforce, the IDEs. Every one of them reaches a model through the router, and only through the
router. The router is therefore the one place where the estate's constraints can be put in
front of every model and every answer can be checked against them.

The founder's rules for it (2026-09-26):

- **Nothing is anchored.** No model is special and none holds a permanent seat. Which model
  answers, which model judges, the rules, the retry count, the token caps: all config in git,
  and any of them can change any of the others. No model name appears in code.
- **The judge answers yes or no.** It does not write critique.
- **Strict constraints, no flaky practice.** A check that can be skipped is not called a gate.

## Design

One router hook, `platform/llm/constitution_gate.py`, registered in `litellm_settings.callbacks`
beside `efficiency_gateway` (the founder chose this placement over a separate Go proxy). The router
already normalises every client shape and every provider, so the hook contains no vendor format
code and needs no new process.

Config (one file in git, read at router start):

| Key | Meaning |
|---|---|
| `constitution` | the rules, each with an id (`R1`, `R2`, …), injected as a system message into every call |
| `judge.models` | the pool the judge is drawn from; never the model that generated the answer |
| `judge.max_tokens` | per model, because models that reason before answering cannot be capped at 1 |
| `retries` | how many rewrites before the caller gets a refusal |
| `applies_to` | which routes, callers or model groups are judged (all, by default) |

The judge is **Jev** (ADR 0030), called through the JevLayer (`mcp/plugins/jev.py`), not a second
judge: `jev_choice` over the options `YES` / `NO <rule-id>`, which also returns a confidence.
Below the confidence floor counts as `NO`. Which backend Jev runs on is itself config, like everything else.

Verdict contract: the judge replies `YES` or `NO <rule-id>`. Anything else is `NO`
(fail closed). A `NO` sends the answer back to the generating model with the broken rule's text;
after `retries` the caller receives an error naming the rule, never an unchecked answer with a
warning banner. The judge being unreachable is also `NO`.

Streaming: an answer that streams to the caller cannot be judged before it is seen. Streamed
responses are judged after the stream ends and the verdict is recorded; they are reported as
*checked*, never as *gated*.

Every verdict is one log line: model, judge, verdict, rule, latency. That line is the proof it runs.

## What this is not

- Not a second router, not a Go proxy in front of the router (`bin/negative-constraints-proxy`
  exists; it refuses banned tool calls and is a separate layer).
- Not a guarantee. An LLM judging an answer is a check. The guarantee is that vendor keys exist
  only inside the router: in the cluster, `platform/calico/raw/deny-direct-ai-vendor-egress.yaml`
  drops every pod's packets to AI vendors except the router's; on the laptop, keys live only in
  the router's environment.

## Open facts (measured 2026-09-26)

| # | Fact | Consequence |
|---|---|---|
| 1 | The laptop router routes `claude-*` and three Ollama models only (`llm/config.base.yaml`) | Kimi is added as the first new pool entry; it is not a fixture |
| 2 | The laptop router's launcher, `bin/litellm-local`, is not on main (branch `fix/local-claude-max-router`, 7 commits ahead) | the hook can land on main, but the running laptop router does not load it until that branch lands |
| 3 | The cluster router (`llm/litellm`) is at 0 replicas; cluster agents (agent-workforce, otto-gateway) point at it | cluster agents are judged only once they reach a running router; ADR 0034 rung 5 places the gateway on the laptop |

## Jev everywhere, aggressively

Founder, 2026-09-26: "roll out jev aggressively across the platform", "any and everywhere",
"where possible and feasible". Jev is invoked at every decision point where a typed answer
with a confidence can replace a hand-written rule or a threshold. The gateway's judge is one of them.

Measured 2026-09-26: `docs/jev-capability-map.md` audits 50+ decision points across 8 repos. Three
call Jev today: `bin/idp-pr-risk`, `bin/idp-affected`, `sovereign/consensus`. The rollout converts
the rest, one PR per repo. A ratchet file lists the decision points not yet converted, and CI refuses
any PR that adds a line to it.

### Why Jev is not working now, and the fix for each (measured on the founder's laptop)

| # | Blocker | Fix |
|---|---|---|
| 1 | `TYPESAFE_API_KEY` is absent from the laptop environment and from `secret-load`; `platform/vendors/consoles.yaml` delivers it only to `mcp-gateway` and `dagster` | add a laptop target to the `typesafe` entry; the key arrives through the vault, by name |
| 2 | `jev.py` refuses to call unless `typesafe_sdk` imports, but the call uses plain `httpx` (installed, 0.28.1); the SDK is absent, so every call falls back | drop the import gate; gate on the key alone |
| 3 | the endpoint `https://api.typesafe.ai/v1/systemone` is a literal in code | `JEV_URL`, config |
| 4 | the ledger path defaults to `/data/estate.db`, which does not exist on the laptop; `~/.estate/estate.db` has no `jev_decisions` table | Jev has recorded zero decisions here; point `ESTATE_DB_PATH` at the laptop store and create the table on first write |
| 5 | idp-pr-risk and idp-affected run Jev before anything else, and today they fail open | once 1–4 land, they answer for real; that change is the first measurement |

## Real-time founder monitoring of all Jev activity

Every Jev call is published the moment it returns, including fallbacks, escalations and timeouts:
caller, decision id, question, answer, confidence, latency. The Fleet page shows them live as a
stream, not as a report. Transport: the estate's JetStream bus, subject `estate.jev.decision`,
the same bus voice uses. The `jev_decisions` table stays the record; the stream is what the
founder watches. A Jev call that is not published did not happen, as far as the founder can see.

## Done when

A production log line from the router shows a real agent's call judged: one `YES`, and one `NO`
that the generating model rewrote into a `YES`. Latency is reported as measured, not quoted.
The same verdicts appear live on the Fleet page as they happen, and `bin/idp-pr-risk` records a
real Jev answer (not `jev_unavailable`) in `jev_decisions`.
