"""claim-gate refuses a change nobody declared (AGENTS.md §5), and passes one that lands on a live claim.

Founder, 2026-09-30: "we can't afford all this chaos"; "not seeing any enforcement". Each test is a
way an undeclared or colliding change would otherwise land.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "bin" / "claim-gate"
NOW = datetime(2026, 9, 30, 20, 0, tzinfo=timezone.utc)


def _gate():
    loader = importlib.machinery.SourceFileLoader("claim_gate", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _issue(state="open", labels=("in-progress",), claim=None):
    comments = [{"body": claim}] if claim else []
    return {"state": state, "labels": [{"name": n} for n in labels]}, comments


def _claim(
    agent="idp-60", paths="bin/voice-*,tests/test_voice*", age=timedelta(minutes=10)
):
    hb = (NOW - age).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"CLAIM agent={agent} model=claude-opus paths={paths} heartbeat={hb}"


MSG = "fix(voice): a thing\n\nClaim: Mumchimp/crew#12\nAgent: idp-60\n"
FILES = ["bin/voice-doctor", "tests/test_voice_doctor.py"]


def run(text=MSG, files=FILES, issue=None):
    g = _gate()
    iss = issue or _issue(claim=_claim())
    return g.verdict(text, files, "Mumchimp/idp", lambda r, n: iss, NOW)


def test_a_change_on_a_live_claim_passes():
    assert run() == []


def test_no_claim_line_is_refused():
    assert "no `Claim:" in run(text="fix: a thing\n")[0]


def test_no_agent_line_is_refused():
    assert "no `Agent:" in run(text="fix\n\nClaim: #12\n")[0]


def test_another_agents_claim_is_refused():
    out = run(issue=_issue(claim=_claim(agent="idp-57")))
    assert "claimed by idp-57, not idp-60" in out[0]


def test_a_lapsed_heartbeat_is_refused():
    assert "lapsed" in run(issue=_issue(claim=_claim(age=timedelta(hours=3))))[0]


def test_a_closed_or_unlabelled_issue_is_refused():
    assert "not open" in run(issue=_issue(state="closed", claim=_claim()))[0]
    assert "not labelled in-progress" in run(issue=_issue(labels=(), claim=_claim()))[0]


def test_files_outside_the_claim_are_refused():
    out = run(files=FILES + ["platform/llm/config.yaml"])
    assert "outside every claim's paths: platform/llm/config.yaml" in out[0]


def test_an_issue_with_no_claim_comment_is_refused():
    assert "no CLAIM comment" in run(issue=_issue())[0]


def test_only_image_tag_bumps_are_exempt_by_content_not_by_author_name():
    g = _gate()
    bump = '--- a/k.yaml\n+++ b/k.yaml\n-  newTag: a # {"$imagepolicy": "flux-system:x:tag"}\n+  newTag: b # {"$imagepolicy": "flux-system:x:tag"}\n'
    assert g.image_bump_only(bump)
    assert not g.image_bump_only(bump + "+  replicas: 9\n")
    assert not g.image_bump_only("")


def _sh(cwd, *a):
    import subprocess

    return subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", *a],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def test_a_squash_whose_lane_head_is_gone_is_judged_on_its_own_message(
    tmp_path, monkeypatch
):
    # 2026-10-08, PR #5511: land() force-pushed the squash over the lane branch, the
    # Greenlane-Head sha was on no ref, and `git log base..<head>` crashed claim-gate (exit 128)
    # on a change it had passed minutes earlier. The lane requeued twice.
    _sh(tmp_path, "init", "-q", "-b", "main")
    _sh(tmp_path, "config", "user.email", "t@t")
    _sh(tmp_path, "config", "user.name", "t")
    _sh(tmp_path, "commit", "-q", "--allow-empty", "-m", "base")
    base = _sh(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "voice-doctor").write_text("x\n")
    _sh(tmp_path, "add", "-A")
    gone = "f" * 40
    _sh(
        tmp_path,
        "commit",
        "-q",
        "-m",
        f"fix(voice): a thing\n\nGreenlane-Head: {gone}\n\nClaim: Mumchimp/crew#12\nAgent: idp-60\n",
    )
    head = _sh(tmp_path, "rev-parse", "HEAD")
    monkeypatch.chdir(tmp_path)
    g = _gate()
    iss = _issue(claim=_claim())
    assert g.judge(base, head, "Mumchimp/idp", lambda r, n: iss, NOW, "", "") == []
    refused = _issue(claim=_claim(paths="tests/*"))
    out = g.judge(base, head, "Mumchimp/idp", lambda r, n: refused, NOW, "", "")
    assert "outside every claim's paths: bin/voice-doctor" in out[0]
