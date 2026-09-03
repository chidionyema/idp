"""The flux-events relay's alarm is the P0 issue on the board, never a failed run.

crew#766 (founder, 2026-08-31): a failed run makes GitHub email the founder one "Run failed"
notice per reconcile — 762+ from this workflow alone over a weekend, thousands across the repo.
A relayed cluster error is data for the board; the run may only go red when the alarm itself
cannot be filed (a gh call failing under `-e`), which is the one failure the workflow owns.
"""

from pathlib import Path

import yaml

WORKFLOW = (
    Path(__file__).resolve().parents[1] / ".github" / "workflows" / "flux-events.yml"
)


def _steps():
    doc = yaml.safe_load(WORKFLOW.read_text())
    return doc["jobs"]["ledger"]["steps"]


def _error_step():
    return next(s for s in _steps() if "severity == 'error'" in s.get("if", ""))


def test_the_error_annotation_survives_so_the_run_log_still_names_the_object():
    assert "::error::" in _error_step()["run"]


def test_a_recovery_event_still_closes_the_open_alarm():
    close = next(s for s in _steps() if "Health check passed" in s.get("if", ""))
    assert "gh issue close" in close["run"]
