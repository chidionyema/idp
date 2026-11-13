"""Falsifiers for bin/pin-open -- a session cannot file a duplicate and cannot work elsewhere.

WHY (founder, 2026-11-10): "any agent that tried to report an issue already logged once must be
forced to resolve it, not getting swarm until the issue moves" and "they cant work on anything
else - pin the agent session down to that issue".

The defect being closed: five agents hit one failure, all five file a note, the founder reads the
same complaint five times and nothing moves. Every test here proves the door REFUSES that, and each
mutation test proves the suite would go RED if the refusal were removed.

The ledger is redirected with ESTATE_PIN_LEDGER so no test touches the real ~/.estate/state.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DOOR = REPO / "bin" / "pin-open"

EXIT_OK = 0
EXIT_BLIND = 2
EXIT_PINNED = 3
EXIT_REFUSED = 4


@pytest.fixture()
def ledger(tmp_path):
    p = tmp_path / "pin.json"
    env = dict(os.environ)
    env["ESTATE_PIN_LEDGER"] = str(p)
    env.pop("TELEGRAM_BOT_TOKEN", None)
    env.pop("TELEGRAM_HOME_CHANNEL", None)
    return p, env


def run(env, *args):
    return subprocess.run(
        [str(DOOR), *args], capture_output=True, text=True, env=env, timeout=60
    )


# ---- the door is clear when nothing is open ------------------------------------------------
def test_a_clean_ledger_is_clear(ledger):
    _, env = ledger
    r = run(env)
    assert r.returncode == EXIT_OK
    assert "CLEAR" in r.stdout


# ---- recording a failure pins the session --------------------------------------------------
def test_recording_a_failure_pins_the_session(ledger):
    _, env = ledger
    r = run(
        env,
        "open",
        "#7351",
        "--err",
        "URLError EOF in violation of protocol",
        "--do",
        "fix the memory door manifest",
    )
    assert r.returncode == EXIT_PINNED
    # the message carries the error AND the action: "what they need to do and the error"
    assert "THE ERROR" in r.stdout
    assert "URLError EOF in violation of protocol" in r.stdout
    assert "WHAT TO DO" in r.stdout
    assert "fix the memory door manifest" in r.stdout
    assert "bin/pin-open resolve" in r.stdout


def test_a_pinned_session_refuses_other_work(ledger):
    _, env = ledger
    run(env, "open", "#7351", "--err", "x", "--do", "y")
    r = run(env)
    assert r.returncode == EXIT_PINNED
    assert "NO other work" in r.stdout


def test_the_verdict_is_gateable_as_data(ledger):
    _, env = ledger
    run(env, "open", "#7351", "--err", "x", "--do", "y")
    r = run(env, "--json")
    assert r.returncode == EXIT_PINNED
    d = json.loads(r.stdout)
    assert d["pinned"] is True
    assert d["open"][0]["issue"] == "#7351"


# ---- THE SECOND LAW: the same complaint twice is refused -----------------------------------
def test_the_same_issue_cannot_be_logged_twice(ledger):
    _, env = ledger
    run(
        env,
        "open",
        "#7351",
        "--err",
        "URLError EOF in violation of protocol",
        "--do",
        "y",
    )
    r = run(
        env,
        "open",
        "#7351",
        "--err",
        "URLError EOF in violation of protocol",
        "--do",
        "y",
    )
    assert r.returncode == EXIT_REFUSED
    assert "ALREADY OPEN" in r.stdout
    assert "Do not log it again" in r.stdout


def test_a_different_agent_recognises_the_same_symptom(ledger):
    """The second agent does not know the first's id. It knows the symptom. It must still be refused."""
    _, env = ledger
    run(
        env,
        "open",
        "#7351",
        "--err",
        "URLError EOF in violation of protocol",
        "--do",
        "y",
    )
    env2 = dict(env)
    env2["ESTATE_AGENT"] = "a-second-agent"
    r = run(
        env2,
        "open",
        "memory door is broken",
        "--err",
        "EOF in violation of protocol",
        "--do",
        "z",
    )
    assert r.returncode == EXIT_REFUSED, (
        "a second agent re-logging the same symptom must be refused"
    )


def test_one_issue_only_is_recorded(ledger):
    p, env = ledger
    run(env, "open", "#7351", "--err", "a", "--do", "x")
    run(env, "open", "#7351", "--err", "a", "--do", "x")
    entries = json.loads(p.read_text())["entries"]
    assert len(entries) == 1, "the refused duplicate must not have been appended"


# ---- a resolution needs proof --------------------------------------------------------------
def test_a_resolution_without_proof_is_refused(ledger):
    p, env = ledger
    run(env, "open", "#7351", "--err", "x", "--do", "y")
    eid = json.loads(p.read_text())["entries"][0]["id"]
    r = run(env, "resolve", eid, "--proof", "   ")
    assert r.returncode == EXIT_REFUSED
    assert "needs PROOF" in r.stdout


