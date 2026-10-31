"""The live plan-link state: the derivation rule, the state, the summary, the publisher.

The derivation cases live in extensions/pi-plan-lock/cases.json and are replayed HERE against
the Python copy and, by the node suite, against the TypeScript copy: one rule, one contract, so
neither copy can drift alone.

The publisher's falsifier is the fingerprint: a second publication with the same numbers must
NOT reach the bus, and a publication that cannot reach the bus must be RED, never a green
board that stopped moving (AGENTS.md section 9, R1 and R2).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ESTATE_PKG = str(ROOT / "platform" / "estate")
MEMORY_PKG = str(ROOT / "platform" / "estate" / "memory")
if ESTATE_PKG not in sys.path:
    sys.path.insert(0, ESTATE_PKG)
if MEMORY_PKG not in sys.path:
    sys.path.insert(0, MEMORY_PKG)

from governance import plan_links  # noqa: E402
import plan  # noqa: E402

CASES = json.loads((ROOT / "extensions" / "pi-plan-lock" / "cases.json").read_text())
DOOR = ROOT / "bin" / "estate-plan-links"


def _home(tmp_path, monkeypatch, intents=(), prompts=(), plans=None):
    home = tmp_path / "estate"
    (home / "plans").mkdir(parents=True)
    (home / "state").mkdir(parents=True)
    monkeypatch.setenv("ESTATE_HOME", str(home))
    with open(home / "plans" / "intents.jsonl", "w", encoding="utf-8") as fh:
        for row in intents:
            fh.write(json.dumps(row) + "\n")
    with open(home / "state" / "prompts.jsonl", "w", encoding="utf-8") as fh:
        for row in prompts:
            fh.write(json.dumps(row) + "\n")
    for session, args in (plans or {}).items():
        with open(home / "plans" / f"{session}.jsonl", "w", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "at": 1.0,
                        "session": session,
                        "tool": "declare_plan",
                        "args": args,
                    }
                )
                + "\n"
            )
    return home


def _linked_home(tmp_path, monkeypatch):
    return _home(
        tmp_path,
        monkeypatch,
        intents=[{"session": "s1", "intent": "lane-submit"}],
        prompts=[
            {
                "session": "s1",
                "id": "prompt-0001",
                "text": "ship the links",
                "protocol_binding": "execution",
            }
        ],
        plans={
            "s1": {
                "goal": "land the links",
                "subgoals": [{"id": "g1", "text": "wire the door"}],
            }
        },
    )


@pytest.mark.parametrize("case", CASES["derivations"], ids=lambda c: c["name"])
def test_the_derivation_rule_holds_in_python_too(monkeypatch, tmp_path, case):
    _home(
        tmp_path,
        monkeypatch,
        intents=case["intents"],
        prompts=case["prompts"],
    )
    links = plan_links.derive_links(case["session"])
    assert links["instruction"] == case["instruction"], case["name"]
    assert links["prompt"] == case["prompt"], case["name"]


def test_the_state_counts_what_the_summary_says(monkeypatch, tmp_path):
    _linked_home(tmp_path, monkeypatch)
    state = plan_links.state()
    assert state["available"] is True
    assert state["sessions"] == 1
    assert state["linked"] == 1
    assert state["unlinked"] == 0
    assert state["violations"] == 0
    assert state["gaps"] == 0
    assert state["summary"] == "plan links: 1 sessions, 0 violations, 0 gaps"


def test_a_plan_with_no_links_at_all_is_a_gap_not_a_violation(monkeypatch, tmp_path):
    _home(
        tmp_path,
        monkeypatch,
        plans={
            "s1": {
                "goal": "land the links",
                "subgoals": [{"id": "g1", "text": "wire the door"}],
            }
        },
    )
    state = plan_links.state()
    assert state["violations"] == 0
    assert state["gaps"] == 2
    assert state["summary"] == "plan links: 1 sessions, 0 violations, 2 gaps"


def test_the_summary_is_one_line_in_one_order():
    assert (
        plan_links.summary_line(3, 1, 2)
        == "plan links: 3 sessions, 1 violations, 2 gaps"
    )


def _fake_bus(tmp_path, sent, exit_code=0):
    fake = tmp_path / "fleet.py"
    fake.write_text(
        "import sys\n"
        "with open(%s, 'a', encoding='utf-8') as fh:\n"
        "    fh.write(' '.join(sys.argv[1:]) + '\\n')\n"
        "sys.exit(%d)\n" % (json.dumps(str(sent)), exit_code)
    )
    return fake


def test_the_publisher_speaks_only_when_the_state_moved(tmp_path, monkeypatch):
    home = _linked_home(tmp_path, monkeypatch)
    sent = tmp_path / "sent.txt"
    fake = _fake_bus(tmp_path, sent)
    env = dict(os.environ)
    env["ESTATE_HOME"] = str(home)
    env["ESTATE_FLEET_BIN"] = str(fake)

    first = subprocess.run(
        [sys.executable, str(DOOR), "--publish"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert first.returncode == 0, first.stdout + first.stderr
    assert first.stdout.startswith("published: "), first.stdout

    second = subprocess.run(
        [sys.executable, str(DOOR), "--publish"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert second.returncode == 0, second.stdout + second.stderr
    assert second.stdout.startswith("unchanged: "), second.stdout

    lines = [l for l in sent.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1, lines
    assert "plan links: 1 sessions" in lines[0], lines


def test_a_publication_that_cannot_reach_the_bus_is_red(tmp_path, monkeypatch):
    home = _linked_home(tmp_path, monkeypatch)
    sent = tmp_path / "sent.txt"
    fake = _fake_bus(tmp_path, sent, exit_code=3)
    env = dict(os.environ)
    env["ESTATE_HOME"] = str(home)
    env["ESTATE_FLEET_BIN"] = str(fake)

    out = subprocess.run(
        [sys.executable, str(DOOR), "--publish"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert out.returncode == 4, out.stdout + out.stderr
    assert out.stdout.startswith("publish failed"), out.stdout


def test_the_door_reports_the_state_as_json(tmp_path, monkeypatch):
    _linked_home(tmp_path, monkeypatch)
    out = subprocess.run(
        [sys.executable, str(DOOR), "--json"],
        capture_output=True,
        text=True,
        env={**os.environ, "ESTATE_HOME": str(tmp_path / "estate")},
    )
    assert out.returncode == 0, out.stdout + out.stderr
    state = json.loads(out.stdout)
    assert state["summary"] == "plan links: 1 sessions, 0 violations, 0 gaps"


@pytest.mark.parametrize("case", CASES["linkRules"], ids=lambda c: c["name"])
def test_the_link_rule_holds_in_python_too(case):
    """The same cases the TypeScript copy replays, against the Python copy.

    One contract, two copies: a rule that drifts in one of them fails here.
    """
    decision = plan.link_decision(
        case["stated"], case["derived"], case["unresolvable"], case["strict"]
    )
    assert decision["ok"] == case["expect"], case["name"]
    if not decision["ok"] and case.get("reason"):
        assert case["reason"] in decision["reason"], case["name"]


def test_the_founder_session_that_has_an_instruction_but_no_prompt_is_accepted(
    monkeypatch,
):
    """The founder's live session (pi-1793437500991-9xsel16v) has 7 intent records and no
    prompt record. A rule that refused it would trap the founder mid-work, so the estate
    observes that gap instead of refusing it."""
    monkeypatch.delenv("ESTATE_PLAN_LINK_STRICT", raising=False)
    derived = {"instruction": "lane-submit", "prompt": ""}
    decision = plan.link_decision({}, derived, [], False)
    assert decision["ok"] is True


def test_a_stated_link_that_resolves_to_nothing_is_refused(monkeypatch, tmp_path):
    """A link the estate can DISPROVE refuses, even while the estate observes."""
    home = tmp_path / "estate"
    (home / "intents").mkdir(parents=True)
    monkeypatch.setenv("ESTATE_HOME", str(home))
    (home / "intents" / "lane-submit.yaml").write_text(
        "name: lane-submit\n", encoding="utf-8"
    )
    problems = plan.unresolvable_links({"instruction": "no-such-intent"})
    assert problems == ["instruction 'no-such-intent' resolves to no known intent"]
    decision = plan.link_decision(
        {"instruction": "no-such-intent"}, {}, problems, False
    )
    assert decision["ok"] is False
    assert "resolves to no known intent" in decision["reason"]


def test_a_prompt_that_resolves_to_no_founder_prompt_is_refused(monkeypatch, tmp_path):
    home = tmp_path / "estate"
    (home / "state").mkdir(parents=True)
    monkeypatch.setenv("ESTATE_HOME", str(home))
    (home / "state" / "prompts.jsonl").write_text(
        json.dumps({"session": "s1", "id": "prompt-0001", "text": "go"}) + "\n",
        encoding="utf-8",
    )
    problems = plan.unresolvable_links({"prompt": "prompt-9999"})
    assert problems == ["prompt 'prompt-9999' resolves to no founder prompt"]


def test_an_empty_prompt_ledger_disproves_nothing(monkeypatch, tmp_path):
    """A gate that refuses on what it cannot see is an outage, not a gate."""
    home = tmp_path / "estate"
    (home / "state").mkdir(parents=True)
    monkeypatch.setenv("ESTATE_HOME", str(home))
    (home / "state" / "prompts.jsonl").write_text("", encoding="utf-8")
    assert plan.unresolvable_links({"prompt": "prompt-9999"}) == []


def test_the_bridges_own_ledger_keeps_the_derived_links(monkeypatch, tmp_path):
    """The links the estate derives are the ones the ledger records, so the door and the live
    plan read one truth."""
    home = _home(
        tmp_path,
        monkeypatch,
        intents=[{"session": "s1", "intent": "lane-submit"}],
        prompts=[{"session": "s1", "id": "prompt-0001", "text": "go"}],
    )
    args, decision = plan.enrich_plan_args(
        "s1",
        "declare_plan",
        {
            "goal": "land the links everywhere",
            "subgoals": [{"id": "g1", "text": "wire the door"}],
        },
    )
    assert decision["ok"] is True
    assert args["instruction"] == "lane-submit"
    assert args["prompt"] == "prompt-0001"


def test_an_explicit_link_is_never_overwritten(monkeypatch, tmp_path):
    _home(
        tmp_path,
        monkeypatch,
        intents=[{"session": "s1", "intent": "lane-submit"}],
        prompts=[{"session": "s1", "id": "prompt-0001", "text": "go"}],
    )
    args, _ = plan.enrich_plan_args(
        "s1",
        "declare_plan",
        {
            "goal": "land the links everywhere",
            "subgoals": [{"id": "g1", "text": "wire the door"}],
            "instruction": "the-intent-i-chose",
        },
    )
    assert args["instruction"] == "the-intent-i-chose"


def test_a_raw_transcript_replay_does_not_refuse_a_plan_the_live_path_accepted(
    monkeypatch, tmp_path
):
    """The hook replays the RAW transcript. A plan the live path accepted must not be refused
    here out of the raw call, or the hook would block all subsequent work."""
    _home(
        tmp_path,
        monkeypatch,
        intents=[{"session": "s1", "intent": "lane-submit"}],
    )
    raw = [
        [
            "declare_plan",
            {
                "goal": "land the links everywhere",
                "subgoals": [{"id": "g1", "text": "wire the door"}],
            },
        ]
    ]
    rebuilt = plan.replay(raw, "s1")
    assert rebuilt is not None
    assert rebuilt["goal"] == "land the links everywhere"


def test_strict_refuses_a_plan_the_estate_cannot_link(monkeypatch, tmp_path):
    _home(tmp_path, monkeypatch)
    monkeypatch.setenv("ESTATE_PLAN_LINK_STRICT", "1")
    args, decision = plan.enrich_plan_args(
        "s1",
        "declare_plan",
        {
            "goal": "land the links everywhere",
            "subgoals": [{"id": "g1", "text": "wire the door"}],
        },
    )
    assert decision["ok"] is False
    assert "the instruction it serves" in decision["reason"]
    assert "the founder prompt that started it" in decision["reason"]


def test_the_observe_log_counts_what_strict_would_refuse(monkeypatch, tmp_path):
    _home(tmp_path, monkeypatch)
    monkeypatch.delenv("ESTATE_PLAN_LINK_STRICT", raising=False)
    plan.enrich_plan_args(
        "s1",
        "declare_plan",
        {
            "goal": "land the links everywhere",
            "subgoals": [{"id": "g1", "text": "wire the door"}],
        },
    )
    log = tmp_path / "estate" / "logs" / "plan-link-observe.log"
    assert log.exists(), "an unlinked plan must leave a measurement behind"
    row = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
    assert row["session"] == "s1"
    assert row["instruction"] == ""
    assert row["prompt"] == ""
