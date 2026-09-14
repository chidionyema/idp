# Build: The Cognitive Stack — Epistemic Fabric, Neural Compiler, Inference Engine

Issue: https://github.com/chidionyema/idp/issues/3448
Written by pm-agent on 2026-09-14 from conversation with @chidionyema333@gmail.com.

## What the founder asked for

Founder's own words, verbatim:

Three layers, in order:

**Layer 1: The Epistemic Fabric (Knowledge Graph)**
- Ingestion: Redpanda or Kafka. Pipe GitHub webhooks, Slack exports, CI/CD telemetry,
  incident logs into topics.
- Storage: Memgraph (memory-first graph database, not a vector DB).
- Structure: every piece of data becomes a node with causal edges (e.g. PR #124 fixes
  Jira-99 -> temporal edge).
- Auto-Healer: a background LLM worker continuously reads the graph and checks it against
  live OpenTelemetry data; if the graph claims an edge (e.g. "Service A calls Service B")
  the traces don't show, the worker deletes the edge. Graph must be empirically true, not
  human-written.

**Layer 2: The Neural Compiler (Continuous LoRA)**
- Pipeline: Ray for distributed orchestration, Unsloth for training.
- Trigger: when a major node changes in the Knowledge Graph (e.g. a core API schema
  updates), Ray kicks off a background job.
- Output: trains a Rank-16 LoRA adapter (e.g. auth_api_v3_lora.safetensors) overnight from
  the graph's delta.

**Layer 3: The Inference Engine (Global KV-Cache)**
- Engine: vLLM or SGLang, both supporting RadixAttention (prefix caching).
- Setup: on deploy, the engine processes the estate's non-negotiable enterprise constraints
  once, computing a KV-cache matrix pinned in GPU VRAM.
- Execution: a new agent passes a UUID pointer to that cache, inheriting full enterprise
  context at zero input-token cost, and dynamically mounts the relevant LoRA (e.g.
  auth_api_v3_lora) in milliseconds to execute a patch, then unmounts it.

Founder has overridden discussion of the merits this session. Build exactly as specified.
Two prerequisites carry forward as tracked dependency line items, not objections:

- idp already has a graph layer at `catalog/estate.db` (the estate twin, `bin/estate-twin-runtime`)
  and provider-agnostic model routing via `sovereign/policy.py`'s `[routing]` block
  (minimax/groq/gemini/deepseek, `llm/config.yaml`). CP1 carries the decision line for the
  founder: does Memgraph become the new source of truth and `estate.db` migrates into it, or
  does Memgraph sit alongside it as a second store. Not a blocker — a decision the founder
  makes once, recorded on the issue.
- No GPU node pool exists in this estate for Ray/Unsloth training or vLLM/SGLang serving.
  `estate-defaults.yaml` caps `node_pool.budget_monthly_usd` at 50 total — a GPU pool is paid
  capacity above that cap, which is FOUNDER ACTION under the `capacity-requests-need-proof`
  admission policy and LAW 47, never a silent assumption. This is CP0, before any of the three
  layers can run anywhere but a laptop.

Every new namespace/workload carries the default-deny NetworkPolicy + ResourceQuota +
LimitRange (`bin/ns-fence-gate`) and a healthcheck naming a real object
(`bin/idp-healthcheck-exists`) — existing gates, not new ones. Every layer stays
provider/model agnostic: vLLM/SGLang serve open-weight models, no checkpoint couples to one
vendor's API.

