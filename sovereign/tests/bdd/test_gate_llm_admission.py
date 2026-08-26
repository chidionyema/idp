"""Binds features/gates/llm-admission.feature (crew#284 CP2). Incident 2026-08-26: the llm Flux
Kustomization read `Deployment/llm/litellm dry-run failed: admission webhook ... denied` for the
policies secrets-not-from-env-vars and no-optional-secret-references, because
bin/idp-kyverno-render judged HelmReleases only and platform/llm ships a plain Deployment. Both
ways: the shipped manifest is admitted, the envFrom shape is refused. BLIND without kyverno."""
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, scenarios, then, when

scenarios("features/gates/llm-admission.feature")

IDP = Path(__file__).resolve().parents[3]
LLM = IDP / "platform" / "llm"
RENDER = IDP / "bin" / "idp-kyverno-render"


@pytest.fixture
def state() -> dict:
    return {}


def _deployment() -> dict:
    docs = [d for d in yaml.safe_load_all((LLM / "litellm.yaml").read_text()) if isinstance(d, dict)]
    return next(d for d in docs if d["kind"] == "Deployment")


@given("platform/llm carries the litellm Deployment with its secrets mounted as files")
def _shipped(state: dict) -> None:
    c = _deployment()["spec"]["template"]["spec"]["containers"][0]
    assert "envFrom" not in c, "litellm takes secrets from envFrom; the cluster refuses that"
    assert {m["name"] for m in c["volumeMounts"]} >= {"upstream", "langfuse"}


@given("the litellm Deployment rewritten to take its secrets from envFrom")
def _envfrom(state: dict, tmp_path: Path) -> None:
    dep = _deployment()
    c = dep["spec"]["template"]["spec"]["containers"][0]
    c["envFrom"] = [{"secretRef": {"name": "litellm-upstream"}}, {"secretRef": {"name": "litellm-langfuse", "optional": True}}]
    (tmp_path / "litellm.yaml").write_text(yaml.safe_dump(dep))
    (tmp_path / "kustomization.yaml").write_text("resources: [litellm.yaml]\n")
    state["dir"] = tmp_path


def _run(target: str) -> subprocess.CompletedProcess:
    if not shutil.which("kyverno"):
        pytest.skip("BLIND: kyverno not installed")
    return subprocess.run([str(RENDER), target], cwd=IDP, capture_output=True, text=True)


@when("bin/idp-kyverno-render platform/llm runs")
def _render_llm(state: dict) -> None:
    state["run"] = _run("platform/llm")


@when("bin/idp-kyverno-render runs on that directory")
def _render_tmp(state: dict) -> None:
    state["run"] = _run(str(state["dir"]))


@then("the plain workload passes every policy and it exits 0")
def _admitted(state: dict) -> None:
    r = state["run"]
    assert r.returncode == 0 and "ok    plain    platform/llm" in r.stdout, r.stdout + r.stderr


@then("it reports FAIL for the plain workload and exits 1")
def _refused(state: dict) -> None:
    r = state["run"]
    assert r.returncode == 1 and "FAIL  plain" in r.stdout and "secrets-not-from-env-vars" in r.stdout, r.stdout + r.stderr
