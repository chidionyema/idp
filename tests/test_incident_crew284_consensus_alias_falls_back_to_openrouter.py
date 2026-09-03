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
            first = fallbacks[alias][0]
            params = models[first]
            assert params["model"].startswith("openrouter/"), (rel, alias, first)
            assert params["api_key"] == "os.environ/OPENROUTER_API_KEY", (rel, alias, first)
            # the same vendor's model, not a substitute: consensus stays three different models
            vendor = alias if alias != "gemini" else "google"
            assert f"/{vendor}/" in params["model"], (rel, alias, params["model"])
