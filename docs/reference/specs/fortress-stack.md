# Fortress stack: LiteLLM, Langfuse/OTel, SPIFFE, MCP, AGENTS.md inside idp

Written by pm-agent on 2026-08-24 from a conversation with the founder. Tracked at
`chidionyema/crew` issue (number filled in once `crew plan` opens it — see the
issue link this doc is committed alongside).

## The founder's ask, in his own words (tidied)

He wants the estate to pass an acquirer's technical diligence on five rows, plus
one thing fixed first:

1. **Model routing** — LiteLLM as the universal API/abstraction layer, fallback
   chains, per-agent cost logging. Every agent's base URL points at LiteLLM.
2. **Observability & audit** — OpenTelemetry GenAI instrumentation on agent code,
   routed to Langfuse, giving an immutable audit trail (cost, latency, tokens,
   tool invocations) for EU AI Act diligence.
3. **Agent identity** — SPIFFE/SPIRE issuing short-lived cryptographic identities
   to agents as non-human identities.
4. **Protocols** — official MCP Python/TypeScript SDKs replace the proprietary
   board schema; agents reach SQLite and internal tools through MCP; Agentgateway
   secures the agent-to-tool connection.
5. **Living specs** — AGENTS.md as the version-controlled boundary/rules format.

All of it inside docker-compose, for portability. And, ahead of all five: **fix
the database today** — the catalog database behind `bin/idp-verify` must be
green, because a buyer's engineer runs that command before he reads a single row
of this doc.

## Where this lives, and where it does not

Per `~/AGENTS.md` headline: one platform, `~/dev/code/idp`. Every row below is a
platform layer and lives here — `llm/`, `observability/`, the new `mcp/` and
`identity/` directories, `AGENTS.md` at the repo root. Nothing here is a second
repo. `prospector` and `hermes-v2` stay products; they are onboarded onto these
layers (a config value pointing at LiteLLM's URL, a `catalog-info.yaml` entity,
traces landing in the shared Langfuse), never given their own copy.

## Measured state, 2026-08-24 — do not re-measure without a fresh command

```
$ bin/idp-verify
source    237 entities in catalog-info.yaml
schema    237/237 entity documents valid against https://json.schemastore.org/catalog-info.json
FAIL      fallback serves 'none', expected 237 (db has 236, HTTP 000000)
SKIP      primary (Backstage backend on 7107 is not answering)
FAIL

$ bin/litellm-status
PROXY      LOCAL              HTTP   BASE URL FOR EVERY AGENT
litellm    127.0.0.1:4000     down   http://127.0.0.1:4000/v1
CONTAINERS  none running

$ bin/langfuse-status
RECEIVER   LOCAL                     HTTP   ENDPOINT
primary    127.0.0.1:3200 langfuse   down   http://127.0.0.1:3200/api/public/otel
fallback   127.0.0.1:4318 otel-col   200    http://127.0.0.1:4318
```

STANDARDS.md (crew repo): row 25 — LiteLLM is a **CANDIDATE**, importable in 0
venvs, imported by 0 files. Row 26 — Langfuse traces are **partially live**. Row
21 — job monitoring (Healthchecks) is **to adopt**, already tracked at
crew#177; not duplicated here.

No SPIFFE/SPIRE process runs anywhere on the estate. No Agentgateway. No MCP
server exists for the board or for `catalog/estate.db` — `~/.claude/mcp/` holds
one unrelated bridge (`pi_bridge.py`, dispatches work to a `pi` CLI, not an MCP
tool surface). `hermes-v2/config.yaml` already references `litellm`, ahead of
LiteLLM actually running.

## Checkpoints

### CP1 — Data: the catalog database is green (fix it first, LAW 1)

`bin/idp-verify` fails today because the fallback Datasette renderer on
`127.0.0.1:8001` is not answering (`HTTP 000000`) and the row counts disagree
(YAML 237, db 236). This is not a governance-stack problem; it blocks every row
below, because a buyer who runs `idp-verify` and sees FAIL never reads the rest
of the diligence. Engineering finds the `db-gen`/Datasette cause; this doc does
not prescribe it.

**Done when:** `bin/idp-verify` last line is `PASS`.

### CP2 — Model routing: LiteLLM is the universal base URL

LiteLLM compose (`llm/litellm.yml`, `llm/config.yaml`, `bin/litellm-up`) already
exists and is docker-compose-native; it has never been started, and STANDARDS
row 25 correctly grades it CANDIDATE, not live. Turning it live means: the proxy
answers, its router config carries a real fallback chain, spend logging is on,
and at least the two agents already configured for it (`hermes-v2`) plus
`prospector`'s `operator.py` factory point their base URL at
`http://127.0.0.1:4000/v1`. `claude_cli` and `gemini_cli` stay outside it on
purpose — they run on a subscription, not an API key, and `bin/litellm-status`
already documents that exclusion.

**Done when:** `bin/litellm-status` shows the proxy `up`, HTTP `200`, and at
least one configured fallback chain; `grep -rl '127.0.0.1:4000'` across agent
configs finds every non-CLI agent; STANDARDS row 25 is edited from CANDIDATE to
live in the same PR that flips the proxy on.

