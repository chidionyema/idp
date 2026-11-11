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
export HELM_INFERENCE_URL=https://ai-gateway.kilo.ai/api/v1/chat/completions
export HELM_MODEL=cohere/north-mini-code:free
# For an authenticated estate model route, provide HELM_TOKEN via managed secrets.
node experiments/helm/cli.mjs live
```

The GitHub Actions `helm-research` workflow runs a bounded 20-first-call, 5-task × 4-arm trial via Kilo's anonymous free-model route. Send public/synthetic benchmarks only: the free inference provider may record prompts and outputs. It writes the candidate and baseline outputs, per-call timings, schema/semantic decisions, token counts when provided and source SHA as a JSON artifact. A provider refusal, unavailable model, empty completion or timeout is reported separately and is never counted as an answer. The score reports knowledge and action fitness independently as well as strict joint correctness.

**Arms:** baseline; generic skills; evidence-only memory; HELM (bounded context + constrained action contract + syntax verification + one repair attempt). Prompt order alternates by task. Initial tasks are **known synthetic/replayed estate incidents**, not freshly executed fleet actions. This trial can establish the value of evidence injection on independently graded tasks, not production/fleet uplift or causal proof at scale.

## Scientific advance / falsifiers

- Does HELM outperform generic skill advice on held-out sequential agent tasks without leaking the answer from fixtures?
- Does runtime verification actually catch/fix more invalid actions, at what token/latency cost?
- Do lessons learned on one task generalise across other incidents, agents and models?
- Does provenance filtering prevent untrusted memory from becoming privileged instructions?
- Can Q4 collect genuine successful/failed paired trajectories, or does it mostly expose a lack of verified successes?

Do not train on the oracle file or copy task-specific labels into the prompt. Static fixtures are public and thus **not** a contamination-proof benchmark. Add genuine held-out tasks, independently produced grader outcomes, cross-model tests, agent-run trajectory capture and production-policy-blast-radius controls before promotion.

## Literature independently checked (11 November 2026)

- GitHub Models retired 2026-07-30: https://github.blog/changelog/2026-07-30-github-models-is-now-retired/ — its dead endpoint may return HTTP 200 with body OK.
- Kilo public free endpoint: https://kilo.ai/docs/gateway/authentication — anonymous free-model research traffic; rate limited, third-party data handling applies.
- Proxy-Tuning: https://arxiv.org/abs/2401.08565 — requires output-vocabulary predictions/logits; ordinary text-only closed endpoints do not provide this boundary.
- GEPA (ICLR 2026): https://proceedings.iclr.cc/paper_files/paper/2026/hash/0e9e708b6f48e14fd0ac29e167413f76-Abstract-Conference.html — reflection and prompt search as a sample-efficient learning candidate.
- Agent Lightning: https://arxiv.org/abs/2508.03680 — separates agent runtime and training, relevant to providers and frameworks.
- Agent Memory Distillation (EMNLP 2026): https://aclanthology.org/2026.findings-emnlp.2407/ — hierarchical memory can improve smaller tool-use agents in benchmark settings; numbers are study-specific, not HELM estimates.
- MemoryArena (ICML 2026): https://proceedings.mlr.press/v306/he26am.html — multi-session use of memory is harder than fact retrieval.
- SWE-bench-Live: https://swe-bench-live.github.io/ — recommends independent executable agent traces and leakage checks.

**Commercial:** no HELM product listing or performance claims until repeated credible agent-run outcomes justify them.

## Reproducibility counterexample

HELM-001 initially scored 2/3 joint passes against memory's 1/3, but the next independent run scored 0/3 against memory's 2/3. Model-provider errors and brittle lexical/opcode grading made this unstable. Source run IDs: 42951727380 and 42952186577. HELM-002 preregisters separate factual, opcode, schema, and joint metrics and introduces a previously unseen operations task. **None of these tiny experiments demonstrates a fleet-level effect or credible commercial uplift.**

## Live agent adapter: opt-in, source-aligned, no authority promotion

An existing estate agent may **opt into HELM** through `experiments/helm/agent-adapter.mjs`.
It consumes the real C1 ContextPlan (`items[]`, `plan_hash`, `provenance.commit`),
preserves the context engine's ordering, rejects a mismatched indexed commit, and emits
`helm.agent-proposal.v1`. It never executes the proposed action and always states
`independentlyVerified:false`. Authorized machine actions still go through the existing
YAML intent executor, and operational verification stays out-of-process.

```bash
# An authorized estate agent requests a ContextPlan from the existing compiler:
bin/estate-context-compile --task "inspect system task" --json > /tmp/helm-context-plan.json
# task.json contains { "id": "INS-...", "question": "...", "patchTarget": "...", "language": "python" }
# Internal model credentials must come from existing managed environment/secret infrastructure.
node experiments/helm/agent-adapter.mjs task.json /tmp/helm-proposal.json /tmp/helm-context-plan.json
```

**Critical data boundary:** an unauthenticated free provider is for public synthetic cases
only. The agent adapter explicitly refuses to send a real ContextPlan to that provider.
Never move actual private estate code, work instructions, or credentials to free models.
A response is a proposal, not an instruction grant, deployment, claim, or evidence of yield.

## Executable-code evaluation and robustness

`experiments/helm/functional-bench.mjs` compares **baseline, generic skills, memory,
memory+repair, and HELM**. Model-generated code is graded against Python unit tests,
not keyword matches, in a `--network none --read-only --cap-drop ALL` container with
memory, CPU, process and user limits. The oracle source is not sent to the model.

The `helm-verify` workflow is short and independent of third-party model availability:
23/23 runtime/adapter tests and all 24 reference/empty-patch two-sided grader checks
passed on 2026-11-11 in GitHub Actions run 42957465830. This proves that the research
harness is working; it does not prove HELM improves coding agents.

`helm-functional` is the slower model-evaluation workflow. Free-model availability,
rate limits, over-long internal reasoning, token budgets and provider errors are recorded
as failed or inconclusive attempts, never silently relabelled successful. A reference
solution passing and an empty patch failing each test suite is a necessary floor, not
a substitute for independent, larger, contamination-resistant benchmarks.

## Additional reviewed methodology

- SWE-Bench Pro V2 (2026-09-22): https://labs.scale.com/leaderboard/swe_bench_pro_public_v2
  — executable graders need both positive reference and negative empty-patch controls.
- OpenAI coding benchmark audit (2026-07-08):
  https://openai.com/index/separating-signal-from-noise-coding-evaluations/
  — strict/underspecified/low-coverage test sets distort agent performance estimates.
- TAME (EMNLP 2026): https://aclanthology.org/2026.emnlp-main.2100/
  — memory can degrade trustworthiness during evolution; independently evaluate reuse.