def test_a_resolution_with_proof_clears_the_pin(ledger):
    p, env = ledger
    run(env, "open", "#7351", "--err", "x", "--do", "y")
    eid = json.loads(p.read_text())["entries"][0]["id"]
    r = run(env, "resolve", eid, "--proof", "bin/idp-ci: exit 0, All checks passed!")
    assert r.returncode == EXIT_OK
    assert run(env).returncode == EXIT_OK, "a resolved pin must unblock the session"


def test_a_resolved_issue_can_be_reopened_by_a_new_failure(ledger):
    p, env = ledger
    run(env, "open", "#7351", "--err", "x", "--do", "y")
    eid = json.loads(p.read_text())["entries"][0]["id"]
    run(env, "resolve", eid, "--proof", "proved")
    r = run(env, "open", "#7351", "--err", "x", "--do", "y")
    assert r.returncode == EXIT_PINNED, (
        "a genuinely recurring failure must be recordable again"
    )


# ---- BLIND is never a pass -----------------------------------------------------------------
def test_an_unreadable_ledger_is_blind_not_clear(ledger):
    p, env = ledger
    p.write_text("{ this is not json")
    r = run(env)
    assert r.returncode == EXIT_BLIND, "an unreadable ledger must never report CLEAR"
    assert "BLIND" in r.stderr
    assert "NOT clear" in r.stderr


def test_blind_uses_the_declared_exit_code_not_sys_exit_string(ledger):
    """`sys.exit("string")` exits 1, not the declared code. AST-walk the door to prove it never
    does that -- a text search would flag this docstring instead of the code."""
    import ast

    tree = ast.parse(DOOR.read_text())
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = getattr(fn, "id", "") or getattr(fn, "attr", "")
        if name == "exit" and node.args and isinstance(node.args[0], ast.Constant):
            if isinstance(node.args[0].value, str):
                offenders.append(node.lineno)
    assert offenders == [], (
        f"sys.exit(<string>) at lines {offenders} exits 1, not the declared code"
    )


# ---- escalation goes to TELEGRAM, never to the founder in-session --------------------------
def test_an_ordinary_step_pages_nobody(ledger):
    _, env = ledger
    r = run(
        env,
        "open",
        "#7351",
        "--err",
        "x",
        "--do",
        "rename the function and re-run the tests",
    )
    assert r.returncode == EXIT_PINNED
    assert "ESCALATED" not in r.stdout, "ordinary work must not page the founder"


def test_a_step_needing_a_human_is_escalated_to_telegram(ledger):
    _, env = ledger
    r = run(
        env,
        "open",
        "#7351",
        "--err",
        "x",
        "--do",
        "approve the production credential rotation",
    )
    assert r.returncode == EXIT_PINNED
    assert "ESCALATED" in r.stdout
    # with no vault sourced it says so rather than pretending it paged him
    assert "not sent" in r.stdout or "TELEGRAM" in r.stdout


def test_the_escalation_channel_is_telegram_and_never_a_chat_body(ledger):
    """Founder: "not to me to the telegram, i dont want agents chatting to me". The door's page
    target is api.telegram.org and its ledger records the route, so an in-session chat is not a
    path that exists."""
    src = DOOR.read_text()
    assert "api.telegram.org" in src
    assert "TELEGRAM_HOME_CHANNEL" in src


# ---- mutation: remove the refusal and the suite must go RED --------------------------------
def test_removing_the_duplicate_refusal_makes_the_suite_red(ledger, tmp_path):
    """The falsifier-of-the-falsifier: prove this suite actually grades the refusal.

    A mutation test that only re-runs the REAL door grades nothing -- it passes whether or not the
    guard exists. So the mutant is EXECUTED, and the test asserts the observed difference: the
    shipped door refuses the duplicate (exit 4), the mutant with the guard deleted accepts it.
    """
    _, env = ledger
    src = DOOR.read_text()
    guard = "    hit = _match(d, issue) or (err and _match(d, err[:80]))"
    assert guard in src, "mutation anchor missing -- the mutation would grade nothing"
    mutant = tmp_path / "pin-open-mutant"
    mutant.write_text(src.replace(guard, "    hit = None", 1))
    mutant.chmod(0o755)

    env_real = dict(env, ESTATE_PIN_LEDGER=str(tmp_path / "real.json"))
    env_mut = dict(env, ESTATE_PIN_LEDGER=str(tmp_path / "mutant.json"))

    # Both doors record the failure once, then meet the SAME duplicate report.
    for door, e in ((DOOR, env_real), (mutant, env_mut)):
        subprocess.run(
            [str(door), "open", "#7351", "--err", "same", "--do", "y"],
            capture_output=True,
            text=True,
            env=e,
            timeout=60,
        )

    real = run(env_real, "open", "#7351", "--err", "same", "--do", "y")
    mut = subprocess.run(
        [str(mutant), "open", "#7351", "--err", "same", "--do", "y"],
        capture_output=True,
        text=True,
        env=env_mut,
        timeout=60,
    )

    assert real.returncode == EXIT_REFUSED, "the shipped door must refuse the duplicate"
    assert mut.returncode != EXIT_REFUSED, (
        "the mutant must ACCEPT the duplicate, or the guard is not what this suite grades"
    )



