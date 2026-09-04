"""crew#659 CP3: the research worker reaches a frontier model only, through the router.

Founder, 2026-08-30 (Science Department Blueprint, verbatim): "It must hit a frontier model through
your router key - do not use local models here." The edge is on the key, not in an env var: the
science key is minted by vault-seed with the frontier and gemini lanes plus the embedding lane the
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

#: The frontier lanes by their neutral names. They were `claude`/`claude-fast` until
#: 2026-09-04, when the founder ruled the estate will never hold an Anthropic API key; a key
#: names a lane, and the lane names whichever vendor the estate pays (LAW 34).
FRONTIER = {"default", "fast", "gemini", "gemini-or"}
#: Paid vendor lanes that answered a 4096-token call with fallbacks off on 2026-08-30 06:2xZ while
#: every frontier account refused on credit. Founder, 2026-08-30 07:0xZ: "why is minimax not there"
#: ... "we have work to do". A paid lane is on the key so the worker runs while the frontier
#: accounts are empty; a local model is still never on it.
PAID = {"minimax", "minimax_m27"}
ALLOWED = FRONTIER | PAID


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


def test_the_science_key_is_frontier_and_paid_lanes_plus_embed_and_nothing_else():
    lanes = _science_lanes()
    assert "embed" in lanes
    assert lanes - {"embed"} <= ALLOWED, (
        f"a lane that is neither frontier nor a paid vendor is on the science key: {lanes - ALLOWED - {'embed'}}"
    )
    assert lanes & FRONTIER, "the worker has no frontier lane to run on"
    assert PAID <= lanes, (
        "the worker has no funded lane while the frontier accounts are empty"
    )
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
