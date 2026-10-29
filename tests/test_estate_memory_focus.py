"""Active Focus is read from the claim ledger, ghosts never reach an agent, and memory + focus are
enforced where agents work (idp#6543 follow-on).

What is graded is the behaviour at the two doors every runtime uses -- the stdio bridge an agent's
`brief`/`recall` call passes through, and the PreToolUse/Stop hooks -- with GitHub stood in for,
because a test must not depend on the network the estate itself calls flaky.
"""

import importlib.machinery
import importlib.util
import json
import time
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "platform", "estate", "memory"))
import focus  # noqa: E402


def script(name):
    path = os.path.join(ROOT, "bin", name)
    loader = importlib.machinery.SourceFileLoader(name.replace("-", "_"), path)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


NOW = 1_800_000_000.0


def iso(age_s):
    import time

    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - age_s))


def issue(n, title, *comments):
    return {"number": n, "title": title, "comments": [{"body": c} for c in comments]}


def claim(agent, paths, age_s):
    return f"CLAIM agent={agent} paths={paths} heartbeat={iso(age_s)}"


# --- ghosts: a closed claim's focus fact never leaves the bridge -----------------------------------


def closed(n, p, c, path):
    return "CLOSED" if n == 6525 else "OPEN"


def test_scrub_drops_a_closed_claims_focus_fact_from_brief_and_recall(tmp_path):
    ghost = {"text": "ACTIVE FOCUS claim idp6525: lane verdicts"}
    live = {"text": "ACTIVE FOCUS claim idp6579: dns-01"}
    other = {"text": "a plain decision"}
    brief = {"relevant": [ghost, live], "recent": [other, dict(ghost)]}
    recall = {"memories": [ghost, other]}
    p = str(tmp_path / "c.json")
    d1 = focus.scrub("brief", brief, closed, p)
    d2 = focus.scrub("recall", recall, closed, p)
    assert len(d1) == 2 and len(d2) == 1
    assert brief == {"relevant": [live], "recent": [other]}
    assert recall == {"memories": [other]}


def test_an_unknown_claim_state_keeps_the_fact(tmp_path):
    item = {"text": "ACTIVE FOCUS claim idp1: x"}
    kept, dropped = focus.drop_stale([item], lambda *a: None, str(tmp_path / "c.json"))
    assert kept == [item] and not dropped


def test_a_closed_state_is_cached_for_minutes_not_an_hour():
    # an hour of cache kept a ghost alive for 60 minutes after its issue closed
    assert focus.STATE_TTL_S <= 600 and focus.FOCUS_TTL_S <= 600


def test_the_bridge_retires_ghosts_in_both_result_shapes_and_adds_the_register(
    monkeypatch, tmp_path
):
    bridge = script("estate-memory-mcp")
    monkeypatch.setattr(
        bridge.focus, "claim_state", lambda n, p, c, path: closed(n, p, c, path)
    )
    monkeypatch.setenv("ESTATE_MEMORY_HOME", str(tmp_path))
    rows = [{"claim": "idp#6579", "live": True}]
    monkeypatch.setattr(bridge.focus, "live_focus", lambda: rows)
    payload = {
        "relevant": [{"text": "ACTIVE FOCUS claim idp6525: dead"}],
        "recent": [{"text": "kept"}],
    }
    result = {
        "structuredContent": json.loads(json.dumps(payload)),
        "content": [{"type": "text", "text": json.dumps(payload)}],
    }
    bridge.Bridge().retire_ghosts("brief", result)
    assert result["structuredContent"]["relevant"] == []
    text = json.loads(result["content"][0]["text"])
    assert text["relevant"] == [] and text["recent"] == [{"text": "kept"}]
    assert result["structuredContent"]["active_focus"] == rows
    assert text["active_focus"] == rows


def test_the_bridge_never_raises_on_a_result_it_cannot_read():
    bridge = script("estate-memory-mcp")
    result = {"content": [{"type": "text", "text": "not json"}]}
    bridge.Bridge().retire_ghosts("recall", result)  # must not raise
    assert result["content"][0]["text"] == "not json"


# --- the register: focus is the ledger, not a typed fact ------------------------------------------


