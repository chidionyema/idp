"""The consultation plane: budgeted, signed, blind-challenged consultation.

Three concerns, one package:

  * `budget_ledger`      -- micro-USD conservation and the Tier-0 digest cache.
  * `search_twin`        -- signed research receipts behind a trust firewall.
  * `dialectical_consult` -- the lead / blind challenge / veto pipeline.

This package is NOT the estate memory plane (ADR 0036) and NOT the estate spend
ledger (penny-core). It is the per-consultation enforcement surface in front
of them. Standard library only; no local browser is ever launched.
"""

from __future__ import annotations

__all__ = [
    "budget_ledger",
    "dialectical_consult",
    "search_twin",
]
