import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Our vision — Research, experimentation and the future of work",
  description: "Meridian researches what is possible, tests ideas carefully and turns promising discoveries into useful products and businesses. Explore our vision and request a private investor briefing.",
};

const principles = [
  { n: "01", title: "Research", text: "Ask bigger questions about how technology can help people and organisations do better work." },
  { n: "02", title: "Experiment", text: "Put ideas to the test, learn from what succeeds and be open about what still needs work." },
  { n: "03", title: "Commercialise", text: "Turn the most promising findings into useful products, real services and businesses that can grow." },
] as const;

export default function InvestorsPage() {
  return <div className="mi-interior mi-investor-page">
    <section className="mi-page-hero mi-investor-hero" aria-labelledby="investor-heading"><div className="mi-shell">
      <span className="mi-eyebrow">MERIDIAN / A CONVERSATION ABOUT WHAT COMES NEXT</span>
      <h1 id="investor-heading">THE WORKPLACE<br/>OF THE FUTURE<br/><em>IS HUMAN.</em></h1>
      <div className="mi-page-hero-bottom"><p>We&apos;re a research-led company exploring a better way to work: less time chasing updates, more time thinking, creating and leading.</p>
        <Link href="/contact?topic=investor" className="mi-button mi-button-gold">Request an investor conversation <span aria-hidden="true">→</span></Link>
      </div>
    </div></section>
    <section className="mi-section mi-investor-opening" aria-labelledby="investor-why"><div className="mi-shell mi-investor-opening-grid">
      <span className="mi-eyebrow">01 / OUR PURPOSE</span>
      <div><h2 id="investor-why">Great people deserve<br/><em>a better working day.</em></h2>
        <p>Talented people spend too much time searching for answers, chasing deadlines and coordinating the work around the work. We believe technology can help make the working day simpler, clearer and more human.</p>
        <p>This is one direction within Meridian&apos;s broader mission: research new possibilities, test them through real experiments and bring the most useful discoveries to market.</p>
      </div>
    </div></section>
    <section className="mi-section mi-investor-principles" aria-labelledby="investor-method"><div className="mi-shell">
      <div className="mi-section-intro"><span className="mi-eyebrow">02 / HOW WE BUILD</span><p>RESEARCH / EXPERIMENTATION / COMMERCIALISATION</p></div>
      <h2 id="investor-method">Curious enough to explore.<br/>Disciplined enough to build.</h2>
      <div className="mi-investor-ideas">{principles.map(x=><article key={x.n}><span>{x.n}</span><h3>{x.title}</h3><p>{x.text}</p></article>)}</div>
    </div></section>
    <section className="mi-section mi-investor-products" aria-labelledby="investor-products"><div className="mi-shell">
      <div className="mi-section-intro"><span className="mi-eyebrow">03 / THE OPPORTUNITY</span><p>OUR IDEAS, SEEN THROUGH PEOPLE&apos;S LIVES</p></div>
      <h2 id="investor-products">What could a better workplace look like?</h2>
      <div className="mi-investor-product-grid">
        <article className="mi-investor-product-primary"><span>CHRONOS / IN DEVELOPMENT</span><h3>Less time chasing.<br/>More time creating.</h3><p>Imagine a working week with clear priorities, thoughtful handovers, timely decisions and fewer interruptions. Chronos is our developing vision for making that possible.</p><Link href="/products/chronos">Explore Chronos <span aria-hidden="true">→</span></Link><small>Concept walkthrough — not a launched product</small></article>
        <article><span>GENESIS / RESEARCH EXPERIENCE</span><h3>How intelligent work could come together.</h3><p>Genesis is where we explore the systems behind coordinated work, research their strengths and limitations, and test outcomes before making claims.</p><Link href="/investors/room">View by invitation <span aria-hidden="true">→</span></Link><small>Private read-only access requires an approved, unexpired invitation</small></article>
        <article><span>OTTO / RESEARCH EXPERIENCE</span><h3>A clearer way to stay in the loop.</h3><p>OTTO explores how leaders can stay informed, make important decisions and interact with complex work in a more natural way.</p><Link href="/investors/room">View by invitation <span aria-hidden="true">→</span></Link><small>Private read-only access; no access to operational controls</small></article>
      </div>
    </div></section>
    <section className="mi-section mi-investor-proof" aria-labelledby="investor-proof"><div className="mi-shell mi-investor-opening-grid">
      <span className="mi-eyebrow">04 / A RELATIONSHIP BUILT ON TRUST</span>
      <div><h2 id="investor-proof">Ambition matters.<br/><em>So does honesty.</em></h2>
        <p>We&apos;re building for the long term. During a private briefing we distinguish clearly between concepts, working experiments and demonstrated results. We won&apos;t present research as a finished customer product.</p>
        <p>Approved guests can explore selected, current, read-only Genesis and OTTO views for a limited time. Identity checks, permission boundaries and automatic expiry protect the private operational estate.</p>
        <div className="mi-investor-journey">
          <div><span>01</span><strong>Discover Meridian</strong><small>Start here, openly</small></div>
          <div><span>02</span><strong>Talk to us</strong><small>See if there&apos;s a fit</small></div>
          <div><span>03</span><strong>Receive an invitation</strong><small>Named guest, limited time</small></div>
          <div><span>04</span><strong>Explore privately</strong><small>Genesis and OTTO, view only</small></div>
        </div>
        <div className="mi-investor-actions">
          <Link href="/contact?topic=investor" className="mi-button mi-button-gold">Request a private briefing <span aria-hidden="true">→</span></Link>
          <Link href="/investors/room" className="mi-button mi-button-dark">Already invited? Enter the room <span aria-hidden="true">→</span></Link>
        </div>
      </div>
    </div></section>
    <section className="mi-close mi-investor-close" aria-labelledby="investor-close"><div className="mi-shell mi-close-inner">
      <span className="mi-eyebrow">05 / LET&apos;S MEET</span>
      <h2 id="investor-close">THE FUTURE OF WORK<br/><em>STARTS WITH PEOPLE.</em></h2>
      <div className="mi-close-bottom"><p>We&apos;d welcome a thoughtful conversation about the research, products and businesses we&apos;re building—and what the next chapter could become.</p>
        <Link href="/contact?topic=investor" className="mi-button mi-button-gold">Start the conversation <span aria-hidden="true">→</span></Link>
      </div>
      <p className="mi-investor-disclosure">This page introduces our business and research. It is not an offer to invest or a solicitation to purchase securities. Confidential materials are available only through separately approved, time-limited access.</p>
    </div></section>
  </div>;
}
