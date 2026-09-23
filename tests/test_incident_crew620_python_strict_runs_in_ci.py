"""crew#620 CP4: the estate Python standard runs in CI as the same file every Mac runs as a
commit hook (founder 2026-08-29: "and python tooling what we do have?" -> "platform wide").
A push from a machine without the hook is caught here, and the two can never disagree.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FAST = ROOT / ".github" / "workflows" / "fast-gate.yml"


def _steps() -> list[dict]:
    return yaml.safe_load(FAST.read_text())["jobs"]["fast-gate"]["steps"]


def test_fast_gate_checks_out_the_estate_hooks_and_runs_python_strict() -> None:
    steps = _steps()
    estate = [
        s for s in steps if s.get("with", {}).get("repository") == "chidionyema/estate"
    ]
    assert estate, (
        "fast-gate must check out chidionyema/estate, the one copy of the gate"
    )
    assert estate[0]["with"]["path"] == ".estate-hooks"
    runs = [s.get("run", "") for s in steps]
    assert any(
        "PYTHON_STRICT_RANGE=" in r
        and ".estate-hooks/guards/hooks/python-strict-default" in r
        for r in runs
    )


def test_checkout_has_full_history_so_the_range_base_exists() -> None:
    first = _steps()[0]
    assert first["with"]["fetch-depth"] == 0


def test_the_gate_is_not_copied_into_this_repo() -> None:
    """One copy (LAW 43): a second python-strict under bin/ would drift from the hook."""
    assert not (ROOT / "bin" / "idp-python-strict").exists()
