"""cp23 acceptance: Presence -- Ghost is the default; the chat is the fire alarm, not the control room

Owner: W3 (R1, R13). Steps drive sovereign.presence for real against the
temporary estate: the receipt chain is the real one, the alert inbox is
the real file, and the only fake is the Telegram boundary (MessageSink,
plus the otto card's two Telegram calls routed into it so that any send
the card attempted would be visible as a chat message).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from .conftest import MessageSink

scenarios("features/sovereign-bus/cp23_presence_ghost.feature")


@pytest.fixture
def telegram_into_sink(monkeypatch: pytest.MonkeyPatch, messages: MessageSink, context: dict[str, Any]):
    """Every Telegram call sovereign/ can make lands in the sink. A send is
    a new chat message; an edit is recorded separately (an edit is not a
    message, spec 2.2)."""
    from sovereign.otto import card

    context["edits"] = []
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_HOME_CHANNEL", "-100")
    # The pinned card already exists (cp4 adopts it by id); a new card
    # would be a send, and routine work sends nothing.
    context["card_id"] = 1
    monkeypatch.setenv("SB_ADOPT_CARD_ID", str(context["card_id"]))
    monkeypatch.setattr(card, "_send", lambda chat_id, text, keyboard=None: messages.send("telegram", text).text and 1)
    monkeypatch.setattr(card, "_edit", lambda chat_id, mid, text, keyboard=None: context["edits"].append((mid, text)) or True)
    monkeypatch.setattr(card, "_pin", lambda chat_id, mid: None)
    return messages


def _row(i: int, status: str = "done") -> dict[str, Any]:
    return {
        "session_id": f"sb-{i:04d}",
        "task": f"task {i}",
        "step": 3,
        "status": status,
        "runner": "echo",
        "kind": "step",
        "budget": 2000,
        "budget_remaining": 1500,
        "tokens": 500,
        "commit": f"{i:040x}",
        "hash": f"{i:064x}",
        "updated_at": "2026-08-25T09:00:00+00:00",
        "line_message_id": 100 + i,
    }


# --- Routine execution sends nothing ---------------------------------------


@given("three sessions run to done within budget")
def _three_done(config, telegram_into_sink: MessageSink, context: dict[str, Any]) -> None:
    from sovereign.presence import router

    context["rows"] = [_row(i) for i in range(1, 4)]
    for row in context["rows"]:
        router.on_state_change(row)


@then("the Otto card was edited")
def _card_edited(context: dict[str, Any]) -> None:
    edited = {mid for mid, _text in context["edits"]}
    assert edited == {context["card_id"], *(row["line_message_id"] for row in context["rows"])}, context["edits"]


@then("zero new messages were sent to the chat")
def _silent(messages: MessageSink) -> None:
    messages.assert_silent()


@then("the inbox received every state change as a receipt")
def _inbox_has_receipts(config, context: dict[str, Any]) -> None:
    from sovereign.presence import config_keys

    lines = [json.loads(l) for l in Path(config.ESTATE_ALERT_INBOX).read_text().splitlines() if l.strip()]
    receipts = [l for l in lines if l.get("kind") == config_keys.resolve("presence.receipt_kind")]
    assert [r["session_id"] for r in receipts] == [row["session_id"] for row in context["rows"]]
    for r in receipts:
        assert "\n" not in r["line"] and "hash:" in r["line"] and "budget:" in r["line"]


# --- A catastrophe is exactly one message ----------------------------------


@given("a session's receipt hash no longer matches the repo")
def _tampered_chain(receipts_path: Path, context: dict[str, Any]) -> None:
    from sovereign.engine import receipts as receipts_mod

    row = receipts_mod.append({**_row(7, status="running"), "by": "worker", "text": "commit"})
    context["session_id"] = row["session_id"]
    context["hash"] = row["hash"]
    lines = receipts_path.read_text().splitlines()
    last = json.loads(lines[-1])
    last["commit"] = "f" * len(last["commit"])  # the repo moved under the receipt
    lines[-1] = json.dumps(last, sort_keys=True)
    receipts_path.write_text("\n".join(lines) + "\n")


@when("integrity verification fails")
def _verify_fails(messages: MessageSink, context: dict[str, Any]) -> None:
    from sovereign.engine import receipts as receipts_mod
    from sovereign.presence import router

    verdict = receipts_mod.verify()
    assert verdict["ok"] is False, verdict
    context["halted"] = []
    context["after"] = router.integrity_failure(
        verdict, context["session_id"], sink=messages, halt=context["halted"].append, detected_hash=context["hash"]
    )


@then("exactly one message is sent, containing the hash and the remediation command")
def _one_message(messages: MessageSink, context: dict[str, Any]) -> None:
    from sovereign.presence import config_keys

    msg = messages.assert_exactly_one()
    assert context["hash"] in msg.text
    assert config_keys.resolve("presence.remediation_command") in msg.text
    assert "?" not in msg.text


@then("the session is halted")
def _halted(context: dict[str, Any]) -> None:
    from sovereign.presence.fsm import Spatial

    assert context["halted"] == [context["session_id"]]
    assert context["after"] == Spatial(cause="catastrophe")


# --- The daily digest is six lines, signed ---------------------------------


@when(parsers.parse('I run "bin/sb {args}"'))
def _run_sb(sb, args: str, context: dict[str, Any]) -> None:
    result = sb(*args.split())
    assert result.ok, result.stderr
    context["digest"] = result.json()


@then(parsers.parse("the text has at most {n:d} lines"))
def _at_most(n: int, context: dict[str, Any]) -> None:
    assert len(context["digest"]["text"].splitlines()) <= n
    assert context["digest"]["lines"] <= n


@then("the text ends with the receipts-file hash it was built from")
def _ends_with_hash(receipts_path: Path, context: dict[str, Any]) -> None:
    from sovereign.presence import digest as digest_mod

    text = context["digest"]["text"]
    assert text.endswith(context["digest"]["receipts_hash"])
    assert text.endswith(digest_mod.receipts_file_hash(receipts_path))
    assert len(context["digest"]["sig"]) == 64
