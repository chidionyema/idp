"""Incident crew#85 / crew#376, 2026-08-27: every schedule skipped for 16 hours.

The load gate compared the 1-minute load average against a flat 6.0 that the
importer had stamped on 43 of 44 jobs. Load sat at 9-11 on a 12-core Mac,
which is under one runnable thread per core, and 3836 ticks skipped in 24h
(schedules.db job_ticks, 2026-08-27). The rule: the default ceiling scales
with the machine; an explicit max_load is still honoured as written.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scheduler"))

from estate_scheduler.definitions import load_gate  # noqa: E402


def test_one_thread_per_core_is_not_a_reason_to_skip() -> None:
    assert load_gate("x", {}, current=10.7, cores=12) is None


def test_load_that_froze_the_dock_still_skips() -> None:
    skip = load_gate("x", {}, current=30.0, cores=12)
    assert skip is not None and "per core" in skip.skip_message


def test_explicit_max_load_is_honoured_as_written() -> None:
    assert load_gate("x", {"max_load": 8.0}, current=9.0, cores=12) is not None
    assert load_gate("x", {"max_load": 8.0}, current=7.0, cores=2) is None


def test_schedule_yml_carries_no_stamped_flat_ceiling() -> None:
    jobs = yaml.safe_load((ROOT / "scheduler" / "schedule.yml").read_text())
    stamped = [k for k, v in jobs.items() if isinstance(v, dict) and v.get("max_load") == 6.0]
    assert stamped == [], stamped
