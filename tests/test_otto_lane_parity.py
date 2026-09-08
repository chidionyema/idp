"""The door and its rehearsal run the same router lanes, or the pull request is refused.

otto-golden exists to rehearse otto-gateway. A rehearsal on different lanes rehearses
nothing, and on 2026-09-08 it was worse than nothing: otto-golden's deployment carried
``judgment: deepseek`` and ``bulk: deepseek`` inline, and ``otto/router/config.py`` refuses a
configuration whose judgment and bulk lanes share one model family, so their error modes
cannot correlate. That pod could not have answered a message if one had arrived -- most of
why 72 hours of its log held one boot line and nothing else.

One ConfigMap read by both was the obvious fix and kustomize will not have it: each overlay
carries a ``namespace:`` transformer, so one document naming the other namespace is rewritten
back into an ID conflict, and a cross-directory ``resources:`` reference builds under Flux
(which runs with the load restrictor off) while ``kustomize build`` in CI refuses it. So there
are two files, and this is what keeps them one value.
"""

import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOOR = ROOT / "platform" / "otto-gateway" / "router-lanes.yaml"
REHEARSAL = ROOT / "platform" / "otto-golden" / "router-lanes.yaml"


def _lanes(path):
    maps = [
        d
        for d in yaml.safe_load_all(path.read_text())
        if d
        and d.get("kind") == "ConfigMap"
        and d["metadata"]["name"] == "otto-router-lanes"
    ]
    assert len(maps) == 1, (
        f"{path.name}: expected one otto-router-lanes ConfigMap, found {len(maps)}"
    )
    return maps[0]["data"]


def test_the_rehearsal_runs_the_doors_lanes():
    assert _lanes(DOOR) == _lanes(REHEARSAL)


def test_judgment_and_bulk_come_from_different_vendors():
    """The refusal in otto/router/config.py, graded before the pod has to log it."""
    lanes = _lanes(DOOR)
    assert (
        lanes["OTTO_ROUTER_LANE_JUDGMENT_MODEL"] != lanes["OTTO_ROUTER_LANE_BULK_MODEL"]
    )
    assert (
        lanes["OTTO_ROUTER_LANE_JUDGMENT_MODEL"]
        != lanes["OTTO_ROUTER_LANE_VERIFY_MODEL"]
    )
