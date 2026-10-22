"""Throwaway: read-only. Which Modal apps spent this billing cycle's credit? Starts no containers."""
import datetime as dt
import json

import modal

now = dt.datetime.now(dt.timezone.utc)
start = now - dt.timedelta(days=45)
try:
    rows = modal.billing.workspace_billing_report(start=start, end=now, resolution="d")
    rows = list(rows) if not hasattr(rows, "__aiter__") else rows
    print("BILL rows", len(rows))
    by_app: dict[str, float] = {}
    by_day: dict[str, float] = {}
    for r in rows:
        cost = float(r.get("cost", 0))
        by_app[r.get("description", "?")] = by_app.get(r.get("description", "?"), 0) + cost
        d = str(r.get("interval_start", ""))[:10]
        by_day[d] = by_day.get(d, 0) + cost
    print("BILL by_app", json.dumps(dict(sorted(by_app.items(), key=lambda kv: -kv[1])), indent=1))
    print("BILL by_day", json.dumps(dict(sorted(by_day.items())), indent=1))
except Exception as exc:  # noqa: BLE001 -- a probe: say what happened
    print("BILL error", type(exc).__name__, str(exc)[:400])
print("BILL sample", json.dumps(rows[0], default=str) if rows else None)
