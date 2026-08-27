"""Incident crew#506 CP1 / crew#496 (2026-08-27): a 500k-token Telegram session was sent to the
`minimax` lane (window 204,800), failed, and walked the fallback chain through OpenRouter (402,
no credit) and Gemini (429, prepaid empty) before dying; Telegram was down for the founder until
the session was reset by hand. Rule (rung 4): the direct MiniMax lane declares its window on the
router, so an oversized turn is refused at the gateway before any fallback is tried, and the
first fallback hop of every consensus alias is a funded direct lane, never an aggregator.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _cfg(rel):
    return yaml.safe_load((ROOT / rel).read_text())


def test_incident_crew506_direct_minimax_lane_declares_its_window():
    for rel in ("platform/llm/config.yaml", "llm/config.yaml"):
        cfg = _cfg(rel)
        lane = next(m for m in cfg["model_list"] if m["model_name"] == "minimax")
        assert lane.get("model_info", {}).get("max_input_tokens") == 204800, rel


def test_incident_crew506_first_fallback_hop_is_never_an_aggregator():
    for rel in ("platform/llm/config.yaml", "llm/config.yaml"):
        cfg = _cfg(rel)
        models = {m["model_name"]: m["litellm_params"]["model"] for m in cfg["model_list"]}
        for entry in cfg["router_settings"]["fallbacks"]:
            for src, chain in entry.items():
                assert not models[chain[0]].startswith("openrouter/"), (rel, src, chain)
