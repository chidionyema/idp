"""Datasette plugin: the `get_estate_inventory` MCP tool (crew#216 CP1).

Registers one new tool on the EXISTING estate MCP server via datasette-mcp's own
extension point, `register_mcp_tools(datasette, mcp)`
(github.com/datasette/datasette-mcp) -- the mechanism datasette-mcp itself uses for
its three built-in tools. This is not a second server: it is one more Python file the
same Datasette process loads from `--plugins-dir`, which is how ADR 0006's "one voice"
rule and the headline's "no second MCP server" both hold (docs/decisions/
0006-the-platform-answers-for-itself-over-one-mcp.md).

It answers "what is the estate, and what does it run" from what the estate already
computed -- crew/STATE.md (the hourly snapshot, `com.founder.estatesnapshot`) and the
Backstage catalog (catalog/catalog-info.yaml, `bin/catalog-gen`) -- never by re-probing
a running process. features/self-aware-platform/cp1_inventory_tool.feature scenario 2
requires no subprocess, no os.system, no shell=True below; there is exactly one
`import` block and two `open()` calls in this file and nothing else touches the OS.

CONFIG (LAW 46 -- no path, host or port is a literal in the code that decides behaviour;
every one below is an env var with a container-local default, wired in
mcp/agentgateway.yml so the *host* path never appears here):
  ESTATE_CATALOG_PATH             the generated Backstage catalog
                                   (default /data/catalog-info.yaml)
  ESTATE_STATE_MD_PATH            the hourly snapshot
                                   (default /data/STATE.md)
  ESTATE_INVENTORY_BYTE_CEILING   summary payload ceiling in bytes -- ADR 0006 point 2,
                                   "fat tools, summarised by default" (default 8000)
  ESTATE_INVENTORY_STALE_MINUTES  age past which the snapshot is disclosed as stale;
                                   scripts/estate-snapshot runs hourly, so the default
                                   is 1.5x that interval (default 90)

SECRETS (LAW 21). Exactly four fields ever leave this file per entity: kind, name,
owner, repo. All four are read from Backstage annotations that are already public
identifiers (a GitHub owner/repo slug and a Backstage group name). No other
annotation, no environment variable, no byte of either input file outside those four
fields reaches the response -- restricting the field set is the guard, not a filter
that could be bypassed by a differently-shaped entity.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re

import yaml
from datasette import hookimpl

_STATE_MD_TS_RE = re.compile(r"\*\*Generated (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) UTC\*\*")


def config() -> dict:
    return {
        "catalog_path": os.environ.get("ESTATE_CATALOG_PATH", "/data/catalog-info.yaml"),
        "state_md_path": os.environ.get("ESTATE_STATE_MD_PATH", "/data/STATE.md"),
        "byte_ceiling": int(os.environ.get("ESTATE_INVENTORY_BYTE_CEILING", "8000")),
        "stale_minutes": int(os.environ.get("ESTATE_INVENTORY_STALE_MINUTES", "90")),
    }


def read_state_md_snapshot(path: str, now: "dt.datetime | None" = None) -> dict:
    """Parse crew/STATE.md's own '**Generated ... UTC**' header line.

    Pure and offline: one open(), one regex, no subprocess (feature scenario 2).
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            head = fh.read(4096)
    except OSError as e:
        return {"path": path, "generated_at": None, "age_minutes": None, "error": str(e)}
    m = _STATE_MD_TS_RE.search(head)
    if not m:
        return {"path": path, "generated_at": None, "age_minutes": None,
                 "error": "no '**Generated ... UTC**' header found in the first 4096 bytes"}
    generated = dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc)
    age_minutes = (now - generated).total_seconds() / 60.0
    return {"path": path, "generated_at": generated.isoformat(),
             "age_minutes": round(age_minutes, 1), "error": None}


