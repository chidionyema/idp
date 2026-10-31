# Primary-source research for estate lockdown and memory acceptance

Reviewed 2026-10-29/30 UTC. Decisions below are engineering inferences for this estate, not
claims of standards compliance or new founder approvals.

| Source | What it supports | Estate application |
|---|---|---|
| [Google SRE error-budget policy](https://sre.google/workbook/error-budget-policy/) | Reliability objectives can control release policy; its example freezes ordinary changes when the error budget is exhausted while permitting urgent repairs | Make release refusal an executable consequence of measured service failure. Preserve a bounded recovery path. |
| [Google SRE: implementing SLOs](https://sre.google/workbook/implementing-slos/) | Specify meaningful user outcomes, measurement and the reason for target values | Measure successful instruction delivery/application, not endpoint health. Distinguish existing founder thresholds from newly selected targets. |
| [LongMemEval](https://arxiv.org/abs/2410.10813) | Evaluates extraction, reasoning across sessions and time, updating knowledge, and abstaining when information is missing | Build estate cases for instruction capture, cross-session transfer, changed directives, temporal context and unknown answers. A write/read probe covers only a small part of this space. |
| [LoCoMo](https://arxiv.org/abs/2402.17753) | Uses long conversations to test question answering, event summaries and dialogue behavior | Replay long estate histories. Hold out later sessions and measure whether provenance-bearing answers remain correct. |
| [LoCoMo-Plus](https://arxiv.org/abs/2602.10715) | Tests retaining and applying constraints when the later query does not explicitly repeat them | The founder should not have to mention the old instruction in the next task. Test action constraint consistency, not only exact-string recall. |
| [Meta Muse Wonder](https://research.meta.ai/blog/muse-wonder) | Describes relevant context carried across conversations, and sustained goal pursuit through alternatives and adaptation | Active Memory must change later behavior; Active Focus must demonstrate bounded progress and adaptation. The primary article does not establish the exact scoring formulas claimed in older estate comparisons. |
| [SLSA 1.2 artifact verification](https://slsa.dev/spec/v1.2/verifying-artifacts) | Verifies trusted provenance and expectations bound to an artifact's digest | Bind acceptance to the tested candidate and running image/config. Artifact authenticity is necessary but does not prove a service's functional behavior. |
| [NIST AI RMF MEASURE](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) | Calls for testing before deployment and measurement during operation with documented methods and uncertainty | Separate controlled conformance tests from observed service performance; continuous verification remains necessary after release. |
| [NIST generative AI profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) | Provides a lifecycle risk-management frame for generative AI | Use provenance, impact and monitoring to choose estate-specific controls; this audit does not claim certification. |
| [OpenTelemetry GenAI attributes](https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/) | Provides identities and correlation attributes for agents, conversations and retrieval; the page reports migration to the GenAI conventions repository | Reuse the estate's telemetry with stable agent/session/trace identifiers and pin its convention version. Attribute presence alone is not proof of effective memory. |

The current research pass supports evaluation dimensions and release-control design. It does not
validate the correctness of all upstream implementations, every numerical benchmark, or all of
the estate's older third-party citations. No vendor leaderboard score is used as a release gate.

## Initial target policy

The founder's existing Definition of Done supplies API p95 <2s, agent-step p95 <10s, 100% session
resume, and 100% receipt integrity. Those measurements need the exact caller, window and denominator.
Additional targets in `contracts.json` are explicitly engineering proposals under this task:
all mandatory directives delivered/applied, no acknowledged directive loss, propagation <=60s,
and no unknown result counted as a pass. These are acceptance targets, not claims that a service
currently attains them. Tightening them has a throughput/availability cost described in `audit.md`.
