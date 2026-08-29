"""Incident 2026-08-28 (crew#539, receipt oke-check 33128543299 00:09Z): HelmRelease robusta/robusta
never installed — Kyverno refused robusta-runner and robusta-forwarder on 15 rules (drop ALL,
runAsNonRoot, seccomp, probes, ro rootfs, requests, secrets-from-env) — so the Alertmanager
`robusta` receiver and the CrashLoop playbooks (CP8/9/11) pointed at nothing for 14 hours.
The class: bin/idp-ci step 9 rendered only HelmRelease dirs that carry postRenderers, so a
release with none was never judged (crew#284 closed the same gap for plain workloads). Rule:
every HelmRelease dir with a kustomization.yaml is rendered, and the robusta release itself
carries the restricted profile it was refused for."""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_ci_renders_every_helmrelease_dir_not_only_the_patched_ones() -> None:
    ci = (ROOT / "bin/idp-ci").read_text()
    step = ci.split("kyverno-render")[0].rsplit("dirs=", 1)[1]
    assert "postRenderers" not in step, "idp-ci still filters HelmRelease dirs on postRenderers"
    assert "kind: HelmRelease" in step


def _robusta():
    docs = [d for d in yaml.safe_load_all((ROOT / "platform/robusta/robusta.yaml").read_text()) if d]
    return next(d for d in docs if d["kind"] == "HelmRelease")


def test_runner_and_forwarder_carry_the_restricted_profile() -> None:
    v = _robusta()["spec"]["values"]
    for name in ("runner", "kubewatch"):
        c = v[name]["securityContext"]["container"]
        assert c["capabilities"] == {"drop": ["ALL"]} and c["runAsNonRoot"] is True, name
        assert c["allowPrivilegeEscalation"] is False and c["seccompProfile"] == {"type": "RuntimeDefault"}, name
    assert v["runner"]["hardenedFs"] is True   # readOnlyRootFilesystem on the runner comes from this
    assert v["kubewatch"]["securityContext"]["container"]["readOnlyRootFilesystem"] is True
    pod = v["runner"]["securityContext"]["pod"]
    assert pod["runAsUser"] == 1000 and pod["runAsNonRoot"] is True, "the runner image has no USER line"
    assert {"name": "HOME", "value": "/tmp"} in v["runner"]["additional_env_vars"], "/root/.cache is unreachable as uid 1000"


def test_probes_and_init_container_profile_come_from_the_post_renderer() -> None:
    patches = _robusta()["spec"]["postRenderers"][0]["kustomize"]["patches"]
    by = {p["target"]["name"]: yaml.safe_load(p["patch"])["spec"]["template"]["spec"] for p in patches if "name" in p["target"]}
    kw = by["robusta-forwarder"]["containers"][0]
    assert kw["name"] == "kubewatch" and kw["readinessProbe"]["httpGet"] == {"path": "/metrics", "port": 2112}
    runner = by["robusta-runner"]
    assert runner["containers"][0]["readinessProbe"]["httpGet"] == {"path": "/healthz", "port": 5000}
    init = runner["initContainers"][0]
    assert init["name"] == "setup-venv" and init["securityContext"]["capabilities"] == {"drop": ["ALL"]}
    assert init["securityContext"]["runAsNonRoot"] is True and "limits" in init["resources"]


def test_secrets_exception_is_scoped_to_the_runner_and_lives_in_namespace_kyverno() -> None:
    exc = yaml.safe_load((ROOT / "platform/edge/robusta-exception.yaml").read_text())
    assert exc["metadata"]["namespace"] == "kyverno"
    assert [e["policyName"] for e in exc["spec"]["exceptions"]] == ["secrets-not-from-env-vars"]
    res = exc["spec"]["match"]["any"][0]["resources"]
    assert res["namespaces"] == ["robusta"] and res["names"] == ["robusta-runner*"]
    kust = yaml.safe_load((ROOT / "platform/edge/kustomization.yaml").read_text())
    assert "robusta-exception.yaml" in kust["resources"]
    assert re.search(r"^  - robusta-exception\.yaml$", (ROOT / "platform/edge/kustomization.yaml").read_text(), re.M)
