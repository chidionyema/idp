"""The Greenlane spends its one serial slot on work that can land, and a red verdict names its cause.

Founder, 2026-11-06: the Greenlane should be "a world class product that reduces friction for
agents, enabling them to do their best work safely and to the estate's standards".

Measured on refs/greenlane/state that day (200 batch verdicts, 8.4 days): 127 landed, 73 did not,
and those 73 are cycles of the ONE serial slot every other lane waits behind. 30 were a lone red
lane re-tested at the front of the line, 10 bisections re-discovered a lane the state already
knew was red on its own, and the reason every agent read was `ci-success failure <url>` -- the
aggregator's name, not the cause.

Two contracts, each falsifiable:

1. CYCLES. On the engine's own chaos model (greenlane/simulate.py, 500 lanes, the seeds the BDD
   suite uses plus more), the engine drains the lanes in materially fewer ticks and with
   materially fewer candidates than the engine before this change, and every invariant the BDD
   suite asserts still holds on every seed. The baseline numbers are the pre-change engine's,
   measured on the same seeds and pinned here; a regression past them fails.
2. CAUSE. A red required check carries the failing job, its failing step and the most specific
   failure line of that job's log; the lane's status links to the failing job, and keeps the
   words inside GitHub's 140 characters. A cause that cannot be read leaves the old reason.
"""

from __future__ import annotations

import statistics
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from greenlane import github as G  # noqa: E402
from greenlane.engine import RED  # noqa: E402
from greenlane.simulate import run  # noqa: E402

SEEDS = tuple(range(8))
# The engine before 2026-11-06 (main 76ab9cc), the same 8 seeds x 500 lanes:
BASELINE_TICKS = 1320.6
BASELINE_CANDIDATES = 425.6


def _invariants(r) -> None:
    assert r.main_ever_red == 0, r
    assert r.broken_lanes_landed == 0, r
    assert r.direct_push_succeeded == 0, r
    assert r.hand_prs_refused == r.hand_prs, r
    assert r.open_red_pr_observations == 0, r
    assert r.landed + r.red + r.conflict + r.deleted_by_agents == r.lanes, r
    assert r.still_open == 0, r
    assert r.work_lost == 0, r
    assert r.good_lanes_not_landed == 0, r


@pytest.fixture(scope="module")
def reports():
    return [run(lanes=500, seed=s) for s in SEEDS]


def test_every_invariant_holds_on_every_seed(reports):
    for r in reports:
        _invariants(r)


def test_the_lanes_drain_in_fewer_ticks_and_fewer_candidates(reports):
    ticks = statistics.mean(r.ticks for r in reports)
    cands = statistics.mean(r.candidates for r in reports)
    # at least 15% fewer of each: the measured gain is ~23% ticks and ~27% candidates
    assert ticks <= BASELINE_TICKS * 0.85, (ticks, BASELINE_TICKS)
    assert cands <= BASELINE_CANDIDATES * 0.85, (cands, BASELINE_CANDIDATES)


def test_the_restart_proof_still_holds():
    a = run(lanes=500, seed=0)
    b = run(lanes=500, seed=0, reload_state=True)
    assert a.__dict__ == b.__dict__


# -- cause ---------------------------------------------------------------------------------

JOB = "https://github.com/o/idp/actions/runs/42263152128/job/{}"
LOG = """2026-11-06T17:40:05.1Z ok    fast rungs
2026-11-06T17:40:05.3133803Z FAIL  registry the Estate Capability Registry is not true (rc=1)  (3s)
2026-11-06T17:40:05.3161403Z       FAIL    registry-gate  completeness: dependencies: measured coverage fell from 721/1048 to 725/1054 (coverage may only improve)
2026-11-06T17:40:05.3315522Z FAIL  idp-ci
2026-11-06T17:40:06.6222020Z ##[error]Process completed with exit code 1.
"""


class Recorded(G.GitHubBackend):
    def __init__(self, table: dict, logs: dict):
        super().__init__("o/idp", ["fast-gate / fast-gate", "ci-success"])
        self.table, self.logs, self.reads = table, logs, []
        self.statuses: list[dict] = []

    def gh(self, path, method="GET", fields=None):
        self.reads.append(path)
        return self.table.get(path.partition("?")[0])

    def _status(self, sha, fields):
        self.statuses.append(fields)


