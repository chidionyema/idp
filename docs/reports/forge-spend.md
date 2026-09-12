# Forge compute spend

Generated 2026-09-12T17:20:04Z. Cumulative spend across recorded Forge runs (5 spend-bearing record(s)).

**Cumulative Modal/compute spend: **$0.7095** against a $5.00 cap.**

**Under the cap: runs may dispatch.**

| record | usd |
|---|---|
| 20260909T0137Z-ci-flake-triage.md | $0.1632 |
| 20260909T2048Z-ci-flake-triage.md | $0.1603 |
| 20260911T1113Z-ticket-lane-triage.md | $0.0505 |
| 20260911T1232Z-ci-flake-triage.md | $0.1593 |
| 20260911T1657Z-ci-flake-triage.md | $0.1762 |

The cap lives in forge/common.py (modal_spend_gate, DEFAULT_MONTHLY_CAP_USD) and is enforced before a Modal GPU bills; Kaggle's free lane adds no usd.