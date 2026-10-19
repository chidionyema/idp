"""The scheduled half of Active Memory consolidation (a CronJob; see oke-unified-memory.yaml).

What already consolidates, per turn: every `remember` posts its fact to
/harness/memory/consolidate, where ActiveMemoryEngine gates ephemeral facts into the scratchpad,
promotes a recurring preference, and writes a permanent fact bi-temporally. That path is wired
(mcp/plugins/estate_memory.py, idp#6254, #6581) and needs no schedule.

What nothing did, until this: housekeeping between turns. Scratchpad rows past `expires_at` were
deleted only when the same run next read its own scratchpad, so a run that never came back left its
rows forever; preference-recurrence counters were never aged out.

What this deliberately does NOT do, and why:
  - It does not promote or quarantine memories (curation_worker.py's job, never deployed). Under
    the default scores (rho = tau = 1, harm 0) the promotion gate passes every fact, and an UPDATE
    of `memories` fires fn_bump_memory_version, which resets updated_at -- it would make every old
    fact look new to ranking.py. That needs its own decision, not a side effect of a sweep.
  - It does not distil episodic facts into semantic ones. That needs a model call; the estate's
    `chat` lane could do it, but nobody has measured whether it improves recall, and a write path
    that invents facts is a trust-boundary change (anti-Ouroboros, schema.sql section 6).

Each tenant is swept in its own transaction with app.tenant_id set, because every table touched is
FORCE ROW LEVEL SECURITY: without the GUC the DELETE matches nothing and reports success (the same
failure idp#6507 found on the harness conns).
"""

from __future__ import annotations

import os
import sys

# A preference seen once and never again carries no signal after this long.
RECURRENCE_MAX_AGE_DAYS = int(os.environ.get("MEMORY_RECURRENCE_MAX_AGE_DAYS", "90"))


def _secret(name: str):
    path = os.environ.get(f"{name}_FILE")
    if path:
        with open(path) as f:
            return f.read().strip()
    return os.environ.get(name)


def sweep_tenant(cur, tenant_id: str) -> dict:
    """Housekeeping for one tenant, inside the caller's transaction. Returns what it removed."""
    cur.execute("SELECT set_config('app.tenant_id', %s, true);", (tenant_id,))
    cur.execute("DELETE FROM harness_scratchpad WHERE expires_at < CURRENT_TIMESTAMP;")
    scratchpad = cur.rowcount
    cur.execute(
        "DELETE FROM preference_recurrence "
        "WHERE updated_at < CURRENT_TIMESTAMP - make_interval(days => %s);",
        (RECURRENCE_MAX_AGE_DAYS,),
    )
    return {"scratchpad_expired": scratchpad, "recurrence_aged": cur.rowcount}


def sweep(conn) -> dict:
    """Sweep every tenant; one tenant failing does not stop the others."""
    with conn.cursor() as cur:
        cur.execute("SELECT tenant_id FROM tenants;")
        tenants = [str(r["tenant_id"]) for r in cur.fetchall()]
    totals = {
        "tenants": len(tenants),
        "failed": 0,
        "scratchpad_expired": 0,
        "recurrence_aged": 0,
    }
    for tid in tenants:
        try:
            with conn.transaction(), conn.cursor() as cur:
                got = sweep_tenant(cur, tid)
            for k, v in got.items():
                totals[k] += v
        except Exception as e:  # noqa: BLE001 -- isolate tenants; report the count below
            totals["failed"] += 1
            print(f"consolidation: tenant {tid} failed: {e}", file=sys.stderr)
    return totals


def main() -> int:
    import psycopg
    from psycopg.rows import dict_row

    url = _secret("DATABASE_URL")
    if not url:
        print(
            "consolidation: DATABASE_URL (or DATABASE_URL_FILE) is required",
            file=sys.stderr,
        )
        return 2
    with psycopg.connect(url, row_factory=dict_row) as conn:
        totals = sweep(conn)
    print(f"consolidation: {totals}")
    # A sweep that failed for any tenant must not look green to the CronJob.
    return 1 if totals["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
