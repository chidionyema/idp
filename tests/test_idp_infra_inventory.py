"""Falsifiers for bin/idp-infra-inventory.

A gate that cannot fail is not a gate, so every finding the inventory raises has a test
that proves the tool refuses on it, and a test that proves the tool accepts the clean
case. The tests build a tiny synthetic repository and run the real tool against it: the
tool is the contract, not the helper functions behind it.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent
TOOL = REPO / "bin" / "idp-infra-inventory"


FLUX_ROW = """\
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: app
  namespace: flux-system
spec:
  path: ./platform/app
  prune: true
  sourceRef:
    kind: GitRepository
    name: flux-system
---
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: chart
  namespace: flux-system
spec:
  path: ./platform/chart
  prune: true
  sourceRef:
    kind: GitRepository
    name: flux-system
"""

APP = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
  namespace: app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: app
  template:
    metadata:
      labels:
        app: app
    spec:
      containers:
        - name: app
          image: ghcr.io/chidionyema/app:main
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
"""

CHART = """\
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: chart
  namespace: charts
spec:
  interval: 5m
  chart:
    spec:
      chart: chart
      sourceRef:
        kind: HelmRepository
        name: charts
"""

ORPHAN = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orphan
  namespace: orphan
spec:
  replicas: 1
  selector:
    matchLabels:
      app: orphan
  template:
    metadata:
      labels:
        app: orphan
    spec:
      containers:
        - name: orphan
          image: ghcr.io/chidionyema/orphan:main
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
"""


def build_repo(
    root: pathlib.Path, budget: dict, broken_app: bool = False
) -> pathlib.Path:
    (root / "clusters" / "test").mkdir(parents=True)
    (root / "clusters" / "test" / "flux.yaml").write_text(FLUX_ROW)
    (root / "platform" / "app").mkdir(parents=True)
    (root / "platform" / "app" / "kustomization.yaml").write_text(
        "resources:\n  - app.yaml\n"
    )
    (root / "platform" / "app" / "app.yaml").write_text(APP)
    (root / "platform" / "chart").mkdir(parents=True)
    (root / "platform" / "chart" / "kustomization.yaml").write_text(
        "resources:\n  - chart.yaml\n"
    )
    (root / "platform" / "chart" / "chart.yaml").write_text(CHART)
    (root / "platform" / "orphan").mkdir(parents=True)
    (root / "platform" / "orphan" / "kustomization.yaml").write_text(
        "resources:\n  - orphan.yaml\n"
    )
    (root / "platform" / "orphan" / "orphan.yaml").write_text(ORPHAN)
    if broken_app:
        (root / "platform" / "app" / "app.yaml").write_text(
            APP.replace("image: ghcr.io/chidionyema/app:main", "image: [broken")
        )
    (root / "platform" / "infra-budget.yaml").write_text(
        yaml.safe_dump(budget, sort_keys=False)
    )
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    return root


def run(root: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, IDP_ROOT=str(root))
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(root),
        timeout=120,
    )


def clean_budget() -> dict:
    return {
        "budget": {
            "node_cpu_requests_m": 3600,
            "node_memory_requests_mi": 21504,
            "node_disk_gb": 200,
            "pvc_storage_gb": 120,
        },
        "admission": [
            {
                "workload": "app/deployment/app",
                "cpu": "100m",
                "memory": "128Mi",
                "justification": "the app under test",
                "rung": "7",
            },
            {
                "workload": "charts/helmrelease/chart",
                "cpu": "200m",
                "memory": "512Mi",
                "justification": "the chart under test",
                "rung": "7",
            },
        ],
        "reserves": [
            {
                "workload": "charts/helmrelease/chart",
                "cpu": "200m",
                "memory": "512Mi",
                "basis": "an envelope, not a measurement",
            }
        ],
        "refused": [],
        "orphans": [
            {
                "path": "platform/orphan",
                "decision": "cut",
                "reason": "a dead experiment",
            },
        ],
    }


def test_a_clean_declaration_exits_zero(tmp_path):
    root = build_repo(tmp_path / "repo", clean_budget())
    out = run(root)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "ok  the declared infrastructure fits the node budget" in out.stdout


def test_an_unlisted_workload_is_refused(tmp_path):
    budget = clean_budget()
    budget["admission"] = []
    root = build_repo(tmp_path / "repo", budget)
    out = run(root)
    assert out.returncode == 1, out.stdout
    assert "neither admitted nor refused" in out.stdout


def test_an_admission_without_a_justification_is_refused(tmp_path):
    budget = clean_budget()
    budget["admission"][0].pop("justification")
    root = build_repo(tmp_path / "repo", budget)
    out = run(root)
    assert out.returncode == 1, out.stdout
    assert "no justification" in out.stdout


def test_a_declared_only_directory_without_a_decision_is_refused(tmp_path):
    budget = clean_budget()
    budget["orphans"] = []
    root = build_repo(tmp_path / "repo", budget)
    out = run(root)
    assert out.returncode == 1, out.stdout
    assert "no decision" in out.stdout or "no cut/reserved decision" in out.stdout


def test_an_over_budget_admission_is_refused(tmp_path):
    budget = clean_budget()
    budget["budget"]["node_cpu_requests_m"] = 50
    root = build_repo(tmp_path / "repo", budget)
    out = run(root)
    assert out.returncode == 1, out.stdout
    assert "over" in out.stdout.lower()


def test_a_stale_value_is_refused(tmp_path):
    budget = clean_budget()
    budget["admission"][0]["cpu"] = "500m"
    root = build_repo(tmp_path / "repo", budget)
    out = run(root)
    assert out.returncode == 1, out.stdout
    assert "drifted" in out.stdout


def test_a_chart_without_a_reserve_is_refused(tmp_path):
    budget = clean_budget()
    budget["reserves"] = []
    root = build_repo(tmp_path / "repo", budget)
    out = run(root)
    assert out.returncode == 1, out.stdout
    assert "unknown capacity is not zero capacity" in out.stdout


def test_a_refusal_without_a_destination_is_refused(tmp_path):
    budget = clean_budget()
    budget["refused"] = [
        {
            "workload": "app/deployment/app",
            "cpu": "100m",
            "memory": "128Mi",
            "reason": "it does not fit",
        }
    ]
    budget["admission"] = []
    root = build_repo(tmp_path / "repo", budget)
    out = run(root)
    assert out.returncode == 1, out.stdout
    assert "no destination" in out.stdout


def test_an_unreadable_applied_path_is_blind(tmp_path):
    root = build_repo(tmp_path / "repo", clean_budget(), broken_app=True)
    out = run(root)
    assert out.returncode == 2, out.stdout
    assert "BLIND" in out.stdout


def test_the_report_is_machine_readable(tmp_path):
    root = build_repo(tmp_path / "repo", clean_budget())
    target = tmp_path / "inventory.json"
    out = run(root, "--json", str(target))
    assert out.returncode == 0, out.stdout
    report = json.loads(target.read_text())
    assert report["totals"]["workloads"] == 2
    assert report["verdicts"]["app/deployment/app"] == "ADMITTED"
    assert report["blind"] == []
