import Link from "next/link";
import type { Metadata } from "next";
export const metadata: Metadata = {
  title: "Commercial evidence",
  description: "Independent verification precedes public commercial performance claims.",
};
export default function CaseStudiesPage() {
  return (
    <section className="container section">
      <div style={{ maxWidth: "780px" }}>
        <span className="tag tag-accent">Commercial evidence</span>
        <h1 style={{ fontFamily: "var(--serif)", marginTop: "20px" }}>Results must stand up to scrutiny.</h1>
        <p style={{ color: "var(--ink-3)", fontSize: "18px", lineHeight: 1.8, marginTop: "22px" }}>
          We distinguish experiments, prototypes and products in customer use. We publish commercial
          performance only after checking the baseline, the measurements and permission to disclose.
          The absence of a case study is not a claim of commercial deployment.
        </p>
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginTop: "32px" }}>
          <Link href="/research" className="btn-primary">View research</Link>
          <Link href="/products" className="btn-secondary">Explore products</Link>
        </div>
      </div>
    </section>
  );
}
