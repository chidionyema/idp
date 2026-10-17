import { CostCalculator } from "@/components/CostCalculator";
import { Reveal } from "@/components/Reveal";
import type { Metadata } from "next";
export const metadata: Metadata = { title: "LLM Cost Calculator", description: "Compare LLM pricing across GPT-4o, Claude, Gemini, and DeepSeek. Calculate per-request, daily, and monthly costs." };

export default function CostCalculatorPage() {
  return (
    <div className="container section">
      <Reveal><div style={{ marginBottom: "48px" }}>
        <span className="tag tag-accent" style={{ marginBottom: "16px", display: "inline-flex" }}>Tools</span>
        <h1>LLM Cost Calculator</h1>
        <p style={{ marginTop: "16px", color: "var(--ink-3)", fontSize: "18px", maxWidth: "60ch" }}>See what your LLM bill looks like at different token volumes and model choices. Adjust the sliders to get real numbers for your use case.</p>
      </div></Reveal>
      <Reveal>
        <div style={{ border: "1px solid var(--rule)", background: "var(--white)", padding: "32px", marginBottom: "48px" }}>
          <CostCalculator />
        </div>
      </Reveal>
      <div style={{ borderTop: "1px solid var(--rule)", paddingTop: "48px" }}>
        <Reveal><h2 style={{ marginBottom: "24px" }}>How routing reduces costs</h2></Reveal>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "24px" }}>
          {[{ title: "Classify before routing", desc: "A lightweight model classifies each request by complexity in 8–40ms. Simple tasks route to cheap models. Complex ones go to frontier models. No hard-coded rules." }, { title: "60–80% of tasks are simple", desc: "Classification, extraction, basic Q&A — the bulk of production volume — route to models that cost 10–40× less than GPT-4o." }, { title: "Circuit breakers, not retries", desc: "When a model degrades, traffic pre-emptively routes to the fallback. No retry storms, no wasted spend." }, { title: "Cost attribution by team", desc: "Every trace span carries team and feature tags. ClickHouse queries show you exactly which product line is driving your bill." }].map((t) => (
            <Reveal key={t.title}>
              <div className="card">
                <h4 style={{ fontFamily: "var(--serif)", marginBottom: "12px" }}>{t.title}</h4>
                <p style={{ fontSize: "14px", color: "var(--ink-3)", lineHeight: 1.7 }}>{t.desc}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </div>
  );
}
