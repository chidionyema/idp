"""crew#740: the founder asked at the start of the cloud migration for one inventory of everything
the estate runs that can never be out of sync, and on 2026-08-31 the sessions could not say
whether LiteLLM was in the estate. The blueprint (his doc 2026-08-31T11:55Z): read the control
planes, never git; four verdicts; a plane that cannot be read is UNKNOWN, never a green zero.

These pin the shape without a cloud: the grader on a cluster dump on disk, the four verdicts and
no fifth, the read-only workflow with its cron on the drill catalogue, and the query files the
SaaS planes run. Proved red first: a dump with an undeclared Deployment reads ORPHAN, a
Kustomization whose inventory names a missing object reads GHOST, a not-Ready one DRIFTED."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "bin/idp-inventory"
WORKFLOW = ROOT / ".github/workflows/estate-inventory.yml"
FIXTURE = ROOT / "tests/fixtures/inventory-kube-dump.json"


def grade(tmp_path: Path, fixture: Path = FIXTURE) -> dict:
    p = subprocess.run(
        [sys.executable, str(TOOL), "--fixture", str(fixture), "--out", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert p.returncode == 0, p.stdout + p.stderr
    return json.loads((tmp_path / "inventory.json").read_text())


def by_id(doc: dict) -> dict:
    return {r["id"]: r for r in doc["rows"]}


def test_the_four_verdicts_come_from_the_dump_and_nothing_is_a_fifth(tmp_path):
    doc = grade(tmp_path)
    rows = by_id(doc)
    assert rows["llm/Deployment/litellm"]["verdict"] == "MANAGED"
    assert (
        rows["llm/Deployment/litellm"]["declared_in"] == "Kustomization flux-system/llm"
    )
    assert rows["llm/Deployment/by-hand"]["verdict"] == "ORPHAN"
    assert rows["llm/Deployment/gone"]["verdict"] == "GHOST"
    assert rows["flux-system/Kustomization/tailscale"]["verdict"] == "DRIFTED"
    assert (
        rows["observability/Service/signoz"]["declared_in"]
        == "HelmRelease observability/signoz"
    )
    assert rows["tools/Deployment/plain-helm"]["verdict"] == "ORPHAN"
    assert rows["kube-system/ConfigMap/coredns"]["verdict"] == "MANAGED"
    assert {r["verdict"] for r in doc["rows"]} <= {
        "MANAGED",
        "DRIFTED",
        "ORPHAN",
        "GHOST",
    }


def test_cluster_noise_is_not_an_orphan(tmp_path):
    """A ReplicaSet, the root CA ConfigMap and a Helm release Secret are made by the cluster for
    something declared; listing them ORPHAN is the noise a reviewer stops reading."""
    ids = set(by_id(grade(tmp_path)))
    assert "llm/ReplicaSet/litellm-abc" not in ids
    assert "llm/ConfigMap/kube-root-ca.crt" not in ids
    assert "llm/Secret/sh.helm.release.v1.x" not in ids


def test_the_table_lists_every_red_row_and_the_counts(tmp_path):
    doc = grade(tmp_path)
    table = (tmp_path / "inventory.md").read_text()
    assert "| kubernetes | " in table
    for rid in (
        "llm/Deployment/by-hand",
        "llm/Deployment/gone",
        "flux-system/Kustomization/tailscale",
    ):
        assert rid in table
    c = doc["counts"]["kubernetes"]
    assert (c["MANAGED"], c["DRIFTED"], c["ORPHAN"], c["GHOST"]) == (4, 1, 2, 1)


def test_strict_is_the_red_gate_and_audit_mode_is_not(tmp_path):
    p = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--fixture",
            str(FIXTURE),
            "--out",
            str(tmp_path),
            "--strict",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert p.returncode == 1 and "not MANAGED" in p.stdout


def test_nothing_in_the_tool_lists_git_to_decide_what_exists():
    """The blueprint's first law: inventory from the control planes, never from git. The only git
    read is the Mac plane's 'is this plist tracked' on the declared side."""
    text = TOOL.read_text()
    assert "git ls-files" not in text.replace(
        '["git", "-C", str(repo), "ls-files"]', ""
    )
    assert "glob(" not in text.replace('QUERIES.glob(f"{plane}-*.sql")', "")


def test_every_saas_plane_has_a_query_file_that_names_type_id_and_name():
    q = ROOT / "platform/inventory/queries"
    for plane in ("github", "cloudflare", "tailscale"):
        files = sorted(q.glob(f"{plane}-*.sql"))
        assert files, plane
        for f in files:
            sql = f.read_text().lower()
            assert (
                " as type" in sql
                and re.search(r"\bid\b", sql)
                and re.search(r"\bname\b", sql)
            ), f


def test_the_workflow_is_read_only_scheduled_and_on_the_drill_catalogue():
    wf = yaml.safe_load(WORKFLOW.read_text())
    on = wf.get(True) or wf.get("on")
    cron = on["schedule"][0]["cron"]
    rows = yaml.safe_load((ROOT / "drills/catalogue.yaml").read_text())["drills"]
    row = next(r for r in rows if r["workflow"] == "estate-inventory.yml")
    assert row["schedule"] == cron and row["owner"]
    assert wf["permissions"]["contents"] == "read"
    text = WORKFLOW.read_text()
    assert "--strict" not in text, "audit mode until E1 flips the red gate on"
    assert "tofu apply" not in text and "kubectl apply" not in text
    assert re.search(r"steampipe-action-setup@[0-9a-f]{40}", text)
