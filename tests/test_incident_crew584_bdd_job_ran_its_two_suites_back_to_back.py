"""crew#584, 2026-08-28: ci.yml's bdd job ran the acceptance suite (54 s) and the root pytest
suite (57 s) one after the other on a single runner -- 2m13s on run 33203670180 -- when the
platform's own matrix runs them side by side. The fix is GitHub's matrix, not a script: the job
keeps its id, each suite step is gated on its own matrix leg, and the wall-clock is the slower
suite plus setup instead of the sum.

The guard: the bdd job declares a matrix with both legs, every pytest step is gated on exactly one
leg, and the two legs each own at least one pytest step -- so nobody can quietly collapse it back
into one serial job, or gate both suites onto the same leg (which is the serial job with extra
runner time).
"""
from pathlib import Path

import yaml

WF = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"


def _bdd():
    return yaml.safe_load(WF.read_text())["jobs"]["bdd"]


def test_the_bdd_job_is_a_matrix_of_both_suites():
    job = _bdd()
    legs = job["strategy"]["matrix"]["suite"]
    assert sorted(legs) == ["acceptance", "tests"], legs
    assert job["strategy"]["fail-fast"] is False, "one red suite must not cancel the other's verdict"


def test_every_pytest_step_runs_on_exactly_one_leg_and_every_leg_has_one():
    job = _bdd()
    legs = set(job["strategy"]["matrix"]["suite"])
    owned = {leg: [] for leg in legs}
    for step in job["steps"]:
        if "pytest" not in step.get("run", ""):
            continue
        cond = step.get("if", "")
        gated = [leg for leg in legs if f"matrix.suite == '{leg}'" in cond]
        assert len(gated) == 1, f"{step['name']!r} must be gated on one matrix leg, got {cond!r}"
        owned[gated[0]].append(step["name"])
    for leg, names in owned.items():
        assert names, f"matrix leg {leg!r} runs no suite -- it is a paid-for idle runner"