@pytest.fixture
def red_world(monkeypatch):
    calls = []

    def fake_run(*args, check=True, input=None, env=None):
        calls.append(args)
        job = args[2].split("/")[-2]
        if job not in logs:
            raise RuntimeError("gh api: rc=1 HTTP 404")
        return logs[job]

    logs = {"128048562627": LOG}
    monkeypatch.setattr(G, "_run", fake_run)
    table = {
        "commits/tip/check-runs": {
            "check_runs": [
                {
                    "name": "fast-gate / fast-gate",
                    "status": "completed",
                    "conclusion": "success",
                    "id": 1,
                    "html_url": JOB.format(1),
                },
                {
                    "name": "ci-success",
                    "status": "completed",
                    "conclusion": "failure",
                    "id": 2,
                    "html_url": JOB.format("128050314789"),
                },
            ]
        },
        "actions/runs/42263152128/jobs": {
            "jobs": [
                {
                    "id": 128048562627,
                    "name": "offline-gate",
                    "conclusion": "failure",
                    "html_url": JOB.format("128048562627"),
                    "steps": [
                        {"name": "tools", "conclusion": "success"},
                        {"name": "Run bin/idp-ci", "conclusion": "failure"},
                    ],
                },
                {
                    "id": 128050314789,
                    "name": "ci-success",
                    "conclusion": "failure",
                    "steps": [
                        {
                            "name": "every required job is success",
                            "conclusion": "failure",
                        }
                    ],
                },
                {"id": 3, "name": "bdd", "conclusion": "success", "steps": []},
            ]
        },
    }
    return Recorded(table, logs), calls


def test_a_red_verdict_names_the_failing_job_step_and_line(red_world):
    b, _ = red_world
    verdict, reason = b.checks("tip")
    assert verdict == "red"
    assert reason.startswith("ci-success failure " + JOB.format("128050314789"))
    assert "offline-gate > Run bin/idp-ci: " in reason
    assert "registry-gate  completeness: dependencies: measured coverage fell" in reason
    assert "every required job" not in reason, "the aggregator is not its own cause"


def test_the_cause_is_read_once_per_run_and_never_for_main(red_world):
    b, calls = red_world
    b.checks("tip")
    b.checks("tip")
    assert sum(1 for r in b.reads if r.startswith("actions/runs/")) == 1
    assert len(calls) == 1, "one log read for one failing job, cached"
    b.reads.clear()
    assert b.main_red("tip") is True
    assert not any(r.startswith("actions/") for r in b.reads), (
        "main_red is the verdict only"
    )


def test_an_unreadable_cause_leaves_the_old_reason(red_world):
    b, _ = red_world
    b.table["actions/runs/42263152128/jobs"] = None
    assert b.checks("tip") == (
        "red",
        "ci-success failure " + JOB.format("128050314789"),
    )


def test_a_missing_log_still_names_the_job_and_step(red_world):
    b, _ = red_world
    b.logs.clear()
    _, reason = b.checks("tip")
    assert reason.endswith(
        "-- offline-gate > Run bin/idp-ci " + JOB.format("128048562627")
    ), reason


def test_the_lane_status_links_the_failing_job_and_keeps_the_words(red_world):
    b, _ = red_world
    _, reason = b.checks("tip")
    b.report("lane/x", "h", RED, reason)
    f = b.statuses[-1]
    assert f["target_url"] == JOB.format("128048562627"), "one click to the failing log"
    assert "http" not in f["description"]
    assert f["description"].startswith(
        "ci-success failure -- offline-gate > Run bin/idp-ci"
    )
    assert len(f["description"]) <= 140


def test_a_reason_without_a_job_link_keeps_the_run_link(red_world):
    b, _ = red_world
    b.run_url = "https://github.com/o/idp/actions/runs/7"
    b.report("lane/x", "h", RED, "no live claim: o/idp#1 is not open")
    assert b.statuses[-1]["target_url"] == b.run_url
    assert b.statuses[-1]["description"] == "no live claim: o/idp#1 is not open"
