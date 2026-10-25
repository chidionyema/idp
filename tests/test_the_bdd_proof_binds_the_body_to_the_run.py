"""The proof gate grades the pull request's body now, against the commit this run tested.

Measured 2026-10-25, on this gate's own pull request (#7167, run 40245349600 attempt 2). The
rung dumped `pid.pull_request` out of `GITHUB_EVENT_PATH` and graded that. A re-run replays the
payload GitHub froze when the run was created, body and all -- so the rung refused a pull request
whose body had already been corrected:

    refused: the proof names ced59a268, but the pull request's head is b9a59de20889

The proof was right; the gate was grading a photograph of it. The author's only recourse was to
push a new commit purely to refresh a snapshot, and that is the re-run loop AGENTS.md section 2
forbids. So the payload now supplies what is frozen and correct -- which pull request this is, and
the head commit this run graded -- and the body is read live.

These tests fix that shape in place, in both directions: the live body wins when gh can read it,
the payload body is still graded (named) when gh cannot, and the head being compared is always
the commit this run tested, never one the branch moved to mid-run.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "bin" / "idp-bdd-proof-gate"

TESTED = "b9a59de208895f434b68add9b8a0f5a7e875b669"
FROZEN = "ced59a268559ec0ed4ee1b4e4a0e8c8b0f7a9c1d"
MOVED = "0badc0de1234567890abcdef1234567890abcdef"

PROOF = "BDD-PROOF\nhead: {head}\n50 passed in 44.43s\nEND-BDD-PROOF"


def _payload(tmp_path: Path, *, body_head: str, head: str = TESTED) -> Path:
    """A frozen GitHub pull_request payload, as a re-run replays it."""
    p = tmp_path / "event.json"
    p.write_text(
        json.dumps(
            {
                "action": "synchronize",
                "pull_request": {
                    "number": 7167,
                    "title": "fix(voice): confirmation ladder and agent target become data",
                    "body": PROOF.format(head=body_head),
                    "head": {"sha": head},
                },
            }
        )
    )
    return p


def _gh(tmp_path: Path, *, body_head: str | None, head: str = TESTED) -> Path:
    """A `gh pr view` on PATH. `body_head=None` makes gh fail, like a job with no token."""
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    script = bindir / "gh"
    if body_head is None:
        script.write_text("#!/bin/sh\necho 'gh: authentication required' >&2\nexit 4\n")
    else:
        row = {
            "number": 7167,
            "title": "fix(voice): confirmation ladder and agent target become data",
            "body": PROOF.format(head=body_head),
            "headRefOid": head,
        }
        script.write_text(f"#!/bin/sh\ncat <<'JSON'\n{json.dumps(row)}\nJSON\n")
    script.chmod(0o755)
    return bindir


def _run(tmp_path: Path, *, env_extra: dict, gh: Path | None = None):
    env = {
        k: v
        for k, v in os.environ.items()
        if k
        not in ("GITHUB_EVENT_PATH", "GITHUB_HEAD_REF", "BDD_PR_HEAD", "BDD_RUN_HEAD")
    }
    env["GITHUB_EVENT_PATH"] = str(tmp_path / "event.json")
    env["PATH"] = f"{gh}:{env['PATH']}" if gh else env["PATH"]
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(GATE), "--live"],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )


def test_the_corrected_body_passes_even_though_the_run_replays_a_stale_payload(
    tmp_path,
):
    """The exact production refusal. This is the test that would have turned CI green."""
    _payload(tmp_path, body_head=FROZEN)  # frozen payload: proved an older commit
    gh = _gh(tmp_path, body_head=TESTED)  # the PR now names the commit under test
    out = _run(tmp_path, env_extra={}, gh=gh)
    assert out.returncode == 0, out.stderr
    assert TESTED in out.stdout
    assert "gh pr view" in out.stdout, "the gate did not say which body it read"


def test_a_stale_body_is_still_refused_when_gh_cannot_read_the_pull_request(tmp_path):
    """No token is not a licence to pass: the payload's body is graded, and named as such."""
    _payload(tmp_path, body_head=FROZEN)
    gh = _gh(tmp_path, body_head=None)
    out = _run(tmp_path, env_extra={}, gh=gh)
    assert out.returncode == 1
    assert FROZEN in out.stderr
    assert "event payload" in out.stderr


def test_a_payload_body_on_the_tested_head_passes_with_no_token(tmp_path):
    """A token-less job still gets a real verdict, not BLIND -- deck the fallback honestly."""
    _payload(tmp_path, body_head=TESTED)
    gh = _gh(tmp_path, body_head=None)
    out = _run(tmp_path, env_extra={}, gh=gh)
    assert out.returncode == 0, out.stderr


def test_the_head_compared_is_the_commit_this_run_tested_not_the_moved_branch(tmp_path):
    """The branch can move mid-run; this run graded TESTED, so the proof must name TESTED."""
    _payload(tmp_path, body_head=TESTED, head=TESTED)
    gh = _gh(tmp_path, body_head=TESTED, head=MOVED)  # PR has since been re-headed
    out = _run(tmp_path, env_extra={}, gh=gh)
    assert out.returncode == 0, out.stderr
    assert TESTED in out.stdout
    assert MOVED not in out.stdout


def test_a_push_event_is_skipped_by_name_not_graded(tmp_path):
    (tmp_path / "event.json").write_text(json.dumps({"ref": "refs/heads/main"}))
    out = _run(tmp_path, env_extra={}, gh=None)
    assert out.returncode == 3
    assert "no pull request" in out.stderr


def test_a_body_with_no_block_is_refused_and_says_where_it_read_it(tmp_path):
    p = tmp_path / "event.json"
    p.write_text(
        json.dumps(
            {
                "pull_request": {
                    "number": 7167,
                    "title": "t",
                    "body": "no proof",
                    "head": {"sha": TESTED},
                }
            }
        )
    )
    gh = _gh(tmp_path, body_head=None)
    out = _run(tmp_path, env_extra={}, gh=gh)
    assert out.returncode == 1
    assert "carries no BDD-PROOF" in out.stderr


def test_the_file_path_and_the_live_path_grade_the_same_pull_request_the_same_way(
    tmp_path,
):
    """One grader, two doors. `--live` used to check only that a block existed."""
    pr = tmp_path / "pr.json"
    pr.write_text(
        json.dumps(
            {
                "number": 1,
                "title": "t",
                "body": PROOF.format(head=FROZEN),
                "headRefOid": TESTED,
            }
        )
    )
    env = {k: v for k, v in os.environ.items() if not k.startswith("BDD_")}
    env.pop("GITHUB_EVENT_PATH", None)
    file_run = subprocess.run(
        [sys.executable, str(GATE), str(pr)],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    _payload(tmp_path, body_head=FROZEN)
    gh = _gh(tmp_path, body_head=None)
    live_run = _run(tmp_path, env_extra={}, gh=gh)
    assert file_run.returncode == live_run.returncode == 1, (
        file_run.stderr,
        live_run.stderr,
    )
    assert "the proof names" in file_run.stderr and "the proof names" in live_run.stderr
