"""handback.py: a turn that returns work to the founder is blocked; a proven blocker or a clean report is not."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import handback  # noqa: E402

HANDBACKS = [
    "Shipped the detector.\n\nStill open:\n- wire the router",
    "The change is merged. Want me to deploy it?",
    "Done with the hook. Shall I add the plugin tests too?",
    "Landed. Let me know if you want the pi extension next.",
    "## Next steps\n1. add cursor support",
    "**Remaining work:** the opencode plugin",
    "That's the first half. When you're ready, run the lane.",
    "I'll leave the rest to you.",
    "You'll need to restart the router for this to take effect.",
    "I'll wait for your go-ahead.",
]

CLEAN = [
    "Wired the hook, ran 14 tests, all pass. The lane head is 9cc4f9c and the ledger shows the refusal.",
    'The detector blocks "still open" lists; verified with test_handback.py (14 passed).',
    "```\nStill open:\n- example inside a fence\n```\nThat output is the fixture the test feeds in.",
    "> Want me to continue?\nThe quoted line above is what the model said before the fix.",
    "Fixed `want me to` handling in the quoted-phrase stripper; tests pass.",
    "It is still opened by the router at startup, so the socket stays live.",
]

BLOCKER = (
    "Blocked: the lane cannot push.\n\n```\n$ estate-execute lane-submit\nexit status 1\n"
    "fatal: Authentication failed for 'ssh://git@github.com/chidionyema/idp'\n```\n"
    "Tried the SSH key and the API path; both refused. Let me know if the key is rotated."
)


def test_handback_phrases_are_blocked():
    for text in HANDBACKS:
        verdict = handback.judge(text)
        assert verdict["block"], text
        assert verdict["found"], text
        assert "Do not stop here" in verdict["reason"]


def test_clean_reports_pass():
    for text in CLEAN:
        verdict = handback.judge(text)
        assert not verdict["block"], (text, verdict["found"])


def test_evidenced_blocker_passes_even_with_a_handback_phrase():
    verdict = handback.judge(BLOCKER)
    assert verdict["found"], "the phrase is still seen"
    assert not verdict["block"]


def test_blocker_claim_without_evidence_is_still_blocked():
    # "blocked" with no intent run and no exit status is a guess, not a blocker (AGENTS.md section 3).
    assert handback.judge("I'm blocked. Let me know if you can unblock me.")["block"]
    assert handback.judge(
        "Blocked on auth; estate-execute lane-submit was refused. Let me know if it changes."
    )["block"]


def test_stop_hook_active_allows_so_one_retry_never_loops():
    assert not handback.judge(HANDBACKS[0], stop_hook_active=True)["block"]


def test_blind_input_allows():
    for blind in ("", "   \n", None, 7):
        assert not handback.judge(blind)["block"]


def _line(role: str, content, kind: str | None = None) -> str:
    return json.dumps(
        {"type": kind or role, "message": {"role": role, "content": content}}
    )


def test_transcript_judges_only_the_last_agent_message_of_the_final_turn():
    transcript = "\n".join(
        [
            _line("user", "build it"),
            _line("assistant", [{"type": "text", "text": "Still open: everything"}]),
            _line("user", [{"type": "tool_result", "content": "ok"}]),
            _line(
                "assistant", [{"type": "text", "text": "Built and proven: 14 passed."}]
            ),
        ]
    )
    assert handback.last_agent_text(transcript) == "Built and proven: 14 passed."
    assert not handback.judge_transcript(transcript)["block"]

    closing = (
        transcript
        + "\n"
        + _line("assistant", [{"type": "text", "text": "Want me to ship it?"}])
    )
    assert handback.judge_transcript(closing)["block"]


def test_earlier_turn_does_not_leak_into_the_next():
    transcript = "\n".join(
        [
            _line("user", "first"),
            _line("assistant", [{"type": "text", "text": "Want me to continue?"}]),
            _line("user", "second"),
        ]
    )
    assert handback.last_agent_text(transcript) == ""
    assert not handback.judge_transcript(transcript)["block"]


def test_unreadable_transcript_allows():
    assert handback.last_agent_text("not json at all\n{broken") is None
    assert not handback.judge_transcript("not json at all\n{broken")["block"]
    assert not handback.judge_transcript("")["block"]


def test_cli_check_roundtrip():
    out = subprocess.run(
        [sys.executable, str(Path(handback.__file__)), "check"],
        input="Want me to push it?",
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert json.loads(out)["block"] is True
    assert (
        subprocess.run(
            [sys.executable, str(Path(handback.__file__)), "nope"], capture_output=True
        ).returncode
        == 2
    )
    said = subprocess.run(
        [sys.executable, str(Path(handback.__file__)), "directive"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert said.strip() == handback.DIRECTIVE


def test_directive_names_the_blocker_evidence():
    for needle in ("estate-execute", "exit status", "operational and proven"):
        assert needle in handback.DIRECTIVE
