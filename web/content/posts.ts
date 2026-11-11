export interface Post {
  slug: string;
  title: string;
  date: string;
  excerpt: string;
  body: string;
  readTime: string;
  references?: { label: string; url: string }[];
}

// Published notes describe engineering methods and hypotheses. Performance claims require
// traceable measurements: never turn an illustrative design into a claimed deployment.
export const posts: Post[] = [
  {
    slug: "persistent-operational-intelligence",
    title: "When an AI Agent's Work Outlives Its Session",
    date: "2026-11-11",
    readTime: "4 min read",
    excerpt: "A laboratory experiment in preserving independently verified agent work across sessions—and what it does not yet prove.",
    body: `A useful AI system should leave behind more than a transcript. When an agent completes a task, can another agent inherit an actual working result, verify it independently and continue without repeating the original inference?

This is one of the questions we are investigating at Merdian Intelligence. It sits at the intersection of agent memory, executable verification, distributed systems and the economics of artificial intelligence.

## From recollection to operational evidence

Remembering that a task was completed is different from possessing a reproducible result. A written summary can be inaccurate, stale or disconnected from the deployed revision. A verified executable artifact provides a stronger foundation: it can be checked against its original requirements and tested again after a session disappears.

In one narrow internal laboratory trial, a model-generated Python authorization function passed eight independently authored tests. Another temporary runner subsequently recovered that exact implementation, independently retested it and replayed the result without another model call. The verified implementation was retained in version-controlled research material for subsequent checks.

That is evidence for exact-task reuse—not proof that an agent has acquired general intelligence or learned new model weights.

## Measure what the next agent can actually do

Our evaluation separates successful inference from successful execution. We preserve the task definition, result fingerprint, test expectations, revision identity and observed failures. Independent checks must accept a reference result and reject an empty implementation.

If a task or its test definition changes, a remembered solution should be treated as unverified until it passes the new test. Success is not inherited merely because an earlier agent claimed it.

## The harder unanswered question

Can verified experience from one task improve an agent's performance on a genuinely new task? Our initial related-task comparisons did not establish that advantage; third-party model availability and inconsistent completions interfered with the experiment.

The next stage is controlled, repeated comparison across models, genuinely held-out tasks and measurable costs. A research programme should report the experiments that did not establish its hypothesis as carefully as those that did.

For organisations adopting autonomous systems, the long-term opportunity is not simply a larger memory. It is a way to preserve trustworthy operational knowledge—and establish which parts are actually transferable.`,
  },
  {
    slug: "agentic-routing-for-enterprise",
    title: "Agentic Routing for the Enterprise",
    date: "2025-01-15",
    readTime: "7 min read",
    excerpt: "Routing is a quality, cost and availability decision. Here is how to test it without confusing a diagram with evidence.",
    body: `A model router is a control plane for inference. It classifies a request, chooses an eligible model and records why that choice was made. The objective is not to use the cheapest model. It is to find the lowest-cost route that meets a measured quality and latency requirement.

There is a familiar failure: teams benchmark a classifier on clean requests and then assume it can route production traffic. Real traffic includes truncated requests, unfamiliar languages, missing context and tool calls that must preserve permissions.

## Start with an evaluation set

Build a representative, versioned corpus of requests. Each item needs an expected capability, a required output format, a risk category and a quality rubric. Include ambiguous requests and samples the classifier should abstain from routing.

Evaluate routing decisions against a fixed-model baseline. Report correctness, cost per successful request, p50 and p95 latency, and the rate at which the router must fall back. Savings without a quality denominator are not a meaningful result.

## Separate routing from recovery

A router chooses an upstream before the request. A circuit breaker monitors health and changes eligibility when error or latency thresholds are breached. Retries are bounded and must respect idempotency. These are different controls.

A cascade of retries can overload a struggling provider. Add time budgets, exponential backoff with jitter and a cap on total attempts. Every failed route should surface the selected provider, reason code and final disposition without exposing prompt contents unnecessarily.

## Measure the whole transaction

Trace the intake, classification, inference, tool execution and synthesis stages under one request identity. Distinguish queued time from service time. Record the model version, token usage and pricing assumptions alongside output-quality measurements.

OpenTelemetry's generative AI semantic conventions provide a shared vocabulary for telemetry. Instrumentation is only useful when its attributes are checked against the actual SDK and provider behavior.

## A falsifiable experiment

Compare at least two routing policies on the same held-out traffic. Freeze model versions, prompts and evaluation criteria for the comparison. Track the failure distribution as well as aggregate cost. A routing policy can win on median cost and lose on the worst ten percent of requests.

No universal savings multiplier is asserted here. The result must come from an independently repeatable benchmark on the intended workload.`,
    references: [
      { label: "OpenTelemetry semantic conventions", url: "https://opentelemetry.io/docs/specs/otel/semantic-conventions/" },
      { label: "OpenTelemetry generative AI attributes", url: "https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/" },
    ],
  },
  {
    slug: "llm-red-teaming",
    title: "LLM Red-Teaming at Scale",
    date: "2024-11-20",
    readTime: "6 min read",
    excerpt: "A repeatable security evaluation method for prompt injection, unsafe tool use and retrieval poisoning.",
    body: `A red-team exercise produces useful evidence only when its threat model and scoring criteria can be repeated. A list of clever prompts is an input to that process, not its output.

The hardest failures often cross trust boundaries. A retrieved document can contain an instruction. An agent can promote a tool response into authority. A model may obey a hostile instruction that looks like normal task context.

## Name the trust boundaries

Map each entry point: user input, retrieval, browsing, tool output, memory and agent-to-agent messages. Mark which sources are untrusted. Record the tools and data each step is allowed to access.

Test indirect prompt injection separately from direct user attempts. Evaluate what the system did, not whether the model sounded cautious. A refusal is not a safe outcome if an earlier tool call already disclosed a secret.

## Build a reproducible harness

Version the adversarial cases, model configuration, system instructions, tool permissions and scoring rules. Every case needs an expected result and an account of its impact if the boundary fails.

Run variants enough times to estimate uncertainty. Report confidence intervals with an appropriate statistical method and the actual sample size. Do not claim fine-grained failure probabilities from a handful of stochastic executions.

## Score observable behavior

Capture attempted and completed tool calls, boundary violations, sensitive-data exposure and instruction hierarchy failures. Capture false positives as well: a guardrail that blocks safe customer work has an operational cost.

Input screening, constrained tool access, output validation and human approval are complementary controls. No classifier alone can make an agent safe.

## Close the loop

Turn confirmed findings into regression cases. Compare each change to a versioned baseline, and investigate changes in the failure distribution. A gate should explain how to reproduce its failure and point to the responsible boundary.

This note specifies a testing method. It does not assert that a particular model or deployment has passed that test.`,
    references: [
      { label: "OWASP prompt injection prevention guidance", url: "https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html" },
    ],
  },
  {
    slug: "spiffe-for-ai-workloads",
    title: "SPIFFE for AI Workloads",
    date: "2024-09-05",
    readTime: "7 min read",
    excerpt: "An identity pattern for short-lived AI services, including the integration work it actually requires.",
    body: `A private network does not establish the identity of a workload. When an inference worker calls a document store or another service, the receiver needs to know which workload made the call and whether it should be trusted.

SPIFFE defines workload identities. SPIRE can issue verifiable identity documents after attesting a node and the process making the request. This is useful for ephemeral services because identity can follow the workload rather than a machine image.

## What the standard provides

The SPIFFE Workload API provides X.509-SVIDs, JWT-SVIDs and trust bundles. An X.509-SVID encodes a SPIFFE ID in a certificate. Consumers use a trusted bundle to validate the identity presented by a peer.

The Workload API is not a universal drop-in feature for every model server. An application must use a compatible client library, proxy or sidecar. Verify the actual integration path for the selected vLLM, gateway or LiteLLM version before promising mutual TLS.

## Attestation and authorization

SPIRE attests nodes and workloads against configured selectors. The resulting identity says which workload was authenticated. It does not decide which resources that workload is allowed to access.

Write authorization rules separately. Deny unrecognised IDs. Protect the Workload API socket and the trust bundle lifecycle. Define rotation and revocation behavior for each process that consumes a certificate.

## Rotation is an integration test

A Workload API client can receive updated SVID material. Whether a specific server handles an update without dropped connections depends on its TLS integration. Test certificate renewal while real traffic flows and record the behavior.

Do not assume a fixed rotation interval or a particular signal such as SIGUSR2; these are implementation choices, not guarantees of the SPIFFE specification.

## Evidence to collect

Validate identity issuance, failed attestation, rejected trust domains, certificate expiry, rotation and policy denial. Correlate identity evidence with request traces without logging private keys or sensitive customer input.

SPIFFE provides an identity foundation, not automatic compliance certification. Compliance claims require evidence against the applicable controls and the real deployed environment.`,
    references: [
      { label: "SPIFFE: Working with SVIDs", url: "https://spiffe.io/docs/latest/deploying/svids/" },
      { label: "SPIFFE: Concepts and trust domains", url: "https://spiffe.io/docs/latest/spiffe-about/spiffe-concepts/" },
    ],
  },
];
