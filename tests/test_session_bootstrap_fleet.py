"""Session bootstrap joins the fleet: announce presence, recover a silent bus, start one watcher."""

import os
import subprocess
import tempfile
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin"


def _run(fleet_body, args=(), extra_env=None, execute_body=None):
    with tempfile.TemporaryDirectory() as d:
        b = Path(d) / "bin"
        b.mkdir()
        (b / "idp-session-bootstrap").write_text(
            (BIN / "idp-session-bootstrap").read_text()
        )
        (b / "estate-fleet").write_text(fleet_body)
        if execute_body is not None:
            (b / "estate-execute").write_text(execute_body)
        for f in b.iterdir():
            f.chmod(0o755)
        home = Path(d) / "home"
        (home / "scripts").mkdir(parents=True)
        (home / "scripts" / "hook-run.py").write_text("")
        env = dict(os.environ, ESTATE_HOME=str(home))
        env.pop("ESTATE_AGENT", None)
        env.update(extra_env or {})
        if execute_body is not None:
            env["PATH"] = str(b) + os.pathsep + env.get("PATH", "")
        return subprocess.run(
            [str(b / "idp-session-bootstrap"), *args],
            env=env,
            capture_output=True,
            text=True,
        )


def test_announce_publishes_presence_with_ticket_and_worktree():
    worktree = str(Path(tempfile.gettempdir()) / "wt")
    r = _run(
        '#!/bin/sh\nif [ "$1" = broadcast ]; then echo "broadcast:$2"; fi\n',
        args=("--announce",),
        extra_env={
            "ESTATE_AGENT": "agent-a",
            "ESTATE_TICKET": "idp#7790",
            "ESTATE_WORKTREE": worktree,
        },
    )
    assert r.returncode == 0
    assert "broadcast:PRESENCE actor=agent-a ticket=idp#7790" in r.stdout
    assert f"worktree={worktree}" in r.stdout


def test_no_announce_by_default():
    r = _run('#!/bin/sh\necho "fleet:$*"\n')
    assert "broadcast" not in r.stdout


def test_blind_bus_uses_recovery_door_then_rereads():
    r = _run(
        '#!/bin/sh\nif [ -f "$ESTATE_HOME/bus-up" ]; then echo "fleet:$*"; exit 0; fi\n'
        'echo "BLIND" >&2; exit 2\n',
        execute_body='#!/bin/sh\ntouch "$ESTATE_HOME/bus-up"\n',
    )
    assert r.returncode == 0
    assert "fleet:inbox" in r.stdout
    assert "still unreadable" not in r.stderr


def test_missing_binary_is_reported_blind_after_recovery_attempt():
    r = _run(
        '#!/bin/sh\necho "BLIND" >&2; exit 2\n',
        execute_body="#!/bin/sh\nexit 1\n",
    )
    assert r.returncode == 0
    assert "still unreadable" in r.stderr


def test_watch_starts_one_watcher_and_reports_pid():
    r = _run("#!/bin/sh\nsleep 1\n", args=("--watch",))
    assert r.returncode == 0
    assert "watcher started pid=" in r.stdout
