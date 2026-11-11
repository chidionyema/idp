import Link from "next/link";
import type { Metadata } from "next";
import { verifiedGumroadProductUrl } from "@/lib/commercialStorefront";
import "./fieldbooks.css";

export const metadata: Metadata = {
  title: "Fieldbooks | Practical AI Systems Engineering",
  description: "Original fieldbooks and applied training from Merdian Intelligence. From prompt to proof: engineering autonomous systems, trustworthy operations and real outcomes.",
  alternates: { canonical: "/fieldbooks" },
  openGraph: { title: "From Prompt to Proof | Merdian Fieldbooks", description: "Technical knowledge for people who need AI systems to deliver, not merely demonstrate." },
};

const chapters = [
  { n: "01", title: "The delivery gap", desc: "Why fluent models, healthy-looking dashboards and completed tickets do not establish that the requested outcome happened." },
  { n: "02", title: "Instructions as durable objects", desc: "Identity, provenance, ownership and continuations across disconnected agents and sessions." },
  { n: "03", title: "Trust at execution boundaries", desc: "Permission expiry, revocation, idempotency and failure at the moment an effect is attempted." },
  { n: "04", title: "Proof before production claims", desc: "Observations, independent checks, release regression tests and customer-visible readbacks." },
  { n: "05", title: "Operational intelligence", desc: "Meaningful metrics, truthful uncertainty and recovering without a human babysitting a laptop." },
  { n: "06", title: "The 14-day implementation plan", desc: "An incremental, testable path from brittle agent demos to measurable operational outcomes." },
];

const formats = [
  { n: "01 / READ", name: "Fieldbooks", status: "First title prepared", text: "Concise technical books, decision frameworks, tested checklists and practical exercises. Built for engineering teams rather than passive reading." },
  { n: "02 / PRACTISE", name: "Masterclasses", status: "Curriculum in development", text: "Instructor-led deep dives using realistic failure scenarios, acceptance criteria and hands-on exercises. Not a pre-recorded lecture carousel." },
  { n: "03 / APPLY", name: "Engineering partnerships", status: "Consultancy", text: "Turn the ideas into an architecture review, assurance exercise or implementation plan for your own systems." },
];

