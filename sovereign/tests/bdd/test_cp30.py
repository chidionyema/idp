"""cp30 acceptance: Cross-model consensus under a policy invariant.

Owner: W6 (crew#219). Steps drive sovereign/consensus/decide.py for real:
the vote fan-out, the quorum tally, the conftest policy evaluation and the
receipt. The one fake is the LiteLLM proxy, a true external boundary,
replaced at the HTTP wire by an httpx.MockTransport so a model can answer,
answer late, or never answer.
"""
from __future__ import annotations

import asyncio
import importlib
import json
import re
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from sovereign import config as config_mod
from sovereign.consensus import config_keys as ck
decide_mod = importlib.import_module("sovereign.consensus.decide")  # the package exports a function named decide
from sovereign.consensus import models as models_mod
from sovereign.engine import receipts as receipts_mod

scenarios("features/sovereign-bus/cp30_consensus_and_policy.feature")

THREE_MODELS = ["alpha", "beta", "gamma"]
ALLOWED_CALL = 'git commit -am "checkpoint"'
FORBIDDEN_CALL = "git push --force origin main"
# The feature says "within 30 seconds"; that is consensus.timeout_s and the
# scenario asserts it. The wall-clock deadline the fan-out actually waits
# is scaled down so a model that never answers costs the suite well under
# a second rather than thirty.
SCALED_DEADLINE_S = 0.2


