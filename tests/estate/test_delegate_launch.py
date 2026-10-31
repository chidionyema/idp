"""The generic routed launch path: preflight, bounded child, measured progress.

These tests are empirical: they run the real script as a subprocess with a fake `pi` on the
route, so what is asserted is what the dispatcher wrote, not what it claims it wrote.

The contract under test:
  * preflight refuses an identity mismatch, a missing worktree, a missing claim and a model
    that is not on the route -- before any child is started;
  * the done-check is reality: the launch succeeds only when the check exits 0;
  * progress is a verified milestone, never a heartbeat or a tool call;
  * the second attempt is rebuilt from the failed check's output (the empirical recovery the
    plan/dispatch path already used) and never from the failed attempt's own words;
  * an identical retry is refused, and a repeated failure signature is escalated.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2] / "platform/estate/libexec/delegate-build.py"
)

FAKE_PI = """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

record = Path(os.environ["FAKE_PI_RECORD"])
argv = sys.argv[1:]
prompt = ""
for a in argv:
    if a.startswith("@"):
        prompt = Path(a[1:]).read_text()
record.parent.mkdir(parents=True, exist_ok=True)
with record.open("a") as f:
    f.write(json.dumps({"argv": argv, "prompt": prompt}) + "\\n")

payload = json.loads(os.environ.get("FAKE_PI_PAYLOAD", "{}"))
if payload.get("writes"):
    target = Path(payload["writes"])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload.get("content", "written"))
