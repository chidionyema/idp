"""The router's two image lanes (founder 2026-08-30).

His words: "we test with MiniMax see what the image quality is like, then we use Gemini for the
ones that will ship to production". Before this the router had no image lane at all, so a caller
that wanted a picture had two choices, both wrong: hold a vendor key itself, or not have images.

Rung 2, property over the config the cluster runs. What each test pins is the thing that would
quietly stop being true: that the shipping lane is named by capability, that the MiniMax door
demands a router key, and that neither vendor key is written down anywhere but the mounted secret.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "platform" / "llm" / "config.yaml").read_text())
MINIMAX_IMAGE_PATH = "/minimax/image"


def _models() -> dict[str, dict]:
    return {m["model_name"]: m["litellm_params"] for m in CFG["model_list"]}


def _minimax_route() -> dict:
    routes = CFG["general_settings"]["pass_through_endpoints"]
    return next(r for r in routes if r["path"] == MINIMAX_IMAGE_PATH)


def test_the_shipping_lane_is_named_image_and_served_by_gemini() -> None:
    """Callers ask for a capability. "image" is the production lane, and it is Gemini's."""
    image = _models()["image"]
    assert image["model"].startswith("gemini/"), image["model"]
    assert "image" in image["model"].rsplit("/", 1)[1], (
        "the id must be one of Google's image models"
    )
    assert image["api_key"] == "os.environ/GEMINI_API_KEY"


def test_the_minimax_lane_forwards_the_vendor_shape() -> None:
    """LiteLLM has no MiniMax image provider and OpenRouter does not resell it, so the vendor's
    own endpoint is the only door. It is forwarded, never re-shaped."""
    route = _minimax_route()
    assert route["target"] == "https://api.minimax.io/v1/image_generation"
    assert route["methods"] == ["POST"], (
        "a GET on an image endpoint is a misconfiguration, not a read"
    )


def test_the_minimax_door_refuses_a_caller_with_no_router_key() -> None:
    """The whole point of routing it. Without auth this path forwards anything that reaches
    llm.<zone> and spends the MiniMax account for a stranger."""
    assert _minimax_route()["auth"] is True


def test_no_vendor_key_is_written_down_in_the_config() -> None:
    """LAW 34 and LAW 21 together: every lane, model row or pass-through, reads its key from the
    mounted secret. A literal here would be a key in git."""
    raw = (ROOT / "platform" / "llm" / "config.yaml").read_text()
    assert "os.environ/MINIMAX_API_KEY" in _minimax_route()["headers"]["Authorization"]
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue  # prose about a key is not a key
        if stripped.startswith(("api_key:", "Authorization:")):
            assert "os.environ/" in stripped, f"a key is written out at: {stripped}"


def test_an_image_lane_never_falls_back_to_a_text_model() -> None:
    """A fallback chain that lands a picture request on a chat model returns prose to a caller
    waiting for bytes: worse than a clean failure, because it looks like an answer. Every hop
    out of an image lane must itself be an image lane."""
    models = _models()
    image_lanes = {n for n, p in models.items() if "image" in p["model"]}
    assert "image" in image_lanes and "image-or" in image_lanes
    for entry in CFG["router_settings"]["fallbacks"]:
        for src, targets in entry.items():
            if src not in image_lanes:
                assert not (set(targets) & image_lanes), (
                    f"{src} is a text lane and must not fall back into an image lane"
                )
                continue
            for target in targets:
                assert target in image_lanes, (
                    f"{src} falls back to the text lane {target}"
                )


def test_the_shipping_lane_survives_one_empty_account() -> None:
    """Measured 2026-08-30: Google's prepay was depleted AND OpenRouter was over its credit, so
    a single-route image lane is a capability that leaves whenever one account runs dry, the way
    `embed` did. Two ways to buy the same model, so funding either one is enough."""
    models = _models()
    assert models["image-or"]["model"].startswith("openrouter/")
    assert models["image-or"]["api_key"] == "os.environ/OPENROUTER_API_KEY"
    # Same underlying model, bought through two accounts -- not two different pictures.
    assert (
        models["image"]["model"].rsplit("/", 1)[1]
        == models["image-or"]["model"].rsplit("/", 1)[1]
    )
    chain = next(
        e["image"] for e in CFG["router_settings"]["fallbacks"] if "image" in e
    )
    assert "image-or" in chain
