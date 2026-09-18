#!/usr/bin/env python3
"""Ablation + A/B harness for the efficiency mechanisms. Reproducible, seeded, in real tokens.

WHY. Until 2026-09-18 the only statements anyone could make about the eight mechanisms were
prose: "25% token reduction", "60-90% on bash commands", percentages from a roadmap that
marked every ticket TODO. A percentage nobody can reproduce is not a measurement. This runs
the actual code, on a fixed input, and reports token counts a reader can re-derive.

METHOD
  * one deterministic transcript fixture (seed 1337) -- the same bytes on every run
  * tiktoken cl100k_base for real token counts, never bytes/4
  * EXPERIMENT A (A/B)     : identical input, mechanisms ALL ON vs ALL OFF
  * EXPERIMENT B (ablation): identical input, each mechanism disabled alone
  * EXPERIMENT C (rates)   : the counterfactual the session ledger supports -- identical
                             tokens at each tier's own OBSERVED rate, no external price sheet

The ablation is the part that answers "what is effective". A/B tells you the chain as a
whole; turning one mechanism off at a time tells you which ones are load-bearing and which
are decorative, which aggregate counters cannot show.

USAGE
    python3 bin/estate-efficiency-experiment.py           # all three experiments
    python3 bin/estate-efficiency-experiment.py --json    # machine-readable

Requires tiktoken. In a PEP-668 environment:
    python3 -m venv /tmp/tkvenv && /tmp/tkvenv/bin/pip install tiktoken
    /tmp/tkvenv/bin/python bin/estate-efficiency-experiment.py
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.machinery
import importlib.util
import json
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATEWAY = ROOT / "platform" / "llm" / "efficiency_gateway.py"
SEED = 1337

MECHANISMS = [
    ("_cache_guardian", "[1] CacheGuardian"),
    ("_token_killer", "[2] TokenKiller"),
    ("_mcp_adapter", "[3] MCPAdapter"),
    ("_sol_pi", "[5] SoLPi"),
    ("_dynamic_pruning", "[6] Pruning"),
    ("_compaction_manager", "[7] Compaction"),
    ("_gisting", "[8] Gisting"),
]


def _load_gateway():
    spec = importlib.util.spec_from_loader(
        "gw_under_test",
        importlib.machinery.SourceFileLoader("gw_under_test", str(GATEWAY)),
        origin=str(GATEWAY),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gw_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def _fixture():
    """A deterministic agent transcript: many turns, duplicate lines, a repeated large
    observation, a verbose tool description. Seeded, so the bytes are identical each run.

    `random` here is the point of the experiment, not a security choice (ruff S311): the whole
    value of the A/B and the ablation is that a reader re-runs this file and gets the SAME token
    counts. A seed is what makes the measurement reproducible; `secrets` would make it
    unreproducible, which is the opposite of what a measurement needs.
    """
    # noqa: S311 -- random is the point of the experiment, not a security choice: a fixed
    # seed is what makes the token counts reproducible, and `secrets` would make the
    # measurement unreproducible, which is the opposite of what a measurement needs.
    random.seed(SEED)
    msgs = [{"role": "system", "content": "You are a coding agent. " + "x" * 4000}]
    for i in range(120):
        msgs.append(
            {
                "role": "user",
                "content": f"task step {i} " + "y" * random.randint(50, 300),  # noqa: S311,
            }
        )
        if i % 3 == 0:
            msgs.append(
                {
                    "role": "tool",
                    "tool_call_id": f"c{i}",
                    "content": "\n".join(
                        f"line-{j}-{random.randint(0, 999)}"  # noqa: S311
                        for j in range(200)
                    ),
                }
            )
    msgs.append({"role": "tool", "tool_call_id": "cbig", "content": "z" * 12000})
    msgs.append({"role": "tool", "tool_call_id": "cbig2", "content": "z" * 12000})
    tools = [{"function": {"name": "bigtool", "description": "d" * 3000}}]
    return msgs, tools


class _Key:
    """Minimal stand-in for user_api_key_dict; the mechanisms read nothing from it."""


def _count(enc, obj) -> int:
    return len(enc.encode(json.dumps(obj, separators=(",", ":"), default=str)))


def run_gateway(gw, disabled=()):
    for name in disabled:
        setattr(gw, name, lambda x: x)
    msgs, tools = _fixture()
    return asyncio.run(
        gw.async_pre_call_hook(
            _Key(),
            None,
            {"messages": msgs, "tools": tools, "model": "deepseek-v4-flash"},
            "acompletion",
        )
    )


def experiment_a(mod, enc) -> dict:
    """A/B: identical input, chain ON vs OFF."""
    on = run_gateway(mod.EstateEfficiencyGateway())
    off = run_gateway(mod.EstateEfficiencyGateway(), [n for n, _ in MECHANISMS])
    t_on = _count(enc, on["messages"]) + _count(enc, on.get("tools") or [])
    t_off = _count(enc, off["messages"]) + _count(enc, off.get("tools") or [])
    return {
        "tokens_control_all_off": t_off,
        "tokens_treatment_all_on": t_on,
        "tokens_saved": t_off - t_on,
        "reduction_pct": (1 - t_on / t_off) * 100 if t_off else 0.0,
        "messages_control": len(off["messages"]),
        "messages_treatment": len(on["messages"]),
    }


def experiment_b(mod, enc) -> dict:
    """Ablation: each mechanism off alone. Answers 'what is effective'."""
    full_on = run_gateway(mod.EstateEfficiencyGateway())
    baseline = _count(enc, full_on["messages"]) + _count(
        enc, full_on.get("tools") or []
    )
    rows = []
    for attr, label in MECHANISMS:
        out = run_gateway(mod.EstateEfficiencyGateway(), [attr])
        t = _count(enc, out["messages"]) + _count(enc, out.get("tools") or [])
        rows.append(
            {
                "mechanism": label,
                "tokens_with_it_off": t,
                "tokens_lost_by_removing_it": t - baseline,
                "verdict": "ESSENTIAL"
                if (t - baseline) > 1000
                else ("marginal" if (t - baseline) > 0 else "NO EFFECT"),
            }
        )
    rows.sort(key=lambda r: -r["tokens_lost_by_removing_it"])
    return {
        "baseline_all_on_tokens": baseline,
        "per_mechanism": rows,
        "no_effect": [
            r["mechanism"] for r in rows if r["tokens_lost_by_removing_it"] <= 0
        ],
    }


def experiment_c() -> dict:
    """Counterfactual from this session's own ledger: identical tokens, each tier's
    OBSERVED rate. No external price sheet enters the number."""
    import collections
    import glob

    by = collections.defaultdict(lambda: {"tok": 0, "cost": 0.0, "n": 0})
    for f in glob.glob(
        os.path.expanduser("~/.pi/agent/sessions/**/*.jsonl"), recursive=True
    ):
        for line in open(f, errors="ignore"):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            msg = d.get("message") or d
            u = msg.get("usage")
            if not u:
                continue
            name = msg.get("model") or d.get("model") or "?"
            tok = u.get("totalTokens") or 0
            cost = (u.get("cost") or {}).get("total") or 0
            if tok <= 0:
                continue
            by[name]["tok"] += tok
            by[name]["cost"] += cost
            by[name]["n"] += 1

    pro = by.get("deepseek-v4-pro")
    flash = by.get("deepseek-v4-flash")
    if not (pro and flash and pro["tok"] and flash["tok"]):
        return {"available": False, "reason": "pro/flash rows not both present"}

    rate_pro = pro["cost"] / pro["tok"]
    rate_flash = flash["cost"] / flash["tok"]
    return {
        "available": True,
        "flash_tokens": flash["tok"],
        "flash_calls": flash["n"],
        "actual_cost_flash_rate": flash["cost"],
        "counterfactual_cost_pro_rate": flash["tok"] * rate_pro,
        "ratio": rate_pro / rate_flash,
        "rate_pro_per_token": rate_pro,
        "rate_flash_per_token": rate_flash,
        "observed": {
            "pro": {"calls": pro["n"], "tokens": pro["tok"], "cost": pro["cost"]},
            "flash": {
                "calls": flash["n"],
                "tokens": flash["tok"],
                "cost": flash["cost"],
            },
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    try:
        import tiktoken
    except ImportError:
        print(
            "tiktoken is required for real token counts (not bytes/4).\n"
            "  python3 -m venv /tmp/tkvenv && /tmp/tkvenv/bin/pip install tiktoken\n"
            "  /tmp/tkvenv/bin/python bin/estate-efficiency-experiment.py",
            file=sys.stderr,
        )
        return 2
    enc = tiktoken.get_encoding("cl100k_base")
    mod = _load_gateway()

    A = experiment_a(mod, enc)
    B = experiment_b(mod, enc)
    C = experiment_c()

    if a.json:
        print(json.dumps({"A_ab": A, "B_ablation": B, "C_rates": C}, indent=2))
        return 0

    print("=" * 78)
    print("EXPERIMENT A — A/B. Identical seeded fixture. tiktoken cl100k_base.")
    print("=" * 78)
    print(
        f"  control  (chain OFF) : {A['tokens_control_all_off']:>9,} tokens  "
        f"{A['messages_control']:>5} messages"
    )
    print(
        f"  treatment(chain ON)  : {A['tokens_treatment_all_on']:>9,} tokens  "
        f"{A['messages_treatment']:>5} messages"
    )
    print(
        f"  saved                : {A['tokens_saved']:>9,} tokens  "
        f"{A['reduction_pct']:.2f}% reduction"
    )

    print()
    print("=" * 78)
    print("EXPERIMENT B — ABLATION. Each mechanism disabled alone.")
    print("=" * 78)
    print(f"  baseline (all on): {B['baseline_all_on_tokens']:,} tokens\n")
    print(f"  {'mechanism OFF':<20}{'tokens':>10}{'cost of removing':>20}  verdict")
    for r in B["per_mechanism"]:
        print(
            f"  {r['mechanism']:<20}{r['tokens_with_it_off']:>10,}"
            f"{r['tokens_lost_by_removing_it']:>+20,}  {r['verdict']}"
        )
    if B["no_effect"]:
        print(f"\n  no effect at all: {', '.join(B['no_effect'])}")

    print()
    print("=" * 78)
    print(
        "EXPERIMENT C — RATES. From this session's own ledger, no external price sheet."
    )
    print("=" * 78)
    if C.get("available"):
        print(f"  unit of work : the {C['flash_calls']} flash calls in this session")
        print(f"  tokens       : {C['flash_tokens']:,}")
        print(f"  actual cost  : ${C['actual_cost_flash_rate']:.6f}  (flash rate)")
        print(
            f"  at pro rate  : ${C['counterfactual_cost_pro_rate']:.6f}  (same tokens)"
        )
        print(f"  ratio        : {C['ratio']:.2f}x")
        print(
            f"  saved        : ${C['counterfactual_cost_pro_rate'] - C['actual_cost_flash_rate']:.6f}"
        )
    else:
        print(f"  unavailable: {C.get('reason')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
