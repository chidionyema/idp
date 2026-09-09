# Forge compute spend

Generated 2026-09-09T07:06:03Z. Cumulative spend across recorded Forge runs (1 spend-bearing record(s)).

**Cumulative Modal/compute spend: **$0.1632** against a $5.00 cap.**

**Under the cap: runs may dispatch.**

| record | usd |
|---|---|
| 20260909T0137Z-ci-flake-triage.md | $0.1632 |

The cap lives in forge/common.py (modal_spend_gate, DEFAULT_MONTHLY_CAP_USD) and is enforced before a Modal GPU bills; Kaggle's free lane adds no usd.