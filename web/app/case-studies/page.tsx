import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Commercial evidence",
  description: "Merian Intelligence publishes commercial case studies with independently checked outcomes and permission to disclose.",
};
export default function CaseStudiesPage() {
  return (
    <section className="container section">
      <div style={{ maxWidth: "760px" }}>
        <span className="tag tag-accent">Commercial evidence</span>
        <h1 style={{ fontFamily: "var(--serif)", marginTop: "20px" }}>Claims should survive scrutiny.</h1>
        <p style={{ color: "var(--ink-3)", lineHeight: 1.8, fontSize: "18px", marginTop: "20px" }}>
          Research, prototypes and customer systems carry different proof requirements. Commercial case studies will be published here
          when their baselines, measurements and permission to disclose have been independently checked.
          Until then, we will not present unsupported performance figures as customer outcomes.
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", marginTop: "32px" }}>
          <Link className="btn-primary" href="/research">Explore our research</Link>
          <Link className="btn-secondary" href="/products">See the portfolio</Link>
        </div>
      </div>
    </section>
  );
}
