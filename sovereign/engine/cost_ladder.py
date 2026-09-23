"""The Rung 0-3 compute cost ladder (idp#3525 CP1, COST-03).

"The cost ladder (Rung 0-3) SHALL be versioned config data. Rung 2
(flat-rate rental) SHALL activate only when measured trace volume crosses
the breakeven band computed from real router token prices ... No
pre-commitment."

The ladder itself lives in platform/llm/cost-ladder.yaml, not here --
this module only loads it and does the one piece of arithmetic the spec
requires: at what monthly token volume does a flat-rate rung 2 lease cost
the same as staying on the metered router. Below that volume the router
is cheaper; above it, the lease is. Because router prices differ for
input vs output tokens, the breakeven point is a band, not a point: an
all-output workload crosses it at a lower token count than an all-input
one.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_LADDER_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "platform"
    / "llm"
    / "cost-ladder.yaml"
)

RUNG_ROUTER_METERED = 1
RUNG_FLAT_RATE = 2


class LadderError(ValueError):
    """The ladder file is missing, unparsable, or lacks a rung §3.03 needs."""


def load_ladder(path: Path | None = None) -> dict[str, Any]:
    path = path or DEFAULT_LADDER_PATH
    try:
        text = path.read_text()
    except OSError as exc:
        raise LadderError(f"cannot read {path}: {exc}") from exc
    data = yaml.safe_load(text)
    if not isinstance(data, dict) or not isinstance(data.get("rungs"), list):
        raise LadderError(f"{path}: not a ladder document (need version + rungs)")
    return data


def _rung(ladder: dict[str, Any], rung: int) -> dict[str, Any]:
    for row in ladder["rungs"]:
        if int(row.get("rung", -1)) == rung:
            return row
    raise LadderError(f"ladder has no rung {rung}")


def breakeven_band_tokens(
    flat_rate_usd_per_month: float,
    input_cost_per_token: float,
    output_cost_per_token: float,
) -> tuple[float, float]:
    """(low, high) monthly token volumes at which the flat-rate lease
    costs the same as staying on the metered router.

    Low end: an all-output workload (output tokens are the pricier of
    the two) reaches the lease's price at the fewest tokens. High end:
    an all-input workload (cheaper per token) needs the most tokens to
    reach the same price. A real workload is a mix of both, so it
    crosses breakeven somewhere inside this band, never outside it.
    """
    if flat_rate_usd_per_month <= 0:
        raise LadderError("flat_rate_usd_per_month must be positive")
    if input_cost_per_token <= 0 or output_cost_per_token <= 0:
        raise LadderError("router token prices must be positive")
    low = flat_rate_usd_per_month / output_cost_per_token
    high = flat_rate_usd_per_month / input_cost_per_token
    return (low, high)


@dataclass(frozen=True)
class LadderEvaluation:
    rung: int
    tokens_per_month: float
    band_low: float
    band_high: float
    activation_proposed: bool
    flat_rate_usd_per_month: float


def evaluate(
    tokens_per_month: float, ladder: dict[str, Any] | None = None
) -> LadderEvaluation:
    """COST-03's ACCEPT: below the band, no proposal; above it, a
    proposal carrying the computed numbers. "Crosses the breakeven band"
    is read conservatively -- a proposal fires only once volume clears
    `band_high`, the token count at which the lease wins even under the
    cheapest (all-input) router mix, so a real workload's actual mix
    (somewhere inside the band) can never make a proposed activation a
    loss. Inside the band is deliberately still "no proposal": that is
    the "No pre-commitment" half of COST-03, not a gap.

    Never a pre-commitment -- this function only ever reports; nothing
    here provisions anything (that boundary is
    sovereign.engine.paid_compute.activate, gated on a hardware signature
    per COST-02, called by whoever acts on a proposal this function
    returns)."""
    ladder = ladder or load_ladder()
    router = _rung(ladder, RUNG_ROUTER_METERED)
    flat = _rung(ladder, RUNG_FLAT_RATE)
    low, high = breakeven_band_tokens(
        float(flat["usd_per_month"]),
        float(router["input_cost_per_token"]),
        float(router["output_cost_per_token"]),
    )
    return LadderEvaluation(
        rung=RUNG_FLAT_RATE,
        tokens_per_month=float(tokens_per_month),
        band_low=low,
        band_high=high,
        activation_proposed=float(tokens_per_month) >= high,
        flat_rate_usd_per_month=float(flat["usd_per_month"]),
    )
