"""Incident crew#284 (2026-08-26): the router was live at llm.mumchimp.com, but every consensus
alias (`minimax`, `deepseek`, `gemini`, sovereign/config.py model.consensus) answered 429: MiniMax
in cooldown, DeepSeek "Insufficient Balance", Gemini "prepayment credits are depleted". The
`openrouter` alias on the same router answered 200. One empty vendor account took the whole
consensus down. Rule (rung 4): each consensus alias falls back first to a deployment of the same
model routed through OpenRouter, so consensus survives any one direct account running dry.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONSENSUS = ("minimax", "deepseek", "gemini")


def _cfg(rel):
    return yaml.safe_load((ROOT / rel).read_text())


def test_incident_crew284_each_consensus_alias_falls_back_to_openrouter_first():
    for rel in ("platform/llm/config.yaml", "llm/config.yaml"):
        cfg = _cfg(rel)
        models = {m["model_name"]: m["litellm_params"] for m in cfg["model_list"]}
        fallbacks = {k: v for e in cfg["router_settings"]["fallbacks"] for k, v in e.items()}
        for alias in CONSENSUS:
            chain = fallbacks[alias]
            # crew#506 CP1 (2026-08-27): the first hop is a funded direct lane of a different
            # vendor; the OpenRouter deployment of the same model is still in the chain, so one
            # empty direct account never takes consensus down, and an empty OpenRouter account
            # (the 2026-08-27 outage) is in no chain until it is funded (crew#506 CP4).
            first = models[chain[0]]
            assert not first["model"].startswith("openrouter/"), (rel, alias, chain[0])
            assert first["api_key"] != f"os.environ/{alias.upper()}_API_KEY", (rel, alias, chain[0])
            # and at least one hop is a funded direct lane of another vendor, so consensus
            # survives this alias's account running dry (the crew#284 rule, kept)
            other = [h for h in chain if models[h]["api_key"] != models[alias]["api_key"] and not models[h]["model"].startswith("openrouter/")]
            assert other, (rel, alias, chain)
