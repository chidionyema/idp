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
        for j in ("firewall", "submit-lane")
        for s in _steps(j)
        if s.get("uses", "").startswith("actions/checkout@")
    )
    grade = _step("firewall", "Grade every claim")["run"]
    assert "bin/epistemic_firewall.py" in grade and 'exit "$rc"' in grade


def test_nothing_is_published_until_the_firewall_passes():
    assert "firewall" in JOBS["submit-lane"]["needs"]


def test_the_work_lands_through_the_greenlane_not_a_pull_request():
    """AGENTS.md section 2: an agent pushes lane/<name> and the Greenlane lands it."""
    text = _text("submit-lane")
    assert "gh pr create" not in text
    commit = _step("submit-lane", "Commit through the estate's own hooks")["run"]
    assert 'branch="lane/agent-${HARNESS}-${GITHUB_RUN_ID}"' in commit
    assert (
        "core.hooksPath .githooks" in commit
    )  # the stamp comes from the estate's hook
    # the App's checkout pushes, so the push is the App's and the lander's push trigger fires
    checkout = next(
        s
        for s in _steps("submit-lane")
        if s.get("uses", "").startswith("actions/checkout@")
    )
    assert checkout["with"]["token"] == "${{ steps.app.outputs.token }}"  # noqa: S105


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
    run = _step("submit-lane", "Apply the patch")["run"]
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
        "GEMINI_API_KEY": "x",
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


@pytest.mark.parametrize("harness", ["pi", "claude-code", "gemini"])
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


def test_gemini_runs_in_pi_on_googles_api_with_its_own_key(tmp_path):
    """Gemini is a model, pi is a harness: the estate's transcript format, Google's provider."""
    body = 'echo "$@" > "$HOME/args"\n' + FAKE["pi"]
    p, _ = _agent_step(tmp_path, "gemini", body)
    assert p.returncode == 0, p.stdout + p.stderr
    args = (tmp_path / "home" / "args").read_text()
    assert "--provider google" in args and "--model gemini-3.5-flash" in args
    run = _step("agent", "Run the agent")
    assert run["env"]["GEMINI_API_KEY"] == "${{ secrets.SEED_GEMINI_API_KEY }}"  # noqa: S105


def test_failed_gemini_preserves_its_private_transcript(tmp_path):
    private_detail = "private-provider-diagnostic-sentinel"
    body = FAKE["pi"] + f'echo "{private_detail}"\nexit 1\n'
    result, out = _agent_step(tmp_path, "gemini", body)
    assert result.returncode == 1
    assert private_detail not in result.stdout + result.stderr
    assert private_detail in (out / "stdout").read_text()
    assert (out / "transcript.jsonl").read_text() == "{}\n"


@pytest.mark.parametrize(
    "category", ["RESOURCE_EXHAUSTED", "PERMISSION_DENIED", "NOT_FOUND"]
)
def test_google_failure_reports_only_the_allowlisted_category(tmp_path, category):
    private_detail = "private-provider-diagnostic-sentinel"
    body = (
        FAKE["pi"]
        + f'echo \'{{"error":{{"status":"{category}","message":"{private_detail}"}}}}\'\nexit 1\n'
    )
    result, out = _agent_step(tmp_path, "gemini", body)
    assert result.returncode == 1
    assert category in result.stdout
    assert private_detail not in result.stdout + result.stderr
    assert private_detail in (out / "stdout").read_text()


def test_private_evidence_is_sealed_and_uploaded_after_agent_failure():
    assert _step("agent", "Encrypt what leaves").get("if") == "always()"
    upload = next(
        step
        for step in _steps("agent")
        if step.get("uses", "").startswith("actions/upload-artifact@")
    )
    assert upload.get("if") == "always()"
    assert upload["with"]["path"] == "${{ runner.temp }}/sealed/work.tar.age"


# The claim and the commit, run for real: a fake `gh`, a bare origin, the estate's own hooks.
_GH = """#!/bin/bash
echo "$@" >> "$GH_LOG"
case "$1 $2" in
  "issue create") echo "https://github.com/o/r/issues/77" ;;
esac
"""


def _claim_gate_regex():
    src = (ROOT / "bin/claim-gate").read_text()
    start = src.index("CLAIM = re.compile(")
    ns: dict = {"re": re}
    exec(src[start : src.index(")\n", start) + 2], ns)  # noqa: S102 -- the gate's own regex
    return ns["CLAIM"]


def _submit(tmp_path: Path, issue: str):
    r = _repo(tmp_path)
    bare = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    subprocess.run(
        ["git", "-C", str(r), "remote", "add", "origin", str(bare)], check=True
    )
    (r / ".githooks").mkdir()
    for hook in (
        "commit-msg",
    ):  # the stamp; pre-commit's linters are installed in the job
        (r / ".githooks" / hook).write_text((ROOT / ".githooks" / hook).read_text())
        (r / ".githooks" / hook).chmod(0o755)
    subprocess.run(["git", "-C", str(r), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(r), "commit", "-qm", "hooks"], check=True)
    (r / "app.py").write_text("x = 2\n")
    (r / "app.py").rename(r / "lib.py")
    subprocess.run(["git", "-C", str(r), "add", "-A"], check=True)
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    (bin_ / "gh").write_text(_GH)
    (bin_ / "gh").chmod(0o755)
    out = tmp_path / "gh_output"
    env = {
        "PATH": f"{bin_}:/usr/bin:/bin",
        "HOME": str(tmp_path),
        "GH_LOG": str(tmp_path / "gh.log"),
        "GITHUB_OUTPUT": str(out),
        "GITHUB_RUN_ID": "4242",
        "RUNNER_TEMP": str(tmp_path),
        "HARNESS": "gemini",
        "TASK": "fix the router\nsecond line",
        "ISSUE": issue,
        "RUN_URL": "https://example/run",
    }
    claim = _step("submit-lane", "Claim the work")["run"]
    p1 = subprocess.run(
        ["bash", "-c", claim], cwd=r, env=env, capture_output=True, text=True
    )
    assert p1.returncode == 0, p1.stdout + p1.stderr
    for line in out.read_text().splitlines():
        k, v = line.split("=", 1)
        env[k.upper()] = v
    commit = _step("submit-lane", "Commit through the estate's own hooks")["run"]
    p2 = subprocess.run(
        ["bash", "-c", commit], cwd=r, env=env, capture_output=True, text=True
    )
    return p2, r, bare, (tmp_path / "gh.log").read_text()


@pytest.mark.parametrize("issue", ["", "31"])
def test_the_lane_carries_a_claim_the_gate_accepts_and_the_hooks_stamp(tmp_path, issue):
    p, r, bare, gh = _submit(tmp_path, issue)
    assert p.returncode == 0, p.stdout + p.stderr
    num = issue or "77"
    assert ("issue create" in gh) is (not issue)
    claim = next(ln for ln in gh.splitlines() if "CLAIM agent=" in ln)
    m = _claim_gate_regex().search(claim[claim.index("CLAIM") :])
    assert m and m["agent"] == "gemini"
    assert set(m["paths"].split(",")) == {
        "app.py",
        "lib.py",
    }  # both sides of the rename
    msg = subprocess.run(
        [
            "git",
            "--git-dir",
            str(bare),
            "log",
            "-1",
            "--format=%B",
            "lane/agent-gemini-4242",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert f"Claim: #{num}" in msg and "Agent: gemini" in msg
    assert "X-Idp-Signed: " in msg
    assert msg.splitlines()[0] == "agent-sandbox (gemini): fix the router"
