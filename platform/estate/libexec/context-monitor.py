"""context-monitor: detect session-context loss in OpenCode's local store, with proof.

The founder keeps losing work between sessions (2026-11-23: "now we keep losing
work, previous sessions were working on Gortex and other things, context"). The
losses were invisible because nothing watched the store. This door holds three
invariants, each falsifiable:

I1 PERSISTENCE: a session updated inside the window must have persisted messages
   (session_message rows). A session row with zero messages is context that lives
   nowhere but the (already gone) process. Grace: a session updated seconds ago
   may simply not have flushed yet; staleness beyond PERSISTENCE_GRACE_S is the
   defect, not the flush.

I2 FRESHNESS: the newest persisted message must be no older than FRESHNESS_SLACK_S
   behind the newest session update. A store whose last write falls hours behind
   sessions that kept running is a silent context bleed -- that is exactly the
   2026-11-17..23 condition this door was written after.

I3 WORK MAP: every successful write/edit each session made is inventoried from the
   producer's own recorded tool input, and compared against disk:
   PRESENT-IDENTICAL   last successful op was `write` and sha256(disk) == sha256(recorded content)
   PRESENT-DIFFERS      last successful op was `write` and the hashes differ (later change or loss)
   PRESENT-UNVERIFIED   file exists but the last op was `edit` (identity not reconstructable here)
   MISSING-RECOVERABLE  file gone, but a full `write` content survives in the record -> recoverable byte-for-byte
   MISSING-PARTIAL      file gone, only `edit` deltas survive -> name the holes, never guess a reconstruction
   (AGENTS.md 3a/9.P11: the producer's oracle is the judge; "reconstructed" and
   "verified" are different facts and the report says which.)

Read-only against the real database. Exit 0 with counts when the invariants hold;
exit 1 naming the broken invariant when they do not -- a monitor that cannot fail
is not a monitor (AGENTS.md 9.P1).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

DEFAULT_DB = "~/.local/share/opencode/opencode.db"
DEFAULT_REPORT = "~/.estate/state/context-monitor/latest.json"
PERSISTENCE_GRACE_S = 900  # a session younger than this may not have flushed yet
FRESHNESS_SLACK_S = 900  # last persisted message may lag last session update by this
WORK_TOOLS = ("write", "edit")

# The storage contract this door watches. Kept as SQL so the tests build the
# exact same fixture store the real harness writes into (one contract, no drift,
# AGENTS.md 9.P7 / R7).
SCHEMA_SQL = """
CREATE TABLE session_v2 (
  id text PRIMARY KEY,
  title text,
  directory text NOT NULL,
  time_created integer NOT NULL,
  time_updated integer NOT NULL
);
CREATE TABLE session_message (
  id text PRIMARY KEY,
  session_id text NOT NULL,
  type text NOT NULL,
  seq integer NOT NULL,
  time_created integer NOT NULL,
  time_updated integer NOT NULL,
  data text NOT NULL
);
CREATE INDEX session_message_session_time_created_id_idx
  ON session_message (session_id, time_created, id);
