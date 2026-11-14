import Link from "next/link";
import type { Metadata } from "next";
export const metadata: Metadata = {title:"Ventures and products",description:"Mumchimp and Genesis: separate commercial and experimental initiatives within Meridian Intelligence."};
export default function ProductsPage(){
 return <div className="mi-interior">
  <section className="mi-page-hero"><div className="mi-shell"><span className="mi-eyebrow">MERIDIAN / VENTURES</span><h1>WE BUILD<br/><em>THE BUSINESSES</em><br/>TOO.</h1><div className="mi-page-hero-bottom"><p>Our method moves from measurable research through engineering into selected ventures. Commercial storefronts and experimental operating systems are identified separately; no undisclosed concept is presented as a shipped product.</p><Link href="/contact" className="mi-button mi-button-gold">Explore a partnership <span aria-hidden="true">→</span></Link></div></div></section>
  <section className="mi-section mi-portfolio-list"><div className="mi-shell">
   <div className="mi-portfolio-row"><div className="mi-portfolio-number">04.1 / GROUP COMPANY</div><div><h2>Mumchimp<span className="mi-gold-stop">.</span></h2><p>Research-backed business opportunities and products for people ready to build. A separately operated commercial business within the group.</p><span className="mi-portfolio-status">COMMERCIAL STOREFRONT</span></div><a href="https://mumchimp.com" target="_blank" rel="noopener noreferrer">Visit company ↗</a></div>
   <div className="mi-portfolio-row"><div className="mi-portfolio-number">04.2 / LABORATORY PRODUCT</div><div><h2>Genesis<span className="mi-gold-stop">.</span></h2><p>The Autonomous Estate. A research-driven operating environment for fleets of AI agents, coordinated work and continuous operational intelligence.</p><span className="mi-portfolio-status">RESEARCH + EXPERIMENTAL OPERATIONS</span></div><Link href="/research">Explore research →</Link></div>
   <div className="mi-portfolio-row"><div className="mi-portfolio-number">04.3 / PRODUCT CONCEPT</div><div><h2>Chronos<span className="mi-gold-stop">.</span></h2><p>A better rhythm for work. We&apos;re exploring how to give teams clearer priorities, smoother handovers and more time for meaningful work.</p><span className="mi-portfolio-status">IN DEVELOPMENT / CONCEPT WALKTHROUGH</span></div><Link href="/products/chronos">Explore Chronos →</Link></div>
  </div></section>
  <section className="mi-proof-band"><div className="mi-shell"><span className="mi-eyebrow">ONE PARENT / MULTIPLE OPPORTUNITIES</span><h2 className="mi-wide-statement">WE INVEST IN IDEAS.<br/>WE TEST THEM.<br/><em>WE BUILD THE ONES THAT WORK.</em></h2></div></section>
 </div>;
}
