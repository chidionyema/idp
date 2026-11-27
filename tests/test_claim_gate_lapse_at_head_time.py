"""A lane is judged on whether its claim was live when the work was made, not when the queue got
to it (idp#8629).

Measured 2026-11-27: claude-code stamped its claims, pushed, opened three pull requests and
stopped, as AGENTS.md section 2 requires. The Greenlane adopted the lanes at 08:21:38Z and
judged them in CI at 08:40Z, where the gate is read-only (no renewal): all three went RED on
"heartbeat is 24m old (lapse is 15m): re-stamp". So obeying "open the PR, then STOP" turned
every lane whose queue ran longer than 15 minutes RED. The work had been made under a live claim.

The lapse frees files for OTHER agents (AGENTS.md section 5.4), and that protection stays: a
rival's newer claim still refuses, and so does another agent's lapsed one. A head authored after
the holder's own claim had lapsed still refuses. Only the queue's wait no longer counts against
the holder.

    python3 -m pytest -q tests/test_claim_gate_lapse_at_head_time.py
    python3 tests/test_claim_gate_lapse_at_head_time.py --optimus
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import subprocess
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT = Path(
    os.environ.get("CLAIM_GATE_SCRIPT")
    or Path(__file__).resolve().parent.parent / "bin" / "claim-gate"
)
NOW = datetime(2026, 11, 27, 8, 40, tzinfo=timezone.utc)
CONTRACT = (
    "SHIP-CONTRACT\n"
    "accept: GET https://voice.example.test/health expect 200 within 30m\n"
    "optimus: claims.ship_contract_enforced baseline=UNKNOWN target=1\n"
    "failure-classes: gate-blocks-its-own-repair\n"
    "debug-pack: DBG-001"
)
MSG = "fix(voice): a thing\n\nClaim: Mumchimp/crew#12\nAgent: idp-60\n"


def _gate():
    loader = importlib.machinery.SourceFileLoader("claim_gate_lapse", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    mod.RENEW = None  # CI: the gate only reads
    return mod


def _stamp(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def _claim(agent="idp-60", at=NOW - timedelta(minutes=24)):
    return (
        f"CLAIM agent={agent} paths=bin/voice-*,tests/test_voice* "
        f"heartbeat={_stamp(at)}"
    )


def _issue(*claims):
    return {"state": "open", "labels": [], "body": CONTRACT}, [
        {"body": c} for c in claims
    ]


@contextmanager
def _repo(authored: datetime, msg: str = MSG):
    """A real repository: base, then a head authored at `authored` carrying `msg`."""
    with tempfile.TemporaryDirectory() as d:
        env = dict(
            os.environ,
            GIT_CONFIG_GLOBAL="/dev/null",
            GIT_CONFIG_NOSYSTEM="1",
            GIT_AUTHOR_NAME="a",
            GIT_AUTHOR_EMAIL="a@example.test",
            GIT_COMMITTER_NAME="a",
            GIT_COMMITTER_EMAIL="a@example.test",
        )

        def run(*a, **kw):
            return subprocess.run(
                ["git", *a],
                cwd=d,
                env={**env, **kw},
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

        run("init", "-q", "-b", "main")
        Path(d, "README").write_text("base\n")
        run("add", "-A")
        run("commit", "-q", "-m", "base")
        base = run("rev-parse", "HEAD")
        Path(d, "bin").mkdir()
        Path(d, "bin", "voice-doctor").write_text("#!/bin/sh\n")
        run("add", "-A")
        # the committer date is when the queue rebased it; only the author date is the work
        run(
            "commit",
            "-q",
            "-m",
            msg,
            GIT_AUTHOR_DATE=authored.isoformat(),
            GIT_COMMITTER_DATE=NOW.isoformat(),
        )
        head = run("rev-parse", "HEAD")
        old = os.getcwd()
        os.chdir(d)
        try:
            yield base, head
        finally:
            os.chdir(old)


def _judge(issue, authored, msg=MSG):
    g = _gate()
    with _repo(authored, msg) as (base, head):
        return g.judge(
            base, head, "Mumchimp/idp", lambda r, n: issue, NOW, "", "idp-60"
        )


def test_work_made_under_a_live_claim_lands_after_a_long_queue():
    # the measured case: claim at 08:16, head authored at 08:17, judged in CI at 08:40
    out = _judge(_issue(_claim()), NOW - timedelta(minutes=23))
    assert out == [], out


def test_work_authored_after_the_holders_claim_lapsed_still_refuses():
    out = _judge(_issue(_claim()), NOW - timedelta(minutes=2))
    assert any("re-stamp" in p for p in out), out


def test_another_agents_lapsed_claim_still_refuses():
    msg = MSG.replace("Agent: idp-60", "Agent: idp-77")
    out = _judge(_issue(_claim()), NOW - timedelta(minutes=23), msg)
    assert any("has no live CLAIM" in p for p in out), out


def test_a_rivals_newer_claim_still_refuses():
    rival = _claim(agent="idp-77", at=NOW - timedelta(minutes=5))
    out = _judge(_issue(_claim(), rival), NOW - timedelta(minutes=23))
    assert any("claimed by idp-77" in p for p in out), out


def test_a_live_claim_still_passes():
    out = _judge(
        _issue(_claim(at=NOW - timedelta(minutes=5))), NOW - timedelta(minutes=4)
    )
    assert out == [], out


if __name__ == "__main__":
    import sys

    if "--optimus" not in sys.argv:
        sys.exit("usage: python3 tests/test_claim_gate_lapse_at_head_time.py --optimus")
    try:
        out = _judge(_issue(_claim()), NOW - timedelta(minutes=23))
    except Exception as e:  # noqa: BLE001 -- a crash is a refusal, never a pass
        out = [repr(e)]
    print(f"optimus.claims.queue_lapse_refusals={1 if out else 0}")
