"""crew#974 P1: the newsroom director's deploy row -- namespace, RBAC, Deployment, image
policy, and the Flux Kustomization that applies it."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _render(path: str) -> list[dict]:
    exe = shutil.which("kustomize")
    cmd = [exe, "build", path] if exe else ["kubectl", "kustomize", path]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    return [d for d in yaml.safe_load_all(r.stdout) if d]


def test_the_director_is_the_newsroom():
    objs = _render("platform/voice-router/deploy")
    deploys = [
        o
        for o in objs
        if o["kind"] == "Deployment"
        and o["metadata"]["name"] == "voice-router-director"
    ]
    assert deploys, "no Deployment voice-router-director rendered"
    d = deploys[0]

    assert d["metadata"]["namespace"] == "voice-router"
    assert d["spec"]["replicas"] == 1
    assert d["metadata"]["annotations"]["reloader.stakater.com/auto"] == "true"

    pod_spec = d["spec"]["template"]["spec"]
    assert pod_spec["serviceAccountName"] == "voice-router-director"

    container = pod_spec["containers"][0]
    env = {e["name"]: e.get("value") for e in container["env"]}
    assert env["VOICE_MODE"] == "director"
    assert env["NATS_URL"] == "nats://nats.event-bus.svc:4222"
    assert env["LLM_BASE_URL"] == "http://litellm.llm.svc:4000/v1"
    assert "OTEL_EXPORTER_OTLP_ENDPOINT" in env

    assert container["resources"] == {
        "requests": {"cpu": "10m", "memory": "64Mi"},
        "limits": {"cpu": "100m", "memory": "128Mi"},
    }

    sc = container["securityContext"]
    assert sc["readOnlyRootFilesystem"] is True
    assert sc["allowPrivilegeEscalation"] is False
    assert sc["capabilities"]["drop"] == ["ALL"]

    assert pod_spec["securityContext"]["runAsNonRoot"] is True

    assert container["image"].startswith("ghcr.io/chidionyema/voice-router:main-")


def test_the_director_may_only_read_five_kinds():
    objs = _render("platform/voice-router/deploy")

    roles = [
        o
        for o in objs
        if o["kind"] == "ClusterRole"
        and o["metadata"]["name"] == "voice-router-newsroom"
    ]
    assert roles, "no ClusterRole voice-router-newsroom rendered"
    rules = {
        (rule["apiGroups"][0], rule["resources"][0], tuple(sorted(rule["verbs"])))
        for rule in roles[0]["rules"]
    }
    assert rules == {
        ("", "events", ("get", "list", "watch")),
        ("kustomize.toolkit.fluxcd.io", "kustomizations", ("get", "list", "watch")),
        ("helm.toolkit.fluxcd.io", "helmreleases", ("get", "list", "watch")),
        # crew#987 CP6: flux/deploy's pushes and freshness SLO (internal/newsroom/deploybranch.go).
        ("image.toolkit.fluxcd.io", "imageupdateautomations", ("get", "list", "watch")),
        ("source.toolkit.fluxcd.io", "gitrepositories", ("get", "list", "watch")),
    }

    bindings = [
        o
        for o in objs
        if o["kind"] == "ClusterRoleBinding"
        and o["metadata"]["name"] == "voice-router-newsroom"
    ]
    assert bindings, "no ClusterRoleBinding voice-router-newsroom rendered"
    subjects = bindings[0]["subjects"]
    assert {
        "kind": "ServiceAccount",
        "name": "voice-router-director",
        "namespace": "voice-router",
    } in subjects


def test_a_flux_row_applies_it():
    rows = [d for d in _render("clusters/oke") if d["kind"] == "Kustomization"]
    voice_router_rows = [r for r in rows if r["metadata"]["name"] == "voice-router"]
    assert voice_router_rows, (
        f"no Flux row named voice-router (rows: {[r['metadata']['name'] for r in rows]})"
    )
    row = voice_router_rows[0]
    assert row["spec"]["path"] == "./platform/voice-router/deploy"
    assert row["spec"]["prune"] is True


def test_the_image_has_a_policy():
    objs = _render("platform/image-automation")

    policies = [
        o
        for o in objs
        if o["kind"] == "ImagePolicy" and o["metadata"]["name"] == "voice-router"
    ]
    assert policies, "no ImagePolicy voice-router rendered"
    assert (
        policies[0]["spec"]["filterTags"]["pattern"]
        == "^main-(?P<run>[0-9]+)-[0-9a-f]{40}$"
    )

    repos = [
        o
        for o in objs
        if o["kind"] == "ImageRepository" and o["metadata"]["name"] == "voice-router"
    ]
    assert repos, "no ImageRepository voice-router rendered"
    assert repos[0]["spec"]["image"] == "ghcr.io/chidionyema/voice-router"

    kustomization_text = (
        ROOT / "platform/voice-router/deploy/kustomization.yaml"
    ).read_text()
    assert '# {"$imagepolicy": "flux-system:voice-router:tag"}' in kustomization_text