@dataclass
class FakeProxy:
    """What each model says when asked. A model absent from `answers`
    never answers -- its request parks until the fan-out cancels it."""

    answers: dict[str, str] = field(default_factory=dict)
    calls: list[str] = field(default_factory=list)

    async def handle(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        model = str(body["model"])
        self.calls.append(model)
        if model not in self.answers:
            await asyncio.Event().wait()  # never set: cancelled at the deadline
        return httpx.Response(
            200, json={"choices": [{"message": {"content": self.answers[model]}}]}
        )


@pytest.fixture
def proxy(estate_home, monkeypatch: pytest.MonkeyPatch) -> FakeProxy:
    """The LiteLLM proxy, faked at the wire. Skips, not fails, when the
    policy engine is absent: that is an environment gap and idp-ci names
    it, not a consensus defect."""
    if shutil.which(str(ck.get("consensus.policy_binary"))) is None:
        pytest.skip("conftest is not on PATH; bin/idp-ci and ci.yml install it")
    fake = FakeProxy()
    real_client = httpx.AsyncClient

    def client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = httpx.MockTransport(fake.handle)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(models_mod.httpx, "AsyncClient", client)
    monkeypatch.setenv("LITELLM_BASE_URL", "http://litellm.invalid")
    monkeypatch.setenv("SB_MODEL_CONSENSUS", ",".join(THREE_MODELS))
    importlib.reload(config_mod)
    return fake


def _decide(op: str, destructive: bool) -> dict[str, Any]:
    return asyncio.run(decide_mod.decide_async(op, destructive=destructive, deadline_s=SCALED_DEADLINE_S))


def _latest_receipt() -> dict[str, Any]:
    rows = [r for r in receipts_mod.read_all() if r.get("kind") == "model_consensus"]
    assert rows, "decide() wrote no model_consensus receipt"
    return rows[-1]


# --- Scenario 1: two of three agree and the call is allowed ------------------


@given("a destructive op proposal and three configured models")
def _destructive_with_three(proxy: FakeProxy, config, context: dict[str, Any]) -> None:
    assert list(config.SB_MODEL_CONSENSUS) == THREE_MODELS
    assert int(config.get("consensus.timeout_s").value) == 30
    context["op"] = "commit the working tree before the force push"
    context["destructive"] = True


@when("two models propose the same normalized tool call within 30 seconds")
def _two_agree(proxy: FakeProxy, context: dict[str, Any]) -> None:
    proxy.answers = {"alpha": ALLOWED_CALL, "beta": ALLOWED_CALL + "  ", "gamma": "git status"}
    context["result"] = _decide(context["op"], destructive=True)


@when("the call is in the allowlist")
def _call_allowed(context: dict[str, Any]) -> None:
    result = context["result"]
    assert result["quorum"]["agreed"] and result["quorum"]["count"] == 2, result["quorum"]
    assert result["policy"]["allowed"] is True, result["policy"]


@then("the op proceeds with a receipt naming the three votes")
def _proceeds(proxy: FakeProxy, context: dict[str, Any]) -> None:
    result = context["result"]
    assert result["ok"] is True and result["proposal"] == models_mod.normalize_tool_call(ALLOWED_CALL)
    receipt = _latest_receipt()
    assert receipt["status"] == "allowed"
    assert [v["model"] for v in receipt["votes"]] == THREE_MODELS
    assert sorted(proxy.calls) == THREE_MODELS


# --- Scenario 2: consensus outside policy is blocked -------------------------


@when("three models agree on a call not in the allowlist")
def _three_agree_forbidden(proxy: FakeProxy, context: dict[str, Any]) -> None:
    proxy.answers = {m: FORBIDDEN_CALL for m in THREE_MODELS}
    context["result"] = _decide("push the rewritten branch", destructive=True)
    assert context["result"]["quorum"]["count"] == 3


@then(parsers.parse('the op is blocked and the receipt says "{reason}"'))
def _blocked_by_policy(context: dict[str, Any], reason: str) -> None:
    result = context["result"]
    assert result["ok"] is False and result["reason"] == reason, result
    receipt = _latest_receipt()
    assert receipt["status"] == "blocked" and receipt["reason"] == reason
    assert receipt["policy_violations"], receipt


# --- Scenario 3: a late vote does not count ----------------------------------


@when("only one model answers within 30 seconds")
def _one_answers(proxy: FakeProxy, config, context: dict[str, Any]) -> None:
    assert int(config.get("consensus.timeout_s").value) == 30
    proxy.answers = {"alpha": ALLOWED_CALL}
    context["result"] = _decide("commit the working tree", destructive=True)
    context["calls_after"] = list(proxy.calls)


@then("the op fails hard and no retry happens without a founder signal")
def _fails_hard(proxy: FakeProxy, context: dict[str, Any]) -> None:
    result = context["result"]
    assert result["ok"] is False and result["reason"] in (decide_mod.REASON_STALE, decide_mod.REASON_QUORUM)
    assert result["proposal"] == "" and result["policy"] is None  # policy never rescues a failed quorum
    assert result["quorum"]["fresh"] == 1 and result["quorum"]["stale"] == 2
    # One request per model and nothing after the verdict: no retry.
    assert sorted(context["calls_after"]) == THREE_MODELS
    assert proxy.calls == context["calls_after"]
    assert _latest_receipt()["status"] == "blocked"


# --- Scenario 4: non-destructive ops use one cheap model ---------------------


@given("a non-destructive op")
def _non_destructive(proxy: FakeProxy, context: dict[str, Any]) -> None:
    cheap = str(ck.get("consensus.cheap_model"))
    proxy.answers = {cheap: "git status --short"}
    context["result"] = _decide("show me the working tree", destructive=False)


@then("exactly one model is called, the cheapest in the LiteLLM fallback chain")
def _one_cheap_model(proxy: FakeProxy, context: dict[str, Any]) -> None:
    cheap = str(ck.get("consensus.cheap_model"))
    assert proxy.calls == [cheap]
    assert context["result"]["ok"] is True
    # The cheapest: the last entry of every fallback chain in llm/config.yaml,
    # the local model that cannot run out of credit.
    litellm = (config_mod.POLICY.path.parent / "llm" / "config.yaml").read_text()
    chains = re.findall(r"^\s*-\s*\w+:\s*\[([^\]]+)\]", litellm, flags=re.MULTILINE)
    assert chains, "llm/config.yaml declares no fallback chains"
    for chain in chains:
        assert chain.split(",")[-1].strip() == cheap, chain
    assert config_mod.POLICY.routing["cheap"] == cheap


# crew#284 CP2: spec 4.2 says three models. Three copies of one alias is one
# model voting three times, which the old default was.
@given("the shipped configuration with no consensus override", target_fixture="voters")
def _shipped_voters(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    monkeypatch.delenv("SB_MODEL_CONSENSUS", raising=False)
    from sovereign.config import KEYS

    return list(KEYS["model.consensus"].default)


@then("the consensus list names three aliases and no alias appears twice")
def _three_distinct(voters: list[str]) -> None:
    assert len(voters) == 3, voters
    assert len(set(voters)) == 3, voters


@then("every alias is a model_name the LiteLLM proxy config serves")
def _served_by_proxy(voters: list[str]) -> None:
    root = Path(__file__).resolve().parents[3]
    text = (root / "llm" / "config.yaml").read_text()
    served = set(re.findall(r"^\s*- model_name:\s*(\S+)", text, re.M))
    missing = [v for v in voters if v not in served]
    assert not missing, f"not in llm/config.yaml model_list: {missing}"


# Incident 2026-08-26: `sb model-consensus` raised AttributeError before any
# vote, because `from sovereign.consensus import decide` bound the function,
# not the module. The command must reach decide() and print its verdict.
@then('"sb model-consensus --op <op> --destructive" exits 0 with the verdict')
def _cli_reaches_vote(context: dict[str, Any], capsys: pytest.CaptureFixture[str]) -> None:
    import argparse

    from sovereign import cli

    args = argparse.Namespace(op=context["op"], destructive=True, non_destructive=False, json=True)
    rc = cli.cmd_model_consensus(args)
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["ok"] is True, out
