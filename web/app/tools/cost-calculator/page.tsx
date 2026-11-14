import { CostCalculator } from "@/components/CostCalculator";
import { pricingChecked } from "@/content/models";
import { Reveal } from "@/components/Reveal";
import type { Metadata } from "next";
export const metadata: Metadata = { title: "LLM Cost Calculator", description: "Compare published LLM list prices across OpenAI, Anthropic and Google. Calculate per-request, daily and monthly cost." };

export default function CostCalculatorPage() {
  return (
    <div className="container section">
      <Reveal><div style={{ marginBottom: "48px" }}>
        <span className="tag tag-accent" style={{ marginBottom: "16px", display: "inline-flex" }}>Tools</span>
        <h1>LLM Cost Calculator</h1>
        <p style={{ marginTop: "16px", color: "var(--ink-3)", fontSize: "18px", maxWidth: "60ch" }}>See what your LLM bill looks like at different token volumes and model choices. Adjust the sliders to get real numbers for your use case.</p>
      </div></Reveal>
      <Reveal>
        <div style={{ border: "1px solid var(--rule)", background: "var(--white)", padding: "32px", marginBottom: "16px" }}>
          <CostCalculator />
        </div>
        <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)", marginBottom: "48px", maxWidth: "72ch", lineHeight: 1.7 }}>
          Published list rates per 1M tokens, checked {pricingChecked}. Gemini 3.8 Flash is at its introductory rate until 31 December 2026, then $1.50 and $7.50.
        </p>
      </Reveal>
      <div style={{ borderTop: "1px solid var(--rule)", paddingTop: "48px" }}>
        <Reveal><h2 style={{ marginBottom: "24px" }}>How routing reduces costs</h2></Reveal>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "24px" }}>
          {[{ title: "Classify before routing", desc: "A lightweight model reads each request and sorts it by complexity. Simple work goes to a cheap model. Hard work goes to a frontier model. Nobody writes the rules by hand." }, { title: "Twenty times less on input", desc: "GPT-6 Luna lists at $0.10 per million input tokens. Claude Sonnet 5.5 lists at $2.00. Move the same request to the cheap tier and the input cost falls twenty times." }, { title: "Circuit breakers, not retries", desc: "When a model degrades, traffic pre-emptively routes to the fallback. No retry storms, no wasted spend." }, { title: "Cost attribution by team", desc: "Every trace span carries team and feature tags. ClickHouse queries show you exactly which product line is driving your bill." }].map((t) => (
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
