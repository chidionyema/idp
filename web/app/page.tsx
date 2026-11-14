import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Meridian Intelligence | AI laboratory, consultancy and ventures",
  description: "Meridian Intelligence researches artificial intelligence, engineers systems for organisations, and develops commercial AI ventures.",
};

const disciplines = [
  { n: "02.1", title: "AI strategy & architecture", text: "Architecture and model-economics assessment, risk register, implementation options, and a measurable investment decision.", marker: "ADVISE" },
  { n: "02.2", title: "AI engineering & delivery", text: "Integration architecture, secure delivery pipelines, observability, test harnesses, and documented operational handover.", marker: "BUILD" },
  { n: "02.3", title: "Autonomous systems", text: "Agent workflow design with bounded retries, human escalation, execution traces, and verifiable outcome criteria.", marker: "AUTOMATE" },
  { n: "02.4", title: "Research & experimentation", text: "Baseline-defined model evaluations, adversarial test cases, reproducible runs, and explicit failure reporting.", marker: "DISCOVER" },
];

export default function HomePage() {
  return (
    <>
      <section className="mi-hero" aria-labelledby="mi-hero-title">
        <div className="mi-hero-grid" aria-hidden="true" />
        <div className="mi-hero-glow" aria-hidden="true" />
        <div className="mi-shell mi-hero-shell">
          <div className="mi-hero-topline"><span><i className="mi-live-dot" /> MERIDIAN INTELLIGENCE</span><span>INDEPENDENT AI LABORATORY + CONSULTANCY</span><span>UK / GLOBAL</span></div>
          <div className="mi-hero-composition">
            <div className="mi-hero-content">
              <div className="mi-hero-overline">RESEARCH THE UNKNOWN. ENGINEER THE POSSIBLE.</div>
              <h1 id="mi-hero-title" className="mi-hero-title">
                INTELLIGENCE<span className="mi-hero-comma">,</span><br/>
                <span className="mi-hero-outline">MADE</span> REAL<span className="mi-gold-stop">.</span>
              </h1>
              <p className="mi-hero-intro">One method, three outcomes: investigate with measurable experiments, engineer reliable systems for clients, and develop ventures when the evidence supports them.</p>
              <div className="mi-hero-actions">
                <Link href="/consulting" className="mi-button mi-button-gold">Work with us <span aria-hidden="true">→</span></Link>
                <Link href="/research" className="mi-button mi-button-outline">Enter the laboratory <span aria-hidden="true">→</span></Link>
              </div>
            </div>
            <div className="mi-hero-art" aria-hidden="true">
              <div className="mi-art-label mi-art-label-top">STUDY / INTELLIGENCE IN MOTION</div>
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
          <div className="mi-hero-bottom"><span>RESEARCH / ENGINEER / BUILD</span><span>SCROLL TO EXPLORE <b aria-hidden="true">↓</b></span></div>
        </div>
      </section>

      <section className="mi-manifesto" aria-labelledby="mi-manifesto-title">
        <div className="mi-shell mi-manifesto-grid">
          <p className="mi-eyebrow">01 / MANIFESTO</p>
          <div>
            <h2 id="mi-manifesto-title">Not another AI pitch.<br/><em>Real intelligence. Real work.</em></h2>
            <p>Meridian exists at the intersection of science and commerce. We experiment continuously, build for real-world constraints and develop our own companies. The laboratory creates the advantage. Consulting brings it to clients. Products take it into new markets.</p>
          </div>
          <div className="mi-manifesto-symbol" aria-hidden="true">M</div>
        </div>
      </section>


      <section className="mi-future-section mi-section" aria-labelledby="meridian-future-work">
        <div className="mi-shell mi-future-grid">
          <div><span className="mi-eyebrow">OUR NEXT CHAPTER / A BETTER WAY TO WORK</span>
            <h2 id="meridian-future-work">Research the future.<br/><em>Build something better.</em></h2>
            <p>Meridian&apos;s work begins with research, grows through experimentation and finds its purpose in products and businesses that improve people&apos;s lives.</p>
            <p>One question we keep returning to: what if people could spend less time chasing work and more time doing it?</p>
            <div className="mi-future-actions">
              <Link href="/products/chronos" className="mi-button mi-button-gold">Meet Chronos <span aria-hidden="true">→</span></Link>
              <Link href="/investors" className="mi-button mi-button-dark">Explore our vision <span aria-hidden="true">→</span></Link>
            </div>
          </div>
          <div className="mi-future-panel" aria-label="Meridian's three steps from idea to business">
            <span>MERIDIAN / THE IDEA-TO-IMPACT JOURNEY</span>
            <div><strong>01 / Research</strong><p>Ask the questions that matter.</p></div>
            <div><strong>02 / Experiment</strong><p>See what works, and learn honestly.</p></div>
            <div><strong>03 / Commercialise</strong><p>Make promising ideas useful to people.</p></div>
          </div>
        </div>
      </section>

      <section className="mi-services mi-section" aria-labelledby="mi-services-heading">
        <div className="mi-shell">
          <div className="mi-section-intro"><span className="mi-eyebrow">02 / CONSULTANCY</span><p>FOR ORGANISATIONS BUILDING WITH AI</p></div>
          <div className="mi-split-heading"><h2 id="mi-services-heading">Serious ambition.<br/><span>Serious engineering.</span></h2><div><p>From boardroom decisions to production architecture. We define acceptance criteria before delivery: architecture, cost and latency budgets, security boundaries, automated evaluation, and operational ownership.</p><Link className="mi-text-action" href="/consulting">Explore our consultancy <span aria-hidden="true">→</span></Link></div></div>
          <div className="mi-services-grid">
            {disciplines.map(d => <Link key={d.n} href="/consulting" className="mi-service-card">
              <div className="mi-service-top"><span>{d.n} / {d.marker}</span><span aria-hidden="true">→</span></div>
              <div><h3>{d.title}</h3><p>{d.text}</p></div>
              <div className="mi-service-rule"/>
            </Link>)}
          </div>
        </div>
      </section>

      <section className="mi-lab mi-section" aria-labelledby="mi-lab-heading">
        <div className="mi-shell mi-lab-layout">
          <div className="mi-lab-copy">
            <span className="mi-eyebrow">03 / THE LABORATORY</span>
            <h2 id="mi-lab-heading">Curiosity<br/>is an <em>operating</em><br/>principle.</h2>
            <p>We compare candidate models and agent architectures against explicit baselines. Each experiment records parameters, quality, failure cases, latency, and cost. Results guide engineering decisions; experiments are not presented as production deployments.</p>
            <Link href="/research" className="mi-button mi-button-gold">Explore research <span aria-hidden="true">→</span></Link>
          </div>
          <div className="mi-lab-board">
            <div className="mi-lab-board-head"><span><i className="mi-live-dot"/> RESEARCH PROGRAMMES</span><span>MERIDIAN / LAB</span></div>
            <div className="mi-lab-programme"><span>03.1</span><div><h3>Autonomous intelligence</h3><p>Agent execution, bounded recovery, human escalation, and outcome evidence</p></div></div>
            <div className="mi-lab-programme"><span>03.2</span><div><h3>AI systems & evaluation</h3><p>Baseline comparisons, adversarial test sets, quality, latency, and cost</p></div></div>
            <div className="mi-lab-programme"><span>03.3</span><div><h3>Trust & infrastructure</h3><p>Workload identity, traceability, recovery, and release verification</p></div></div>
            <div className="mi-lab-board-foot"><span>METHOD / HYPOTHESIS → EXPERIMENT → EVIDENCE</span></div>
          </div>
        </div>
      </section>

      <section className="mi-ventures mi-section" aria-labelledby="mi-ventures-heading">
        <div className="mi-shell">
          <div className="mi-section-intro"><span className="mi-eyebrow">04 / VENTURES + PRODUCTS</span><p>FROM THE LABORATORY TO THE MARKET</p></div>
          <div className="mi-split-heading"><h2 id="mi-ventures-heading">We don&apos;t only advise.<br/><span>We build businesses.</span></h2><div><p>Meridian connects research, client delivery, and venture development through the same evaluate–engineer–verify method. Each initiative is identified by its actual maturity.</p><Link className="mi-text-action" href="/products">Discover the portfolio <span aria-hidden="true">→</span></Link></div></div>
          <div className="mi-venture-grid">
            <article className="mi-venture mi-venture-mumchimp"><div className="mi-venture-top"><span>GROUP COMPANY / COMMERCE</span><span>04.1</span></div><div><div className="mi-venture-mark">m<span>.</span></div><h3>Mumchimp</h3><p>Research-backed business opportunities, built for people ready to act.</p></div><a href="https://mumchimp.com" target="_blank" rel="noopener noreferrer">Visit Mumchimp <span aria-hidden="true">↗</span></a></article>
            <article className="mi-venture mi-venture-genesis"><div className="mi-venture-top"><span>LABORATORY PRODUCT / AUTONOMY</span><span>04.2</span></div><div><div className="mi-venture-mark mi-genesis-mark">G<span>•</span></div><h3>Genesis</h3><p>The Autonomous Estate: an experimental operating system for coordinated AI agents and work.</p></div><Link href="/products">Explore the vision <span aria-hidden="true">→</span></Link></article>
            <article className="mi-venture mi-venture-chronos"><div className="mi-venture-top"><span>PRODUCT VISION / FUTURE OF WORK</span><span>04.3</span></div><div><div className="mi-venture-mark">C<span>·</span></div><h3>Chronos</h3><p>Less time chasing updates. More time for meaningful work. A product concept we&apos;re developing.</p></div><Link href="/products/chronos">Explore the concept <span aria-hidden="true">→</span></Link></article>
          </div>
        </div>
      </section>

      <section className="mi-close" aria-labelledby="mi-close-heading">
        <div className="mi-shell mi-close-inner"><span className="mi-eyebrow">NEXT / WORK WITH MERIDIAN</span><h2 id="mi-close-heading">THE NEXT<br/>MOVE IS <em>YOURS.</em></h2><div className="mi-close-bottom"><p>Have an AI problem worth solving, a platform worth building or an idea worth testing? Bring it to Meridian.</p><Link href="/contact" className="mi-button mi-button-gold">Start a conversation <span aria-hidden="true">→</span></Link></div></div>
      </section>
    </>
  );
}
