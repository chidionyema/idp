"""The pre-push gate must fit the budget that contains it, and grade only what the push changes.

2026-11-08. The delivery friction every agent session inherited was measured, not guessed. A
lane-submit push step is capped at 50 s (`platform/estate/intents/lane-submit.yaml`). The
pre-push hook runs inside that step, and inside the hook the fast gate ran for **51.1 s** on a
two-file Python change -- so the door killed the push *mid-gate*, and the retry paid the
identical 51.1 s again. Under parallel agent sessions that repeats once per lane: one session's
friction becomes every session's friction.

Two defects, one class:

1. **A budget larger than the budget that contains it.** `bin/idp-ci` declared the fast gate
   "under 60 s" while the push step allowed 50 s. A correct machine cannot satisfy a bound
   bigger than its container, so the push was killed at the door and the retry re-ran the
   identical work. The declared budget is now read from `bin/idp-ci` and held to the push
   step's own timeout, so the two cannot drift apart again.

2. **The gate graded more than the push changed.** 37 of the 51.1 s went to rungs that ran
   unconditionally: the language gate's own proof suite (20 s -- a proof about `bin/language-gate`
   the push had not touched) and the inner-budget ratchet (7 s -- which can only find a new bound
   in an intent, in the gate, or in its baseline). "Grade what the push changes" is this repo's
   own rule; `tests/test_prepush_grades_only_what_the_push_changes.py` holds the hook to it, and
   these rungs now obey it.

The third piece is the retry. A verdict already on disk for *this exact diff* is read, not
recomputed: `bin/idp-ci` writes `~/.cache/idp-ci-verified/<head>-<base>` when the fast gate
grades that diff green against that base, and the hook reads it before running anything. The key
carries BOTH head and base -- a commit graded against one base is not proof against another,
because once main moves the same tree is a different diff.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / "bin/idp-ci"
HOOK = ROOT / ".githooks/pre-push"
INTENT = ROOT / "platform/estate/intents/lane-submit.yaml"

# The push step's own timeout covers everything the hook does before the bytes move: the claim
# gate, the fast gate, and the push itself. These two reserves are what is left over once the
# gate has been given its budget, and they are measured, not wished: the estate's own record of
# the push step says the guard cost 32 s of its own accord and the push itself took 37.4 s once
# and past 40 s the next time (platform/estate/intents/lane-submit.yaml).
PUSH_RESERVE_SEC = 10
CLAIM_GATE_RESERVE_SEC = 10


def _fast_gate_budget() -> int:
    """The budget the fast gate declares for itself, read from the script that runs it."""
    text = CI.read_text()
    m = re.search(r'IDP_CI_FAST_BUDGET_S="\$\{IDP_CI_FAST_BUDGET_S:-(\d+)\}"', text)
    assert m, (
        "bin/idp-ci no longer declares IDP_CI_FAST_BUDGET_S; the gate's budget must be a number"
    )
    return int(m.group(1))


def _push_step_timeout() -> int:
    steps = yaml.safe_load(INTENT.read_text())["steps"]
    for step in steps:
        if "push" in step.get("name", "").lower():
            return int(step.get("timeout", 0))
    raise AssertionError("lane-submit no longer has a push step")


def _guard_above(script: str, needle: str, also: str | None = None) -> str:
    """The `touched` guard that governs a call, found by walking back from the call itself."""
    lines = script.splitlines()
    hits = [
        i
        for i, line in enumerate(lines)
        if needle in line and (also is None or also in line)
    ]
    assert hits, f"bin/idp-ci no longer calls {needle}"
    for j in range(hits[0], -1, -1):
        if "touched " in lines[j]:
            return lines[j]
    raise AssertionError(f"the {needle} call is not behind a touched() guard")


def test_the_fast_gate_declares_a_budget_the_push_step_can_hold():
    """The defect in one assertion: a gate whose declared budget exceeds the budget of the door
    that runs it can never be honoured, so every push is killed mid-gate and every retry pays
    the same price again."""
    budget, push_timeout = _fast_gate_budget(), _push_step_timeout()
    ceiling = push_timeout - PUSH_RESERVE_SEC - CLAIM_GATE_RESERVE_SEC
    assert budget <= ceiling, (
        f"bin/idp-ci declares a {budget}s fast gate, but the lane-submit push step allows only "
        f"{push_timeout}s in total -- {CLAIM_GATE_RESERVE_SEC}s for the claim gate and "
        f"{PUSH_RESERVE_SEC}s for the push itself leave {ceiling}s for the gate. A gate that "
        f"declares more than its container can hold is killed mid-flight, and the retry re-runs "
        f"the identical work."
    )


def test_the_declared_budget_is_the_one_the_repository_enforces():
    """The number in the script and the number the test reads must be the same number. A budget
    that only exists in a comment is a budget nobody holds."""
    text = CI.read_text()
    assert re.search(r"IDP_CI_FAST_BUDGET_S=", text), (
        "bin/idp-ci does not declare the fast gate's budget"
    )
    assert str(_fast_gate_budget()) in text


def test_the_language_proof_suite_runs_only_when_the_gate_it_proves_changed():
    """The proof suite proves `bin/language-gate` is sound; it says nothing about the lane. It
    earned its 20 s only when the gate script or its own proof changed."""
    guard = _guard_above(
        CI.read_text(),
        "test_language_gate.py",
        also="-m pytest",
    )
    lines = [
        line
        for line in guard.split()
        if "test_language_gate.py" in line or "language-gate" in line
    ]
    assert any("bin/language-gate" in line for line in lines), (
        "the language gate's proof suite is still run for every push: the gate proves the GATE, "
        "not the lane, and re-proving it cost 20 s of a 51 s gate on a two-file change"
    )


def test_the_language_rung_still_runs_its_gate_on_every_push():
    """Scoping the proof must not scope the gate: `bin/language-gate` grades the files the push
    adds, and it is the only thing that can refuse a new Python file."""
    text = CI.read_text()
    assert "bin/language-gate" in text and "lg_rc" in text, (
        "the language rung no longer runs its gate"
    )


def test_the_inner_budget_ratchet_runs_only_when_a_bound_could_have_appeared():
    """`bin/timeout-budget` refuses a NEW inner wall-clock bound. A new bound can only arrive in
    an intent, in the gate itself, or in its baseline -- so a push that touches none of them
    cannot have introduced one."""
    text = CI.read_text()
    guard = _guard_above(text, 'elif out=$("$MPY" "$IDP/bin/timeout-budget"')
    assert "platform/estate/intents/" in guard and "bin/timeout-budget" in guard, (
        "the inner-budget ratchet is not scoped to the files that can introduce a bound; it cost "
        "7 s of a 51 s gate on a diff that touched no intent"
    )


def test_the_inner_budget_ratchet_can_still_fail():
    """A rung that cannot fail is not a rung. Scoping it must not have removed its refusal."""
    text = CI.read_text()
    assert 'say "FAIL  budget' in text, "the inner-budget ratchet can no longer fail"


def test_the_schema_ratchet_still_grades_every_intent_a_lane_adds():
    """The schema proof is scoped; the RATCHET that grades the intents is not. An intent is what
    the ratchet exists to grade, so its guard has to stay wide."""
    text = CI.read_text()
    guard = _guard_above(text, 'sc=$("$IDP/bin/schema-conformance" intents')
    assert "platform/estate/intents/" in guard, (
        "the schema ratchet no longer fires for a lane that changed an intent: the ratchet is the "
        "gate that grades intents, and scoping it would let a new intent through unchecked"
    )


def test_the_schema_proof_runs_when_the_checker_it_proves_changed():
    """The proof proves the checker. It must not become theatre: it runs whenever the checker,
    its own proof, or its baseline changed."""
    text = CI.read_text()
    guard = _guard_above(text, 'sp=$("$MPY" -m pytest')
    for needed in ("bin/schema-conformance", "tests/test_schema_conformance.py"):
        assert needed in guard, (
            f"the schema proof no longer runs when {needed} changed: a proof that only runs for "
            f"some of the files it proves is a gate whose own proof nothing runs"
        )


def test_the_facts_rung_is_not_scoped_for_speed():
    """The facts rung is deliberately unconditional: it re-executes the estate's active facts, and
    it protects epistemic integrity rather than the diff. It is not a speed knob, and a change
    that made it conditional would have to be argued in a commit message, not slipped in."""
    text = CI.read_text()
    start = text.find("facts_n=0")
    assert start != -1, "the facts rung is gone: no fact store is re-executed any more"
    end = text.find('say "skip  facts', start)
    assert end != -1, (
        "the facts rung no longer reports the no-store case it must never pass silently"
    )
    # The guard, if one were added, would sit ABOVE the loop it scopes -- so the window starts a
    # little before the first line of the rung, at the nearest blank line, and not at `facts_n=0`.
    window_start = text.rfind("\n\n", 0, start) + 1
    block = text[window_start:end]
    assert "touched" not in block, (
        "the facts rung has been put behind a touched() guard: it is unconditional by design, "
        "because it protects the estate's facts and not the diff"
    )
    assert "facts_n=0" in block, (
        "the facts rung no longer counts the stores it executes"
    )
    assert "estate-claim-check" in block, (
        "the facts rung no longer re-executes its stores"
    )
    assert 'say "FAIL  facts' in block, "the facts rung can no longer fail"


def test_the_verdict_is_written_where_the_fast_path_exits():
    """The cache is only a cache if the run that earns it writes it. The fast path prints its PASS
    line and exits immediately; a writer placed at the end of the script is never reached by a
    fast run, so every retry re-paid the whole gate (measured 2026-11-08)."""
    text = CI.read_text()
    fast_exit = text.find('say "ok    fast-gate: ruff"')
    assert fast_exit != -1, "the fast gate's own PASS line is gone"
    # The next `exit` after the fast PASS line closes the fast path.
    fast_path_end = text.find('exit "$fail"', fast_exit)
    assert fast_path_end != -1, "the fast path no longer exits"
    fast_path = text[fast_exit:fast_path_end]
    # The file must actually be CREATED on this path. Naming the directory is not writing a
    # verdict: the writer is the touch against the head-and-base key.
    assert 'touch "$HOME/.cache/idp-ci-verified/${_head}-${_base}"' in fast_path, (
        "the scoped verdict is not written on the fast path: a fast run prints PASS and exits "
        "before reaching any writer at the end of the script, so the hook's cache read never hits"
    )


def test_the_proof_suites_fan_out_when_xdist_is_available():
    """The schema proof costs 29 s serially because every one of its 36 tests spawns a process.
    The flag was defined hundreds of lines below the rung that needed it, so the rung blamed
    `set -u` and ran serial forever. A missing xdist is serial; an available one must be used."""
    text = CI.read_text()
    assert 'XD_MP=""; "$MPY" -c \'import xdist\'' in text, (
        "the fan-out flag for the proof suites is not defined next to the interpreter that runs "
        "them, so the suites run serially by default"
    )
    assert "$XD_MP" in text, "the fan-out flag is defined but never used"


def _stub_repo(tmp_path: Path) -> tuple[Path, Path, str, str]:
    """A checkout with the real hook, a gate that announces itself, and a claim gate that passes.

    The hook is the code under test; everything it calls is stubbed so the measurement is about
    the hook's own decision and not about how long the estate's gate takes."""
    repo = tmp_path / "repo"
    (repo / "bin").mkdir(parents=True)
    (repo / ".githooks").mkdir()
    shutil.copy(HOOK, repo / ".githooks" / "pre-push")
    os.chmod(repo / ".githooks" / "pre-push", 0o700)
    (repo / "bin" / "idp-ci").write_text("#!/usr/bin/env bash\necho STUB-GATE-RAN\n")
    os.chmod(repo / "bin" / "idp-ci", 0o700)
    (repo / "bin" / "claim-gate").write_text(
        "#!/usr/bin/env bash\necho 'ok    claim-gate stub'\n"
    )
    os.chmod(repo / "bin" / "claim-gate", 0o700)

    env = {
        **os.environ,
        "HOME": str(tmp_path / "home"),
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
    }
    (tmp_path / "home").mkdir()

    def git(*args: str) -> str:
        out = subprocess.run(
            ("git", *args),
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        return out.stdout.strip()

    git("init", "-q")
    git("checkout", "-q", "-b", "main")
    (repo / "hello.txt").write_text("hello\n")
    git("add", "-A")
    git("-c", "user.email=t@example", "-c", "user.name=t", "commit", "-q", "-m", "base")
    base = git("rev-parse", "HEAD")
    git("update-ref", "refs/remotes/origin/main", base)
    (repo / "hello.txt").write_text("hello again\n")
    git("add", "-A")
    git("-c", "user.email=t@example", "-c", "user.name=t", "commit", "-q", "-m", "work")
    head = git("rev-parse", "HEAD")
    return repo, tmp_path / "home", head, base


def _push(repo: Path, home: Path, head: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(repo / ".githooks" / "pre-push")],
        cwd=repo,
        input=f"refs/heads/lane/probe {head} refs/heads/lane/probe {'0' * 40}\n",
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "HOME": str(home),
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
        },
    )


def test_a_push_of_an_already_graded_diff_does_not_run_the_gate_again(tmp_path):
    """The retry has to be cheap. A verdict on disk for this exact diff is read, not recomputed."""
    repo, home, head, base = _stub_repo(tmp_path)
    verdict = home / ".cache" / "idp-ci-verified" / f"{head}-{base}"
    verdict.parent.mkdir(parents=True)
    verdict.write_text("")

    result = _push(repo, home, head)
    assert result.returncode == 0, result.stderr
    assert "STUB-GATE-RAN" not in result.stdout, (
        "the gate ran again for a diff that was already graded green: the retry pays the whole "
        "gate a second time, which is how one session's friction became every session's"
    )
    assert "already graded green" in result.stdout, (
        "the hook did not report that it read the verdict instead of recomputing it"
    )


def test_a_verdict_about_another_base_is_not_used(tmp_path):
    """The key carries the base as well as the head. Once main moves, the same commit is a
    different diff, and a verdict about the old one is not proof about the new. A cache keyed by
    head alone would read that stale verdict, so a verdict for another base is planted at BOTH
    the head-only path and the real head-other-base path: only a key that names the base can
    tell them apart."""
    repo, home, head, base = _stub_repo(tmp_path)
    cache = home / ".cache" / "idp-ci-verified"
    cache.mkdir(parents=True)
    # A verdict earned against a different base (and at the head-only path, which a key that
    # forgot the base would consult).
    other_base = "0" * 40
    assert other_base != base, "the stub's base must differ from the borrowed one"
    (cache / f"{head}-{other_base}").write_text("")
    (cache / head).write_text("")

    result = _push(repo, home, head)
    assert result.returncode == 0, result.stderr
    assert "STUB-GATE-RAN" in result.stdout, (
        "the hook reused a verdict that was graded against a different base: the same commit is "
        "a different diff once main moves"
    )


def test_an_ungraded_diff_still_runs_the_gate(tmp_path):
    """The cache is an optimisation, never a bypass: a diff with no verdict on disk is graded."""
    repo, home, head, _base = _stub_repo(tmp_path)
    result = _push(repo, home, head)
    assert result.returncode == 0, result.stderr
    assert "STUB-GATE-RAN" in result.stdout, (
        "an ungraded diff was pushed without being graded"
    )
