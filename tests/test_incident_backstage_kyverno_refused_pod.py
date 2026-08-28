"""Incident 2026-08-25: the Backstage image finally built (idp#125) and the catalogue still had
no pod. The ReplicaSet reported `admission webhook "validate.kyverno.svc-fail" denied the
request`: require-ro-rootfs and secrets-not-from-env-vars, both installed cluster-wide by the
prospector Flux row (prospector-main/deploy/k8s/policies). Postgres only ran because its pod
predates the policies; its next restart would have been refused the same way.

Rule (rung 4, incident test): every Pod the Backstage overlays render passes the estate's
Kyverno policy set, evaluated by the kyverno CLI against the policies as prospector ships them.
Proved both ways: the origin/main render of 2026-08-25 failed 4 rules; a fixture that repeats
one of those shapes must still fail here.

The policies live in a sibling checkout named by ESTATE_CODE (LAW 46: no path literal); with
no checkout or no kyverno binary the test is BLIND and says so, never green."""
import os
import pathlib
import shutil
import subprocess

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
ESTATE_CODE = pathlib.Path(os.environ.get("ESTATE_CODE", ROOT.parent))
POLICIES = ESTATE_CODE / "prospector-main" / "deploy" / "k8s" / "policies"
# The oke overlay only: the local (k3d) overlay generates a ConfigMap from a gitignored
# catalog file and k3d runs no Kyverno; the policies bind the production cluster.
OVERLAYS = [ROOT / "platform" / "backstage" / "overlays" / "oke" / "kustomization.yaml"]


def _blind():
    if not shutil.which("kyverno"):
        pytest.skip("BLIND: kyverno CLI not installed; the estate policy set cannot be evaluated")
    if not (POLICIES / "kustomization.yaml").exists():
        pytest.skip(f"BLIND: no policy checkout at {POLICIES} (set ESTATE_CODE)")


def _pods_of(overlay_dir):
    rendered = subprocess.run(
        ["kubectl", "kustomize", "--load-restrictor", "LoadRestrictionsNone", str(overlay_dir)],
        check=True, capture_output=True, text=True,
    ).stdout
    for d in yaml.safe_load_all(rendered):
        if d and d.get("kind") in ("Deployment", "StatefulSet"):
            t = d["spec"]["template"]
            yield {
                "apiVersion": "v1", "kind": "Pod",
                "metadata": {"name": d["metadata"]["name"], "namespace": d["metadata"].get("namespace", "backstage"),
                             "labels": t["metadata"].get("labels", {})},
                "spec": t["spec"],
            }


def _apply(tmp_path, pods):
    policies = tmp_path / "policies.yaml"
    policies.write_text(subprocess.run(["kubectl", "kustomize", str(POLICIES)], check=True,
                                       capture_output=True, text=True).stdout)
    resource = tmp_path / "pods.yaml"   # a leading dot hides the file from the CLI: 0 rules applied
    resource.write_text(yaml.safe_dump_all(list(pods)))
    out = subprocess.run(["kyverno", "apply", str(policies), "--resource", str(resource)],
                         capture_output=True, text=True).stdout
    summary = [line for line in out.splitlines() if line.startswith("pass:")]
    assert summary, out
    counts = dict(kv.strip().split(": ") for kv in summary[-1].split(","))
    return int(counts["pass"]), int(counts["fail"]), out


def test_every_backstage_overlay_pod_passes_the_estate_policies(tmp_path):
    _blind()
    assert OVERLAYS, "no overlays found"
    for k in OVERLAYS:
        pods = list(_pods_of(k.parent))
        assert pods, f"{k.parent}: renders no workload"
        passed, failed, out = _apply(tmp_path, pods)
        assert failed == 0 and passed > 0, f"{k.parent}: {out[-1500:]}"


def test_the_incident_shape_is_still_refused(tmp_path):
    """The guard must be seen refusing: the catalogue as it was on origin/main that morning."""
    _blind()
    pods = list(_pods_of(OVERLAYS[0].parent))
    c = pods[0]["spec"]["containers"][0]
    c["securityContext"]["readOnlyRootFilesystem"] = False
    c["envFrom"] = [{"secretRef": {"name": "backstage-env"}}]
    _, failed, out = _apply(tmp_path, pods)
    assert failed == 2, out[-1500:]
    assert "require-ro-rootfs" in out and "secrets-not-from-env-vars" in out