print(json.dumps({"type": "tool_execution_start", "toolName": "write"}))
print(json.dumps({
    "type": "message_end",
    "message": {
        "usage": {"totalTokens": 4242},
        "content": [{"type": "text", "text": payload.get("said", "I wrote the file")}],
    },
}))
"""


def _setup(
    tmp_path: Path, *, writes: str | None = "artifact.md", said: str = "I wrote it"
):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "base.txt").write_text("base\n")

    spec = tmp_path / "spec.md"
    spec.write_text("Write the word DELEGATED into artifact.md.\n")

    models = tmp_path / "models.json"
    models.write_text(
        json.dumps(
            {
                "providers": {
                    "estate": {
                        "baseUrl": "http://127.0.0.1:4000/v1",
                        "models": [{"id": "minimax_m27"}, {"id": "other_model"}],
                    }
                }
            }
        )
    )

    fake_pi = tmp_path / "fake-pi"
    fake_pi.write_text(FAKE_PI)
    fake_pi.chmod(fake_pi.stat().st_mode | 0o755)

    claims = tmp_path / "claims.json"
    claims.write_text(
        json.dumps(
            {
                "claims": [
                    {
                        "issue": 7310,
                        "agent": "pi-delegate-intent",
                        "paths": ["artifact.md"],
                        "heartbeat": datetime.now(timezone.utc).strftime(
                            "%Y-%m-%dT%H:%M:%SZ"
                        ),
                    }
                ]
            }
        )
    )

    env = {
        **os.environ,
        "ESTATE_AGENT": "pi-delegate-intent",
        "ESTATE_DELEGATE_ROOT": str(tmp_path / "root"),
        "ESTATE_DELEGATE_CLAIM_FILE": str(claims),
        "ESTATE_PI_MODELS": str(models),
        "ESTATE_PI_BIN": str(fake_pi),
        "FAKE_PI_RECORD": str(tmp_path / "pi-record.jsonl"),
        "FAKE_PI_PAYLOAD": json.dumps(
            {"writes": writes, "said": said, "content": "DELEGATED\n"}
        ),
    }

    def packet(**overrides):
        base = {
            "task_id": "demo-1",
            "spec": str(spec),
            "worktree": str(repo),
            "identity": "pi-delegate-intent",
            "claim_issue": 7310,
            "harness": "pi",
            "provider": "estate",
            "model": "minimax_m27",
            "done_check": "grep -q DELEGATED artifact.md",
            "milestones": [{"id": "artifact", "kind": "file", "path": "artifact.md"}],
            "budget": {"max_wall_s": 30, "max_attempts": 2, "max_steps": 10},
            "strategies": ["write it directly", "write it another way"],
        }
        base.update(overrides)
        path = tmp_path / "task.json"
        path.write_text(json.dumps(base))
        return path

    def launch(*args, env_overrides=None, packet_path=None):
        run_env = dict(env)
        run_env.update(env_overrides or {})
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "launch",
                "slug=demo",
                f"task={packet_path or packet()}",
                *args,
            ],
            env=run_env,
            capture_output=True,
            text=True,
            timeout=120,
        )

    return {
        "launch": launch,
        "packet": packet,
        "env": env,
        "repo": repo,
        "tmp": tmp_path,
    }


def test_launch_succeeds_only_when_the_done_check_passes(tmp_path):
    s = _setup(tmp_path)
    r = s["launch"]()
    assert r.returncode == 0, r.stdout + r.stderr

    state = json.loads((tmp_path / "root/demo/state.json").read_text())
    assert state["state"] == "succeeded"
    # Progress is a verified milestone, and the budget is carried in the state.
    assert state["last_verified_milestone"] == "artifact"
    assert state["milestones"]["artifact"]["verified"] is True
    assert state["tokens"] == 4242
    assert state["route"]["model"] == "minimax_m27"
    assert state["identity"] == "pi-delegate-intent"

    results = json.loads((tmp_path / "root/demo/results.json").read_text())
    assert results["demo-1"]["done"] is True
    assert results["demo-1"]["empirical"][0]["check_rc"] == 0


def test_a_failing_check_is_a_failure_even_when_the_worker_says_it_is_done(tmp_path):
    s = _setup(tmp_path, writes="other.md", said="all tests pass, I am done")
    r = s["launch"]()
    assert r.returncode == 1, r.stdout + r.stderr

    state = json.loads((tmp_path / "root/demo/state.json").read_text())
    assert state["state"] == "failed"
    assert state["blocker"]
    # The worker's own words are kept, but never as evidence.
    assert "I am done" in state["attempts"][0]["said"]
    assert state["last_verified_milestone"] is None
    results = json.loads((tmp_path / "root/demo/results.json").read_text())
    assert results["demo-1"]["done"] is False


def test_preflight_refuses_a_foreign_identity_before_any_child(tmp_path):
    s = _setup(tmp_path)
    r = s["launch"](env_overrides={"ESTATE_AGENT": "someone-else"})
    assert r.returncode == 1
    assert "identity mismatch" in r.stderr
    record = tmp_path / "pi-record.jsonl"
    assert not record.exists(), "no child may be started when preflight refuses"
    state = json.loads((tmp_path / "root/demo/state.json").read_text())
    assert state["state"] == "failed"
    assert state["blocker"].startswith("preflight:")


def test_preflight_refuses_a_missing_worktree(tmp_path):
    s = _setup(tmp_path)
    r = s["launch"](packet_path=s["packet"](worktree=str(tmp_path / "nope")))
    assert r.returncode == 1
    assert "does not exist" in r.stderr
    assert not (tmp_path / "pi-record.jsonl").exists()


def test_preflight_refuses_a_model_that_is_not_on_the_route(tmp_path):
    s = _setup(tmp_path)
    r = s["launch"](packet_path=s["packet"](model="not_a_model"))
    assert r.returncode == 1
    assert "not on the" in r.stderr
    assert not (tmp_path / "pi-record.jsonl").exists()


def test_preflight_refuses_when_the_claim_is_not_held_by_this_identity(tmp_path):
    s = _setup(tmp_path)
    claims = tmp_path / "claims.json"
    claims.write_text(json.dumps({"claims": []}))
    r = s["launch"]()
    assert r.returncode == 1
    assert "no CLAIM by" in r.stderr
    assert not (tmp_path / "pi-record.jsonl").exists()


def test_preflight_refuses_a_stale_claim(tmp_path):
    s = _setup(tmp_path)
    claims = tmp_path / "claims.json"
    stale = datetime.now(timezone.utc) - timedelta(hours=5)
    claims.write_text(
        json.dumps(
            {
                "claims": [
                    {
                        "issue": 7310,
                        "agent": "pi-delegate-intent",
                        "paths": ["artifact.md"],
                        "heartbeat": stale.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    }
                ]
            }
        )
    )
    r = s["launch"]()
    assert r.returncode == 1
    assert "stale" in r.stderr


def test_the_second_attempt_is_built_from_the_failed_check_not_the_failed_words(
    tmp_path,
):
    s = _setup(tmp_path, writes="other.md", said="MY-PRIVATE-REASONING")
    r = s["launch"]()
    assert r.returncode == 1, r.stdout + r.stderr

    records = [
        json.loads(line)
        for line in (tmp_path / "pi-record.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert len(records) == 2, (
        "the failed attempt is retried once with a changed strategy"
    )
    second = records[1]["prompt"]
    assert "[EMPIRICAL_STATE]" in second
    assert "grep -q DELEGATED artifact.md" in second
    assert "MY-PRIVATE-REASONING" not in second
    # The harness and the route are the caller's choice, and they are kept apart.
    assert "--provider" in records[0]["argv"] and "estate" in records[0]["argv"]
    assert "minimax_m27" in records[0]["argv"]


def test_an_identical_retry_is_refused(tmp_path):
    s = _setup(tmp_path, writes="other.md")
    r = s["launch"](packet_path=s["packet"](strategies=["same", "same"]))
    assert r.returncode == 1
    state = json.loads((tmp_path / "root/demo/state.json").read_text())
    assert "strategy did not change" in state["blocker"]
    assert state["next_recovery"] == "needs-supervisor"


def test_a_repeated_failure_signature_is_escalated(tmp_path):
    s = _setup(tmp_path, writes="other.md")
    r = s["launch"](packet_path=s["packet"](strategies=["one", "two"]))
    assert r.returncode == 1
    state = json.loads((tmp_path / "root/demo/state.json").read_text())
    assert len(state["failure_signatures"]) == 1, "the same failure has one signature"
    assert state["failure_signatures"][0] == state["attempts"][0]["failure_signature"]
    assert state["blocker"] and "needs-supervisor" in state["blocker"]


def test_cancel_refuses_a_pid_it_does_not_own(tmp_path):
    s = _setup(tmp_path)
    root = tmp_path / "root/demo"
    root.mkdir(parents=True)
    (root / "state.json").write_text(
        json.dumps(
            {
                "slug": "demo",
                "state": "running",
                "pid": os.getpid(),
                "run_id": "delegate-demo-1",
            }
        )
    )
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "cancel", "slug=demo"],
        env=s["env"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 1
    assert "not this delegation's child" in r.stderr
    assert os.getpid() > 0
