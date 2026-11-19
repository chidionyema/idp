"""idp#8304: the pre-push check runs in the cloud door, so no agent needs local tools or a skip.

Each assertion is a property the door must keep; every one fails on main, where the door does
not exist.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOOR = ROOT / ".github" / "workflows" / "submit-gate.yml"


def _flow() -> dict:
    return yaml.safe_load(DOOR.read_text())


def test_the_door_opens_on_submit_branches_only():
    on = _flow().get("on", _flow().get(True))
    assert on == {"push": {"branches": ["submit/**"]}}


def test_the_check_is_the_one_ci_runs_not_a_copy():
    gate = _flow()["jobs"]["gate"]
    assert gate["uses"] == "./.github/workflows/fast-gate.yml"


def test_only_a_green_commit_reaches_a_lane():
    jobs = _flow()["jobs"]
    assert jobs["promote"]["needs"] == "gate"
    script = "\n".join(s.get("run", "") for s in jobs["promote"]["steps"])
    assert "$SHA:refs/heads/lane/$name" in script, (
        "the exact checked commit is promoted"
    )
    assert "--no-verify" not in script, "the door itself never skips a check"


def test_a_red_commit_is_told_to_its_owner():
    owner = _flow()["jobs"]["tell-the-owner"]
    assert owner["needs"] == "gate" and owner["if"] == "failure()"
    script = "\n".join(s.get("run", "") for s in owner["steps"])
    assert "Claim:" in script and "/comments" in script


def test_the_caller_grants_what_the_reusable_gate_asks():
    perms = _flow()["permissions"]
    assert perms.get("pull-requests") == "read" and perms.get("contents") == "read"
