"""Datasette plugin: the `get_workload_logs` MCP tool (crew#216 CP3).

The separate drill-down tool CP2's own docstring names: "drilling into logs is a
separate tool, CP3's get_workload_logs" (mcp/plugins/workload_state.py). Same
--plugins-dir mechanism, ADR 0006 one voice -- and a genuinely separate registered
tool, not a verbose flag on get_workload_state (feature scenario 3): this file's
register_mcp_tools defines exactly one @mcp.tool(), named get_workload_logs, in a
module workload_state.py never imports and is never imported by.

WHERE THE LOG PATH COMES FROM. catalog/estate.db's `plist` column already names
each scheduled_job asset's own launchd plist file (a real file every scheduled_job
has -- e.g. ~/Library/LaunchAgents/ai.aiden.watch.plist). That plist's own
StandardOutPath/StandardErrorPath keys are the job's real, already-configured log
file: read here by parsing the plist itself, never invented or guessed by
convention. An asset that is not a scheduled_job (a repo Component, say) has no
such per-asset log source on this laptop substrate, and the tool degrades with an
`error` field rather than guessing a path.

RESIDUAL, stated plainly rather than implied: the estate-mcp container is not
currently mounted with read access to the host paths launchd's StandardOutPath/
StandardErrorPath name -- they differ per job (~/.claude/scripts/logs,
~/Library/Logs, hermes-v2/logs, ...; see catalog/estate.db's plist column).
Deciding which host directories to mount, and how broadly, is an infra change
outside one checkpoint's diff and outside this session's authority to decide alone
(LAW 11) -- especially so given the standing rule that a colima mount from outside
$HOME silently becomes an empty directory rather than failing loud. Until that
mount lands, get_workload_logs against the live container returns the same
degrade-not-raise "no known log source" response for every asset; the tail/bound
logic below is fully proven against real files by the property and incident tests
in this checkpoint, and is exercised for real the moment the mount is added.

CONFIG (LAW 46):
  ESTATE_CATALOG_PATH   same catalog CP1/CP2 read (default /data/catalog-info.yaml)
  ESTATE_DB_PATH         same estate.db CP2 reads (default /data/estate.db)
  ESTATE_LOGS_MAX_TAIL   the server's enforced maximum, regardless of what a caller
                          requests (default 500) -- feature scenario 2

SECRETS (LAW 21). The only file content that ever leaves this module is the tail of
a log file a launchd job already writes as part of its own normal operation, bounded
to at most ESTATE_LOGS_MAX_TAIL lines. No other estate.db column, no plist key other
than the two log-path keys, reaches the response.
"""
from __future__ import annotations

import os
import plistlib
import sqlite3

import yaml

# See mcp/plugins/estate_inventory.py for why this import is guarded: the offline CI
# venv that runs tests/test_cp3_workload_logs.py has no datasette installed.
try:
    from datasette import hookimpl
except ImportError:  # pragma: no cover - exercised only in the datasette-less CI venv
    def hookimpl(fn):
        return fn


def config() -> dict:
    return {
        "catalog_path": os.environ.get("ESTATE_CATALOG_PATH", "/data/catalog-info.yaml"),
        "estate_db_path": os.environ.get("ESTATE_DB_PATH", "/data/estate.db"),
        "max_tail": int(os.environ.get("ESTATE_LOGS_MAX_TAIL", "500")),
    }


