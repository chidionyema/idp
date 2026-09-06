# Model Forge and Edge Runtime — two platform capabilities, one artifact between them

**Status:** v1 spec, building. **Date:** 2026-09-06. **Tracked:** crew#885.
**Founder records (verbatim, the file is the record):**
`~/.claude/docs/founder/2026-09-06T0740Z-3-the-4-step-playbook-to-cut-reliance-d75d416a.md`,
`~/.claude/docs/founder/2026-09-06T0741Z-5-src-tier2-rs-arm-native-local-inference-e410c62e.md`,
`~/.claude/docs/founder/2026-09-06T0750Z-that-distinction-changes-everything-and-separating-those-two-0a0fa055.md`,
`~/.claude/docs/founder/2026-09-06T0755Z-also-work-is-already-underway-for-the-voice-ec3c584d.md`.
**Roles:** this session leads (spec, review, integration, proof); Gemini web is the contractor and
writes most of the code from the briefs in section 7.
**Convention:** every checkpoint ends in a command that proves it (LAW 33); done means live proof
on the OKE node, never a quoted number (empirical proof rule).

---

## 0. Contract

Two capabilities, decoupled by one artifact. The Forge never serves; the Runtime never trains.
A tenant is a task: it brings examples, gets back a model artifact, and calls the Runtime.

| Capability | What it is | Standing cost |
|---|---|---|
| **A. Model Forge** | An offline, repeatable workflow: task examples in, quantized model artifact out. Runs on an ephemeral GPU that terminates when the run ends. | 0 |
| **B. Edge Runtime** | A memory-safe Rust service on the estate's ARM64 nodes that loads an artifact and answers single-task inferences, with an abstain signal for the paid fallback. | the pod |

The artifact (section 3) is the whole interface. A tenant can swap either side without touching
the other.

### Measured on 2026-09-06, the ground this stands on

- Spend: `SPEND_VELOCITY: last hour 704 calls, 45899540 tokens, $9.0993` (job
  `spend-velocity-check-29811340`, namespace `llm`) against a $150/month contract. By key, all
  time: laptop $43.0, agent-workforce $21.9, k8sgpt $3.3. By model: moonshot/kimi-k3 $35.9,
  deepseek-v4-flash $26.2.
- Nodes: two `arm64`, 6 CPU, 24 GB each (Oracle A1). No GPU anywhere in the estate.
- The laptop is an Intel i7-8850H with 16 GB. It cannot train (no MLX, no GPU); it can run
  the Runtime's tests.
- Image pipeline: `.github/workflows/build-multiarch.yml` already builds `linux/arm64` on
  `ubuntu-24.04-arm`. The Runtime reuses it.
- Prior planning: crew#513 CP6 said "distillation only if CP4 shows a gap the compiled prompt
  cannot close". The founder's 2026-09-06 records supersede that: own models are a product line.

## 1. Non-goals

- No agentic loops on local models. The Forge targets narrow, repeated tasks with a label or a
  schema as output. The crew's planning and grading loops stay on the router.
- No second scheduler, secret store, trace backend or registry. Runs are Dagster jobs, secrets
  come from the one vault, traces land in the estate collector, artifacts live in GHCR.
- No 15 ms promise in a document. Latency is a number the Runtime prints from the A1 node.

## 2. Capability A — Model Forge

**Buy, not build (LAW 43, sources in section 9):**

| Step | Tool | Why |
|---|---|---|
| Launcher | Modal (Starter plan, $30/month credits renew; per-second billing, scale to zero) | Ephemeral GPU with zero standing cost; a T4 is about $0.59/hour, so a 15-minute LoRA is under $0.15 and the free credits cover 100+ runs a month. Fits R14 (free tier) and the founder's "under $0.50 a run". Code-driven, no console step (R52). |
| Trainer | Unsloth (LoRA/QLoRA on Qwen3 0.6B and 1.7B, direct GGUF export `q4_k_m`) | One library does train, merge and export; T4 is a supported target. |
| Data | Langfuse datasets (teacher outputs are already stored as traces) | No re-generation of what the estate already paid for. |
| Artifact store | GHCR as an OCI artifact, pushed with `oras` | Same registry as every image; the image pipeline already authenticates to it. |

