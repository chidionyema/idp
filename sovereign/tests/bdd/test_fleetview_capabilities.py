"""FleetView capability badge (item #5): sessions.py's `_engine_capabilities()`, graded the same
way test_fleetview_notes.py grades notes.py -- a plain unit suite, no feature file.

`_engine_capabilities()` reads AGENTS.md's own ```toml [capabilities] block through
`sovereign/policy.py` (crew#219 R38) -- never a second, hand-kept copy of that table. This suite
proves it returns the real `engine` row, and degrades to None (never a fabricated list) when the
policy file cannot be read or parsed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SESSIONS_MODULE = (
    REPO / "backstage" / "plugins" / "fleetview-backend" / "src" / "sessions.py"
)


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def sessions_mod():
    return _load(SESSIONS_MODULE, "fleetview_sessions_under_test")


def test_engine_capabilities_matches_agents_md_policy(sessions_mod):
    from sovereign import policy as policy_mod

    expected = list(policy_mod.load().capabilities.get("engine", []))
    assert sessions_mod._engine_capabilities() == expected
    assert expected, (
        "AGENTS.md's [capabilities] block must still define an 'engine' row"
    )


def test_a_policy_load_failure_degrades_to_none_not_a_fabricated_list(
    sessions_mod, monkeypatch
):
    from sovereign import policy as policy_mod

    def broken_load():
        raise policy_mod.PolicyError("AGENTS.md missing on this host")

    monkeypatch.setattr(policy_mod, "load", broken_load)
    assert sessions_mod._engine_capabilities() is None


def test_sovereign_rows_carry_the_engine_class_and_capabilities(sessions_mod):
    row = {
        "session_id": "sb-1",
        "task": "do a thing",
        "state": "running",
        "repo": None,
        "step": 1,
        "updated_at": None,
    }
    session = sessions_mod.session_from_engine_row(row)
    assert session["capability_class"] == "engine"
    assert session["capabilities"] == sessions_mod._engine_capabilities()
    assert session["capabilities"], (
        "engine sessions must carry a real, non-empty capability list"
    )
