"""The founder-action door: one message, one tap, no model in the path.

An action is something no agent can do. It travels the founder-decision door: ONE Telegram
message with buttons. A tap from the founder's chat is the answer; a tap from anywhere else,
for an unknown decision, or with an unknown key records nothing. Telegram is replaced by a
list of calls, so what is asserted is the door's own behaviour.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_LIB = Path(__file__).resolve().parents[1] / "sovereign" / "otto" / "decision.py"
FOUNDER_CHAT = "1001"


def _load():
    spec = importlib.util.spec_from_file_location("estate_founder_action", _LIB)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["estate_founder_action"] = module
    spec.loader.exec_module(module)
    return module


decision = _load()


class FakeTelegram:
    def __init__(self) -> None:
        self.calls: list = []
        self.updates: list = []

    def __call__(self, token, method, payload, timeout_s=10.0):
        self.calls.append((method, payload))
        if method == "sendMessage":
            return {"ok": True, "result": {"message_id": 77}}
        if method == "getUpdates":
            return {"ok": True, "result": self.updates}
        return {"ok": True, "result": True}

    def sent(self) -> list:
        return [p for m, p in self.calls if m == "sendMessage"]

    def toasts(self) -> list:
        return [p["text"] for m, p in self.calls if m == "answerCallbackQuery"]


@pytest.fixture
def tg(monkeypatch):
    fake = FakeTelegram()
    monkeypatch.setattr(decision, "telegram_call", fake)
    return fake


@pytest.fixture
def door(tmp_path, tg):
    return decision.Door(
        state_file=tmp_path / "decisions.json", token="T", chat_id=FOUNDER_CHAT
    )


def _action(door, **kw):
    request = decision.build_request(
        question=kw.pop("question", "Approve the Google sign-in for gcloud"),
        kind="action",
        proof=kw.pop("proof", "gcloud auth list shows the account"),
        decision_id=kw.pop("decision_id", "dec-aaaa1111"),
        **kw,
    )
    return door.ask(request)


def _tap(tg, data, chat=FOUNDER_CHAT, cid="cb1"):
    tg.updates = [
        {
            "update_id": 1,
            "callback_query": {
                "id": cid,
                "data": data,
                "message": {"chat": {"id": int(chat)}},
            },
        }
    ]


def test_action_sends_one_message_with_buttons_and_default_options(door, tg):
    record = _action(door)
    assert record["ok"] and record["kind"] == "action"
    (sent,) = tg.sent()
    keys = [row[0]["callback_data"] for row in sent["reply_markup"]["inline_keyboard"]]
    assert keys == ["dec-aaaa1111:done", "dec-aaaa1111:cannot"]
    assert "ACTION ONLY YOU CAN DO" in sent["text"]
    assert "proof it is done: gcloud auth list" in sent["text"]


def test_asking_twice_sends_no_second_message(door, tg):
    _action(door)
    again = _action(door)
    assert again["idempotent"] is True
    assert len(tg.sent()) == 1


def test_founder_tap_records_the_option(door, tg):
    _action(door)
    _tap(tg, "dec-aaaa1111:done")
    result = door.poll()
    assert result["answered"] == ["dec-aaaa1111"]
    record = door.show("dec-aaaa1111")
    assert record["state"] == "answered" and record["option"] == "done"
    assert tg.toasts() == ["recorded"]


def test_tap_from_another_chat_records_nothing(door, tg):
    _action(door)
    _tap(tg, "dec-aaaa1111:done", chat="999")
    assert door.poll()["answered"] == []
    assert door.show("dec-aaaa1111")["state"] == "asked"


def test_tap_for_unknown_decision_or_key_records_nothing(door, tg):
    _action(door)
    _tap(tg, "dec-ffff0000:done")
    assert door.poll()["answered"] == []
    _tap(tg, "dec-aaaa1111:approve-everything")
    assert door.poll()["answered"] == []
    assert door.show("dec-aaaa1111")["state"] == "asked"


def test_second_tap_does_not_rewrite_the_first_answer(door, tg):
    _action(door)
    _tap(tg, "dec-aaaa1111:cannot")
    door.poll()
    _tap(tg, "dec-aaaa1111:done", cid="cb2")
    assert door.poll()["answered"] == []
    assert door.show("dec-aaaa1111")["option"] == "cannot"
    assert tg.toasts()[-1] == "already answered"


def test_action_without_proof_is_refused():
    with pytest.raises(decision.DecisionError):
        decision.build_request(question="Do the thing", kind="action", proof="")


def test_unknown_kind_is_refused():
    with pytest.raises(decision.DecisionError):
        decision.build_request(question="x", kind="wish")


def test_button_payload_over_64_bytes_is_refused_at_build_time():
    with pytest.raises(decision.DecisionError):
        decision.build_request(
            question="x",
            options=f"{'k' * 31}: long",
            decision_id="dec-" + "a" * 32,
        )


def test_plain_decision_is_unchanged(door, tg):
    request = decision.build_request(
        question="Ship it?", options="ship: go, hold: wait", decision_id="dec-bbbb2222"
    )
    record = door.ask(request)
    assert record["kind"] == "decision"
    assert "ACTION ONLY" not in tg.sent()[0]["text"]
    assert door.absorb("dec-bbbb2222 ship")["option"] == "ship"
