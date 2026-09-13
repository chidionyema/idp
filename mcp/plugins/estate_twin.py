"""Datasette plugin: the `get_estate_state` MCP tool (estate-twin, 2026-09-12).

Registers one tool on the EXISTING estate MCP server through datasette-mcp's own extension
point, `register_mcp_tools(datasette, mcp)` -- the same mechanism the other plugins use. This
is not a second server (ADR 0006: "extend `mcp/`; never add a second server"), and it reads
the same `catalog/estate.db` the server already mounts.

WHY THIS EXISTS. The estate had three inventories and every one described DECLARED state --
what `clusters/` and `platform/` say, plus what git declares. Measured 2026-09-12, none of
them could name a single one of: 1,523 unmerged branches, 722 files that exist on no commit
of main, 11 zero-scaled deployments, or three agents deployed and dead (`research` 0/1,
`hindsight` 0/1, `otto-gateway` 2/13). A dead pod is declared nowhere.

`bin/estate-twin-runtime` writes that missing half into estate.db. This tool is the half that
lets an AGENT read it, so the next session asked "do we already have this?" stops answering
no and rebuilding work that exists on a branch.

NO SUBPROCESS, NO SHELL. Everything below reads the mounted SQLite file. The one deliberate
exception is the freshness window, which is a column, not a clock call.

CONFIG (LAW 46 -- no path or port is a literal in code that decides behaviour):
  ESTATE_DB_PATH              catalog/estate.db, already mounted read-only (default /data/estate.db)
  ESTATE_TWIN_BYTE_CEILING    payload ceiling in bytes; ADR 0006 point 2, "fat tools,
                              summarised by default" (default 8000)
  ESTATE_TWIN_FRESH_S         the window a domain is judged fresh within (default 180)
"""

from __future__ import annotations

import json
import os
import sqlite3

try:  # datasette-mcp's plugin hook, exactly as the sibling plugins load it
    from datasette import hookimpl
except Exception:  # pragma: no cover - importable outside Datasette for tests

    def hookimpl(fn):
        return fn


def config() -> dict:
    return {
        "db_path": os.environ.get("ESTATE_DB_PATH", "/data/estate.db"),
        "ceiling": int(os.environ.get("ESTATE_TWIN_BYTE_CEILING", "8000")),
        "fresh_s": int(os.environ.get("ESTATE_TWIN_FRESH_S", "180")),
    }


# What "not serving" means, precisely. A workload that should be up and is not; built work
# that runs nowhere. NOT this list: `event` and `diagnosis` nodes carry status `dead` because
# they are records of a failure, not failures -- 240 warning events ranked above 2 dead
# deployments is the same mistake that made the first dead list 215 rows long.
NOT_SERVING = ("dead", "crashlooping", "stranded")

# Node types that ARE a failure, in the order a founder should read them.
FAILURE_TYPES = (
    "deployment",
    "statefulset",
    "daemonset",
    "pod",
    "secret-staleness",
    "unlisted-service",
    "branch",
    "collector-error",
    "monitoring",
    "identity",
    "capacity",
)
# Node types that are EVIDENCE about a failure, reported separately so they never bury one.
EVIDENCE_TYPES = ("event", "diagnosis", "alert", "flux")
STATES = ("MEASURED_OK", "MEASURED_FAIL", "UNKNOWN")


def _connect(db_path: str) -> sqlite3.Connection:
    """Read-only, and immutable: this tool can never write the graph it reports on."""
    uri = f"file:{db_path}?mode=ro&immutable=1"
    return sqlite3.connect(uri, uri=True, timeout=10)


def domain_states(con: sqlite3.Connection, fresh_s: int) -> list[dict]:
    """The estate's three-state rule, per domain -- the same rule the CLI applies.

    `UNKNOWN` is the default and is not a failure. A reader that cannot tell a five-minute
    answer from a five-day one is exactly the failure this whole system exists to prevent,
    so a domain with no freshness row, or one read outside its window, is UNKNOWN and never
    MEASURED_OK.
    """
    out: list[dict] = []
    try:
        rows = list(con.execute("select domain, fresh_s, updated_at from freshness"))
    except sqlite3.OperationalError:
        rows = []
    seen = {r[0] for r in rows}
    for domain, win, updated in rows:
        age = con.execute(
            "select cast((julianday('now') - julianday(?)) * 86400 as integer)",
            (updated,),
        ).fetchone()[0]
        age = int(age or 0)
        total = con.execute(
            "select count(*) from nodes where domain = ?", (domain,)
        ).fetchone()[0]
        if age > int(win):
            out.append(
                {
                    "domain": domain,
                    "state": "UNKNOWN",
                    "nodes": total,
                    "age_s": age,
                    "window_s": int(win),
                }
            )
            continue
        bad = con.execute(
            "select count(*) from nodes where domain = ? and status in (?,?,?)",
            (domain, *NOT_SERVING),
        ).fetchone()[0]
        out.append(
            {
                "domain": domain,
                "state": "MEASURED_FAIL" if bad else "MEASURED_OK",
                "nodes": total,
                "not_serving": bad,
                "age_s": age,
                "window_s": int(win),
            }
        )
    # A domain with nodes and no freshness row is UNKNOWN, not absent.
    for (domain,) in con.execute("select distinct domain from nodes"):
        if domain not in seen:
            total = con.execute(
                "select count(*) from nodes where domain = ?", (domain,)
            ).fetchone()[0]
            out.append(
                {
                    "domain": domain,
                    "state": "UNKNOWN",
                    "nodes": total,
                    "age_s": None,
                    "window_s": fresh_s,
                }
            )
    return sorted(out, key=lambda d: d["domain"])


