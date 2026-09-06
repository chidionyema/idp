# ruff: noqa: S101
"""The outcome label, the log slice and the redaction of forge/collect_ci_runs.py, offline."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import collect_ci_runs as c  # noqa: E402

RUN = {"name": "ci", "head_sha": "abc", "created_at": "2026-09-06T10:00:00Z"}


def test_label_is_flake_only_for_a_later_green_run_of_the_same_workflow(monkeypatch):
    seen = {}

    def fake_gh(path):
        seen["path"] = path
        return (
            '{"workflow_runs": ['
            '{"name": "ci", "created_at": "2026-09-06T09:00:00Z"},'
            '{"name": "other", "created_at": "2026-09-06T11:00:00Z"}]}'
        )

    monkeypatch.setattr(c, "gh", fake_gh)
    assert (
        c.label("o/r", RUN) == "0"
    )  # earlier green, and a different workflow: not a flake
    assert "head_sha=abc" in seen["path"] and "status=success" in seen["path"]
    monkeypatch.setattr(
        c,
        "gh",
        lambda p: (
            '{"workflow_runs": [{"name": "ci", "created_at": "2026-09-06T10:30:00Z"}]}'
        ),
    )
    assert c.label("o/r", RUN) == "1"


def test_step_log_slices_the_step_and_stops_at_its_error_line(monkeypatch):
    log = "\n".join(
        [
            "2026-09-06T09:59:59.1Z Current runner version",
            "2026-09-06T10:00:00.5Z ##[group]Run bin/idp-ci",
            "2026-09-06T10:00:01.0Z FAIL  idp-ci",
            "2026-09-06T10:00:02.0Z ##[error]Process completed with exit code 1.",
            "2026-09-06T10:00:02.3Z Post job cleanup.",
            "2026-09-06T10:00:02.6Z Removing credentials config",
            "2026-09-06T10:00:03.0Z Cleaning up orphan processes",
        ]
    )
    monkeypatch.setattr(c, "gh_bytes", lambda p: log.encode())
    step = {
        "started_at": "2026-09-06T10:00:00Z",
        "completed_at": "2026-09-06T10:00:02Z",
    }
    out = c.step_log("o/r", {"id": 1}, step)
    assert out.splitlines()[0].endswith("Run bin/idp-ci")
    assert out.splitlines()[-1].endswith("exit code 1.")
    assert "Removing credentials" not in out and "runner version" not in out


def test_clean_tail_strips_noise_and_redacts_tokens():
    raw = "\n".join(
        [
            "2026-09-06T10:00:00.5Z ##[group]Run thing",
            "2026-09-06T10:00:01.0Z \x1b[31mFAIL\x1b[0m gate token ghp_abcdefghijklmnopqrstuvwxyz0123",
            "2026-09-06T10:00:01.5Z Authorization: Bearer abcdefghijklmnopqrstu",
            "",
            "2026-09-06T10:00:02.0Z ##[endgroup]",
        ]
    )
    out = c.clean_tail(raw)
    assert out.splitlines() == [
        "FAIL gate token <redacted>",
        "Authorization: <redacted>",
    ]


def test_stratify_caps_each_workflow_then_the_total():
    failed = [{"name": "noisy", "id": i} for i in range(5)] + [{"name": "ci", "id": 9}]
    kept = c.stratify(failed, per_workflow=2, limit=3)
    assert [r["name"] for r in kept] == ["noisy", "noisy", "ci"]
