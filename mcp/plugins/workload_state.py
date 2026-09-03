"""Datasette plugin: the `get_workload_state` MCP tool (crew#216 CP2).

Same mechanism as CP1 (mcp/plugins/estate_inventory.py): one more Python file the
existing Datasette process loads from `--plugins-dir`, registering a tool through
datasette-mcp's own extension point, `register_mcp_tools(datasette, mcp)`
(github.com/datasette/datasette-mcp). Not a second server -- ADR 0006 and the headline
both require one voice.

Founder's pasted design (crew/docs/specs/issue-216.md): "get_workload_state(app)
returns catalog + metrics + desired state in one payload." Failure named: payload
bloat -- raw logs and raw timeseries kill the context. Fix named: summarize by
default; drilling is a separate tool (CP3, `get_workload_logs`).

WHERE EACH PART COMES FROM (crew/docs/specs/issue-216.md, "Design substance"):
  catalog          Backstage catalog/catalog-info.yaml (bin/catalog-gen). One entity's
                    kind, owner, repo, and its spec.dependsOn edges.
  desired vs actual "Flux/k8s is desired vs actual state... on the laptop substrate
                    (Fly destroyed, OKE not live) is launchd job state and colima
                    container state standing in for k8s until a cluster exists."
                    That state is catalog/estate.db (the same inventory catalog-gen
                    reads), joined to the catalog entity by the `estate/path`
                    annotation catalog-gen already writes -- LAW 43: reuse the join
                    key the estate already computed, never re-derive
                    catalog-gen's slug()/collision handling here.
  metrics          "the vitals come from OTel/Prometheus per the fortress stack
                    (crew#180)". crew#180 is not live: grep of docs/specs/
                    fortress-stack.md and observability/ (langfuse.yml,
                    otel-fallback.yaml, clickhouse-low-memory.xml) turns up traces
                    only, zero Prometheus references. collect_metric_samples() below
                    is an explicit, documented stub -- the one numeric reading
                    estate.db already collects per asset (age_h) stands in as a
                    single-sample series, the same posture crew#216's CP8 takes for
                    its k8s adapter ("a stub proving the interface... not a live
                    cluster call"). summarize_metrics() itself is pure and is proven
                    directly against synthetic sample counts up to 10,000 by the
                    property test, independent of the stub.

CONFIG (LAW 46 -- no path or port is a literal in code that decides behaviour):
  ESTATE_CATALOG_PATH             same catalog CP1 reads (default /data/catalog-info.yaml)
  ESTATE_DB_PATH                  catalog/estate.db, already mounted read-only into
                                   this container for execute_sql/list_databases
                                   (default /data/estate.db) -- no new mount needed
  ESTATE_WORKLOAD_BYTE_CEILING    summary payload ceiling in bytes (default 8000)

SECRETS (LAW 21). The catalog entity contributes exactly kind/owner/repo/dependsOn,
the same public-identifier fields CP1 already allows. estate.db contributes only the
DESIRED_FIELDS/ACTUAL_FIELDS allow-list below -- every other column (branch, remote,
plist, coupling, note, ...) never leaves read_asset_state. Metrics are five aggregate
numbers per named series; the samples themselves never leave summarize_metrics.
"""
from __future__ import annotations

import json
import os
import sqlite3

import yaml

# See mcp/plugins/estate_inventory.py for why this import is guarded: the offline CI
# venv that runs tests/test_cp2_workload_state.py has no datasette installed.
try:
    from datasette import hookimpl
except ImportError:  # pragma: no cover - exercised only in the datasette-less CI venv
    def hookimpl(fn):
        return fn


DESIRED_FIELDS = ("loaded", "pinned", "max_age_days", "interval_s")
ACTUAL_FIELDS = ("running", "last_status", "health", "stale", "age_h", "dirty", "collected")


def config() -> dict:
    return {
        "catalog_path": os.environ.get("ESTATE_CATALOG_PATH", "/data/catalog-info.yaml"),
        "estate_db_path": os.environ.get("ESTATE_DB_PATH", "/data/estate.db"),
        "byte_ceiling": int(os.environ.get("ESTATE_WORKLOAD_BYTE_CEILING", "8000")),
    }


