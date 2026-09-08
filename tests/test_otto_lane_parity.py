"""The door and its rehearsal apply the same router lanes, or the pull request is refused.

otto-golden exists to rehearse otto-gateway before the founder's traffic meets it. It was
rehearsing nothing. Its deployment carried the lanes inline as ``judgment: deepseek`` and
``bulk: deepseek``, and ``otto/router/config.py`` refuses a configuration whose judgment and
bulk lanes share one model family, so their error modes cannot correlate. That pod could not
have answered a message if one had arrived -- most of why 72 hours of its log held one boot
line and nothing else.

One ConfigMap read by both was the obvious fix and kustomize will not have it: each overlay
carries a ``namespace:`` transformer, so a document naming the other namespace is rewritten
back and the build fails with an ID conflict, and a cross-directory ``resources:`` reference
builds under Flux (load restrictor off) and is refused by ``kustomize build``. So there are
two files, and this is what keeps them one value.

It grades the built output rather than the two source files, because the source files are not
what runs: the namespace transformer, the overlay's resource list and the Deployment's
``envFrom`` all sit between the YAML and the pod, and each is a way for the rehearsal to end
up on lanes the door does not run while both files still read the same.
"""

import json
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOOR = ROOT / "platform" / "otto-gateway"
REHEARSAL = ROOT / "platform" / "otto-golden"

pytestmark = pytest.mark.skipif(
    shutil.which("kustomize") is None, reason="kustomize is not installed"
)


def _build(overlay):
    out = subprocess.run(
        ["kustomize", "build", str(overlay)], capture_output=True, text=True, check=True
    ).stdout
    docs = [
        json.loads(d)
        for d in subprocess.run(
            [
                "python3",
                "-c",
                "import sys,yaml,json;[print(json.dumps(d)) for d in yaml.safe_load_all(sys.stdin) if d]",
            ],
            input=out,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
    ]
    return docs


def _lanes(docs, namespace):
    maps = [
        d
        for d in docs
        if d["kind"] == "ConfigMap"
        and d["metadata"]["name"] == "otto-router-lanes"
        and d["metadata"].get("namespace") == namespace
    ]
    assert len(maps) == 1, (
        f"{namespace}: expected one applied otto-router-lanes, found {len(maps)}"
    )
    return maps[0]["data"]


def test_the_rehearsal_applies_the_doors_lanes():
    assert _lanes(_build(REHEARSAL), "otto-golden") == _lanes(
        _build(DOOR), "otto-gateway"
    )


def test_the_rehearsals_pod_reads_that_configmap_and_holds_no_lane_of_its_own():
    """envFrom, not env: an inline entry of the same name wins over the ConfigMap, which is
    exactly how the two doors drifted apart in the first place."""
    deployments = [d for d in _build(REHEARSAL) if d["kind"] == "Deployment"]
    assert deployments, "the rehearsal overlay builds no Deployment"
    for dep in deployments:
        for container in dep["spec"]["template"]["spec"]["containers"]:
            sources = [
                s.get("configMapRef", {}).get("name")
                for s in container.get("envFrom") or []
            ]
            assert "otto-router-lanes" in sources, (
                f"{container['name']} does not read the lanes"
            )
            inline = [
                e["name"]
                for e in container.get("env") or []
                if e["name"].startswith("OTTO_ROUTER_LANE_")
            ]
            assert not inline, (
                f"{container['name']} overrides the ConfigMap with {inline}"
            )


def test_judgment_and_bulk_come_from_different_vendors():
    """The refusal in otto/router/config.py, graded before the pod has to log it."""
    lanes = _lanes(_build(DOOR), "otto-gateway")
    assert (
        lanes["OTTO_ROUTER_LANE_JUDGMENT_MODEL"] != lanes["OTTO_ROUTER_LANE_BULK_MODEL"]
    )
    assert (
        lanes["OTTO_ROUTER_LANE_JUDGMENT_MODEL"]
        != lanes["OTTO_ROUTER_LANE_VERIFY_MODEL"]
    )
