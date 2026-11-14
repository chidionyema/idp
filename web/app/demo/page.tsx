import { HeroPlayground } from "@/components/HeroPlayground";
import { models, pricingChecked } from "@/content/models";
import { Reveal } from "@/components/Reveal";
import type { Metadata } from "next";
export const metadata: Metadata = { title: "LLM Playground", description: "LLM routing playground. Compare model responses, latency, and cost across five models from three providers." };

const MODELS = models;

export default function DemoPage() {
  return (
    <div className="container section">
      <Reveal><div style={{ marginBottom: "48px" }}>
        <span className="tag tag-accent" style={{ marginBottom: "16px", display: "inline-flex" }}>LLM Playground</span>
        <h1>LLM Routing Playground</h1>
        <p style={{ marginTop: "16px", color: "var(--ink-3)", fontSize: "18px", maxWidth: "60ch" }}>Compare responses, latency, and token costs across five models. Running in demo mode: set LITELLM_PROXY_URL to connect to a live model fleet.</p>
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
                  <div key={m.key} style={{ borderBottom: "1px solid var(--rule)", paddingBottom: "12px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                      <span style={{ fontFamily: "var(--mono)", fontSize: "12px", fontWeight: 500 }}>{m.label}</span>
                      <span style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)" }}>{m.inputPer1M === 0 ? "Free" : `$${m.inputPer1M.toFixed(2)}/$${m.outputPer1M.toFixed(2)}`}</span>
                    </div>
                    <p style={{ fontFamily: "var(--mono)", fontSize: "10px", color: "var(--ink-3)", marginBottom: "4px" }}>{m.provider} · {m.speed}</p>
                    <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--accent)" }}>{m.bestFor}</p>
                  </div>
                ))}
              </div>
              <p style={{ fontFamily: "var(--mono)", fontSize: "10px", color: "var(--ink-3)", marginTop: "16px", lineHeight: 1.6 }}>
                Published list rates per 1M tokens, checked {pricingChecked}. Gemini 3.8 Flash is at its introductory rate until 31 December 2026, then $1.50 and $7.50.
              </p>
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
                    <span className="mi-demo-label">{t.label}</span>
                    <span className="mi-demo-desc">{t.desc}</span>
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
