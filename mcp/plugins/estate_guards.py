"""Datasette plugin: the `get_estate_guards` MCP tool.

One more file the existing estate MCP server loads from `--plugins-dir`, registered through
datasette-mcp's `register_mcp_tools(datasette, mcp)` -- the same mechanism as
estate_inventory.py and estate_state.py; not a second server (ADR 0006).

Founder, 2026-09-12: "the final proof is me seeing everything real time on ops dashboard, every
active guard or extension... need to see it working and doing this thing realtime" -- and then
"i need all guards".

So this enumerates EVERY guard this estate has, from the four places they live, and reports each
one's REAL state rather than a list of names:

    ~/.estate/guards/hooks/           the git hooks every repository inherits (core.hooksPath)
    ~/.estate/guards/bin/             the estate gate binaries
    ~/.claude/scripts/*guard*.py      the session and commit guards
    ~/.pi/agent/extensions/           the pi extensions, and which of them intercept a tool call

STATE IS READ, NEVER ASSUMED. A guard that cannot be read is reported `unreadable` with the
reason, and a guard that has never fired in the window is `idle` -- which is not the same as
`working`, and this tool never conflates the two. The decision ledger (~/.estate/guards.jsonl)
is what says a guard FIRED; the file system is what says it EXISTS. Both are needed, and a guard
with no ledger rows is `no evidence of firing`, never green.

No subprocess, no shell, no network: directory listings, one file read, and a clock.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

try:
    from datasette import hookimpl
except ImportError:  # pragma: no cover - datasette-less CI venv

    def hookimpl(fn):
        return fn


# The four places a guard lives. Each entry is (kind, directory, how to recognise one).
# A file named by a path that does not exist is reported, not skipped: an inventory that hides
# its own gaps is a list of wishes.
GUARD_DIRS = (
    ("git-hook", "~/.estate/guards/hooks", None),
    ("estate-bin", "~/.estate/guards/bin", None),
    ("claude-guard", "~/.claude/scripts", "guard"),
    ("pi-extension", "~/.pi/agent/extensions", None),
)

# THE OTHER LEDGER, and it is the bigger one. The git-hook router and the claude session guards
# record every decision they make to this file -- 78,201 rows when this was written, the newest
# seconds old. Each row is one guard, one event, an exit code and whether it REFUSED.
#
# Two ledgers rather than one because they are written by different systems: guards.jsonl is
# written by the pi extensions, hook-outcomes.jsonl by the git hooks and the claude guards. The
# estate already had the second one and I did not know it -- an inventory that reports only its
# own half is the same lie as a green tick with no evidence.
OUTCOMES = "~/.claude/state/hook-outcomes.jsonl"


def config() -> dict:
    return {
        "ledger": os.environ.get(
            "ESTATE_GUARD_LEDGER", str(Path.home() / ".estate" / "guards.jsonl")
        ),
        "window_minutes": int(os.environ.get("ESTATE_GUARD_WINDOW_MINUTES", "1440")),
    }


def _ts(value: str) -> dt.datetime | None:
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError, AttributeError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _executable(p: Path) -> bool:
    return os.access(p, os.X_OK)


def _inventory(directory: str, needle: str | None) -> tuple[list[dict], str | None]:
    """Every guard file in one place. Returns (rows, why_it_could_not_be_read)."""
    d = Path(directory).expanduser()
    try:
        entries = sorted(p for p in d.iterdir() if p.name != "__pycache__")
    except OSError as exc:
        return [], f"{d}: {exc.strerror or exc}"
    rows = []
    for p in entries:
        if needle and needle not in p.name:
            continue
        if p.is_dir():
            # A pi extension is a directory holding its entrypoint.
            entry = p / f"{p.name}.ts"
            rows.append(
                {
                    "name": p.name,
                    "path": str(p),
                    "executable": None,
                    "note": "directory (pi extension)"
                    if entry.exists()
                    else "directory",
                }
            )
            continue
        rows.append(
            {
                "name": p.name,
                "path": str(p),
                "executable": _executable(p),
                "note": "" if _executable(p) else "NOT executable -- it cannot run",
            }
        )
    return rows, None


def _ledger(path: str, since: dt.datetime) -> tuple[dict, str | None, int]:
    """What the decision record says. Returns (per-guard counts, why unreadable, lines parsed)."""
    p = Path(path).expanduser()
    try:
        text = p.read_text(errors="replace")
    except OSError as exc:
        return {}, f"{p}: {exc.strerror or exc}", 0
    counts: dict[str, dict] = {}
    parsed = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except ValueError:
            continue
        at = _ts(e.get("at", ""))
        if at is None or at < since:
            continue
        parsed += 1
        g = str(e.get("guard", "?"))
        c = counts.setdefault(
            g, {"fired": 0, "blocked": 0, "last_at": "", "last_command": ""}
        )
        c["fired"] += 1
        if e.get("action") == "block":
            c["blocked"] += 1
        if str(e.get("at", "")) >= c["last_at"]:
            c["last_at"] = str(e.get("at", ""))
            c["last_command"] = str(e.get("command", ""))[:160]
    return counts, None, parsed


def _outcomes(path: str, since: dt.datetime) -> tuple[dict, str | None, int]:
    """Read the git-hook and claude-guard ledger.

    Each row is `{at, event, hook, session, exit, ms, refused}`. `refused: true` is a guard that
    stopped something; `exit` is what it exited with. A row with neither is still evidence the
    guard RAN, which is the distinction this whole tool exists to make.
    """
    p = Path(path).expanduser()
    try:
        text = p.read_text(errors="replace")
    except OSError as exc:
        return {}, f"{p}: {exc.strerror or exc}", 0
    counts: dict[str, dict] = {}
    parsed = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except ValueError:
            continue
        at = _ts(e.get("at", ""))
        if at is None or at < since:
            continue
        parsed += 1
        name = str(e.get("hook", "?"))
        c = counts.setdefault(
            name, {"fired": 0, "blocked": 0, "last_at": "", "last_command": ""}
        )
        c["fired"] += 1
        if e.get("refused"):
            c["blocked"] += 1
        if str(e.get("at", "")) >= c["last_at"]:
            c["last_at"] = str(e.get("at", ""))
            c["last_command"] = f"exit={e.get('exit')} event={e.get('event')}"
    return counts, None, parsed


def build_guards(cfg: dict | None = None, now: dt.datetime | None = None) -> dict:
    """The whole answer. Pure given the file system, the ledger and the clock."""
    cfg = cfg or config()
    now = now or dt.datetime.now(dt.timezone.utc)
    since = now - dt.timedelta(minutes=cfg["window_minutes"])

    places = []
    missing = []
    for kind, directory, needle in GUARD_DIRS:
        rows, why = _inventory(directory, needle)
        if why:
            missing.append(f"{kind}: {why}")
        for r in rows:
            r["kind"] = kind
        places.append(
            {"kind": kind, "directory": os.path.expanduser(directory), "guards": rows}
        )

    counts, ledger_why, parsed = _ledger(cfg["ledger"], since)
    if ledger_why:
        missing.append(f"ledger: {ledger_why}")

    # The second ledger: the git hooks and the claude session guards. Merged into the same map so
    # a reader sees one answer per guard rather than two half-answers in two places.
    outcomes, out_why, out_rows = _outcomes(OUTCOMES, since)
    if out_why:
        missing.append(f"outcomes: {out_why}")
    for name, c in outcomes.items():
        cur = counts.setdefault(
            name, {"fired": 0, "blocked": 0, "last_at": "", "last_command": ""}
        )
        cur["fired"] += c["fired"]
        cur["blocked"] += c["blocked"]
        if c["last_at"] > cur["last_at"]:
            cur["last_at"] = c["last_at"]
            cur["last_command"] = c["last_command"]

    total = sum(len(p["guards"]) for p in places)
    return {
        "available": True,
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "window_minutes": cfg["window_minutes"],
        "total_guards": total,
        "places": places,
        # What the ledger says. A guard absent from this map has produced NO EVIDENCE of firing in
        # the window -- which is not the same as being idle, and not the same as being broken.
        "fired": counts,
        "ledger": {
            "extensions": {"path": cfg["ledger"], "rows_in_window": parsed},
            "hooks_and_session": {
                "path": os.path.expanduser(OUTCOMES),
                "rows_in_window": out_rows,
            },
        },
        # Anything that could not be read. An inventory that hides its own gaps is a list of wishes.
        "unreadable": missing,
        "note": (
            "A guard appears here because it EXISTS on disk. Whether it FIRED is the `fired` map, "
            "read from the decision ledger. A guard with no entry there has no evidence of firing "
            "in the window -- absence of evidence, never a green tick."
        ),
    }


def register_mcp_tools(datasette, mcp):
    """Register `get_estate_guards` (ADR 0006: one interface answers questions about the estate).

    Summarises by default and drills only on request, under a byte ceiling, like estate_state.py.
    """

    def _ceiling(doc: dict, limit: int = 20000) -> str:
        text = json.dumps(doc, indent=2)
        if len(text) <= limit:
            return text
        doc = dict(doc)
        doc["places"] = [
            {
                **p,
                "guards": p["guards"][:12],
                "truncated": max(0, len(p["guards"]) - 12),
            }
            for p in doc["places"]
        ]
        doc["truncated"] = True
        return json.dumps(doc, indent=2)

    async def get_estate_guards(drill: bool = False) -> str:
        """Every guard this estate has, from the four places they live, with the state of each.

        Lists the git hooks, the estate binaries, the session guards and the pi extensions, and
        says for each whether it exists, whether it is executable, and whether the decision ledger
        records it having FIRED in the window. A guard with no ledger entry has no evidence of
        firing -- absence of evidence, never a green tick. Set drill=true for every guard row;
        the default summarises.
        """
        doc = build_guards()
        if drill:
            return json.dumps(doc, indent=2)[:200000]
        return _ceiling(doc)

    mcp.add_tool(get_estate_guards, name="get_estate_guards")
