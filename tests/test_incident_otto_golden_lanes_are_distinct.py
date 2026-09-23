"""Otto answered nothing because two of its lanes named the same model.

On 2026-09-04 the staging bot took every message and produced no reply. The
pod's own log named the reason once per message::

    webhook.pipeline_error ... policy defect: judgment and bulk lanes share
    one model family ('minimax', derived from the configured models); the
    spec requires distinct families so errors do not correlate

The router is right to refuse: a judge that fails the same way as the thing
it judges is not a judge. What was wrong was the deployment, which overrode
the judgment lane onto the bulk lane's shipped default and so asked for a
configuration the router had always promised to reject.

The refusal happens inside the pod at request time, where nobody reads it
until the founder says the bot is dead. This test moves the same judgement
to the manifest, where it is read before the manifest is merged.
"""

from __future__ import annotations

import pathlib

import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
DEPLOYMENT = REPO / "platform" / "otto-golden" / "deployment.yaml"

LANE_PREFIX = "OTTO_ROUTER_LANE_"
LANE_SUFFIX = "_MODEL"


def _lane_models() -> dict[str, str]:
    """Every ``OTTO_ROUTER_LANE_<NAME>_MODEL`` the pod is given, by lane."""
    docs = [d for d in yaml.safe_load_all(DEPLOYMENT.read_text()) if d]
    deployments = [d for d in docs if d.get("kind") == "Deployment"]
    assert len(deployments) == 1, f"expected one Deployment, found {len(deployments)}"
    container = deployments[0]["spec"]["template"]["spec"]["containers"][0]
    lanes = {}
    for entry in container.get("env", []):
        name = entry.get("name", "")
        if name.startswith(LANE_PREFIX) and name.endswith(LANE_SUFFIX):
            lane = name[len(LANE_PREFIX) : -len(LANE_SUFFIX)].lower()
            lanes[lane] = entry.get("value")
    return lanes


def test_the_deployment_pins_a_judgment_lane_model() -> None:
    assert "judgment" in _lane_models(), (
        "the judgment lane is the default lane; if this manifest stops naming "
        "it, delete this test with the override rather than leaving it green"
    )


def test_no_two_lanes_name_the_same_model() -> None:
    lanes = _lane_models()
    duplicated = {
        model
        for model in lanes.values()
        if model is not None and list(lanes.values()).count(model) > 1
    }
    assert not duplicated, (
        f"lanes {lanes} name the same model {sorted(duplicated)} more than "
        "once; otto/router/config.py refuses that configuration at request "
        "time and the pod answers nothing"
    )


def test_overriding_one_lane_onto_a_shipped_default_moves_the_other() -> None:
    """The specific shape of the 2026-09-04 outage, pinned.

    The bulk lane ships as ``minimax``. Pointing judgment at minimax without
    moving bulk is the exact configuration the router refused.
    """
    lanes = _lane_models()
    if lanes.get("judgment") == "minimax":
        assert lanes.get("bulk") not in (None, "minimax"), (
            "judgment is pinned to minimax, which is also the bulk lane's "
            "shipped default; this manifest must move the bulk lane too"
        )
