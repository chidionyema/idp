"""crew#596 — founder, 2026-08-28: "on Otto and founder surface set goal and tick to it".

The founder page and the Telegram GOAL pin render the same block: every open crew issue labelled `goal`,
one line per checkbox, ☑ when ticked. Nothing typed by hand; a missing label says so instead of going quiet.
"""

import importlib.machinery
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_loader(
    "estate_founder",
    importlib.machinery.SourceFileLoader(
        "estate_founder", str(ROOT / "bin" / "estate-founder")
    ),
)
ef = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ef)

ISSUES = [
    {
        "number": 596,
        "title": "Union: the road to 9D",
        "url": "https://github.com/x/crew/issues/596",
        "labels": ["goal"],
        "body": "intro\n- [x] CP1 Stage 1 gate green\n- [ ] CP2 Stage 2 gate = 9D\n",
    },
    {
        "number": 1,
        "title": "not a goal",
        "url": "u",
        "labels": [],
        "body": "- [ ] CP1 something",
    },
]


def test_goal_block_lists_only_goal_issues_with_ticks():
    lines = ef.goal_lines(ef.goals(ISSUES))
    assert (
        lines[0]
        == "**[crew#596](https://github.com/x/crew/issues/596)** Union: the road to 9D — 1/2 ticked"
    )
    assert lines[1:] == ["- ☑ CP1 Stage 1 gate green", "- ☐ CP2 Stage 2 gate = 9D"]
    assert not any("not a goal" in l for l in lines)


def test_no_goal_label_is_said_not_hidden():
    assert "goal is unset" in ef.goal_lines(ef.goals(ISSUES[1:]))[0]


def test_telegram_pin_edits_an_existing_goal_pin(monkeypatch, tmp_path):
    monkeypatch.setenv("ESTATE_FOUNDER_GOAL_STATE", str(tmp_path / "goal"))
    calls = []

    class R:
        def __init__(self, body):
            self.body = body

        def read(self):
            return json.dumps({"result": self.body}).encode()

    def urlopen(url, data=None, timeout=0):
        calls.append(url.rsplit("/", 1)[1])
        if url.endswith("getChat"):
            return R({"pinned_message": {"message_id": 7, "text": "GOAL old"}})
        return R({"message_id": 7})

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_HOME_CHANNEL", "c")
    assert ef.telegram_pin("GOAL new", urlopen=urlopen) == "7"
    assert calls == ["getChat", "editMessageText"]


def test_telegram_pin_sends_and_pins_when_no_goal_pin(monkeypatch, tmp_path):
    monkeypatch.setenv("ESTATE_FOUNDER_GOAL_STATE", str(tmp_path / "goal"))
    calls = []

    class R:
        def __init__(self, body):
            self.body = body

        def read(self):
            return json.dumps({"result": self.body}).encode()

    def urlopen(url, data=None, timeout=0):
        calls.append(url.rsplit("/", 1)[1])
        return R(
            {"pinned_message": {"message_id": 1}}
            if url.endswith("getChat")
            else {"message_id": 9}
        )

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_HOME_CHANNEL", "c")
    assert ef.telegram_pin("GOAL", urlopen=urlopen) == "9"
    assert calls == ["getChat", "sendMessage", "pinChatMessage"]


def test_incident_20260829_goal_post_never_takes_the_pin_from_a_founder_action(
    monkeypatch, tmp_path
):
    """06:07Z: the GOAL pin replaced founder-blocker's pinned FOUNDER ACTION (Telegram 18778) and the
    founder said "not seeing the message". While a FOUNDER ACTION or STAGED message holds the pin,
    the goal is sent but not pinned."""
    for holder in ("FOUNDER ACTION: open the form", "STAGED: rotate is ready"):
        monkeypatch.setenv("ESTATE_FOUNDER_GOAL_STATE", str(tmp_path / holder[:6]))
        calls = []

        class R:
            def __init__(self, body):
                self.body = body

            def read(self):
                return json.dumps({"result": self.body}).encode()

        def urlopen(url, data=None, timeout=0):
            calls.append(url.rsplit("/", 1)[1])
            return R(
                {"pinned_message": {"message_id": 5, "text": holder}}
                if url.endswith("getChat")
                else {"message_id": 9}
            )

        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
        monkeypatch.setenv("TELEGRAM_HOME_CHANNEL", "c")
        assert ef.telegram_pin("GOAL", urlopen=urlopen) == "9"
        assert calls == ["getChat", "sendMessage"], holder


def test_incident_20260829_goal_is_one_message_edited_while_a_founder_action_holds_the_pin(
    monkeypatch, tmp_path
):
    """Founder, 2026-08-29: "how do i get anything done with 6vnessages ? nost of then recurring".
    Four catalog-renders a day each sent a new GOAL message while his Tailscale action held the pin."""
    calls = []
    state = tmp_path / "goal"

    class R:
        def __init__(self, body):
            self.body = body

        def read(self):
            return json.dumps({"result": self.body}).encode()

    def urlopen(url, data=None, timeout=0):
        calls.append(url.rsplit("/", 1)[1])
        if url.endswith("getChat"):
            return R(
                {
                    "pinned_message": {
                        "message_id": 18845,
                        "text": "FOUNDER ACTION: Tailscale, one form",
                    }
                }
            )
        return R({"message_id": 18900})

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_HOME_CHANNEL", "c")
    monkeypatch.setenv("ESTATE_FOUNDER_GOAL_STATE", str(state))
    assert ef.telegram_pin("GOAL one", urlopen=urlopen) == "18900"
    assert calls == ["getChat", "sendMessage"], (
        calls
    )  # posted once, pin left to the founder action
    assert state.read_text() == "18900"
    calls.clear()
    assert ef.telegram_pin("GOAL two", urlopen=urlopen) == "18900"
    assert calls == ["getChat", "editMessageText"], (
        calls
    )  # the second run edits, never a new message
