"""lane-submit must be able to observe `already done` without spending its budget.

THE DEFECT THIS PROVES ABSENT (idp#7503, same class as #5814).

Step 2 of `lane-submit` handed the branch to the Greenlane by launching `git push` and then
watching it for up to 18 x 2s. On a branch that was ALREADY on origin -- the normal case for any
retry, and the case for a lane whose ref the Greenlane itself moved -- the push had nothing to
send.

"Nothing to send" is not "finishes immediately". Measured on this estate on 2026-11-11:

    git push --dry-run origin HEAD:refs/heads/lane/...   ->  exit 124 (SIGTERM at the 100s ceiling)

A dry-run sends no objects at all, and it still exceeded the executor's ceiling, because the
PRE-PUSH HOOK (`bin/idp-ci`) runs before git works out that there is nothing to do. So the step
spent its entire 50s cap observing a push that was running the gate, not sending, and then
reported

    TIMEOUT / OPTIMISATION REQUIRED / halted

for a lane that was fully handed over. Two lanes, two false failures, on 2026-11-11.

The fix is one question asked before the push:

    on_now=$(git ls-remote --heads origin "$lane" 2>/dev/null | awk '{print $1}')
    if [ "$on_now" = "$sha" ]; then say ok; exit 0; fi

These tests are the falsifier. They run the REAL shell fragment against a REAL git repository and
a REAL local bare remote, so they assert the behaviour of the step rather than the presence of a
string in a file.

WHAT WOULD MAKE THIS GATE STOP WORKING, said out loud:
  * remove the pre-check -> `test_noop_push_launches_no_push` fails (a push is launched), and
    `test_the_precheck_comes_before_the_push` fails (there is no pre-check to find).
  * move the pre-check AFTER the push -> `test_noop_push_launches_no_push` catches it, because the
    stub remote counts push invocations and expects zero.
  * make the pre-check always short-circuit -> `test_a_branch_that_really_needs_pushing` fails,
    because a branch origin does not have would never be sent.
  * treat an unanswerable `ls-remote` as "already there" -> `test_a_blind_remote_falls_through`
    fails, which is the difference between a fail-open gate and a gate that lies.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
INTENT = REPO_ROOT / "platform" / "estate" / "intents" / "lane-submit.yaml"

requires_git = pytest.mark.skipif(
    shutil.which("git") is None or shutil.which("sh") is None,
    reason="git and sh are required to run the step for real",
)


# --------------------------------------------------------------------------------------
# Reading the step out of the intent, without running the intent through the door.
# --------------------------------------------------------------------------------------
def _step2_shell() -> str:
    """The shell of lane-submit's step 2, from `sha=` THROUGH the push launch.

    The slice deliberately runs past `pushlog=$(mktemp`, because it must include the real push
    launch that follows. A slice that stopped at the push log would "pass" the no-push assertion
    in every case -- the push would never be reachable, so the test could not fail. That is the
    estate's R1 defect (a gate that fails open), and it was caught by this file's own
    `test_a_branch_that_really_needs_pushing_still_pushes` the first time it ran.

    The slice ends immediately after the push is launched (`push_pid=$!`), so the slow 18 x 2s
    observation tail is not part of the unit under test: the DECISION (short-circuit vs push) is,
    and it is settled before the window opens.
    """
    text = INTENT.read_text()
    start = text.index("sha=$(git rev-parse HEAD)")
    end = text.index("push_alive()", start)
    return text[start:end]


def test_the_step_is_not_empty():
    """A falsifier that read an empty string would pass every assertion below.

    The estate's own rule: a test that executes nothing is not a test.
    """
    body = _step2_shell()
    assert "git rev-parse HEAD" in body, body
    assert "ls-remote" in body, (
        "no ls-remote pre-check in the step: this is the defect, restored"
    )
    assert len(body) > 200, f"the step body looks truncated: {body!r}"


def test_the_precheck_comes_before_the_push():
    """THE ORDER IS THE FIX.

    If `ls-remote` moved after the push were launched, the step would pay the pre-push gate again
    and the defect would be back, so the position is the assertion.
    """
    body = _step2_shell()
    pos_ls = body.index("ls-remote")
    pos_exec = body.find("execvp")
    if pos_exec != -1:
        assert pos_ls < pos_exec, "the pre-check runs AFTER the push is launched"


# --------------------------------------------------------------------------------------
# The behavioural falsifier: a real repo, a real remote, a real step body.
# --------------------------------------------------------------------------------------
def _git(cwd, *args) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture()
def sandbox(tmp_path):
    """A bare 'origin' holding one lane branch, and a clone sitting on that same commit."""
    origin = tmp_path / "origin.git"
    seed = tmp_path / "seed"
    work = tmp_path / "work"

    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    subprocess.run(["git", "init", "-q", str(seed)], check=True)
    _git(seed, "config", "user.email", "test@example.invalid")
    _git(seed, "config", "user.name", "test")
    (seed / "README").write_text("x\n")
    _git(seed, "add", "README")
    _git(seed, "commit", "-qm", "seed")
    _git(seed, "branch", "-M", "lane/subject-of-the-test")
    _git(seed, "remote", "add", "origin", str(origin))
    _git(seed, "push", "-q", "origin", "lane/subject-of-the-test")

    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True)
    _git(work, "config", "user.email", "test@example.invalid")
    _git(work, "config", "user.name", "test")
    _git(work, "checkout", "-q", "lane/subject-of-the-test")

    counter = tmp_path / "pushes"
    counter.write_text("0")

    return {"origin": origin, "work": work, "tmp": tmp_path, "counter": counter}


def _stub(work: Path, tmp: Path, counter: Path, *, ls_remote_exit: int = 0) -> Path:
    """A `git` first on PATH that counts pushes and delegates everything else to real git.

    Only the push is intercepted, so `ls-remote` is exercised for real unless the caller asks for
    it to fail.
    """
    bindir = tmp / "stubbin"
    bindir.mkdir(exist_ok=True)
    real_git = shutil.which("git")
    stub = bindir / "git"
    lines = [
        "#!/bin/sh",
        'if [ "$1" = "push" ]; then',
        f'  echo $(( $(cat "{counter}") + 1 )) > "{counter}"',
        "  exit 0",
        "fi",
    ]
    if ls_remote_exit:
        lines += [
            'if [ "$1" = "ls-remote" ]; then',
            f"  exit {ls_remote_exit}",
            "fi",
        ]
    lines.append(f'exec "{real_git}" "$@"')
    stub.write_text("\n".join(lines) + "\n")
    stub.chmod(0o755)
    return bindir


def _run_step(sandbox, body: str, lane: str, *, ls_remote_exit: int = 0):
    work, tmp, counter = sandbox["work"], sandbox["tmp"], sandbox["counter"]
    if not (tmp / "stubbin" / "git").exists() or ls_remote_exit:
        bindir = _stub(work, tmp, counter, ls_remote_exit=ls_remote_exit)
    else:
        bindir = tmp / "stubbin"

    # `pushlog` is set in the intent between the fragment's start and its mktemp, which the slice
    # now runs past; and the pull-request/verdict tail is outside the unit under test. Supply the
    # log path and stop after the push is launched, so the test measures the DECISION.
    script = "\n".join(
        [
            "set -e",
            f'lane="{lane}"',
            f'pushlog="{tmp}/push.log"',
            body,
            # The step's tail (observation window, verdict) is bounded and slow; the decision is
            # already made by here. Record that the push branch was reached, then stop.
            'echo "REACHED_PUSH_LAUNCH"',
            "exit 0",
        ]
    )
    env = dict(os.environ)
    env["PATH"] = f"{bindir}:{env['PATH']}"
    return subprocess.run(
        ["sh", "-c", script],
        cwd=str(work),
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


@requires_git
def test_noop_push_launches_no_push_and_says_so(sandbox):
    """THE FALSIFIER FOR #7503.

    The branch is already on origin at the same sha. Without the pre-check the step runs the push;
    with it, the step returns `already on origin` and the counter stays at 0.

    Zero pushes is not a style preference. It is the measurement: the push is what costs the
    pre-push gate's 40-60s, and that cost is what killed the step.
    """
    result = _run_step(sandbox, _step2_shell(), "lane/subject-of-the-test")

    assert result.returncode == 0, (result.stdout, result.stderr)
    assert int(sandbox["counter"].read_text()) == 0, (
        "the step launched a push for a branch already on origin -- it pays the pre-push gate "
        "before discovering there is nothing to send, which is the defect"
    )
    assert "REACHED_PUSH_LAUNCH" not in result.stdout, (
        "the step fell through to the push branch for a branch already on origin"
    )
    assert "already on origin" in result.stdout, result.stdout


@requires_git
def test_the_noop_path_reports_a_verdict_not_a_timeout(sandbox):
    """The false failure is what reached the founder.

    `TIMEOUT / OPTIMISATION REQUIRED / halted` on a lane that was handed over is the report that
    made lane-submit look 53% broken (#7503). The no-op path must say what is true.
    """
    result = _run_step(sandbox, _step2_shell(), "lane/subject-of-the-test")
    out = result.stdout + result.stderr

    assert "TIMEOUT" not in out
    assert "halted" not in out
    assert "ok" in result.stdout


@requires_git
def test_a_branch_that_really_needs_pushing_still_pushes(sandbox):
    """THE OTHER HALF OF THE FALSIFIER.

    A pre-check that short-circuited everything would be a gate that always passes -- the estate's
    R1 defect. This proves the step still hands over a branch origin does not have.
    """
    work = sandbox["work"]
    (work / "README").write_text("changed\n")
    _git(work, "commit", "-qam", "work that has not been handed over")

    result = _run_step(sandbox, _step2_shell(), "lane/subject-of-the-test")

    assert result.returncode == 0, (result.stdout, result.stderr)
    assert int(sandbox["counter"].read_text()) == 1, (
        "the step did NOT push a branch that genuinely needed sending -- the pre-check has "
        "become a gate that always short-circuits"
    )
    assert "REACHED_PUSH_LAUNCH" in result.stdout, (
        "the push branch was never reached, so this test could not have observed a missing push"
    )
    assert "already on origin" not in result.stdout, result.stdout


@requires_git
def test_a_blind_remote_falls_through_to_the_real_push(sandbox):
    """A network hiccup must not report a handover that never happened.

    If `ls-remote` cannot answer, `on_now` is empty and the step proceeds to the push exactly as
    before this change. Reading the blind case as 'already there' would let a DNS failure tell the
    founder a lane was handed over when it was not.
    """
    work = sandbox["work"]
    (work / "README").write_text("changed again\n")
    _git(work, "commit", "-qam", "another commit")

    result = _run_step(
        sandbox, _step2_shell(), "lane/subject-of-the-test", ls_remote_exit=128
    )

    assert result.returncode == 0, (result.stdout, result.stderr)
    assert int(sandbox["counter"].read_text()) == 1, (
        "ls-remote failed and the step still refused to push -- a blind remote would be read as "
        "'already on origin', reporting a handover that never happened"
    )
    assert "REACHED_PUSH_LAUNCH" in result.stdout, result.stdout
