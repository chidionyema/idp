import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI systems engineering",
  description: "Meridian Intelligence engineers accountable AI systems for real operating environments.",
};

const disciplines = [
  { id: "01", title: "Infrastructure", text: "Model routing, retrieval and orchestration engineered around the workload, its cost and its failure modes.", focus: "ROUTING / RETRIEVAL / IDENTITY" },
  { id: "02", title: "Autonomous operations", text: "Durable workflows with owned state, bounded recovery and explicit authority for consequential decisions.", focus: "EXECUTION / RECOVERY / OVERSIGHT" },
  { id: "03", title: "Assurance", text: "Instrument the decision path, test failure conditions and independently verify the result against the original objective.", focus: "EVALUATION / TRACING / EVIDENCE" },
];

const method = [
  { n: "01", title: "Define the outcome", desc: "Understand the operating problem and the constraints. Decide what success must prove." },
  { n: "02", title: "Engineer the system", desc: "Integrate with the environment you already own. Design for actual workload and risk." },
  { n: "03", title: "Exercise failure", desc: "Test timeouts, dependency loss, manual intervention and recovery before release." },
  { n: "04", title: "Verify and hand over", desc: "Deliver working interfaces, operational evidence and a maintainable system." },
];

export default function HomePage() {
  return (
    <div className="mi-home">
      <section className="mi-hero" aria-labelledby="mi-hero-title">
        <div className="container mi-hero-grid">
          <div className="mi-hero-copy">
            <p className="mi-eyebrow"><span aria-hidden="true" /> MERIDIAN INTELLIGENCE <small>/ ENGINEERING PRACTICE</small></p>
            <h1 id="mi-hero-title">Intelligence is only useful <em>when it runs.</em></h1>
            <p className="mi-hero-lead">We engineer AI systems for real operating environments. From architecture to autonomous execution, important outcomes need a way to be observed, challenged and recovered.</p>
            <div className="mi-actions"><Link className="mi-primary" href="/contact">Discuss your project <span aria-hidden="true">↗</span></Link><Link className="mi-secondary" href="#approach">How we work <span aria-hidden="true">↓</span></Link></div>
            <p className="mi-hero-note">◇ &nbsp; Designed for ownership, not dependency.</p>
          </div>
          <div className="mi-workflow" aria-label="Illustrative execution architecture; not live telemetry">
            <div className="mi-workflow-top"><span>REFERENCE ARCHITECTURE / 001</span><span className="mi-workflow-status">ILLUSTRATIVE</span></div>
            <div className="mi-workflow-body">
              <div className="mi-workflow-heading"><span>From instruction</span><span aria-hidden="true">→</span><span>to evidence</span></div>
              {[
                ["01", "Intent", "Outcome and operating constraints", "◎"],
                ["02", "Decision", "Capability, policy and authority", "◇"],
                ["03", "Execution", "State, observation and recovery", "↗"],
                ["04", "Verification", "Evidence against the original goal", "✓"],
              ].map(([n, name, description, glyph], index) => (
                <div key={n}>{index > 0 && <div className="mi-connector" aria-hidden="true" />}<div className={"mi-workflow-step" + (index === 3 ? " mi-workflow-final" : "")}><span className="mi-step-number">{n}</span><div><strong>{name}</strong><small>{description}</small></div><span className="mi-step-glyph" aria-hidden="true">{glyph}</span></div></div>
              ))}
            </div>
            <div className="mi-workflow-bottom"><small>THE PRINCIPLE</small><strong>A system is accountable when its results can be verified.</strong></div>
          </div>
        </div>
      </section>
      <div className="mi-strip"><div className="container"><span><b>01</b> Defined constraints</span><span><b>02</b> Human authority</span><span><b>03</b> Inspectable results</span></div></div>
      <section className="mi-section" id="capabilities" aria-labelledby="mi-capabilities-title">
        <div className="container">
          <div className="mi-heading"><div><p className="mi-kicker">01 / CAPABILITIES</p><h2 id="mi-capabilities-title">Engineering beyond <em>the demonstration.</em></h2></div><p>We work on the systems behind AI features: how they operate, what happens when something breaks and what the business can prove afterwards.</p></div>
          <div className="mi-disciplines">{disciplines.map((d) => <article key={d.id} className="mi-discipline"><span className="mi-kicker">{d.id}</span><h3>{d.title}</h3><p>{d.text}</p><div className="mi-discipline-foot"><span>{d.focus}</span><span aria-hidden="true">↗</span></div></article>)}</div>
          <div className="mi-more"><Link href="/consulting">Explore our services <span aria-hidden="true">↗</span></Link></div>
        </div>
      </section>
      <section className="mi-section mi-method" id="approach" aria-labelledby="mi-method-title">
        <div className="container">
          <div className="mi-heading"><div><p className="mi-kicker">02 / METHOD</p><h2 id="mi-method-title">Built to work. <em>Built to be understood.</em></h2></div><p>Architecture is a means, not the result. Our work begins with what the operation needs and finishes with a result the team can inspect.</p></div>
          <div className="mi-method-grid">{method.map((m) => <article key={m.n}><span className="mi-kicker">{m.n} / 04</span><h3>{m.title}</h3><p>{m.desc}</p></article>)}</div>
        </div>
      </section>
      <section className="mi-section" aria-labelledby="mi-evidence-title">
        <div className="container mi-evidence-grid">
          <div><p className="mi-kicker">03 / ASSURANCE</p><h2 id="mi-evidence-title">A claim is a starting point. <em>Evidence is the standard.</em></h2><p>Architecture diagrams are useful. A working endpoint is better. The operating result, constraints and failure record should be available for inspection.</p><Link className="mi-secondary" href="/case-studies">Explore engineering work <span aria-hidden="true">↗</span></Link></div>
          <div className="mi-evidence"><div className="mi-evidence-title"><span>DELIVERY RECORD</span><span>ILLUSTRATIVE FORMAT</span></div>{[["Expected result","Defined before execution"],["System boundary","Owned and documented"],["Recovery","Exercised in failure tests"],["Verification","Independent of the claim"]].map(([label,value]) => <div className="mi-evidence-row" key={label}><span>{label}</span><strong>{value}</strong></div>)}<p>Example evidence structure, not a live customer report.</p></div>
        </div>
      </section>
      <section className="mi-close" aria-labelledby="mi-close-title"><div className="container mi-close-inner"><div><p className="mi-kicker">04 / START A CONVERSATION</p><h2 id="mi-close-title">Bring us the hard problem.</h2><p>Tell us what needs to run, where it breaks today and what a successful result must prove.</p></div><Link href="/contact" className="mi-primary">Start a technical conversation <span aria-hidden="true">↗</span></Link></div></section>
    </div>
  );
}
