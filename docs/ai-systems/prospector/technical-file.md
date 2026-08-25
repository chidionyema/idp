# Prospector: technical documentation (Annex IV)

Kept voluntarily to Annex IV shape for a limited-risk system (founder, 2026-08-25).
Section numbers follow Annex IV of Regulation (EU) 2024/1689; the structure follows
aai-institute/practical-ai-act. `bin/ai-act-gate` refuses this file if a section is
missing. Owner: chidionyema. Last reviewed: 2026-08-25.

## 1. General description

Prospector researches companies and contacts from public sources and drafts B2B
outreach for a human to send. The estate is its **provider** (Art. 3(3): placed on
the market under our name) and its **deployer** (Art. 3(4)). Model vendors carry
only the Ch. V model duties; calling their API transfers no system duty to them.
Risk tier: **limited** (Art. 50: generated text reaches natural persons, so a
disclosure is owed; no Annex III area applies:
not biometrics, critical infrastructure, education, employment, essential services,
law enforcement, migration or justice). Intended user: the founder and sales staff.
Not intended for: automated sending, decisions about individuals, consumer targeting.

## 2. Elements and development process

- Design: research → verify → draft pipeline in `prospector-main`; each step is a
  separate operator with a fixed system prompt.
- Architecture: Python services, model calls through the operator factory (LiteLLM
  routing pending, LAW 34), traces to Langfuse (onboarding pending).
- Data requirements: the declared sources in `platform/ai/systems.yaml`, section
  `data_sources`, with provenance, lawful basis, personal-data class and retention.
- Human oversight: every draft is reviewed by a person before it leaves; sending
  and spending tools require an approval step.
- Validation and testing: incident tests per bug (`tests/`), verifier step refuses
  unsourced claims, `bin/ai-act-gate` on every pull request.

## 3. Monitoring, functioning and control

Runtime traces are the audit trail (Langfuse, STANDARDS row Agent traces). Known
limits: the model can state plausible falsehoods; scraped pages can carry
instructions. Both are risks R-PROSP-002 and R-PROSP-005 with live mitigations.

## 4. Performance metrics

Measured per run in the research record: claims with a source / total claims;
drafts accepted by the reviewer without edit; provider error rate. Baselines are
not yet published; the Langfuse onboarding publishes them.

## 5. Risk management system

`platform/ai/risk-register.yaml`, entries R-PROSP-001 to R-PROSP-005, each with
owner, likelihood, impact, mitigation, an OWASP AI Exchange control and a review
date. Reviewed quarterly; the gate refuses an overdue entry.

## 6. Changes through the lifecycle

Every change is a pull request with CI evidence; model changes are a register
edit here, reviewed like code. Retired models are removed from `models`.

## 7. Standards applied

ISO/IEC 27001:2022 Annex A for the security controls (`docs/reference/security-policy.md`);
OWASP AI Exchange for AI risk controls; ISO/IEC 42001 clauses as the management
frame, noting it is not a harmonised standard under the Act.

## 8. Declaration of conformity

Not required for a limited-risk system. `bin/conformity-report` renders the Annex
VI internal-control assessment from the gates' output on demand; it is generated,
never hand-written.

## 9. Post-market monitoring

Incidents go to the crew board with the `security` label; each one becomes a
guard (LAW 45). Provider policy changes are checked at each quarterly review.
