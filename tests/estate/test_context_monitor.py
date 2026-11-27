"""context-monitor falsifiers: each invariant must fail on known-bad input.

The monitor exists because context went missing between sessions with nothing
saying so (founder, 2026-11-23). A monitor that cannot fail is not a monitor
(AGENTS.md 9.P1), so every test here feeds the real script a fixture store that
contains the exact condition the invariant guards against, and asserts the
verdict -- including the known-good cases that must NOT raise.
"""

from __future__ import annotations

import hashlib
import importlib.util
import itertools
import json
import os
import sqlite3
import time
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2] / "platform/estate/libexec/context-monitor.py"
)
spec = importlib.util.spec_from_file_location("context_monitor", SCRIPT)
cm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm)

NOW = time.time()
_SEQ = itertools.count()  # the real store enforces UNIQUE(session_id, seq)


def fixture_db(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.executescript(cm.SCHEMA_SQL)
    return con


def add_session(con, sid, title, updated_age_s, messages=0, directory="/tmp"):
    con.execute(
        "INSERT INTO session_v2 (id, title, directory, time_created, time_updated) VALUES (?,?,?,?,?)",
        (
            sid,
            title,
            directory,
            int((NOW - updated_age_s - 60) * 1000),
            int((NOW - updated_age_s) * 1000),
        ),
    )
    for i in range(messages):
        add_message(
            con, f"{sid}_m{i}", sid, updated_age_s - 1, {"kind": "text", "text": "x"}
        )


def add_message(con, mid, sid, age_s, payload, seq=None):
    con.execute(
        "INSERT INTO session_message (id, session_id, type, seq, time_created, time_updated, data) "
        "VALUES (?,?,?,?,?,?,?)",
        (
            mid,
            sid,
            payload.get("type", "assistant"),
            seq if seq is not None else next(_SEQ),
            int((NOW - age_s) * 1000),
            int((NOW - age_s) * 1000),
            # compact separators: the real harness stores compact JSON
            json.dumps(payload, separators=(",", ":")),
        ),
    )


def tool_message(mid, sid, age_s, name, path, status="completed", **extra):
    part = {
        "type": "tool",
        "name": name,
        "state": {"status": status, "input": {"path": path, **extra}},
    }
    return {
        "type": "assistant",
        "time": {"created": int((NOW - age_s) * 1000)},
        "content": [part],
    }


def test_zero_message_session_past_grace_is_a_violation(tmp_path):
    """I1 known-bad: session updated an hour ago, no persisted messages."""
    con = fixture_db(tmp_path / "d.db")
    add_session(con, "ses_bad", "Gortex work", updated_age_s=3600, messages=0)
    con.commit()
    state = cm.persistence_state(con, window_s=7200, now=NOW)
    assert [v["id"] for v in state["zero_message_sessions"]] == ["ses_bad"]
    assert state["zero_message_sessions"][0]["invariant"] == "I1_PERSISTENCE"


def test_fresh_session_without_messages_is_not_yet_a_violation(tmp_path):
    """I1 grace: a session updated a minute ago may not have flushed yet."""
    con = fixture_db(tmp_path / "d.db")
    add_session(con, "ses_new", "just opened", updated_age_s=60, messages=0)
    con.commit()
    state = cm.persistence_state(con, window_s=7200, now=NOW)
    assert state["zero_message_sessions"] == []


def test_healthy_session_is_not_flagged(tmp_path):
    """I1 known-good: session with persisted messages passes clean."""
    con = fixture_db(tmp_path / "d.db")
    add_session(con, "ses_ok", "fine", updated_age_s=600, messages=3)
    con.commit()
    state = cm.persistence_state(con, window_s=7200, now=NOW)
    assert state["zero_message_sessions"] == []
    assert state["sessions_with_messages"] == 1


def test_messages_lagging_behind_sessions_is_a_stall(tmp_path):
    """I2 known-bad: sessions kept updating 1m ago, last message is 3h old."""
    con = fixture_db(tmp_path / "d.db")
    add_session(con, "ses_live", "live", updated_age_s=60, messages=0)
    add_session(con, "ses_old", "old", updated_age_s=3 * 3600, messages=2)
    con.commit()
    state = cm.persistence_state(con, window_s=6 * 3600, now=NOW)
    assert state["persistence_stalled"]["invariant"] == "I2_FRESHNESS"
    assert state["last_message_lag_s"] > cm.FRESHNESS_SLACK_S


def test_fresh_store_is_not_stalled(tmp_path):
    """I2 known-good: message written after the last session update."""
    con = fixture_db(tmp_path / "d.db")
    add_session(con, "ses_ok", "fine", updated_age_s=600, messages=1)
    add_message(con, "late", "ses_ok", 300, {"kind": "text", "text": "x"})
    con.commit()
    state = cm.persistence_state(con, window_s=7200, now=NOW)
    assert state["persistence_stalled"] is None


def test_work_map_verdicts_and_recovery(tmp_path):
    """I3: the four disk truths, including byte-for-byte recovery from the
    producer's own recorded write (3a: the producer's oracle is the judge)."""
    con = fixture_db(tmp_path / "d.db")
    add_session(con, "ses_w", "writer", updated_age_s=600, directory=str(tmp_path))

    identical = tmp_path / "identical.txt"
    identical.write_text("final content\n")
    gone = str(tmp_path / "gone.txt")

    con.execute("DELETE FROM session_message")
    add_message(
        con,
        "m1",
        "ses_w",
        500,
        tool_message(
            "t1", "ses_w", 500, "write", str(identical), content="final content\n"
        ),
    )
    add_message(
        con,
        "m2",
        "ses_w",
        400,
        tool_message("t2", "ses_w", 400, "write", gone, content="recoverable body\n"),
    )
    add_message(
        con,
        "m3",
        "ses_w",
        300,
        tool_message("t3", "ses_w", 300, "edit", gone, oldString="a", newString="b"),
    )
    add_message(
        con,
        "m4",
        "ses_w",
        200,
        tool_message(
            "t4",
            "ses_w",
            200,
            "write",
            str(tmp_path / "differ.txt"),
            content="original\n",
        ),
    )
    add_message(
        con,
        "m5",
        "ses_w",
        100,
        tool_message(
            "t5",
            "ses_w",
            100,
            "edit",
            str(tmp_path / "unverified.txt"),
            oldString="a",
            newString="b",
        ),
    )
    (tmp_path / "differ.txt").write_text("changed later\n")
    (tmp_path / "unverified.txt").write_text("whatever\n")
    con.commit()

    wm = cm.work_map(con, since_days=1)
    v = {f["path"]: f["verdict"] for f in wm["files"]}
    assert v[str(identical)] == "PRESENT-IDENTICAL"
    assert v[str(tmp_path / "differ.txt")] == "PRESENT-DIFFERS"
    assert v[str(tmp_path / "unverified.txt")] == "PRESENT-UNVERIFIED"
    assert (
        v[gone] == "MISSING-PARTIAL"
    )  # edits followed the surviving write: holes named, not guessed

    entry = next(f for f in wm["files"] if f["path"] == gone)
    assert (
        entry["recorded_write_sha256"]
        == hashlib.sha256(b"recoverable body\n").hexdigest()
    )


def test_missing_file_with_only_a_write_is_recoverable(tmp_path):
    """I3 recovery: gone file, full write content in the record, no edits after."""
    con = fixture_db(tmp_path / "d.db")
    add_session(con, "ses_r", "recovery", updated_age_s=600, directory=str(tmp_path))
    gone = str(tmp_path / "vanished.txt")
    add_message(
        con,
        "m1",
        "ses_r",
        500,
        tool_message("t1", "ses_r", 500, "write", gone, content="byte truth\n"),
    )
    con.commit()
    wm = cm.work_map(con, since_days=1)
    entry = next(f for f in wm["files"] if f["path"] == gone)
    assert entry["verdict"] == "MISSING-RECOVERABLE"
    assert entry["recorded_write_sha256"] == hashlib.sha256(b"byte truth\n").hexdigest()
    assert "disk_sha256" not in entry


def test_errored_tool_calls_are_not_work(tmp_path):
    """A refused write never reached the disk, so it must not enter the map."""
    con = fixture_db(tmp_path / "d.db")
    add_session(con, "ses_e", "errors", updated_age_s=600, directory=str(tmp_path))
    add_message(
        con,
        "m1",
        "ses_e",
        500,
        tool_message(
            "t1",
            "ses_e",
            500,
            "write",
            str(tmp_path / "nope.txt"),
            status="error",
            content="x",
        ),
    )
    con.commit()
    wm = cm.work_map(con, since_days=1)
    assert wm["files"] == []


def test_main_exit_codes(tmp_path, capsys):
    """The monitor's own gate: exit 1 naming the invariant on known-bad, 0 on
    known-good. This is the falsifier of last resort (AGENTS.md 9.P1)."""
    bad = tmp_path / "bad.db"
    con = fixture_db(bad)
    add_session(con, "ses_bad", "lost context", updated_age_s=3600, messages=0)
    con.commit()
    con.close()
    rc_bad = cm.main(
        ["--db", str(bad), "--report", str(tmp_path / "bad.json"), "--window-s", "7200"]
    )
    assert rc_bad == 1
    out = capsys.readouterr().out
    assert "CONTEXT-LOSS-DETECTED" in out and "I1_PERSISTENCE" in out

    good = tmp_path / "good.db"
    con = fixture_db(good)
    add_session(con, "ses_good", "healthy", updated_age_s=600, messages=2)
    con.commit()
    con.close()
    rc_good = cm.main(
        [
            "--db",
            str(good),
            "--report",
            str(tmp_path / "good.json"),
            "--window-s",
            "7200",
        ]
    )
    assert rc_good == 0
    assert "CONTEXT-OK" in capsys.readouterr().out


def _recovery_fixture(tmp_path):
    con = fixture_db(tmp_path / "d.db")
    add_session(con, "ses_r", "recovery", updated_age_s=600, directory=str(tmp_path))
    gone = str(tmp_path / "gone.txt")  # missing on disk, full write in the record
    edit_only = str(tmp_path / "edit-only.txt")  # missing, deltas only: never guessed
    present = tmp_path / "present.txt"  # still on disk: must not be touched
    present.write_text("live body\n")
    add_message(
        con,
        "m1",
        "ses_r",
        500,
        tool_message("t1", "ses_r", 500, "write", gone, content="recovered body\n"),
    )
    add_message(
        con,
        "m2",
        "ses_r",
        400,
        tool_message(
            "t2", "ses_r", 400, "edit", edit_only, oldString="a", newString="b"
        ),
    )
    add_message(
        con,
        "m3",
        "ses_r",
        300,
        tool_message("t3", "ses_r", 300, "write", str(present), content="live body\n"),
    )
    con.commit()
    con.close()
    return gone, edit_only, str(present)


def test_recovery_is_quarantine_only_and_idempotent(tmp_path):
    """3a: quarantine first, never overwrite, second run copies 0."""
    gone, edit_only, present = _recovery_fixture(tmp_path)
    q = tmp_path / "quarantine"

    dry = cm.recover(str(tmp_path / "d.db"), 1, str(q), execute=False)
    assert dry["execute"] is False
    assert dry["counts"]["recovered"] == 0
    assert not q.exists()  # a dry run writes nothing

    first = cm.recover(str(tmp_path / "d.db"), 1, str(q), execute=True)
    assert first["counts"] == {
        "recovered": 1,
        "skipped_existing_target": 0,
        "original_still_present": 1,
        "partial_not_recoverable": 1,
    }
    # quarantine preserves the full original path under the session id
    target = q / "ses_r" / gone.lstrip("/")
    assert target.read_text() == "recovered body\n"
    assert not os.path.exists(
        gone
    )  # the original path was NOT created (quarantine only)
    assert Path(present).read_text() == "live body\n"  # untouched
    manifest = json.loads((q / "manifest.json").read_text())
    assert manifest["counts"]["recovered"] == 1
    row = manifest["files"][0]
    assert row["sha256"] == hashlib.sha256(b"recovered body\n").hexdigest()
    assert row["original_path"] == gone

    second = cm.recover(str(tmp_path / "d.db"), 1, str(q), execute=True)
    assert second["counts"]["recovered"] == 0
    assert (
        second["counts"]["skipped_existing_target"] == 1
    )  # idempotent: copies 0, overwrites 0
    assert target.read_text() == "recovered body\n"
