"""m4, the Budget Orchestrator, in the LiteLLM gateway: a conversation's spend is recorded and
never enforced.

The orchestrator was counted in every "8 mechanisms" figure but only n10_validator ran it.
In the gateway it charges each conversation what the vendor billed and writes where that
conversation stands on the outcome row. What must not happen is the thing the orchestrator
does elsewhere: block a call. A conversation far over budget still gets its request through
untouched.
"""

from __future__ import annotations

import asyncio
import importlib.machinery
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _gw(monkeypatch, tmp_path, budget):
    monkeypatch.setenv("ESTATE_EFFICIENCY_LEDGER", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setenv("ESTATE_EPOCH_DIR", str(tmp_path / "epochs"))
    # control arm: the chain stays out of it, so the case is about m4 alone
    monkeypatch.setenv("ESTATE_HOLDOUT_PCT", "100")
    monkeypatch.setenv("ESTATE_CONV_TOKEN_BUDGET", str(budget))
    name = "gw_budget_under_test"
    loader = importlib.machinery.SourceFileLoader(
        name, os.path.join(ROOT, "platform", "llm", "efficiency_gateway.py")
    )
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    sys.modules[name] = mod
    loader.exec_module(mod)
    return mod.EstateEfficiencyGateway()


def _turn(gw, i):
    data = {
        "model": "claude-sonnet-5",
        "litellm_call_id": f"call-{i}",
        "metadata": {"user_id": json.dumps({"session_id": "s-budget"})},
        "messages": [{"role": "user", "content": "go"}],
    }
    sent = json.dumps(data, sort_keys=True)
    out = asyncio.run(gw.async_pre_call_hook(None, None, data, "anthropic_messages"))
    usage = {"prompt_tokens": 1000, "completion_tokens": 100}
    gw._outcome({"litellm_call_id": f"call-{i}"}, {"usage": usage}, None, None)
    return sent, out


def _outcomes(tmp_path):
    rows = [json.loads(x) for x in open(tmp_path / "ledger.jsonl")]
    return [r for r in rows if r["kind"] == "outcome"]


def test_each_conversation_is_charged_what_was_billed(monkeypatch, tmp_path):
    gw = _gw(monkeypatch, tmp_path, 5000)
    _turn(gw, 1)
    _turn(gw, 2)
    m4 = [r["m4"] for r in _outcomes(tmp_path)]
    assert [m["charged"] for m in m4] == [1100, 1100]
    assert [m["remaining"] for m in m4] == [3900, 2800]
    assert not any(m["over"] for m in m4)


def test_over_budget_is_flagged_and_the_call_still_goes_through(monkeypatch, tmp_path):
    gw = _gw(monkeypatch, tmp_path, 1500)
    _turn(gw, 1)
    sent, out = _turn(gw, 2)
    last = _outcomes(tmp_path)[-1]["m4"]
    assert last["over"] and last["remaining"] == -700
    assert out is not None and json.dumps(out, sort_keys=True) == sent
