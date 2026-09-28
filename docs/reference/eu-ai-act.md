# EU AI Act: scope, classification, and what we actually owe

Status: draft for legal review. Written 2026-08-25 against the consolidated AI Act
as amended by the Digital Omnibus on AI, Regulation (EU) 2026/1744.

This is a preparation document. It is written so that a qualified lawyer can check
it in an hour rather than start from nothing. It is not legal advice and nothing in
it should be relied on as a legal conclusion until that review has happened.

---

## The verdict

We are in scope, we are close to compliant, and the work is days rather than
quarters. That is the opposite of the assessment circulated on 2026-08-24, which
listed twelve requirements, marked nine of them red, and concluded "you cannot pass
the EU AI Act as of today".

Two corrections carry the whole difference.

**The obligations that report called critical do not apply to us and are not in
force.** Articles 9 to 15, 17, 43, 49 and 71 — risk management, data governance,
technical documentation, conformity assessment, CE marking, EU database
registration — are obligations on the **provider of a high-risk AI system**. They
bind nobody else. Nothing we run is high-risk, for reasons set out below. And even
for the systems they do bind, the Digital Omnibus deferred them: Annex III
standalone systems now apply from **2 December 2027**, Annex I embedded systems
from **2 August 2028**. The 2 August 2026 date the report was working to is gone.

**The two obligations that do bind us today were both missing from that report.**
Article 4 (AI literacy) has bound us since 2 February 2025 — eighteen months. It
applies at every risk level, to organisations of every size, and we have done
nothing about it. Article 50 (transparency) became enforceable on 2 August 2026,
three weeks ago. A report that marks CE marking critical and omits the two live
duties is not conservative, it is miscalibrated in both directions at once.

The correct answer to a buyer's lawyer is not "we have no conformity assessment".
It is a dated classification memo, a register, and a gate. Those are what this
document and the work it specifies produce.

---

## 1. Are we in scope

Yes, on two independent grounds. Neither depends on having an EU entity.

**Article 2(1)(c) — extraterritorial reach.** The Act catches providers and
deployers established in a third country where the *output* of the system is used
in the Union. The UK is a third country post-Brexit. The trigger is use, not
location. If prospector's output reaches a user in Ireland or Germany, we are in
scope for that system regardless of where we sit.

**Article 3(11) — putting into service includes own use.** "Putting into service"
means supplying for first use directly to the deployer *or for the provider's own
use*. Building an agent and running it ourselves makes us both its provider and its
deployer. Internal-only is not out of scope; it is in scope at a low risk tier.

So the question was never whether the Act reaches us. It is which tier we land in,
and that is Article 6.

## 2. What is in force today, 2026-08-25

| Obligation | Applies to us | In force since | Our state |
|---|---|---|---|
| Art. 5 — prohibited practices | Yes, all operators | 2 Feb 2025 | Nothing we run is on the list. Assert and evidence. |
| Art. 4 — AI literacy | Yes, all operators, all tiers | 2 Feb 2025 | **Nothing done. 18 months overdue.** |
| Art. 50 — transparency | Yes, if we ship a user-facing AI surface | 2 Aug 2026 | Depends on prospector's surface. See §4. |
| Ch. V — GPAI model obligations | **No** — see §5 | 2 Aug 2025 | Not applicable. |
| Arts. 9–15, 17, 43, 49, 71 — high-risk | **No** — see §3 | 2 Dec 2027 (Annex III) | Not applicable. |

Two dates to diary. The Omnibus added two prohibited categories to Article 5 —
non-consensual intimate imagery and CSAM generation — with the technical-safeguard
grace period running to **2 December 2026**. And Article 50(2)'s machine-readable
marking duty reaches systems placed on the market before 2 August 2026 only from
**2 December 2026**.

Penalties are live. Article 99 sets three tiers: €35M or 7% of worldwide turnover
for Article 5 breaches, €15M or 3% for most other operator obligations, €7.5M or 1%
for supplying incorrect or misleading information to an authority. Article 4 carries
no fine of its own. It is not therefore free: a market surveillance authority
investigating anything else may treat an absence of AI literacy as an aggravating
factor when it sets a penalty inside the 3% tier.

## 3. Classification under Article 6

Annex III has exactly eight areas: biometrics; safety components of critical
infrastructure; education and vocational training; employment and worker
management; access to essential private and public services; law enforcement;
migration, asylum and border control; administration of justice and democratic
processes.

An agent that writes code, opens pull requests and reconciles infrastructure is in
none of them. "Critical infrastructure" in Annex III(2) means safety components in
the management of digital infrastructure, road traffic, and the supply of water,
gas, heating and electricity. It does not mean "infrastructure that is critical to
us". A laptop-hosted internal developer platform is not within it, and the claim
that autonomous agents making commits push us toward high-risk has no article
behind it.

