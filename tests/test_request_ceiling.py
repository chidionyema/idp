"""The per-request ceiling refuses a call, and the refusal is what makes the leak impossible.

WHAT THIS GRADES. `platform/llm/request_ceiling.py` is a LiteLLM pre-call hook. The claim it
makes is not "the bill is lower" -- that is an effect nobody can assert from a unit test. The
claim is narrower and it is checkable: a request above the ceiling is REFUSED, and the refusal
comes back before anything is sent.

WHY THE ASSERTIONS ARE SHAPED THIS WAY. Every one of these was written against the measured
incident, not against an idea of one:

    2026-09-13  one key, 439 calls, 86,525,924 input tokens in 60 minutes
                largest single call 737,169 in / 436 out

So the test builds a request of exactly that size and requires a refusal, and builds a request of
an ordinary working size and requires passage. A guard that refuses the good case is an outage
(R38), and a guard that passes the bad case is this incident happening again.

THE HOOK IS CALLED THE WAY LITELLM CALLS IT. `async_pre_call_hook(user_api_key_dict, cache, data,
call_type)` -- taken from the signature LiteLLM 1.98.0 ships in
`litellm/integrations/custom_logger.py`, read from the running pod rather than from memory. A
test that invents its own calling convention proves nothing about the router.
"""

import asyncio
import importlib.util
import pathlib
import sys

import pytest

MODULE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "platform"
    / "llm"
    / "request_ceiling.py"
)


def _load():
    """Load the hook by path. It is mounted into the router image, not installed as a package."""
    spec = importlib.util.spec_from_file_location("request_ceiling", MODULE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["request_ceiling"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ceiling():
    return _load()


def _call(mod, data, key="sk-961a3bcddeadbeef"):
    """Call the hook exactly as LiteLLM does."""

    class _Key:
        api_key = key

    return asyncio.run(
        mod.EstateRequestCeiling().async_pre_call_hook(
            user_api_key_dict=_Key(), cache=None, data=data, call_type="completion"
        )
    )


def _request(tokens):
    """A request body carrying approximately `tokens` input tokens."""
    # 4 chars per token, the ratio the module and pi's own estimator both use.
    return {
        "model": "deepseek",
        "messages": [{"role": "user", "content": "x" * (tokens * 4)}],
    }


def test_the_measured_leak_is_refused(ceiling):
    """737,169 tokens in one call -- the exact largest call of the incident."""
    verdict = _call(ceiling, _request(737_169))
    assert verdict is not None, (
        "the 737k call that caused the incident was allowed through"
    )
    assert "Refused" in verdict or "refused" in verdict


def test_the_refusal_names_the_size_and_the_ceiling(ceiling):
    """A refused caller must be able to see what to do, or it retries."""
    verdict = _call(ceiling, _request(737_169))
    assert "737,169" in verdict.replace("~", "")
    assert f"{ceiling.MAX_INPUT_TOKENS:,}" in verdict
    # a retry loop is how one bad call became 439 -- the message must say retrying is pointless
    assert "compaction" in verdict.lower()


def test_the_default_is_the_ceiling_the_router_runs_at(ceiling):
    """The module default and bin/litellm-local's export are one number (idp#6675).

    This test used to require the incident's AVERAGE call (197,098) to be refused. That held only
    for the 128,000 default; the live router has run at 200,000 since litellm-local began
    exporting it, so the assertion graded a value nothing ran. Pinning the two together is the
    property that matters: router_catalog hands this module's number to pi as its window."""
    launcher = (MODULE.parents[2] / "bin" / "litellm-local").read_text()
    want = f'ESTATE_MAX_INPUT_TOKENS="${{ESTATE_MAX_INPUT_TOKENS:-{ceiling.MAX_INPUT_TOKENS}}}"'
    assert want in launcher


def test_a_call_just_over_the_ceiling_is_refused(ceiling):
    assert _call(ceiling, _request(ceiling.MAX_INPUT_TOKENS + 1_000)) is not None


def test_an_ordinary_working_turn_passes(ceiling):
    """R38: a guard that refuses correct work is an outage. This one must not."""
    assert _call(ceiling, _request(20_000)) is None


def test_a_call_exactly_at_the_ceiling_passes(ceiling):
    """The boundary is a ceiling, not a tripwire. At the limit is allowed."""
    assert _call(ceiling, _request(ceiling.MAX_INPUT_TOKENS)) is None


def test_tool_schemas_are_counted(ceiling):
    """Message text alone under-counts.

    A session accumulates tool schemas, and they ride on every call without appearing in
    `messages`. A ceiling that only counts messages is a ceiling a real session walks past:
    the message text here is an ordinary 1,000 tokens and the schemas are the whole breach.
    """
    data = _request(1_000)
    data["tools"] = [
        {"name": f"tool{i}", "description": "d" * 40_000} for i in range(20)
    ]
    verdict = _call(ceiling, data)
    assert verdict is not None, (
        "800k characters of tool schemas were not counted: the request measured as an "
        "ordinary turn"
    )


def test_the_refusal_never_echoes_the_api_key(ceiling):
    """A key in a log line is a key leaked. The message names the caller by prefix only."""
    secret = "sk-" + "SECRETTAIL" * 4 + "END961a3bcd"
    verdict = _call(ceiling, _request(737_169), key=secret)
    assert "SECRETTAIL" not in verdict
    assert "961a3bcd" in verdict, "the refusal does not say which caller to go and fix"


# pi-coding-agent's OVERFLOW_PATTERNS, the ones a 400 can match to be classed as "context too big"
# (read from pi's bundle 2026-10-20, @earendil-works/pi-coding-agent). Only the ones a router
# message could plausibly satisfy are copied; the point is the contract, not a full mirror.
_PI_OVERFLOW_PATTERNS = [
    r"exceeds (?:the )?(?:model'?s )?maximum context length(?: of [\d,]+ tokens?|\s*\([\d,]+\))",
    r"maximum context length is \d+ tokens",
    r"context[_ ]length[_ ]exceeded",
]


def test_pi_classifies_the_refusal_as_a_context_overflow(ceiling):
    """The refusal must be recoverable by the client, or the session is stuck for good.

    Measured 2026-10-20: the old wording matched none of pi's overflow patterns, so pi never
    compacted and every later turn re-sent the same oversized history and was refused again.
    A pattern that matches makes pi compact once and retry with a smaller request.
    """
    import re

    verdict = _call(ceiling, _request(257_537))
    assert any(re.search(p, verdict, re.I) for p in _PI_OVERFLOW_PATTERNS), (
        "no pi overflow pattern matches the refusal, so pi will not compact and retry:\n"
        + verdict
    )
