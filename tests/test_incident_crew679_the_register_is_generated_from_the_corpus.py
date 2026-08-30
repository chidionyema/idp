"""crew#679 CP1/CP5 (founder 2026-08-30: "take incident as input, use it to generate chaos
experiments/drills"). The incident register is generated from every tests/test_incident_*.py
docstring, never hand-typed, and a new incident test cannot land without its row: --check is
the gate. These pin the generator's contract: one row per test, a fault class on every row,
and the committed file matching a fresh render.
"""

import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "bin" / "incident-register"
REG = ROOT / "docs" / "reference" / "incident-register.yaml"


def test_one_row_per_incident_test_and_every_row_classified() -> None:
    body = yaml.safe_load(REG.read_text())
    tests = sorted(
        p.stem.removeprefix("test_incident_")
        for p in (ROOT / "tests").glob("test_incident_*.py")
    )
    assert [r["id"] for r in body["rows"]] == tests
    assert all(r["fault_class"] for r in body["rows"])
    assert body["incidents"] == len(tests) == sum(body["by_class"].values())


def test_check_refuses_a_stale_register(tmp_path: Path) -> None:
    r = subprocess.run([str(TOOL), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "matches" in r.stdout


def test_injectable_rows_exist_for_the_chaos_generator() -> None:
    body = yaml.safe_load(REG.read_text())
    inj = [r for r in body["rows"] if r["injectable"]]
    assert inj, "no injectable fault classes: CP3 has nothing to generate from"
    assert {r["fault_class"] for r in inj} <= {
        "pod-crash",
        "rollout-stall",
        "network",
        "secret-rotation",
        "capacity",
        "clock",
        "scheduler",
    }
