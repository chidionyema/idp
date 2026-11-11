# HELM — estate cognitive exocortex research experiment

**Claim:** idp#7908. **Mode:** internal RESEARCH. **Order:** Chesed first (build and run), Geburah second (falsify, learn). Nothing in this directory is promoted as a commercial product or deployed as an autonomous execution authority.

## Executable architecture

- **Q1 / Context** — consumes an existing `estate-context-compile` plan and provenance-tagged memory. Builds a scoped, bounded, integrity-checkable seal. It does not introduce a new graph, index or independent memory authority.
- **Q2 / Action cortex** — validates typed model proposals against the fixed opcode interface; never executes a proposed shell command. The actual estate intent executor remains the only action authority.
- **Q3 / Shadow verifier** — locally parses Python proposals with AST, rejecting syntax errors and bare exceptions. This is static verification, *not* runtime proof of correctness. A bounded repair pass can feed the static error back to the model.
- **Q4 / Experience distillation** — generates preference *candidates* only from linked rejected and independently verified preferred trajectories. It does not claim to train a model, modify weights or make a cloud model inherently compliant.

`GENESIS_HELMET.dna` from the attached proposal is **not** a magic 4 KB intelligence transfer. HELM's seal is an actual size-enforced, SHA-256 integrity-checked portable compressed context bundle, and is always subordinate to the installed runtime's authorization rules.

## Immediate operations

```bash
node --test experiments/helm/helm.test.mjs
node experiments/helm/cli.mjs compile
# Connect the existing estate context compiler; it owns selection:
bin/estate-context-compile ... > /tmp/estate-context.json
node experiments/helm/cli.mjs from-compiler /tmp/estate-context.json

# Explicitly provisioned model route (GitHub Actions uses built-in models:read):
export HELM_INFERENCE_URL=https://models.github.ai/inference/chat/completions
export HELM_TOKEN=...      # supply via a managed secret; never commit or echo it
export HELM_MODEL=openai/gpt-4.1-mini
node experiments/helm/cli.mjs live
```

The GitHub Actions `helm-research` workflow runs those tests and a bounded 12-call, 3-task × 4-arm trial on the research branch using its ephemeral `GITHUB_TOKEN`. It writes the candidate and baseline outputs, per-call timings, schema/semantic decisions, token counts when provided and source SHA as a JSON artifact. A provider refusal or missing token is reported, not counted as a successful trial.

**Arms:** baseline; generic skills; evidence-only memory; HELM (bounded context + constrained action contract + syntax verification + one repair attempt). Prompt order alternates by task. Initial tasks are **known synthetic/replayed estate incidents**, not freshly executed fleet actions. This trial can establish the value of evidence injection on independently graded tasks, not production/fleet uplift or causal proof at scale.

## Scientific advance / falsifiers

- Does HELM outperform generic skill advice on held-out sequential agent tasks without leaking the answer from fixtures?
- Does runtime verification actually catch/fix more invalid actions, at what token/latency cost?
- Do lessons learned on one task generalise across other incidents, agents and models?
- Does provenance filtering prevent untrusted memory from becoming privileged instructions?
- Can Q4 collect genuine successful/failed paired trajectories, or does it mostly expose a lack of verified successes?

Do not train on the oracle file or copy task-specific labels into the prompt. Static fixtures are public and thus **not** a contamination-proof benchmark. Add genuine held-out tasks, independently produced grader outcomes, cross-model tests, agent-run trajectory capture and production-policy-blast-radius controls before promotion.

## Literature independently checked (11 November 2026)

- Proxy-Tuning: https://arxiv.org/abs/2401.08565 — requires output-vocabulary predictions/logits; ordinary text-only closed endpoints do not provide this boundary.
- GEPA (ICLR 2026): https://proceedings.iclr.cc/paper_files/paper/2026/hash/0e9e708b6f48e14fd0ac29e167413f76-Abstract-Conference.html — reflection and prompt search as a sample-efficient learning candidate.
- Agent Lightning: https://arxiv.org/abs/2508.03680 — separates agent runtime and training, relevant to providers and frameworks.
- Agent Memory Distillation (EMNLP 2026): https://aclanthology.org/2026.findings-emnlp.2407/ — hierarchical memory can improve smaller tool-use agents in benchmark settings; numbers are study-specific, not HELM estimates.
- MemoryArena (ICML 2026): https://proceedings.mlr.press/v306/he26am.html — multi-session use of memory is harder than fact retrieval.
- SWE-bench-Live: https://swe-bench-live.github.io/ — recommends independent executable agent traces and leakage checks.

**Commercial:** no HELM product listing or performance claims until repeated credible agent-run outcomes justify them.
