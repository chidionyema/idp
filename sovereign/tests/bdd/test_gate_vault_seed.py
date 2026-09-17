"""Binds features/drills/vault-seed.feature (crew#284, crew#248)."""

import re
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, scenarios, then

scenarios("features/drills/vault-seed.feature")

IDP = Path(__file__).resolve().parents[3]
WF = IDP / ".github" / "workflows" / "vault-seed.yml"


@pytest.fixture
def state() -> dict:
    return {}


@given(".github/workflows/vault-seed.yml")
def _wf(state: dict) -> None:
    assert WF.is_file()
    doc = yaml.safe_load(WF.read_text())
    step = next(
        s for s in doc["jobs"]["seed"]["steps"] if "idp-vault-put" in s.get("name", "")
    )
    state.update(doc=doc, step=step, run=step["run"])


@then("every KEY=KEY pair passed to bin/idp-vault-put has a SEED_KEY in the step's env")
def _keys(state: dict) -> None:
    needed = set(re.findall(r"\b([A-Z0-9_]+)=\1\b", state["run"])) | set(
        re.findall(
            r"\b[a-z_0-9]+=((?:GITHUB_APP|FLUX_WRITER|TEMPORAL_DB)_[A-Z0-9_]+)",
            state["run"],
        )
    )
    assert needed, "no KEY=KEY pairs found"
    missing = {k for k in needed if f"SEED_{k}" not in state["step"]["env"]}
    assert not missing, f"no SEED_ secret for {sorted(missing)}"


@then(
    "the workflow is dispatch-only with entries all, prospector-engine-env, github-app, flux-writer, temporal-db and mcp-gateway"
)
def _dispatch(state: dict) -> None:
    on = (
        state["doc"][True] if True in state["doc"] else state["doc"]["on"]
    )  # yaml parses `on:` as True
    assert list(on) == ["workflow_dispatch"]
    assert on["workflow_dispatch"]["inputs"]["entry"]["options"] == [
        "all",
        "prospector-engine-env",
        "github-app",
        "flux-writer",
        "temporal-db",
        "mcp-gateway",
        "hindsight",
        "k8sgpt",
        "holmes",
        "tailscale-operator",
        "laptop",
        "hermes",
        "science",
        "router-rows",
    ]


@then(
    "the run step never echoes, prints or cats the seed env file and removes it at the end"
)
def _silent(state: dict) -> None:
    run = state["run"]
    assert not re.search(r"\b(echo|cat|printf)\b[^\n]*ESTATE_ENV_FILE", run)
    assert run.rstrip().splitlines()[-1].strip() == 'rm -f "$ESTATE_ENV_FILE"'


@given("clusters/oke/platform.yaml and clusters/oke/image-automation.yaml")
def _clusters(state: dict) -> None:
    assert (IDP / "clusters" / "oke" / "platform.yaml").is_file()


@then(
    "the git-writer ExternalSecret is a resource of platform/image-automation, not platform/secret-store"
)
def _relocated() -> None:
    ia = yaml.safe_load(
        (IDP / "platform" / "image-automation" / "kustomization.yaml").read_text()
    )["resources"]
    ss = yaml.safe_load(
        (IDP / "platform" / "secret-store" / "kustomization.yaml").read_text()
    )["resources"]
    assert "github-app.yaml" not in ss and "flux-writer.yaml" in ia
    assert (IDP / "platform" / "image-automation" / "flux-writer.yaml").is_file()


@given("clusters/oke/secrets.yaml")
def _secrets(state: dict) -> None:
    assert (IDP / "clusters" / "oke" / "secrets.yaml").is_file()


@then("platform/secret-store has no ExternalSecret; every consumer owns its own")
def _store_only() -> None:
    d = IDP / "platform" / "secret-store"
    res = yaml.safe_load((d / "kustomization.yaml").read_text())["resources"]
    kinds = {
        doc["kind"]
        for r in res
        for doc in yaml.safe_load_all((d / r).read_text())
        if doc
    }
    assert "ExternalSecret" not in kinds, kinds
    assert (IDP / "platform" / "alerts-secret" / "flux-telegram.yaml").is_file()