def _json_bytes(obj) -> int:
    return len(json.dumps(obj, default=str).encode())


def _fit(items: list, ceiling: int, render) -> tuple[list, bool, int]:
    """Trim a list until the rendered payload fits the ceiling, and say that it was trimmed.

    A tool that silently truncates is a tool whose absence reads as "nothing there" -- the
    same class of lie as an inventory that reports declared state as actual. So the caller
    is always told `truncated` and the true count.
    """
    kept: list = []
    for item in items:
        trial = kept + [item]
        if _json_bytes(render(trial)) > ceiling and kept:
            return kept, True, len(items)
        kept = trial
    return kept, False, len(items)


def build_estate_state(
    domain: str | None = None, query: str | None = None, cfg: dict | None = None
) -> dict:
    """One call answers what the estate IS, not what it declares.

    `domain`  'runtime' | 'code' | ... -- narrows the answer.
    `query`   a substring matched against node ids, so "lago" or "stranded" narrows it.

    Summarised by default under a byte ceiling: counts and the worst offenders, never raw
    rows. Drilling is the caller asking again with a narrower `query`.
    """
    cfg = cfg or config()
    db_path = str(cfg["db_path"])
    ceiling = int(cfg["ceiling"])
    fresh_s = int(cfg["fresh_s"])

    if not os.path.exists(db_path):
        # BLIND, named. Not an empty answer, which would read as "nothing is broken".
        return {
            "state": "UNKNOWN",
            "why": f"the estate graph is not at {db_path}; bin/estate-twin-runtime has never run",
            "domains": [],
        }

    con = _connect(db_path)
    try:
        domains = domain_states(con, fresh_s)

        # Four fixed statements per query, chosen by which filters the caller passed. No SQL
        # text is assembled from a variable, so a reader can check every statement in one
        # glance and no value ever reaches the query text.
        #
        # `type in (...)` and `status in (...)` are written out: the tuples are module
        # constants, not caller input, but spelling them keeps the text free of `join`.
        params: tuple = ()
        if domain and query:
            counts_sql = (
                "select domain, type, status, count(*) from nodes "
                "where domain = ? and id like ? group by 1,2,3 order by 4 desc"
            )
            fail_sql = (
                "select id, status, metadata from nodes "
                "where domain = ? and id like ? "
                "and status in ('dead','crashlooping','stranded') "
                "and type in ('deployment','statefulset','daemonset','pod',"
                "'secret-staleness','unlisted-service','branch','collector-error',"
                "'monitoring','identity','capacity') "
                "order by case type when 'deployment' then 0 when 'statefulset' then 1 "
                "when 'daemonset' then 2 when 'pod' then 3 else 4 end, "
                "case status when 'crashlooping' then 0 when 'dead' then 1 else 2 end, id"
            )
            ev_sql = (
                "select type, count(*) from nodes "
                "where domain = ? and id like ? "
                "and type in ('event','diagnosis','alert','flux') group by 1 order by 2 desc"
            )
            params = (domain, f"%{query}%")
        elif domain:
            counts_sql = (
                "select domain, type, status, count(*) from nodes "
                "where domain = ? group by 1,2,3 order by 4 desc"
            )
            fail_sql = (
                "select id, status, metadata from nodes where domain = ? "
                "and status in ('dead','crashlooping','stranded') "
                "and type in ('deployment','statefulset','daemonset','pod',"
                "'secret-staleness','unlisted-service','branch','collector-error',"
                "'monitoring','identity','capacity') "
                "order by case type when 'deployment' then 0 when 'statefulset' then 1 "
                "when 'daemonset' then 2 when 'pod' then 3 else 4 end, "
                "case status when 'crashlooping' then 0 when 'dead' then 1 else 2 end, id"
            )
            ev_sql = (
                "select type, count(*) from nodes where domain = ? "
                "and type in ('event','diagnosis','alert','flux') group by 1 order by 2 desc"
            )
            params = (domain,)
        elif query:
            counts_sql = (
                "select domain, type, status, count(*) from nodes "
                "where id like ? group by 1,2,3 order by 4 desc"
            )
            fail_sql = (
                "select id, status, metadata from nodes where id like ? "
                "and status in ('dead','crashlooping','stranded') "
                "and type in ('deployment','statefulset','daemonset','pod',"
                "'secret-staleness','unlisted-service','branch','collector-error',"
                "'monitoring','identity','capacity') "
                "order by case type when 'deployment' then 0 when 'statefulset' then 1 "
                "when 'daemonset' then 2 when 'pod' then 3 else 4 end, "
                "case status when 'crashlooping' then 0 when 'dead' then 1 else 2 end, id"
            )
            ev_sql = (
                "select type, count(*) from nodes where id like ? "
                "and type in ('event','diagnosis','alert','flux') group by 1 order by 2 desc"
            )
            params = (f"%{query}%",)
        else:
            counts_sql = (
                "select domain, type, status, count(*) from nodes "
                "group by 1,2,3 order by 4 desc"
            )
            fail_sql = (
                "select id, status, metadata from nodes "
                "where status in ('dead','crashlooping','stranded') "
                "and type in ('deployment','statefulset','daemonset','pod',"
                "'secret-staleness','unlisted-service','branch','collector-error',"
                "'monitoring','identity','capacity') "
                "order by case type when 'deployment' then 0 when 'statefulset' then 1 "
                "when 'daemonset' then 2 when 'pod' then 3 else 4 end, "
                "case status when 'crashlooping' then 0 when 'dead' then 1 else 2 end, id"
            )
            ev_sql = (
                "select type, count(*) from nodes "
                "where type in ('event','diagnosis','alert','flux') group by 1 order by 2 desc"
            )

        counts = list(con.execute(counts_sql, params))
        not_serving = list(con.execute(fail_sql, params))
        evidence = list(con.execute(ev_sql, params))
    finally:
        con.close()

    rows = [{"id": i, "status": s, "detail": _summarise(m)} for i, s, m in not_serving]
    kept, truncated, total = _fit(rows, ceiling, lambda k: {"not_serving": k})

    payload = {
        "read_at": _read_at(db_path),
        "domains": domains,
        "counts": [
            {"domain": d, "type": t, "status": s, "n": n} for d, t, s, n in counts
        ],
        "not_serving_total": len(rows),
        "not_serving": kept,
        "evidence": [{"type": t, "n": n} for t, n in evidence],
        "truncated": truncated,
    }
    if truncated:
        payload["note"] = (
            f"{len(rows) - len(kept)} more not shown under the {ceiling}-byte "
            f"ceiling; narrow with a domain or a query"
        )
    return payload


