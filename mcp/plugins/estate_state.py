"""Datasette plugin: the `get_estate_state` MCP tool (crew#648 CP3).

One more file the existing estate MCP server loads from `--plugins-dir`, registered
through datasette-mcp's `register_mcp_tools(datasette, mcp)` -- the same mechanism as
estate_inventory.py; not a second server (ADR 0006).

It returns the estate-state document (platform/estate-state/schema.json) that the
producer workflow (crew#648 CP2) writes into the estate-db artifact, so the file is at
ESTATE_STATE_JSON_PATH next to estate.db, catalog-info.yaml and STATE.md. Founder,
2026-08-29: "at every session start, all agents [get] the state of the estate,
structured format, ingested via mcp".

The one rule that matters (CP3 acceptance): a document older than
ESTATE_STATE_STALE_MINUTES is returned with `stale: true`, and a missing or unreadable
document is `stale: true` with `available: false`. Nothing this tool returns is ever
presented as current unless generated_at is inside the window.

No subprocess, no shell, no network: one open() and a clock.
"""

from __future__ import annotations

import datetime as dt
import json
import os

try:
    from datasette import hookimpl
except ImportError:  # pragma: no cover - datasette-less CI venv

    def hookimpl(fn):
        return fn


REQUIRED_SECTIONS = ("overview", "delivery", "runtime", "docs_apis", "security")


def config() -> dict:
    return {
        "path": os.environ.get("ESTATE_STATE_JSON_PATH", "/data/estate-state.json"),
        "stale_minutes": int(os.environ.get("ESTATE_STATE_STALE_MINUTES", "30")),
    }


def _parse_ts(value: str) -> dt.datetime | None:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError, AttributeError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def build_state(cfg: dict | None = None, now: dt.datetime | None = None) -> dict:
    """The whole answer. Pure given the file and the clock."""
    cfg = cfg or config()
    now = now or dt.datetime.now(dt.timezone.utc)
    envelope = {
        "available": False,
        "stale": True,
        "stale_threshold_minutes": cfg["stale_minutes"],
        "age_minutes": None,
        "error": None,
        "document": None,
    }
    try:
        with open(cfg["path"], "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except FileNotFoundError:
        envelope["error"] = (
            "no estate-state document at the configured path; the producer (crew#648 CP2) has not written one"
        )
        return envelope
    except (OSError, ValueError) as exc:
        envelope["error"] = (
            f"estate-state document unreadable: {exc.__class__.__name__}"
        )
        return envelope

    missing = [
        s for s in REQUIRED_SECTIONS if not isinstance(doc, dict) or s not in doc
    ]
    if missing:
        envelope["error"] = "estate-state document is missing sections: " + ", ".join(
            missing
        )
        return envelope

    generated = _parse_ts(doc.get("generated_at", ""))
    if generated is None:
        envelope["error"] = "estate-state document has no parseable generated_at"
        envelope["document"] = doc
        return envelope

    age = (now - generated).total_seconds() / 60.0
    envelope.update(
        available=True,
        age_minutes=round(age, 1),
        stale=age > cfg["stale_minutes"] or age < 0,
        document=doc,
    )
    return envelope


@hookimpl
def register_mcp_tools(datasette, mcp):
    @mcp.tool()
    async def get_estate_state() -> dict:
        """The state of the estate as one structured document (crew#648): overview
        (freeze, rulings, sessions, board), delivery (open P0s, failed runs), runtime
        (clusters, Flux rows, surfaces), docs_apis, security. A document older than
        ESTATE_STATE_STALE_MINUTES is returned with stale: true; a missing one is
        available: false. Read the envelope before the document."""
        return build_state()
