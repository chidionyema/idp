"""crew#568 phase 1 (ADR 0011): Claude is a lane on the one router, not a key on the Mac.

Pins: both routers carry `claude` and `claude-fast` on the Anthropic provider reading
ANTHROPIC_API_KEY; the key reaches litellm-upstream by the vendor bootstrapper (R52), the
secret-name doc line the external-secret test greps names it; both lanes sit in a fallback chain
that ends in the cheap model; the ADR and the scored matrix entry exist and agree.
"""

import re
from pathlib import Path

import yaml

IDP = Path(__file__).resolve().parents[1]
CLUSTER = yaml.safe_load((IDP / "platform/llm/config.yaml").read_text())
LAPTOP = yaml.safe_load((IDP / "llm/config.yaml").read_text())
LANES = {
    "claude": "anthropic/claude-sonnet-5",
    "claude-fast": "anthropic/claude-haiku-4-5-20251001",
}


def _lanes(cfg):
    return {m["model_name"]: m for m in cfg["model_list"]}


def test_both_routers_carry_the_two_claude_lanes_on_the_anthropic_provider():
    for cfg in (CLUSTER, LAPTOP):
        lanes = _lanes(cfg)
        for name, model in LANES.items():
            p = lanes[name]["litellm_params"]
            assert p["model"] == model, (name, p)
            assert p["api_key"] == "os.environ/ANTHROPIC_API_KEY"
            assert lanes[name]["model_info"]["max_input_tokens"] == 200000


def test_the_key_is_born_by_the_vendor_bootstrapper_into_litellm_upstream():
    reg = yaml.safe_load((IDP / "platform/vendors/consoles.yaml").read_text())[
        "vendors"
    ]["anthropic"]
    assert reg["secret"] == "SEED_ANTHROPIC_API_KEY"  # noqa: S105 a secret NAME, never a value (R49)
    assert {"entry": "litellm-upstream", "field": "ANTHROPIC_API_KEY"} in reg["targets"]
    doc = (IDP / "platform/llm/external-secret.yaml").read_text()
    assert "ANTHROPIC_API_KEY=ANTHROPIC_API_KEY" in doc


def test_every_claude_chain_ends_in_the_cheap_model():
    for cfg in (CLUSTER, LAPTOP):
        chains = {
            k: v for d in cfg["router_settings"]["fallbacks"] for k, v in d.items()
        }
        assert chains["claude"] == ["minimax", "deepseek"]
        assert chains["claude-fast"] == ["claude", "deepseek"]


def test_the_decision_is_written_and_scored():
    adr = (
        IDP
        / "docs/decisions/0011-claude-is-a-lane-on-the-router-not-a-key-on-the-mac.md"
    )
    assert re.search(r"^Matrix: claude-on-the-router", adr.read_text(), re.M)
    m = yaml.safe_load((IDP / "docs/decisions/decision-matrix.yaml").read_text())
    d = next(x for x in m["decisions"] if x["slug"] == "claude-on-the-router")
    assert d["decision"] == "router-lane-direct"
    assert set(d["candidates"]) == {
        "router-lane-direct",
        "claude-code-subscription",
        "openrouter-lane",
    }