Prospector vets business opportunities. It ranks ideas and companies, not people.
It makes no decision about a person's employment, credit, education, insurance or
access to a service. It is outside Annex III on its face.

**Two conditions would change that answer, and both are product decisions, not
engineering ones.**

The first is profiling. Article 6(3) closes with an absolute rule: an Annex III
system is *always* high-risk where it performs profiling of natural persons, and no
derogation is available. That only bites if we are already inside an Annex III
area, but it removes any argument we might otherwise have had if we moved into one.

The second is drift into employment. If prospector's signal sourcing were ever
pointed at ranking or filtering individual people for work — candidates,
contractors, freelancers — it lands in Annex III(4) and the whole high-risk regime
switches on. That is one product decision away, which is precisely why the
classification has to be a live field rather than a document written once.

Article 6(3) itself is our fallback, not our primary argument. It excuses an Annex
III system that performs a narrow procedural task, improves the result of a
completed human activity, detects deviations from prior decision patterns, or
performs a preparatory task. We do not need it, because we are not in Annex III at
all. It is worth knowing it exists for the day we consider a feature that would put
us there.

**Classification: our systems are minimal risk, save for any surface caught by
Article 50, which is limited risk.**

## 4. Article 50, the one live thing to build

Article 50 is the obligation the circulated report attributed to Article 13.
Article 13 is transparency owed by a provider of a *high-risk* system to its
deployer, which is not our situation. Article 50 is the user-facing one and it is
enforceable now.

Three sub-duties can reach us:

- **50(1)** — a system intended to interact directly with a person must inform that
  person they are dealing with an AI, unless it is obvious from the circumstances.
- **50(2)** — a provider of a system generating synthetic text, audio, image or
  video must mark the output in a machine-readable format and make it detectable as
  AI-generated.
- **50(4)** — a deployer publishing AI-generated text to inform the public on
  matters of public interest must disclose that it is AI-generated, unless a human
  reviewed it and someone holds editorial responsibility.

50(4) is the one to look at hardest. Prospector publishes vetted opportunity
reports. If any of that is published to inform the public, the disclosure is owed.
The exemption exists and we can rely on it, but relying on it means naming the human
who holds editorial responsibility, and that name has to be real.

## 5. We are not a GPAI provider

The circulated report raised "Articles 52-56" for general-purpose AI. That is the
draft numbering; the final text puts GPAI in Chapter V, Articles 51 to 56. The
substance matters more than the numbering.

Calling Claude, or any model, through an API does not make us the provider of a
GPAI model. That status attaches to whoever trains the model, or to a downstream
actor whose modification significantly changes the model's generality, capabilities
or systemic risk. Fine-tuning for our own task does not reach that bar. We are the
provider of an AI *system* built on someone else's model, which is a different and
much lighter set of duties.

Neither is a notified body relevant to us. Third-party conformity assessment under
Article 43 applies to Annex III(1) biometrics and to Annex I product-embedded
systems. Everything else is internal control. Engaging a notified body for an
internal developer platform would be spending money to answer a question nobody
asked.

## 6. The circulated report, row by row

Kept here because the same mistakes will be made again, and because a buyer's
engineer who reads both documents deserves to see which one we corrected.

| Row | Claim | What is actually true |
|---|---|---|
| Risk classification | Critical gap | Correct that we owe one. This document is it. |
| Risk management (Art. 9) | Critical | High-risk only. Deferred to 2 Dec 2027. Not applicable. |
| Data governance (Art. 10) | Critical | High-risk only, and addressed to training data. We train nothing. |
| Technical documentation (Art. 11) | Critical | High-risk only. Not applicable. |
| Record-keeping (Art. 12) | Medium | High-risk only. Our trace gap is real but it is not this. |
| Transparency (Art. 13) | Critical | Wrong article. Art. 13 runs to deployers of high-risk systems. Art. 50 is the live duty. |
| Human oversight (Art. 14) | Critical | High-risk only. Not applicable. |
| Accuracy, robustness (Art. 15) | Medium | High-risk only. Not applicable. |
| Quality management (Art. 17) | Critical | High-risk providers only. ISO 9001 alignment is not required of us by this Act. |
| Conformity assessment (Art. 43) | Critical | High-risk only, and mostly internal control even then. Not applicable. |
| CE marking (Art. 49) | Critical | High-risk only. Affixing a CE mark to a system that is not high-risk would itself be a misrepresentation. |
| EU database registration (Art. 71) | Critical | High-risk only. Registering a minimal-risk system is not possible. |
| — | not raised | **Art. 4 AI literacy. Live since Feb 2025. Ours is overdue.** |
| — | not raised | **Art. 50 transparency. Live since 2 Aug 2026.** |

