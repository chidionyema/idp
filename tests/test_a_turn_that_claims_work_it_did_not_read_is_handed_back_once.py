"""The Stop hook hands a turn back, once, when it claims completed work its own tool calls do not back.

Runs the real bin/reasoning_gateway_hook.py --hook (which runs bin/epistemic_firewall.py --turn)
on Claude Code-shaped transcripts: tool calls named `Bash`, nested under `message`, prompts as
user lines with text and tool results as user lines with tool_result blocks.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "bin/reasoning_gateway_hook.py"
FIREWALL = ROOT / "bin/epistemic_firewall.py"


def _prompt(text: str) -> dict:
    return {"type": "user", "message": {"role": "user", "content": text}}


def _bash(command: str) -> list[dict]:
    return [
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "name": "Bash", "input": {"command": command}}
                ],
            },
        },
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "tool_result", "content": "..."}],
            },
        },
    ]


def _say(text: str) -> dict:
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
    }


READS = [
    *_bash("git show HEAD --stat"),
    *_bash("kubectl -n spire-mgmt get pods"),
    *_bash("gh pr view 4436"),
]
CLAIM = "I fixed spire-proof-run and pushed it."


def _write(tmp_path: Path, lines: list[dict]) -> Path:
    t = tmp_path / "session.jsonl"
    t.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    return t


def _hook(tmp_path: Path, transcript: Path, active: bool = False):
    payload = {
        "transcript_path": str(transcript),
        "session_id": "t",
        "stop_hook_active": active,
    }
    return subprocess.run(
        [sys.executable, str(HOOK), "--hook"],
        input=json.dumps(payload),
        env={**os.environ, "HOME": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_a_recap_turn_that_read_nothing_is_handed_back(tmp_path):
    # Earlier turns read plenty; this turn only talks. Session-wide, the old rule passed it.
    t = _write(
        tmp_path,
        [_prompt("fix it"), *READS, _say("done"), _prompt("status?"), _say(CLAIM)],
    )
    r = _hook(tmp_path, t)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["decision"] == "block"
    assert CLAIM in out["reason"] and "does not block again" in out["reason"]


def test_the_continuation_is_never_blocked_again(tmp_path):
    t = _write(tmp_path, [_prompt("fix it"), *READS, _prompt("status?"), _say(CLAIM)])
    r = _hook(tmp_path, t, active=True)
    assert r.returncode == 0 and r.stdout.strip() == "", r.stdout


def test_a_turn_whose_own_reads_back_the_claim_passes(tmp_path):
    t = _write(tmp_path, [_prompt("fix it"), *READS, _say(CLAIM)])
    r = _hook(tmp_path, t)
    assert r.returncode == 0 and r.stdout.strip() == "", r.stdout
    ledger = json.loads((tmp_path / ".pi/agent/reasoning-gateway/t.json").read_text())
    assert ledger["epistemic"]["exit"] == 0, ledger["epistemic"]


def test_claude_codes_capitalised_bash_counts_as_a_witness(tmp_path):
    # Before: every piece was "Bash:...", the witness check read only "bash:", and a session
    # backed by git show, kubectl and gh graded "no piece of evidence reads state".
    t = _write(tmp_path, [_prompt("fix it"), *READS, _say(CLAIM)])
    r = subprocess.run(
        [sys.executable, str(FIREWALL), str(t)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_the_founders_own_words_are_not_graded_as_claims(tmp_path):
    t = _write(tmp_path, [_prompt("I fixed the router myself, now look at spire")])
    r = subprocess.run(
        [sys.executable, str(FIREWALL), "--turn", str(t)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stdout + r.stderr
