#!/usr/bin/env python3
"""bin/estate-flux-dag: property + incident tests (R29, the deploy-time map).

Rungs, per ~/AGENTS.md "How to test":
  property  for random synthetic Kustomization/HelmRelease trees, every declared object is a
            node, every dependsOn entry is an edge, a dependsOn target with no manifest of its
            own is drawn dashed rather than silently dropped, and rendering twice over one
            unchanged tree gives the same bytes (every generator must be idempotent).
  incident  named for R29 "a hand-drawn one is deleted": --check fails when the .dot on disk
            drifts from the manifests and passes after a real render, and BLINDs when there is
            no clusters/ or platform/ tree to read, proved in one run.

Run: python3 tests/test_estate_flux_dag.py (needs pyyaml). Exit 0 pass, 1 fail.
"""

import importlib.machinery
import importlib.util
import random
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin" / "estate-flux-dag"
spec = importlib.util.spec_from_loader(
    "estate_flux_dag", importlib.machinery.SourceFileLoader("estate_flux_dag", str(BIN))
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def synth_tree(root: Path, rng: random.Random) -> None:
    """A random Kustomization/HelmRelease tree, one file per object, some with dependsOn
    targets that have no manifest of their own -- the dashed-node case must be exercised."""
    (root / "clusters").mkdir(parents=True, exist_ok=True)
    n = rng.randint(3, 12)
    names = [f"obj{i}" for i in range(n)]
    for i, name in enumerate(names):
        kind = rng.choice(["Kustomization", "HelmRelease"])
        ns = rng.choice(["flux-system", "ns-a", "ns-b"])
        deps = []
        for prior in names[:i]:
            if rng.random() < 0.4:
                deps.append({"name": prior})
        if rng.random() < 0.2:
            deps.append({"name": "not-in-this-tree"})
        doc = {
            "apiVersion": "kustomize.toolkit.fluxcd.io/v1"
            if kind == "Kustomization"
            else "helm.toolkit.fluxcd.io/v2",
            "kind": kind,
            "metadata": {"name": name, "namespace": ns},
            "spec": {"dependsOn": deps} if deps else {"path": "./x"},
        }
        (root / "clusters" / f"{name}.yaml").write_text(yaml.safe_dump(doc))


def prop_every_object_is_a_node_and_deps_are_edges(n=200) -> int:
    fails = 0
    for seed in range(n):
        rng = random.Random(seed)  # noqa: S311 -- synthetic fixture data, not cryptographic
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            synth_tree(root, rng)
            declared, edges = mod.build_graph(root)
            page = mod.render(root)
            page2 = mod.render(root)
            if page != page2:
                fails += 1
                print(f"FAIL seed={seed}: not idempotent")
                continue
            for nid in declared:
                if mod.dot_id(nid) + ";" not in page:
                    fails += 1
                    print(f"FAIL seed={seed}: {nid} missing as a node")
                    break
            else:
                for src, dst in edges:
                    if f"{mod.dot_id(src)} -> {mod.dot_id(dst)};" not in page:
                        fails += 1
                        print(f"FAIL seed={seed}: edge {src}->{dst} missing")
                        break
    return fails


def incident_r29_hand_drawn_map_is_refused() -> int:
    with tempfile.TemporaryDirectory() as td:
        root, out = Path(td), Path(td) / "map.dot"
        synth_tree(root, random.Random(3))  # noqa: S311 -- synthetic fixture data, not cryptographic
        out.write_text("digraph hand_drawn {}\n")
        bad = subprocess.run(
            [sys.executable, str(BIN), "--root", root, "--out", out, "--check"],
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [sys.executable, str(BIN), "--root", root, "--out", out],
            check=True,
            capture_output=True,
        )
        good = subprocess.run(
            [sys.executable, str(BIN), "--root", root, "--out", out, "--check"],
            capture_output=True,
            text=True,
        )
        empty = Path(tempfile.mkdtemp())
        missing = subprocess.run(
            [sys.executable, str(BIN), "--root", empty, "--check"],
            capture_output=True,
            text=True,
        )
    ok = (
        bad.returncode == 1
        and "FAIL" in bad.stdout
        and good.returncode == 0
        and "ok" in good.stdout
        and missing.returncode == 3
        and "BLIND" in missing.stderr
    )
    print(
        f"{'ok  ' if ok else 'FAIL'}  incident r29: drifted rc={bad.returncode}, rendered rc={good.returncode}, no manifests rc={missing.returncode}"
    )
    return 0 if ok else 1


def test_property_every_object_is_a_node_and_deps_are_edges():
    assert prop_every_object_is_a_node_and_deps_are_edges() == 0


def test_incident_r29_hand_drawn_map_is_refused():
    assert incident_r29_hand_drawn_map_is_refused() == 0


if __name__ == "__main__":
    f = prop_every_object_is_a_node_and_deps_are_edges()
    print(f"{'ok  ' if not f else 'FAIL'}  property: 200 synthetic trees, {f} failures")
    f += incident_r29_hand_drawn_map_is_refused()
    sys.exit(1 if f else 0)
