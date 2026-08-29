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


def _pr(head: str, conclusions: list[str], state: str = "OPEN", merge: str = "CLEAN") -> dict:
    # mergeStateStatus is always in the real answer; the stub carried no such key until 2026-08-29,
    # so every case here was silently the "GitHub cannot say" one and the guard was never graded on
    # a PR it could actually see. CLEAN is the shape of the PR the guard exists to protect.
    return {"number": 628, "state": state, "headRefOid": head, "mergeStateStatus": merge,
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
    # The PR's head must be THIS repo's HEAD: two `git init` + empty commits only share a sha when
    # they land in the same second (the test was flaky on 2026-08-28, idp#629 push refused by it).
    repo2, env2 = _repo(tmp_path / "same", _pr(head, ["SUCCESS"]))
    head2 = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo2, capture_output=True, text=True).stdout.strip()
    (tmp_path / "same" / "bin" / "gh").write_text("#!/bin/sh\ncat <<'EOF'\n" + json.dumps(_pr(head2, ["SUCCESS"])) + "\nEOF\n")
    out = _run(repo2, env2)
    assert out.returncode == 0 and "nothing new" in out.stdout, out.stdout


def test_the_override_is_an_environment_variable_typed_on_purpose(tmp_path):
    repo, env = _repo(tmp_path, _pr("0" * 40, ["SUCCESS"]))
    out = _run(repo, {**env, "IDP_PUSH_ON_GREEN": "1"})
    assert out.returncode == 0 and "on purpose" in out.stdout, out.stdout


def test_the_pre_push_hook_runs_the_rung_first():
    rungs = [l for l in (ROOT / ".githooks" / "pre-push").read_text().splitlines() if l.startswith('"$IDP/bin/')]
    assert rungs[0] == '"$IDP/bin/idp-push-on-green"', rungs


def test_a_pr_that_conflicts_with_main_is_never_refused(tmp_path):
    """The only way to make a conflicting PR mergeable is to push the merge onto it."""
    repo, env = _repo(tmp_path, _pr("0" * 40, ["SUCCESS"], merge="DIRTY"))
    out = _run(repo, env)
    assert out.returncode == 0 and "conflicts with main" in out.stdout, out.stdout


def test_an_uncomputed_merge_state_stands_the_guard_down_rather_than_refusing(tmp_path):
    """2026-08-29, idp#800: GitHub computes mergeability lazily, so the first query after main moves
    answers UNKNOWN. The guard read that as "mergeable", refused two pushes and threw away about
    thirteen minutes of pre-push suite, while `gh pr view 800` was already answering DIRTY. A value
    that means "not computed yet" is the instrument saying it cannot see, and this script's own
    header says a blind instrument does not refuse a push."""
    repo, env = _repo(tmp_path, _pr("0" * 40, ["SUCCESS"], merge="UNKNOWN"))
    out = _run(repo, env)
    assert out.returncode == 0 and "BLIND" in out.stdout, out.stdout