def test_the_register_takes_the_newest_claim_and_marks_lapsed_ones():
    rows = focus.register_from_issues(
        [
            issue(
                1,
                "refreshed",
                claim("a", "bin/x", 9000),  # first claim: lapsed on its own
                claim("a", "bin/x", 60),  # heartbeat since: live
            ),
            issue(2, "abandoned", claim("b", "docs/*", 3 * 3600)),
            issue(3, "no claim at all", "just a comment"),
        ],
        NOW,
    )
    assert [r["claim"] for r in rows] == [
        "idp#1",
        "idp#2",
    ]  # live first, unclaimed absent
    assert rows[0]["live"] is True and rows[0]["heartbeat_age_s"] == 60
    assert rows[1]["live"] is False


def test_a_closed_issue_cannot_be_in_the_register():
    # the register is built from `--state open`: closing a claim is what retires its focus.
    src = open(os.path.join(ROOT, "platform/estate/memory/focus.py")).read()
    assert '"--state",\n            "open"' in src


def test_render_lists_live_claims_counts_lapsed_ones_and_unknown_renders_nothing():
    rows = focus.register_from_issues(
        [
            issue(1, "live work", claim("a", "bin/x,bin/y,bin/z", 60)),
            issue(2, "abandoned", claim("b", "docs/*", 3 * 3600)),
        ],
        NOW,
    )
    text = focus.render_register(rows)
    assert "idp#1 a: live work" in text and "+1 more" in text
    assert "idp#2" not in text and "1 recently touched claims have lapsed" in text
    assert focus.render_register(None) == ""
    assert "no live claim" in focus.render_register([])


def test_the_ledger_is_asked_only_for_issues_a_heartbeat_could_have_touched(
    tmp_path, monkeypatch
):
    seen = {}

    def gh(args, timeout):
        seen["args"] = args
        return json.dumps([issue(6597, "new", claim("claude", "bin/x", 60))])

    monkeypatch.setattr(focus, "_gh", gh)
    monkeypatch.setattr(focus, "mark_stuck", lambda rows, now=0.0: rows)
    rows = focus.live_focus(str(tmp_path / "c.json"), NOW)
    query = seen["args"][seen["args"].index("--search") + 1]
    since = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - focus.LAPSE_S))
    # 2026-10-19: unfiltered, 130+ claimed issues came back in best-match order and a claim
    # refreshed minutes earlier was past the 50th row, so its own agent was refused its files.
    assert f"updated:>={since}" in query and "sort:updated-desc" in query
    assert [r["claim"] for r in rows] == ["idp#6597"]


# --- stuck detection: alive is not the same as moving ----------------------------------------------


def opened_claim(agent, paths, opened_age_s, heartbeat_age_s):
    return {
        "body": claim(agent, paths, heartbeat_age_s),
        "createdAt": iso(opened_age_s),
    }


def stuck_rows(issues, progress):
    rows = focus.register_from_issues(
        [{"number": n, "title": t, "comments": cs} for n, t, cs in issues],
        NOW,
    )
    return {r["claim"]: r for r in focus.mark_stuck(rows, progress, NOW)}


def test_a_live_old_claim_with_no_commit_since_it_opened_is_stuck():
    rows = stuck_rows(
        [(1, "t", [opened_claim("a", "bin/x", 6 * 3600, 60)])],
        lambda paths: NOW - 7 * 3600,  # the last commit predates the claim
    )
    assert rows["idp#1"]["stuck"] is True and rows["idp#1"]["idle_s"] == 6 * 3600


def test_a_commit_after_the_claim_opened_clears_it():
    rows = stuck_rows(
        [(1, "t", [opened_claim("a", "bin/x", 6 * 3600, 60)])],
        lambda paths: NOW - 600,
    )
    assert rows["idp#1"]["stuck"] is False


def test_a_young_lapsed_or_unknowable_claim_is_never_called_stuck():
    never = lambda paths: 0  # noqa: E731 - would flag anything it was asked about
    rows = stuck_rows(
        [
            (1, "young", [opened_claim("a", "bin/x", 600, 60)]),
            (2, "lapsed", [opened_claim("b", "bin/y", 9 * 3600, 5 * 3600)]),
            (3, "no timestamp", [{"body": claim("c", "bin/z", 60)}]),
        ],
        never,
    )
    assert not any(r["stuck"] for r in rows.values())
    unknown = stuck_rows(
        [(4, "t", [opened_claim("a", "bin/x", 6 * 3600, 60)])], lambda paths: None
    )
    assert unknown["idp#4"]["stuck"] is False


