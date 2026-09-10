"""Every hop of the embedding chain writes vectors of the width the column was created at.

Founder, 2026-09-10: "check ottos conversation history something not right, and I'm tired of
the shit user experience."

Two defects were behind that, and this test grades the second one -- the one nobody had hit
yet. The chain the router serves for `embed` was, that morning:

    embed          gemini/gemini-embedding-001              dimensions: 1536
    embed-fallback openrouter/openai/text-embedding-3-small dimensions: 1536
    embed-cohere   cohere/embed-english-v3.0                (no dimensions declared)

The v3 Cohere models emit 1024 floats and take no width parameter. `otto_facts.embedding` is
created at 1536. So on the first day both lanes above refused together, the third hop would
have written a vector the store cannot compare against anything it already holds -- and it
would have reported success while doing it, exactly like the defect the founder actually
found. A wrong-width hop is not a degraded answer, it is a silent corruption with a delay
fuse on it.

The failure this class belongs to is why the test exists rather than a comment: a fallback
hop is by definition the one nobody exercises, so it can be wrong for months and no probe,
no gate and no user will say so. This one grades it from the rendered router config and the
gateway's own environment, so the two cannot drift apart.
"""

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "platform" / "llm" / "config.yaml"
GATEWAY = ROOT / "platform" / "otto-gateway" / "deployment.yaml"


def _router():
    return yaml.safe_load(ROUTER.read_text())


def _gateway_env():
    """The env of the container that holds Otto's memory, as a flat name -> value map."""
    env = {}
    for doc in yaml.safe_load_all(GATEWAY.read_text()):
        if not isinstance(doc, dict) or doc.get("kind") != "Deployment":
            continue
        for c in doc["spec"]["template"]["spec"].get("containers", []):
            for e in c.get("env", []):
                if "value" in e:
                    env[e["name"]] = e["value"]
    return env


def _chain(cfg, group):
    """The model groups an embedding call can land on, in the order the router tries them."""
    hops = [group]
    for entry in (cfg.get("router_settings") or {}).get("fallbacks") or []:
        for name, rest in entry.items():
            if name == group:
                hops.extend(rest)
    return hops


def _lanes(cfg, group):
    return [m for m in cfg["model_list"] if m.get("model_name") == group]


def test_the_gateway_asks_for_a_model_group_the_router_serves():
    env = _gateway_env()
    group = env["OTTO_MEMORY_EMBEDDING_MODEL"]
    assert _lanes(_router(), group), (
        f"otto-gateway embeds through the model group {group!r} and the estate router "
        f"declares no lane by that name, so every fact is stored with no vector"
    )


def test_every_hop_of_the_embed_chain_declares_the_column_width():
    cfg, env = _router(), _gateway_env()
    width = int(env["OTTO_MEMORY_EMBEDDING_DIM"])
    group = env["OTTO_MEMORY_EMBEDDING_MODEL"]

    wrong = []
    for hop in _chain(cfg, group):
        lanes = _lanes(cfg, hop)
        assert lanes, f"the {group!r} chain names {hop!r} and no lane serves it"
        for lane in lanes:
            declared = lane["litellm_params"].get("dimensions")
            if declared != width:
                wrong.append((hop, lane["litellm_params"].get("model"), declared))

    assert not wrong, (
        f"otto_facts.embedding is {width} wide; these hops of the {group!r} chain would write "
        f"another width, or leave it to the model's default, and the store would accept the "
        f"row and never match it again: {wrong}"
    )


def test_the_embedding_write_outlives_a_walk_down_the_whole_chain():
    """A client that gives up before the chain finishes has no fallback, only the illusion.

    This is the first of the two defects: the bound was 1.5 seconds, the walk past one
    refusing hop was about six, so otto stored every fact with no embedding rather than
    waiting for the lane that answers. The floor is one second of budget per hop plus one --
    deliberately loose, because the point is to catch a bound set below the chain's own
    length, not to pin a latency.
    """
    cfg, env = _router(), _gateway_env()
    group = env["OTTO_MEMORY_EMBEDDING_MODEL"]
    bound = float(env["OTTO_MEMORY_EMBEDDING_TIMEOUT_S"])
    hops = len(_chain(cfg, group))
    assert bound >= hops + 1, (
        f"the {group!r} chain is {hops} hops and otto-gateway gives up after {bound}s, so the "
        f"hops past the first can never answer: the fact is stored with no vector instead"
    )


@pytest.mark.parametrize("hop_width", [1024, 3072])
def test_the_grader_refuses_a_chain_whose_hops_disagree(hop_width):
    """The check above, run against a chain built to be wrong, so a pass means something."""
    cfg = {
        "model_list": [
            {
                "model_name": "embed",
                "litellm_params": {"model": "a", "dimensions": 1536},
            },
            {
                "model_name": "embed-x",
                "litellm_params": {"model": "b", "dimensions": hop_width},
            },
        ],
        "router_settings": {"fallbacks": [{"embed": ["embed-x"]}]},
    }
    bad = [
        h
        for h in _chain(cfg, "embed")
        for lane in _lanes(cfg, h)
        if lane["litellm_params"].get("dimensions") != 1536
    ]
    assert bad == ["embed-x"]