**Provider-agnostic (LAW 34):** `forge/train.py` is a plain script that runs on any CUDA box.
`forge/modal_app.py` is only the launcher. A second launcher (Kaggle, a rented box) is a file,
not a rewrite.

**Run shape:** `dataset.jsonl` (prompt, completion, split) → LoRA on the base named in
`task.yaml` → merge → GGUF `q4_k_m` → held-out eval against the teacher labels → artifact push
→ Langfuse trace of the run (LAW 50) → a comment on the tenant's ticket with the eval table.

**Refusals:** a run whose held-out agreement with the teacher is below `task.yaml: min_agreement`
pushes nothing and says why. A dataset under 500 examples is refused.

## 3. The artifact — the contract between A and B

An OCI artifact `ghcr.io/chidionyema/models/<task>:<version>` holding exactly:

```
model.gguf          # q4_k_m, merged, base named in the card
model-card.yaml     # the contract below
eval.json           # held-out numbers the Forge measured
```

```yaml
# model-card.yaml
task: voice-gate            # tenant id
base: Qwen/Qwen3-0.6B
kind: classify              # classify | extract
prompt_template: |          # exact text the Runtime renders, {input} is the only placeholder
  Classify as customer ready (0) or internal engine leak (1).

  Text: {input}

  Verdict:
labels:                     # classify: first-token candidates the Runtime compares
  "0": customer_ready
  "1": internal_leak
abstain_below: 0.80         # softmax margin under which the Runtime answers abstain
schema: null                # extract: JSON Schema the Runtime validates against
eval: { held_out: 500, agreement: 0.97, abstain_rate: 0.06 }
```

## 4. Capability B — Edge Runtime

Rust, in `platform/edge-runtime/`. It is a separate crate from `platform/voice-gate/`; Voice
Gate calls it over loopback for its Tier 2 verdict and keeps its own Tier 1 rules.

- **Engine:** `candle-core` + `candle-transformers::quantized_llama` loading the GGUF by mmap;
  CPU device; the arm64 build sets `target-cpu=neoverse-n1`.
- **Classify:** render the template, one forward pass over the prompt, read the logits of the
  next token for each label's first token, softmax over those candidates only. Answer
  `{label, p, margin, latency_ms}`; `abstain` when `margin < abstain_below`.
- **Extract:** bounded generation with a JSON grammar, validated against `schema`; `abstain` on
  a validation failure.
- **API:** `POST /v1/infer {task, input}`, `GET /v1/health` (loaded tasks, artifact digests,
  p50/p95 over the last 1000 calls), `GET /metrics`. Binds loopback only (R20); the gateway
  fronts it.
- **Artifacts:** pulled at start from GHCR by digest pinned in the ConfigMap; a pull failure
  keeps the previous artifact and reports it on `/v1/health`.
- **Telemetry:** every call is a span to the estate collector with task, label, margin,
  latency (LAW 50). Abstains are counted; the count is the paid-fallback bill.
- **Fallback:** the caller, not the Runtime, sends an abstain to the LiteLLM alias for the
  task. The Runtime never holds a router key.
- **Honest sizing:** a 0.6B Q4 model is about 400 MB; 1.7B about 1.1 GB. The image is the
  binary plus nothing; the artifact is a volume, not a layer. Cold start is the mmap of that
  file, measured, not "microseconds".

## 5. Tenants

| Tenant | Task | Output | Source of examples |
|---|---|---|---|
| 0 Voice Gate | customer-ready vs internal leak on storefront and portal copy | label | ombudsman rulings, the leak scrub of Phase 0 |
| 1 Triage | route an incoming issue or ticket to a lane | label | crew ticket history with lane labels |
| 2 Extraction | messy listing text to a strict JSON schema | JSON | prospector listings with teacher extractions in Langfuse |
| 3 PR review | flag the estate's own anti-patterns before a human reads the diff | label + span | the AGENTS.md gates and their fixtures |

Tenant 0 goes first because its examples exist today and its cost is a leak on a public site,
not a token bill.

## 5a. Overlap with the Voice Gate session (record 0755Z)

Another session owns Voice Gate: the Python bleed-stop and oracle, the Rust Tier 1 crate, the
conformance suite, the `VOICE_GATE_IMPL=rust` flip, and the GLiNER/Extism product image. The
split, so neither side does the other's work twice:

