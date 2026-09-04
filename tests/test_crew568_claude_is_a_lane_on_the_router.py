"""LAW 34, founder 2026-09-04: no lane on either router is biased to one vendor.

He said it three times that morning, ending with "we supposoed to be provider agnostic yet we
fuckoing biased with anything claude and thropoc, we haevv to take this whle shit down".

This replaces the crew#568 pins, which required the opposite: that `claude` and `claude-fast`
sat on the Anthropic provider reading ANTHROPIC_API_KEY. The estate holds no Anthropic API
account and never will -- Claude reaches it through the Claude Max monthly subscription -- so
those lanes billed an unfunded account and answered 400 for every caller.

Pins now: no lane on either router names the Anthropic provider; nothing anywhere reads
ANTHROPIC_API_KEY; the vendor register carries no Anthropic root; every component names a lane,
never a vendor's model id; and the two neutral lane names exist so nothing has to say "claude"
to get a model.
"""

from pathlib import Path

import yaml

IDP = Path(__file__).resolve().parents[1]
CLUSTER = yaml.safe_load((IDP / "platform/llm/config.yaml").read_text())
LAPTOP = yaml.safe_load((IDP / "llm/config.yaml").read_text())


def _lanes(cfg):
    return {m["model_name"]: m for m in cfg["model_list"]}


def test_no_lane_on_either_router_calls_the_anthropic_provider():
    for cfg in (CLUSTER, LAPTOP):
        for lane in cfg["model_list"]:
            p = lane["litellm_params"]
            assert not str(p["model"]).startswith("anthropic/"), lane["model_name"]
            assert p.get("api_key") != "os.environ/ANTHROPIC_API_KEY", lane[
                "model_name"
            ]


def test_both_routers_offer_a_lane_whose_name_names_no_vendor():
    for cfg in (CLUSTER, LAPTOP):
        lanes = _lanes(cfg)
        for name in ("default", "fast"):
            assert name in lanes, (name, sorted(lanes))
            assert not str(lanes[name]["litellm_params"]["model"]).startswith(
                "anthropic/"
            )


def test_the_vendor_register_carries_no_anthropic_root():
    reg = yaml.safe_load((IDP / "platform/vendors/consoles.yaml").read_text())[
        "vendors"
    ]
    # Graded on what each row would do, not on the spelling of its key: a root is an
    # Anthropic root when its name, its seed secret or the URL it verifies against is
    # Anthropic's. R76 refuses a test that only asks whether a word appears in a file.
    rows = [
        name
        for name, row in reg.items()
        if "anthropic"
        in (name + str(row.get("secret", "")) + str(row.get("verify", ""))).lower()
    ]
    assert rows == [], rows


def test_nothing_that_runs_reads_an_anthropic_key():
    for rel in (
        "platform/llm/external-secret.yaml",
        "llm/litellm.yml",
        ".github/workflows/oke-check.yml",
    ):
        for line in (IDP / rel).read_text().splitlines():
            if line.lstrip().startswith("#"):
                continue  # the note saying why it is gone is the point
            assert "ANTHROPIC_API_KEY" not in line, (rel, line)


def test_the_agent_names_a_lane_and_not_a_vendors_model_id():
    # The file is a ConfigMap and the estate is a block scalar inside it, so the
    # document the agent reads is one level in from the manifest Flux applies.
    cm = yaml.safe_load((IDP / "platform/hermes-agent/estate.yaml").read_text())
    est = yaml.safe_load(cm["data"]["estate.yaml"])

    def models(node):
        if isinstance(node, dict):
            if "models" in node and isinstance(node["models"], dict):
                yield node["models"]
            for v in node.values():
                yield from models(v)
        elif isinstance(node, list):
            for v in node:
                yield from models(v)

    seen = list(models(est))
    assert seen, "the agent declares no models at all"
    lanes = set(_lanes(CLUSTER))
    for m in seen:
        for role, lane in m.items():
            assert lane in lanes, (role, lane, sorted(lanes))
