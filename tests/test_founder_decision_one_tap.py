"""The founder answers a decision with ONE TAP, not by typing an id.

The founder's instruction (2026-11-08): "you need to make everything one tap seamless for
founder". Before this, the door sent PLAIN TEXT -- no reply_markup -- so the only way to answer
was to copy a decision id out of the message and type `<id> <option-key>` back. That is founder
labour by construction: an id to copy, a key to guess, a syntax to remember.

These tests pin the tap contract, not the implementation spelling:
  * the question carries one button per option,
  * a tap is understood by the SAME matcher as typed text (one matcher, cannot drift),
  * a tap records the answer,
  * a bad keyboard never costs the founder the message.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_LIB = _REPO / "sovereign" / "otto" / "decision.py"


def _load():
    spec = importlib.util.spec_from_file_location("one_tap_decision", _LIB)
    module = importlib.util.module_from_spec(spec)
    sys.modules["one_tap_decision"] = module
    spec.loader.exec_module(module)
    return module


def _request(mod, **kw):
    return mod.DecisionRequest(
        decision_id="dec-9c816eda",
        question=kw.get("question", "Unblock the three Argon PRs?"),
        options=(
            mod.DecisionOption("approve", "Approve them"),
            mod.DecisionOption("deny", "Leave them draft"),
        ),
        context=("#55", "#21", "#57"),
        requester="pi @ idp",
        deadline_min=kw.get("deadline_min", 30),
    )


def test_the_question_carries_one_button_per_option():
    """A message with no keyboard is the defect: it forces typing."""
    mod = _load()
    req = _request(mod)

    markup = mod.option_markup(req.decision_id, req.options)

    assert markup is not None, "no keyboard sent: the founder is forced to type an id"
    buttons = [b for row in markup["inline_keyboard"] for b in row]
    assert len(buttons) == len(req.options)
    assert [b["text"] for b in buttons] == ["Approve them", "Leave them draft"]
    assert all("callback_data" in b for b in buttons)


def test_a_tap_is_understood_by_the_same_matcher_as_typed_text():
    """A tap arrives as callback_query. If only message.text is read, the tap is invisible."""
    mod = _load()
    tapped = {
        "callback_query": {
            "id": "cb-1",
            "data": "dec:dec-9c816eda:approve",
            "message": {"chat": {"id": 42}},
        }
    }

    text = mod.update_text(tapped)

    assert text is not None, "a button tap was invisible to the door"
    assert mod.match_comment(text, _request(mod)).option == "approve"


def test_a_tap_and_a_typed_answer_record_the_same_option():
    """Both paths must converge -- otherwise the two disagree about what was approved."""
    mod = _load()
    req = _request(mod)
    tapped = {"callback_query": {"id": "cb-1", "data": "dec:dec-9c816eda:deny"}}

    by_tap = mod.match_comment(mod.update_text(tapped), req)
    by_type = mod.match_comment("dec-9c816eda deny", req)

    assert by_tap.option == by_type.option == "deny"


def test_the_chat_of_a_tap_is_read_from_the_callback_message():
    mod = _load()
    tapped = {
        "callback_query": {
            "id": "cb-1",
            "data": "dec:x:y",
            "message": {"chat": {"id": 7}},
        }
    }

    assert mod.update_chat_id(tapped) == "7"


def test_an_oversized_option_is_left_out_rather_than_truncated():
    """Truncating callback_data would send a DIFFERENT option than the one labelled."""
    mod = _load()

    markup = mod.option_markup(
        "dec-1",
        (mod.DecisionOption("k" * 80, "Long"), mod.DecisionOption("ok", "Fine")),
    )

    buttons = [b for row in markup["inline_keyboard"] for b in row]
    assert [b["text"] for b in buttons] == ["Fine"]


def test_a_rejected_keyboard_never_costs_the_message(monkeypatch):
    """If Telegram refuses reply_markup, the founder must still get the question."""
    mod = _load()
    calls = []

    def fake_call(token, method, payload):
        calls.append(payload)
        if "reply_markup" in payload:
            return {"ok": False, "description": "Bad Request: reply markup"}
        return {"ok": True, "result": {"message_id": 99}}

    monkeypatch.setattr(mod, "telegram_call", fake_call)

    msg_id = mod.send_message(
        "t", "42", "hello", {"inline_keyboard": [[{"text": "x"}]]}
    )

    assert msg_id == 99
    assert len(calls) == 2 and "reply_markup" not in calls[1]


def test_the_ask_delivers_a_keyboard(monkeypatch, tmp_path):
    """The end of the wire that matters: the message the founder receives has buttons."""
    mod = _load()
    seen = {}

    def fake_send(token, chat, text, reply_markup=None):
        seen["markup"] = reply_markup
        return 123

    monkeypatch.setattr(mod, "send_message", fake_send)

    door = mod.Door(
        state_file=tmp_path / "one-tap-state.json",
        token="t",  # noqa: S106 - a placeholder for a unit test, not a credential
        chat_id="42",
    )
    door.ask(_request(mod))

    assert seen.get("markup") is not None, "the delivered message carried no buttons"
    buttons = [b for row in seen["markup"]["inline_keyboard"] for b in row]
    assert [b["text"] for b in buttons] == ["Approve them", "Leave them draft"]


def test_a_typed_answer_still_works():
    """No founder who prefers typing is cut off by the tap."""
    mod = _load()

    assert mod.match_comment("dec-9c816eda approve", _request(mod)).option == "approve"
