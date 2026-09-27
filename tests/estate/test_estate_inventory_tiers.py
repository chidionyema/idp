"""estate-inventory tells declared, deployed and running apart, and never reads a failed probe as absent.

Runs the repo's platform/estate/libexec/estate-inventory.py against a throwaway git repo (what
main declares) and a stub kubectl (what the cluster reports), so nothing reaches a cluster.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2] / "platform/estate/libexec/estate-inventory.py"
)

ROW = """apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: {name}
  namespace: flux-system
spec:
  path: ./platform/{name}
  sourceRef: {{kind: GitRepository, name: flux-system}}
"""
HEAD = "main@sha1:aaaaaaaa"


def _ks(name, ready="True", applied=HEAD):
    return {
        "metadata": {"name": name},
        "spec": {"path": f"./platform/{name}", "sourceRef": {"name": "flux-system"}},
        "status": {
            "lastAppliedRevision": applied,
            "conditions": [{"type": "Ready", "status": ready}],
        },
    }


def _deploy(ns, name, labels, ready, want=1):
    return {
        "kind": "Deployment",
        "metadata": {"namespace": ns, "name": name, "labels": labels},
        "spec": {"replicas": want},
        "status": {"readyReplicas": ready},
    }


LIVE = {
    "kustomizations": [_ks("alpha"), _ks("delta", applied="main@sha1:old")],
    "helmreleases": [
        {
            "metadata": {
                "namespace": "a",
                "name": "alpha-chart",
                "labels": {"kustomize.toolkit.fluxcd.io/name": "alpha"},
            }
        }
    ],
    "deployments": [
        _deploy("a", "api", {"kustomize.toolkit.fluxcd.io/name": "alpha"}, 1),
        _deploy("a", "chart", {"helm.toolkit.fluxcd.io/name": "alpha-chart"}, 2, 2),
        _deploy("b", "frozen-one", {"kustomize.toolkit.fluxcd.io/name": "beta"}, 1),
    ],
    "gitrepository": {"status": {"artifact": {"revision": HEAD}}},
}

STUB = """#!/usr/bin/env python3
import json, os, sys
if os.environ.get("STUB_FAIL"):
    sys.stderr.write("Unable to connect to the server: i/o timeout\\n"); sys.exit(1)
live = json.load(open(os.environ["STUB_LIVE"]))
a = " ".join(sys.argv)
if "gitrepository" in a:
    print(json.dumps(live["gitrepository"]))
else:
    key = next(k for k in ("kustomizations", "helmreleases", "deployments") if k in a)
    print(json.dumps({"items": live[key]}))
"""


def _run(tmp_path: Path, fail: bool = False) -> dict:
    repo = tmp_path / "repo"
    for d in ("alpha", "beta", "gamma", "delta", "epsilon"):
        (repo / "platform" / d).mkdir(parents=True)
        (repo / "platform" / d / "kustomization.yaml").write_text("resources: []\n")
    (repo / "clusters/oke").mkdir(parents=True)
    for n in ("alpha", "gamma", "delta"):
        (repo / f"clusters/oke/{n}.yaml").write_text(ROW.format(name=n))
    g = ["git", "-C", str(repo)]
    subprocess.run([*g, "init", "-q"], check=True)
    subprocess.run([*g, "add", "."], check=True)
    subprocess.run(
        [*g, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"],
        check=True,
    )
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    (bin_ / "kubectl").write_text(STUB)
    (bin_ / "kubectl").chmod(0o755)
    (tmp_path / "live.json").write_text(json.dumps(LIVE))
    env = {
        **os.environ,
        "PATH": f"{bin_}:{os.environ['PATH']}",
        "IDP_REPO": str(repo),
        "IDP_REF": "HEAD",
        "STUB_LIVE": str(tmp_path / "live.json"),
    }
    if fail:
        env["STUB_FAIL"] = "1"
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "json"],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    out = json.loads(r.stdout)
    out["by"] = {c["component"]: c for c in out["components"]}
    return out


def test_each_component_lands_on_the_tier_it_actually_reached(tmp_path):
    by = _run(tmp_path)["by"]
    assert by["alpha"]["status"] == "operating"
    # the HelmRelease's workload counts toward the row that owns the HelmRelease
    assert by["alpha"]["running"] == "3/3"
    assert by["beta"]["status"] == "frozen"
    assert by["beta"]["orphan_owners"] == ["beta"]
    assert by["gamma"]["status"] == "declared-not-deployed"
    assert by["delta"]["status"] == "degraded"
    assert "STALE" in by["delta"]["deployed"][0]
    assert by["epsilon"]["status"] == "code-only"


def test_a_cluster_that_cannot_be_read_is_unknown_never_absent(tmp_path):
    out = _run(tmp_path, fail=True)
    assert out["live_read"] is False
    assert {c["status"] for c in out["components"]} == {"UNKNOWN"}
    assert out["by"]["gamma"]["declared"] == ["gamma"]
    assert out["by"]["alpha"]["running"] == "UNKNOWN"