# ---- complaint DoF canary: scope by trusted harness session ---------------------------
def test_targeted_complaint_refuses_only_accountable_session(ledger):
    _, env = ledger
    r = run(
        env, "open", "#8030", "--err", "machine-work handback",
        "--do", "reproduce and verify correction",
        "--target-session", "signed-session-a",
    )
    assert r.returncode == EXIT_PINNED
    implicated = dict(env, ESTATE_PIN_SESSION="signed-session-a")
    independent = dict(env, ESTATE_PIN_SESSION="signed-session-b")
    denied = run(implicated, "--json")
    allowed = run(independent, "--json")
    assert denied.returncode == EXIT_PINNED
    assert json.loads(denied.stdout)["open"][0]["target_session"] == "signed-session-a"
    assert allowed.returncode == EXIT_OK
    assert json.loads(allowed.stdout)["open"] == []


def test_unbound_session_never_reports_scoped_complaint_as_verified_clear(ledger):
    _, env = ledger
    run(env, "open", "#8030", "--err", "x", "--do", "y",
        "--target-session", "signed-session-a")
    result = run(env, "--json")
    assert result.returncode == EXIT_OK
    report = json.loads(result.stdout)
    assert report["session_bound"] is False
    assert report["scoped_unobserved"] == 1
    assert report["pinned"] is False  # no global outage invented


def test_legacy_unscoped_pins_continue_to_block_every_session(ledger):
    _, env = ledger
    run(env, "open", "#7351", "--err", "x", "--do", "y")
    for sid in ("signed-session-a", "signed-session-b", ""):
        result = run(dict(env, ESTATE_PIN_SESSION=sid), "--json")
        assert result.returncode == EXIT_PINNED


def test_scoped_duplicate_is_refused_and_original_issue_retained(ledger):
    p, env = ledger
    args = ("open", "#8030", "--err", "repeated handback",
            "--do", "machine fix", "--target-session", "signed-session-a")
    assert run(env, *args).returncode == EXIT_PINNED
    assert run(env, *args).returncode == EXIT_REFUSED
    assert len(json.loads(p.read_text())["entries"]) == 1


def test_legacy_open_issue_never_shadows_scoped_case_in_ledger(ledger):
    p, env = ledger
    run(env, "open", "#7351", "--err", "legacy", "--do", "repair")
    run(env, "open", "#8030", "--err", "new complaint",
        "--do", "repair", "--target-session", "signed-session-b")
    assert len(json.loads(p.read_text())["entries"]) == 2


def test_pretool_hook_binds_trusted_tool_session_not_agent_supplied_environment():
    source = (REPO / "bin" / "estate-memory-enforce").read_text()
    assert 'env={**os.environ, "ESTATE_PIN_SESSION": sid}' in source
    assert "pin_ok, pin_why = pin_verdict(sid, path)" in source



def test_targeted_repair_requires_matching_live_issue_and_file(tmp_path):
    """Extract the shipped pure function: no mocked pass from a different issue."""
    import ast
    import fnmatch

    source = (REPO / "bin" / "estate-memory-enforce").read_text()
    tree = ast.parse(source)
    node = next(n for n in tree.body
                if isinstance(n, ast.FunctionDef)
                and n.name == "pinned_repair_permitted")
    module = ast.Module(body=[node], type_ignores=[])
    namespace = {
        "os": os,
        "real": lambda path: path,
        "git_root_if_idp": lambda path: "/repo",
        "covers": lambda row, rel: any(
            fnmatch.fnmatchcase(rel, name.strip())
            for name in row.get("paths", "").split(",")
        ),
    }
    exec(compile(module, "<shipped pinned-repair predicate>", "exec"), namespace)
    allowed = namespace["pinned_repair_permitted"]
    pin = {"issue": "#8030", "target_session": "signed-session-a"}
    correct = [{
        "claim": "idp#8030", "agent": "agent-a",
        "live": True, "paths": "platform/estate/governance/*.py",
    }]
    path = "/repo/platform/estate/governance/founder_intake.py"
    assert allowed(pin, path, "agent-a", correct)
    assert not allowed(pin, path, "agent-b", correct)
    assert not allowed(pin, path, "agent-a", [{
        **correct[0], "claim": "idp#8031",
    }])
    assert not allowed(pin, path, "agent-a", [{
        **correct[0], "live": False,
    }])
    assert not allowed(pin, "/repo/web/app/new-product.tsx", "agent-a", correct)
    assert not allowed(pin, path, "agent-a", [])
    assert not allowed({"issue": "#8030"}, path, "agent-a", correct)
    assert not allowed({"issue": "not-an-issue", "target_session": "signed-session-a"},
                       path, "agent-a", correct)
