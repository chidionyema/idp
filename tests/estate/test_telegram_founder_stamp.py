"""The Telegram ingress stamps the founder's own words into the canonical prompt ledger.

Falsifiers, not assertions. The stamp must HAPPEN, through the ONE canonical door, with the
right arguments; it must happen ONCE per message; a decision answer must NOT be stamped as a
new task; and it must FAIL OPEN -- a dead ledger never blocks the founder's message (AGENTS.md
section 3: a claim without its proof is not made; section 9, R1: a gate that cannot fail is not
a gate -- and here, a gate that can fail the founder's message is worse than no gate).
"""

import importlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

plugin = importlib.import_module("sovereign.otto.hermes_plugin")


class _Source:
    def __init__(self, chat_id):
        self.chat_id = chat_id


class _Event:
    def __init__(self, text, chat_id="42", media=None):
        self.text = text
        self.source = _Source(chat_id)
        self.media_urls = media or []


class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _capture(monkeypatch, result=None, raises=None):
    """Record every subprocess call the plugin makes, without making one."""
    calls = []

    def fake_run(cmd, **kw):
        calls.append({"cmd": list(cmd), "input": kw.get("input")})
        if raises is not None:
            raise raises
        if result is not None:
            return result
        return _Proc(stdout=json.dumps({"id": "prompt-0001"}))

    monkeypatch.setattr(plugin.subprocess, "run", fake_run)
    return calls


def _quiet(monkeypatch):
    """No decision door, no bus, no Telegram: this file tests the stamp, nothing else."""
    monkeypatch.setattr(plugin, "_decision_answer", lambda text: None)
    monkeypatch.setattr(plugin, "_publish_in_background", lambda event: None)


def test_the_founder_words_are_stamped_through_the_canonical_door(monkeypatch):
    _quiet(monkeypatch)
    calls = _capture(monkeypatch)

    assert plugin.on_pre_gateway_dispatch(_Event("ship the protocol kit")) is None

    assert len(calls) == 1, "the founder's words must be stamped exactly once"
    cmd = calls[0]["cmd"]
    assert cmd[1].endswith("bin/estate-founder-intake"), cmd
    assert "--stdin" in cmd
    assert "--source" in cmd and cmd[cmd.index("--source") + 1] == "telegram", cmd
    assert "--session" in cmd and cmd[cmd.index("--session") + 1] == "tg-42", cmd
    assert "--no-publish" in cmd, "the stamp must not make the founder wait for the bus"
    assert "--json" in cmd
    assert calls[0]["input"] == "ship the protocol kit"


def test_a_message_without_a_chat_id_is_stamped_under_a_named_session(monkeypatch):
    _quiet(monkeypatch)
    calls = _capture(monkeypatch)
    event = _Event("hello")
    event.source = _Source(None)

    plugin.on_pre_gateway_dispatch(event)

    assert len(calls) == 1
    cmd = calls[0]["cmd"]
    assert cmd[cmd.index("--session") + 1] == "tg-unknown"


def test_a_decision_answer_is_not_stamped_as_a_new_task(monkeypatch):
    monkeypatch.setattr(
        plugin,
        "_decision_answer",
        lambda text: {"state": "answered", "decision_id": "D1", "option": "a"},
    )
    monkeypatch.setattr(plugin, "_publish_in_background", lambda event: None)
    calls = _capture(monkeypatch)

    out = plugin.on_pre_gateway_dispatch(_Event("D1 a"))

    assert isinstance(out, dict) and out.get("action") == "skip"
    assert calls == [], "the decision door already recorded those words"


def test_a_dead_intake_door_never_blocks_the_founder(monkeypatch):
    _quiet(monkeypatch)
    _capture(monkeypatch, raises=OSError("the ledger is unreachable"))

    # No exception, and the message dispatches normally: the founder's words are never held
    # hostage by the estate's bookkeeping.
    assert plugin.on_pre_gateway_dispatch(_Event("do the thing")) is None


def test_a_refused_intake_door_never_blocks_the_founder(monkeypatch):
    _quiet(monkeypatch)
    _capture(monkeypatch, result=_Proc(returncode=4, stderr="refused"))

    assert plugin.on_pre_gateway_dispatch(_Event("do the thing")) is None


def test_the_state_is_published_once_per_message_and_in_the_background(monkeypatch):
    monkeypatch.setattr(plugin, "_decision_answer", lambda text: None)
    published = []
    monkeypatch.setattr(
        plugin, "_publish_in_background", lambda event: published.append(event)
    )
    _capture(monkeypatch)

    plugin.on_pre_gateway_dispatch(_Event("look at the links"))

    assert len(published) == 1, (
        "the live state must be published on every founder message"
    )


def test_a_publication_that_moved_the_state_is_the_only_one_spoken(monkeypatch):
    """The founder hears a line when the state MOVED, not on every message."""
    monkeypatch.setattr(plugin, "_decision_answer", lambda text: None)
    monkeypatch.setattr(
        plugin,
        "_publish_plan_link_state",
        lambda: "published: plan links: 1 sessions, 0 violations, 0 gaps",
    )
    sent = []
    monkeypatch.setattr(
        plugin, "_send_line", lambda event, line: sent.append(line) or True
    )

    plugin._publish_in_background(_Event("x"))

    # The background thread is a thread: wait for it, bounded.
    import time

    for _ in range(100):
        if sent:
            break
        time.sleep(0.01)
    assert sent == ["plan links: 1 sessions, 0 violations, 0 gaps"], sent


def test_an_unchanged_state_is_never_spoken(monkeypatch):
    monkeypatch.setattr(plugin, "_decision_answer", lambda text: None)
    monkeypatch.setattr(
        plugin,
        "_publish_plan_link_state",
        lambda: "unchanged: plan links: 1 sessions, 0 violations, 0 gaps",
    )
    sent = []
    monkeypatch.setattr(
        plugin, "_send_line", lambda event, line: sent.append(line) or True
    )

    plugin._publish_in_background(_Event("x"))

    import time

    time.sleep(0.2)
    assert sent == [], sent
