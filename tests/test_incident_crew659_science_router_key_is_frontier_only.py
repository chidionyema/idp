"""crew#659 CP3: the research worker reaches a frontier model only, through the router.

Founder, 2026-08-30 (Science Department Blueprint, verbatim): "It must hit a frontier model through
your router key - do not use local models here." The edge is on the key, not in an env var: the
science key is minted by vault-seed with the claude and gemini lanes plus the embedding lane the
worker needs to rank sources, and nothing else. If someone adds a small lane to that key, or drops
the embed lane, the worker either drifts off the frontier or cannot run; both are this incident.
"""

from __future__ import annotations

import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "vault-seed.yml"
CONFIG = ROOT / "platform" / "llm" / "config.yaml"

FRONTIER = {"claude", "claude-fast", "gemini", "gemini-or"}


def _lanes() -> dict[str, dict]:
    cfg = yaml.safe_load(CONFIG.read_text())
    return {m["model_name"]: m for m in cfg["model_list"]}


def _seed_run() -> str:
    doc = yaml.safe_load(WORKFLOW.read_text())
    steps = doc["jobs"]["seed"]["steps"]
    return "\n".join(s.get("run", "") for s in steps)


def _science_lanes() -> set[str]:
    line = next(l for l in _seed_run().splitlines() if "idp-router-key science" in l)
    return set(line.split()[-1].split(","))


def test_the_router_has_an_embedding_lane_the_worker_can_rank_with():
    lanes = _lanes()
    assert "embed" in lanes, (
        "gpt-researcher needs an embedding model; the router is its only door"
    )
    assert lanes["embed"]["model_info"]["mode"] == "embedding"


def test_the_science_key_is_frontier_lanes_plus_embed_and_nothing_else():
    lanes = _science_lanes()
    assert "embed" in lanes
    assert lanes - {"embed"} <= FRONTIER, (
        f"a non-frontier lane is on the science key: {lanes - FRONTIER - {'embed'}}"
    )
    assert lanes & FRONTIER, "the worker has no frontier lane to run on"
    assert lanes <= set(_lanes()), (
        "the science key names a lane the router does not serve"
    )


def test_science_is_a_vault_seed_entry_and_lands_in_the_sops_vault():
    doc = yaml.safe_load(WORKFLOW.read_text())
    options = doc[True]["workflow_dispatch"]["inputs"]["entry"]["options"]
    assert "science" in options
    run = _seed_run()
    assert re.search(r'\[ "\$ENTRY" = all \] \|\| \[ "\$ENTRY" = science \]', run)
    assert 'secret-add" dev LITELLM_SCIENCE_KEY LITELLM_API_KEY' in run
    assert "add secrets/dev/LITELLM_SCIENCE_KEY.yaml" in run


def test_the_embed_lane_does_not_share_the_gemini_lane_account():
    """2026-08-30 05:3xZ: Google's prepaid credit ran out, `embed` answered 429 RESOURCE_EXHAUSTED
    and had no fallback group, so the worker could not rank a single page while `gemini-or` on
    OpenRouter still answered. Embeddings go through the account that answered; endpoint from
    https://openrouter.ai/docs/api-reference/embeddings (read 2026-08-30)."""
    lanes = _lanes()
    embed = lanes["embed"]["litellm_params"]
    assert embed["api_base"] == "https://openrouter.ai/api/v1"
    assert embed["api_key"] == "os.environ/OPENROUTER_API_KEY"
    assert embed["model"] == "openai/openai/text-embedding-3-small"
    assert embed["api_key"] != lanes["gemini"]["litellm_params"]["api_key"], (
        "one empty account must not take both the grader and the ranker down"
    )
