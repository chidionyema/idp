"""ci-success is the one check main requires for ci.yml, so it must judge every job in ci.yml.

Measured 2026-10-14: offline-gate was absent from ci-success's `needs`. On the Greenlane candidate
a5ef26fae (PR #6191) offline-gate was `failure`, ci-success `success`, and main fast-forwarded red.
A job added to ci.yml and not to `needs` is a gate nothing enforces; this test refuses it.
"""

from pathlib import Path

import yaml

CI = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"

# Jobs that run only after a commit has landed on main. They cannot block a landing that has
# already happened, so judging them in ci-success would only make main's own run red.
AFTER_LANDING = {"estate-graph-sync"}


def jobs():
    return yaml.safe_load(CI.read_text())["jobs"]


def test_ci_success_needs_every_job_in_the_workflow():
    all_jobs = jobs()
    needs = set(all_jobs["ci-success"]["needs"])
    missing = sorted(set(all_jobs) - needs - AFTER_LANDING - {"ci-success"})
    assert not missing, f"ci-success does not judge {missing}: add them to its needs"


def test_after_landing_jobs_only_run_after_landing():
    all_jobs = jobs()
    for name in AFTER_LANDING:
        cond = str(all_jobs[name].get("if", ""))
        assert "refs/heads/main" in cond and "push" in cond, (
            f"{name} runs before landing: {cond!r}"
        )


def test_the_loop_judges_needs_not_a_second_list():
    steps = jobs()["ci-success"]["steps"]
    script = "\n".join(str(s.get("run", "")) for s in steps)
    assert "keys[]" in script, (
        "ci-success must iterate the keys of needs, not a hand-written list"
    )
