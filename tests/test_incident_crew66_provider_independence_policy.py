"""crew#66, founder decree 2026-08-28 (ruling R43): never couple the platform to a provider,
enforced as enterprise policy. The control is platform/edge/provider-independence.yaml, a Kyverno
ClusterPolicy in Enforce; this file proves three things about it with the same CLI CI runs:
it refuses every known way of coupling (one fixture object per way, each caught by the rule
written for it, so a rule that silently stopped matching fails here); a clean tree and the one
declared hole (the edge load balancer the cluster row patches) pass; and the platform tree as
it stands carries no coupling (LAW 38: an Enforce policy that refuses correct work is an outage,
so it is graded against every plain manifest Flux applies before it can merge).

Never a silent pass: without the CLI the module fails, it does not skip (LAW 28)."""
import pathlib
import re
import shutil
import subprocess

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "platform/edge/provider-independence.yaml"
EXCEPTION = ROOT / "platform/edge/provider-edge-exception.yaml"
FIXTURES = ROOT / "tests/fixtures/kyverno/provider-coupled"
JUDGED_KINDS = {"Service", "Ingress", "PersistentVolumeClaim", "StatefulSet", "Deployment",
                "DaemonSet", "Pod", "Job", "CronJob", "ClusterSecretStore", "SecretStore"}
FAILED = re.compile(r"^policy provider-independence -> resource (\S+) failed:\n\d+ - (\S+) ", re.M)


def _apply(resource: pathlib.Path, *, exception: bool) -> str:
    assert shutil.which("kyverno"), "BLIND: the kyverno CLI is not installed; ci.yml installs it"
    cmd = ["kyverno", "apply", str(POLICY), "--resource", str(resource)]
    if exception:
        cmd += ["--exception", str(EXCEPTION)]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def _summary(out: str) -> dict:
    line = [l for l in out.splitlines() if l.startswith("pass:")][-1]
    return {k: int(v) for k, v in re.findall(r"(\w+): (\d+)", line)}


def test_every_way_of_coupling_is_refused_by_the_rule_written_for_it():
    out = _apply(FIXTURES / "coupled.yaml", exception=False)
    assert set(FAILED.findall(out)) == {
        ("apps/Service/lb-with-oci-shape", "no-provider-annotations"),
        ("apps/Service/lb-with-aws-annotation", "no-provider-annotations"),
        ("apps/Service/lb-with-provider-class", "no-provider-load-balancer-class"),
        ("apps/PersistentVolumeClaim/claim-on-oci-bv", "no-provider-storage-class"),
        ("apps/StatefulSet/db-on-gp3", "no-provider-storage-class-in-templates"),
        # autogen: the Pod rule is carried onto the Deployment's template by Kyverno itself.
        ("apps/Deployment/pod-with-oci-csi", "autogen-no-provider-csi-driver"),
        ("default/ClusterSecretStore/second-door", "one-provider-secret-door"),
    }, out
    assert _summary(out)["fail"] == 7, out


def test_a_clean_tree_and_the_one_declared_hole_pass():
    out = _apply(FIXTURES / "clean.yaml", exception=True)
    s = _summary(out)
    assert s["fail"] == 0 and s["error"] == 0, out
    # The hole is one Service (edge/traefik), excused by one exception, and shows as one skip;
    # without the exception the same file is refused, so the exception is doing the work.
    assert s["skip"] == 1, out
    assert _summary(_apply(FIXTURES / "clean.yaml", exception=False))["fail"] == 1


def test_the_platform_tree_as_it_stands_carries_no_coupling(tmp_path):
    """LAW 38. Every plain object of a judged kind in every kustomization under platform/,
    rendered as Flux renders it, passes the policy with only the declared exception."""
    assert shutil.which("kubectl"), "BLIND: kubectl is not installed"
    docs, dirs = [], []
    for kz in sorted(ROOT.glob("platform/**/kustomization.yaml")):
        if any(part in {"k3d", "overlays", "base"} for part in kz.relative_to(ROOT).parts):
            continue  # overlays are rendered through their parents; k3d is a throwaway local
        r = subprocess.run(["kubectl", "kustomize", str(kz.parent)], capture_output=True, text=True)
        assert r.returncode == 0, f"{kz.parent} does not build: {r.stderr}"
        dirs.append(kz.parent)
        docs += [d for d in yaml.safe_load_all(r.stdout) if d and d.get("kind") in JUDGED_KINDS]
    assert len(dirs) >= 10 and len(docs) >= 10, (dirs, len(docs))
    tree = tmp_path / "tree.yaml"
    tree.write_text(yaml.safe_dump_all(docs))
    out = _apply(tree, exception=True)
    assert not FAILED.findall(out), out
    s = _summary(out)
    assert s["fail"] == 0 and s["error"] == 0 and s["pass"] > 0, out


def test_the_portability_drill_runs_on_every_platform_and_cluster_change():
    wf = yaml.safe_load((ROOT / ".github/workflows/portability-drill.yml").read_text())
    paths = set(wf[True]["pull_request"]["paths"])  # yaml parses the `on:` key as True
    assert {"platform/**", "clusters/**"} <= paths, paths
