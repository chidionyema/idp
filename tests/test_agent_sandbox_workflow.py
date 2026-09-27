"""agent-sandbox.yml: the agent can reach nothing that matters, and only graded work leaves.

crew#975 CP11. Each test is one property the design rests on, read from the real workflow file;
weakening the file (a token in the agent job, a task interpolated into a script, the firewall run
from the patched tree) turns one red. The last test runs the open-pr refusal step itself against a
real git repository.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/agent-sandbox.yml"
JOBS = yaml.safe_load(WORKFLOW.read_text())["jobs"]


def _steps(job: str) -> list[dict]:
    return JOBS[job]["steps"]


def _step(job: str, name_starts: str) -> dict:
    return next(s for s in _steps(job) if s.get("name", "").startswith(name_starts))


def _text(job: str) -> str:
    return yaml.safe_dump(JOBS[job])


def test_the_agent_job_can_only_read():
    assert JOBS["agent"]["permissions"] == {"contents": "read"}


@pytest.mark.parametrize("job", ["agent", "firewall"])
def test_no_credential_is_left_in_git_where_untrusted_or_graded_work_runs(job):
    checkouts = [
        s for s in _steps(job) if s.get("uses", "").startswith("actions/checkout@")
    ]
    assert checkouts
    assert all(s["with"]["persist-credentials"] is False for s in checkouts)


@pytest.mark.parametrize(
    "secret", ["SEED_GITHUB_APP", "AGENT_TRANSCRIPT_AGE_KEY", "GITHUB_TOKEN"]
)
def test_the_agent_job_never_sees_a_secret_that_could_publish_or_read_back(secret):
    assert secret not in _text("agent")


def test_no_input_is_ever_interpolated_into_a_script():
    for job in JOBS:
        for s in _steps(job):
            assert not re.search(
                r"\$\{\{\s*(inputs|github\.event)\.", s.get("run", "")
            ), (
                job,
                s.get("name"),
            )


def test_the_firewall_is_mains_code_not_the_patched_tree():
    assert all(
        s["with"]["ref"] == "main"
        for j in ("firewall", "open-pr")
        for s in _steps(j)
        if s.get("uses", "").startswith("actions/checkout@")
    )
    grade = _step("firewall", "Grade every claim")["run"]
    assert "bin/epistemic_firewall.py" in grade and 'exit "$rc"' in grade


def test_nothing_is_published_until_the_firewall_passes():
    assert "firewall" in JOBS["open-pr"]["needs"]


def test_the_pr_is_opened_by_the_app_so_required_checks_run():
    push = _step("open-pr", "Push a branch")
    assert push["env"]["GH_TOKEN"] == "${{ steps.app.outputs.token }}"  # noqa: S105 -- an expression, not a value


def test_every_action_is_pinned_to_a_commit():
    for job in JOBS:
        for s in _steps(job):
            if "uses" in s:
                assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", s["uses"]), s[
                    "uses"
                ]


def _repo(tmp_path: Path) -> Path:
    r = tmp_path / "r"
    r.mkdir()

    def git(*a):
        subprocess.run(["git", "-C", str(r), *a], check=True, capture_output=True)

    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    (r / ".github/workflows").mkdir(parents=True)
    (r / ".github/workflows/ci.yml").write_text("on: push\n")
    (r / "app.py").write_text("x = 1\n")
    git("add", "-A")
    git("commit", "-q", "-m", "base")
    return r


def _patch(r: Path, change) -> str:
    change(r)
    subprocess.run(["git", "-C", str(r), "add", "-A"], check=True)
    p = subprocess.run(
        ["git", "-C", str(r), "diff", "--cached", "--binary", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    subprocess.run(["git", "-C", str(r), "reset", "-q", "--hard", "HEAD"], check=True)
    subprocess.run(["git", "-C", str(r), "clean", "-qfd"], check=True)
    return p


def _refusal_step(r: Path, patch: str, tmp_path: Path) -> subprocess.CompletedProcess:
    """Run the step's own shell after its decrypt lines, with the patch already in place."""
    run = _step("open-pr", "Apply the patch")["run"]
    tail = run[run.index('[ -s "$work/patch" ]') :]
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    (work / "patch").write_text(patch)
    return subprocess.run(
        ["bash", "-c", f'set -euo pipefail\nwork="{work}"\n{tail}'],
        cwd=r,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.mark.parametrize(
    ("change", "refused"),
    [
        (lambda r: (r / "app.py").write_text("x = 2\n"), False),
        (lambda r: (r / ".github/workflows/ci.yml").write_text("on: []\n"), True),
        (lambda r: (r / ".github/workflows/ci.yml").rename(r / "moved.yml"), True),
        (
            lambda r: (
                (r / ".githooks").mkdir()
                or (r / ".githooks/pre-push").write_text("exit 0\n")
            ),
            True,
        ),
    ],
)
def test_the_open_pr_step_refuses_a_patch_that_touches_ci_or_hooks(
    tmp_path, change, refused
):
    r = _repo(tmp_path)
    p = _refusal_step(r, _patch(r, change), tmp_path)
    assert (p.returncode != 0) is refused, p.stdout + p.stderr


def test_an_empty_patch_is_a_failure_not_a_quiet_success(tmp_path):
    r = _repo(tmp_path)
    p = _refusal_step(r, "", tmp_path)
    assert p.returncode != 0 and "changed nothing" in p.stdout
