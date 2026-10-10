"""The randomised holdout (bin/estate-token-proof's TRIAL): what makes a saving provable.

With a prompt cache, tokens cut are not dollars saved, so the only causal measurement is a
control arm: a fixed share of conversations the chain never touches. These cases pin what that
measurement depends on: a conversation keeps one arm for its whole life, the control arm reaches
the vendor byte-identical, both arms are recorded with the arm on the billed row, and the report
turns the two arms into a per-lane verdict with a confidence interval.
"""

from __future__ import annotations

import asyncio
import copy
import importlib.machinery
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_loader(
        name, importlib.machinery.SourceFileLoader(name, path)
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _gw(monkeypatch, tmp_path, pct):
    monkeypatch.setenv("ESTATE_EFFICIENCY_LEDGER", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setenv("ESTATE_EPOCH_DIR", str(tmp_path / "epochs"))
    monkeypatch.setenv("ESTATE_HOLDOUT_PCT", str(pct))
    mod = _load(
        "gw_holdout_under_test",
        os.path.join(ROOT, "platform", "llm", "efficiency_gateway.py"),
    )
    return mod, mod.EstateEfficiencyGateway()


def _req(session):
    noisy = "\n".join(["retrying connection"] * 40)
    return {
        "model": "claude-opus-5-5",
        "litellm_call_id": f"call-{session}",
        "metadata": {"user_id": json.dumps({"session_id": session})},
        "messages": [
            {"role": "user", "content": "go"},
            {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": "t1", "name": "Bash", "input": {}}
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "t1", "content": noisy}
                ],
            },
        ],
    }


def _rows(tmp_path):
    # the exact count (#5683) lands its own row after the call's; these cases read the call's
    rows = [json.loads(x) for x in (tmp_path / "ledger.jsonl").read_text().splitlines()]
    return [r for r in rows if r.get("kind") != "count"]


def test_a_conversation_keeps_one_arm_and_the_split_matches_the_share(
    monkeypatch, tmp_path
):
    mod, _ = _gw(monkeypatch, tmp_path, 25)
    arms = [mod._arm(f"s{i}") for i in range(4000)]
    assert all(mod._arm(f"s{i}") == arms[i] for i in range(4000))
    share = arms.count("control") / len(arms)
    assert 0.22 < share < 0.28


