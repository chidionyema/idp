import Link from "next/link";
import { site } from "@/content/site";
import { HeroPlayground } from "@/components/HeroPlayground";
import { Reveal } from "@/components/Reveal";
import type { Metadata } from "next";
export const metadata: Metadata = { description: site.tagline };

export default function HomePage() {
  return (
    <>
      {/* Hero */}
      <section style={{ borderBottom: "1px solid var(--rule)" }}>
        <div className="container section hero-grid">
          <div className="hero-copy">
            <span className="tag tag-accent">AI Infrastructure Consulting</span>
            <h1 style={{ fontFamily: "var(--serif)" }}>AI infrastructure consulting for companies<br /><em style={{ fontStyle: "normal", color: "var(--accent)" }}>shipping production LLM systems</em>.</h1>
            <p style={{ fontSize: "18px", lineHeight: 1.7, color: "var(--ink-3)", maxWidth: "52ch" }}>
              We build the routing, the traces, the workload identity and the eval suite a production LLM feature needs. Most teams get the demo working. The gap between that and ten thousand requests an hour is the job.
            </p>
            <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
              <Link href="/contact" className="btn-primary">Talk to us →</Link>
              <Link href="/case-studies" className="btn-secondary">See our work</Link>
            </div>
          </div>
          <div className="hero-demo">
            <p style={{ fontFamily: "var(--mono)", fontSize: "11px", fontWeight: 500, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--ink-3)", marginBottom: "20px" }}>LLM routing demo</p>
            <HeroPlayground />
          </div>
        </div>
      </section>
      {/* Stats */}
      <section style={{ background: "var(--ink)", padding: "48px 0" }}>
        <div className="container" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "32px" }}>
          {[
            { value: "12", label: "deployments" },
            { value: "$1.1M", label: "monthly spend removed" },
            { value: "73%", label: "bill reduction, largest" },
            { value: "0.3/mo", label: "incidents, down from 3" },
          ].map((s) => (
            <div key={s.label} className="metric" style={{ textAlign: "center" }}>
              <span className="metric-value" style={{ color: "#fff" }}>{s.value}</span>
              <span className="metric-label" style={{ color: "rgba(255,255,255,0.6)" }}>{s.label}</span>
            </div>
          ))}
        </div>
      </section>
      {/* Research */}
      <section className="section">
        <div className="container">
          <Reveal><div style={{ marginBottom: "48px" }}><h2>Research</h2><p style={{ color: "var(--ink-3)", marginTop: "12px" }}>Written from engagements, not from conference talks.</p></div></Reveal>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(300px, 100%), 1fr))", gap: "24px" }}>
            {site.research.map((r) => (
              <Reveal key={r.title}>
                <div className="card" style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <span className="tag">{r.kind}</span><span style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)" }}>{r.year}</span>
                  </div>
                  <h3 style={{ fontSize: "1.3rem", fontWeight: 500 }}>{r.title}</h3>
                  <p style={{ fontSize: "14px", color: "var(--ink-3)", lineHeight: 1.7 }}>{r.blurb}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>
      {/* Process */}
      <section className="section" style={{ background: "var(--panel)", borderTop: "1px solid var(--rule)", borderBottom: "1px solid var(--rule)" }}>
        <div className="container">
          <Reveal><h2 style={{ marginBottom: "48px" }}>How we work</h2></Reveal>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "32px" }}>
            {[
              { n: "01", title: "Audit", desc: "We read what you have and find where it breaks. Then we put a number on what the current setup costs you every month." },
              { n: "02", title: "Design", desc: "We design against your ceilings, not a reference architecture. If the routing layer cannot hold your p95, we find that out on paper." },
              { n: "03", title: "Build", desc: "We build it with you. The eval harness and the regression pipeline ship in the same week as the feature, because after that nobody goes back for them." },
              { n: "04", title: "Hand over", desc: "We stay ninety days, tune thresholds with your team, then leave you the runbooks and go quiet." },
            ].map((step) => (
              <Reveal key={step.n}>
                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  <span style={{ fontFamily: "var(--mono)", fontSize: "11px", fontWeight: 500, color: "var(--accent)" }}>{step.n}</span>
                  <h3 style={{ fontSize: "1.2rem", fontWeight: 500 }}>{step.title}</h3>
                  <p style={{ fontSize: "14px", color: "var(--ink-3)", lineHeight: 1.7 }}>{step.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>
      {/* Tooling */}
      <section className="section">
        <div className="container">
          <Reveal><div style={{ marginBottom: "48px" }}><h2>Open-source tooling</h2><p style={{ color: "var(--ink-3)", marginTop: "12px" }}>Every library here came out of a client’s problem. We kept them because the next client had the same one.</p></div></Reveal>
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {site.tooling.map((t) => (
              <Reveal key={t.name}>
                <div style={{ border: "1px solid var(--rule)", background: "var(--white)", padding: "20px 24px", display: "flex", justifyContent: "space-between", alignItems: "center", gap: "16px", flexWrap: "wrap" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
                    <code style={{ fontFamily: "var(--mono)", fontSize: "14px", fontWeight: 500, color: "var(--accent)" }}>{t.name}</code>
                    <span className={`tag ${t.status === "stable" ? "tag-ok" : t.status === "beta" ? "tag-beta" : ""}`}>{t.status}</span>
                  </div>
                  <p style={{ fontSize: "14px", color: "var(--ink-3)", flex: 1, minWidth: "200px" }}>{t.desc}</p>
                  <Link href={`/tooling#${t.name}`} style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--accent)", textDecoration: "none" }}>Details →</Link>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>
      {/* Case Studies teaser */}
      <section className="section" style={{ background: "var(--ink)", borderTop: "1px solid rgba(255,255,255,0.06)" }}>
        <div className="container">
          <Reveal><div style={{ marginBottom: "48px" }}><span className="tag tag-accent" style={{ marginBottom: "16px", display: "inline-flex" }}>Case studies</span><h2 style={{ color: "#fff", fontFamily: "var(--serif)" }}>What we’ve shipped</h2></div></Reveal>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(280px, 100%), 1fr))", gap: "24px" }}>
            {[
              { industry: "Fintech", result: "73% bill reduction", detail: "$1.1M a month down to $297K. LiteLLM routing and SPIFFE identity across three regions." },
              { industry: "SaaS", result: "6 weeks to production", detail: "A full AI platform for a 400-engineer company, built by eight of their own people." },
              { industry: "Healthcare", result: "SOC 2 in 4 months", detail: "HIPAA-grade inference with residency enforced in three jurisdictions." },
            ].map((c) => (
              <Reveal key={c.industry}>
                <div style={{ border: "1px solid rgba(255,255,255,0.08)", background: "rgba(255,255,255,0.04)", padding: "24px" }}>
                  <span style={{ fontFamily: "var(--mono)", fontSize: "10px", color: "rgba(255,255,255,0.6)", textTransform: "uppercase", letterSpacing: "0.08em" }}>{c.industry}</span>
                  <p style={{ fontFamily: "var(--serif)", fontSize: "1.4rem", fontWeight: 500, color: "#fff", marginTop: "12px" }}>{c.result}</p>
                  <p style={{ fontFamily: "var(--mono)", fontSize: "12px", color: "rgba(255,255,255,0.7)", marginTop: "8px", lineHeight: 1.6, maxWidth: "none" }}>{c.detail}</p>
                </div>
              </Reveal>
            ))}
          </div>
          <div style={{ marginTop: "40px", textAlign: "center" }}><Link href="/case-studies" className="btn-secondary" style={{ color: "#fff", borderColor: "rgba(255,255,255,0.2)" }}>Read the full case studies →</Link></div>
        </div>
      </section>
      {/* CTA */}
      <section className="section">
        <div className="container" style={{ textAlign: "center", maxWidth: "640px", margin: "0 auto" }}>
          <Reveal>
            <h2 style={{ fontFamily: "var(--serif)" }}>We take on a handful of projects each quarter.</h2>
            <p style={{ marginTop: "20px", color: "var(--ink-3)", fontSize: "17px" }}>If you’re staring at an LLM bill you can’t explain, that’s usually where the conversation starts.</p>
            <div style={{ display: "flex", gap: "12px", justifyContent: "center", marginTop: "32px", flexWrap: "wrap" }}>
              <Link href="/contact" className="btn-primary">Schedule a call</Link>
              <Link href="/research" className="btn-secondary">Read our research</Link>
            </div>
          </Reveal>
        </div>
      </section>
    </>
  );
}
