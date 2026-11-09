import Link from "next/link";
import type { Metadata } from "next";
export const metadata: Metadata = {
  title: "Products and companies",
  description: "Merian Intelligence portfolio: Mumchimp group company and Genesis Autonomous Estate research product.",
};
const portfolio = [
  {
    label: "Group company",
    name: "Mumchimp",
    state: "Commercial storefront",
    body: "Research-led business opportunity packs published through Mumchimp's own customer operation.",
    href: "https://mumchimp.com",
    link: "Visit Mumchimp",
  },
  {
    label: "Laboratory product",
    name: "Genesis / Autonomous Estate",
    state: "Research and operating capability",
    body: "Agent coordination and experimental orchestration. Commercial readiness is assessed separately from demos or commits.",
    href: "https://github.com/chidionyema/argon",
    link: "Explore Genesis source",
  },
];
export default function ProductsPage() {
  return (
    <div className="container section">
      <div style={{ maxWidth: "820px", marginBottom: "60px" }}>
        <span className="tag tag-accent">Merian Intelligence / Portfolio</span>
        <h1 style={{ fontFamily: "var(--serif)", marginTop: "16px" }}>From discovery to useful products.</h1>
        <p style={{ fontSize: "18px", color: "var(--ink-3)", lineHeight: 1.8, marginTop: "18px" }}>
          Products can occupy different stages of maturity. We distinguish group companies, experimental products and commercial customer operations.
        </p>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(min(300px,100%),1fr))", gap: "24px" }}>
        {portfolio.map(p => <article key={p.name} className="card" style={{ padding: "32px", display: "flex", flexDirection: "column", gap: "16px" }}>
          <span className="tag tag-accent">{p.label}</span>
          <h2 style={{ fontFamily: "var(--serif)", fontSize: "26px" }}>{p.name}</h2>
          <span style={{ fontSize: "12px", fontFamily: "var(--mono)", color: "var(--ink-3)" }}>{p.state}</span>
          <p style={{ color: "var(--ink-3)", fontSize: "15px", lineHeight: 1.8, flex: 1 }}>{p.body}</p>
          <a href={p.href} target="_blank" rel="noopener noreferrer" className="text-link">{p.link} →</a>
        </article>)}
      </div>
      <div style={{ marginTop: "60px", borderTop: "1px solid var(--rule)", paddingTop: "50px" }}>
        <h2 style={{ fontFamily: "var(--serif)" }}>Experiments earn their next stage.</h2>
        <p style={{ color: "var(--ink-3)", lineHeight: 1.7, marginTop: "16px" }}>A successful prototype still needs independent proof before customers can rely on it.</p>
        <div style={{ marginTop: "24px" }}><Link href="/research" className="btn-primary">Read the research →</Link></div>
      </div>
    </div>
  );
}
