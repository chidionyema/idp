"""claim-gate refuses a change nobody declared (AGENTS.md §5), and passes one that lands on a live claim.

Founder, 2026-09-30: "we can't afford all this chaos"; "not seeing any enforcement". Each test is a
way an undeclared or colliding change would otherwise land.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
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


def test_a_lapsed_heartbeat_nobody_took_over_still_lands():
    """A pull request that waits past two hours is not a collision (#6198, #6208 on 10-14)."""
    assert run(issue=_issue(claim=_claim(age=timedelta(hours=30)))) == []


def test_a_claim_taken_over_after_it_lapsed_is_refused():
    """Lapsing is what lets the next agent claim; once they have, the old holder cannot land."""
    old = _claim(age=timedelta(hours=3))
    rival = _claim(agent="idp-77")
    iss = ({"state": "open", "labels": []}, [{"body": old}, {"body": rival}])
    assert "claimed by idp-77, not idp-60" in run(issue=iss)[0]


def test_a_heartbeat_from_the_future_is_refused():
    assert "future" in run(issue=_issue(claim=_claim(age=-timedelta(hours=5))))[0]


def test_a_closed_issue_is_refused():
    assert "not open" in run(issue=_issue(state="closed", claim=_claim()))[0]


def test_files_outside_the_claim_are_refused():
    out = run(files=FILES + ["platform/llm/config.yaml"])
    assert "outside every claim's paths: platform/llm/config.yaml" in out[0]


def test_a_claim_names_a_dynamic_route_literally_and_covers_it():
    # A Next.js dynamic route's literal path carries glob metacharacters:
    # `web/app/writing/[slug]/page.tsx`. `claim-open` posts the changed files as literals, so the
    # claim holds that exact string -- and fnmatch read `[slug]` as a character class, so the file
    # matched no claim at all and could not satisfy its own (measured 2026-10-17: `FAIL claim-gate
    # 1 file(s) outside every claim's paths: web/app/writing/[slug]/page.tsx`). A claimant who
    # names a file has claimed that file.
    route = "web/app/writing/[slug]/page.tsx"
    assert run(files=[route], issue=_issue(claim=_claim(paths=route))) == []


def test_a_glob_in_a_claim_still_covers_many_files():
    # The literal comparison must not be the only one: `paths=web/**` covers a tree.
    files = ["web/app/page.tsx", "web/app/layout.tsx"]
    assert run(files=files, issue=_issue(claim=_claim(paths="web/**"))) == []


def test_a_claim_naming_one_bracketed_route_does_not_cover_its_siblings():
    # The fix widens coverage to the file named, not to anything containing brackets.
    named = "web/app/writing/[slug]/page.tsx"
    sibling = "web/app/writing/other/page.tsx"
    out = run(files=[named, sibling], issue=_issue(claim=_claim(paths=named)))
    assert f"outside every claim's paths: {sibling}" in out[0]


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


def test_the_lane_stage_asks_which_pull_request_the_head_is(monkeypatch):
    """The Greenlane runs this gate one stage before CI, on a LANE, and exports none of the pull
    request context ci.yml exports (greenlane/github.py::unclaimed). A lane whose two trailers
    live in its pull request body -- allowed by AGENTS.md §5 rule 5 and read by judge() -- was
    held with `no live claim`, measured 2026-10-15 on #6202 and #6198 (both green, both
    mergeable). With nothing in the environment the gate now asks GitHub; it must not guess."""
    g = _gate()
    monkeypatch.delenv("PR_NUMBER", raising=False)
    monkeypatch.delenv("PR_AUTHOR", raising=False)
    asked: list[tuple[str, str]] = []

    def fake(repo, head):
        asked.append((repo, head))
        return "6202", "otto"

    monkeypatch.setattr(g, "pr_of_head", fake)
    assert g.pr_context("chidionyema/idp", "d4ed1c50f") == ("6202", "otto")
    assert asked == [("chidionyema/idp", "d4ed1c50f")]


def test_ci_pays_nothing_for_the_lane_stages_lookup(monkeypatch):
    """ci.yml sets both variables, so a pull request run must not go to the network at all."""
    g = _gate()
    monkeypatch.setenv("PR_NUMBER", "6202")
    monkeypatch.setenv("PR_AUTHOR", "otto")
    monkeypatch.setattr(
        g,
        "pr_of_head",
        lambda repo, head: (_ for _ in ()).throw(AssertionError("asked the network")),
    )
    assert g.pr_context("chidionyema/idp", "d4ed1c50f") == ("6202", "otto")


def test_only_the_open_pull_request_supplies_the_body(monkeypatch):
    import subprocess as sp

    g = _gate()
    monkeypatch.setattr(
        g.subprocess,
        "run",
        lambda argv, **kw: sp.CompletedProcess(
            argv,
            0,
            json.dumps(
                [
                    {"number": 1, "state": "closed", "user": {"login": "a"}},
                    {"number": 6202, "state": "open", "user": {"login": "otto"}},
                ]
            ),
            "",
        ),
    )
    assert g.pr_of_head("chidionyema/idp", "d4ed1c50f") == ("6202", "otto")


def test_a_lookup_that_cannot_run_supplies_nothing(monkeypatch):
    import subprocess as sp

    g = _gate()
    monkeypatch.setattr(
        g.subprocess,
        "run",
        lambda argv, **kw: sp.CompletedProcess(argv, 1, "", "gh: boom"),
    )
    assert g.pr_of_head("chidionyema/idp", "d4ed1c50f") == ("", "")


def test_a_landed_lane_reads_the_body_of_its_pull_request(monkeypatch):
    """judge()'s lane path reads the lane branch's commit messages, so a body-declared lane was
    refused one stage later, inside the batch. The batch commit names the lane head; the body of
    the pull request that head belongs to is part of the declaration."""
    g = _gate()
    monkeypatch.setattr(g, "pr_of_head", lambda repo, sha: ("6202", "otto"))
    monkeypatch.setattr(
        g, "live_body", lambda repo, num="": "Claim: #6228\nAgent: otto\n"
    )
    assert (
        g.lane_body("chidionyema/idp", "d4ed1c50f", "abc1234")
        == "Claim: #6228\nAgent: otto\n"
    )


def test_runner_pin_only_passes_without_a_claim(tmp_path, monkeypatch):
    # GitHub retires ubuntu-latest; pinning to ubuntu-NN.NN is mechanical infrastructure
    # hygiene that does not belong to any agent. A commit that only changes runs-on in
    # workflow files passes without Claim:/Agent:.
    _sh(tmp_path, "init", "-q", "-b", "main")
    _sh(tmp_path, "config", "user.email", "t@t")
    _sh(tmp_path, "config", "user.name", "t")
    _sh(tmp_path, "commit", "-q", "--allow-empty", "-m", "base")
    base = _sh(tmp_path, "rev-parse", "HEAD")
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github/workflows").mkdir()
    (tmp_path / ".github/workflows/ci.yml").write_text(
        "name: ci\non:\n  push:\njobs:\n  test:\n    runs-on: ubuntu-24.04\n    steps:\n      - run: echo hi\n"
    )
    _sh(tmp_path, "add", "-A")
    _sh(tmp_path, "commit", "-q", "-m", "fix(ci): pin ubuntu runner")
    head = _sh(tmp_path, "rev-parse", "HEAD")
    monkeypatch.chdir(tmp_path)
    g = _gate()
    assert g.judge(base, head, "Mumchimp/idp", lambda r, n: _issue(), NOW, "", "") == []


def test_a_failed_fetch_falls_back_to_the_snapshot(monkeypatch):
    import subprocess as sp

    monkeypatch.setenv("PR_NUMBER", "5704")
    monkeypatch.setenv("PR_BODY", "Claim: Mumchimp/idp#1\nAgent: a\n")

    def fake_run(argv, capture_output=False, text=False, timeout=None):
        return sp.CompletedProcess(argv, 1, "", "gh: boom")

    g = _gate()
    monkeypatch.setattr(g.subprocess, "run", fake_run)
    assert "Claim: Mumchimp/idp#1" in g.live_body("Mumchimp/idp")
