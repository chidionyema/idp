"""The router, not the harness, decides when Opus runs: only on a Claude Code plan-mode turn.

Measured 2026-09-28: opusplan sessions ran Sonnet only (71 sessions), but 35 interactive sessions
pinned Opus with /model and produced 88% of all turns -- a setting any session can override is not
a guarantee. The marker is the exact text Claude Code 2.1.283 injects in plan mode.
"""

from __future__ import annotations

import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "platform", "llm", "efficiency_gateway.py")


def _gw():
    spec = importlib.util.spec_from_file_location("efficiency_gateway", PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PLAN = (
    "Plan mode is active. The user indicated that they do not want you to execute yet"
)


def _req(model, text, pad=0):
    return {
        "model": model,
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": text + "x" * pad}]}
        ],
    }


def test_opus_outside_plan_mode_runs_on_sonnet():
    g = _gw()
    data = _req("claude-opus-5-5", "fix the bug")
    assert g._route_model(data) == g.EXECUTOR_MODEL


def test_opus_in_plan_mode_stays_opus():
    g = _gw()
    data = _req(
        "claude-opus-5-5", "<system-reminder>" + PLAN + "</system-reminder> plan it"
    )
    assert g._route_model(data) == "claude-opus-5-5"


def test_plan_marker_only_counts_in_the_newest_user_turn():
    g = _gw()
    data = _req("claude-opus-5-5", PLAN)
    data["messages"] += [
        {"role": "assistant", "content": [{"type": "text", "text": "plan"}]},
        {"role": "user", "content": [{"type": "text", "text": "go build it"}]},
    ]
    assert g._route_model(data) == g.EXECUTOR_MODEL


def test_non_opus_models_are_untouched():
    g = _gw()
    for m in ("claude-sonnet-5", "claude-haiku-4-5", "groq"):
        assert g._route_model(_req(m, "hi")) == m


def test_a_context_too_large_for_the_executor_keeps_its_model():
    g = _gw()
    data = _req("claude-opus-5-5", "big", pad=g.EXECUTOR_MAX_BYTES + 1)
    assert g._route_model(data) == "claude-opus-5-5"
