import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Engineering work",
  description: "Explore technical patterns behind Meridian Intelligence AI systems engineering, with the distinction between demonstrations and real operating evidence made explicit.",
};

const work = [
  {
    number: "01",
    discipline: "Model infrastructure",
    title: "Routing under changing conditions",
    problem: "The fastest or cheapest model is not always the correct choice. Providers also degrade, time out and impose limits.",
    method: "Evaluate the request class, define the budget, route deliberately and preserve enough information to inspect the decision.",
    link: "/demo",
    linkLabel: "Explore the routing simulation",
  },
  {
    number: "02",
    discipline: "Observability",
    title: "Tracing a multi-step decision",
    problem: "A final answer does not explain which model was selected, what a tool returned or where time was lost.",
    method: "Connect spans, state transitions and failures into a single execution trace that an engineer can investigate.",
    link: "/tools/trace-explorer",
    linkLabel: "Inspect example traces",
  },
  {
    number: "03",
    discipline: "Operational assurance",
    title: "Proving the result independently",
    problem: "A successful build is not evidence that an operator's instruction was fulfilled. A retry that runs is not necessarily recovery.",
    method: "Specify the result and its acceptance conditions in advance, exercise adverse scenarios and verify behaviour at the operational boundary.",
    link: "/consulting",
    linkLabel: "Discuss an assurance engagement",
  },
];

export default function EngineeringWorkPage() {
  return (
    <div className="container section" style={{ maxWidth: 1180 }}>
      <div style={{ marginBottom: 65 }}>
        <p className="tag tag-accent" style={{ display: "inline-flex", marginBottom: 18 }}>Engineering / evidence</p>
        <h1 style={{ maxWidth: "18ch" }}>What it takes to make AI operational.</h1>
        <p style={{ color: "var(--ink-3)", fontSize: 18, marginTop: 20, maxWidth: "60ch" }}>Engineering decisions worth showing, even before the polished result.</p>
        <p style={{ color: "var(--ink-3)", fontSize: 13, marginTop: 16, maxWidth: "80ch" }}>These are technical reference patterns and clearly labelled demonstrations. They are not client case studies, verified production metrics or independent compliance attestations. Named customer outcomes will appear here only when disclosure permission and supporting evidence are available.</p>
      </div>
      <div style={{ display: "grid", gap: 1, background: "var(--rule)", border: "1px solid var(--rule)" }}>
        {work.map((item) => (
          <article key={item.number} style={{ background: "var(--white)", padding: "clamp(25px, 4vw, 48px)" }}>
            <div style={{ fontFamily: "var(--mono)", color: "var(--accent)", fontSize: 11 }}>{item.number} / {item.discipline}</div>
            <h2 style={{ fontSize: "clamp(1.6rem, 3vw, 2.7rem)", maxWidth: "24ch", marginTop: 24 }}>{item.title}</h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(min(270px,100%),1fr))", gap: 32, marginTop: 25 }}>
              <div><p style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--accent)", marginBottom: 11 }}>THE PROBLEM</p><p style={{ fontSize: 15, lineHeight: 1.8 }}>{item.problem}</p></div>
              <div><p style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--accent)", marginBottom: 11 }}>THE ENGINEERING APPROACH</p><p style={{ fontSize: 15, lineHeight: 1.8 }}>{item.method}</p></div>
            </div>
            <Link href={item.link} className="text-link" style={{ display: "inline-flex", marginTop: 30, fontSize: 12, color: "var(--accent)" }}>{item.linkLabel} →</Link>
          </article>
        ))}
      </div>
      <div style={{ marginTop: 80, borderTop: "1px solid var(--rule)", paddingTop: 55 }}>
        <h2>Have a specific system in mind?</h2>
        <p style={{ marginTop: 14, color: "var(--ink-3)" }}>Start with the operating problem. The technical approach follows.</p>
        <Link href="/contact" className="btn-primary" style={{ marginTop: 24 }}>Talk to Meridian →</Link>
      </div>
    </div>
  );
}
