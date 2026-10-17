export interface Post { slug: string; title: string; date: string; excerpt: string; body: string; readTime: string; }
export const posts: Post[] = [
  {
    slug: "agentic-routing-for-enterprise",
    title: "Agentic Routing for the Enterprise",
    date: "2025-01-15",
    readTime: "12 min read",
    excerpt: "Why most routing layers fail at scale — and the three failure modes we encountered in our first 12 deployments.",
    body: `A routing layer that sends everything to GPT-4o works fine in a demo. It falls apart at 10,000 requests per hour with a cost ceiling and a 99.9% uptime SLA. We know because we watched it happen.

This is the reference architecture we've used across 12 enterprise deployments. It's not a product pitch. Every component has survived real traffic.

## The three things that break first

**Latency spikes** — one of your upstream model providers degrades for 20 minutes. Latency doubles. Without observability, you don't know why.

**Retry storms** — a rate limit triggers a naive retry. Within seconds, you've multiplied the problem by your retry count and burned your cost budget for the hour.

**Hallucination cascades** — a slow model returns a partial response. A downstream tool call gets corrupted input. The synthesis layer treats it as fact.

These aren't edge cases. In our first three deployments, at least one of these happened within the first two weeks.

## The routing layer

The router sits between the user request and the model fleet. Before anything else, it classifies the request by complexity. Not by rules — by a lightweight model that runs in 8–40ms and outputs an intent class.

Intent classes map to models. Simple extractions go to DeepSeek V3. Classification goes to GPT-4o Mini. Complex reasoning goes to GPT-4o. The savings on routine tasks: 10–40× versus routing everything to GPT-4o.

This is the part most teams skip. They hard-code rules for what goes where, and the rules work for the 60% of requests that look like what they tested. They fail silently for the other 40%.

## Fallback chains

A fallback chain is a prioritized list of models with health thresholds. The router monitors error rate and p95 latency per model over a 5-minute sliding window. If either crosses the threshold, the circuit opens and traffic routes to the next model preemptively.

The user never hits a degraded endpoint. This is the distinction that matters: pre-emptive re-route, not retry logic. Retry logic reacts to errors that have already happened. Circuit breaking prevents them.

## Workload identity

Every request carries a SPIFFE SVID — an X.509 certificate that encodes the calling service's cryptographic identity. The inference server validates it before processing. Downstream services validate it before accepting the response.

This sounds like security theater until you need it. Then it matters for every request: audit logging, downstream access control, upstream mTLS.

## What the observability looks like

Every routing decision emits a span: intent class, selected model, fallback state, latency, error rate. These flow to ClickHouse via OTLP.

The latency budget we target per task type: 200ms for classification, 2000ms for inference, 500ms for tool calls, 200ms for synthesis. Total: under 5 seconds p95 for complex multi-step tasks.

## Three things we got wrong

Rules-based intent classification worked for 60% of requests. It failed silently for the other 40%. We switched to a model-based classifier. It catches the edge cases that rules miss.

We didn't monitor fallback hit rate. A fallback hit rate above 2% turned out to be an early signal that a primary model was degrading — hours before it caused user-visible errors.

We treated the routing layer as infrastructure that couldn't fail. If it goes down, nothing routes anywhere. The fix: stateless design backed by Redis with three replicas. The router fails independently of the model fleet.`,
  },
  {
    slug: "llm-red-teaming",
    title: "LLM Red-Teaming at Scale",
    date: "2024-11-20",
    readTime: "9 min read",
    excerpt: "A methodology for finding the failure modes in a production LLM pipeline before someone else does.",
    body: `Most LLM red-teaming is a few hours of someone running jailbreak prompts, writing down what broke, and calling it done. That produces a list. It doesn't produce a system for catching regressions.

A production red-teaming program has four parts that actually work together.

## The threat model first

LLM systems have an attack surface that doesn't exist in traditional software: the attack is against the output distribution, not the memory layout. This changes everything about what you're defending.

Prompt injection — adversarial instructions embedded in the input. The model follows them even when they contradict the system prompt.

Jailbreaking — structured inputs designed to bypass safety training. Effective jailbreaks exploit how safety training generalizes, not how it's implemented.

Hallucination amplification — inputs tuned to maximize the model's confidence in wrong outputs.

Context poisoning — adversarial content in the retrieval corpus. The model retrieves false information and treats it as ground truth.

Each requires different defenses. You can't have one mitigiation strategy that covers all four.

## The evaluation harness

The harness runs 200+ prompt variants against the full pipeline per evaluation run. It's triggered by any model update or significant prompt change — not run ad hoc.

Prompt variants come from templates with adversarial perturbations: character-level typos, encoding tricks, language mixing, context window manipulation. The goal is to test generalization rather than recall of known attack patterns.

Outputs are scored across six dimensions: correctness, safety, instruction following, coherence, hallucination, and latency.

## Statistical significance

One run is not a finding. Each variant runs 20 times with temperature variation. Failure rates are reported with 95% confidence intervals.

This matters because LLM outputs are non-deterministic. A single run tells you almost nothing. A 20-run sample with a confidence interval tells you whether the failure rate is 0.1% or 5% — which is the difference between "acceptable" and "a problem."

## The regression pipeline

The harness runs in CI on every pull request that changes the model or the prompt. A new model version that increases any failure rate by more than 2 percentage points blocks the merge.

This is the part most teams skip. It's also the most important. Without it, you catch failures in production instead of in CI. With it, a safety regression in the model you shipped last Tuesday gets caught before anyone ships the model you shipped today.`,
  },
  {
    slug: "spiffe-for-ai-workloads",
    title: "SPIFFE for AI Workloads",
    date: "2024-09-05",
    readTime: "10 min read",
    excerpt: "Workload identity is the missing security layer in most AI deployments. Here's how to add it.",
    body: `Most AI deployments have a security model that looks like this: the inference endpoint is behind a VPC. Anyone inside the VPC can call it.

This is not wrong — it's just incomplete. It doesn't cover the case where something inside the VPC shouldn't be calling the inference endpoint. It doesn't cover what happens when a compromised container starts making requests. It doesn't give you an audit trail of which service called what, when, with what attestation evidence.

The tooling for workload identity in ephemeral compute didn't exist at the level AI workloads require. SPIFFE/SPIRE changes that.

## Why AI workloads are different

Traditional services run for months on the same instance. You can manage their certificates manually or with a long-lived rotation schedule. AI inference servers — vLLM on GPU nodes, for example — might run for 8 hours and then get replaced as the autoscaler responds to demand.

During those 8 hours, the inference server needs to authenticate to a vector database, a document store, and a downstream model gateway. If you're doing mTLS, that means certificates. If those certificates are managed manually or with a rotation policy designed for long-lived services, you're not rotating them fast enough.

SPIRE's workload API handles this. The SPIRE Agent runs on every node. It attests the node's platform via the platform's metadata service — AWS IID, GCP MT, Azure MSI. Then it issues SVIDs to every workload on the node via a Unix socket. The workload never has to know where the certificates come from.

## Integrating with vLLM and LiteLLM

vLLM and LiteLLM proxy both support SPIFFE as a workload identity source via the standard Workload API — no code changes to the AI runtime.

For LiteLLM, configure the proxy to use the SPIRE agent's workload API for outbound mTLS connections. The proxy presents its SVID to upstream model providers that support mTLS. You get mutual TLS without managing a certificate infrastructure.

## Certificate rotation without downtime

The SVID rotation policy is 24 hours. The SPIRE agent polls every 15 minutes. When a new SVID is available, it writes to disk and signals the workload via SIGUSR2.

LiteLLM handles SIGUSR2 by reloading the certificate from disk. The next outbound request uses the new certificate. No connection drop. No restart. No downtime.

## What you get

Every SVID issuance is logged: workload SPIFFE ID, node ID, attestation data, timestamp. This is your audit trail for authentication events — which satisfies the equivalent SOC 2 control, and gives you forensic capability if something behaves unexpectedly.

Combined with Langfuse trace data (anonymized before ingestion), you have end-to-end traceability from workload identity to model inference.`,
  },
];