export default function FieldbooksPage() {
  // Only the seller can connect the merchant account. Never invent a live checkout.
  const checkoutUrl = verifiedGumroadProductUrl(process.env.MERDIAN_GUMROAD_FIELD_GUIDE_URL);
  return <div className="mi-interior mi-knowledge">
    <section className="mi-knowledge-hero" aria-labelledby="knowledge-heading">
      <div className="mi-shell">
        <div className="mi-knowledge-top"><span>MERDIAN / ORIGINAL INTELLIGENCE</span><span>THE FIELDBOOK SERIES · VOL. 01</span></div>
        <div className="mi-knowledge-hero-grid">
          <div>
            <p className="mi-eyebrow">ENGINEERING KNOWLEDGE / NO EMPTY PROMISES</p>
            <h1 id="knowledge-heading">HARD-WON.<br/><em>HARD TO FAKE.</em></h1>
            <p className="mi-knowledge-lede">Most AI content teaches you to make a model respond. We teach the harder discipline: turning intelligence into work that survives interruption, resists unsafe actions and can be independently verified.</p>
            <div className="mi-knowledge-actions">
              <Link className="mi-button mi-button-gold" href="/fieldbooks/from-prompt-to-proof">Read the open chapter <span aria-hidden="true">↗</span></Link>
              <a className="mi-knowledge-text-link" href="#first-title">Explore the first fieldbook <span aria-hidden="true">↓</span></a>
            </div>
          </div>
          <div className="mi-knowledge-cover-wrap" aria-label="Conceptual preview of the From Prompt to Proof fieldbook">
            <div className="mi-knowledge-book">
              <span className="mi-knowledge-book-kicker">MERDIAN INTELLIGENCE / FIELDBOOK 001</span>
              <div className="mi-knowledge-book-line" aria-hidden="true"/>
              <strong>FROM<br/>PROMPT<br/>TO <em>PROOF.</em></strong>
              <p>Engineering autonomous AI that delivers accountable results.</p>
              <span className="mi-knowledge-book-footer">SYSTEMS · EVIDENCE · EXECUTION</span>
            </div>
          </div>
        </div>
        <div className="mi-knowledge-hero-bottom">A NEW KIND OF TECHNICAL PUBLISHING <span>OPEN METHODS. PROTECTED COMPANY INTELLIGENCE.</span></div>
      </div>
    </section>

    <section className="mi-knowledge-principle mi-section">
      <div className="mi-shell mi-knowledge-principle-grid">
        <p className="mi-eyebrow">THE DIFFERENCE</p>
        <h2>THE MODEL IS NOT<br/><em>THE OUTCOME.</em></h2>
        <div>
          <p>Impressive demos are abundant. Reliable systems are not. Real engineering begins where model benchmarks end: state continuity, execution authority, failed dependencies, observable consequences and recovery.</p>
          <p>Our public work shares the transferable principles. Our private implementations, sensitive incidents, commercial data and proprietary research remain protected.</p>
        </div>
      </div>
    </section>

    <section id="first-title" className="mi-knowledge-product mi-section" aria-labelledby="first-title-heading">
      <div className="mi-shell">
        <div className="mi-section-intro"><span className="mi-eyebrow">FIELDBOOK / 001</span><p>ENGINEERING / AI / AUTONOMY</p></div>
        <div className="mi-knowledge-product-grid">
          <div>
            <h2 id="first-title-heading">FROM PROMPT<br/>TO <em>PROOF.</em></h2>
            <p className="mi-knowledge-product-intro">An applied manual for technical founders, engineering leaders and teams building with autonomous agents. It focuses on failure modes, decisions, measurable acceptance and practical implementation.</p>
            <div className="mi-knowledge-tags"><span>ENGINEERING FIELD GUIDE</span><span>CHECKLISTS + TEST SCENARIOS</span><span>IMPLEMENTATION PLAYBOOK</span></div>
            <div className="mi-knowledge-purchase">
              {checkoutUrl ? <a href={checkoutUrl} target="_blank" rel="noopener noreferrer" className="mi-button mi-button-gold">Buy securely on Gumroad <span aria-hidden="true">↗</span></a>
                : <div className="mi-knowledge-checkout-pending" role="status"><span>MERCHANT CONNECTION PENDING</span><p>Purchasing is not enabled yet. No payment or order can be taken on this page.</p></div>}
              <Link href="/fieldbooks/from-prompt-to-proof" className="mi-knowledge-text-link">Explore the free chapter <span aria-hidden="true">↗</span></Link>
            </div>
          </div>
          <div className="mi-knowledge-chapter-list" aria-label="Contents of the first fieldbook">
            {chapters.map(c => <div className="mi-knowledge-chapter" key={c.n}><span>{c.n}</span><div><h3>{c.title}</h3><p>{c.desc}</p></div></div>)}
          </div>
        </div>
      </div>
    </section>

    <section className="mi-knowledge-ladder mi-section" aria-labelledby="formats-heading">
      <div className="mi-shell">
        <div className="mi-section-intro"><span className="mi-eyebrow">KNOWLEDGE TO APPLICATION</span><p>THREE LEVELS. ONE STANDARD.</p></div>
        <h2 id="formats-heading">STUDY IT.<br/><em>PRACTISE IT.</em><br/>DEPLOY IT.</h2>
        <div className="mi-knowledge-format-grid">
          {formats.map(f => <article key={f.n} className="mi-knowledge-format"><span className="mi-knowledge-format-code">{f.n}</span><h3>{f.name}</h3><span className="mi-knowledge-format-status">{f.status}</span><p>{f.text}</p>{f.n.startsWith("03") && <Link href="/consulting">Our engineering work <span aria-hidden="true">↗</span></Link>}</article>)}
        </div>
      </div>
    </section>
    <section className="mi-knowledge-close">
      <div className="mi-shell"><p className="mi-eyebrow">THE FREE READING ROOM</p><h2>JUDGE THE THINKING<br/>BEFORE YOU BUY.</h2><p>No mystery claims. Read a substantive open chapter and inspect the quality for yourself.</p><Link href="/fieldbooks/from-prompt-to-proof" className="mi-button mi-button-gold">Read the chapter <span aria-hidden="true">↗</span></Link></div>
    </section>
  </div>;
}
