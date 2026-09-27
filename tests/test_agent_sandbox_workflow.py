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


# The agent step itself, run with a stand-in harness on PATH. Run 36317202633 died here in 0.75s
# with no message: the structural tests above passed, and the step had never executed.
FAKE = {
    "pi": 'for a; do [ "$prev" = --session-dir ] && d="$a"; prev="$a"; done\n'
    'echo "{}" > "$d/2026-09-27T00-00-00Z_s.jsonl"\necho there >> a.txt\n',
    "claude": 'mkdir -p "$HOME/.claude/projects/p"\necho "{}" > "$HOME/.claude/projects/p/s.jsonl"\n'
    "echo there >> a.txt\n",
}


def _agent_step(
    tmp_path: Path, harness: str, fake: str | None
) -> tuple[subprocess.CompletedProcess, Path]:
    r = _repo(tmp_path)
    (r / "a.txt").write_text("hi\n")
    subprocess.run(["git", "-C", str(r), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(r), "commit", "-qm", "a"], check=True)
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    for name, body in FAKE.items():
        f = bin_ / name
        f.write_text("#!/bin/bash\n" + (fake if fake is not None else body))
        f.chmod(0o755)
    temp, home = tmp_path / "runner", tmp_path / "home"
    temp.mkdir()
    home.mkdir()
    env = {
        "PATH": f"{bin_}:/usr/bin:/bin",
        "HOME": str(home),
        "RUNNER_TEMP": str(temp),
        "HARNESS": harness,
        "TASK": "append there",
        "CLAUDE_CODE_OAUTH_TOKEN": "x",
        "MINIMAX_API_KEY": "x",
    }
    run = _step("agent", "Run the agent")["run"]
    p = subprocess.run(
        ["bash", "-e", "-c", run],
        cwd=r,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return p, temp / "out"


@pytest.mark.parametrize("harness", ["pi", "claude-code"])
def test_the_agent_step_hands_on_a_transcript_and_the_patch(tmp_path, harness):
    p, out = _agent_step(tmp_path, harness, None)
    assert p.returncode == 0, p.stdout + p.stderr
    assert (out / "transcript.jsonl").read_text() == "{}\n"
    assert "+there" in (out / "patch").read_text()


def test_a_harness_that_leaves_no_transcript_says_why(tmp_path):
    p, _ = _agent_step(tmp_path, "pi", 'echo "error: no API key for minimax"; exit 1\n')
    assert p.returncode == 1
    assert "harness exit 1" in p.stdout and "no API key for minimax" in p.stdout


def test_a_harness_that_fails_stops_the_run_with_the_providers_reason(tmp_path):
    """Run 36317773590: pi exited 1 in 0.6s, left a transcript, and the firewall passed it."""
    body = FAKE["pi"] + (
        'echo \'401 {"type":"error","error":{"type":"authentication_error","message":"login fail"}}\'\nexit 1\n'
    )
    p, _ = _agent_step(tmp_path, "pi", body)
    assert p.returncode == 1, p.stdout + p.stderr
    assert "401 authentication_error" in p.stdout
    assert "login fail" not in p.stdout
