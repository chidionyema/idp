import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Private investor access",
  robots: { index: false, follow: false, noarchive: true },
};
export const dynamic = "force-dynamic";

export default function InvestorUnavailable() {
  return <div className="mi-interior mi-investor-page">
    <section className="mi-page-hero mi-investor-hero"><div className="mi-shell">
      <span className="mi-eyebrow">MERIDIAN / PRIVATE BRIEFING</span>
      <h1>GOOD CONVERSATIONS<br/><em>START WITH TRUST.</em></h1>
      <div className="mi-page-hero-bottom"><p>We can&apos;t verify your private invitation through this entry point right now. For your security, no Genesis or OTTO information has been shared.</p>
        <Link href="/contact?topic=investor" className="mi-button mi-button-gold">Speak with Meridian <span aria-hidden="true">→</span></Link>
      </div>
    </div></section>
    <section className="mi-section mi-investor-proof"><div className="mi-shell mi-investor-opening-grid">
      <span className="mi-eyebrow">YOUR ACCESS / NEXT STEP</span>
      <div><h2>We protect the work.<br/><em>And the people invited to see it.</em></h2>
        <p>A private briefing is tied to a named guest and a limited access window. We only open approved, read-only views when we can verify both your identity and your current invitation.</p>
        <p>Our team can help arrange access. Until that verification is available, the private room remains closed.</p>
        <div className="mi-investor-actions"><Link href="/contact?topic=investor" className="mi-button mi-button-gold">Ask about a briefing <span aria-hidden="true">→</span></Link><Link href="/investors" className="mi-button mi-button-dark">Explore our vision <span aria-hidden="true">→</span></Link></div>
      </div>
    </div></section>
  </div>;
}
