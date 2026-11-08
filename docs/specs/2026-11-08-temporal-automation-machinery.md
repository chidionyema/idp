# Estate Automation Machinery — code-defined Temporal workflows

- Date: 2026-11-08
- Status: **candidate recovery implementation in PR; not deployed or runtime verified**
- Execution plane: existing \`sovereign\` Temporal worker, task queue and namespace
- Principle: **first occurrence is diagnosis; second recurrence is an automation defect**

## Decision amendment: ADR 0031

ADR 0031 correctly refused another orchestrator but wrongly assigned orchestration authority to the visual reactor. That React-based projection is a **read model**, not a durable, deterministic state machine. The existing \`SessionWorkflow\` remains unchanged; \`EstateAutomationWorkflowV1\` runs alongside it on the same Temporal worker and task queue. Do not introduce another workflow engine or state database.

## Contract and work domain

\`Instruction → authenticated gateway → capability discovery → immutable context compilation → Temporal execution → independently verified receipt → founder/agent projection\`.

The code-defined workflow implementation is the source of manifest fields, not a YAML catalogue. \`sovereign/automation/definitions\` holds executable classes with stable ID, SemVer, supported surfaces, input/output JSON Schema, owner, permissions, capacity, cost/latency budget, DAG dependencies, retries, verification probes and compensator status. \`contracts.catalogue()\` discovers implementations automatically. \`bin/estate-automation search/describe\` provides outcome-first discovery for operators.

A compiled plan binds request, actor, stable idempotency key, contract version, source commit SHA, worker image digest, deployment configuration digest, task DAG, concurrency limit and signed-receipt schema version under \`plan_hash\`. Unknown versions, missing release provenance, extra arguments, unapproved actors and a modified plan are refused.

\`workflow_id\` is deterministically derived from the actor, idempotency key and workflow version. Temporal owns its immutable execution \`run_id\`. Never rewrite or downgrade historic workflow types. New incompatible execution changes require \`EstateAutomationWorkflowV2\`, a replay test and explicit migrations.

## First vertical slice — recover candidate router

\`\`\`mermaid
flowchart TD
  A[Code-compiled plan] --> B[Pin unique Git ref to release SHA]
  B --> C[Dispatch existing router-recovery GitHub workflow]
  C --> D[Observe matching GitHub run and verify SHA/conclusion]
  D --> E[Independent HTTP liveliness probe]
  D --> F[Independent model inventory probe]
  E --> G[Real model completion, max 8 tokens]
  F --> G
  G --> H[Existing estate signed receipt activity]
\`\`\`

The existing \`.github/workflows/router-recovery.yml\` owns bundle generation, OCI vault merge, object upload and Cloudflare candidate tunnel configuration. Temporal reuses this proven *implementation boundary* for the candidate, rather than reproducing its cloud commands or accepting the GitHub job's own claims as sufficient evidence.

For correlation, the dispatch adapter creates \`refs/heads/auto-run-<marker>\` pinned to \`source_sha\` and dispatches GitHub Actions against that branch; the observer requires the matching \`head_branch\`, exact \`head_sha\`, completed status and successful conclusion. An existing orphaned branch with no run makes dispatch **ambiguous and blocked**. There is never an automatic second POST after a lost response. The per-run branches require future retention/garbage-collection policy.

Once the GitHub run is successful, \`health\` and \`models\` fan out independently; completion joins them. Missing probe keys, empty inventory, absent generated content, source mismatch or provider fault cannot produce a verified receipt. Every activity has a finite deadline (≤600s). Observation heartbeats and is limited to 540s. Result evidence and plan fingerprint are in Temporal state; terminal evidence is written via the existing \`append_receipt\` activity.

## The hard boundary: no untested production cutover

The existing GitHub recovery job has **no demonstrated snapshot/restore** for DNS, vault and object state. The candidate may itself replace prior candidate state. Therefore this slice is *candidate-only*: \`cutover=true\` is rejected at JSON Schema validation and the manifest explicitly reports \`rollback.supported=false\`. Neither a green unit test nor a successful GitHub Actions job authorizes routing live production traffic. True rollback and pre-state snapshots are P0 before enabling cutover.

## Surface and release prerequisites

The read-only commands \`bin/estate-automation list\`, \`search "recover router"\` and \`describe router-recovery\` derive their answers from executable classes.

The \`plan <request.json>\` command requires \`ESTATE_AUTOMATION_SOURCE_SHA\` (40 lowercase hex), \`ESTATE_AUTOMATION_ARTIFACT_DIGEST\` and \`ESTATE_AUTOMATION_CONFIG_DIGEST\` (\`sha256:\` digests); no defaults are guessed. A \`run\` additionally requires an **authenticated service principal** bound by the trusted gateway (same as \`request.actor\`), a worker deployed with matching release fingerprint, and provisioned \`ESTATE_AUTOMATION_GITHUB_TOKEN\` (actions read/write and contents write for run refs) and \`ESTATE_AUTOMATION_ROUTER_PROBE_KEY\` through the estate's secrets path. The preliminary local CLI environment variable is not a production-grade authentication protocol; public MCP/voice/founder invocation must not be exposed until the authenticated gateway is connected.

The registered workflow and activity must be deployed in the existing worker image; a CI merge alone is not a live deployment. Health reporting must echo the deployed source/config/image identity before operational claims can be made. The old intent catalogue remains unmodified in this slice. No synthetic success receipt or manufactured 30-day usage count is permitted.

## Executable acceptance and falsifiers

1. Search for “recover router” discovers the implementation-defined workflow; an unknown version or mutation is read-only.
2. Unauthenticated principal, unexpected repository/URL, unknown parameter and \`cutover=true\` are rejected before side effects.
3. Duplicate \`request_id\` derives one Temporal workflow ID; ambiguous dispatch and orphan branches never cause another POST.
4. A DAG cycle, missing parent or duplicated task ID fails compilation.
5. \`health\` and \`models\` are independent after \`observe\`; \`completion\` joins them; all activities are time bounded.
6. HTTP 200 without model completion does not produce a verified receipt.
7. Mismatched worker release, source SHA, read failure or missing credential is a visible refusal, never “operating”.
8. Temporal worker restart, history replay, GitHub provider outage, duplicate delivery and eventual verified rollback **must be demonstrated in the deployed integration suite**; they are not proven by offline unit tests.

## Remaining measured delivery gaps

**P0:** Temporal SDK-backed deterministic replay and worker death/fault-injection tests; verified candidate recovery against live GH/OCI/Cloudflare; active release identity and credentials; durable remote receipts (current worker's filesystem-based signature anchoring may not survive replacement). **P0 before cutover:** pre-state snapshot, idempotent compensating actions and independent rollback evidence. **P1:** publish the code-derived workflow records *into the existing* \`bin/capability-index\` store (not a second registry), expose a single authenticated API through MCP, founder surface, CLI and voice, then add cost, last success, health, receipts and progress timelines to the founder projection. **P1:** measure real 30-day usage of existing intents, freeze and archive unused definitions. **P1:** feed existing observability with progress/heartbeats, detect genuine 10-minute stagnation and trigger bounded authorized remediation.

**Do not mark this automation operational until the independent verifier and current deployed release prove it.**
