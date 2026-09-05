"""cp36 acceptance: the hermes plugin turns Telegram into a receipt channel.

Owner: crew#284 CP1 (sovereign/otto/hermes_plugin). The two real boundaries
are stubbed: `sb` (a subprocess) and the Telegram Bot API (card._send).
Everything between them -- the hook's decision, the receipt formatter, the
argv handed to sb -- is real.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from sovereign.presence import config_keys as presence_ck

scenarios("features/sovereign-bus/cp36_telegram_kernel.feature")

PLUGIN = Path(__file__).resolve().parents[2] / "otto" / "hermes_plugin" / "__init__.py"


@pytest.fixture
def plugin(monkeypatch):
    spec = importlib.util.spec_from_file_location("hermes_sovereign_plugin", PLUGIN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    calls: list[list[str]] = []
    sent: list[str] = []
    chain: list[dict] = []

    def fake_run_sb(*args):
        calls.append(list(args))
        if args[0] == "intake":
            return True, {"line": "[✓] DOC_COMMIT | file:docs/save-this-article.md | hash:8f2a1b3c | tags:#ml | budget:-1.2k | state:8f2a1b3c", "commit": "8f2a1b3c"}
        if args[0] == "episodes":
            return True, chain
        return True, {}

    monkeypatch.setattr(mod, "_run_sb", fake_run_sb)
    monkeypatch.setattr(mod, "_send_line", lambda event, line: sent.append(line) or True)
    mod._test = SimpleNamespace(calls=calls, sent=sent, chain=chain, event=None, result=None, reply=None)
    return mod


@given(parsers.parse('the founder sends a photo with caption "{caption}"'))
def photo_with_caption(plugin, tmp_path, caption):
    img = tmp_path / "photo.jpg"
    img.write_bytes(b"\xff\xd8\xff")
    plugin._test.event = SimpleNamespace(text=caption, media_urls=[str(img)], source=SimpleNamespace(chat_id="42"))


@given("the founder sends a photo with no caption")
def photo_no_caption(plugin, tmp_path):
    img = tmp_path / "photo.jpg"
    img.write_bytes(b"\xff\xd8\xff")
    plugin._test.event = SimpleNamespace(text="", media_urls=[str(img)], source=SimpleNamespace(chat_id="42"))


@given(parsers.parse('session "{sid}" has a receipt of kind "{kind}" in the chain'))
def receipt_in_chain(plugin, sid, kind):
    plugin._test.chain.append({"session_id": sid, "kind": kind, "hash": "abcdef0123456789", "counter": 7, "tokens": 120, "status": "ok", "fsm_state": "terminal"})


@when("the gateway pre-dispatch hook runs")
def run_hook(plugin):
    plugin._test.result = plugin.on_pre_gateway_dispatch(event=plugin._test.event, gateway=None, session_store=None)


@when(parsers.parse('the founder sends "/sb-undo {args}"'))
def send_undo(plugin, args):
    plugin._test.reply = plugin.sb_undo(args)


@when(parsers.parse('the founder sends "/sb-stop {args}"'))
def send_stop(plugin, args):
    plugin._test.reply = plugin.sb_stop(args)


@then("the message is skipped before dispatch")
def skipped(plugin):
    assert plugin._test.result and plugin._test.result["action"] == "skip"
    assert plugin._test.calls[0][:2] == ["intake", plugin._test.event.media_urls[0]]
    assert "--caption" in plugin._test.calls[0]


@then("exactly one Telegram message is sent")
def one_sent(plugin):
    assert len(plugin._test.sent) == 1


@then(parsers.parse('that message is one line containing "{word}", a hash and a budget delta'))
def one_line(plugin, word):
    line = plugin._test.sent[0]
    assert "\n" not in line and word in line and "hash:" in line and "budget:" in line


@then("the hook returns None")
def returns_none(plugin):
    assert plugin._test.result is None
    assert plugin._test.calls == []


@then(parsers.parse('sb was invoked with "{argv}"'))
def sb_argv(plugin, argv):
    assert argv.split() in plugin._test.calls


@then(parsers.parse('the reply is one line starting with the ok mark and "{op}"'))
def reply_line(plugin, op):
    mark = str(presence_ck.resolve("presence.receipt_ok_mark"))
    reply = plugin._test.reply
    assert reply is not None and "\n" not in reply
    assert reply.startswith(f"{mark} {op}"), reply
    assert "hash:" in reply and "budget:" in reply
