"""crew#584 / idp#628, 2026-08-28: the PR was green at 18:42:42Z (run 33200030561, 6m40s) and was
pushed to three more times -- 18:45, 18:50, 18:52 -- each push cancelling the run before it. A
7-minute PR stayed open 21 minutes; founder: "look how long it takes" / "so wondeer nothing got
delievred". bin/idp-push-on-green is the pre-push rung that refuses a push onto a green PR with
the fix on the line (merge it, open a second PR). No network: `gh` is a stub on PATH."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-push-on-green"


def _repo(tmp_path: Path, pr: dict | None) -> tuple[Path, dict]:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty",
                    "-m", "one"], cwd=repo, check=True)
    fake = tmp_path / "bin"
    fake.mkdir(parents=True)
    gh = fake / "gh"
    if pr is None:
        gh.write_text("#!/bin/sh\nexit 1\n")
    else:
        gh.write_text("#!/bin/sh\ncat <<'EOF'\n" + json.dumps(pr) + "\nEOF\n")
    gh.chmod(0o755)
    env = {**os.environ, "PATH": f"{fake}:{os.environ['PATH']}"}
    env.pop("IDP_PUSH_ON_GREEN", None)
    return repo, env


def _run(repo: Path, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run([str(SCRIPT)], cwd=repo, env=env, capture_output=True, text=True)


def _pr(head: str, conclusions: list[str], state: str = "OPEN") -> dict:
    return {"number": 628, "state": state, "headRefOid": head,
            "statusCheckRollup": [{"name": f"c{i}", "conclusion": c} for i, c in enumerate(conclusions)]}


def test_a_push_onto_a_green_pr_is_refused_with_the_merge_on_the_line(tmp_path):
    repo, env = _repo(tmp_path, _pr("0" * 40, ["SUCCESS", "SKIPPED", "SUCCESS"]))
    out = _run(repo, env)
    assert out.returncode == 1, out.stdout + out.stderr
    assert "GREEN" in out.stdout and "gh pr merge 628 --merge" in out.stdout, out.stdout


def test_a_red_or_pending_check_means_the_push_is_a_fix(tmp_path):
    repo, env = _repo(tmp_path, _pr("0" * 40, ["SUCCESS", "FAILURE"]))
    assert _run(repo, env).returncode == 0
    repo, env = _repo(tmp_path / "p", _pr("0" * 40, ["SUCCESS", None]))
    assert _run(repo, env).returncode == 0


def test_no_pr_or_nothing_new_or_blind_is_never_refused(tmp_path):
    repo, env = _repo(tmp_path, None)
    assert _run(repo, env).returncode == 0
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
    repo2, env2 = _repo(tmp_path / "same", _pr(head, ["SUCCESS"]))
    head2 = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo2, capture_output=True, text=True).stdout.strip()
    repo2, env2 = _repo(tmp_path / "same2", _pr(head2, ["SUCCESS"]))
    out = _run(repo2, env2)
    assert out.returncode == 0 and "nothing new" in out.stdout, out.stdout


def test_the_override_is_an_environment_variable_typed_on_purpose(tmp_path):
    repo, env = _repo(tmp_path, _pr("0" * 40, ["SUCCESS"]))
    out = _run(repo, {**env, "IDP_PUSH_ON_GREEN": "1"})
    assert out.returncode == 0 and "on purpose" in out.stdout, out.stdout


def test_the_pre_push_hook_runs_the_rung_first():
    rungs = [l for l in (ROOT / ".githooks" / "pre-push").read_text().splitlines() if l.startswith('"$IDP/bin/')]
    assert rungs[0] == '"$IDP/bin/idp-push-on-green"', rungs
