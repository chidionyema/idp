import Link from "next/link";
import type { Metadata } from "next";
import "../fieldbooks.css";

export const metadata: Metadata = {
  title: "The Delivery Gap | An Open Chapter from From Prompt to Proof",
  description: "A practical, openly readable chapter on why autonomous AI systems need durable instructions, independent proof and real operational outcomes.",
  alternates: { canonical: "/fieldbooks/from-prompt-to-proof" },
};

const failureTests = [
  { n: "01", name: "Lost-instruction test", scenario: "The original agent session disappears immediately after acknowledging an instruction.", expected: "Another authorised worker can recover the exact instruction, owner, current state and evidence from an independent durable store. The founder does not repeat themselves." },
  { n: "02", name: "Revoked-authority test", scenario: "An agent receives a permission, disconnects, and attempts a protected operation after that permission has been revoked.", expected: "The action is denied at the execution boundary. The rejection and its reason are recorded. An earlier cached approval cannot be replayed." },
  { n: "03", name: "False-green test", scenario: "A dashboard receives HTTP 200 from an API that returns cached state instead of current operational evidence.", expected: "Connectivity is reported separately from operational health; missing freshness and missing verification are visible rather than coloured green." },
  { n: "04", name: "Double-effect test", scenario: "A worker loses its acknowledgement after a successful effect and retries the instruction.", expected: "The existing effect receipt is returned by idempotency key. The protected business action does not happen twice." },
  { n: "05", name: "Release-regression test", scenario: "A normal software release builds successfully but swaps a public company's premium website for retired content.", expected: "The old design is rejected before promotion. The public alias stays pinned to the last approved release; the visitor-facing result is independently rechecked." },
];

const truth = [
  { label: "Requested", desc: "A human asked for an outcome. Nothing has run yet." },
  { label: "Acknowledged", desc: "The system durably recorded the exact instruction and assigned an owner." },
  { label: "Attempted", desc: "A worker started an action under a specific authority and revision." },
  { label: "Observed", desc: "Telemetry reports something happened. It may still be partial or misleading." },
  { label: "Verified", desc: "An independent check demonstrates the intended externally observable effect." },
];

