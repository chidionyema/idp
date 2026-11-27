"""How did each recent session end? Read from its own transcript, no model (idp#8624).

The fleet calls every session `stopped`, so a session that died is indistinguishable from one that
finished. Session 21ea7eac (2026-11-26) ended on three consecutive `API Error: Connection refused`
messages; the founder typed "go on" twice into it, and the next session started blind. This module
reads the tail of each transcript and names how it ended:

    ENDED      the last assistant message is a real reply
    API-ERROR  the last assistant message is an API or lane error; `errors` counts the run of them
    MID-TURN   the transcript stops on a tool call or on input nobody answered (killed, crashed)

Claude Code (`~/.estate/harness/cc/projects`, `~/.claude/projects`) and pi (`~/.pi/agent/sessions`)
are read; opencode keeps its sessions in its own store and is not read yet (named, not hidden).
A malformed line costs that line and is counted; an unreadable file is UNREADABLE, never ENDED.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

TAIL_BYTES = 1 << 20
LIVE_S = 600  # written this recently: a live session (this one included), not an ending
WINDOW_S = 24 * 3600
MAX_FILES = 60


def _stores() -> list[tuple[str, Path]]:
    home = Path.home()
    cc = [home / ".estate/harness/cc/projects", home / ".claude/projects"]
    if os.environ.get("CLAUDE_CONFIG_DIR"):
        cc.insert(0, Path(os.environ["CLAUDE_CONFIG_DIR"]) / "projects")
    out, seen = [], set()
    for p in cc:
        if p.is_dir() and p.resolve() not in seen:
            seen.add(p.resolve())
            out.append(("claude-code", p))
    pi = home / ".pi/agent/sessions"
    if pi.is_dir():
        out.append(("pi", pi))
    return out


def _tail_lines(path: Path) -> list[str]:
    with open(path, "rb") as fh:
        fh.seek(0, os.SEEK_END)
        size = fh.tell()
        fh.seek(max(0, size - TAIL_BYTES))
        data = fh.read()
    lines = data.decode("utf-8", "replace").splitlines()
    return (
        lines[1:] if size > TAIL_BYTES else lines
    )  # the first line of a cut tail is partial


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(str(b.get("text", "")) for b in content if isinstance(b, dict))
    return ""


def _event(entry: dict) -> tuple[str, str, str] | None:
    """(kind, timestamp, detail) for a conversational entry, kind in ok/error/tool/user."""
    msg = entry.get("message")
    if not isinstance(msg, dict):
        return None
    ts = str(entry.get("timestamp") or msg.get("timestamp") or "")
    role = msg.get("role") or entry.get("type")
    content = msg.get("content")
    blocks = content if isinstance(content, list) else []
    if role == "assistant":
        if (
            entry.get("isApiErrorMessage")
            or msg.get("model") == "<synthetic>"
            or msg.get("stopReason") == "error"
        ):
            return "error", ts, str(msg.get("errorMessage") or _text(content))
        tools = [
            b.get("name", "")
            for b in blocks
            if isinstance(b, dict) and b.get("type") in ("tool_use", "toolCall")
        ]
        if tools or msg.get("stopReason") == "toolUse":
            return "tool", ts, tools[-1] if tools else ""
        return "ok", ts, ""
    if role in ("user", "toolResult"):
        return "user", ts, ""
    return None


def classify(path: Path) -> dict:
    """{"verdict", "at", "errors", "error", "last_action", "malformed"} for one transcript."""
    try:
        lines = _tail_lines(path)
    except OSError as exc:
        return {
            "verdict": "UNREADABLE",
            "at": "",
            "errors": 0,
            "error": type(exc).__name__,
            "last_action": "",
            "malformed": 0,
        }
    events, malformed = [], 0
    for line in lines:
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            malformed += 1
            continue
        if isinstance(entry, dict) and (ev := _event(entry)):
            events.append(ev)
    out = {
        "verdict": "UNREADABLE",
        "at": "",
        "errors": 0,
        "error": "",
        "last_action": "",
        "malformed": malformed,
    }
    if not events:
        return out
    tools = [d for k, _, d in events if k == "tool" and d]
    out["last_action"] = tools[-1] if tools else ""
    kind, ts, detail = events[-1]
    out["at"] = ts
    if kind == "ok":
        out["verdict"] = "ENDED"
        return out
    if kind in ("tool", "user"):
        out["verdict"] = "MID-TURN"
        return out
    out["verdict"], out["error"] = "API-ERROR", " ".join(detail.split())[:160]
    for k, _, _ in reversed(
        events
    ):  # the run of errors, across the "go on"s typed into it
        if k == "error":
            out["errors"] += 1
        elif k != "user":
            break
    return out


def unclean(now: float | None = None) -> list[dict]:
    """Sessions of the last WINDOW_S that did not end cleanly, newest first."""
    now = time.time() if now is None else now
    found = []
    for runtime, root in _stores():
        try:
            files = list(root.glob("*/*.jsonl"))
        except OSError:
            continue
        for f in files:
            try:
                age = now - f.stat().st_mtime
            except OSError:
                continue
            if LIVE_S <= age <= WINDOW_S:
                found.append((f.stat().st_mtime, runtime, f))
    rows = []
    for mtime, runtime, f in sorted(found, reverse=True)[:MAX_FILES]:
        got = classify(f)
        if got["verdict"] != "ENDED":
            rows.append(
                {
                    "runtime": runtime,
                    "session": f.stem.split("_")[-1][:8],
                    "path": str(f),
                    "mtime": mtime,
                    **got,
                }
            )
    return rows


def _cause(row: dict) -> tuple[str, str, str]:
    # one cause, whatever clock time or count it names ("resets 6:30am" vs "resets 11:30am")
    return row["runtime"], row["verdict"], re.sub(r"\d+", "#", row["error"])[:80]


def render(rows: list[dict], limit: int = 6) -> str:
    """One line per cause, newest first, so twenty sessions killed by one limit read as one fact."""
    if not rows:
        return ""
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault(_cause(r), []).append(r)
    out = [
        f"Sessions that did not end cleanly (last {WINDOW_S // 3600} h, newest first; "
        f"{len(rows)} sessions, {len(groups)} causes):"
    ]
    for members in list(groups.values())[:limit]:
        r = members[0]
        verdict = (
            f"API-ERROR x{r['errors']}" if r["verdict"] == "API-ERROR" else r["verdict"]
        )
        what = f": {r['error']}" if r["error"] else ""
        last = f"; last action {r['last_action']}" if r["last_action"] else ""
        many = f"{len(members)} sessions, newest " if len(members) > 1 else ""
        others = " ".join(m["session"] for m in members[1:6])
        also = f" (also {others}{' ...' if len(members) > 6 else ''})" if others else ""
        out.append(
            f"- {r['runtime']} {many}{r['session']} {r['at'][:19]}Z {verdict}{what}{last}"
            f" -- {r['path']}{also}"
        )
    if len(groups) > limit:
        out.append(f"- ... and {len(groups) - limit} more causes")
    return "\n".join(out)
