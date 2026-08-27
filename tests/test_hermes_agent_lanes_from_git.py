"""crew#524 CP2: the Architect's lanes are switched on from git. The entrypoint (hermes-v2#40) copies
$HERMES_ESTATE_YAML over estate.yaml before bin/render, so the ConfigMap in this row is the estate
the cluster runs and the Mac's gitignored estate.yaml is retired with the Mac. Rules: the ConfigMap
carries a parseable estate with watch, work and evolution on; the gateway mounts it and points
HERMES_ESTATE_YAML at the mounted file; nothing secret sits in it (tokens come through
hermes-agent-env); the spend cap the lanes run under is stated.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "platform" / "hermes-agent"


def _estate():
    cm = [d for d in yaml.safe_load_all((DIR / "estate.yaml").read_text()) if d][0]
    assert cm["kind"] == "ConfigMap" and cm["metadata"]["name"] == "hermes-agent-estate"
    return yaml.safe_load(cm["data"]["estate.yaml"]), cm["data"]["estate.yaml"]


def test_the_three_lanes_are_on_from_git_under_a_stated_cap():
    e, _ = _estate()
    assert e["features"]["watch"] is True and e["features"]["work"] is True and e["features"]["evolution"] is True
    assert e["limits"]["max_cost_usd_per_task"] <= 5 and e["limits"]["budget_hard_stop"] is True
    assert e["dispatch"]["board"] and e["github"]["owner"] and e["github"]["repo"]


def test_nothing_secret_sits_in_the_estate():
    _, raw = _estate()
    for line in raw.splitlines():
        assert not re.search(r"(token|secret|password|api_key)\s*:\s*\S", line, re.I), line
    assert not re.search(r"\b(ghp_|xox[bp]-|sk-)[A-Za-z0-9]", raw)


def test_the_gateway_mounts_it_and_points_the_entrypoint_at_it():
    dep = [d for d in yaml.safe_load_all((DIR / "gateway.yaml").read_text()) if d and d["kind"] == "Deployment"][0]
    spec = dep["spec"]["template"]["spec"]
    (c,) = spec["containers"]
    env = {e["name"]: e.get("value") for e in c["env"]}
    mounts = {m["name"]: m for m in c["volumeMounts"]}
    vols = {v["name"]: v for v in spec["volumes"]}
    assert vols["estate"]["configMap"]["name"] == "hermes-agent-estate"
    assert mounts["estate"]["readOnly"] is True
    assert env["HERMES_ESTATE_YAML"].startswith(mounts["estate"]["mountPath"] + "/")
    assert env["HERMES_ESTATE_YAML"].endswith("/estate.yaml")
    assert "estate.yaml" in (DIR / "kustomization.yaml").read_text()