| Work | Owner |
|---|---|
| Python sanitizer, export scripts, storefront JSON scrub, Vale removal | Voice Gate session |
| Tier 1 Rust rules, Python-vs-Rust differential fuzz, golden samples | Voice Gate session |
| Tier 2 model: the 100-string labelling grows into Tenant 0's dataset (section 5) | Voice Gate labels, Forge trains |
| The llama.cpp vs candle benchmark on the A1 shape (their Phase 2) | this spec's CP4; one benchmark, numbers shared on crew#885 |
| Serving the Tier 2 model on the node | Edge Runtime, this spec |

Voice Gate's Phase 2 benchmark and this spec's CP4 are the same measurement. It runs once, here,
and the Voice Gate session reads the numbers from the ticket rather than running its own.

## 6. Checkpoints (each ends in the command that proves it)

- **CP0 Bleed.** Per-key `max_budget` with `budget_duration` in LiteLLM for `agent-workforce`
  and `laptop`; the workforce loop no longer regrades a red PR. Proof:
  `bin/idp-kube -n llm logs job/<next spend-velocity-check> | grep 'within limits'`.
- **CP1 Forge smoke.** `modal run forge/modal_app.py --task voice-gate --dry-run` trains on a
  200-example fixture and exits with an eval table and no push. Proof: the run's Langfuse
  trace id in the PR.
- **CP2 First artifact.** `oras pull ghcr.io/chidionyema/models/voice-gate:v1` yields the three
  files; `eval.json` agreement at or above `min_agreement`.
- **CP3 Runtime on the laptop.** `cargo test` green; `curl 127.0.0.1:8421/v1/infer` on the
  fixture answers with a label and a margin.
- **CP4 Runtime on the node.** Pod 1/1 in namespace `edge-runtime`; `/v1/health` prints p50 and
  p95 from real calls; `bin/idp-kube get events -n edge-runtime` shows no restart. The numbers
  go in the ticket. This is the first time a latency is written down.
- **CP5 Tenant 0 live.** Voice Gate Tier 2 calls the Runtime; the fallback share from the spend
  logs is under 15 percent over one day.
- **CP6 Forge as a tool.** A new tenant is a `task.yaml` and a dataset, one Dagster job, no new
  code. Proof: tenant 1 ships from the button with no PR to the Forge.

## 7. Contractor briefs (Gemini web)

Each brief is one PR. Constraints on every PR: no literal path, host, account or key (LAW 46);
loopback bind only (R20); every claim in a comment carries its receipt; tests grade behavior,
never prose (R76); `bin/idp-ci` green.

**Brief A — `forge/`** (Python 3.12):
1. `forge/task.yaml` schema: `task, base, kind, prompt_template, labels|schema, abstain_below,
   min_agreement, lora: {r, alpha, epochs, lr}`.
2. `forge/train.py`: Unsloth LoRA on `base`, dataset from a JSONL path, merge, export
   `model.gguf q4_k_m`, write `model-card.yaml` and `eval.json` (held-out agreement,
   abstain rate at `abstain_below`). Refuse under 500 examples or under `min_agreement`.
3. `forge/modal_app.py`: Modal function on a T4, mounts `forge/`, secrets from Modal's secret
   store named `estate-ghcr` and `estate-langfuse`, calls `train.py`, pushes with `oras`,
   emits one Langfuse trace with the eval table.
4. `forge/export_langfuse.py`: Langfuse dataset name in, `dataset.jsonl` with a deterministic
   80/20 split out.
5. `forge/tests/`: `train.py` on a 50-example fixture with a 10-step budget must produce the
   three files; the refusals must fire.

**Brief B — `platform/edge-runtime/`** (Rust 2021, axum 0.7, candle 0.8):
1. `artifact.rs`: pull by digest with `oras` semantics over the OCI distribution API, verify
   the digest, mmap `model.gguf`, parse `model-card.yaml`.
2. `engine.rs`: `classify(&Card, &str) -> Verdict{label, p, margin, latency_ms}` reading
   next-token logits for each label's first token; `extract` with grammar-bounded generation.
3. `server.rs`: the API in section 4, loopback only, JSON tracing, OTLP span per call.
4. `Dockerfile`: multi-stage, distroless `cc-debian12` arm64, non-root, the binary only.
5. `tests/`: a 20 MB fixture GGUF (tiny model) checked into git-lfs; classify on ten prompts
   returns the fixture's known labels; abstain fires below the threshold; a wrong digest is
   refused.

