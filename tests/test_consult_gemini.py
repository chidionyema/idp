"""consult.gemini contract: one door (the router), named failures, loud fallback, bounded context.

Each test fails if the behaviour it names is removed. Google is never called: the HTTP
function is injected.
"""

import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "platform" / "estate" / "libexec" / "consult_gemini.py"
INTENT = ROOT / "platform" / "estate" / "intents" / "consult-gemini.yaml"

spec = importlib.util.spec_from_file_location("consult_gemini", HELPER)
cg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cg)


def reply(model, text="an answer"):
    return {"model": model, "choices": [{"message": {"content": text}}]}


def test_answers_through_the_router_not_google():
    seen = {}

    def post(url, key, payload, timeout):
        seen.update(url=url, model=payload["model"])
        return reply("gemini/gemini-2.5-flash")

    text, replied, requested, notes = cg.consult(
        "review x", [], "gemini", 1000, 5, "k", post=post
    )
    assert seen["url"].endswith("/v1/chat/completions")
    assert "googleapis" not in seen["url"]
    assert (text, replied, requested, notes) == (
        "an answer",
        "gemini/gemini-2.5-flash",
        "gemini",
        [],
    )


def test_a_refusing_lane_falls_back_and_says_so():
    calls = []

    def post(url, key, payload, timeout):
        calls.append(payload["model"])
        if payload["model"] == "gemini":
            raise cg.ConsultError("router answered HTTP 402")
        return reply("openai/MiniMax-M3")

    _, replied, requested, notes = cg.consult(
        "q", [], "gemini", 1000, 5, "k", post=post
    )
    assert calls == ["gemini", "default"]
    assert replied == "openai/MiniMax-M3" and requested == "gemini"
    assert any("retried on default" in n for n in notes)


def test_both_lanes_dead_is_a_named_error_not_a_hang():
    def post(*a, **k):
        raise cg.ConsultError("router unreachable or timed out")

    with pytest.raises(cg.ConsultError, match="unreachable"):
        cg.consult("q", [], "gemini", 1000, 5, "k", post=post)


@pytest.mark.parametrize(
    "question,key,msg", [("", "k", "empty"), ("q", "", "no router key")]
)
def test_refuses_before_spending(question, key, msg):
    def post(*a, **k):
        raise AssertionError("must not call the router")

    with pytest.raises(cg.ConsultError, match=msg):
        cg.consult(question, [], "gemini", 1000, 5, key, post=post)


def test_empty_answer_is_an_error():
    with pytest.raises(cg.ConsultError, match="empty"):
        cg.ask("gemini", "q", "", "k", 5, post=lambda *a: reply("m", "  "))


def test_context_is_bounded_and_the_cut_is_named(tmp_path):
    big = tmp_path / "big.md"
    big.write_text("x" * 5000)
    ctx, cut = cg.build_context([str(big)], 1000)
    assert str(big) in cut and "TRUNCATED at 1000 of 5000 bytes" in ctx
    assert len(ctx.encode()) < 1500


def test_missing_context_file_is_named(tmp_path):
    with pytest.raises(cg.ConsultError, match="not found"):
        cg.build_context([str(tmp_path / "nope.md")], 1000)


def test_review_is_saved_with_the_model_that_answered(tmp_path):
    path, footer = cg.save(tmp_path, "Is the lane safe?", "yes", "m1", "gemini", ["n1"])
    body = path.read_text()
    assert path.name.endswith("-consult-is-the-lane-safe.md")
    assert "answered by: m1 (asked: gemini)" in body and "note: n1" in body


def test_intent_is_committed_and_runs_the_helper():
    d = yaml.safe_load(INTENT.read_text())
    assert d["name"] == INTENT.stem
    assert "question" in d["args"] and d["halt_on_failure"] is True
    assert "consult_gemini.py" in d["steps"][0]["cmd"]


def test_default_asks_a_named_gemini_model_not_the_pinned_lane():
    # The router's `gemini` lane is pinned to gemini-2.5-flash, which Google 404s for new users,
    # so it answered as MiniMax. The default must name the live model directly.
    assert cg.DEFAULT_MODEL.startswith("gemini/")
    assert cg.DEFAULT_MODEL != "gemini"
    assert (
        yaml.safe_load(INTENT.read_text())["args"]["model"]["default"]
        == cg.DEFAULT_MODEL
    )


def test_the_fallback_gets_what_the_door_has_left_not_a_fresh_timeout():
    # One door bounds the invocation: a Gemini ask that burns its whole timeout must leave the
    # fallback a bounded, positive budget that still fits inside the 100s door.
    seen = []

    def post(url, key, payload, timeout):
        seen.append((payload["model"], timeout))
        if payload["model"] == cg.DEFAULT_MODEL:
            raise cg.ConsultError("429 free-tier quota")
        return reply("default", "answer")

    cg.consult("q", [], cg.DEFAULT_MODEL, 1000, 70, "k", post=post)
    assert [m for m, _ in seen] == [cg.DEFAULT_MODEL, "default"]
    assert 15 <= seen[1][1] <= cg.FALLBACK_RESERVE_S + 70
    assert 70 + seen[1][1] - 70 <= 100
