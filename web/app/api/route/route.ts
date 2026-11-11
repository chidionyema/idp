import { NextRequest, NextResponse } from "next/server";
import { models } from "@/content/models";

const DEMO_RESPONSES = [
  "Agentic routing classifies each incoming request by complexity before deciding which model to send it to. Simple classification, extraction, and basic Q&A tasks route to lightweight models like GPT-6 Luna or Claude Haiku 5.5, which list at $0.10 per million input tokens. Claude Sonnet 5.5 lists at $2.00. The same request costs twenty times less on input when it runs on the cheap tier.\n\nThe routing layer also maintains fallback chains per intent class. If the primary model starts erroring or latency climbs past the threshold, traffic automatically re-routes to the next model in the chain. This happens before users see an error — it's a pre-emptive re-route, not a retry.\n\nObservability is built in: every routing decision emits a span with intent class, selected model, fallback state, latency, and error rate. These go to ClickHouse via OTLP. That's how you get cost attribution by team and feature, and how you catch a degraded model before it becomes an incident.",
  "A production LLM stack needs five things:\n\n1. **A routing layer** — classifies each request and routes it to the right model. Handles fallback chains, rate limits, and cost caps. LiteLLM proxy is the common choice here.\n\n2. **An inference layer** — your model fleet. In production you want at least two upstream providers with independent fallback chains. Single-provider setups fail in ways that cascade.\n\n3. **Observability** — Langfuse for LLM-native traces (prompt/response pairs, token counts, cost) and OpenTelemetry for infrastructure spans. ClickHouse for storage. Grafana for dashboards.\n\n4. **Workload identity** — SPIFFE/SPIRE. Every inference request carries a cryptographic SVID. Downstream services validate it. You get audit logging and mTLS without managing a certificate infrastructure.\n\n5. **An eval pipeline** — automated tests that run in CI on every model or prompt change. Statistical significance testing. Regression blocking.",
];

const MODELS = models.map((m) => m.key);

const MODEL_COSTS: Record<string, { input: number; output: number }> = Object.fromEntries(
  models.map((m) => [m.key, { input: m.inputPer1M, output: m.outputPer1M }]),
);

export async function GET() {
  return NextResponse.json({ models: MODELS, status: "ok" });
}

export async function POST(req: NextRequest) {
  try {
    const { message, model = "gpt-6-luna" } = await req.json();
    if (!message?.trim()) return NextResponse.json({ error: "message is required" }, { status: 400 });
    const start = Date.now();
    const latency = 80 + Math.floor(Math.random() * 120);
    await new Promise((r) => setTimeout(r, latency));
    const response = DEMO_RESPONSES[Math.floor(Math.random() * DEMO_RESPONSES.length)];
    const totalTokens = Math.floor(response.length * 0.7);
    const inputTokens = Math.floor(totalTokens * 0.4);
    const outputTokens = totalTokens - inputTokens;
    const costs = MODEL_COSTS[model] ?? MODEL_COSTS["gpt-6-luna"];
    const costUsd = (inputTokens / 1_000_000) * costs.input + (outputTokens / 1_000_000) * costs.output;
    return NextResponse.json({ response, model, latency, totalTokens, costUsd, mode: "demo" });
  } catch {
    return NextResponse.json({ error: "Invalid request body" }, { status: 400 });
  }
}
