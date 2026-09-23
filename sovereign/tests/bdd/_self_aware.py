"""Shared fixtures for the self-aware-platform specs (crew#297 binds cp1-cp3).

The steps drive the real plugin modules in mcp/plugins through their pure
builders (build_inventory, build_workload_state, build_workload_logs); the
only thing faked is the estate on disk: a catalog file, a STATE.md snapshot,
an estate.db and a launchd plist, all in tmp_path. Nothing here shells out.
"""
from __future__ import annotations

import datetime as dt
import plistlib
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGINS = REPO_ROOT / "mcp" / "plugins"
if str(PLUGINS) not in sys.path:
    sys.path.insert(0, str(PLUGINS))

NOW = dt.datetime(2026, 8, 26, 12, 0, tzinfo=dt.timezone.utc)
DB_COLS = ["path", "loaded", "pinned", "max_age_days", "interval_s", "running",
           "last_status", "health", "stale", "age_h", "dirty", "collected", "kind", "plist"]


def write_catalog(path: Path, entities: list[dict]) -> None:
    docs = []
    for e in entities:
        ann = [f"    github.com/project-slug: {e['repo']}"]
        if e.get("asset_path"):
            ann.append(f"    estate/path: {e['asset_path']}")
        deps = e.get("depends_on") or []
        dep_lines = ["  dependsOn:"] + [f"    - {d}" for d in deps] if deps else []
        docs.append("\n".join([
            "---", "apiVersion: backstage.io/v1alpha1", f"kind: {e.get('kind', 'Component')}",
            "metadata:", f"  name: {e['name']}", "  annotations:", *ann,
            "spec:", f"  owner: {e['owner']}", *dep_lines,
        ]))
    path.write_text("\n".join(docs) + "\n", encoding="utf-8")


def write_state_md(path: Path, generated: dt.datetime, threshold_minutes: int = 90) -> None:
    path.write_text(
        f"# Estate snapshot\n\n**Generated {generated.strftime('%Y-%m-%d %H:%M')} UTC** "
        f"by `scripts/estate-snapshot`; stale after {threshold_minutes} minutes.\n",
        encoding="utf-8",
    )


def write_estate_db(path: Path, rows: list[dict]) -> None:
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    conn.execute(f"create table assets ({', '.join(DB_COLS)})")
    for r in rows:
        conn.execute(
            f"insert into assets ({', '.join(DB_COLS)}) values ({', '.join('?' * len(DB_COLS))})",
            tuple(r.get(c) for c in DB_COLS),
        )
    conn.commit()
    conn.close()


def write_job(tmp: Path, label: str, lines: int) -> tuple[Path, Path]:
    log = tmp / f"{label}.out.log"
    log.write_text("\n".join(f"{label}-line-{i}" for i in range(lines)) + "\n", encoding="utf-8")
    plist = tmp / f"{label}.plist"
    with plist.open("wb") as fh:
        plistlib.dump({"Label": label, "StandardOutPath": str(log)}, fh)
    return plist, log


def job_row(asset_path: str, plist: Path) -> dict:
    return {"path": asset_path, "loaded": 1, "pinned": 0, "max_age_days": 7, "interval_s": 3600,
            "running": 1, "last_status": "ok", "health": "green", "stale": 0, "age_h": 1.5,
            "dirty": 0, "collected": 1, "kind": "scheduled_job", "plist": str(plist)}