def read_catalog_asset_path(path: str, app: str) -> "tuple[str | None, str | None]":
    """The `estate/path` annotation on the entity named `app` -- the same join key
    workload_state.py uses. Duplicated in ~20 lines rather than imported cross-plugin
    (datasette's --plugins-dir loads each file standalone; workload_state's own
    already-merged contract stays untouched by this diff, same reasoning as
    _fit_under_ceiling in workload_state.py).

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
        ann = meta.get("annotations") or {}
        asset_path = ann.get("estate/path")
        if not asset_path:
            return None, f"catalog entity {app!r} carries no estate/path annotation"
        return asset_path, None
    return None, f"no catalog entity named {app!r}"


def resolve_log_path(db_path: str, asset_path: str) -> "tuple[str | None, str | None]":
    """The log file a scheduled_job asset's own plist already names, read from the
    plist itself. Pure file I/O (sqlite3 read-only connection + plistlib), no
    subprocess, no shell."""
    try:
        conn = sqlite3.connect(f"file:{os.path.abspath(db_path)}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "select kind, plist from assets where path = ? limit 1", (asset_path,)
        ).fetchone()
        conn.close()
    except sqlite3.Error as e:
        return None, str(e)
    if row is None:
        return None, f"no assets row for path {asset_path!r}"
    if row["kind"] != "scheduled_job" or not row["plist"]:
        return None, "no known log source for this asset (not a scheduled_job, or no plist recorded)"
    try:
        with open(row["plist"], "rb") as fh:
            plist = plistlib.load(fh)
    except (OSError, ValueError) as e:
        return None, f"plist unreadable: {e}"
    log_path = plist.get("StandardOutPath") or plist.get("StandardErrorPath")
    if not log_path:
        return None, "plist names no StandardOutPath or StandardErrorPath"
    return log_path, None


def tail_lines(path: str, requested_tail: int, max_tail: int) -> "tuple[list, int, str | None]":
    """The last min(requested_tail, max_tail) lines of `path`, and the max actually
    enforced (feature scenario 2: the response states the maximum it enforced).
    Reads at most a bounded number of trailing bytes rather than the whole file, so a
    1,000,000-line request against a huge file never loads it fully into memory.
    Pure I/O, no subprocess."""
    enforced = min(max(int(requested_tail), 0), max_tail)
    if enforced == 0:
        return [], 0, None
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            pos = fh.tell()
            block = 65536
            data = b""
            while pos > 0 and data.count(b"\n") <= enforced:
                step = min(block, pos)
                pos -= step
                fh.seek(pos)
                data = fh.read(step) + data
    except OSError as e:
        return [], enforced, str(e)
    lines = data.decode("utf-8", errors="replace").splitlines()
    return lines[-enforced:], enforced, None


def build_workload_logs(app: str, tail: int = 50, cfg: "dict | None" = None) -> dict:
    cfg = cfg or config()
    asset_path, catalog_error = read_catalog_asset_path(cfg["catalog_path"], app)
    if catalog_error:
        return {"app": app, "found": False, "log_path": None, "lines": [],
                "line_count": 0, "requested_tail": tail, "max_tail": cfg["max_tail"],
                "tail_enforced": 0, "error": catalog_error}
    log_path, resolve_error = resolve_log_path(cfg["estate_db_path"], asset_path)
    if resolve_error:
        return {"app": app, "found": True, "log_path": None, "lines": [],
                "line_count": 0, "requested_tail": tail, "max_tail": cfg["max_tail"],
                "tail_enforced": 0, "error": resolve_error}
    lines, enforced, read_error = tail_lines(log_path, tail, cfg["max_tail"])
    return {"app": app, "found": True, "log_path": log_path, "lines": lines,
            "line_count": len(lines), "requested_tail": tail,
            "max_tail": cfg["max_tail"], "tail_enforced": enforced, "error": read_error}


@hookimpl
def register_mcp_tools(datasette, mcp):
    @mcp.tool()
    async def get_workload_logs(app: str, tail: int = 50) -> dict:
        """The last `tail` raw log lines for `app`, bounded by
        ESTATE_LOGS_MAX_TAIL (default 500) no matter how large `tail` is
        requested -- the response states the maximum it enforced. This is the
        separate drill-down tool get_workload_state's docstring names: raw
        content lives here only, never inlined into the summary. Degrades with
        an `error` field (never raises) when the catalog does not know `app` or
        no log source is known for it."""
        return build_workload_logs(app, tail=tail)