def _summarise(metadata: str) -> dict:
    """The few fields that make a row actionable, never the raw payload."""
    try:
        m = json.loads(metadata)
    except Exception:
        return {}
    out = {}
    for k in (
        "namespace",
        "workload",
        "name",
        "ready",
        "replicas",
        "restarts",
        "unmerged_files",
        "staleness_days",
        "age_s",
        "reason",
        "since",
        "kinds_scanned",
        "interval",
        "remediation_enabled",
        "state",
    ):
        if m.get(k) not in (None, "", []):
            out[k] = m[k]
    return out


def _read_at(db_path: str) -> str:
    """The newest last_seen in the graph. The caller decides what that age means."""
    try:
        con = _connect(db_path)
        row = con.execute("select max(last_seen) from nodes").fetchone()
        con.close()
        return row[0] or ""
    except Exception:
        return ""


@hookimpl
def register_mcp_tools(datasette, mcp):
    @mcp.tool()
    async def get_estate_state(domain: str = "", query: str = "") -> dict:
        """What the estate actually IS, not what it declares.

        Answers from the estate's own graph (catalog/estate.db), written by
        bin/estate-twin-runtime from the cluster-state receipt and from git. Use it before
        building anything: "do we already have this?" is answerable here, and 648 branches
        carrying 94,093 files absent from main are in it.

        domain: 'runtime' | 'code' | '' for everything.
        query:  a substring of a node id, e.g. 'lago', 'stranded', 'commerce'.

        Every domain carries one of MEASURED_OK, MEASURED_FAIL or UNKNOWN, with the age of
        the reading. UNKNOWN is not a failure -- it means the graph has not been read inside
        its window, and nothing in it may be treated as current.
        """
        return build_estate_state(domain or None, query or None)
