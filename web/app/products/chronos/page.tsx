import Link from "next/link";
import type { Metadata } from "next";
import { ChronosWalkthrough } from "@/components/ChronosWalkthrough";

export const metadata: Metadata = {
  title: "Chronos — A better rhythm for work",
  description: "Meet Chronos, Meridian's developing vision for a workplace where priorities are clear, work keeps moving and people stay in control.",
};

const outcomes = [
  { number: "01", title: "Know what matters", text: "Everyone should understand the priorities, who owns them and what a good outcome looks like." },
  { number: "02", title: "Keep work moving", text: "Handovers, deadlines and unanswered decisions should be easier to see before they slow a team down." },
  { number: "03", title: "Give time back", text: "Spend less of the day asking for updates and more of it doing the work that calls for human judgement." },
] as const;

export default function ChronosPage() {
  return <div className="mi-interior mi-chronos-page">
    <section className="mi-page-hero mi-chronos-hero" aria-labelledby="chronos-hero-title">
      <div className="mi-shell">
        <span className="mi-eyebrow">MERIDIAN / CHRONOS · IN DEVELOPMENT</span>
        <h1 id="chronos-hero-title">WORK HAS A RHYTHM.<br/><em>LET&apos;S MAKE IT BETTER.</em></h1>
        <div className="mi-page-hero-bottom">
          <p>Chronos is our vision for a working day with less chasing, fewer forgotten handovers and more time for the things people do best.</p>
          <Link href="/contact?topic=chronos" className="mi-button mi-button-gold">Discuss Chronos <span aria-hidden="true">→</span></Link>
        </div>
      </div>
    </section>
    <section className="mi-section mi-chronos-opening" aria-labelledby="chronos-problem-title">
      <div className="mi-shell mi-chronos-statement">
        <span className="mi-eyebrow">THE PROBLEM WE WANT TO SOLVE</span>
        <h2 id="chronos-problem-title">Too much work is spent <em>organising the work.</em></h2>
        <p>People are capable of remarkable things. But too often their days are filled with status meetings, scattered messages, missed handovers and the question: “What&apos;s happening with this?” We believe there&apos;s a better way.</p>
      </div>
    </section>
    <section className="mi-section mi-chronos-benefits" aria-labelledby="chronos-benefits-title">
      <div className="mi-shell">
        <div className="mi-section-intro"><span className="mi-eyebrow">WHAT WE ARE BUILDING TOWARDS</span><p>BETTER WORK, BUILT AROUND PEOPLE</p></div>
        <h2 id="chronos-benefits-title">Clarity, without the constant noise.</h2>
        <div className="mi-chronos-benefits-grid">
          {outcomes.map(item => <article className="mi-chronos-benefit" key={item.number}>
            <span>{item.number}</span><h3>{item.title}</h3><p>{item.text}</p>
          </article>)}
        </div>
      </div>
    </section>
    <div className="mi-shell"><ChronosWalkthrough /></div>
    <section className="mi-section mi-chronos-human" aria-labelledby="chronos-human-title">
      <div className="mi-shell mi-chronos-human-grid">
        <span className="mi-eyebrow">THE PRINCIPLE</span>
        <div><h2 id="chronos-human-title">People lead.<br/><em>Technology helps.</em></h2>
          <p>Chronos is not about taking people out of their work. It is about helping teams keep their promises, giving leaders the right information at the right time and making room for better decisions.</p>
          <p className="mi-chronos-disclosure">Chronos is a product direction under development. The walkthrough above illustrates our intended experience; it does not represent a shipped product, customer adoption or measured performance.</p>
          <div className="mi-hero-actions"><Link href="/contact?topic=chronos" className="mi-button mi-button-gold">Start a conversation <span aria-hidden="true">→</span></Link><Link href="/investors" className="mi-button mi-button-outline">Our bigger vision <span aria-hidden="true">→</span></Link></div>
        </div>
      </div>
    </section>
  </div>;
}