def test_git_is_asked_about_the_claims_paths_and_a_missing_repo_is_unknown(
    monkeypatch, tmp_path
):
    seen = {}

    class R:
        returncode, stdout = 0, "1799990000\n"

    def run(argv, **k):
        seen["argv"] = argv
        return R()

    monkeypatch.setattr(focus.subprocess, "run", run)
    assert focus.last_commit_touching("bin/a,docs/*") == 1799990000
    assert seen["argv"][-3:] == [
        "--",
        "bin/a",
        "docs/*",
    ]  # paths after `--`: never flags
    R.returncode = 128
    assert focus.last_commit_touching("bin/a") is None
    assert focus.last_commit_touching("") is None


def test_the_register_shows_stuck_claims_with_the_caveat():
    rows = stuck_rows(
        [(1, "slow", [opened_claim("a", "bin/x", 6 * 3600, 60)])], lambda p: 0
    )
    text = focus.render_register(list(rows.values()))
    assert "STUCK 6h" in text and "as of the last fetch" in text
    fine = stuck_rows([(2, "ok", [opened_claim("a", "bin/x", 60, 60)])], lambda p: 0)
    assert "STUCK" not in focus.render_register(list(fine.values()))


# --- enforcement ------------------------------------------------------------------------------------


@pytest.fixture
def enforce(monkeypatch, tmp_path):
    mod = script("estate-memory-enforce")
    monkeypatch.setenv("ESTATE_MEMORY_HOME", str(tmp_path))
    monkeypatch.delenv("ESTATE_AGENT", raising=False)
    monkeypatch.delenv("ESTATE_MEMORY_ENFORCE", raising=False)
    # /repo/... stands for an idp checkout; anything else is not one
    monkeypatch.setattr(
        mod, "git_root_if_idp", lambda p: "/repo" if p.startswith("/repo/") else None
    )
    return mod


def transcript(tmp_path, *blocks):
    path = tmp_path / "t.jsonl"
    path.write_text(
        "\n".join(json.dumps({"message": {"content": [b]}}) for b in blocks)
    )
    return str(path)


BRIEF_CALL = {"type": "tool_use", "name": "mcp__estate-memory__brief", "input": {}}
REMEMBER = {"type": "tool_use", "name": "mcp__estate-memory__remember", "input": {}}


def edit(path):
    return {"type": "tool_use", "name": "Edit", "input": {"file_path": path}}


def pre_call(enforce, capsys, tpath, path="/repo/bin/x"):
    enforce.pre(
        {
            "tool_name": "Edit",
            "tool_input": {"file_path": path},
            "transcript_path": tpath,
            "session_id": "s",
        }
    )
    out = capsys.readouterr().out
    return json.loads(out)["hookSpecificOutput"] if out else None


def live_row(agent="me", paths="bin/*"):
    return {
        "claim": "idp#1",
        "agent": agent,
        "paths": paths,
        "live": True,
        "heartbeat_age_s": 5,
        "title": "t",
    }


def test_an_unbriefed_session_is_refused_its_first_edit(
    enforce, capsys, tmp_path, monkeypatch
):
    monkeypatch.setattr(enforce.focus, "live_focus", lambda: [live_row()])
    monkeypatch.setattr(enforce, "git_root_if_idp", lambda p: "/repo")
    out = pre_call(
        enforce, capsys, transcript(tmp_path, {"type": "text", "text": "hi"})
    )
    assert (
        out["permissionDecision"] == "deny"
        and "brief" in out["permissionDecisionReason"]
    )


def test_a_briefed_session_with_a_covering_live_claim_passes(
    enforce, capsys, tmp_path, monkeypatch
):
    monkeypatch.setattr(enforce.focus, "live_focus", lambda: [live_row()])
    monkeypatch.setattr(enforce, "git_root_if_idp", lambda p: "/repo")
    assert pre_call(enforce, capsys, transcript(tmp_path, BRIEF_CALL)) is None


def test_the_session_start_hook_output_counts_as_briefed(
    enforce, capsys, tmp_path, monkeypatch
):
    monkeypatch.setattr(enforce.focus, "live_focus", lambda: [live_row()])
    monkeypatch.setattr(enforce, "git_root_if_idp", lambda p: "/repo")
    hook = {
        "type": "text",
        "text": "<estate-memory>\nContext the estate's agents wrote: facts",
    }
    assert pre_call(enforce, capsys, transcript(tmp_path, hook)) is None


def test_no_covering_claim_is_refused_with_the_command_to_fix_it(
    enforce, capsys, tmp_path, monkeypatch
):
    monkeypatch.setattr(enforce.focus, "live_focus", lambda: [live_row(paths="docs/*")])
    monkeypatch.setattr(enforce, "git_root_if_idp", lambda p: "/repo")
    out = pre_call(enforce, capsys, transcript(tmp_path, BRIEF_CALL))
    assert (
        out["permissionDecision"] == "deny"
        and "bin/claim-open" in out["permissionDecisionReason"]
    )


