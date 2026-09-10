# Forge compute spend

Generated 2026-09-10T22:20:07Z. Cumulative spend across recorded Forge runs (2 spend-bearing record(s)).

**Cumulative Modal/compute spend: **$0.3235** against a $5.00 cap.**

**Under the cap: runs may dispatch.**

| record | usd |
|---|---|
| 20260909T0137Z-ci-flake-triage.md | $0.1632 |
| 20260909T2048Z-ci-flake-triage.md | $0.1603 |

The cap lives in forge/common.py (modal_spend_gate, DEFAULT_MONTHLY_CAP_USD) and is enforced before a Modal GPU bills; Kaggle's free lane adds no usd.