"""


def connect(db_path: str) -> sqlite3.Connection:
    path = os.path.expanduser(db_path)
    uri = f"file:{path}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    return con


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: str) -> str | None:
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return None


def persistence_state(
    con: sqlite3.Connection, window_s: int, now: float | None = None
) -> dict:
    """I1 + I2. Returns counts, the zero-message sessions that violate I1 (past
    grace), and whether persisted messages have fallen behind session updates."""
    now = time.time() if now is None else now
    since_ms = int((now - window_s) * 1000)
    rows = con.execute(
        "SELECT id, title, time_created, time_updated FROM session_v2 "
        "WHERE time_updated > ? ORDER BY time_updated DESC",
        (since_ms,),
    ).fetchall()
    counts = con.execute(
        "SELECT session_id, COUNT(*) c FROM session_message GROUP BY session_id"
    ).fetchall()
    msg_counts = {r[0]: r[1] for r in counts}
    last_msg_row = con.execute(
        "SELECT MAX(time_created) m FROM session_message"
    ).fetchone()
    last_msg_ms = last_msg_row[0] or 0

    sessions, zero_message = [], []
    last_session_ms = 0
    for r in rows:
        sid, title, updated = r[0], r[1] or "", r[3]
        c = msg_counts.get(sid, 0)
        sessions.append(
            {"id": sid, "title": title, "time_updated": updated, "messages": c}
        )
        last_session_ms = max(last_session_ms, updated)
        if c == 0:
            age_s = now - updated / 1000
            if age_s > PERSISTENCE_GRACE_S:
                zero_message.append(
                    {
                        "id": sid,
                        "title": title,
                        "updated_age_s": int(age_s),
                        "invariant": "I1_PERSISTENCE",
                    }
                )

    lag_s = (last_session_ms - last_msg_ms) / 1000
    stalled = bool(last_session_ms) and lag_s > FRESHNESS_SLACK_S
    return {
        "window_s": window_s,
        "sessions_in_window": len(sessions),
        "sessions_with_messages": sum(1 for s in sessions if s["messages"]),
        "zero_message_sessions": zero_message,
        "last_message_lag_s": int(lag_s) if last_session_ms else None,
        "persistence_stalled": {"invariant": "I2_FRESHNESS"} if stalled else None,
    }


def _tool_ops(con: sqlite3.Connection, since_ms: int) -> list[dict]:
    """Every successful write/edit op in the record, in order, with the
    producer's own input (path/content for write; path/old/new for edit)."""
    rows = con.execute(
        "SELECT m.session_id, m.seq, m.time_created, m.data FROM session_message m "
        "WHERE m.time_created > ? AND m.data LIKE '%\"tool\"%' ORDER BY m.time_created, m.seq",
        (since_ms,),
    ).fetchall()
    ops = []
    for r in rows:
        r_session, r_time, r_data = r[0], r[2], r[3]
        try:
            data = json.loads(r_data)
        except json.JSONDecodeError:
            continue  # a malformed record costs that record, not the corpus (3a)
        content = data.get("content")
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict) or item.get("type") != "tool":
                continue
            if item.get("name") not in WORK_TOOLS:
                continue
            state = item.get("state") or {}
            if state.get("status") != "completed":
                continue
            inp = state.get("input") or {}
            path = inp.get("path") or inp.get("file")
            if not path:
                continue
            ops.append(
                {
                    "session_id": r_session,
                    "tool": item["name"],
                    "path": path,
                    "content": inp.get("content"),
                    "old": inp.get("oldString"),
                    "new": inp.get("newString"),
                    "time_created": r_time,
                }
            )
    return ops


def work_map(
    con: sqlite3.Connection, since_days: int, session_dirs: dict[str, str] | None = None
) -> dict:
    """I3. Per (session, path): the ordered op chain, the last successful write
    content if any, and a disk verdict. MISSING never guesses content the record
    does not hold."""
    now = time.time()
    since_ms = int((now - since_days * 86400) * 1000)
    dirs = session_dirs or {}
    chains: dict[tuple[str, str], dict] = {}
    for op in _tool_ops(con, since_ms):
        key = (op["session_id"], op["path"])
        ch = chains.setdefault(
            key,
            {
                "session_id": op["session_id"],
                "path": op["path"],
                "ops": 0,
                "last_write": None,
                "saw_edit": False,
            },
        )
        ch["ops"] += 1
        if op["tool"] == "write" and op["content"] is not None:
            ch["last_write"] = op["content"]
        if op["tool"] == "edit":
            ch["saw_edit"] = True

    files = []
    tally: dict[str, int] = {}
    for (sid, path), ch in sorted(chains.items()):
        if not os.path.isabs(path):
            base = dirs.get(sid)
            path = os.path.join(base, path) if base else path
        disk_sha = sha256_file(path)
        rec_sha = (
            sha256_text(ch["last_write"]) if ch["last_write"] is not None else None
        )
        if disk_sha is not None:
            if rec_sha is not None:
                verdict = (
                    "PRESENT-IDENTICAL" if disk_sha == rec_sha else "PRESENT-DIFFERS"
                )
            else:
                verdict = "PRESENT-UNVERIFIED"  # last op was edit; identity not reconstructable
        elif rec_sha is not None:
            if ch["saw_edit"]:
                # a write survived but edits followed it: content is a base, not the final byte truth
                verdict = "MISSING-PARTIAL"
            else:
                verdict = "MISSING-RECOVERABLE"
        else:
            verdict = "MISSING-PARTIAL"
        entry = {
            "session_id": sid,
            "path": path,
            "ops": ch["ops"],
            "verdict": verdict,
        }
        if rec_sha:
            entry["recorded_write_sha256"] = rec_sha
        if disk_sha:
            entry["disk_sha256"] = disk_sha
        files.append(entry)
        tally[verdict] = tally.get(verdict, 0) + 1
    return {"since_days": since_days, "files": files, "verdicts": tally}