def read_catalog_entities(path: str) -> "tuple[list[dict], str | None]":
    """Every Backstage entity's kind, name, owner and repo. No other field.

    Pure and offline: one open(), yaml.safe_load_all, no subprocess.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as e:
        return [], str(e)
    entities = []
    for doc in yaml.safe_load_all(text):
        if not isinstance(doc, dict):
            continue
        meta = doc.get("metadata") or {}
        spec = doc.get("spec") or {}
        ann = meta.get("annotations") or {}
        repo = ann.get("github.com/project-slug") or ann.get("backstage.io/source-location")
        name = meta.get("name")
        if not isinstance(name, str):
            continue
        entities.append({
            "kind": doc.get("kind"),
            "name": name,
            "owner": spec.get("owner"),
            "repo": repo,
        })
    entities.sort(key=lambda e: (e["kind"] or "", e["name"] or ""))
    return entities, None


def _json_bytes(obj) -> int:
    return len(json.dumps(obj, separators=(",", ":")).encode("utf-8"))


def summarize_entities(entities: list, ceiling: int, render) -> "tuple[list, bool, int]":
    """The largest prefix of `entities` for which render(prefix, ...) fits in `ceiling`
    bytes. `render(kept, truncated, omitted)` builds the whole payload envelope, so the
    search is exact against what a caller actually receives, not an estimate.

    Binary search finds a candidate cut fast; the linear pass afterwards corrects the
    at-most-one-off edge where `truncated`/`omitted` themselves change width at the
    boundary (True/False and digit count are a few bytes, and the search used a
    worst-case placeholder for both while probing). Nothing here drops a field on a
    kept entity -- only whole entities are cut from the tail, and the count cut is
    reported, never silently (cp1_inventory_tool.feature scenario 3, same principle
    applied to the entity list as to the staleness flag).
    """
    lo, hi, best = 0, len(entities), 0
    while lo <= hi:
        mid = (lo + hi) // 2
        if _json_bytes(render(entities[:mid], True, len(entities) - mid)) <= ceiling:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    truncated = best < len(entities)
    omitted = len(entities) - best
    while best > 0 and _json_bytes(render(entities[:best], truncated, omitted)) > ceiling:
        best -= 1
        truncated = best < len(entities)
        omitted = len(entities) - best
    return entities[:best], truncated, omitted


def build_inventory(cfg: "dict | None" = None, now: "dt.datetime | None" = None) -> dict:
    cfg = cfg or config()
    state = read_state_md_snapshot(cfg["state_md_path"], now=now)
    entities, catalog_error = read_catalog_entities(cfg["catalog_path"])
    stale = state["age_minutes"] is not None and state["age_minutes"] > cfg["stale_minutes"]

    def render(kept, truncated, omitted):
        return {
            "snapshot_generated_at": state["generated_at"],
            "snapshot_age_minutes": state["age_minutes"],
            "snapshot_stale": stale,
            "snapshot_stale_threshold_minutes": cfg["stale_minutes"],
            "snapshot_error": state["error"],
            "catalog_error": catalog_error,
            "entity_count_total": len(entities),
            "byte_ceiling": cfg["byte_ceiling"],
            "entities": kept,
            "entities_truncated": truncated,
            "entities_omitted": omitted,
        }

    kept, truncated, omitted = summarize_entities(entities, cfg["byte_ceiling"], render)
    return render(kept, truncated, omitted)


@hookimpl
def register_mcp_tools(datasette, mcp):
    @mcp.tool()
    async def get_estate_inventory() -> dict:
        """List every Backstage catalog entity (kind, name, owner, repo) and the
        crew/STATE.md snapshot timestamp it was read from, in one call. Summarised
        under a byte ceiling (ESTATE_INVENTORY_BYTE_CEILING); a stale snapshot is
        disclosed with its age, never hidden. Reads crew/STATE.md and
        catalog/catalog-info.yaml only -- no shell-out, no live process probe."""
        return build_inventory()
