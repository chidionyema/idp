"""The door contract for bin/debug-packs, and the falsifier that each exit code can be reached.

A door's exit codes are its API: 0 ok, 2 BLIND (it could not look), 3 none (it looked and the
catalogue holds nothing matching), 4 refused (the catalogue violates its own contract). The
distinction between 2 and 3 is the whole point -- "I could not read it" must never be reported
as "there is nothing there" (AGENTS.md section 3a).

Every exit code below is asserted by RUNNING the shipped door, not by describing it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOOR = REPO / "bin" / "debug-packs"

EXIT_OK = 0
EXIT_BLIND = 2
EXIT_NONE = 3
EXIT_REFUSED = 4


def run(*args: str, catalogue: Path | None = None) -> tuple[int, str]:
    env = {**os.environ}
    if catalogue is not None:
        env["ESTATE_DEBUG_PACKS"] = str(catalogue)
    p = subprocess.run(
        [sys.executable, str(DOOR), *args],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    return p.returncode, p.stdout + p.stderr


def test_the_door_is_executable():
    assert DOOR.exists(), f"{DOOR} is missing, so nothing was graded"
    assert os.access(DOOR, os.X_OK), f"{DOOR} is not executable"


def test_check_passes_on_the_shipped_catalogue():
    rc, out = run("--check")
    assert rc == EXIT_OK, (
        f"--check must pass on the shipped catalogue, got {rc}:\n{out}"
    )
    assert out.startswith("ok ") and "packs" in out, out


def test_a_missing_catalogue_is_blind_not_none(tmp_path):
    rc, out = run("--check", catalogue=tmp_path / "does-not-exist.json")
    assert rc == EXIT_BLIND, f"an unreadable catalogue must be BLIND, got {rc}: {out}"
    assert "BLIND" in out, out


def test_an_unparseable_catalogue_is_blind_not_none(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text("{ this is not json ")
    rc, out = run("--check", catalogue=broken)
    assert rc == EXIT_BLIND, f"a malformed catalogue must be BLIND, got {rc}: {out}"
    assert "BLIND" in out, out


def test_an_unknown_pack_is_none_not_blind():
    rc, out = run("--show", "DBG-DOES-NOT-EXIST")
    assert rc == EXIT_NONE, (
        f"looking successfully and finding nothing is exit 3, got {rc}: {out}"
    )


def test_a_pack_claiming_fixed_on_prose_is_refused(tmp_path):
    """A gate that cannot fail is not a gate: the contract must reject a known-bad pack."""
    bad = tmp_path / "packs.json"
    bad.write_text(
        json.dumps(
            {
                "version": 1,
                "packs": [
                    {
                        "id": "DBG-001",
                        "title": "t",
                        "symptom": "s",
                        "cause": "c",
                        "falsifier": "we keep an eye on it",
                        "remedy": "r",
                        "status": "fixed",
                        "law": "AGENTS.md section 3",
                    }
                ],
            }
        )
    )
    rc, out = run("--check", catalogue=bad)
    assert rc == EXIT_REFUSED, (
        f"a prose falsifier under status=fixed must be refused, got {rc}: {out}"
    )
    assert "DBG-001" in out, out


def test_a_pack_missing_a_required_field_is_refused(tmp_path):
    bad = tmp_path / "packs.json"
    bad.write_text(
        json.dumps({"version": 1, "packs": [{"id": "DBG-001", "title": "t"}]})
    )
    rc, out = run("--check", catalogue=bad)
    assert rc == EXIT_REFUSED, f"an incomplete pack must be refused, got {rc}: {out}"
    assert "missing" in out, out


def test_search_finds_a_shipped_pack():
    rc, out = run("--search", "claim")
    assert rc == EXIT_OK, out
    assert "DBG-035" in out, f"the claim-parse pack must be searchable:\n{out}"


def test_json_output_round_trips():
    rc, out = run("--json")
    assert rc == EXIT_OK, out
    data = json.loads(out)
    assert isinstance(data["packs"], list) and data["packs"], (
        "no packs in --json output"
    )
