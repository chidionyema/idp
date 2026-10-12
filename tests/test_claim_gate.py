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


def test_an_unlabelled_issue_is_no_longer_a_reason_to_refuse():
    # 2026-10-10, founder "b": the `in-progress` label was a second way to say what the
    # heartbeat already says, so it is gone. This test is the contract: an open issue with a
    # live claim comment passes whether or not anybody remembered to label it.
    assert run(issue=_issue(labels=(), claim=_claim())) == []


def test_a_claim_comment_without_the_model_field_still_passes():
    # model= was read by nothing; it is now optional rather than required.
    hb = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
    bare = f"CLAIM agent=idp-60 paths=bin/voice-*,tests/test_voice* heartbeat={hb}"
    assert run(issue=_issue(claim=bare)) == []


def test_no_claim_line_is_refused():
    assert "no `Claim:" in run(text="fix: a thing\n")[0]


def test_no_agent_line_is_refused():
    assert "no `Agent:" in run(text="fix\n\nClaim: #12\n")[0]


def test_another_agents_claim_is_refused():
    out = run(issue=_issue(claim=_claim(agent="idp-57")))
    assert "claimed by idp-57, not idp-60" in out[0]


def test_a_range_naming_two_agents_is_refused():
    # 2026-10-12: `git log --format=%B` prints newest first and the gate read `agents[-1]`, i.e.
    # the OLDEST commit's trailer. So a second agent's commits passed whenever the claim holder
    # happened to be the older one. Measured before the fix: this exact range was judged clear
    # against a claim held by idp-99, while idp-60 wrote to files only idp-99 had claimed.
    two = (
        "fix(voice): the newer commit\n\nClaim: Mumchimp/crew#12\nAgent: idp-60\n"
        "\nfix(voice): the older commit\n\nClaim: Mumchimp/crew#12\nAgent: idp-99\n"
    )
    out = run(text=two, issue=_issue(claim=_claim(agent="idp-99")))
    assert "names 2 agents" in out[0]
    assert "idp-60" in out[0] and "idp-99" in out[0]


def test_a_range_naming_one_agent_twice_still_passes():
    # The refusal above is about DIFFERENT names, not about a lane carrying several commits.
    # One agent's multi-commit lane is the ordinary case and must not be refused.
    two = (
        "fix(voice): the newer commit\n\nClaim: Mumchimp/crew#12\nAgent: idp-60\n"
        "\nfix(voice): the older commit\n\nClaim: Mumchimp/crew#12\nAgent: idp-60\n"
    )
    assert run(text=two) == []


def test_a_lapsed_heartbeat_is_refused():
    assert "lapsed" in run(issue=_issue(claim=_claim(age=timedelta(hours=3))))[0]


def test_a_closed_issue_is_refused():
    assert "not open" in run(issue=_issue(state="closed", claim=_claim()))[0]


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


def test_a_body_trailer_fix_is_seen_without_a_new_event(monkeypatch):
    """idp#5758 mechanism 3: a re-run judges the original pull_request event's body snapshot,
    so a trailer fix in the body stayed invisible and the gate failed identically (measured on
    run 38131990376). When PR_NUMBER is set the gate fetches the live body."""
    import subprocess as sp

    monkeypatch.setenv("PR_NUMBER", "5704")
    monkeypatch.delenv("PR_BODY", raising=False)

    def fake_run(argv, capture_output=False, text=False, timeout=None):
        assert argv[:2] == ["gh", "api"]
        return sp.CompletedProcess(
            argv, 0, "Claim: Mumchimp/idp#5755\nAgent: opencode\n", ""
        )

    g = _gate()
    monkeypatch.setattr(g.subprocess, "run", fake_run)
    assert "Claim: Mumchimp/idp#5755" in g.live_body("Mumchimp/idp")


def test_with_no_pr_number_the_snapshot_still_speaks(monkeypatch):
    monkeypatch.delenv("PR_NUMBER", raising=False)
    monkeypatch.setenv("PR_BODY", "Claim: Mumchimp/idp#1\nAgent: a\n")
    assert "Claim: Mumchimp/idp#1" in _gate().live_body("Mumchimp/idp")


def test_a_failed_fetch_falls_back_to_the_snapshot(monkeypatch):
    import subprocess as sp

    monkeypatch.setenv("PR_NUMBER", "5704")
    monkeypatch.setenv("PR_BODY", "Claim: Mumchimp/idp#1\nAgent: a\n")

    def fake_run(argv, capture_output=False, text=False, timeout=None):
        return sp.CompletedProcess(argv, 1, "", "gh: boom")

    g = _gate()
    monkeypatch.setattr(g.subprocess, "run", fake_run)
    assert "Claim: Mumchimp/idp#1" in g.live_body("Mumchimp/idp")
