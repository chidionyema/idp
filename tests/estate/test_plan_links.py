"""Falsifiers for the plan links: the instruction, the founder prompt and the protocol.

Every test here proves the door CAN fail. A link that is present and wrong must be reported as
a violation; a link that is absent must be a gap, not a silent pass. A test that cannot fail is
not a test, and a gate that cannot fail is not a gate (AGENTS.md section 9, R1 and R2).
"""

import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ESTATE_PKG = os.path.join(REPO_ROOT, "platform", "estate")
if ESTATE_PKG not in sys.path:
    sys.path.insert(0, ESTATE_PKG)

from governance import founder_intake  # noqa: E402
from governance import plan_links  # noqa: E402


def _home(tmp_path, monkeypatch):
    home = tmp_path / "estate"
    (home / "plans").mkdir(parents=True)
    (home / "state").mkdir(parents=True)
    monkeypatch.setenv("ESTATE_HOME", str(home))
    return home


def _plan(home, session, **args):
    event = {
        "at": 1.0,
        "session": session,
        "tool": "declare_plan",
        "args": dict(
            {
                "goal": "land the links",
                "subgoals": [{"id": "g1", "text": "wire the door"}],
            },
            **args,
        ),
    }
    with open(home / "plans" / f"{session}.jsonl", "w", encoding="utf-8") as fh:
        fh.write(json.dumps(event) + "\n")


def _intent(home, session, intent):
    with open(home / "plans" / "intents.jsonl", "a", encoding="utf-8") as fh:
        fh.write(
            json.dumps({"intent": intent, "session": session, "source": "intent-door"})
            + "\n"
        )


def _prompt(home, **rec):
    rec.setdefault("fingerprint", "fp-" + str(rec.get("id", "x")))
    with open(home / "state" / "prompts.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")


def test_a_plan_with_an_instruction_and_a_founder_prompt_links_all_three(
    tmp_path, monkeypatch
):
    home = _home(tmp_path, monkeypatch)
    _plan(home, "s1", instruction="lane-submit", prompt="prompt-0001")
    _intent(home, "s1", "lane-submit")
    _prompt(home, id="prompt-0001", session="s1", text="land it and prove it")

    result = plan_links.audit()
    assert result["sessions"] == 1
    row = result["rows"][0]
    assert row["session"] == "s1"
    assert row["declared_instruction"] == "lane-submit"
    assert row["observed_instructions"] == ["lane-submit"]
    assert row["prompt_id"] == "prompt-0001"
    assert row["protocol"] == "execution"
    assert result["violations"] == []
    assert result["gaps"] == []


def test_an_instruction_that_resolves_to_no_known_intent_is_a_violation(
    tmp_path, monkeypatch
):
    home = _home(tmp_path, monkeypatch)
    _plan(home, "s1", instruction="no-such-intent")
    _intent(home, "s1", "no-such-intent")

    result = plan_links.audit()
    assert any("resolves to no known intent" in v for v in result["violations"])


def test_an_instruction_that_is_not_an_intent_name_is_a_violation(
    tmp_path, monkeypatch
):
    home = _home(tmp_path, monkeypatch)
    _plan(home, "s1", instruction="not an intent")

    result = plan_links.audit()
    assert any("is not an intent name" in v for v in result["violations"])


def test_a_founder_prompt_that_resolves_to_nothing_is_a_violation(
    tmp_path, monkeypatch
):
    home = _home(tmp_path, monkeypatch)
    _plan(home, "s1", prompt="prompt-missing")

    result = plan_links.audit()
    assert any("resolves to no founder prompt" in v for v in result["violations"])


def test_a_missing_founder_prompt_is_a_gap_and_not_a_violation(tmp_path, monkeypatch):
    home = _home(tmp_path, monkeypatch)
    _plan(home, "s1")

    result = plan_links.audit()
    assert result["violations"] == []
    assert any("no founder prompt linked" in g for g in result["gaps"])


def test_a_prompt_bound_to_no_protocol_is_reported_by_the_kit_audit(
    tmp_path, monkeypatch
):
    home = _home(tmp_path, monkeypatch)
    _plan(home, "s1", prompt="prompt-0001")
    _prompt(
        home,
        id="prompt-0001",
        session="s1",
        text="land it",
        protocol_binding="not_a_protocol",
    )

    result = plan_links.audit()
    assert any("Protocol_Binding" in v for v in result["violations"])


def test_the_binder_always_names_exactly_one_protocol():
    assert founder_intake.bind_protocol("land it and prove it") == "execution"
    assert founder_intake.bind_protocol("what is the rate limit?") == "grounded_inquiry"
    assert founder_intake.bind_protocol("compare the two routers") == "deep_synthesis"
    # The same words always give the same protocol: the binding is a rule, not a guess.
    assert founder_intake.bind_protocol(
        "land it and prove it"
    ) == founder_intake.bind_protocol("land it and prove it")


def test_the_door_refuses_on_a_wrong_link(tmp_path, monkeypatch):
    home = _home(tmp_path, monkeypatch)
    _plan(home, "s1", instruction="no-such-intent")
    env = dict(os.environ)
    env["ESTATE_HOME"] = str(home)
    proc = subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "bin", "estate-plan-links"), "--json"],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    assert proc.returncode == 4, proc.stdout + proc.stderr
    assert "no known intent" in proc.stdout