def test_the_holdout_is_off_unless_someone_reopens_it(monkeypatch, tmp_path):
    # 2026-10-10 (#5678): every conversation runs the chain; no control arm by default.
    monkeypatch.delenv("ESTATE_HOLDOUT_PCT", raising=False)
    monkeypatch.setenv("ESTATE_EFFICIENCY_LEDGER", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setenv("ESTATE_HOLDOUT_FORCE_FILE", str(tmp_path / "none.json"))
    mod = _load(
        "gw_holdout_default",
        os.path.join(ROOT, "platform", "llm", "efficiency_gateway.py"),
    )
    assert mod.HOLDOUT_PCT == 0
    assert {mod._arm(f"s{i}") for i in range(4000)} == {"treat"}


def test_the_control_arm_reaches_the_vendor_untouched_and_is_recorded(
    monkeypatch, tmp_path
):
    _, gw = _gw(monkeypatch, tmp_path, 100)
    data = _req("s-control")
    sent = copy.deepcopy(data)
    out = asyncio.run(gw.async_pre_call_hook(None, None, data, "anthropic_messages"))
    assert out["messages"] == sent["messages"]
    pre = _rows(tmp_path)[-1]
    assert (pre["arm"], pre["steps"], pre["bytes_before"]) == (
        "control",
        {},
        pre["bytes_after"],
    )


def test_the_treated_arm_is_shaped_and_the_billed_row_carries_arm_and_dollars(
    monkeypatch, tmp_path
):
    _, gw = _gw(monkeypatch, tmp_path, 0)
    data = _req("s-treat")
    asyncio.run(gw.async_pre_call_hook(None, None, data, "anthropic_messages"))
    usage = {
        "prompt_tokens": 100,
        "completion_tokens": 5,
        "cache_read_input_tokens": 90,
    }
    gw._outcome(
        {"litellm_call_id": "call-s-treat", "response_cost": 0.0123},
        {"usage": usage},
        None,
        None,
    )
    pre, out = _rows(tmp_path)[-2:]
    assert pre["arm"] == "treat" and pre["bytes_after"] < pre["bytes_before"]
    assert (out["arm"], out["cost_usd"], out["conv"]) == ("treat", 0.0123, pre["conv"])


def _call(i, arm, conv, usd, lane="claude-opus-5-5", cut=True):
    at = "2026-09-29T03:00:00Z"
    return [
        {
            "kind": "pre",
            "call_id": f"c{i}",
            "model": lane,
            "at": at,
            "bytes_before": 1200 if arm == "treat" and cut else 1000,
            "bytes_after": 1000,
            "arm": arm,
            "conv": conv,
            "steps": {},
        },
        {
            "kind": "outcome",
            "call_id": f"c{i}",
            "ok": True,
            "arm": arm,
            "conv": conv,
            "at": at,
            "cost_usd": usd,
            "usage": {"prompt_tokens": 1000, "cache_read": 900, "output_tokens": 10},
        },
    ]


def test_the_report_calls_a_real_saving_and_refuses_a_noise_one(monkeypatch, tmp_path):
    proof = _load(
        "token_proof_under_test", os.path.join(ROOT, "bin", "estate-token-proof")
    )
    rows, i = [], 0
    for c in range(30):  # treated conversations cost 0.08-0.09/call, control 0.10-0.11
        for arm, base in (("treat", 0.08), ("control", 0.10)):
            for _ in range(5):
                rows += _call(i, arm, f"{arm}{c}", base + (c % 10) / 1000)
                i += 1
    t = proof.trial(proof.pair(rows), {})
    lane = t["lanes"]["claude-opus-5-5"]
    assert lane["verdict"] == "saves" and lane["ci95"][1] < 0
    assert abs(lane["pct_change_usd_per_call"] - (-0.0845 / 0.1045 + 1) * -100) < 0.5

    noise = []
    for c in range(3):
        for arm in ("treat", "control"):
            noise += _call(
                1000 + c * 2 + (arm == "control"), arm, f"n{arm}{c}", 0.05 + c / 100
            )
    assert (
        proof.trial(proof.pair(noise), {})["lanes"]["claude-opus-5-5"]["verdict"]
        != "saves"
    )


def test_a_lane_the_chain_never_touched_is_not_blamed_for_its_callers():
    # groq, 2026-10: one caller's 8192-token loops landed in treat; the chain had cut nothing
    proof = _load(
        "token_proof_under_test", os.path.join(ROOT, "bin", "estate-token-proof")
    )
    rows = []
    for c in range(10):
        for arm, base in (("treat", 0.01), ("control", 0.0001)):
            rows += _call(
                c * 2 + (arm == "control"), arm, f"{arm}{c}", base, "groq", False
            )
    lane = proof.trial(proof.pair(rows), {})["lanes"]["groq"]
    assert (
        lane["verdict"] == "chain inert (nothing cut)" and lane["treat_bytes_cut"] == 0
    )


def test_a_subscription_lane_billed_zero_is_priced_from_its_usage():
    proof = _load(
        "token_proof_under_test", os.path.join(ROOT, "bin", "estate-token-proof")
    )
    price = {
        "claude-opus-5-5": {
            "input_cost_per_token": 4e-6,
            "cache_read_input_token_cost": 2e-7,
            "output_cost_per_token": 2e-5,
        }
    }
    (c,) = proof.pair(_call(0, "treat", "t0", 0.0))
    c["out"]["usage"]["uncached_input"] = 100
    assert abs(proof.cost(c, price) - (100 * 4e-6 + 900 * 2e-7 + 10 * 2e-5)) < 1e-12
    (g,) = proof.pair(_call(1, "treat", "t1", 0.0, "groq"))
    assert proof.cost(g, price) == 0.0  # a free lane's $0 is its true price
