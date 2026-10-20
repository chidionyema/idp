import { HeroPlayground } from "@/components/HeroPlayground";
import { Reveal } from "@/components/Reveal";
import type { Metadata } from "next";
export const metadata: Metadata = { title: "LLM Playground", description: "LLM routing playground. Compare model responses, latency, and cost across four models." };

const MODELS = [
  { name: "GPT-4o Mini", provider: "OpenAI", input: 0.15, output: 0.60, bestFor: "Fast, low-cost tasks", speed: "Fast" },
  { name: "DeepSeek V3", provider: "DeepSeek", input: 0.27, output: 1.10, bestFor: "Cost-sensitive production", speed: "Fast" },
  { name: "Claude Sonnet 4", provider: "Anthropic", input: 3.00, output: 15.00, bestFor: "Long-context reasoning", speed: "Moderate" },
  { name: "Gemini 2.0 Flash", provider: "Google", input: 0, output: 0, bestFor: "Free tier, high volume", speed: "Fast" },
];

export default function DemoPage() {
  return (
    <div className="container section">
      <Reveal><div style={{ marginBottom: "48px" }}>
        <span className="tag tag-accent" style={{ marginBottom: "16px", display: "inline-flex" }}>LLM Playground</span>
        <h1>LLM Routing Playground</h1>
        <p style={{ marginTop: "16px", color: "var(--ink-3)", fontSize: "18px", maxWidth: "60ch" }}>Compare responses, latency, and token costs across four models. Running in demo mode: set LITELLM_PROXY_URL to connect to a live model fleet.</p>
      </div></Reveal>
      <div style={{ display: "grid", gap: "48px", gridTemplateColumns: "3fr 2fr", alignItems: "start" }}>
        <Reveal>
          <div style={{ border: "1px solid var(--rule)", background: "var(--white)", padding: "32px" }}>
            <HeroPlayground />
          </div>
        </Reveal>
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          <Reveal>
            <div style={{ border: "1px solid var(--rule)", background: "var(--white)", padding: "24px" }}>
              <p style={{ fontFamily: "var(--mono)", fontSize: "11px", fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--ink-3)", marginBottom: "16px" }}>Available models</p>
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {MODELS.map((m) => (
                  <div key={m.name} style={{ borderBottom: "1px solid var(--rule)", paddingBottom: "12px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                      <span style={{ fontFamily: "var(--mono)", fontSize: "12px", fontWeight: 500 }}>{m.name}</span>
                      <span style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)" }}>{m.input === 0 ? "Free" : `$${m.input}/$${m.output}`}</span>
                    </div>
                    <p style={{ fontFamily: "var(--mono)", fontSize: "10px", color: "var(--ink-3)", marginBottom: "4px" }}>{m.provider} · {m.speed}</p>
                    <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--accent)" }}>{m.bestFor}</p>
                  </div>
                ))}
              </div>
            </div>
          </Reveal>
          <Reveal>
            <div style={{ border: "1px solid var(--rule)", background: "var(--panel)", padding: "24px" }}>
              <p style={{ fontFamily: "var(--mono)", fontSize: "11px", fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--ink-3)", marginBottom: "12px" }}>What you’re looking at</p>
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {[
                  { label: "Latency", desc: "End-to-end, including simulated network overhead" },
                  { label: "Tokens", desc: "Input + output, rounded" },
                  { label: "Cost", desc: "Per-request at current token counts" },
                  { label: "Mode", desc: "Demo = synthetic. Set LITELLM_PROXY_URL for live calls." },
                ].map((t) => (
                  <div key={t.label} style={{ display: "flex", gap: "12px", fontFamily: "var(--mono)", fontSize: "11px" }}>
                    <span style={{ color: "var(--accent)", fontWeight: 500, flexShrink: 0 }}>{t.label}</span>
                    <span style={{ color: "var(--ink-3)" }}>{t.desc}</span>
                  </div>
                ))}
              </div>
            </div>
          </Reveal>
        </div>
      </div>
    </div>
  );
}
