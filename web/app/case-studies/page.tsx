import Link from "next/link";
import { caseStudies } from "@/content/case-studies";
import { Reveal } from "@/components/Reveal";
import type { Metadata } from "next";
export const metadata: Metadata = { title: "Case Studies", description: "Real numbers from three production deployments: 73% cost reduction, 99.97% uptime, SOC 2 in 4 months." };

export default function CaseStudiesPage() {
  return (
    <div className="container section">
      <Reveal><div style={{ marginBottom: "64px" }}>
        <span className="tag tag-accent" style={{ marginBottom: "16px", display: "inline-flex" }}>Case Studies</span>
        <h1>What we’ve shipped</h1>
        <p style={{ marginTop: "16px", color: "var(--ink-3)", fontSize: "18px", maxWidth: "60ch" }}>Three engagements. Names anonymized; the numbers are real.</p>
      </div></Reveal>
      <div style={{ display: "flex", flexDirection: "column", gap: "48px" }}>
        {caseStudies.map((cs) => (
          <Reveal key={cs.id}>
            <article style={{ border: "1px solid var(--rule)", background: "var(--white)", overflow: "hidden" }}>
              <div style={{ padding: "40px" }}>
                <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginBottom: "20px" }}>
                  <span className="tag">{cs.industry}</span>
                  <span className="tag">{cs.companyType}</span>
                  <span style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)" }}>{cs.published}</span>
                </div>
                <h2 style={{ fontFamily: "var(--serif)", fontSize: "clamp(1.5rem, 3vw, 2.2rem)", marginBottom: "16px" }}>{cs.company}</h2>
                <p style={{ color: "var(--ink-3)", lineHeight: 1.75, maxWidth: "none" }}>{cs.challenge}</p>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "16px", margin: "32px 0" }}>
                  {cs.metrics.map((m) => (
                    <div key={m.label} style={{ border: "1px solid var(--rule)", background: "var(--panel)", padding: "20px" }}>
                      <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "8px" }}>{m.label}</p>
                      <p style={{ fontFamily: "var(--mono)", fontSize: "28px", fontWeight: 600, color: m.value === "✓" ? "var(--ok)" : "var(--accent)", lineHeight: 1 }}>{m.value}</p>
                      <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)", marginTop: "6px" }}>{m.detail}</p>
                    </div>
                  ))}
                </div>
                <div style={{ borderLeft: "3px solid var(--accent)", paddingLeft: "20px", margin: "32px 0" }}>
                  <p style={{ fontFamily: "var(--serif)", fontSize: "1.1rem", fontStyle: "italic", color: "var(--ink-2)", lineHeight: 1.7, maxWidth: "none" }}>“{cs.quote.text}”</p>
                  <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)", marginTop: "12px" }}>— {cs.quote.author}, {cs.quote.company}</p>
                </div>
                <div style={{ border: "1px solid var(--rule)", background: "var(--panel)", padding: "24px", margin: "0 0 32px" }}>
                  <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "12px" }}>What went wrong</p>
                  <p style={{ color: "var(--ink-2)", lineHeight: 1.75, maxWidth: "none" }}>{cs.friction}</p>
                </div>
                <div style={{ paddingTop: "32px", borderTop: "1px solid var(--rule)" }}>
                  <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "16px" }}>Stack</p>
                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                    {cs.stack.map((s) => <span key={s} className="tag tag-accent">{s}</span>)}
                  </div>
                </div>
              </div>
            </article>
          </Reveal>
        ))}
      </div>
      <div style={{ textAlign: "center", marginTop: "80px", paddingTop: "64px", borderTop: "1px solid var(--rule)" }}>
        <Reveal>
          <h2 style={{ fontFamily: "var(--serif)" }}>Working on something similar?</h2>
          <p style={{ color: "var(--ink-3)", marginTop: "16px" }}>We take on a small number of projects each quarter.</p>
          <div style={{ display: "flex", gap: "12px", justifyContent: "center", marginTop: "32px", flexWrap: "wrap" }}>
            <Link href="/contact" className="btn-primary">Schedule a call →</Link>
            <Link href="/consulting" className="btn-secondary">Our consulting practice</Link>
          </div>
        </Reveal>
      </div>
    </div>
  );
}
