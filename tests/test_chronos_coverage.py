"""Chronos loop map: every recurring declaration is CLOSED (graded for delivery) or OPEN.

Founder, 2026-11-13: "map disconnects and track all these loops across estate". The map is a
join of two existing censuses (bin/idp-one-scheduler, scheduler/schedule.yml) with the Chronos
obligations, and its floor only rises.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "bin" / "idp-estate-clocks"


def _mod():
    loader = importlib.machinery.SourceFileLoader("idp_estate_clocks_cov", str(TOOL))
    spec = importlib.util.spec_from_loader("idp_estate_clocks_cov", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


CENSUS = [
    {
        "id": ".github/workflows/a.yml",
        "kind": "GitHub Actions cron",
        "home": "github-cron",
    },
    {
        "id": ".github/workflows/b.yml",
        "kind": "GitHub Actions cron",
        "home": "github-cron",
    },
    {
        "id": "launchd/ai.estate.x.plist.tmpl",
        "kind": "launchd job on the laptop",
        "home": "laptop",
    },
    {"id": "dagster:ai.estate.y", "kind": "Dagster schedule", "home": "dagster@mac"},
]


def test_a_graded_workflow_is_closed_and_everything_else_is_open():
    cov = _mod().coverage({"obligations": [{"id": "a", "workflow": "a.yml"}]}, CENSUS)
    loops = {r["id"]: r["loop"] for r in cov["loops"]}
    assert loops[".github/workflows/a.yml"] == "CLOSED"
    assert [k for k, v in loops.items() if v == "OPEN"] == [
        ".github/workflows/b.yml",
        "launchd/ai.estate.x.plist.tmpl",
        "dagster:ai.estate.y",
    ]
    assert (cov["declared"], cov["closed"], cov["open"]) == (4, 1, 3)
    assert cov["by_home"]["github-cron"] == {"declared": 2, "closed": 1}


def test_a_retired_obligation_does_not_close_its_loop():
    cov = _mod().coverage(
        {"obligations": [{"id": "a", "workflow": "a.yml", "state": "retired"}]}, CENSUS
    )
    assert cov["closed"] == 0


def test_closing_fewer_loops_than_the_floor_is_below_it():
    manifest = {"coverage_floor": 2, "obligations": [{"id": "a", "workflow": "a.yml"}]}
    assert _mod().coverage(manifest, CENSUS)["below_floor"] is True
    manifest["obligations"].append({"id": "b", "workflow": "b.yml"})
    assert _mod().coverage(manifest, CENSUS)["below_floor"] is False


def test_the_committed_registry_carries_a_floor_and_the_tree_meets_it():
    reg = json.loads((ROOT / "legions" / "estate-clocks.json").read_text())
    assert isinstance(reg.get("coverage_floor"), int) and reg["coverage_floor"] >= 6
    out = subprocess.run(
        [sys.executable, str(TOOL), "--coverage", "--json", "--gate"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert out.returncode == 0, out.stderr
    cov = json.loads(out.stdout)
    assert cov["closed"] >= reg["coverage_floor"]
    assert cov["declared"] > cov["closed"]


def test_an_unreadable_census_is_blind_not_an_empty_map(tmp_path):
    mod = _mod()
    try:
        mod._census(tmp_path)
    except mod.RegistryBlind:
        return
    raise AssertionError(
        "a missing census must raise RegistryBlind, not return an empty map"
    )
