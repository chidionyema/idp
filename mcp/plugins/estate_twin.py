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

import yaml

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
        # Same env var and same default as estate_inventory.config()'s "catalog_path" --
        # one file, two plugins reading it read-only, never two paths for one input.
        "catalog_path": os.environ.get(
            "ESTATE_CATALOG_PATH", "/data/catalog-info.yaml"
        ),
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


def _iter_catalog_components(path: str) -> "tuple[list[dict], str | None]":
    """Every Backstage Component's name, type, tags and `estate/*` annotations.

    Pure and offline: one open(), yaml.safe_load_all, no subprocess -- same contract as
    estate_inventory.read_catalog_entities, reading the same file this plugin never writes.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as e:
        return [], str(e)
    out: list[dict] = []
    for doc in yaml.safe_load_all(text):
        if not isinstance(doc, dict) or doc.get("kind") != "Component":
            continue
        meta = doc.get("metadata") or {}
        name = meta.get("name")
        if not isinstance(name, str):
            continue
        ann = meta.get("annotations") or {}
        out.append(
            {
                "name": name,
                "title": meta.get("title") or name,
                "type": (doc.get("spec") or {}).get("type"),
                "tags": meta.get("tags") or [],
                "enabled": ann.get("estate/enabled"),
                "flux_kind": ann.get("estate/flux-kind"),
                "flux_name": ann.get("estate/flux-name"),
                "namespace": ann.get("estate/namespace"),
                "file": ann.get("estate/file"),
            }
        )
    out.sort(key=lambda e: e["name"])
    return out, None


def _choice_keyword(name: str) -> "str | None":
    """`cluster-cni-cilium` -> `cilium`: the token after `cluster-<category>-`.

    Only components actually shaped that way (>= 3 hyphen-parts, `cluster` first)
    produce a keyword; everything else is not this rule's business.
    """
    parts = name.split("-")
    if len(parts) < 3 or parts[0] != "cluster":
        return None
    return "-".join(parts[2:])


def build_catalog_drift(rule: "str | None" = None, cfg: "dict | None" = None) -> dict:
    """Where the catalog's declared pick disagrees with what the estate graph measured.

    Two rule classes, both read off conventions already in catalog/catalog-info.yaml --
    no new annotation invented here:

    * `flux`   a Component carrying `estate/flux-kind: HelmRelease` plus `estate/namespace`
               and `estate/flux-name` (115 components use the flux-kind convention; this
               rule only trusts HelmRelease -- Kustomization ids in catalog/estate.db do not
               carry a namespace segment and would false-positive on every row). Expected
               node id is `flux:HelmRelease:<namespace>/<flux-name>`, an exact match against
               catalog/estate.db. Drift: the id is absent, or its status is one of
               NOT_SERVING.
    * `choice` a Component tagged `cluster-choice` with `estate/enabled: 'true'` (e.g.
               cluster-cni-cilium, cluster-cni-hubble -- a pick applied outside Flux, so it
               has no flux-kind annotation to match on). Drift: no node in the runtime
               domain has an id containing the choice's own keyword ("cilium", "hubble")
               with a status outside NOT_SERVING -- nothing observed is actually running
               the thing the catalog says was picked.

    `rule` narrows to one class ('flux' | 'choice'); default runs both. Summarised by
    default under a byte ceiling, same shape as get_estate_state's `_fit`.
    """
    cfg = cfg or config()
    catalog_path = str(cfg["catalog_path"])
    db_path = str(cfg["db_path"])
    ceiling = int(cfg["ceiling"])

    components, catalog_error = _iter_catalog_components(catalog_path)
    if not os.path.exists(db_path):
        # BLIND, named -- an empty drift list would read as "nothing has drifted".
        return {
            "state": "UNKNOWN",
            "why": f"the estate graph is not at {db_path}; bin/estate-twin-runtime has never run",
            "drift": [],
        }

    con = _connect(db_path)
    try:
        drift: list[dict] = []
        checked = 0
        for c in components:
            if rule not in (None, "flux") and rule != "choice":
                pass  # unrecognised rule falls through to "checked nothing", not an error
            is_flux = (
                rule in (None, "flux")
                and c["flux_kind"] == "HelmRelease"
                and c["namespace"]
                and c["flux_name"]
            )
            is_choice = (
                rule in (None, "choice")
                and "cluster-choice" in c["tags"]
                and c["enabled"] == "true"
            )
            if is_flux:
                node_id = f"flux:HelmRelease:{c['namespace']}/{c['flux_name']}"
                rows = list(
                    con.execute("select status from nodes where id = ?", (node_id,))
                )
                total = len(rows)
                active = sum(1 for (s,) in rows if s not in NOT_SERVING)
                expected, statuses = node_id, sorted({s for (s,) in rows})
            elif is_choice:
                keyword = _choice_keyword(c["name"])
                if not keyword:
                    continue
                rows = list(
                    con.execute(
                        "select status from nodes where domain = 'runtime' and id like ?",
                        (f"%{keyword}%",),
                    )
                )
                total = len(rows)
                active = sum(1 for (s,) in rows if s not in NOT_SERVING)
                expected, statuses = (
                    f"id like '%{keyword}%'",
                    sorted({s for (s,) in rows}),
                )
            else:
                continue

            checked += 1
            if active > 0:
                continue
            drift.append(
                {
                    "name": c["name"],
                    "title": c["title"],
                    "rule": "flux" if is_flux else "choice",
                    "expected": expected,
                    "file": c["file"],
                    "nodes_found": total,
                    "reason": (
                        "not observed in the estate graph"
                        if total == 0
                        else f"observed but not serving ({','.join(statuses)})"
                    ),
                }
            )
        drift.sort(key=lambda d: d["name"])
    finally:
        con.close()

    def render(kept):
        return {
            "read_at": _read_at(db_path),
            "catalog_error": catalog_error,
            "components_checked": checked,
            "drift_total": len(drift),
            "drift": kept,
            "truncated": len(kept) < len(drift),
        }

    kept, truncated, _total = _fit(drift, ceiling, render)
    payload = render(kept)
    if truncated:
        payload["note"] = (
            f"{len(drift) - len(kept)} more not shown under the {ceiling}-byte "
            f"ceiling; narrow with rule='flux' or rule='choice'"
        )
    return payload


@hookimpl
def register_mcp_tools(datasette, mcp):
    @mcp.tool()
    async def get_catalog_drift(rule: str = "") -> dict:
        """Where the Backstage catalog's declared pick disagrees with the estate graph's
        measured state -- e.g. cluster-cni-cilium is declared enabled but no node anywhere
        in catalog/estate.db is actually running Cilium (still flannel, per
        k8s:daemonset:kube-system:kube-flannel-ds). Two rule classes: 'flux' (a Component
        with estate/flux-kind: HelmRelease vs. the matching flux:HelmRelease:<ns>/<name>
        node) and 'choice' (a cluster-choice Component with estate/enabled: 'true' vs. any
        runtime node whose id names it). rule='' runs both. Reads
        catalog/catalog-info.yaml and catalog/estate.db only -- no shell-out, no live probe.
        """
        return build_catalog_drift(rule or None)

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
