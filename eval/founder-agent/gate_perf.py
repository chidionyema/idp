"""Performance, and the recursion that makes a round worth running (idp#6921).

The gate already grades whether Otto *did* the task. This module grades the two things the spec puts
beside correctness -- G6 (latency) and G10 (cost, and regression against the last round) -- and it
keeps the loop honest by grading the harness's own previous output: every round names the
improvements it demands of the next one, and the next round has to say, item by item, which of them
closed. That is the whole recursion. It is measured, not narrated: an item closes when this round's
own numbers no longer contain it, and by nothing else (no model reads the report and declares success).

Plain data, no agent, no clock of its own:

* `aggregate(rows)`            -  p50/p95/max answer latency, cost, models, lanes, from per-run metrics.
* `compare(current, previous)` -  one named row per threshold, each `pass`, `fail` or
  `insufficient-data`. A round with no predecessor is `insufficient-data`, never a pass: round 0 has
  nothing to regress against, and saying so is the point.
* `improvement(report, previous)` -  the items this round demands (failed tasks, the slowest tasks,
  any regression) and the closure of last round's items.
"""

from __future__ import annotations

from typing import Any

#: A round regresses on latency when p95 answer time grows by more than this against the round
#: before it. 50% is the spec's G6 tolerance for a *degraded* round, not a preferred number: a
#: change that doubles latency and calls itself green is the defect this threshold names.
LATENCY_REGRESSION_PCT = 50.0

#: A round regresses on cost when total spend grows by more than this. Cost is compared on the same
#: suite sha only (see `compare`): two different suites are two different measurements.
COST_REGRESSION_PCT = 25.0

#: How many of the slowest tasks an improvement list carries. Three is enough to aim at without
#: turning the report into a table nobody reads.
SLOWEST = 3


def _numbers(rows: list[dict], key: str) -> list[float]:
    out: list[float] = []
    for r in rows:
        v = r.get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out.append(float(v))
    return out


def _quantile(values: list[float], q: float) -> float | None:
    """Nearest-rank quantile. No interpolation, so the number printed is a measurement that
    happened, not a value between two of them."""
    if not values:
        return None
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, int(round(q * (len(ordered) - 1)))))
    return round(ordered[idx], 1)


def aggregate(rows: list[dict]) -> dict[str, Any]:
    """One round's performance, from the per-run metrics the adapters wrote.

    `rows` is one dict per run: `answered_ms` (asked -> answer read back), `accepted_ms` (asked ->
    the door's status), `cost_usd`, `model`, `lane`, `attempts`, `verified`, `task`.
    """
    answered = _numbers(rows, "answered_ms")
    accepted = _numbers(rows, "accepted_ms")
    cost = sum(_numbers(rows, "cost_usd"))
    models = sorted({str(r["model"]) for r in rows if r.get("model")})
    lanes = sorted({str(r["lane"]) for r in rows if r.get("lane")})
    verified = [r for r in rows if r.get("verified") is not None]
    return {
        "runs": len(rows),
        "runs_answered": len(answered),
        "answered_ms": {
            "p50": _quantile(answered, 0.50),
            "p95": _quantile(answered, 0.95),
            "max": round(max(answered), 1) if answered else None,
        },
        "accepted_ms": {
            "p50": _quantile(accepted, 0.50),
            "p95": _quantile(accepted, 0.95),
        },
        "cost_usd": round(cost, 4),
        "cost_per_task_usd": round(cost / len(rows), 4) if rows else None,
        "models": models,
        "lanes": lanes,
        "verified_runs": len(verified),
        "verified_clean": sum(1 for r in verified if r.get("verified") is True),
    }


def _row(
    metric: str,
    current: float | None,
    previous: float | None,
    status: str,
    why: str,
    unit: str = "",
) -> dict[str, Any]:
    change = None
    if current is not None and previous not in (None, 0):
        change = round((current - previous) / previous * 100.0, 1)
    return {
        "metric": metric,
        "current": current,
        "previous": previous,
        "change_pct": change,
        "unit": unit,
        "status": status,
        "why": why,
    }


