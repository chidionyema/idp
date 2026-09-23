"""Binds features/gates/plist-gate.feature. Steps run bin/plist-gate for real over a rendered
template pointing at a script that backgrounds a child, then over the live scheduler template."""
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("features/gates/plist-gate.feature")

IDP = Path(__file__).resolve().parents[3]

TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>ai.estate.test</string>
  <key>ProgramArguments</key><array><string>{prog}</string></array>
  {extra}
</dict></plist>
"""


def _gate(*files: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(IDP / "bin" / "plist-gate"), *map(str, files)],
                          env={**os.environ, "IDP": str(IDP)}, capture_output=True, text=True)


@pytest.fixture
def state(tmp_path: Path) -> dict:
    return {"dir": tmp_path}


@given("a launchd template whose program starts a child with nohup, setsid or disown and then exits")
def _template(state: dict) -> None:
    prog = state["dir"] / "up"
    prog.write_text("#!/bin/sh\nnohup sleep 1 >/dev/null 2>&1 &\n")
    prog.chmod(prog.stat().st_mode | stat.S_IXUSR)
    state["prog"] = prog
    # plist-gate requires Label to match the file name, so each variant sits in its own dir.
    for name, extra in (("bare", ""), ("abandon", "<key>AbandonProcessGroup</key><true/>")):
        d = state["dir"] / name
        d.mkdir()
        (d / "ai.estate.test.plist.tmpl").write_text(TEMPLATE.format(prog=prog, extra=extra))


@when("bin/plist-gate grades it")
def _grade(state: dict) -> None:
    state["bare"] = _gate(state["dir"] / "bare" / "ai.estate.test.plist.tmpl")


@then("it fails unless the job declares AbandonProcessGroup or KeepAlive")
def _fails(state: dict) -> None:
    r = state["bare"]
    assert r.returncode == 1 and "AbandonProcessGroup" in r.stdout, r.stdout + r.stderr


@then("the same template with AbandonProcessGroup true passes")
def _passes(state: dict) -> None:
    r = _gate(state["dir"] / "abandon" / "ai.estate.test.plist.tmpl")
    assert r.returncode == 0, r.stdout + r.stderr


@then("ai.estate.scheduler carries AbandonProcessGroup, so dagster-daemon outlives scheduler-up")
def _scheduler(state: dict) -> None:
    tmpl = IDP / "launchd" / "ai.estate.scheduler.plist.tmpl"
    assert "AbandonProcessGroup" in tmpl.read_text()
    r = _gate(tmpl)
    assert r.returncode == 0, r.stdout + r.stderr
