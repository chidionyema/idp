"""Session-start inbox viewing must not impersonate an applied-effect receipt."""

import os
import subprocess
import tempfile
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin"


def _run(fleet_body):
    with tempfile.TemporaryDirectory() as d:
        b = Path(d) / "bin"
        b.mkdir()
        (b / "idp-session-bootstrap").write_text(
            (BIN / "idp-session-bootstrap").read_text()
        )
        (b / "estate-fleet").write_text(fleet_body)
        for f in b.iterdir():
            f.chmod(0o755)
        home = Path(d) / "home"
        (home / "scripts").mkdir(parents=True)
        (home / "scripts" / "hook-run.py").write_text("")
        env = dict(os.environ, ESTATE_HOME=str(home))
        return subprocess.run(
            [str(b / "idp-session-bootstrap")], env=env, capture_output=True, text=True
        )


def test_inbox_read_does_not_ack_unprocessed_instructions():
    r = _run('#!/bin/sh\necho "directive: $ESTATE_AGENT $*"\n')
    assert r.returncode == 0
    assert "directive: claude-code inbox" in r.stdout
    assert "--ack" not in r.stdout


def test_inbox_is_not_truncated_beyond_40_lines():
    r = _run(
        '#!/bin/sh\ni=1; while [ "$i" -le 75 ]; '
        'do echo "directive-$i"; i=$((i+1)); done\n'
    )
    assert r.returncode == 0
    assert "directive-1\n" in r.stdout
    assert "directive-75\n" in r.stdout
    assert sum(line.startswith("directive-") for line in r.stdout.splitlines()) == 75


def test_dead_bus_marks_blind_without_claiming_application():
    r = _run("#!/bin/sh\nexit 3\n")
    assert r.returncode == 0  # Read-only startup; effect doors gate privilege.
    assert "BLIND   idp-session-bootstrap  fleet inbox unreadable" in r.stderr
    assert "no messages acknowledged" in r.stderr