Infra facts (`bin/idp-ticket-facts scheduling|llm|cluster-state --no-live`): posted verbatim
on the issue thread (crew#629 CP2) — never retyped here.

## Checkpoints

### CP0: GPU capacity request is FOUNDER ACTION and the Memgraph-vs-estate.db decision is recorded

`estate-defaults.yaml` caps total paid node-pool spend at `budget_monthly_usd: 50`; any GPU
pool is over that cap and is refused by `capacity-requests-need-proof` without founder sign-off.

Door (from the UI): Backstage → Catalog → `scheduling` component → the capacity-request issue
this checkpoint opens, showing FOUNDER ACTION with the exact monthly figure and the node shape
(A10/A100/etc) requested; the founder's reply on that issue is the record. The Memgraph-vs-
estate.db decision is recorded as a comment on this issue, not inferred from silence.

Define done before you start, in commands:
```
python3 bin/idp-cost-proof --check docs/specs/issue-3448.md   # cost-proof block present, before/after/command
gh issue view 3448 --json body,comments | grep -c "FOUNDER ACTION"   # >= 1
gh issue view 3448 --json comments | grep -c "Memgraph"              # decision recorded
```

### CP1: Ingestion — Redpanda/Kafka topics carry GitHub webhooks, Slack exports, CI/CD telemetry, incident logs

Door (from the UI): Backstage → Catalog → `epistemic-fabric-ingest` component → link **Open
topic list** → the Redpanda Console showing four topics (`github`, `slack`, `cicd`, `incidents`)
with a non-zero message count.

Define done before you start, in commands:
```
kubectl get kustomization epistemic-fabric -n flux-system -o jsonpath='{.status.conditions}'  # Ready=True
python3 bin/ns-fence-gate platform/epistemic-fabric   # default-deny NetworkPolicy + ResourceQuota + LimitRange present
python3 bin/idp-healthcheck-exists clusters/oke/platform.yaml epistemic-fabric   # healthcheck names a real object
rpk topic list --brokers <redpanda-svc>   # github, slack, cicd, incidents all present with lag=0
```

### CP2: Storage — Memgraph holds every ingested fact as a node with causal edges

Door (from the UI): Backstage → Catalog → `epistemic-fabric` component → link **Open graph** →
Memgraph Lab, a query `MATCH (n)-[e]->(m) RETURN count(e)` returns > 0 with at least one
temporal/causal edge type visible (e.g. `FIXES`).

Define done before you start, in commands:
```
python3 bin/ns-fence-gate platform/epistemic-fabric/memgraph
python3 bin/idp-healthcheck-exists clusters/oke/platform.yaml epistemic-fabric
echo 'MATCH (n)-[e]->(m) RETURN type(e), count(*)' | mgconsole --host <memgraph-svc>   # >=1 causal edge type, count > 0
```

### CP3: Auto-Healer — a background worker deletes a graph edge OpenTelemetry traces do not corroborate

Door (from the UI): Backstage → Catalog → `epistemic-fabric-healer` component → link **Open
worker logs** → a log line naming the deleted edge, the two nodes it joined, and the trace
query that found no corroborating span.

Define done before you start, in commands:
```
kubectl logs deploy/epistemic-fabric-healer -n epistemic-fabric --tail=200 | grep "edge deleted: no corroborating trace"
echo 'MATCH ()-[e:CALLS]->() RETURN count(e)' | mgconsole --host <memgraph-svc>   # count drops after a manufactured false edge + one healer cycle
```

### CP4: Neural Compiler trigger — a major graph node change kicks off a Ray job

Door (from the UI): Backstage → Catalog → `neural-compiler` component → link **Open Ray
dashboard** → a job appears in the Jobs list within one healer cycle of a major-node-change
event (e.g. a core API schema node's version property changing).

Define done before you start, in commands:
```
python3 bin/ns-fence-gate platform/neural-compiler
python3 bin/idp-healthcheck-exists clusters/oke/platform.yaml neural-compiler
ray job list --address <ray-head-svc>   # a SUBMITTED/RUNNING job appears within one cycle of the graph write
```

### CP5: Neural Compiler output — Unsloth trains a Rank-16 LoRA adapter from the graph delta, artifact named and stored

Door (from the UI): Backstage → Catalog → `neural-compiler` component → link **Open adapter
registry** → a new `*_lora.safetensors` artifact named after the triggering node, rank 16,
timestamped overnight.

Define done before you start, in commands:
```
python3 - <<'PY'
import safetensors, json
# rank check: adapter config lora_r == 16
PY
mc ls artifacts/lora-adapters/   # newest object named <node>_lora.safetensors, mtime overnight
```

### CP6: Inference Engine setup — vLLM/SGLang computes and pins a KV-cache matrix over the estate's enterprise constraints once, RadixAttention prefix caching live

Door (from the UI): Backstage → Catalog → `inference-engine` component → link **Open
metrics** → the vLLM/SGLang dashboard shows `prefix_cache_hit_rate` > 0 and one pinned
enterprise-constraints prefix in the radix tree.

Define done before you start, in commands:
```
python3 bin/ns-fence-gate platform/inference-engine
python3 bin/idp-healthcheck-exists clusters/oke/platform.yaml inference-engine
curl -s <vllm-svc>/metrics | grep prefix_cache_hit_rate   # non-zero after one warmup call
```

### CP7: Inference Engine execution — an agent's UUID pointer inherits the pinned cache at zero input-token cost, the relevant LoRA mounts and unmounts around one patch

Door (from the UI): Backstage → Catalog → `inference-engine` component → link **Open agent
trace** → a request trace showing the UUID cache pointer, the LoRA mount event, the patch
execution, and the LoRA unmount event, with `prompt_tokens` for the constraints prefix at 0.

Define done before you start, in commands:
```
curl -s <vllm-svc>/v1/completions -d '{"cache_id":"<uuid>","lora":"auth_api_v3_lora", ...}' \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["usage"]["prefix_tokens_billed"]==0'
kubectl logs deploy/inference-engine -n inference-engine --tail=200 | grep -E "lora mounted|lora unmounted"
```

