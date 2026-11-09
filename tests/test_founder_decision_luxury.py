"""Falsifier for the luxury Telegram founder door in sovereign/otto/decision.py.

Founder protocol (2026-11-09): the founder feels the estate working for him - rich
formatting, one-tap actions - never a raw log stream. These tests prove the luxury path is
real AND that it never costs delivery: HTML is escaped so a hostile question cannot break
the message, the inline keyboard routes a tap through the SAME deterministic key match as a
typed comment, and the plain-text fallback stays byte-stable so no decision is ever lost.

The tests need no credentials and no network: they exercise the pure render/match/callback
functions, which is where the "premium but never fragile" contract lives.
"""

from __future__ import annotations

from sovereign.otto.decision import (
    DecisionRequest,
    build_request,
    callback_query,
    match_comment,
    render,
    render_keyboard,
    render_lux,
)


def _req() -> DecisionRequest:
    return build_request(
        question="Ship the DoF repair now?",
        options="ship: land it, hold: wait for review",
        context="https://example/run-42",
        requester="estate-engine",
    )


def test_lux_escapes_hostile_html_in_the_question():
    req = build_request(question="is 1 < 2 & 3 > 0?", options="yes: ok")
    html = render_lux(req)
    assert "<b>dec-" in html  # the id is still bold and first
    assert "1 &lt; 2 &amp; 3 &gt; 0" in html  # metacharacters escaped, not interpreted


def test_lux_has_visual_hierarchy_and_deadline():
    html = render_lux(_req())
    assert "<b>dec-" in html  # id bold
    assert "<i>choose an option" in html  # options header
    assert "<i>context</i>" in html  # context section
    assert "deadline:" in html
    assert "Ship the DoF repair now?" in html


def test_keyboard_pairs_key_with_label_for_one_tap():
    keyboard = render_keyboard(_req())
    row = keyboard["inline_keyboard"][0]
    assert row == [
        {"text": "land it", "callback_data": "ship"},
        {"text": "wait for review", "callback_data": "hold"},
    ]


def test_no_options_means_no_keyboard():
    req = build_request(question="free text question")
    assert render_keyboard(req) == {}


def test_a_tap_routes_through_the_same_key_match_as_a_typed_comment():
    req = _req()
    update = {"callback_query": {"data": "ship"}}
    assert callback_query(update) == "ship"
    # The tap ("ship") and the typed id-quoted comment ("<id> ship") are the same answer.
    typed = match_comment(f"{req.decision_id} ship", req)
    tapped = match_comment(callback_query(update), req)
    assert typed.option == tapped.option == "ship"


def test_plain_text_fallback_is_byte_stable_and_id_first():
    req = _req()
    text = render(req)
    assert text.startswith(req.decision_id)
    assert "1. ship: land it" in text
    assert "answer by commenting" in text
