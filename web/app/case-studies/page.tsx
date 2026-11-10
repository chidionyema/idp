import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Our approach",
  description: "How Merdian Intelligence distinguishes experiments, prototypes and customer-ready engineering.",
};

export default function CaseStudiesPage() {
  return <div className="mi-interior">
    <section className="mi-page-hero" aria-labelledby="approach-heading">
      <div className="mi-shell">
        <span className="mi-eyebrow">MERDIAN / HOW WE WORK</span>
        <h1 id="approach-heading">SHOW THE WORK.<br/><em>PROVE THE RESULT.</em></h1>
        <div className="mi-page-hero-bottom">
          <p>Claims are easy. Evidence takes work. We keep research findings, prototypes and operating products distinct, so decisions are based on what has been demonstrated.</p>
          <Link href="/contact" className="mi-button mi-button-gold">Discuss a project <span aria-hidden="true">↗</span></Link>
        </div>
      </div>
    </section>
    <section className="mi-proof-band">
      <div className="mi-shell">
        <span className="mi-eyebrow">THREE DIFFERENT LEVELS OF PROOF</span>
        <div className="mi-proof-grid">
          <div><h3>Research.</h3><p>A clear hypothesis, a control or baseline, repeatable methods and results that include negative findings.</p></div>
          <div><h3>Prototype.</h3><p>A working demonstration with visible limitations. A prototype does not establish operational readiness.</p></div>
          <div><h3>Commercial.</h3><p>Customer use, security, reliability and independently checked results before performance claims are published.</p></div>
        </div>
      </div>
    </section>
    <section className="mi-section mi-services">
      <div className="mi-shell mi-approach-close">
        <span className="mi-eyebrow">NEXT / FROM EVIDENCE TO ACTION</span>
        <h2>START WITH THE<br/><em>RIGHT QUESTION.</em></h2>
        <p>We only publish commercial case-study figures when we can verify the baseline, the measurement and permission to disclose. Until then, we show the method.</p>
        <div className="mi-hero-actions">
          <Link href="/research" className="mi-button mi-button-gold">See the research <span aria-hidden="true">↗</span></Link>
          <Link href="/consulting" className="mi-button mi-button-dark">Explore consultancy <span aria-hidden="true">↗</span></Link>
        </div>
      </div>
    </section>
  </div>;
}