def recover(
    db_path: str,
    since_days: int,
    quarantine: str,
    execute: bool = False,
    now: float | None = None,
) -> dict:
    """Recover MISSING-RECOVERABLE files into quarantine (AGENTS.md 3a).

    Never writes to the original path: quarantine only, publish needs an explicit
    --execute. Never overwrites: a target that already exists is counted, not
    replaced, so a second run copies 0 and overwrites 0. Only byte truth is
    recovered -- a full recorded `write` -- and every file carries its sha256;
    edit-only chains are counted as partial and left alone.
    """
    now = time.time() if now is None else now
    since_ms = int((now - since_days * 86400) * 1000)
    con = connect(db_path)
    try:
        chains: dict[tuple[str, str], str | None] = {}
        saw_edit: dict[tuple[str, str], bool] = {}
        for op in _tool_ops(con, since_ms):
            key = (op["session_id"], op["path"])
            if op["tool"] == "write" and op["content"] is not None:
                chains[key] = op["content"]
            elif op["tool"] == "edit":
                saw_edit[key] = True
                chains.setdefault(key, None)

        root = Path(os.path.expanduser(quarantine))
        counts = {
            "recovered": 0,
            "skipped_existing_target": 0,
            "original_still_present": 0,
            "partial_not_recoverable": 0,
        }
        manifest = []
        for (sid, path), content in sorted(chains.items()):
            if os.path.exists(path):
                counts["original_still_present"] += 1
                continue
            if content is None:
                counts["partial_not_recoverable"] += 1
                continue
            target = root / sid / path.lstrip("/")
            if target.exists():
                counts["skipped_existing_target"] += 1
                continue
            digest = sha256_text(content)
            row = {
                "session_id": sid,
                "original_path": path,
                "quarantine_path": str(target),
                "sha256": digest,
                "verdict": "MISSING-PARTIAL"
                if saw_edit.get((sid, path))
                else "MISSING-RECOVERABLE",
            }
            if execute:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content.encode("utf-8"))
                counts["recovered"] += 1
            manifest.append(row)
        if execute:
            root.mkdir(parents=True, exist_ok=True)
            (root / "manifest.json").write_text(
                json.dumps(
                    {
                        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                        "counts": counts,
                        "files": manifest,
                    },
                    indent=1,
                )
                + "\n"
            )
        return {
            "execute": execute,
            "counts": counts,
            "quarantine": str(root),
            "files": manifest,
        }
    finally:
        con.close()


def run(db_path: str, window_s: int, since_days: int, now: float | None = None) -> dict:
    con = connect(db_path)
    try:
        dirs = {
            r[0]: r[1]
            for r in con.execute("SELECT id, directory FROM session_v2").fetchall()
        }
        report = {
            "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "db": os.path.expanduser(db_path),
            "persistence": persistence_state(con, window_s, now=now),
            "work_map": work_map(con, since_days, session_dirs=dirs),
        }
        report["violations"] = report["persistence"]["zero_message_sessions"] + (
            [report["persistence"]["persistence_stalled"]]
            if report["persistence"]["persistence_stalled"]
            else []
        )
        return report
    finally:
        con.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument(
        "--window-s", type=int, default=7200, help="persistence window in seconds"
    )
    ap.add_argument(
        "--since-days", type=int, default=5, help="work-map horizon in days"
    )
    ap.add_argument("--report", default=DEFAULT_REPORT)
    ap.add_argument(
        "--recover",
        action="store_true",
        help="recover MISSING-RECOVERABLE files into quarantine (dry-run unless --execute)",
    )
    ap.add_argument(
        "--execute",
        action="store_true",
        help="with --recover: actually write the quarantine",
    )
    ap.add_argument(
        "--quarantine", default="~/.estate/state/context-monitor/quarantine"
    )
    args = ap.parse_args(argv)

    if args.recover:
        rec = recover(args.db, args.since_days, args.quarantine, execute=args.execute)
        print(
            f"RECOVERY {'EXECUTED' if args.execute else 'DRY-RUN'} "
            f"recoverable={len(rec['files'])} counts={rec['counts']} quarantine={rec['quarantine']}"
        )
        return 0

    report = run(args.db, args.window_s, args.since_days)
    out = Path(os.path.expanduser(args.report))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1) + "\n")

    p, w = report["persistence"], report["work_map"]
    line = (
        f"sessions_in_window={p['sessions_in_window']} "
        f"zero_message_sessions={len(p['zero_message_sessions'])} "
        f"persistence_stalled={bool(p['persistence_stalled'])} "
        f"files={sum(w['verdicts'].values())} verdicts={w['verdicts']}"
    )
    if report["violations"]:
        print("CONTEXT-LOSS-DETECTED " + line)
        for v in report["violations"]:
            print(f"  violation: {v['invariant']} {json.dumps(v)}")
        return 1
    print("CONTEXT-OK " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
