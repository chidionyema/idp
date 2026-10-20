import Link from "next/link";
import { site } from "@/content/site";
import { ResearchQA } from "@/components/ResearchQA";
import { Reveal } from "@/components/Reveal";
import type { Metadata } from "next";
export const metadata: Metadata = { title: "Research", description: "Production-tested frameworks for agentic routing, workload identity, and LLM observability." };

export default function ResearchPage() {
  return (
    <div className="container section">
      <Reveal><div style={{ marginBottom: "64px" }}>
        <span className="tag tag-accent" style={{ marginBottom: "16px", display: "inline-flex" }}>Research</span>
        <h1>What we’ve actually shipped</h1>
        <p style={{ marginTop: "16px", color: "var(--ink-3)", fontSize: "18px", maxWidth: "60ch" }}>Frameworks, architectures, and operational playbooks — tested against real production traffic.</p>
      </div></Reveal>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "24px", marginBottom: "80px" }}>
        {site.research.map((r) => (
          <Reveal key={r.title}>
            <div className="card" style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <span className="tag">{r.kind}</span>
                <span style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)" }}>{r.year}</span>
              </div>
              <h3 style={{ fontSize: "1.3rem" }}>{r.title}</h3>
              <p style={{ fontSize: "14px", color: "var(--ink-3)", lineHeight: 1.75, flex: 1 }}>{r.blurb}</p>
              {r.href && (
                <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
                  <Link href={r.href} className="btn-secondary" style={{ padding: "8px 16px", fontSize: "11px" }}>Read →</Link>
                </div>
              )}
            </div>
          </Reveal>
        ))}
      </div>
      <div style={{ borderTop: "1px solid var(--rule)", paddingTop: "64px" }}>
        <Reveal><div style={{ marginBottom: "40px" }}><h2>Research Q&amp;A</h2><p style={{ color: "var(--ink-3)", marginTop: "12px" }}>Ask a question about our work. Answers are grounded in what we’ve actually shipped, with sources.</p></div></Reveal>
        <ResearchQA />
      </div>
    </div>
  );
}
