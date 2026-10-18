"""`jev.decide` is the door every agent has to the decision layer. It has to actually open.

WHY. ADR 0030 says every decision point calls the one layer, and `sovereign/policy.py`'s [jev]
block sets `force_on_decisions = true` -- but an agent cannot import `mcp/plugins/jev.py`, because
the execution rule is intents-only. Without an intent the layer was callable from exactly three
hard-coded binaries, one of which nothing invoked. These tests keep the door real:

  1. the intent exists, declares the args it documents, and fits a door it can be run through;
  2. its command does NOT quote `{{arg}}` itself -- the executor shell-quotes every substitution,
     so a second layer of quoting turned `estate's` into an unterminated string and the step died
     on line 4 (measured 2026-10-18, first invocation of this intent);
  3. running the helper records the decision in the database (a consultation that leaves no row is
     indistinguishable from a layer that was never asked).
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
INTENT = REPO / "platform" / "estate" / "intents" / "jev.decide.yaml"
HELPER = REPO / "platform" / "estate" / "libexec" / "jev-decide.py"


def _intent() -> dict:
    return yaml.safe_load(INTENT.read_text(encoding="utf-8"))


def test_the_intent_exists_and_names_its_arguments() -> None:
    spec = _intent()
    assert spec["name"] == "jev.decide"
    for arg in ("question", "id", "kind", "layer", "context"):
        assert arg in spec["args"], f"jev.decide must document the {arg} argument"
    assert spec["args"]["question"].get("required") is True
    # A call is one HTTP round trip bounded by policy [jev] timeout_ms (2000); the intent must
    # declare a door big enough for that, like every other intent that shells out.
    assert int(spec.get("door_s", 0)) >= 10


def test_the_intent_does_not_quote_substituted_arguments() -> None:
    """The executor shell-quotes `{{arg}}`; quoting it again breaks on any apostrophe."""
    commands = " ".join(step["cmd"] for step in _intent()["steps"])
    assert '"{{' not in commands and "'{{" not in commands, (
        "jev.decide quotes {{arg}} inside its own command; the executor already shell-quotes "
        "every substitution, so an apostrophe in the question becomes an unterminated string"
    )
    for arg in ("question", "id", "kind", "layer", "context"):
        assert "{{" + arg + "}}" in commands


def test_the_helper_records_the_decision(tmp_path: Path) -> None:
    db = tmp_path / "estate.db"
    out = subprocess.run(  # noqa: S603 -- argv is fixed; runner is this test's own interpreter
        [
            sys.executable,
            str(HELPER),
            "--repo",
            str(REPO),
            "--layer",
            "agent",
            "--id",
            "test:intent-door",
            "--question",
            "Is the decision layer reachable from this intent's helper?",
        ],
        env={"ESTATE_DB": str(db), "PATH": "/usr/bin:/bin", "HOME": str(Path.home())},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert out.returncode == 0, out.stderr
    assert "jev.decide[" in out.stdout

    rows = (
        sqlite3.connect(db)
        .execute("SELECT layer, decision_id, escalated FROM jev_decisions")
        .fetchall()
    )
    assert rows == [("agent", "test:intent-door", 1)], (
        "the intent's helper must record its decision; a consultation with no row is invisible"
    )
