"""The Greenlane stamps a held lane's claim faster than the claim gate lapses it.

bin/claim-gate lapses a claim 15 minutes after its heartbeat (founder SEV-0, 2026-11-25). The
Greenlane kept stamping every 45-50 minutes under a comment that still said the gate's limit was
two hours, so a claim that was waiting in the queue lapsed for most of every wait and a rival
could take its paths. These tests read the gate's own number and fail if the cadence drifts again.
"""

# Pytest assertions are test checks, never runtime input validation.
# ruff: noqa: S101
from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from greenlane import engine as E  # noqa: E402
from greenlane import github as G  # noqa: E402


def _gate_max_age_minutes() -> int:
    source = (ROOT / "bin" / "claim-gate").read_text()
    hit = re.search(r"^MAX_AGE\s*=\s*timedelta\(minutes=(\d+)\)", source, re.M)
    assert hit, (
        "bin/claim-gate no longer declares MAX_AGE in minutes: update this reader"
    )
    return int(hit.group(1))


def test_the_engine_mirrors_the_gates_lapse():
    assert E.CLAIM_LAPSE_MIN == _gate_max_age_minutes(), (
        "the gate's MAX_AGE moved; CLAIM_LAPSE_MIN in greenlane/engine.py must move with it"
    )


def test_the_cadence_leaves_room_for_a_late_tick():
    lapse = _gate_max_age_minutes()
    assert E.HEARTBEAT_EVERY_MIN * 2 <= lapse, (E.HEARTBEAT_EVERY_MIN, lapse)
    assert (
        timedelta(minutes=0) < G.STAMP_AFTER < timedelta(minutes=E.HEARTBEAT_EVERY_MIN)
    )


class Stub(G.GitHubBackend):
    def __init__(self, comments, patch_ok=True):
        self.repo = "Mumchimp/idp"
        self.app_login = "idp-app[bot]"
        self.comments = comments
        self.patch_ok = patch_ok
        self.posted: list[tuple[str, str]] = []
        self.patched: list[tuple[str, str]] = []

    def gh(self, path, method="GET", fields=None):
        body = (fields or {}).get("body", "")
        if method == "POST":
            self.posted.append((path, body))
            return {}
        if method == "PATCH":
            if not self.patch_ok:
                raise RuntimeError("403")
            self.patched.append((path, body))
            return {"id": 1}
        if path == "issues/5755":
            return {"state": "open"}
        if path == "issues/5755/comments?per_page=100":
            return self.comments
        return None

    def git(self, *args, check=True):
        if args[:2] == ("merge-base", "origin/main"):
            return "base"
        if args[:2] == ("log", "--format=%B"):
            return "fix: x\n\nClaim: Mumchimp/idp#5755\nAgent: opencode\n"
        return ""


def _stamp(minutes_old: int, machine: bool, cid: int = 7) -> dict:
    hb = datetime.now(timezone.utc) - timedelta(minutes=minutes_old)
    text = f"CLAIM agent=opencode paths=bin/x heartbeat={hb.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    if machine:
        text += f"\n\n{G.MACHINE_STAMP}: lane `lane/face` is held"
    return {"id": cid, "body": text}


def test_a_claim_ten_minutes_old_is_restamped_before_the_gate_lapses_it():
    b = Stub([_stamp(10, machine=False)])
    b.heartbeat("lane/face", "head1")
    assert len(b.posted) == 1, (
        "a 10 minute old claim is 5 minutes from lapse and was left alone"
    )


def test_the_machines_own_previous_stamp_is_edited_not_piled_up():
    b = Stub([_stamp(10, machine=False), _stamp(10, machine=True, cid=9)])
    b.heartbeat("lane/face", "head1")
    assert b.posted == []
    assert [p for p, _ in b.patched] == ["issues/comments/9"]
    assert "CLAIM agent=opencode paths=bin/x heartbeat=" in b.patched[0][1]


def test_a_stamp_over_a_human_claim_is_a_new_comment_not_an_edit_of_theirs():
    b = Stub([_stamp(10, machine=False)])
    b.heartbeat("lane/face", "head1")
    assert b.patched == []
    assert len(b.posted) == 1


def test_a_refused_edit_falls_back_to_a_new_comment_so_the_stamp_is_never_lost():
    b = Stub([_stamp(10, machine=True)], patch_ok=False)
    b.heartbeat("lane/face", "head1")
    assert len(b.posted) == 1