def read_catalog_entity(path: str, app: str) -> "tuple[dict | None, str | None]":
    """The one Backstage entity named `app`: kind, owner, repo, dependsOn, and the
    `estate/path` annotation catalog-gen already writes (bin/catalog-gen: `ann = {...,
    "path": r.get("path"), ...}`, emitted as `estate/path` since it has no "/").

    Pure and offline: one open(), yaml.safe_load_all, no subprocess.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as e:
        return None, str(e)
    for doc in yaml.safe_load_all(text):
        if not isinstance(doc, dict):
            continue
        meta = doc.get("metadata") or {}
        if meta.get("name") != app:
            continue
        spec = doc.get("spec") or {}
        ann = meta.get("annotations") or {}
        repo = ann.get("github.com/project-slug") or ann.get("backstage.io/source-location")
        depends_on = spec.get("dependsOn") or []
        if not isinstance(depends_on, list):
            depends_on = []
        return {
            "kind": doc.get("kind"),
            "name": meta.get("name"),
            "owner": spec.get("owner"),
            "repo": repo,
            "depends_on": sorted(str(d) for d in depends_on),
            "asset_path": ann.get("estate/path"),
        }, None
    return None, f"no catalog entity named {app!r}"


def read_asset_state(db_path: str, asset_path: "str | None") -> "tuple[dict, dict, str | None]":
    """Desired vs actual state for one asset, read-only, joined by `estate/path`.
    Degrades to ({}, {}, error) rather than raising -- an app the catalog knows but
    estate.db has no row for (a dependsOn target, say) is a normal answer, not a fault.
    """
    if not asset_path:
        return {}, {}, "catalog entity carries no estate/path annotation"
    try:
        conn = sqlite3.connect(f"file:{os.path.abspath(db_path)}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "select * from assets where path = ? limit 1", (asset_path,)
        ).fetchone()
        conn.close()
    except sqlite3.Error as e:
        return {}, {}, str(e)
    if row is None:
        return {}, {}, f"no assets row for path {asset_path!r}"
    d = dict(row)
    desired = {k: d[k] for k in DESIRED_FIELDS if k in d and d[k] is not None}
    actual = {k: d[k] for k in ACTUAL_FIELDS if k in d and d[k] is not None}
    return desired, actual, None


def summarize_metrics(samples: "dict[str, list]") -> dict:
    """min/max/mean/last/count per named metric. Pure, no I/O. The raw `samples` list
    is never part of the return value -- cp2 feature scenario 2, "numeric metrics are
    pre-aggregated" -- and this holds regardless of how many samples came in (scenario
    3: property-tested up to 10,000 per metric)."""
    out = {}
    for name, vals in samples.items():
        vals = [float(v) for v in vals]
        if not vals:
            continue
        out[name] = {
            "min": min(vals), "max": max(vals), "mean": sum(vals) / len(vals),
            "last": vals[-1], "count": len(vals),
        }
    return out


def collect_metric_samples(actual: dict) -> "dict[str, list]":
    """STUB pending crew#180's live OTel/Prometheus pipeline (see module docstring).
    The one numeric reading estate.db already collects for this asset (age_h, hours
    since last touch) stands in as a single-sample series. Real per-second timeseries
    arrive when crew#180 ships; nothing here claims they exist today."""
    samples: "dict[str, list]" = {}
    if actual.get("age_h") is not None:
        samples["age_h"] = [float(actual["age_h"])]
    return samples


def _json_bytes(obj) -> int:
    return len(json.dumps(obj, separators=(",", ":")).encode("utf-8"))


def _fit_under_ceiling(items: list, ceiling: int, render) -> "tuple[list, bool, int]":
    """Same algorithm as estate_inventory.summarize_entities (crew#216 CP1): binary
    search for the largest kept prefix, then a linear correction pass for the
    render()-envelope's own width at the boundary. Duplicated here in ~15 lines rather
    than imported cross-plugin, so CP1's already-merged, already-tested contract is
    never touched by this diff (smallest diff per file, not smallest diff overall)."""
    lo, hi, best = 0, len(items), 0
    while lo <= hi:
        mid = (lo + hi) // 2
        if _json_bytes(render(items[:mid], True, len(items) - mid)) <= ceiling:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    truncated = best < len(items)
    omitted = len(items) - best
    while best > 0 and _json_bytes(render(items[:best], truncated, omitted)) > ceiling:
        best -= 1
        truncated = best < len(items)
        omitted = len(items) - best
    return items[:best], truncated, omitted


def build_workload_state(app: str, cfg: "dict | None" = None,
                          metric_samples: "dict[str, list] | None" = None) -> dict:
    """Assemble one payload: catalog entry, desired vs actual state, summarized
    metrics for `app`. `metric_samples` lets the property test drive up to 10,000
    synthetic samples per metric with no live collector; production passes None and
    collect_metric_samples() supplies the documented-stub real reading."""
    cfg = cfg or config()
    entity, catalog_error = read_catalog_entity(cfg["catalog_path"], app)
    if entity is None:
        desired, actual, state_error, depends_on = {}, {}, None, []
    else:
        desired, actual, state_error = read_asset_state(cfg["estate_db_path"], entity.get("asset_path"))
        depends_on = entity.get("depends_on", [])
    samples = metric_samples if metric_samples is not None else collect_metric_samples(actual)
    metrics = summarize_metrics(samples)

    def render(kept_deps, truncated, omitted):
        return {
            "app": app,
            "found": entity is not None,
            "catalog_error": catalog_error,
            "kind": entity.get("kind") if entity else None,
            "owner": entity.get("owner") if entity else None,
            "repo": entity.get("repo") if entity else None,
            "dependencies": kept_deps,
            "dependencies_truncated": truncated,
            "dependencies_omitted": omitted,
            "dependency_count_total": len(depends_on),
            "desired_state": desired,
            "actual_state": actual,
            "state_error": state_error,
            "metrics": metrics,
            "metrics_source": ("estate.db single-sample stand-in pending crew#180 -- "
                                "no live Prometheus/OTel metrics pipeline yet"),
            "byte_ceiling": cfg["byte_ceiling"],
        }

    kept_deps, truncated, omitted = _fit_under_ceiling(depends_on, cfg["byte_ceiling"], render)
    return render(kept_deps, truncated, omitted)


@hookimpl
def register_mcp_tools(datasette, mcp):
    @mcp.tool()
    async def get_workload_state(app: str) -> dict:
        """One call answers "why is X down": the Backstage catalog entry (owner,
        repo, dependencies) for `app`, its desired vs actual state (launchd/colima
        fields already collected in catalog/estate.db, standing in for k8s until a
        cluster exists), and summarized metrics -- never raw logs or a raw
        timeseries. Summarised under a byte ceiling (ESTATE_WORKLOAD_BYTE_CEILING).
        Drilling into logs is a separate tool, CP3's get_workload_logs."""
        return build_workload_state(app)