## 7. What we build

The register is the deliverable, not the policy page. A policy page is a claim
about the estate; the estate is 291 catalog entities generated hourly from
`~/.estate/state/inventory.json`, and a claim that is not generated from that file
drifts away from it within a week. We have watched that happen to every document
that asserted state in prose.

So classification becomes a field, carried the way every other fact about an asset
is carried:

1. **`estate/ai-role`** on each entity — `none`, `provider`, `deployer`, or both.
   Sourced from the inventory, rendered by `bin/catalog-gen`, visible in the portal.
2. **`estate/ai-risk-tier`** — `minimal`, `limited`, `high`, `prohibited`, with
   `estate/ai-classified-on` carrying the date of the assessment and
   `estate/ai-basis` naming the article relied on. Article 6(3) requires the
   assessment be documented *before* the system is put into service; a dated field
   is that record.
3. **A gate.** A new component that calls a model and carries no `ai-role` fails
   CI. This is the half that makes the register survive us: without it, the register
   is accurate on the day it is written and wrong by the next merge.
4. **Article 50 disclosure as a platform default.** Any surface that talks to a
   person carries the disclosure because the platform gives it one, not because
   somebody remembered.
5. **Langfuse actually collecting.** Not because Article 12 requires it — it does
   not apply to us — but because "which model decided this, on what input, when" is
   the question every one of these regimes eventually asks, and today we cannot
   answer it. Measured 2026-08-25 with `bin/langfuse-verify`: the primary receiver
   rejected the test span with HTTP 000 and only the disk fallback caught it, six
   lines in `/data/traces.jsonl`. `bin/langfuse-status` reports the stored trace
   count as `unreadable`, so the honest statement is that the count is unknown, not
   that it is zero. Either way the backbone is not working.

This is why it is a platform layer and not a document. The buyer's lawyer asks
"show me your AI system inventory and its classification". Every other seller opens
a PDF that was true once. We open a URL, dated today, generated from the running
estate, with a gate behind it that refuses to let the two drift apart. That is a
diligence answer nobody else in our size class can give, and it is worth more than
the compliance it happens to demonstrate.

## 8. What this document does not cover, and the bigger exposure

**GDPR is the larger risk and it is not addressed here.** Prospector sources
candidates from signals. To the extent any of that touches personal data of people
in the EU or UK, the live questions are the Article 6 lawful basis, the Article 14
notice owed when data is collected from somewhere other than the person, and
whether a DPIA is required. Those regimes are in force, fully enforced, and have a
twenty-year record of penalties. A buyer's lawyer reaches them before the AI Act.
This should be assessed next and it is a bigger piece of work than the one above.

Also outside this document: the product liability regime as it now applies to
software, sectoral rules for any regulated customer we sell into, and the terms of
the model providers we build on.

**Residual.** The classification in §3 rests on what prospector does today, as
described in its README and its code. If the product moves toward ranking
individual people, §3 is wrong from that day and the whole high-risk regime applies
from 2 December 2027. The gate in §7 is what makes that change visible rather than
silent.

---

## Sources

- [Article 2: Scope](https://artificialintelligenceact.eu/article/2/)
- [Article 6: Classification rules for high-risk AI systems](https://artificialintelligenceact.eu/article/6/)
- [Annex III: High-risk AI systems](https://artificialintelligenceact.eu/annex/3/)
- [Article 4: AI literacy](https://artificialintelligenceact.eu/article/4/)
- [Article 50 transparency rules, practical guide](https://artificialintelligenceact.eu/transparency-rules-article-50/)
- [Article 99: Penalties](https://artificialintelligenceact.eu/article/99/)
- [European Commission — guidelines on transparency obligations](https://digital-strategy.ec.europa.eu/en/policies/guidelines-transparency-ai-generated-content)
- [White & Case — EU AI Omnibus enters into force, amending the AI Act](https://www.whitecase.com/insight-alert/eu-ai-omnibus-enters-force-amending-ai-act)
- [Gibson Dunn — postponed high-risk deadlines and other key changes](https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/)
- [Future of Privacy Forum — the AI Act implementation timeline after the Omnibus](https://fpf.org/blog/the-ai-act-implementation-timeline-what-changes-under-the-ai-omnibus/)
- [lawandtechnology.eu — the Omnibus rewrite of Article 4](https://lawandtechnology.eu/en/ai-literacy-digital-omnibus-article-4-ai-act/)
- [William Fry — extraterritorial reach of the AI Act](https://www.williamfry.com/knowledge/a-practical-guide-to-the-extraterritorial-reach-of-the-ai-act/)
- [Stephenson Harwood — GPAI model provider obligations](https://www.stephensonharwood.com/insights/eu-obligations-on-providers-of-gpai-models-under-the-eu-ai-act/)
