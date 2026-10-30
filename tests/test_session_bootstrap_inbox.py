"""idp-session-bootstrap prints the fleet inbox and never fails because of it (#7481)."""

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


def test_inbox_printed_with_ack():
    r = _run('#!/bin/sh\necho "directive: $ESTATE_AGENT $*"\n')
    assert r.returncode == 0
    assert "directive: claude-code inbox --ack" in r.stdout


def test_dead_bus_does_not_block_start():
    r = _run("#!/bin/sh\nexit 3\n")
    assert r.returncode == 0
