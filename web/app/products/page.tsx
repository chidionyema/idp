import Link from "next/link";
import type { Metadata } from "next";
export const metadata: Metadata = {title:"Ventures and products",description:"Mumchimp, Genesis and Blabka are part of the Merian Intelligence portfolio."};
export default function ProductsPage(){
 return <div className="mi-interior">
  <section className="mi-page-hero"><div className="mi-shell"><span className="mi-eyebrow">MERIAN / VENTURES</span><h1>WE BUILD<br/><em>THE BUSINESSES</em><br/>TOO.</h1><div className="mi-page-hero-bottom"><p>Research creates possibilities. Product engineering gives those possibilities a form. Our group ventures explore different markets, with clear distinctions between commercial operations and ongoing experiments.</p><Link href="/contact" className="mi-button mi-button-gold">Explore a partnership <span aria-hidden="true">↗</span></Link></div></div></section>
  <section className="mi-section mi-portfolio-list"><div className="mi-shell">
   <div className="mi-portfolio-row"><div className="mi-portfolio-number">01 / GROUP COMPANY</div><div><h2>Mumchimp<span className="mi-gold-stop">.</span></h2><p>Research-backed business opportunities and products for people ready to build. A separately operated commercial business within the group.</p><span className="mi-portfolio-status">COMMERCIAL STOREFRONT</span></div><a href="https://mumchimp.com" target="_blank" rel="noopener noreferrer">Visit company ↗</a></div>
   <div className="mi-portfolio-row"><div className="mi-portfolio-number">02 / LABORATORY PRODUCT</div><div><h2>Genesis<span className="mi-gold-stop">.</span></h2><p>The Autonomous Estate. A research-driven operating environment for fleets of AI agents, coordinated work and continuous operational intelligence.</p><span className="mi-portfolio-status">RESEARCH + EXPERIMENTAL OPERATIONS</span></div><Link href="/research">Explore research ↗</Link></div>
   <div className="mi-portfolio-row"><div className="mi-portfolio-number">03 / PRODUCT VENTURE</div><div><h2>Blabka<span className="mi-gold-stop">.</span></h2><p>A product in the Merian portfolio. Further details will be published as development and commercial readiness progress.</p><span className="mi-portfolio-status">IN DEVELOPMENT</span></div><Link href="/contact">Enquire ↗</Link></div>
  </div></section>
  <section className="mi-proof-band"><div className="mi-shell"><span className="mi-eyebrow">ONE PARENT / MULTIPLE OPPORTUNITIES</span><h2 className="mi-wide-statement">WE INVEST IN IDEAS.<br/>WE TEST THEM.<br/><em>WE BUILD THE ONES THAT WORK.</em></h2></div></section>
 </div>;
}
