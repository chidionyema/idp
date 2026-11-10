import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Merdian Intelligence | AI laboratory, consultancy and ventures",
  description: "Merdian Intelligence researches artificial intelligence, engineers systems for organisations, and develops commercial AI ventures.",
};

const disciplines = [
  { n: "01", title: "AI strategy & architecture", text: "Find the right problem, choose the right systems and turn technical uncertainty into a credible investment decision.", marker: "ADVISE" },
  { n: "02", title: "AI engineering & delivery", text: "From intelligent applications to secure, observable platforms. We design, build, integrate and operate what matters.", marker: "BUILD" },
  { n: "03", title: "Autonomous systems", text: "Agent orchestration, workflow automation and human oversight designed for real operating environments.", marker: "AUTOMATE" },
  { n: "04", title: "Research & experimentation", text: "Test frontier capabilities against meaningful baselines. Capture the evidence, including what does not work.", marker: "DISCOVER" },
];

export default function HomePage() {
  return (
    <>
      <section className="mi-hero" aria-labelledby="mi-hero-title">
        <div className="mi-hero-grid" aria-hidden="true" />
        <div className="mi-hero-glow" aria-hidden="true" />
        <div className="mi-shell mi-hero-shell">
          <div className="mi-hero-topline"><span><i className="mi-live-dot" /> MERDIAN INTELLIGENCE</span><span>INDEPENDENT AI LABORATORY + CONSULTANCY</span><span>UK / GLOBAL</span></div>
          <div className="mi-hero-composition">
            <div className="mi-hero-content">
              <div className="mi-hero-overline">RESEARCH THE UNKNOWN. ENGINEER THE POSSIBLE.</div>
              <h1 id="mi-hero-title" className="mi-hero-title">
                INTELLIGENCE<span className="mi-hero-comma">,</span><br/>
                <span className="mi-hero-outline">MADE</span> REAL<span className="mi-gold-stop">.</span>
              </h1>
              <p className="mi-hero-intro">We are an AI research laboratory, technology consultancy and company builder. We turn new intelligence into systems people can use, businesses can trust and ventures that can grow.</p>
              <div className="mi-hero-actions">
                <Link href="/consulting" className="mi-button mi-button-gold">Work with us <span aria-hidden="true">↗</span></Link>
                <Link href="/research" className="mi-button mi-button-outline">Enter the laboratory <span aria-hidden="true">↗</span></Link>
              </div>
            </div>
            <div className="mi-hero-art" aria-hidden="true">
              <div className="mi-art-label mi-art-label-top">M / 001 — INTELLIGENCE IN MOTION</div>
              <div className="mi-orbit mi-orbit-outer"/>
              <div className="mi-orbit mi-orbit-mid"/>
              <div className="mi-orbit mi-orbit-inner"/>
              <div className="mi-orbit-axis mi-orbit-axis-a"/>
              <div className="mi-orbit-axis mi-orbit-axis-b"/>
              <div className="mi-orbit-center"><div className="mi-orbit-core"/><div className="mi-orbit-coreline"/></div>
              <span className="mi-orbit-node mi-node-one"/><span className="mi-orbit-node mi-node-two"/><span className="mi-orbit-node mi-node-three"/>
              <div className="mi-art-label mi-art-label-bottom">OBSERVE <span>→</span> EXPERIMENT <span>→</span> ENGINEER</div>
            </div>
          </div>
          <div className="mi-hero-bottom"><span>01 / A NEW KIND OF AI COMPANY</span><span>SCROLL TO EXPLORE <b aria-hidden="true">↓</b></span></div>
        </div>
      </section>

      <section className="mi-manifesto" aria-labelledby="mi-manifesto-title">
        <div className="mi-shell mi-manifesto-grid">
          <p className="mi-eyebrow">WHAT MAKES US DIFFERENT / 001</p>
          <div>
            <h2 id="mi-manifesto-title">Not another AI pitch.<br/><em>Real intelligence. Real work.</em></h2>
            <p>Merdian exists at the intersection of science and commerce. We experiment continuously, build for real-world constraints and develop our own companies. The laboratory creates the advantage. Consulting brings it to clients. Products take it into new markets.</p>
          </div>
          <div className="mi-manifesto-symbol" aria-hidden="true">M<span>↗</span></div>
        </div>
      </section>

      <section className="mi-services mi-section" aria-labelledby="mi-services-heading">
        <div className="mi-shell">
          <div className="mi-section-intro"><span className="mi-eyebrow">01 / CONSULTANCY</span><p>FOR ORGANISATIONS BUILDING WITH AI</p></div>
          <div className="mi-split-heading"><h2 id="mi-services-heading">Serious ambition.<br/><span>Serious engineering.</span></h2><div><p>From boardroom decisions to production architecture. We work with organisations that need more than prototypes and promises.</p><Link className="mi-text-action" href="/consulting">Explore our consultancy <span aria-hidden="true">↗</span></Link></div></div>
          <div className="mi-services-grid">
            {disciplines.map(d => <Link key={d.n} href="/consulting" className="mi-service-card">
              <div className="mi-service-top"><span>{d.n} / {d.marker}</span><span aria-hidden="true">↗</span></div>
              <div><h3>{d.title}</h3><p>{d.text}</p></div>
              <div className="mi-service-rule"/>
            </Link>)}
          </div>
        </div>
      </section>

      <section className="mi-lab mi-section" aria-labelledby="mi-lab-heading">
        <div className="mi-shell mi-lab-layout">
          <div className="mi-lab-copy">
            <span className="mi-eyebrow">02 / THE LABORATORY</span>
            <h2 id="mi-lab-heading">Curiosity<br/>is an <em>operating</em><br/>principle.</h2>
            <p>Our lab tests emerging models, agent architectures and new ways to automate work. Hypotheses become controlled trials. Results become knowledge. Promising discoveries become products or client capabilities.</p>
            <Link href="/research" className="mi-button mi-button-gold">Explore research <span aria-hidden="true">↗</span></Link>
          </div>
          <div className="mi-lab-board">
            <div className="mi-lab-board-head"><span><i className="mi-live-dot"/> RESEARCH PROGRAMMES</span><span>MERDIAN / LAB</span></div>
            <div className="mi-lab-programme"><span>01</span><div><h3>Autonomous intelligence</h3><p>Agents, orchestration, recovery and human direction</p></div><b>↗</b></div>
            <div className="mi-lab-programme"><span>02</span><div><h3>AI systems & evaluation</h3><p>Quality, cost, latency and repeatable model experiments</p></div><b>↗</b></div>
            <div className="mi-lab-programme"><span>03</span><div><h3>Trust & infrastructure</h3><p>Identity, reliability, observability and operational proof</p></div><b>↗</b></div>
            <div className="mi-lab-board-foot"><span>METHOD / HYPOTHESIS → EXPERIMENT → EVIDENCE</span><span>↗</span></div>
          </div>
        </div>
      </section>

      <section className="mi-ventures mi-section" aria-labelledby="mi-ventures-heading">
        <div className="mi-shell">
          <div className="mi-section-intro"><span className="mi-eyebrow">03 / VENTURES + PRODUCTS</span><p>FROM THE LABORATORY TO THE MARKET</p></div>
          <div className="mi-split-heading"><h2 id="mi-ventures-heading">We don&apos;t only advise.<br/><span>We build businesses.</span></h2><div><p>Merdian is the parent company. Our ventures and products tackle different markets, each at its own stage of maturity.</p><Link className="mi-text-action" href="/products">Discover the portfolio <span aria-hidden="true">↗</span></Link></div></div>
          <div className="mi-venture-grid">
            <article className="mi-venture mi-venture-mumchimp"><div className="mi-venture-top"><span>GROUP COMPANY / COMMERCE</span><span>01</span></div><div><div className="mi-venture-mark">m<span>.</span></div><h3>Mumchimp</h3><p>Research-backed business opportunities, built for people ready to act.</p></div><a href="https://mumchimp.com" target="_blank" rel="noopener noreferrer">Visit Mumchimp <span aria-hidden="true">↗</span></a></article>
            <article className="mi-venture mi-venture-genesis"><div className="mi-venture-top"><span>LABORATORY PRODUCT / AUTONOMY</span><span>02</span></div><div><div className="mi-venture-mark mi-genesis-mark">G<span>•</span></div><h3>Genesis</h3><p>The Autonomous Estate: an experimental operating system for coordinated AI agents and work.</p></div><Link href="/products">Explore the vision <span aria-hidden="true">↗</span></Link></article>
            <article className="mi-venture mi-venture-blabka"><div className="mi-venture-top"><span>PORTFOLIO PRODUCT / IN DEVELOPMENT</span><span>03</span></div><div><div className="mi-venture-mark">b<span>⁎</span></div><h3>Blabka</h3><p>Part of the Merdian product portfolio. More information will be shared as the product develops.</p></div><Link href="/products">View the portfolio <span aria-hidden="true">↗</span></Link></article>
          </div>
        </div>
      </section>

      <section className="mi-close" aria-labelledby="mi-close-heading">
        <div className="mi-shell mi-close-inner"><span className="mi-eyebrow">NEXT / WORK WITH MERDIAN</span><h2 id="mi-close-heading">THE NEXT<br/>MOVE IS <em>YOURS.</em></h2><div className="mi-close-bottom"><p>Have an AI problem worth solving, a platform worth building or an idea worth testing? Bring it to Merdian.</p><Link href="/contact" className="mi-button mi-button-gold">Start a conversation <span aria-hidden="true">↗</span></Link></div></div>
      </section>
    </>
  );
}
