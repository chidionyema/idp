"""Incident crew#506 CP4 (2026-08-27): a rotated upstream key never reached the router.

GROQ_API_KEY was merged into the vault entry `litellm-upstream` (oke-check 33082342968), ESO
refreshed the Secret, `/v1/models` listed `groq`, and a completion still answered
`Invalid API Key`: the router exports its keys once at start (platform/llm/litellm.yaml command)
and nothing restarted it. Rung 4, both ways: main has no Reloader row and no opt-in annotation,
so every test here fails on main; with the row, the chart passes the estate policy set clean.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
ROW = ROOT / "platform" / "reloader" / "reloader.yaml"
LITELLM = ROOT / "platform" / "llm" / "litellm.yaml"
EXTERNAL_SECRET = ROOT / "platform" / "llm" / "external-secret.yaml"
FLUX = ROOT / "clusters" / "oke" / "platform.yaml"
ESTATE_CODE = Path(os.environ.get("ESTATE_CODE", ROOT.parent))
POLICIES = ESTATE_CODE / "prospector-main" / "deploy" / "k8s" / "policies"


def _docs(path: Path) -> list[dict]:
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def _one(docs: list[dict], kind: str, name: str) -> dict:
    return next(d for d in docs if d["kind"] == kind and d["metadata"]["name"] == name)


def test_router_opts_in_to_a_restart_on_its_upstream_secret() -> None:
    dep = _one(_docs(LITELLM), "Deployment", "litellm")
    target = _one(_docs(EXTERNAL_SECRET), "ExternalSecret", "litellm-upstream")["spec"]["target"]["name"]
    ann = dep["metadata"].get("annotations", {})
    assert ann.get("secret.reloader.stakater.com/reload") == target, (
        f"litellm Deployment must name the Secret {target!r} in secret.reloader.stakater.com/reload; got {ann}")


def test_reloader_row_watches_the_router_namespace_and_only_opted_in_workloads() -> None:
    hr = _one(_docs(ROW), "HelmRelease", "reloader")
    values = hr["spec"]["values"]["reloader"]
    assert values["autoReloadAll"] is False, "a rotation must never roll a workload that did not opt in"
    assert values["watchGlobally"] is False and "llm" in values["namespaces"], values
    assert re.fullmatch(r"\d+\.\d+\.\d+", str(hr["spec"]["chart"]["spec"]["version"])), "chart is pinned"


def test_a_secret_that_predates_reloader_still_rolls_its_workload() -> None:
    """Incident 2026-08-27 15:12Z: #414 applied, GROQ_API_KEY already in the Secret, router still
    `Invalid API Key` -- no update event ever came. reloadOnCreate is the chart's knob for that."""
    values = _one(_docs(ROW), "HelmRelease", "reloader")["spec"]["values"]["reloader"]
    assert values["reloadOnCreate"] is True


def test_flux_applies_the_reloader_row_after_the_secret_store_and_waits_on_it() -> None:
    ks = _one(_docs(FLUX), "Kustomization", "reloader")
    spec = ks["spec"]
    assert spec["path"] == "./platform/reloader" and spec["wait"] is True
    assert {"name": "secret-store"} in spec["dependsOn"], spec["dependsOn"]
    assert any(h["kind"] == "Deployment" and h["name"] == "reloader" for h in spec["healthChecks"])


def test_rendered_chart_passes_the_estate_policy_set_without_an_exception(tmp_path) -> None:
    for tool in ("kyverno", "helm", "kubectl"):
        if not shutil.which(tool):
            pytest.skip(f"BLIND: {tool} not on PATH")
    if not POLICIES.is_dir():
        pytest.skip(f"BLIND: policy set not at {POLICIES}")
    docs = _docs(ROW)
    hr = _one(docs, "HelmRelease", "reloader")
    repo = _one(docs, "HelmRepository", hr["spec"]["chart"]["spec"]["sourceRef"]["name"])
    values = tmp_path / "values.yaml"
    values.write_text(yaml.safe_dump(hr["spec"]["values"]))
    spec = hr["spec"]["chart"]["spec"]
    r = subprocess.run(["helm", "template", "reloader", spec["chart"], "--repo", repo["spec"]["url"],
                        "--version", str(spec["version"]), "-n", hr["metadata"]["namespace"], "-f", str(values)],
                       capture_output=True, text=True)
    if r.returncode:
        pytest.skip(f"BLIND: helm template failed (offline?): {r.stderr[-300:]}")
    rendered = tmp_path / "reloader.yaml"
    rendered.write_text(r.stdout)
    policies = tmp_path / "policies.yaml"
    policies.write_text(subprocess.run(["kubectl", "kustomize", str(POLICIES)], check=True,
                                       capture_output=True, text=True).stdout)
    out = subprocess.run(["kyverno", "apply", str(policies), "--resource", str(rendered)],
                         capture_output=True, text=True).stdout
    summary = [line for line in out.splitlines() if line.startswith("pass:")]
    assert summary, out
    counts = {k.strip(): int(v) for k, v in (kv.split(": ") for kv in summary[-1].split(","))}
    failing = set(re.findall(r"policy ([a-z0-9-]+) -> resource \S+ failed", out))
    assert counts["fail"] == 0 and not failing, f"policy failures {sorted(failing)}: {out[-600:]}"
