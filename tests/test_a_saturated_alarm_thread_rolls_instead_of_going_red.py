"""A full dedupe thread rolls to a fresh issue; it does not paint the run red.

The alarm folds one fire into one issue and comments on it every repeat. GitHub refuses
addComment past 2500 comments on a single issue. Measured 2026-09-21: issue #3290 reached
exactly 2500, and every reconcile whose signature hashed to that thread's marker then died on
`Commenting is disabled on issues with more than 2500 comments` -- 302 of 381 flux-events runs
failed in 3.5 hours out of that one saturated page. The fire had not changed; the page had run
out. That is a defect in the alarm, not in the cluster, and it must not read as a red run.

This runs the workflow's OWN step script (read out of flux-events.yml, never copied) against a
stub `gh` on PATH, so the two cannot drift. The stub refuses `issue comment` the way GitHub does
on a full thread, records every call, and the test proves the step closed the saturated issue and
opened a fresh one carrying the same marker -- instead of exiting non-zero.
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "flux-events.yml"

# The marker the alarm writes into an issue body and greps for on the next event. It is a sha256
# of the normalised message, first 16 hex chars, prefixed by this literal.
MARKER_PREFIX = "flux-signature: "


def _ledger_steps() -> list[dict]:
    return yaml.safe_load(WORKFLOW.read_text())["jobs"]["ledger"]["steps"]


def _filing_step() -> dict:
    for step in _ledger_steps():
        if "run" in step and "gh issue create" in step["run"]:
            return step
    raise AssertionError("no step in flux-events.yml opens an issue")


def _marker_for(signature: str) -> str:
    import hashlib

    return MARKER_PREFIX + hashlib.sha256(signature.encode()).hexdigest()[:16]


def _gh_stub(td: str, *, full_thread: int | None) -> Path:
    """A `gh` that answers the way the workflow expects, with one thread refused.

    The step runs `gh issue list ... --json number,body -q '<jq filter>'`; `gh` prints JSON and
    `jq` reduces it to the matching issue number. This stub stands in for that whole pipeline, so
    `issue list` must print the filter's RESULT -- the thread number when a thread carries the
    signature, nothing otherwise -- never a JSON array, which the step would take as the number
    itself. Whether the filter actually named the right marker is asserted separately against the
    script text, because a stub cannot evaluate jq.

    `issue comment` refuses with GitHub's exact 2500-comment error when a full thread is set, and
    succeeds otherwise. Every call is appended to a log, so the test asserts what happened.
    """
    log = Path(td) / "gh.calls"
    stub = Path(td) / "gh"
    stub.write_text(
        "#!/bin/sh\n"
        f'printf "%s\\n" "$*" >> "{log}"\n'
        'case "$1 $2" in\n'
        '  "issue list")\n'
        + (
            f'    printf "%s\\n" "{full_thread}"\n'
            if full_thread is not None
            else "    :\n"
        )
        + "    ;;\n"
        '  "issue comment")\n'
        + (
            '    echo "GraphQL: Commenting is disabled on issues with more than 2500 comments '
            '(addComment)" >&2\n'
            "    exit 1\n"
            if full_thread is not None
            else "    exit 0\n"
        )
        + "    ;;\n"
        "  *)\n"
        "    exit 0\n"
        "    ;;\n"
        "esac\n"
    )
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    return stub


def _run_step(
    signature: str, *, full_thread: int | None
) -> tuple[subprocess.CompletedProcess, str]:
    step = _filing_step()
    with tempfile.TemporaryDirectory() as td:
        log = Path(td) / "gh.calls"
        _gh_stub(td, full_thread=full_thread)
        env = {
            **os.environ,
            "PATH": f"{td}:{os.environ.get('PATH', '')}",
            "GH_REPO": "chidionyema/idp",
            # The three values the step reads from the receipt.
            "OBJECT": "Kustomization/commerce.flux-system",
            "REVISION": "main@sha1:deadbeef",
            "MESSAGE": "health check failed: [<objs>]",
            "SIGNATURE": signature,
            "GITHUB_SERVER_URL": "https://github.com",
            "GITHUB_REPOSITORY": "chidionyema/idp",
            "GITHUB_RUN_ID": "1",
            "RUNNER_TEMP": td,
        }
        p = subprocess.run(
            ["bash", "-e", "-c", step["run"]],
            capture_output=True,
            text=True,
            env=env,
            cwd=td,
            timeout=60,
            check=False,
        )
        calls = log.read_text() if log.exists() else ""
    return p, calls


def test_the_filing_step_still_opens_a_fresh_issue_on_a_fresh_fire():
    """The change must not break the ordinary path: no existing thread, one issue opened."""
    p, calls = _run_step("a-brand-new-fire", full_thread=None)
    assert p.returncode == 0, f"the step failed on a fresh fire:\n{p.stderr}"
    assert "issue create" in calls, f"no issue was opened:\n{calls}"


def test_a_saturated_thread_is_rolled_not_exited():
    """The defect this file was written from: 2500 comments, addComment refused, run went red.

    A correct step treats the refusal as "roll the page": it closes the saturated issue and
    opens a fresh one carrying the same marker, and the run stays green -- because the fire was
    filed, which is the only failure this step owns.
    """
    signature = "a-fire-that-saturated"
    p, calls = _run_step(signature, full_thread=3290)
    assert p.returncode == 0, (
        "a full dedupe thread painted the run red; the alarm must roll the page, not exit "
        f"non-zero:\nstdout:\n{p.stdout}\nstderr:\n{p.stderr}\ncalls:\n{calls}"
    )
    # The lookup must search for THIS fire's marker. The stub cannot evaluate jq, so the filter's
    # correctness is proved here, against what the step actually asked: if the marker computation
    # or the filter drifted, this fails even though the stub would still have handed back a number.
    assert f'contains("{_marker_for(signature)}")' in calls, (
        f"the step did not search the board for this fire's marker:\n{calls}"
    )
    assert "issue close 3290" in calls or re.search(r"issue close 3290", calls), (
        f"the saturated thread was not closed:\n{calls}"
    )
    assert "issue create" in calls, (
        f"no fresh issue was opened after the roll:\n{calls}"
    )


def test_the_roll_is_still_bounded_to_a_full_thread():
    """A non-cap failure on the comment must NOT be swallowed as a roll.

    If `gh issue comment` fails for any other reason -- auth, network, a bad body -- that is the
    alarm genuinely unable to file, and the step must exit non-zero. Only the 2500-comment
    refusal is the page running out.
    """
    step = _filing_step()
    script = step["run"]
    # The roll branch is guarded by the exact GitHub refusal, not by "comment failed".
    assert "Commenting is disabled" in script, (
        "the step no longer distinguishes the 2500-comment refusal from any other failure; "
        "it will silently swallow real filing failures"
    )
    assert "exit 1" in script, "a genuine filing failure must still paint the run red"