def test_a_file_another_agent_holds_is_refused_as_overlap(
    enforce, capsys, tmp_path, monkeypatch
):
    monkeypatch.setenv("ESTATE_AGENT", "me")
    monkeypatch.setattr(enforce.focus, "live_focus", lambda: [live_row(agent="them")])
    monkeypatch.setattr(enforce, "git_root_if_idp", lambda p: "/repo")
    out = pre_call(enforce, capsys, transcript(tmp_path, BRIEF_CALL))
    assert (
        out["permissionDecision"] == "deny"
        and "Another agent holds it" in out["permissionDecisionReason"]
    )


def test_a_lapsed_claim_does_not_cover(enforce, capsys, tmp_path, monkeypatch):
    row = live_row()
    row["live"] = False
    monkeypatch.setattr(enforce.focus, "live_focus", lambda: [row])
    monkeypatch.setattr(enforce, "git_root_if_idp", lambda p: "/repo")
    assert (
        pre_call(enforce, capsys, transcript(tmp_path, BRIEF_CALL))[
            "permissionDecision"
        ]
        == "deny"
    )


def test_an_unreadable_ledger_fails_open(enforce, capsys, tmp_path, monkeypatch):
    monkeypatch.setattr(enforce.focus, "live_focus", lambda: None)
    monkeypatch.setattr(enforce, "git_root_if_idp", lambda p: "/repo")
    assert pre_call(enforce, capsys, transcript(tmp_path, BRIEF_CALL)) is None
    last = open(enforce.ledger_path()).read().splitlines()[-1]
    assert json.loads(last)["decision"] == "unknown"


def test_files_outside_idp_are_never_gated_not_even_for_a_brief(
    enforce, capsys, tmp_path, monkeypatch
):
    # The hooks are machine-wide: another project, the harness's own settings, scratch notes.
    monkeypatch.setattr(enforce.focus, "live_focus", lambda: [])
    unbriefed = transcript(tmp_path)
    for path in (
        "/Users/x/other-repo/a.py",
        "/Users/x/.estate/harness/cc/settings.json",
    ):
        assert pre_call(enforce, capsys, unbriefed, path) is None
    assert pre_call(enforce, capsys, unbriefed, "/private/tmp/notes.txt") is None  # noqa: S108


WORKTREE = "/tmp/wt"  # noqa: S108 - a path matched, never written


def test_a_worktree_in_scratch_space_is_still_gated(
    enforce, capsys, tmp_path, monkeypatch
):
    # Agents build lanes in /tmp checkouts: location says scratch, content says durable.
    monkeypatch.setattr(enforce.focus, "live_focus", lambda: [])
    monkeypatch.setattr(enforce, "git_root_if_idp", lambda p: WORKTREE)
    path = WORKTREE + "/bin/x"
    denied = pre_call(enforce, capsys, transcript(tmp_path), path)
    assert denied["permissionDecision"] == "deny"
    assert "brief" in denied["permissionDecisionReason"]
    denied = pre_call(enforce, capsys, transcript(tmp_path, BRIEF_CALL), path)
    assert "no live claim" in denied["permissionDecisionReason"]


def test_reads_and_other_tools_are_never_gated(enforce, capsys, tmp_path):
    enforce.pre(
        {
            "tool_name": "Read",
            "tool_input": {"file_path": "/repo/a"},
            "transcript_path": transcript(tmp_path),
            "session_id": "s",
        }
    )
    assert capsys.readouterr().out == ""


def test_stop_refuses_once_when_files_changed_and_nothing_was_written_back(
    enforce, capsys, tmp_path
):
    t = transcript(tmp_path, BRIEF_CALL, edit("/repo/bin/x"))
    enforce.stop({"transcript_path": t, "session_id": "s"})
    assert json.loads(capsys.readouterr().out)["decision"] == "block"
    enforce.stop({"transcript_path": t, "session_id": "s", "stop_hook_active": True})
    assert capsys.readouterr().out == ""  # never loops a session


def test_stop_passes_after_a_write_back_or_with_no_durable_edits(
    enforce, capsys, tmp_path
):
    enforce.stop({"transcript_path": transcript(tmp_path, edit("/repo/a"), REMEMBER)})
    assert capsys.readouterr().out == ""
    enforce.stop({"transcript_path": transcript(tmp_path, edit("/Users/x/other/a"))})
    assert capsys.readouterr().out == ""
    enforce.stop({"transcript_path": transcript(tmp_path, BRIEF_CALL)})
    assert capsys.readouterr().out == ""


