"""delegate-build plan keeps the plan the planner wrote, even when it was not the last reply.

Measured 2026-09-27 (vendor-self-setup): the Opus planner wrote its plan JSON, then a
cross-session message arrived and its final reply answered that message. The plan was read from
the final reply only, so "planner returned no JSON" and the plan was lost though it existed. The
fake claude below replays that stream.
"""

from __future__ import annotations

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
LATE = "SPIFFE/SPIRE ticket status: nothing new from this session."


def _plan(tmp_path: Path, texts: list[str]) -> subprocess.CompletedProcess:
    events = [{"type": "system", "subtype": "init"}]
    events += [
        {"type": "assistant", "message": {"content": [{"type": "text", "text": t}]}}
        for t in texts
    ]
    events.append(
        {
            "type": "result",
            "result": texts[-1],
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "num_turns": len(texts),
            "total_cost_usd": 0,
        }
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "claude"
    fake.write_text(
        f"#!{sys.executable}\nimport json, sys\n"
        "assert sys.argv[sys.argv.index('--output-format') + 1] == 'stream-json'\n"
        f"for e in {events!r}:\n    print(json.dumps(e))\n"
    )
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
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
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
        },
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_the_plan_is_kept_when_a_late_message_is_the_last_reply(tmp_path):
    r = _plan(tmp_path, ["```json\n" + json.dumps(PLAN) + "\n```", LATE])
    assert r.returncode == 0, r.stderr
    plan = json.loads((tmp_path / "root/t/plan.json").read_text())
    assert plan["steps"][0]["id"] == "s1"
    assert LATE in (tmp_path / "root/t/plan-raw.txt").read_text()


def test_no_plan_anywhere_fails_and_names_the_raw_file(tmp_path):
    r = _plan(tmp_path, ["thinking out loud {not json}", LATE])
    assert r.returncode == 1
    assert "plan-raw.txt" in r.stderr
    assert not (tmp_path / "root/t/plan.json").exists()
