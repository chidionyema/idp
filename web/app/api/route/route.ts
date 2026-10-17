import { NextRequest, NextResponse } from "next/server";

const DEMO_RESPONSES = [
  "Agentic routing classifies each incoming request by complexity before deciding which model to send it to. Simple classification, extraction, and basic Q&A tasks route to lightweight models like GPT-4o Mini or DeepSeek V3 — which cost 10–40× less than GPT-4o for those task types.\n\nThe routing layer also maintains fallback chains per intent class. If the primary model starts erroring or latency climbs past the threshold, traffic automatically re-routes to the next model in the chain. This happens before users see an error — it's a pre-emptive re-route, not a retry.\n\nObservability is built in: every routing decision emits a span with intent class, selected model, fallback state, latency, and error rate. These go to ClickHouse via OTLP. That's how you get cost attribution by team and feature, and how you catch a degraded model before it becomes an incident.",
  "A production LLM stack needs five things:\n\n1. **A routing layer** — classifies each request and routes it to the right model. Handles fallback chains, rate limits, and cost caps. LiteLLM proxy is the common choice here.\n\n2. **An inference layer** — your model fleet. In production you want at least two upstream providers with independent fallback chains. Single-provider setups fail in ways that cascade.\n\n3. **Observability** — Langfuse for LLM-native traces (prompt/response pairs, token counts, cost) and OpenTelemetry for infrastructure spans. ClickHouse for storage. Grafana for dashboards.\n\n4. **Workload identity** — SPIFFE/SPIRE. Every inference request carries a cryptographic SVID. Downstream services validate it. You get audit logging and mTLS without managing a certificate infrastructure.\n\n5. **An eval pipeline** — automated tests that run in CI on every model or prompt change. Statistical significance testing. Regression blocking.",
];

const MODELS = ["gpt-4o-mini", "deepseek-chat", "claude-sonnet-4", "gemini-2.0-flash", "gpt-4o"];

const MODEL_COSTS: Record<string, { input: number; output: number }> = {
  "gpt-4o-mini": { input: 0.15, output: 0.60 },
  "deepseek-chat": { input: 0.27, output: 1.10 },
  "claude-sonnet-4": { input: 3.00, output: 15.00 },
  "gemini-2.0-flash": { input: 0, output: 0 },
  "gpt-4o": { input: 2.50, output: 10.00 },
};

export async function GET() {
  return NextResponse.json({ models: MODELS, status: "ok" });
}

export async function POST(req: NextRequest) {
  try {
    const { message, model = "gpt-4o-mini" } = await req.json();
    if (!message?.trim()) return NextResponse.json({ error: "message is required" }, { status: 400 });
    const start = Date.now();
    const latency = 80 + Math.floor(Math.random() * 120);
    await new Promise((r) => setTimeout(r, latency));
    const response = DEMO_RESPONSES[Math.floor(Math.random() * DEMO_RESPONSES.length)];
    const totalTokens = Math.floor(response.length * 0.7);
    const inputTokens = Math.floor(totalTokens * 0.4);
    const outputTokens = totalTokens - inputTokens;
    const costs = MODEL_COSTS[model] ?? MODEL_COSTS["gpt-4o-mini"];
    const costUsd = (inputTokens / 1_000_000) * costs.input + (outputTokens / 1_000_000) * costs.output;
    return NextResponse.json({ response, model, latency, totalTokens, costUsd, mode: "demo" });
  } catch {
    return NextResponse.json({ error: "Invalid request body" }, { status: 400 });
  }
}