## 8. Rejected

- **A candle engine as the answer to Voice Gate alone.** Kept, but as the shared Runtime; a
  tenant-private inference loop is the monolith the memo warns against.
- **Training on the A1 nodes or the laptop.** 6 ARM cores or a 2018 Intel laptop: hours to days
  per run and a blocked cluster. Modal's free credits do it in minutes for nothing.
- **`llama-server` as the Runtime.** Mature, and the fastest path to a number. Rejected on the
  founder's stated direction (memory-safe Rust, no external process); if CP4's numbers on the
  node are poor, this is the one-file fallback and the artifact contract does not change.
- **Quoting 15 to 25 ms.** A decoder still prefills the whole prompt; the figure is measured at
  CP4 or it is not written.

## 9. Sources (ruling: research before choosing, cite what was read)

- Modal pricing and free credits: [Modal Pricing Explained (2026)](https://www.beam.cloud/blog/modal-pricing-explained),
  [Modal Pricing 2026 | CostBench](https://costbench.com/software/ai-gpu-cloud/modal/),
  [Modal GPU Pricing | ComputePrices](https://computeprices.com/providers/modal).
- Unsloth Qwen3 fine-tune and GGUF export: [Qwen3 — How to Run & Fine-tune | Unsloth](https://unsloth.ai/docs/models/tutorials/qwen3-how-to-run-and-fine-tune),
  [unsloth/Qwen3-0.6B-GGUF](https://huggingface.co/unsloth/Qwen3-0.6B-GGUF),
  [unslothai/unsloth](https://github.com/unslothai/unsloth).

## 10. Scale: twenty models a day

The GPU is not the limit; examples and evaluation are. Each stage is sized here.

| Stage | Limit | How it scales | Proof |
|---|---|---|---|
| Datasets | 500 labelled examples per task, minimum | Teacher arbitrage (section 11) labels from traces already paid for; abstains become the next dataset | `forge/export_langfuse.py` prints the count and refuses under 500 |
| Training | Modal runs in parallel, per-second billing; a 15-minute T4 run is about $0.15. 20 runs a day is about $3 a day, $90 a month, three times the $30 free credits | Under the free tier: 6 to 7 runs a day. Above it: `# founder-approved-spend` on the Dagster schedule, or a second free launcher (Kaggle: 30 GPU hours a week, about 120 runs) behind the same `train.py` (LAW 34) | Modal dashboard spend line quoted in the ticket |
| Scheduling | One Dagster job `forge_train`, one partition per task | 20 partitions is a normal Dagster day | Dagster UI, the job's description (LAW 28) |
| Artifacts | GHCR, one OCI artifact per task per version | Unbounded for our sizes | `oras repo tags` |
| Serving | 0.6B Q4 is about 400 MB mmap'd; 1.7B about 1.1 GB. A 24 GB node holds about 20 small models or 8 medium | Runtime loads on first call, evicts least-recently-used above a byte budget in the ConfigMap; a cold load is one mmap | `/v1/health` lists loaded tasks and resident bytes |
| Evaluation | Held-out agreement against the teacher, per run | Automatic; a run under `min_agreement` never ships | `eval.json` in the artifact |

Rule: no model ships without its eval; twenty unchecked models a day is twenty leaks a day.

## 11. Teacher arbitrage

A paid model is worth paying exactly once per example, as a teacher. Three moves:

1. **Reuse before regenerate.** Every teacher answer already paid for is in Langfuse. Tenant
   0 to 3 datasets start there at zero marginal cost.
2. **Cheapest adequate teacher.** For new labels, a 100-example calibration set is labelled by
   the strongest model and the cheapest candidate. If the cheap one agrees above
   `min_agreement`, it labels the rest; the strong one labels only the disagreements.
   Disagreements go to a third vote, never to a human by default.
3. **The student replaces the teacher; the teacher only sees abstains.** Once a model ships,
   the Runtime answers and the paid model is called only on abstains. Those cases are labelled
   by the teacher in the normal course of serving, land in Langfuse, and become the next
   training set. Each retrain shrinks the abstain share; the paid bill converges on the hard
   cases only.

Labelling cost is measured from `LiteLLM_SpendLogs` under the Forge's own router key
`forge-teacher`, never quoted here; teacher spend is a line of its own.
