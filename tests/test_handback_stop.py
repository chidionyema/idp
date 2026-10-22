"""The Stop hook refuses a turn that hands work back (lane/no-handback).

Graded at the door every Claude Code session passes through: `bin/estate-memory-enforce stop`,
fed the hook's stdin JSON, with the ledger isolated under ESTATE_MEMORY_HOME.
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, "bin", "estate-memory-enforce")


def line(role, content):
    return json.dumps({"type": role, "message": {"role": role, "content": content}})


def closing(tmp_path, text):
    path = tmp_path / "t.jsonl"
    path.write_text(
        "\n".join(
            [
                line("user", "build the feature"),
                line("assistant", [{"type": "text", "text": text}]),
            ]
        )
    )
    return str(path)


def stop(tmp_path, text, active=False, env=None):
    payload = {
        "transcript_path": closing(tmp_path, text),
        "session_id": "s-handback",
        "stop_hook_active": active,
    }
    run_env = {k: v for k, v in os.environ.items() if k != "ESTATE_MEMORY_ENFORCE"}
    run_env["ESTATE_MEMORY_HOME"] = str(tmp_path)
    run_env.update(env or {})
    proc = subprocess.run(  # noqa: S603 - fixed argv
        [sys.executable, HOOK, "stop"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=run_env,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout) if proc.stdout.strip() else None


def ledger(tmp_path):
    p = tmp_path / "enforce-ledger.jsonl"
    return [json.loads(row) for row in p.read_text().splitlines()] if p.exists() else []


def test_a_hand_back_closing_is_blocked_and_ledgered(tmp_path):
    out = stop(
        tmp_path,
        "Landed the hook.\n\nStill open:\n- wire the router\n\nWant me to do it?",
    )
    assert out["decision"] == "block"
    assert "Do not stop here" in out["reason"]
    rows = [r for r in ledger(tmp_path) if r["decision"] == "refuse"]
    assert rows and rows[0]["reason"] == "handed work back" and rows[0]["found"]


def test_a_clean_report_is_allowed(tmp_path):
    assert (
        stop(
            tmp_path,
            "Wired the hook and ran 14 tests, all pass. Ledger shows the refusal.",
        )
        is None
    )
    assert not [r for r in ledger(tmp_path) if r["decision"] == "refuse"]


def test_stop_hook_active_allows_so_a_session_never_loops(tmp_path):
    assert stop(tmp_path, "Want me to ship it?", active=True) is None


def test_an_evidenced_blocker_is_allowed(tmp_path):
    text = (
        "Blocked: the lane cannot push.\n\n```\n$ estate-execute lane-submit\nexit status 1\n"
        "fatal: Authentication failed\n```\nLet me know if the key is rotated."
    )
    assert stop(tmp_path, text) is None


def test_an_unevidenced_blocker_is_still_blocked(tmp_path):
    out = stop(tmp_path, "I'm blocked. Let me know if you can unblock me.")
    assert out["decision"] == "block"


def test_the_opt_out_is_honoured_and_ledgered(tmp_path):
    assert (
        stop(tmp_path, "Want me to ship it?", env={"ESTATE_MEMORY_ENFORCE": "0"})
        is None
    )
    assert [r for r in ledger(tmp_path) if r["decision"] == "optout"]
