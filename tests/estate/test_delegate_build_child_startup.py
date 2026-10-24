"""A delegated model call survives the CLI dying at startup, and says so when it cannot.

Measured 2026-10-24: a delegated planner ran through the intent door and its `claude -p` child
failed at startup -- exit 1, no output at all, stderr "error: An unknown error occurred
(Unexpected)". The child never reached the model, so the plan was simply lost and the reason
was buried in a usage blob. The environment was identical in the door that worked and the door
that did not, so the cause was the CLI's own startup, not the estate's.

Two things are proved here: a startup failure is retried (it costs nothing, the model never ran,
and it clears on its own) and the record keeps every failure so a dead call is diagnosable.
"""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2] / "platform/estate/libexec/delegate-build.py"
)

PLAN = {
    "branch": "delegate/t",
    "prior_art": {
        "searches": [
            {"kind": k, "query": f"rg {k}", "found": []}
            for k in ("prs", "tickets", "code")
        ],
        "verdict": "new",
    },
    "steps": [
        {
            "id": "s1",
            "title": "one step",
            "files": ["a.txt"],
            "read": [],
            "depends_on": [],
            "instructions": "write a.txt",
            "done_check": "test -f a.txt",
        }
    ],
}
STARTUP_ERROR = "error: An unknown error occurred (Unexpected)"


def _fake_claude(tmp_path: Path, failures: int) -> Path:
    """A claude that dies at startup `failures` times, then answers with the plan."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    events = [{"type": "system", "subtype": "init"}]
    events += [
        {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": json.dumps(PLAN)}]},
        }
    ]
    events.append(
        {
            "type": "result",
            "result": json.dumps(PLAN),
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "num_turns": 1,
            "total_cost_usd": 0,
        }
    )
    counter = tmp_path / "calls.txt"
    fake = bin_dir / "claude"
    fake.write_text(
        f"#!{sys.executable}\n"
        "import json, sys\n"
        f"counter = {str(counter)!r}\n"
        "try:\n"
        f"    n = int(open(counter).read())\n"
        "except OSError:\n"
        "    n = 0\n"
        f"open(counter, 'w').write(str(n + 1))\n"
        f"if n < {failures}:\n"
        f"    sys.stderr.write({STARTUP_ERROR!r} + '\\n')\n"
        "    sys.exit(1)\n"
        f"for e in {events!r}:\n"
        "    print(json.dumps(e))\n"
    )
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    return bin_dir


def _plan(tmp_path: Path, failures: int):
    bin_dir = _fake_claude(tmp_path, failures)
    spec = tmp_path / "spec.md"
    spec.write_text("build a.txt\n")
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "plan",
            "slug=t",
            f"spec={spec}",
            f"repo={tmp_path}",
        ],
        env={
            **os.environ,
            "ESTATE_DELEGATE_ROOT": str(tmp_path / "root"),
            "ESTATE_DELEGATE_STARTUP_BACKOFF": "0,0,0",
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
        },
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_a_child_that_dies_at_startup_is_retried_and_the_plan_lands(tmp_path):
    r = _plan(tmp_path, failures=1)

    assert r.returncode == 0, r.stderr
    plan = json.loads((tmp_path / "root/t/plan.json").read_text())
    assert plan["steps"][0]["id"] == "s1"
    usage = json.loads((tmp_path / "root/t/plan-usage.json").read_text())
    assert len(usage["startup_failures"]) == 1
    assert usage["startup_failures"][0]["exit"] == 1
    assert STARTUP_ERROR in usage["startup_failures"][0]["stderr"]
    assert int((tmp_path / "calls.txt").read_text()) == 2


def test_every_startup_failure_is_named_not_hidden(tmp_path):
    r = _plan(tmp_path, failures=99)

    assert r.returncode == 1
    assert "failed at startup" in r.stderr
    assert STARTUP_ERROR in r.stderr
    usage = json.loads((tmp_path / "root/t/plan-usage.json").read_text())
    assert len(usage["startup_failures"]) == 3
    assert int((tmp_path / "calls.txt").read_text()) == 3


def test_the_child_is_not_refused_by_the_interactive_plan_gate(tmp_path):
    """The delegated child has no plan tools, so the interactive gate must be off for it."""
    spec = importlib.util.spec_from_file_location("delegate_build_child", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    harness = tmp_path / "harness-cc"
    harness.mkdir()
    mod.HARNESS_CC = harness

    env = mod.child_env()

    assert env["ESTATE_PLAN_LOCK"] == "off"
    assert env["CLAUDE_CONFIG_DIR"] == str(harness)
