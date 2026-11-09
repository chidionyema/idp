import Link from "next/link";
import type { Metadata } from "next";
import { site } from "@/content/site";
import { HeroPlayground } from "@/components/HeroPlayground";
import { Reveal } from "@/components/Reveal";

export const metadata: Metadata = { description: site.tagline };

const work = [
  { n: "01", title: "Hypothesise", detail: "Find the question worth answering. Name the baseline and what would disprove the idea." },
  { n: "02", title: "Experiment", detail: "Run repeatable trials. Preserve the controls, parameters, costs and negative findings." },
  { n: "03", title: "Prototype", detail: "Build only what the evidence supports. Show what works and where it fails." },
  { n: "04", title: "Commercialise", detail: "Independent checks come before production claims: security, reliability, customer outcomes and rollback." },
];

export default function HomePage() {
  return (
    <>
      <section style={{ borderBottom: "1px solid var(--rule)" }}>
        <div className="container section hero-grid">
          <div className="hero-copy">
            <span className="tag tag-accent">Merian Intelligence · Applied AI Laboratory</span>
            <h1 style={{ fontFamily: "var(--serif)" }}>Research first.<br /><em style={{ fontStyle: "normal", color: "var(--accent)" }}>Products that earn their place.</em></h1>
            <p style={{ fontSize: "18px", lineHeight: 1.75, color: "var(--ink-3)", maxWidth: "55ch" }}>
              We investigate AI, test new capabilities and develop useful products for businesses and individuals.
              Our lab is free to experiment. Commercial work has to stand up to a much harder standard of proof.
            </p>
            <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
              <Link href="/research" className="btn-primary">Explore our research</Link>
              <Link href="/products" className="btn-secondary">Products and companies</Link>
            </div>
          </div>
          <div className="hero-demo">
            <p style={{ fontFamily: "var(--mono)", fontSize: "11px", letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--ink-3)", marginBottom: "20px" }}>Illustrative LLM routing demo · not a live deployment claim</p>
            <HeroPlayground />
          </div>
        </div>
      </section>
      <section style={{ background: "var(--ink)", padding: "30px 0" }}>
        <div className="container" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: "36px" }}>
          {[
            { title: "Research", detail: "Test hypotheses with reproducible observations." },
            { title: "Prototype", detail: "Demonstrate what works and name the gaps." },
            { title: "Commercial", detail: "Demand reliable, independently verified user outcomes." },
          ].map(x => <div key={x.title}><p style={{ fontFamily: "var(--serif)", fontSize: "24px", color: "#fff" }}>{x.title}</p><p style={{ marginTop: "8px", fontSize: "13px", lineHeight: 1.7, color: "var(--on-ink)" }}>{x.detail}</p></div>)}
        </div>
      </section>
      <section className="section"><div className="container">
        <Reveal><h2 style={{ fontFamily: "var(--serif)", marginBottom: "14px" }}>Research never stops.</h2><p style={{ color: "var(--ink-3)", marginBottom: "40px" }}>Each experiment gives us a result worth keeping, even when the hypothesis fails. Research is not a marketing synonym for delivered software.</p></Reveal>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(min(280px,100%),1fr))", gap: "24px" }}>
          {site.research.map(r => <Reveal key={r.title}><article className="card" style={{ display: "flex", flexDirection: "column", gap: "15px" }}><span className="tag">{r.kind}</span><h3 style={{ fontFamily: "var(--serif)", fontSize: "22px" }}>{r.title}</h3><p style={{ color: "var(--ink-3)", fontSize: "14px", lineHeight: 1.8 }}>{r.blurb}</p>{r.href && <Link href={r.href} className="text-link">Research notes →</Link>}</article></Reveal>)}
        </div>
      </div></section>
      <section className="section" style={{ background: "var(--panel)" }}><div className="container">
        <Reveal><h2 style={{ fontFamily: "var(--serif)", marginBottom: "40px" }}>How the lab works</h2></Reveal>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(210px,1fr))", gap: "32px" }}>
          {work.map(x => <Reveal key={x.n}><div><span style={{ color: "var(--accent)", fontFamily: "var(--mono)", fontSize: "12px" }}>{x.n}</span><h3 style={{ marginTop: "12px", marginBottom: "12px", fontSize: "21px" }}>{x.title}</h3><p style={{ color: "var(--ink-3)", lineHeight: 1.7, fontSize: "14px" }}>{x.detail}</p></div></Reveal>)}
        </div>
      </div></section>
      <section className="section" style={{ background: "var(--ink)", color: "#fff" }}><div className="container">
        <Reveal><h2 style={{ fontFamily: "var(--serif)", color: "#fff" }}>One laboratory. Different businesses and products.</h2><p style={{ color: "var(--on-ink)", marginTop: "16px", maxWidth: "75ch" }}>Merian Intelligence is the parent lab. Mumchimp is a group company serving its own customers. Genesis, the Autonomous Estate, is an experimental product and operating capability.</p></Reveal>
        <div style={{ marginTop: "36px" }}><Link href="/products" className="btn-secondary" style={{ color: "#fff", borderColor: "rgba(255,255,255,0.2)" }}>View the portfolio →</Link></div>
      </div></section>
      <section className="section"><div className="container" style={{ textAlign: "center", maxWidth: "680px" }}>
        <Reveal><h2 style={{ fontFamily: "var(--serif)" }}>What problem would you like to solve?</h2><p style={{ color: "var(--ink-3)", fontSize: "17px", lineHeight: 1.8, marginTop: "18px" }}>Bring a research question, an AI product hypothesis or a commercial system that needs proper validation.</p><div style={{ marginTop: "28px" }}><Link href="/contact" className="btn-primary">Start a conversation →</Link></div></Reveal>
      </div></section>
    </>
  );
}