def test_the_opt_out_is_ledgered_not_silent(enforce, tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_MEMORY_ENFORCE", "0")
    assert enforce.main(["pre"]) == 0
    assert (
        json.loads(open(enforce.ledger_path()).read().splitlines()[-1])["decision"]
        == "optout"
    )


# --- the installer carries the hooks, idempotently ---------------------------------------------------


def test_the_installer_writes_the_enforcement_hooks_once(tmp_path):
    cfg = tmp_path / "cc"
    cfg.mkdir()
    (cfg / "settings.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Read",
                            "hooks": [{"type": "command", "command": "keep-me"}],
                        }
                    ]
                }
            }
        )
    )
    env = {**os.environ, "CLAUDE_CONFIG_DIR": str(cfg), "HOME": str(tmp_path)}
    run = lambda *a: subprocess.run(  # noqa: E731
        [
            sys.executable,
            os.path.join(ROOT, "bin", "estate-memory-install"),
            "--home",
            str(tmp_path / "home"),
            "--runtime",
            "claude-code",
            *a,
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    assert run().returncode == 0
    hooks = json.loads((cfg / "settings.json").read_text())["hooks"]
    pre = [g for g in hooks["PreToolUse"] if "estate-memory-enforce" in json.dumps(g)]
    assert len(pre) == 1 and pre[0]["matcher"] == "Edit|Write|MultiEdit|NotebookEdit"
    assert any(
        "keep-me" in json.dumps(g) for g in hooks["PreToolUse"]
    )  # others untouched
    assert (
        len([g for g in hooks["Stop"] if "estate-memory-enforce" in json.dumps(g)]) == 1
    )
    assert (
        run("--check").returncode == 0
    )  # idempotent: a second run finds nothing to change
    assert (tmp_path / "home" / "platform/estate/memory/focus.py").exists()


# --- a claim posted minutes ago, before the search index has it ----------------------------------


def claim_issue(num, agent, paths, age_s, state="OPEN"):
    body = f"CLAIM agent={agent} paths={paths} heartbeat={iso(age_s)}"
    return {
        "number": num,
        "title": "t",
        "state": state,
        "comments": [{"body": body, "createdAt": iso(age_s)}],
    }


def test_a_noted_claim_is_read_from_its_issue_not_the_search(tmp_path):
    path = str(tmp_path / "noted.json")
    focus.note_claim(6597, now=NOW - 60, path=path)
    focus.note_claim(42, now=NOW - focus.LAPSE_S - 1, path=path)  # outside the window
    seen = []

    def view(num):
        seen.append(num)
        return claim_issue(num, "claude", "bin/*", 60)

    rows = focus.noted_rows(now=NOW, path=path, view_fn=view)
    assert seen == [6597]
    assert [(r["claim"], r["live"]) for r in rows] == [("idp#6597", True)]


def test_a_noted_claim_on_a_closed_issue_covers_nothing(monkeypatch):
    monkeypatch.setattr(
        focus,
        "_gh",
        lambda a, t: json.dumps(claim_issue(7, "claude", "bin/*", 60, "CLOSED")),
    )
    assert focus._view_issue(7) is None


def test_the_hook_passes_a_claim_the_register_has_not_indexed_yet(
    enforce, capsys, tmp_path, monkeypatch
):
    # The register (search) lags: it knows only an unrelated claim. The noted issue has ours.
    monkeypatch.setattr(enforce.focus, "live_focus", lambda: [live_row(paths="docs/*")])
    monkeypatch.setattr(
        enforce.focus, "_view_issue", lambda n: claim_issue(n, "me", "bin/*", 30)
    )
    enforce.focus.note_claim(6597)
    monkeypatch.setattr(enforce, "git_root_if_idp", lambda p: "/repo")
    assert pre_call(enforce, capsys, transcript(tmp_path, BRIEF_CALL)) is None
    cached = enforce.focus.load_json(enforce.focus.focus_cache_path())["rows"]
    assert {r["claim"] for r in cached} == {
        "idp#1",
        "idp#6597",
    }  # the next edit reads no gh


def test_a_noted_claim_does_not_cover_paths_it_never_named(
    enforce, capsys, tmp_path, monkeypatch
):
    monkeypatch.setattr(enforce.focus, "live_focus", lambda: [])
    monkeypatch.setattr(
        enforce.focus, "_view_issue", lambda n: claim_issue(n, "me", "docs/*", 30)
    )
    enforce.focus.note_claim(6597)
    monkeypatch.setattr(enforce, "git_root_if_idp", lambda p: "/repo")
    out = pre_call(enforce, capsys, transcript(tmp_path, BRIEF_CALL))
    assert out["permissionDecision"] == "deny"
    assert "--paths bin/x" in out["permissionDecisionReason"]


# --- claim-open notes its claim, so the enforce hook sees it before the next ledger poll


def test_claim_open_notes_the_claim_it_posted(monkeypatch, tmp_path):
    monkeypatch.setenv("ESTATE_MEMORY_HOME", str(tmp_path))
    loader = importlib.machinery.SourceFileLoader(
        "claim_open", os.path.join(ROOT, "bin", "claim-open")
    )
    spec = importlib.util.spec_from_loader("claim_open", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    mod.note_claim(6597)
    assert "6597" in json.loads((tmp_path / "claims-noted.json").read_text())


def test_claim_open_declares_a_file_before_it_exists():
    # The enforce hook refuses to create a file no claim covers and tells the agent to run
    # `claim-open --paths <file>`; claim-open has to accept that, or no new file can be written.
    loader = importlib.machinery.SourceFileLoader(
        "claim_open", os.path.join(ROOT, "bin", "claim-open")
    )
    spec = importlib.util.spec_from_loader("claim_open", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    assert mod.globs_for([], ["docs/new.yaml"]) == ["docs/new.yaml"]
    assert mod.globs_for(["bin/x"], ["docs/new.yaml", " "]) == [
        "bin/x",
        "docs/new.yaml",
    ]
    with pytest.raises(SystemExit):
        mod.globs_for([], [""])


# --- an unreadable ledger (#7397): the router falls back, the gates do not ------------------------


def _register(path, at, rows):
    path.write_text(json.dumps({"at": at, "rows": rows}))


def _row(claim_no, age):
    return {
        "claim": f"idp#{claim_no}",
        "title": "t",
        "agent": "a",
        "paths": "x",
        "heartbeat_age_s": age,
        "live": age < focus.LAPSE_S,
    }


def test_a_dead_gh_answers_the_router_with_the_last_register_aged(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("ESTATE_MEMORY_HOME", str(tmp_path))  # no snapshot in the way
    monkeypatch.setattr(
        focus, "_gh", lambda args, timeout: None
    )  # 2026-10-28: gh cut at 3.0 s
    reg = tmp_path / "focus-register.json"
    _register(reg, NOW - 900, [_row(1, 60), _row(2, focus.LAPSE_S - 300)])
    rows = focus.live_focus(str(reg), NOW, fallback=True)
    assert [
        (r["claim"], r["live"], r["heartbeat_age_s"], r["stale_s"]) for r in rows
    ] == [
        ("idp#1", True, 960, 900),
        (
            "idp#2",
            False,
            focus.LAPSE_S + 600,
            900,
        ),  # lapsed since the read: not shown live
    ]
    # the gates decide coverage on the ledger only: unknown stays unknown
    assert focus.live_focus(str(reg), NOW) is None


def test_a_register_older_than_the_lapse_says_nothing_true(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_MEMORY_HOME", str(tmp_path))
    monkeypatch.setattr(focus, "_gh", lambda args, timeout: None)
    reg = tmp_path / "focus-register.json"
    _register(reg, NOW - focus.LAPSE_S - 1, [_row(1, 0)])
    assert focus.live_focus(str(reg), NOW, fallback=True) is None


def test_the_gh_read_gets_the_callers_deadline(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(focus, "_gh", lambda args, timeout: seen.append(timeout))
    focus.live_focus(str(tmp_path / "c.json"), NOW, timeout=10.0)
    focus.live_focus(str(tmp_path / "c.json"), NOW)
    assert seen == [10.0, focus.FOCUS_TIMEOUT_S]


def test_a_full_disk_never_truncates_the_register(tmp_path, monkeypatch):
    reg = tmp_path / "focus-register.json"
    _register(reg, NOW, [_row(1, 0)])

    def full(*_a):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(focus.os, "replace", full)
    focus.save_json(str(reg), {"at": NOW + 1, "rows": []})
    assert json.loads(reg.read_text())["rows"][0]["claim"] == "idp#1"
    assert os.listdir(tmp_path) == ["focus-register.json"]
