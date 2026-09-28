# Declare an AI system

Every AI system the estate runs or sells is registered before it ships (Arts. 9, 10,
11 kept voluntarily; founder 2026-08-25). Four steps, all files, all gated.

1. Add the system to `platform/ai/systems.yaml`: owner, role (provider or deployer),
   risk tier with the Annex III reasoning in the technical file, models, and every
   data source with provenance, lawful basis, personal-data class and retention.
2. Copy `docs/ai-systems/prospector/technical-file.md`, keep the nine Annex IV
   section headings, fill each one.
3. Add at least one risk per system to `platform/ai/risk-register.yaml` with an
   OWASP AI Exchange control id and a review date within a quarter.
4. Run `bin/ai-act-gate`; it refuses a missing section, field, source or overdue
   review. `bin/conformity-report` renders the Annex VI assessment for a buyer.

Demo: `bin/conformity-report` on main prints prospector's assessment from the gates.