export default function OpenChapter() {
  return <div className="mi-interior mi-knowledge mi-chapter">
    <section className="mi-chapter-hero"><div className="mi-shell">
      <Link href="/fieldbooks" className="mi-chapter-back">← FIELD BOOKS / THE COLLECTION</Link>
      <p className="mi-eyebrow">FROM PROMPT TO PROOF · OPEN CHAPTER 01</p>
      <h1>THE MODEL<br/>IS NOT <em>THE OUTCOME.</em></h1>
      <p>What breaks when we confuse fluent AI output with real engineering delivery—and the tests that expose the difference.</p>
      <div className="mi-chapter-meta"><span>PUBLIC EXCERPT</span><span>ENGINEERING + AI SYSTEMS</span><span>READ WITHOUT SIGNING UP</span></div>
    </div></section>
    <article className="mi-chapter-body mi-shell" aria-label="Open engineering chapter">
      <div className="mi-chapter-essay">
        <p className="mi-chapter-lead">Imagine a founder delegates a simple instruction: restore a customer-facing service, prove that it is receiving traffic, and make sure the old broken version cannot return.</p>
        <p>Hours later, the engineering agent presents a confident summary. A branch exists. Tests pass. A dashboard is green. But the customer website is still broken. The founder cannot see which agent owns the instruction, whether the work was deployed, or what changed for users.</p>
        <p>This is not primarily a language-model problem. It is a distributed-systems and product-design problem. A model can plan, describe, generate, debug and reason. None of those activities, by itself, constitutes the outcome the customer needed.</p>

        <h2>1. Treat an instruction as a durable object.</h2>
        <p>A chat message becomes operationally significant when it requests an effect. Record the exact original instruction with a stable identity, an accountable owner and a state that survives any single model session. A summary is useful context; it is not a replacement for the original instruction. Otherwise two agents can unknowingly execute different interpretations of the same request.</p>
        <div className="mi-chapter-pattern"><strong>MINIMUM INSTRUCTION ENVELOPE</strong><pre>{`instruction_id: stable unique ID
received_at: timestamp
origin: authenticated user and surface
original_intent: immutable source reference
scope: permitted target and effect class
owner: worker or delegated role
state: received | executing | blocked | verified | failed
evidence: append-only references to observations
verification: independently observable criterion`}</pre></div>
        <p>The most useful question a founder can ask is not “What did the agents do?” It is: <strong>“Show me every instruction that has not yet produced an independently verified result.”</strong></p>

        <h2>2. Distinguish five levels of evidence.</h2>
        <p>Progress reports tend to collapse distinct states. “The API returned 200” becomes “the service works.” “The CI build passed” becomes “the website is fixed.” “The agent committed” becomes “the instruction is complete.” These are category errors.</p>
      </div>
      <div className="mi-chapter-truth-table" aria-label="Five levels of operational truth">
        {truth.map((item, i) => <div key={item.label}><span>{String(i+1).padStart(2, "0")}</span><strong>{item.label}</strong><p>{item.desc}</p></div>)}
      </div>
      <div className="mi-chapter-essay">
        <p>Each transition needs evidence, not a confidence adjective. The strongest signal is an observable effect that another process or human can check. If the operation creates a record, read that record back from the authoritative store. If it restores a website, load the actual public hostname in a browser. If it changes permissions, attempt the forbidden action at the real boundary and observe the denial.</p>
        <h2>3. Place permission checks at the effect boundary.</h2>
        <p>An agent that had permission when work began may not still have permission when it tries to write. A long-running agent may have stale credentials or a revoked scope. Checking once, in the planning phase, is insufficient. Before a protected effect, validate current authority and an idempotency key at the system that performs the write.</p>
        <p>Test the uncomfortable case: issue authority, disconnect, revoke, reconnect and attempt the effect. A prototype that refuses the action in isolation is valuable evidence, but does not establish that every production action door is protected. The real executor must be part of the test.</p>
        <h2>4. Design for interruptions, not perfect sessions.</h2>
        <p>Stateless workers are a feature when the work state is durable. Each worker should be able to reconstruct the instruction, the last verified state, outstanding dependencies and the evidence required to finish. Durable task identity and idempotent effects protect against duplicate execution; bounded recovery handles temporary failures without inventing success.</p>
        <p>The founder should not be the state store. Repeating instructions to twenty different sessions is a system-design defect, not a productive operating model.</p>
        <h2>5. Prove the actual customer journey.</h2>
        <p>Source-level tests protect important rules; browser-level checks catch what customers actually see. A site can compile and still ship an obsolete visual identity, unreadable text or an enquiry form with no real delivery destination. Combine negative fixtures (forbidden old versions), responsive browser tests and independent public readback.</p>
        <h2>A five-test acceptance suite</h2>
        <p>Before claiming an autonomous engineering system is operational, run these five tests against the relevant real boundaries. They are deliberately adversarial and each has a clear pass/fail result.</p>
      </div>
      <div className="mi-chapter-tests">
        {failureTests.map(t => <section className="mi-chapter-test" key={t.n}><span>{t.n} / EXPERIMENT</span><h3>{t.name}</h3><p><strong>Scenario:</strong> {t.scenario}</p><p><strong>Pass:</strong> {t.expected}</p></section>)}
      </div>
      <div className="mi-chapter-essay">
        <h2>What the operating model should report</h2>
        <p>At the founder layer, show the instruction&apos;s identity, owner, last independently verified step, age, unresolved blocker and available next action. Summarise the exception before exposing raw traces. A connected event stream is not a success metric. A missing measurement must remain unknown, with a way to inspect and recover it.</p>
        <p><strong>Working principle:</strong> engineering activity is an input; externally verified yield is the product. Build the system so that two different agents can independently distinguish those states.</p>
      </div>
      <aside className="mi-chapter-end"><span className="mi-eyebrow">NEXT / THE COMPLETE FIELD GUIDE</span><h2>THE EXCERPT IS<br/>JUST THE START.</h2><p>The full fieldbook expands these ideas into implementation patterns, exercises, threat scenarios, scorecards and a structured rollout plan. The merchant link will appear once the publisher account is verified.</p><Link href="/fieldbooks" className="mi-button mi-button-gold">Explore the complete fieldbook <span aria-hidden="true">↗</span></Link></aside>
    </article>
  </div>;
}
