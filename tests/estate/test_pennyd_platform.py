"""Pennyd is a platform component, not a downloadable router artifact."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import toml
import yaml


ROOT = Path(__file__).resolve().parents[2]
PENNYD = ROOT / "platform" / "llm" / "pennyd"


def test_pennyd_source_and_locked_workspace_are_pinned_in_platform():
    assert (PENNYD / "Cargo.toml").is_file()
    assert (PENNYD / "Cargo.lock").is_file()
    assert (PENNYD / "providers" / "zai.toml").is_file()
    zai = toml.loads((PENNYD / "providers" / "zai.toml").read_text())
    assert {"glm", "zai/glm-5.3"} <= set(zai["models"][0]["aliases"])


def test_runtime_dependencies_and_budget_store_contracts_are_present():
    cargo = (PENNYD / "crates" / "pennyd" / "Cargo.toml").read_text()
    runtime = cargo.split("[dev-dependencies]", 1)[0]
    assert "async-trait" in runtime, "async-trait is used by production lane code"
    budget = (PENNYD / "crates" / "penny-core" / "src" / "budget.rs").read_text()
    assert "persist_snapshot" in budget
    assert "budget_fingerprint" in budget
    assert "self.persist();" not in budget
    keys = (PENNYD / "crates" / "penny-core" / "src" / "keys.rs").read_text()
    assert "pub fn budget_fingerprint" in keys


def test_deployment_has_one_router_container_and_all_required_mounts():
    spec = yaml.safe_load((PENNYD / "deploy" / "deployment.yaml").read_text())
    pod = spec["spec"]["template"]["spec"]
    containers = pod["containers"]
    assert [c["name"] for c in containers] == ["pennyd"]
    assert "secret" not in containers[0], "a volume cannot masquerade as a container"
    volumes = {v["name"]: v for v in pod["volumes"]}
    assert {"config", "keys", "log", "providers", "zai-key"} <= set(volumes)
    assert volumes["log"]["persistentVolumeClaim"]["claimName"] == "pennyd-log"


def test_release_tag_and_crate_version_agree():
    spec = yaml.safe_load((PENNYD / "deploy" / "deployment.yaml").read_text())
    image = spec["spec"]["template"]["spec"]["containers"][0]["image"]
    version = next(
        line.split("=", 1)[1].strip().strip('"')
        for line in (PENNYD / "crates" / "pennyd" / "Cargo.toml").read_text().splitlines()
        if line.startswith("version =")
    )
    assert image.endswith(f":v{version}")


def test_platform_kustomization_renders():
    kubectl = shutil.which("kubectl")
    if not kubectl:
        pytest.skip("kubectl is not installed")
    done = subprocess.run(
        [kubectl, "kustomize", str(PENNYD)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert done.returncode == 0, done.stderr
    rendered = list(yaml.safe_load_all(done.stdout))
    kinds = {item["kind"] for item in rendered if item}
    assert {"ConfigMap", "Deployment", "PersistentVolumeClaim", "Service"} <= kinds


def test_pennyd_is_pinned_into_the_llm_platform_kustomization():
    platform = yaml.safe_load((ROOT / "platform" / "llm" / "kustomization.yaml").read_text())
    assert "pennyd" in platform["resources"]


def test_glm_declares_cross_provider_automatic_failover():
    zai = toml.loads((PENNYD / "providers" / "zai.toml").read_text())
    minimax_path = PENNYD / "providers" / "minimax.toml"
    assert minimax_path.is_file()
    minimax = toml.loads(minimax_path.read_text())

    glm = zai["models"][0]
    edge = minimax["models"][0]
    assert glm["fallbacks"] == ["minimax/MiniMax-M3.1-Flash"]
    assert edge["fallbacks"] == ["deepseek/deepseek-flash"]


def test_local_cloud_lane_uses_the_provider_model_id_behind_the_glm_alias():
    local = toml.loads(
        (PENNYD / "deploy" / "local" / "estate-cloud.toml").read_text()
    )
    model = local["models"][0]
    assert model["id"] == "zai/glm-5.3"
    assert "glm" in model["aliases"]


def test_provider_contracts_are_explicit():
    aliases: set[str] = set()
    for path in sorted((PENNYD / "providers").glob("*.toml")):
        provider = toml.loads(path.read_text())
        assert provider["id"] == path.stem
        assert provider["dialect"] in {"openai", "anthropic"}
        assert provider["base_url"].startswith(("http://", "https://"))
        assert provider["request_path"].startswith("/")
        assert provider["auth"]["kind"] in {"none", "bearer", "header", "queryparam"}
        for model in provider.get("models", []):
            assert model["id"]
            assert model["class"] in {"local", "free", "paid"}
            for alias in model.get("aliases", []):
                assert alias not in aliases, f"duplicate provider alias {alias}"
                aliases.add(alias)
