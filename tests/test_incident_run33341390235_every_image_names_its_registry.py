"""Run 33341390235, 2026-08-30: `Failed to pull image "tailscale/k8s-operator:v1.102.3": short name
mode is enforcing, but image name tailscale/k8s-operator:v1.102.3 returns ambiguous list`. The
tailscale-operator Deployment never rolled, its HelmRelease sat Failed, and Kustomization/guacamole
was dark behind it for hours. Five days earlier the same sentence took langfuse's S3 pod down for
three (crew#325, `chrislusf/seaweedfs:4.23`): the OKE nodes run cri-o with short-name mode
enforcing, so an image reference with no registry host in its first path segment is unresolvable on
this estate, and nothing refuses it -- the manifest is valid, admission passes, and the failure
surfaces minutes later on the kubelet as a stalled controller.

This is instance four in five days, and instances one and two already had a guard: crew#284
(`postgres:17.6-alpine`, platform/llm) and crew#396 (the temporal chart defaults) are held by
tests/test_incident_crew284_short_image_name_refused_by_runtime.py, which scans this repository's
files. That guard names its own blind spot in its docstring, verbatim -- "Residual: a chart default
that the HelmRelease does not override is not in any file here and stays unseen" -- and instances
three and four were both exactly that. A file scan cannot see an image that only exists after
`helm template` runs, so the answer is not a wider regex; it is judging the rendered pod.

LAW 45: the guard is platform/edge/require-registry-host.yaml, a ClusterPolicy that judges the
rendered Pod at admission, and bin/idp-kyverno-render grades it offline over every directory
bin/idp-kyverno-dirs names. These tests pin the guard's shape, the tailscale fix, and -- the part
that makes a source-level sweep honest -- that every short name still written in a base manifest is
one a kustomize `images:` transformer rewrites before it reaches a node (LAW 38: a guard that
refuses correct work is an outage; platform/backstage/base and platform/temporal are correct)."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "platform" / "edge" / "require-registry-host.yaml"
TAILSCALE = ROOT / "platform" / "tailscale" / "operator.yaml"

# A reference names a registry when its first path segment is a host: it carries a dot, or it is
# localhost, either optionally with a port. This is the same shape the policy asserts.
HOST = re.compile(r"^([a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+(:[0-9]+)?|localhost(:[0-9]+)?)/")


def _docs(path):
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def _policy():
    return next(d for d in _docs(POLICY) if d.get("kind") == "ClusterPolicy")


def test_the_policy_judges_the_pod_so_autogen_covers_every_controller():
    p = _policy()
    assert p["metadata"]["name"] == "require-registry-host"
    rule = p["spec"]["rules"][0]
    kinds = rule["match"]["any"][0]["resources"]["kinds"]
    assert kinds == ["Pod"], (
        "matching Pod is what makes Kyverno autogen cover Deployment/StatefulSet/DaemonSet/"
        "CronJob, and what makes bin/idp-kyverno-render grade the object the kubelet acts on"
    )
    listed = rule["validate"]["foreach"][0]["list"]
    for kind in ("containers", "initContainers", "ephemeralContainers"):
        assert kind in listed, (
            f"{kind} images pull through the same runtime and are not judged"
        )


def test_the_policy_starts_in_audit_on_the_crew539_precedent():
    """platform/scheduling/require-priority-class.yaml: a new rule is a PolicyReport row until a
    render of every directory reports zero violations. Flipping this to Enforce is a deliberate
    edit with that render attached, never a default."""
    assert _policy()["spec"]["rules"][0]["validate"]["failureAction"] == "Audit"


def _short_name_sources():
    """Every literal `image:` in platform/ whose reference names no registry, by repository."""
    out = {}
    for f in sorted((ROOT / "platform").rglob("*.yaml")):
        for n, line in enumerate(f.read_text().split("\n"), 1):
            m = re.match(r"^\s*image:\s*([^\s#{'\"]+)\s*$", line)
            if m and not HOST.match(m.group(1)):
                out.setdefault(m.group(1).rsplit(":", 1)[0], []).append(
                    f"{f.relative_to(ROOT)}:{n}"
                )
    return out


def _rewritten_repositories():
    """Every repository a kustomize `images:` transformer renames to a qualified reference."""
    out = set()
    for f in sorted((ROOT / "platform").rglob("kustomization.yaml")):
        doc = yaml.safe_load(f.read_text()) or {}
        for entry in doc.get("images") or []:
            if HOST.match(str(entry.get("newName", ""))):
                out.add(entry["name"])
    return out


def test_the_kyverno_cli_refuses_the_short_name_and_admits_the_qualified_one(tmp_path):
    """Teeth. Every assertion above reads the policy as text; this one runs it. The two references
    are the ones from the two incidents, side by side with their corrected form, judged by the same
    kyverno CLI bin/idp-kyverno-render and .github/workflows/ci.yml pin at v1.19.0."""
    import shutil
    import subprocess

    assert shutil.which("kyverno"), (
        "the kyverno CLI is how this policy is graded offline (ci.yml installs v1.19.0); "
        "without it this test would pass by skipping, which is the silent-green class"
    )
    pods = tmp_path / "pods.yaml"
    pods.write_text(
        "apiVersion: v1\nkind: Pod\nmetadata: { name: short-name, namespace: default }\n"
        "spec:\n  containers:\n    - name: c\n      image: tailscale/k8s-operator:v1.102.3\n"
        "---\n"
        "apiVersion: v1\nkind: Pod\nmetadata: { name: qualified, namespace: default }\n"
        "spec:\n  containers:\n    - name: c\n      image: docker.io/tailscale/k8s-operator:v1.102.3\n"
    )
    r = subprocess.run(
        ["kyverno", "apply", str(POLICY), "--resource", str(pods)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = r.stdout + r.stderr
    assert "pass: 1, fail: 1" in out, out
    assert "default/Pod/short-name failed" in out, out


def test_the_offline_judge_reads_a_post_renderer_images_transformer():
    """A chart that hardcodes a short name in its templates -- lago writes `image: getlago/api:v{{
    .Values.version }}` and has no values key for a registry -- can only be qualified by Flux's
    post-renderer `images:`. bin/idp-kyverno-render read `patches:` and nothing else, so it would
    have judged a correctly-qualified release as unqualified: a red the founder cannot act on."""
    render = (ROOT / "bin" / "idp-kyverno-render").read_text()
    assert '.get("kustomize", {}).get("images", [])' in render, (
        "the judge ignores postRenderers[].kustomize.images"
    )
    assert '"images": images' in render, (
        "the harvested images never reach the kustomization"
    )
    lago = yaml.safe_load_all(
        (ROOT / "platform" / "commerce" / "app" / "lago.yaml").read_text()
    )
    hr = next(
        d
        for d in lago
        if d and d.get("kind") == "HelmRelease" and d["metadata"]["name"] == "lago"
    )
    images = [
        i
        for pr in hr["spec"]["postRenderers"]
        for i in pr["kustomize"].get("images", [])
    ]
    assert images, (
        "lago names no image rewrite, and its chart hardcodes getlago/* short names"
    )
    for entry in images:
        assert HOST.match(entry["newName"]), entry