def test_the_door_passes_on_a_correct_link(tmp_path, monkeypatch):
    home = _home(tmp_path, monkeypatch)
    _plan(home, "s1", instruction="lane-submit", prompt="prompt-0001")
    _intent(home, "s1", "lane-submit")
    _prompt(home, id="prompt-0001", session="s1", text="land it and prove it")
    env = dict(os.environ)
    env["ESTATE_HOME"] = str(home)
    proc = subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "bin", "estate-plan-links"), "--json"],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_strict_audit_refuses_an_empty_estate_instead_of_reporting_green(tmp_path, monkeypatch):
    """An empty ledger cannot establish instruction or yield readiness."""
    home = _home(tmp_path, monkeypatch)
    env = dict(os.environ, ESTATE_HOME=str(home))
    proc = subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "bin", "estate-plan-links"),
         "--strict", "--json"],
        capture_output=True, text=True, env=env, timeout=15,
    )
    assert proc.returncode == 4, proc.stdout + proc.stderr
    result = json.loads(proc.stdout)
    assert result["sessions"] == 0
    assert any("no plan declaration" in gap for gap in result["gaps"])


def test_strict_session_lookup_refuses_absent_named_session(tmp_path, monkeypatch):
    """One-hop lookup cannot silently substitute a different agent's session."""
    home = _home(tmp_path, monkeypatch)
    _plan(home, "existing", instruction="lane-submit", prompt="prompt-1")
    _intent(home, "existing", "lane-submit")
    _prompt(home, id="prompt-1", session="existing", text="land it and prove it")
    env = dict(os.environ, ESTATE_HOME=str(home))
    proc = subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "bin", "estate-plan-links"),
         "--strict", "--session", "missing", "--json"],
        capture_output=True, text=True, env=env, timeout=15,
    )
    assert proc.returncode == 4
    result = json.loads(proc.stdout)
    assert result["rows"] == []
    assert any("missing: no plan declaration" in gap for gap in result["gaps"])


def test_known_declared_instruction_disagreeing_with_executed_intent_is_violation(
    tmp_path, monkeypatch
):
    home = _home(tmp_path, monkeypatch)
    _plan(home, "s1", instruction="lane-submit", prompt="prompt-1")
    _intent(home, "s1", "code-review")
    _prompt(home, id="prompt-1", session="s1", text="land it and prove it")
    result = plan_links.audit("s1")
    assert any("not recorded by the intent door" in v
               for v in result["violations"])


def test_declared_instruction_without_an_executed_intent_is_a_strict_gap(
    tmp_path, monkeypatch
):
    home = _home(tmp_path, monkeypatch)
    _plan(home, "s1", instruction="lane-submit", prompt="prompt-1")
    _prompt(home, id="prompt-1", session="s1", text="land it and prove it")
    result = plan_links.audit("s1")
    assert result["violations"] == []
    assert any("not observed by the intent door" in g for g in result["gaps"])


def test_plan_cannot_reuse_prompt_owned_by_another_session(tmp_path, monkeypatch):
    home = _home(tmp_path, monkeypatch)
    _plan(home, "s1", instruction="lane-submit", prompt="prompt-from-s2")
    _intent(home, "s1", "lane-submit")
    _prompt(home, id="prompt-from-s2", session="s2",
            text="land it and prove it")
    result = plan_links.audit("s1")
    assert any("belongs to another session" in v
               for v in result["violations"])


def test_observed_intent_does_not_replace_missing_plan_instruction(
    tmp_path, monkeypatch
):
    home = _home(tmp_path, monkeypatch)
    _plan(home, "s1", prompt="prompt-1")
    _intent(home, "s1", "lane-submit")
    _prompt(home, id="prompt-1", session="s1", text="land it and prove it")
    result = plan_links.audit("s1")
    assert any("no instruction declared in plan" in g
               for g in result["gaps"])



def test_completion_without_independent_proof_is_not_yield(tmp_path, monkeypatch):
    home = _home(tmp_path, monkeypatch)
    _plan(home, "s1", instruction="lane-submit", prompt="prompt-1")
    _intent(home, "s1", "lane-submit")
    _prompt(home, id="prompt-1", session="s1", text="land it and prove it")
    with open(home / "plans" / "s1.jsonl", "a", encoding="utf8") as out:
        out.write(json.dumps({"tool": "complete_goal", "args": {"goal_id": "g1"}}) + "\n")
    result = plan_links.audit("s1")
    row = result["rows"][0]
    assert row["completion_claims"] == 1
    assert row["verified_yield_count"] == 0
    assert row["yield_state"] == "UNVERIFIED"
    assert any("unproved completion" in g for g in result["gaps"])


def test_claim_with_a_proof_reference_is_still_not_independent_validation(
    tmp_path, monkeypatch
):
    home = _home(tmp_path, monkeypatch)
    _plan(home, "s1", instruction="lane-submit", prompt="prompt-1")
    _intent(home, "s1", "lane-submit")
    _prompt(home, id="prompt-1", session="s1", text="land it and prove it")
    with open(home / "plans" / "s1.jsonl", "a", encoding="utf8") as out:
        out.write(json.dumps({"tool": "complete_goal",
                              "args": {"goal_id": "g1", "proof": "run:42379669617"}}) + "\n")
    result = plan_links.audit("s1")
    row = result["rows"][0]
    assert row["completion_claims"] == 1
    assert row["verified_yield_count"] == 0
    assert row["yield_state"] == "UNVERIFIED"
    assert any("proof not independently verified" in g for g in result["gaps"])
