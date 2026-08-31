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
FLUX = ROOT / "clusters" / "oke" / "platform.yaml"
ESTATE_CODE = Path(os.environ.get("ESTATE_CODE", ROOT.parent))
POLICIES = ESTATE_CODE / "prospector-main" / "deploy" / "k8s" / "policies"


def _docs(path: Path) -> list[dict]:
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def _one(docs: list[dict], kind: str, name: str) -> dict:
    return next(d for d in docs if d["kind"] == kind and d["metadata"]["name"] == name)


# The router's opt-in, the watcher's namespace list and reloadOnCreate were graded here, by name,
# until 2026-08-31. Naming litellm and the Secret it lists is the O(n) shape the founder's blueprint
# refuses (c08d08d9.md), and the namespace list it asserted is the thing that made three annotations
# inert in crew#684. All three properties are now graded once, over every workload, in
# tests/test_incident_crew684_every_workload_restarts_when_its_config_changes.py.
# What stays here is what is genuinely about this row: Flux's ordering, and the chart rendering
# clean against the estate policy set.


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
