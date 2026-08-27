"""crew#516 CP4 (2026-08-27 17:30Z receipt, oke-check 33099660334): the one worker node reported
`0/1 nodes are available: 1 Insufficient cpu` for catalogue, hindsight-api, hindsight-db, the hermes
gateway and the cluster-state / kini-state CronJob pods. Measured from the manifests the same turn:
the CPU requests this repo declares add up to 3.96 cores over 67 containers, on a fleet of one
4-OCPU node (~3.7 allocatable) — before the chart defaults of spire, chaos-mesh, kyverno,
external-secrets, keda, cert-manager and the OKE system daemonsets. Nothing failed until the pods
did. This test is the budget: what the repo declares must fit what platform/oci provisions, with
a tenth kept back for the system pods, and the two numbers come from the files that set them —
never from a literal here."""
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SYSTEM_RESERVE = 0.10  # OKE system daemonsets + kubelet, not declared in this repo


def _cores(v):
    v = str(v)
    return float(v[:-1]) / 1000 if v.endswith("m") else float(v)


def declared_cpu_requests(root=ROOT):
    """[(cores, file, path)] for every resources.requests.cpu in platform/ and clusters/ manifests
    and Helm values (HelmRelease spec.values included)."""
    rows = []

    def walk(o, path, f):
        if isinstance(o, dict):
            r = o.get("resources")
            if isinstance(r, dict) and isinstance(r.get("requests"), dict) and "cpu" in r["requests"]:
                rows.append((_cores(r["requests"]["cpu"]), f, path))
            for k, v in o.items():
                walk(v, f"{path}/{k}", f)
        elif isinstance(o, list):
            for v in o:
                walk(v, path, f)

    for d in ("platform", "clusters"):
        for f in sorted((root / d).rglob("*.y*ml")):
            try:
                docs = list(yaml.safe_load_all(f.read_text()))
            except yaml.YAMLError:
                continue
            for doc in docs:
                walk(doc, "", f.relative_to(root).as_posix())
    return rows


def fleet_ocpus(root=ROOT):
    """worker_ocpus default × node-pool size, read from platform/oci."""
    var = (root / "platform/oci/variables.tf").read_text()
    m = re.search(r'variable "worker_ocpus"\s*\{[^}]*?default\s*=\s*(\d+)', var, re.S)
    main = (root / "platform/oci/main.tf").read_text()
    n = re.search(r"^\s*size\s*=\s*(\d+)", main, re.M)
    assert m and n, "worker_ocpus default or node_pools size not found in platform/oci"
    return int(m.group(1)) * int(n.group(1))


def test_incident_crew516_the_budget_is_read_from_the_files_that_set_it():
    assert fleet_ocpus() >= 4
    rows = declared_cpu_requests()
    assert len(rows) >= 50, "the manifest walk found fewer containers than the 67 measured on 2026-08-27"
    assert any("gotk-components" in f for _, f, _ in rows)  # clusters/ is in the walk
    assert any("/spec/values" in p for _, _, p in rows)  # HelmRelease values are in the walk


def test_incident_crew516_declared_cpu_requests_fit_the_fleet():
    rows = declared_cpu_requests()
    total = sum(c for c, _, _ in rows)
    budget = fleet_ocpus() * (1 - SYSTEM_RESERVE)
    top = "\n".join(f"  {c:5.2f} {f} {p}" for c, f, p in sorted(rows, reverse=True)[:8])
    assert total <= budget, (
        f"declared CPU requests {total:.2f} cores over {len(rows)} containers exceed the fleet budget "
        f"{budget:.2f} ({fleet_ocpus()} OCPU less {SYSTEM_RESERVE:.0%} system reserve); the 17:30Z "
        f"receipt is what that looks like: Pending on 'Insufficient cpu'. Largest:\n{top}"
    )


def test_incident_crew516_a_synthetic_overspend_fails(tmp_path):
    (tmp_path / "platform/oci").mkdir(parents=True)
    (tmp_path / "clusters").mkdir()
    (tmp_path / "platform/oci/variables.tf").write_text('variable "worker_ocpus" {\n  default = 1\n}\n')
    (tmp_path / "platform/oci/main.tf").write_text("node_pools = {\n      size             = 1\n}\n")
    (tmp_path / "platform/a.yaml").write_text(
        "kind: Deployment\nspec:\n  template:\n    spec:\n      containers:\n"
        "      - name: a\n        resources:\n          requests:\n            cpu: 950m\n"
    )
    assert fleet_ocpus(tmp_path) == 1
    assert sum(c for c, _, _ in declared_cpu_requests(tmp_path)) > 1 * (1 - SYSTEM_RESERVE)
    (tmp_path / "platform/a.yaml").write_text(
        "kind: Deployment\nspec:\n  template:\n    spec:\n      containers:\n"
        "      - name: a\n        resources:\n          requests:\n            cpu: 500m\n"
    )
    assert sum(c for c, _, _ in declared_cpu_requests(tmp_path)) <= 1 * (1 - SYSTEM_RESERVE)


@pytest.mark.parametrize("v,cores", [("100m", 0.1), ("1", 1.0), ("1500m", 1.5), (2, 2.0)])
def test_incident_crew516_cpu_quantities_parse(v, cores):
    assert _cores(v) == cores