def compare(
    current: dict[str, Any],
    previous: dict[str, Any] | None,
    *,
    current_suite_sha: str | None = None,
    previous_suite_sha: str | None = None,
) -> list[dict[str, Any]]:
    """Grade this round against the one before it. Every row names its threshold and its data."""
    cur_lat = (current.get("answered_ms") or {}).get("p95")
    cur_cost = current.get("cost_usd")
    rows: list[dict[str, Any]] = []

    if previous is None:
        rows.append(
            _row(
                "latency_p95",
                cur_lat,
                None,
                "insufficient-data",
                "no previous round to compare against: round 0 cannot regress",
                "ms",
            )
        )
        rows.append(
            _row(
                "cost_usd",
                cur_cost,
                None,
                "insufficient-data",
                "no previous round to compare against: round 0 cannot regress",
                "usd",
            )
        )
        return rows

    prev_lat = (previous.get("answered_ms") or {}).get("p95")
    if (
        current_suite_sha
        and previous_suite_sha
        and current_suite_sha != previous_suite_sha
    ):
        note = (
            "the suite changed since the previous round, so latency and cost are not "
            "comparable; re-baseline before reading a regression"
        )
        rows.append(
            _row("latency_p95", cur_lat, prev_lat, "insufficient-data", note, "ms")
        )
        rows.append(
            _row(
                "cost_usd",
                cur_cost,
                previous.get("cost_usd"),
                "insufficient-data",
                note,
                "usd",
            )
        )
        return rows

    if cur_lat is None or prev_lat in (None, 0):
        rows.append(
            _row(
                "latency_p95",
                cur_lat,
                prev_lat,
                "insufficient-data",
                "no answered runs on one side of the comparison",
                "ms",
            )
        )
    else:
        limit = prev_lat * (1 + LATENCY_REGRESSION_PCT / 100.0)
        ok = cur_lat <= limit
        rows.append(
            _row(
                "latency_p95",
                cur_lat,
                prev_lat,
                "pass" if ok else "fail",
                f"p95 {'within' if ok else 'over'} the {LATENCY_REGRESSION_PCT:.0f}% tolerance "
                f"({limit:.0f} ms)",
                "ms",
            )
        )

    prev_cost = previous.get("cost_usd")
    if cur_cost is None or prev_cost in (None, 0):
        rows.append(
            _row(
                "cost_usd",
                cur_cost,
                prev_cost,
                "insufficient-data",
                "the previous round spent nothing, so there is no baseline to regress from",
                "usd",
            )
        )
    else:
        limit = prev_cost * (1 + COST_REGRESSION_PCT / 100.0)
        ok = cur_cost <= limit
        rows.append(
            _row(
                "cost_usd",
                cur_cost,
                prev_cost,
                "pass" if ok else "fail",
                f"spend {'within' if ok else 'over'} the {COST_REGRESSION_PCT:.0f}% tolerance "
                f"(${limit:.2f})",
                "usd",
            )
        )
    return rows


def verdict(rows: list[dict[str, Any]]) -> str:
    """`fail` if any threshold failed; `insufficient-data` if any row could not be measured.

    A row that could not be measured is never folded into a pass -- the same rule the rest of the
    harness keeps for a run the agent was never asked.
    """
    if any(r["status"] == "fail" for r in rows):
        return "fail"
    if any(r["status"] == "insufficient-data" for r in rows):
        return "insufficient-data"
    return "pass"


def items_for(report: dict[str, Any]) -> list[dict[str, Any]]:
    """What this round demands of the next one, derived from its own measurements."""
    items: list[dict[str, Any]] = []
    for f in report.get("failures") or []:
        reason = (f.get("reasons") or [""])[0]
        cause = (f.get("cause") or [""])[0]
        items.append(
            {
                "id": f"task:{f['task']}",
                "kind": "task",
                "subject": f["task"],
                "category": f.get("category"),
                "why": reason or cause or "failed with no reason recorded",
            }
        )
    for row in report.get("performance", {}).get("slowest", []):
        items.append(
            {
                "id": f"latency:{row['task']}",
                "kind": "latency",
                "subject": row["task"],
                "why": f"p95 {row['answered_ms']:.0f} ms is among the slowest in this round",
            }
        )
    for row in (report.get("gates", {}).get("P") or {}).get("rows", []):
        if row["status"] == "fail":
            items.append(
                {
                    "id": f"regression:{row['metric']}",
                    "kind": "regression",
                    "subject": row["metric"],
                    "why": row["why"],
                }
            )
    return items


def closure(
    previous_items: list[dict[str, Any]], current_items: list[dict[str, Any]]
) -> dict[str, Any]:
    """Last round's items, each `closed` or `open` against this round's own measurements.

    Closed means the item is absent from this round: the task passed, the task is no longer among
    the slowest, the threshold is no longer exceeded. Nothing else counts as closed, which is what
    stops a round from being "improved" by writing about it.
    """
    current_ids = {i["id"] for i in current_items}
    rows = [
        {
            "id": i["id"],
            "kind": i.get("kind"),
            "subject": i.get("subject"),
            "demanded_by_round": i.get("round"),
            "state": "open" if i["id"] in current_ids else "closed",
            "why": i.get("why", ""),
        }
        for i in previous_items
    ]
    closed = sum(1 for r in rows if r["state"] == "closed")
    return {
        "previous_round": None,
        "rows": rows,
        "closed": closed,
        "open": len(rows) - closed,
        "closure_rate": round(closed / len(rows), 3) if rows else None,
    }
