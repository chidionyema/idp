"""fleetview_backend.agent_jobs: the job LIST must tell the truth about a run.

Two defects, both measured on the real agent-sandbox workflow and both about status:

  * the third job of `.github/workflows/agent-sandbox.yml` is named `submit-lane`, while the
    board's stage vocabulary still said the old job name. The stage list never matched the
    job, so a run that died in the submission step (the previous run of mission INS-00011 died
    exactly there, on the commit-msg hook) was reported as "The run ended failure." -- the
    run's own failing step was never read;
  * the sandbox pushes `lane/agent-<harness>-<run>` and the Greenlane raises the pull request
    with that lane as its head (greenlane/github.py's `_ensure_pr` posts `{"head": lane}`). The
    lookup still asked for the older `agent/<harness>-<run>` head, so a run that had landed
    answered "The run passed but no PR was found" -- a false failure.

A board that cannot read the truth is worse than a board that is empty: it teaches the reader
to distrust it.
"""

from __future__ import annotations

from fleetview_backend import agent_jobs

RUN_ID = 43074179589


def _run(*, conclusion: str = "failure", status: str = "completed") -> dict:
    return {
        "id": RUN_ID,
        "display_title": "agent (gemini): LEGION #7932",
        "event": "issues",
        "status": status,
        "conclusion": conclusion,
        "created_at": "2026-11-11T00:00:00Z",
        "html_url": f"https://github.com/chidionyema/idp/actions/runs/{RUN_ID}",
    }


def _jobs(sandbox_jobs: list[dict]) -> list[dict]:
    return sandbox_jobs


def _wire(monkeypatch, *, sandbox_jobs, pulls, annotations=404):
    def gh(method: str, path: str, body=None):
        if path.endswith("/jobs"):
            return 200, {"jobs": sandbox_jobs}
        if "/check-runs/" in path and "/annotations" in path:
            return annotations, []
        if "/pulls?" in path:
            # The pull request belongs to the LANE the sandbox pushed; the old branch name
            # has none, which is exactly why the lookup had to change.
            if "head=chidionyema:lane/agent-" in path:
                return 200, pulls
            return 200, []
        if "/actions/runs/" in path:
            return 200, _run()
        raise AssertionError(f"unexpected path {path}")

    monkeypatch.setenv("FLEETVIEW_AGENT_REPO", "chidionyema/idp")
    monkeypatch.setattr(agent_jobs, "_gh", gh)
    agent_jobs.reset_for_tests()


def test_a_run_that_died_in_the_submission_step_names_that_step(monkeypatch):
    _wire(
        monkeypatch,
        sandbox_jobs=[
            {"id": 1, "name": "agent", "status": "completed", "conclusion": "success"},
            {
                "id": 2,
                "name": "firewall",
                "status": "completed",
                "conclusion": "success",
            },
            {
                "id": 3,
                "name": "submit-lane",
                "status": "completed",
                "conclusion": "failure",
                "steps": [
                    {
                        "name": "Commit through the estate's own hooks and push the lane",
                        "conclusion": "failure",
                    }
                ],
            },
        ],
        pulls=[],
    )
    job = agent_jobs.job_from_run(_run())
    assert job["state"] == "failed"
    # The board's word for the submission step is "open-pr"; what matters is that the run's
    # OWN failing step is named, instead of "The run ended failure."
    assert job["stage"] == "open-pr"
    assert "Commit through the estate's own hooks and push the lane" in job["reason"], (
        job
    )


def test_a_landed_run_is_not_reported_as_having_no_pull_request(monkeypatch):
    """The Greenlane raises the pull request from the lane the sandbox pushed."""
    _wire(
        monkeypatch,
        sandbox_jobs=[
            {"id": 1, "name": "agent", "status": "completed", "conclusion": "success"},
            {
                "id": 2,
                "name": "firewall",
                "status": "completed",
                "conclusion": "success",
            },
            {
                "id": 3,
                "name": "submit-lane",
                "status": "completed",
                "conclusion": "success",
            },
        ],
        pulls=[
            {
                "number": 7999,
                "state": "closed",
                "merged_at": "2026-11-11T01:00:00Z",
                "html_url": "https://github.com/chidionyema/idp/pull/7999",
            }
        ],
    )
    job = agent_jobs.job_from_run(_run(conclusion="success"))
    assert job["state"] == "done"
    assert job["stage"] == "merged"
    assert job["pr"]["number"] == 7999
