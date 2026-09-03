"""crew#539 (2026-08-28 00:40Z, measured by 09cd04a6 from run/dagster/schedules/schedules.db).

24 scheduler jobs were skipping every tick with "circuit open after 3 failures; run it by hand
to reset" — com.estate.costsentinel since 2026-08-25 02:30, tripped on exit 1 before ok_exit [1]
landed. The breaker counted failures of a row that no longer existed and never re-closed, so
every fix that landed after a trip stayed dark until a person launched the job. Rules:
a run carries the spec_hash of the row it executed; only failures under the current hash open
the breaker; a row graded `runs_on: retire` gets no job and no schedule.
"""

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scheduler"))
JOBS = yaml.safe_load((ROOT / "scheduler" / "schedule.yml").read_text())["jobs"]


def test_every_job_carries_its_spec_hash_and_retired_rows_get_no_job():
    pytest.importorskip("dagster")
    from estate_scheduler import definitions as d

    jobs = {
        j.tags["estate/label"]: j for j in d.defs.get_repository_def().get_all_jobs()
    }
    retired = {k for k, v in JOBS.items() if v.get("runs_on") == "retire"}
    assert retired, "the estate has retired rows; the rule needs one to bite on"
    assert not retired & set(jobs), (
        f"retired rows still scheduled: {sorted(retired & set(jobs))}"
    )
    assert set(jobs) == set(JOBS) - retired
    for label, j in jobs.items():
        assert j.tags[d.SPEC_HASH_TAG] == d.spec_hash(JOBS[label])
