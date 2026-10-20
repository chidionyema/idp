import Link from "next/link";
import { site } from "@/content/site";
import { Reveal } from "@/components/Reveal";
import type { Metadata } from "next";
export const metadata: Metadata = { title: "Consulting", description: "AI platform architecture, security and compliance, evaluation and fine-tuning." };

export default function ConsultingPage() {
  return (
    <div className="container section">
      <Reveal><div style={{ marginBottom: "64px" }}>
        <span className="tag tag-accent" style={{ marginBottom: "16px", display: "inline-flex" }}>Consulting</span>
        <h1>What we do</h1>
        <p style={{ marginTop: "16px", color: "var(--ink-3)", fontSize: "18px", maxWidth: "60ch" }}>A team of two or three who’ve done this before, working alongside your engineers.</p>
      </div></Reveal>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "24px", marginBottom: "64px" }}>
        {site.consulting.map((c, i) => (
          <Reveal key={i}>
            <div className="card" style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <span style={{ fontFamily: "var(--mono)", fontSize: "11px", fontWeight: 500, color: "var(--accent)" }}>0{i + 1}</span>
              <h3 style={{ fontSize: "1.3rem" }}>{c.title}</h3>
              <p style={{ fontSize: "14px", color: "var(--ink-3)", lineHeight: 1.75, flex: 1 }}>{c.desc}</p>
              <Link href="/contact" style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--accent)", textDecoration: "none" }}>Discuss this →</Link>
            </div>
          </Reveal>
        ))}
      </div>
      <div style={{ borderTop: "1px solid var(--rule)", paddingTop: "64px" }}>
        <Reveal>
          <div style={{ border: "1px solid var(--rule)", background: "var(--ink)", padding: "64px", textAlign: "center" }}>
            <span className="tag tag-accent" style={{ marginBottom: "24px", display: "inline-flex" }}>Talk to us</span>
            <h2 style={{ fontFamily: "var(--serif)", color: "#fff", maxWidth: "none" }}>We take on a small number of projects each quarter.</h2>
            <p style={{ color: "rgba(255,255,255,0.75)", marginTop: "20px", fontSize: "17px", maxWidth: "none" }}>If you’re working on production AI infrastructure and want people who’ve done it before, let’s talk.</p>
            <div style={{ display: "flex", gap: "12px", justifyContent: "center", marginTop: "32px", flexWrap: "wrap" }}>
              <Link href="/contact" className="btn-primary">Book a call →</Link>
              <Link href="/case-studies" className="btn-secondary" style={{ color: "#fff", borderColor: "rgba(255,255,255,0.2)" }}>See our work</Link>
            </div>
          </div>
        </Reveal>
      </div>
    </div>
  );
}
