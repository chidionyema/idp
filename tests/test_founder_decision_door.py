"""features/founder-decision/founder-decision.feature, bound to the real door.

A feature that cannot run is prose. Every step here runs against
`sovereign/otto/decision.py` -- the same library the intent runs -- with the Telegram
transport replaced by a list, so what is asserted is the door's behaviour: one message per
decision, deterministic matching, the founder's comment stored verbatim, silence expiring
rather than assuming, and no model anywhere in the delivery path.

The library lives in the `sovereign` package (not a src-layout package), so it is imported
by path here: the test must not need the package installed.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

_REPO_ROOT = Path(__file__).resolve().parents[1]
_LIB = _REPO_ROOT / "sovereign" / "otto" / "decision.py"


def _load_decision():
    spec = importlib.util.spec_from_file_location("estate_founder_decision", _LIB)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["estate_founder_decision"] = module
    spec.loader.exec_module(module)
    return module


decision = _load_decision()

scenarios("../features/founder-decision/founder-decision.feature")


@pytest.fixture
def door(tmp_path: Path):
    sent: list = []

    def transport(text: str):
        sent.append(text)
        return 4242 + len(sent)

    d = decision.Door(
        state_file=tmp_path / "decisions.json",
        bus=False,
        transport=transport,
    )
    d.sent = sent
    return d


def _ask(door, **kwargs) -> dict:
    params = {
        "question": "Ship the AEI collector now?",
        "options": "ship: land it, hold: wait",
        "context": "#7341",
        "requester": "pi @ idp",
        "deadline_min": 60,
    }
    params.update(kwargs)
    request = decision.build_request(**params)
    record = door.ask(request)
    return record


# --- the scenarios ---------------------------------------------------------------------------------


@given("a decision asking about the AEI collector", target_fixture="record")
def _a_decision(door) -> dict:
    return _ask(door, decision_id="dec-1a2b3c4d")


@given("a decision asking which lane to take", target_fixture="record")
def _a_lane_decision(door) -> dict:
    return _ask(door, decision_id="dec-9f8e7d6c", question="Which lane?")


@given("a live decision with options ship and hold", target_fixture="record")
def _a_live_decision(door) -> dict:
    return _ask(door, decision_id="dec-1a2b3c4d")


@given("a live decision whose deadline has passed", target_fixture="record")
def _an_expired_decision(door) -> dict:
    record = _ask(door, decision_id="dec-1a2b3c4d")
    state = decision.load_state(door.state_file)
    state["decisions"]["dec-1a2b3c4d"]["deadline_at"] = decision._iso(
        decision._now() - timedelta(minutes=1)
    )
    decision.save_state(state, door.state_file)
    return record


@given("a decision that was already asked", target_fixture="record")
def _an_asked_decision(door) -> dict:
    return _ask(door, decision_id="dec-1a2b3c4d")


@given("two live decisions", target_fixture="records")
def _two_live_decisions(door) -> list:
    return [
        _ask(door, decision_id="dec-1a2b3c4d"),
        _ask(door, decision_id="dec-5e6f7a8b"),
    ]


@given("one live decision with options ship and hold", target_fixture="record")
def _one_live_decision(door) -> dict:
    return _ask(door, decision_id="dec-1a2b3c4d")


@when("the agent asks the founder")
def _agent_asks(door, record) -> dict:
    return record


@when("the agent asks again with the same id")
def _agent_asks_again(door, record) -> dict:
    request = decision.build_request(
        question="Ship the AEI collector now?",
        options="ship: land it, hold: wait",
        decision_id="dec-1a2b3c4d",
    )
    return door.ask(request)


@when("the founder comments dec-1a2b3c4d ship", target_fixture="record")
def _founder_picks(door) -> dict:
    return door.absorb("dec-1a2b3c4d ship") or {}


@when(
    "the founder comments dec-1a2b3c4d do it after the cluster comes back",
    target_fixture="record",
)
def _founder_answers_in_words(door) -> dict:
    return door.absorb("dec-1a2b3c4d do it after the cluster comes back") or {}


@when("the founder comments a bare option key", target_fixture="record")
def _founder_comments_plain(door) -> dict:
    absorbed = door.absorb("ship")
    return absorbed or {}


@when("the founder comments ship while two decisions are live")
def _founder_comments_ambiguous(door) -> dict:
    absorbed = door.absorb("ship")
    return absorbed or {}


@when("the agent reads the decision back", target_fixture="record")
def _agent_reads_back(door) -> dict:
    return door.show("dec-1a2b3c4d") or {}


@then("the founder receives exactly one message")
def _one_message(door) -> None:
    assert len(door.sent) == 1, f"the founder got {len(door.sent)} messages"


@then("the message carries the decision id and the question")
def _message_carries(door) -> None:
    message = door.sent[0]
    assert "dec-1a2b3c4d" in message
    assert "Ship the AEI collector now?" in message


@then("the decision is answered")
def _answered(record) -> None:
    assert record["state"] == "answered", record.get("state")


@then("the reported option is ship")
def _option_ship(record) -> None:
    assert record["option"] == "ship"


@then("the reported option is null")
def _option_null(record) -> None:
    assert record["option"] is None


@then("the founder's comment is stored verbatim")
def _verbatim(record) -> None:
    assert record["answer"] == "dec-1a2b3c4d ship"


@then("the answer is the founder's comment verbatim")
def _answer_verbatim(record) -> None:
    assert record["answer"] == "dec-1a2b3c4d do it after the cluster comes back"


@then("the state is expired")
def _expired(record) -> None:
    assert record["state"] == "expired", record.get("state")


@then("no option is reported")
def _no_option(record) -> None:
    assert record["option"] is None
    assert record["answer"] is None


@then("no second message is sent")
def _no_second_message(door) -> None:
    assert len(door.sent) == 1, f"the founder got {len(door.sent)} messages"


@then("the decision is unchanged")
def _unchanged(door) -> None:
    record = decision.get_decision("dec-1a2b3c4d", door.state_file)
    assert record["state"] == "asked"
    assert record["message_id"] == 4243


@then("the door makes exactly one transport call")
def _one_transport_call(door) -> None:
    assert len(door.sent) == 1


@then("the door names no model client")
def _no_model_client() -> None:
    import ast

    tree = ast.parse(_LIB.read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    for forbidden in (
        "litellm",
        "openai",
        "anthropic",
        "httpx",
        "temporalio",
        "requests",
    ):
        assert forbidden not in imported, (
            f"the door's delivery path imports {forbidden}"
        )


@then("neither decision is answered")
def _neither_answered(door) -> None:
    for decision_id in ("dec-1a2b3c4d", "dec-5e6f7a8b"):
        record = decision.get_decision(decision_id, door.state_file)
        assert record["state"] == "asked", f"{decision_id} was captured"


# --- the unit proof ------------------------------------------------------------------------------


def test_the_intent_is_the_governed_door():
    import yaml

    path = _REPO_ROOT / "platform" / "estate" / "intents" / "founder.decision.yaml"
    data = yaml.safe_load(path.read_text())
    assert data["name"] == "founder.decision"
    for arg in (
        "question",
        "options",
        "context",
        "deadline_min",
        "requester",
        "decision_id",
        "wait",
    ):
        assert arg in data["args"], f"the intent has no {arg}"
    assert data.get("door_s"), "the intent has no door ceiling"
    assert data["steps"][0]["cmd"].count("founder-decision") >= 2
    # The bus session is opt-in: a bus session makes the estate's card post a line message as
    # well, and the founder gets exactly ONE message per decision.
    assert data["args"]["bus"]["default"] == "false"
    assert decision.Door().bus is False


def test_the_cli_reads_a_decision_back(tmp_path, capsys):
    import subprocess

    state = tmp_path / "decisions.json"
    request = decision.build_request(
        question="Ship the AEI collector now?",
        options="ship: land it, hold: wait",
        decision_id="dec-1a2b3c4d",
    )
    decision.save_state(
        {
            "schema": decision.SCHEMA,
            "decisions": {
                "dec-1a2b3c4d": {
                    **request.to_dict(),
                    "schema": decision.SCHEMA,
                    "state": "asked",
                    "created_at": decision._iso(decision._now()),
                    "deadline_at": decision._iso(
                        decision._now() + timedelta(minutes=60)
                    ),
                    "message_id": 4242,
                    "option": None,
                    "answer": None,
                }
            },
        },
        state,
    )
    proc = subprocess.run(
        [
            str(_REPO_ROOT / "bin" / "founder-decision"),
            "--state",
            str(state),
            "show",
            "--decision-id",
            "dec-1a2b3c4d",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["decision_id"] == "dec-1a2b3c4d"
    assert payload["state"] == "asked"
    assert payload["message_id"] == 4242


def test_the_gateway_plugin_records_the_founder_comment(tmp_path, monkeypatch):
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))
    monkeypatch.setenv("ESTATE_DECISION_STATE", str(tmp_path / "decisions.json"))
    plugin = importlib.import_module("sovereign.otto.hermes_plugin")
    state = tmp_path / "decisions.json"
    door = decision.Door(state_file=state, bus=False, transport=lambda text: 99)
    request = decision.build_request(
        question="Ship it?",
        options="ship: land it, hold: wait",
        decision_id="dec-1a2b3c4d",
    )
    door.ask(request)
    record = plugin._decision_answer("dec-1a2b3c4d ship")
    assert record is not None
    assert record["state"] == "answered"
    assert record["option"] == "ship"


def test_a_message_that_answers_nothing_is_not_captured(tmp_path):
    door = decision.Door(
        state_file=tmp_path / "d.json", bus=False, transport=lambda t: 1
    )
    request = decision.build_request(
        question="Ship it?",
        options="ship: land it, hold: wait",
        decision_id="dec-1a2b3c4d",
    )
    door.ask(request)
    assert door.absorb("what is the status of the cluster?") is None
    record = decision.get_decision("dec-1a2b3c4d", door.state_file)
    assert record["state"] == "asked"


def test_the_rendered_message_carries_the_options_and_the_links():
    request = decision.build_request(
        question="Ship the AEI collector now?",
        options="ship: land it, hold: wait for the cluster",
        context="#7341, lane/founder-decision",
        requester="pi @ idp",
        decision_id="dec-1a2b3c4d",
    )
    message = decision.render(request)
    assert message.splitlines()[0] == "dec-1a2b3c4d"
    assert "Ship the AEI collector now?" in message
    assert "ship: land it" in message
    assert "hold: wait for the cluster" in message
    assert "#7341" in message
    assert "lane/founder-decision" in message
    assert "pi @ idp" in message
