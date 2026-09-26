"""The compaction hook journals each summary Claude Code writes, exactly once, and never blocks.

Runs the real .claude/hooks/journal_compaction.py as Claude Code does (event JSON on stdin),
with a stand-in `growmos` on PATH that records every call.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

HOOK = (
    Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "journal_compaction.py"
)
MARKER = "This session is being continued from a previous conversation"


def _run(tmp_path, transcript, growmos_rc=0):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    calls = tmp_path / "calls"
    fake = bin_dir / "growmos"
    fake.write_text(
        f'#!/bin/sh\nprintf "%s\\n---\\n" "$*" >> "{calls}"\nexit {growmos_rc}\n'
    )
    fake.chmod(0o755)
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
    }
    event = {"transcript_path": str(transcript), "cwd": str(tmp_path)}
    done = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(event),
        text=True,
        capture_output=True,
        env=env,
        timeout=60,
    )
    journalled = calls.read_text().count("\n---\n") if calls.exists() else 0
    return done, journalled


def _transcript(tmp_path, *texts):
    path = tmp_path / "abc123.jsonl"
    lines = [json.dumps({"type": "user", "message": {"content": t}}) for t in texts]
    path.write_text("\n".join(lines) + "\nnot json\n")
    return path


def test_a_summary_is_journalled_once_across_repeated_runs(tmp_path):
    t = _transcript(
        tmp_path, f"{MARKER}. Pending: land the router.", "an ordinary turn"
    )
    done, first = _run(tmp_path, t)
    assert done.returncode == 0
    assert first == 1
    _, second = _run(tmp_path, t)
    assert second == 1  # the calls file is cumulative: the rerun added nothing


def test_block_form_content_is_read_too(tmp_path):
    t = tmp_path / "blocks.jsonl"
    t.write_text(
        json.dumps(
            {
                "type": "user",
                "message": {"content": [{"type": "text", "text": f"{MARKER}. x"}]},
            }
        )
        + "\n"
    )
    _, journalled = _run(tmp_path, t)
    assert journalled == 1


def test_a_failing_growmos_never_blocks_and_is_retried_next_time(tmp_path):
    t = _transcript(tmp_path, f"{MARKER}. y")
    done, _ = _run(tmp_path, t, growmos_rc=3)
    assert done.returncode == 0
    assert "growmos journal rc=3" in done.stderr
    _, journalled = _run(tmp_path, t)
    assert journalled == 2  # nothing was marked seen, so the summary went again


def test_a_missing_transcript_is_a_no_op(tmp_path):
    done, journalled = _run(tmp_path, tmp_path / "absent.jsonl")
    assert done.returncode == 0
    assert journalled == 0
