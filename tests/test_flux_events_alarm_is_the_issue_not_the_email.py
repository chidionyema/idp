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


def test_an_error_event_files_the_alarm_but_never_fails_the_run():
    run = _error_step()["run"]
    assert "gh issue create" in run, (
        "the P0 issue is the alarm; creating it left the step"
    )
    assert "gh issue comment" in run, (
        "a repeat event must land on the open issue, not a new one"
    )
    assert "exit 1" not in run, (
        "an exit 1 per relayed error event turns GitHub's run-failure email into an alert "
        "firehose at the founder's personal address (crew#766); the issue is the alarm"
    )


def test_the_error_annotation_survives_so_the_run_log_still_names_the_object():
    assert "::error::" in _error_step()["run"]


def test_a_recovery_event_still_closes_the_open_alarm():
    close = next(s for s in _steps() if "Health check passed" in s.get("if", ""))
    assert "gh issue close" in close["run"]
