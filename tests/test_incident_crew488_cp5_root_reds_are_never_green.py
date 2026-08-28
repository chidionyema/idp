"""crew#488 CP5: the portability drill graded 2/38 as ok, because it could not tell a cause from a cascade.

Run 33208911991 (2026-08-28): four layers broke for reasons of their own (a ClusterPolicy applied
before Kyverno's CRD, an ExternalSecret before ESO's, the vault ConfigMap, the private catalog
artifact), thirty-two fell behind them with Flux's "dependency X is not ready", and the line read
`ok portability ready 2/38 (floor 2)`. The floor was met, the tree was broken, and nothing said so.

The grader now names each red: `cascaded` (a row above is red), `oci-red` (a reason of its own that
drills/portability-oci-reds.txt names for that layer), or `ROOT-RED` (a reason of its own nobody has
named), and a ROOT-RED FAILS the run whatever the floor says. Proved both ways per LAW 45 step 3.
The tree fixes that turned the four roots into two honest reds are proved by the drill's own run on
the branch (the PR carries the URL); this file proves the grader, and that the two remaining roots
are on the list and every ClusterPolicy in the tree is applied by some layer.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
_loader = importlib.machinery.SourceFileLoader("drill", str(ROOT / "bin" / "idp-portability-drill"))
drill = importlib.util.module_from_spec(importlib.util.spec_from_loader("drill", _loader))
_loader.exec_module(drill)

REDS = drill.read_reds(str(ROOT / "drills" / "portability-oci-reds.txt"))
CASCADE = "dependency 'flux-system/secret-store' is not ready"


def _ks(name: str, ready: bool, msg: str = "") -> dict:
    return {
        "metadata": {"name": name, "namespace": "flux-system"},
        "status": {"conditions": [{"type": "Ready", "status": "True" if ready else "False", "message": msg}]},
    }


def test_the_measured_run_shape_is_red_not_green():
    """2 ready, 4 roots (one honest), 32 cascaded, floor 2: was ok, is FAIL naming the three unnamed roots."""
    items = [_ks("external-secrets", True), _ks("gateway-api-crds", True),
             _ks("edge", False, "ClusterPolicy/provider-independence dry-run failed: no matches for kind ClusterPolicy"),
             _ks("backstage", False, "ExternalSecret/backstage/backstage-env dry-run failed: no matches for kind ExternalSecret"),
             _ks("estate-catalog", False, "Source artifact not found, retrying in 30s"),
             _ks("secret-store", False, "failed to substitute from ConfigMap/estate-vars: configmaps \"estate-vars\" not found")]
    items += [_ks(f"layer-{i}", False, CASCADE) for i in range(32)]
    verdict, lines = drill.grade(items, floor=2, reds=REDS)
    assert verdict.startswith("FAIL    portability  root-red not on drills/portability-oci-reds.txt: edge backstage"), verdict
    assert "(ready 2/38, cascaded 32)" in verdict
    assert sum(ln.startswith("  cascaded ") for ln in lines) == 32
    assert sum(ln.startswith("  oci-red ") for ln in lines) == 2
    assert sum(ln.startswith("  ROOT-RED ") for ln in lines) == 2


def test_only_named_roots_and_cascades_is_green_and_the_floor_still_bites():
    items = [_ks("external-secrets", True), _ks("gateway-api-crds", True), _ks("kyverno", True), _ks("edge", True),
             _ks("estate-catalog", False, "Source artifact not found, retrying in 30s"),
             _ks("secret-store", False, "failed to substitute from ConfigMap/estate-vars"),
             _ks("backstage", False, CASCADE)]
    ok, _ = drill.grade(items, floor=4, reds=REDS)
    assert ok.startswith("ok      portability  ready 4/7 (root-red 2 all named, cascaded 1)"), ok
    fail, _ = drill.grade(items, floor=5, reds=REDS)
    assert fail.startswith("FAIL    portability  ready 4/7 is below the floor 5"), fail


def test_a_named_reason_on_the_wrong_layer_is_still_a_root():
    """The list names a layer and its reason; the reason alone does not excuse another layer."""
    items = [_ks("a", True), _ks("dns", False, "failed to substitute from ConfigMap/estate-vars")]
    verdict, lines = drill.grade(items, floor=1, reds=REDS)
    assert verdict.startswith("FAIL    portability  root-red"), verdict
    assert lines[0].startswith("  ROOT-RED   flux-system/dns")


def test_a_reds_row_without_a_reason_is_refused(tmp_path):
    p = tmp_path / "reds.txt"
    p.write_text("secret-store\n")
    try:
        drill.read_reds(str(p))
    except ValueError as e:
        assert "root-red" in str(e)
    else:
        raise AssertionError("a layer with no reason was accepted")


def _layer_paths() -> dict[str, str]:
    out = {}
    for f in sorted((ROOT / "clusters" / "oke").glob("*.yaml")):
        for d in yaml.safe_load_all(f.read_text()):
            if d and d.get("kind") == "Kustomization" and str((d.get("spec") or {}).get("path", "")).startswith("./platform/"):
                out[d["metadata"]["name"]] = d["spec"]["path"]
    return out


def test_every_clusterpolicy_in_the_tree_is_applied_by_a_layer_that_waits_on_kyverno():
    """crew#341's secrets policy sat in platform/edge for two days in no kustomization: never installed."""
    layers = _layer_paths()
    deps = {}
    for f in sorted((ROOT / "clusters" / "oke").glob("*.yaml")):
        for d in yaml.safe_load_all(f.read_text()):
            if d and d.get("kind") == "Kustomization":
                deps[d["metadata"]["name"]] = [x["name"] for x in (d.get("spec") or {}).get("dependsOn", [])]

    def waits_on_kyverno(layer: str, seen=()) -> bool:
        return layer == "kyverno" or any(waits_on_kyverno(x, seen + (layer,)) for x in deps.get(layer, []) if x not in seen)

    policies = [p for p in (ROOT / "platform").rglob("*.yaml") if "kind: ClusterPolicy" in p.read_text()]
    assert policies, "no ClusterPolicy in the tree"
    for p in policies:
        rel = f"./{p.parent.relative_to(ROOT)}"
        kust = yaml.safe_load((p.parent / "kustomization.yaml").read_text())
        assert p.name in kust.get("resources", []), f"{p} is in no kustomization: never installed"
        owners = [n for n, path in layers.items() if path == rel]
        assert owners, f"{rel} is applied by no Kustomization under clusters/oke"
        for o in owners:
            assert waits_on_kyverno(o), f"layer {o} applies {p.name} but does not wait on the kyverno layer"


def test_the_two_remaining_roots_are_the_vault_and_the_private_catalog():
    assert [layer for layer, _ in REDS] == ["secret-store", "estate-catalog"], REDS


def test_the_security_page_lists_exactly_the_policies_the_tree_applies():
    """Founder 2026-08-28: the crew must never be confused about how security works. The page
    carries bin/idp-admission-policies' table verbatim; a hand edit or a new policy without a
    regenerate is red, and a policy in no layer is red in the command itself."""
    import subprocess
    r = subprocess.run([str(ROOT / "bin" / "idp-admission-policies")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout
    page = (ROOT / "docs" / "reference" / "security-policy.md").read_text()
    begin, end = "<!-- admission-policies:begin -->\n", "<!-- admission-policies:end -->"
    assert begin in page and end in page
    assert page.split(begin, 1)[1].split(end, 1)[0] == r.stdout, "page table differs from bin/idp-admission-policies; regenerate"
