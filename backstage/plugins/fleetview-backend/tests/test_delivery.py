from __future__ import annotations

import importlib.util
import json
import sqlite3
import stat
from datetime import datetime, timedelta, timezone
from pathlib import Path

_SPEC_PATH = Path(__file__).resolve().parents[1] / "src/fleetview_backend/delivery.py"
_spec = importlib.util.spec_from_file_location("delivery", _SPEC_PATH)
d = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(d)

NOW = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)


def _mkexec(path: Path) -> Path:
    path.write_text("#!/bin/sh\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def test_converger_not_installed(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    prefix = tmp_path / "prefix"
    daemon_plist = tmp_path / "no-such.plist"
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    result = d.delivery(
        home=home,
        now=NOW,
        prefix=prefix,
        daemon_plist=daemon_plist,
        agents_dir=agents_dir,
        launchctl_text="",
    )

    codes = [a["code"] for a in result["alerts"]]
    assert "converger-not-installed" in codes
    assert result["operating"] is False


def test_fresh_state_operating(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    prefix = tmp_path / "prefix"
    (prefix / "converge").mkdir(parents=True)
    daemon_plist = tmp_path / "daemon.plist"
    daemon_plist.write_text("x")
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    state = {
        "checked_at": NOW.isoformat(),
        "behind": False,
        "last_error": None,
        "drift": [],
    }
    (prefix / "converge" / "state.json").write_text(json.dumps(state))

    ledger_lines = [
        json.dumps({"sha": "aaa", "latency_s": 1}),
        json.dumps({"sha": "bbb", "latency_s": 2}),
        "not json garbage",
    ]
    (prefix / "converge" / "ledger.jsonl").write_text("\n".join(ledger_lines) + "\n")

    result = d.delivery(
        home=home,
        now=NOW,
        prefix=prefix,
        daemon_plist=daemon_plist,
        agents_dir=agents_dir,
        launchctl_text="",
    )

    assert result["operating"] is True
    assert len(result["converges"]) == 2
    assert result["converges"][0]["sha"] == "bbb"


def test_converger_silent(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    prefix = tmp_path / "prefix"
    (prefix / "converge").mkdir(parents=True)
    daemon_plist = tmp_path / "daemon.plist"
    daemon_plist.write_text("x")
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    old = NOW - timedelta(minutes=20)
    state = {
        "checked_at": old.isoformat(),
        "behind": False,
        "last_error": None,
        "drift": [],
    }
    (prefix / "converge" / "state.json").write_text(json.dumps(state))

    result = d.delivery(
        home=home,
        now=NOW,
        prefix=prefix,
        daemon_plist=daemon_plist,
        agents_dir=agents_dir,
        launchctl_text="",
    )

    codes = [a["code"] for a in result["alerts"]]
    assert "converger-silent" in codes


def test_fetch_failing(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    prefix = tmp_path / "prefix"
    (prefix / "converge").mkdir(parents=True)
    daemon_plist = tmp_path / "daemon.plist"
    daemon_plist.write_text("x")
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    state = {
        "checked_at": NOW.isoformat(),
        "behind": False,
        "last_error": "git fetch failed: no route to host",
        "drift": [],
    }
    (prefix / "converge" / "state.json").write_text(json.dumps(state))

    result = d.delivery(
        home=home,
        now=NOW,
        prefix=prefix,
        daemon_plist=daemon_plist,
        agents_dir=agents_dir,
        launchctl_text="",
    )

    fetch_alerts = [a for a in result["alerts"] if a["code"] == "fetch-failing"]
    assert len(fetch_alerts) == 1
    assert "no route to host" in fetch_alerts[0]["text"]


def test_delegate_scratchpad_never_copied(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    delegate_dir = home / ".estate" / "delegate" / "builder-1"
    delegate_dir.mkdir(parents=True)

    # The shape delegate-build writes: keyed by step id, check_rc as a string.
    results = {
        "s1": {
            "done": True,
            "attempts": 2,
            "scratchpad": "the builder's own unverified narration, never copied",
            "empirical": [
                {"attempt": "1", "check_rc": "1", "check_output": "x"},
                {"attempt": "2", "check_rc": "0", "check_output": "y"},
            ],
        },
        "s2": {"done": False, "attempts": 0, "empirical": []},
    }
    (delegate_dir / "results.json").write_text(json.dumps(results))

    prefix = tmp_path / "prefix"
    daemon_plist = tmp_path / "no-such.plist"
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    result = d.delivery(
        home=home,
        now=NOW,
        prefix=prefix,
        daemon_plist=daemon_plist,
        agents_dir=agents_dir,
        launchctl_text="",
    )

    assert "scratchpad" not in json.dumps(result)
    delegate = result["delegate"]
    assert len(delegate) == 1
    assert delegate[0]["slug"] == "builder-1"
    assert delegate[0]["steps"] == [
        {"id": "s1", "done": True, "attempts": 2, "last_check_rc": 0},
        {"id": "s2", "done": False, "attempts": 0, "last_check_rc": None},
    ]
    assert "check_output" not in json.dumps(result)


def test_unmerged_runs_and_alert(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".estate").mkdir()
    db_path = home / ".estate" / "estate.db"

    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE intent_tickets (id TEXT, intent TEXT, harness TEXT, started_at TEXT, status TEXT)"
    )
    recent = (NOW - timedelta(hours=1)).isoformat()
    old = (NOW - timedelta(days=2)).isoformat()
    conn.execute(
        "INSERT INTO intent_tickets VALUES (?, ?, ?, ?, ?)",
        ("1", "shell-parse", "unmerged", recent, "ok"),
    )
    conn.execute(
        "INSERT INTO intent_tickets VALUES (?, ?, ?, ?, ?)",
        ("2", "git-branch", "claude+unconverged", old, "ok"),
    )
    conn.commit()
    conn.close()

    prefix = tmp_path / "prefix"
    daemon_plist = tmp_path / "no-such.plist"
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    result = d.delivery(
        home=home,
        now=NOW,
        prefix=prefix,
        daemon_plist=daemon_plist,
        agents_dir=agents_dir,
        launchctl_text="",
    )

    ids = {row["id"] for row in result["unmerged_runs"]}
    assert ids == {"1", "2"}

    unmerged_alerts = [a for a in result["alerts"] if a["code"] == "unmerged"]
    assert len(unmerged_alerts) == 1


def test_jobs_health(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    agents_dir = home / "Library" / "LaunchAgents"
    agents_dir.mkdir(parents=True)

    prog_a = _mkexec(tmp_path / "prog_a.sh")
    prog_b = _mkexec(tmp_path / "prog_b.sh")

    (agents_dir / "ai.estate.a.plist").write_bytes(
        __import__("plistlib").dumps({"Label": "ai.estate.a", "Program": str(prog_a)})
    )
    (agents_dir / "ai.estate.b.plist").write_bytes(
        __import__("plistlib").dumps({"Label": "ai.estate.b", "Program": str(prog_b)})
    )
    (agents_dir / "com.founder.c.plist").write_bytes(
        __import__("plistlib").dumps(
            {
                "Label": "com.founder.c",
                "ProgramArguments": [
                    "/usr/bin/python3",
                    "-u",
                    str(tmp_path / "missing.py"),
                ],
            }
        )
    )
    (agents_dir / "ai.estate.d.plist").write_bytes(
        __import__("plistlib").dumps({"Label": "ai.estate.d", "Program": str(prog_a)})
    )
    (agents_dir / "com.apple.x.plist").write_bytes(
        __import__("plistlib").dumps({"Label": "com.apple.x", "Program": str(prog_a)})
    )

    launchctl_text = (
        "PID\tStatus\tLabel\n"
        "42\t-\tai.estate.a\n"
        "-\t78\tai.estate.b\n"
        "-\t0\tcom.founder.c\n"
    )

    prefix = tmp_path / "prefix"
    daemon_plist = tmp_path / "no-such.plist"

    result = d.delivery(
        home=home,
        now=NOW,
        prefix=prefix,
        daemon_plist=daemon_plist,
        agents_dir=agents_dir,
        launchctl_text=launchctl_text,
    )

    by_label = {j["label"]: j for j in result["jobs"]}
    assert "com.apple.x" not in by_label
    assert by_label["ai.estate.a"]["health"] == "running"
    assert by_label["ai.estate.b"]["health"] == "failing"
    assert by_label["com.founder.c"]["health"] == "orphan"
    assert by_label["ai.estate.d"]["health"] == "not-loaded"

    failing_alerts = [a for a in result["alerts"] if a["code"] == "jobs-failing"]
    assert len(failing_alerts) == 1
    assert "ai.estate.b(78)" in failing_alerts[0]["text"]

    orphan_alerts = [a for a in result["alerts"] if a["code"] == "jobs-orphaned"]
    assert len(orphan_alerts) == 1
    assert "com.founder.c" in orphan_alerts[0]["text"]


def test_repo_field(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    agents_dir = home / "Library" / "LaunchAgents"
    agents_dir.mkdir(parents=True)

    repo_root = tmp_path / "r"
    (repo_root / ".git").mkdir(parents=True)
    (repo_root / "sub").mkdir()
    prog = _mkexec(repo_root / "sub" / "prog")

    (agents_dir / "ai.estate.e.plist").write_bytes(
        __import__("plistlib").dumps({"Label": "ai.estate.e", "Program": str(prog)})
    )

    prefix = tmp_path / "prefix"
    daemon_plist = tmp_path / "no-such.plist"

    result = d.delivery(
        home=home,
        now=NOW,
        prefix=prefix,
        daemon_plist=daemon_plist,
        agents_dir=agents_dir,
        launchctl_text="",
    )

    job = next(j for j in result["jobs"] if j["label"] == "ai.estate.e")
    assert job["repo"] == str(repo_root)


def test_garbage_state_json(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    prefix = tmp_path / "prefix"
    (prefix / "converge").mkdir(parents=True)
    (prefix / "converge" / "state.json").write_text("{not valid json")

    daemon_plist = tmp_path / "daemon.plist"
    daemon_plist.write_text("x")
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    result = d.delivery(
        home=home,
        now=NOW,
        prefix=prefix,
        daemon_plist=daemon_plist,
        agents_dir=agents_dir,
        launchctl_text="",
    )

    assert result["state"] is None
    codes = [a["code"] for a in result["alerts"]]
    assert "converger-missing" in codes