### CP3 — Observability & audit: OTel GenAI traces reach Langfuse

Langfuse's containers already run (`observability/langfuse.yml`); the primary
receiver on `3200` is down while the OTel fallback on `4318` answers and writes
to `/data/traces.jsonl` — STANDARDS row 26's "partially live" is exact. Closing
it means the primary comes up, an agent's real run produces a trace carrying
cost, latency, token counts and tool invocations, and that trace is queryable
through Langfuse's API — the artifact an EU AI Act audit actually asks for.

**Done when:** `bin/langfuse-status` shows primary `200`; a queried trace from a
real agent run has non-null cost, latency, token and tool-call fields; STANDARDS
row 26 moves from partially live to live.

### CP4 — Agent identity: SPIFFE/SPIRE, and why it is deferred

**Strict bar verdict: defer to the k8s exit (crew#78). Adopting it now does not
raise the bar — it lowers confidence in the diligence.**

SPIFFE/SPIRE's value is a control plane (SPIRE Server) attesting SPIRE Agents
running on *separate nodes*, so a workload's identity is proven by where and how
it was scheduled — a k8s ServiceAccount projected token, a cloud instance
identity document, something the node itself cannot forge. This estate is one
laptop (`laptop-is-the-substrate-until-k8s`, memory). There is no second node to
attest against. Standing up a SPIRE Server and a single SPIRE Agent on the same
machine that runs everything else means the attestation boundary is "trust
this laptop to attest itself" — which is exactly the credential the laptop
already holds. A diligence engineer who finds a SPIRE server with one attested
agent does not read "cryptographic identity"; he reads a control plane running
for show, and that is worse than not having the row. Building it now is the
half-stitched habit the headline names, not the fix for it.

The interim, honest control: every agent already gets a distinct secret from
the sops+age vault (STANDARDS row 24) and, once CP2 lands, a distinct API key
scoped in LiteLLM's router config — that is this estate's actual non-human
identity boundary today, and it is recorded here rather than left implicit.
SPIFFE/SPIRE is the documented, correct tool for the day node attestation is
real, which is the k8s exit. This checkpoint's deliverable is the deferral
decision landing on crew#78, not a running SPIRE process.

**Done when:** crew#78's body records the SPIFFE/SPIRE decision and the interim
per-agent-key control; `docker ps` shows no `spire` container anywhere on the
estate.

### CP5 — Protocols: MCP SDK and Agentgateway, adopted now

**Strict bar verdict: adopt now, scoped to the board and `estate.db`. This does
raise the bar — the gap it closes is present today, not hypothetical.**

No MCP server exists for the crew board or for `catalog/estate.db`; agents that
touch either do so through ad hoc scripts and a proprietary board schema
(`crew/crew/board.py`'s hand-parsed issue body). The official `modelcontextprotocol/python-sdk`
(24.1k stars, actively maintained, not archived) replaces that schema with a
protocol other tools already speak, which is what a buyer's own tooling will
expect to plug into.

Agentgateway is different from SPIRE in exactly the dimension that matters
here: it has a standalone, non-k8s runtime (a single compose service in front
of the MCP servers), and the gap it closes — zero authz or audit at the hop
between an agent and a tool server — exists the moment CP5's MCP servers exist,
with or without k8s. Running it standalone means its policy config is static
YAML rather than the CRD-driven dynamic policy it gets under a k8s Gateway API
control plane; that richer mode is deferred to the k8s exit alongside CP4, but
the baseline of "every MCP call passes through one auditable, authenticated
proxy instead of none" is available today and is adopted now, scoped narrowly
to fronting the MCP servers this checkpoint builds — not stood up as a general
service mesh.

**Done when:** an MCP server built on the official SDK exposes the board and
`estate.db` as MCP tools; `docker compose -f idp/mcp/agentgateway.yml ps` shows
it running; a tool call for each server round-trips through Agentgateway and
returns 200.

### CP6 — Living specs: AGENTS.md as the version-controlled boundary

`idp` carries no `AGENTS.md` of its own today — only the estate-wide
`~/AGENTS.md`, which is machine-global and not a git artifact of this repo. This
checkpoint adds a project-scoped `AGENTS.md` at the repo root: the boundary and
rules this repo's agents work under, committed like any other source file, with
a gate (pre-commit, per STANDARDS row 40's `repo: local` pattern already ruled
for this exact class of guard) checking an agent-authored diff against it before
it lands.

**Done when:** `git show HEAD:AGENTS.md` in `idp` is non-empty; the gate that
reads it runs in CI or pre-commit and is shown passing and refusing in the same
run (LAW 45's both-ways proof).

## What this doc does not do

It does not fix CP1's root cause, does not flip LiteLLM or Langfuse on, does not
write the MCP server or the AGENTS.md gate. Those are engineering's checkpoints,
tracked and ticked only by `crew verify` against the feature files in
`features/fortress/`.
