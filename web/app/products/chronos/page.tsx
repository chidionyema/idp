import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Chronos | Time-aware autonomous operations",
  description: "Chronos is Meridian Intelligence's research-stage concept for time-aware autonomous operations: durable obligations, evidence of completion and recovery when work is missed.",
};

const rhythms = [
  { time: "SECONDS", purpose: "Observe", detail: "Notice a stalled handoff before silence becomes normal." },
  { time: "MINUTES", purpose: "Recover", detail: "Escalate missed actions and bounded recovery attempts." },
  { time: "HOURS", purpose: "Reconcile", detail: "Check operational commitments against actual receipts." },
  { time: "DAYS", purpose: "Deliver", detail: "Coordinate reviews, reporting and scheduled execution." },
  { time: "WEEKS", purpose: "Adapt", detail: "Carry unfinished work into the next operating rhythm." },
  { time: "QUARTERS", purpose: "Govern", detail: "Connect immediate action to long-range priorities." },
] as const;

const commitments = [
  { n: "01", title: "Obligations, not alarms", text: "A schedule records when work is due. Chronos is designed to record the obligation, its owner and the evidence required to declare it complete." },
  { n: "02", title: "Time that survives interruption", text: "A missed window should not disappear when an agent, workflow or host restarts. Recovery begins with a durable record of what was due." },
  { n: "03", title: "Proof before progress", text: "A task that ran is different from a task that succeeded. The design separates execution records from independently verifiable outcomes." },
  { n: "04", title: "Autonomy with a boundary", text: "Routine obligations can be recovered automatically where authority permits. High-impact decisions remain visible for human judgement." },
] as const;

export default function ChronosPage() {
  return <div className="mi-interior mi-chronos">
    <section className="mi-chronos-hero" aria-labelledby="chronos-heading">
      <div className="mi-shell mi-chronos-hero-grid">
        <div className="mi-chronos-hero-copy">
          <span className="mi-eyebrow">MERIDIAN / AUTONOMOUS SYSTEMS RESEARCH</span>
          <div className="mi-chronos-identity"><span aria-hidden="true" className="mi-chronos-emblem">C<span>·</span></span><span>CHRONOS</span></div>
          <h1 id="chronos-heading">TIME DOESN&apos;T<br/>WAIT FOR <em>AGENTS.</em></h1>
          <p className="mi-chronos-intro">Autonomous work needs more than instructions. It needs a memory of what must happen, when it was due, and whether the result is real.</p>
          <p className="mi-chronos-maturity"><span aria-hidden="true" /> RESEARCH CONCEPT / NOT GENERALLY AVAILABLE</p>
          <div className="mi-chronos-hero-actions">
            <Link href="/contact" className="mi-button mi-button-gold">Discuss the research <span aria-hidden="true">→</span></Link>
            <a href="#chronos-principles" className="mi-button mi-button-outline">Explore the design <span aria-hidden="true">↓</span></a>
          </div>
        </div>
        <div className="mi-chronos-clock" aria-hidden="true">
          <div className="mi-chronos-ring mi-chronos-ring-one" />
          <div className="mi-chronos-ring mi-chronos-ring-two" />
          <div className="mi-chronos-ring mi-chronos-ring-three" />
          <div className="mi-chronos-axis mi-chronos-axis-h" />
          <div className="mi-chronos-axis mi-chronos-axis-v" />
          <div className="mi-chronos-clock-center"><span>C</span><small>TIME / TRUTH</small></div>
          <span className="mi-chronos-clock-index mi-chronos-clock-index-a">NOW / 00</span>
          <span className="mi-chronos-clock-index mi-chronos-clock-index-b">NEXT / ∞</span>
        </div>
      </div>
    </section>

    <section className="mi-chronos-thesis" aria-labelledby="chronos-thesis">
      <div className="mi-shell mi-chronos-thesis-grid">
        <span className="mi-eyebrow">01 / THE PROBLEM</span>
        <div>
          <h2 id="chronos-thesis">A scheduled task is a promise.<br/><em>Where is the proof?</em></h2>
          <p>Most automation can tell you when something was scheduled. Few systems give the whole story after an outage, a missed deadline or a chain of agents handing work to one another. Chronos explores the missing operational layer: obligations with time semantics, accountable ownership and evidence-backed recovery.</p>
        </div>
      </div>
    </section>

    <section className="mi-chronos-rhythm" aria-labelledby="chronos-rhythm-heading">
      <div className="mi-shell">
        <div className="mi-chronos-section-intro"><span className="mi-eyebrow">02 / THE OPERATING RHYTHM</span><h2 id="chronos-rhythm-heading">One company.<br/><em>Many clocks.</em></h2><p>From immediate recovery to strategic cadence, the same principles should apply. The horizon changes. The obligation remains accountable.</p></div>
        <div className="mi-chronos-rhythm-grid">
          {rhythms.map((entry, i) => <article className="mi-chronos-rhythm-cell" key={entry.time}>
            <span className="mi-chronos-rhythm-index">{String(i + 1).padStart(2, "0")} / {entry.time}</span>
            <h3>{entry.purpose}</h3>
            <p>{entry.detail}</p>
          </article>)}
        </div>
        <p className="mi-chronos-rhythm-note">Design scope includes time zones, daylight-saving changes, missed-run reconciliation and explicit UTC timestamps. These are research requirements, not a claim of a deployed commercial service.</p>
      </div>
    </section>

    <section className="mi-chronos-principles" id="chronos-principles" aria-labelledby="chronos-principles-heading">
      <div className="mi-shell">
        <div className="mi-chronos-section-intro"><span className="mi-eyebrow">03 / ENGINEERING INTENT</span><h2 id="chronos-principles-heading">Built around<br/><em>the missed moment.</em></h2></div>
        <div className="mi-chronos-principle-list">
          {commitments.map(item => <article key={item.n} className="mi-chronos-principle">
            <span>{item.n}</span><h3>{item.title}</h3><p>{item.text}</p>
          </article>)}
        </div>
      </div>
    </section>

    <section className="mi-chronos-outro" aria-labelledby="chronos-outro-heading">
      <div className="mi-shell mi-chronos-outro-grid">
        <div><span className="mi-eyebrow">04 / RESEARCH COLLABORATIONS</span><h2 id="chronos-outro-heading">WHAT HAPPENS<br/><em>WHEN NOBODY'S WATCHING?</em></h2></div>
        <div><p>Chronos is being explored as part of Meridian's autonomous-systems research. We are interested in serious conversations with teams facing persistent scheduling, recovery or agent-operations problems.</p>
          <p className="mi-chronos-disclosure">Current status: research and concept validation. No commercial availability, contracted service guarantee or verified customer integration is implied.</p>
          <Link className="mi-button mi-button-gold" href="/contact">Talk to Meridian <span aria-hidden="true">→</span></Link>
        </div>
      </div>
    </section>
  </div>;
}
