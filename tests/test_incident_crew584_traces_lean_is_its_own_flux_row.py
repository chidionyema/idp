"""crew#584 (founder 2026-08-29): the self-service options must allocate infrastructure, not just
flip a flag. traces/lean was `needs-split` because the node agent and the ClickHouse store shared
one Flux row, so a lean estate could not have the collector without paying for the store. Now the
collector is its own row and the register can select the tier."""
import pathlib
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _docs(p):
    return [d for d in yaml.safe_load_all(p.read_text()) if d]


def _rows():
    return {d["metadata"]["name"]: d for d in _docs(ROOT / "clusters/oke/platform.yaml") if d.get("kind") == "Kustomization"}


def test_the_collector_is_its_own_flux_row_and_needs_no_store():
    rows = _rows()
    col = rows["observability-collector"]
    assert col["spec"]["path"] == "./platform/observability-collector"
    assert "observability" not in [d["name"] for d in col["spec"]["dependsOn"]], "lean must stand without the store"
    kust = yaml.safe_load((ROOT / "platform/observability-collector/kustomization.yaml").read_text())
    assert set(kust["resources"]) == {"helmrepository.yaml", "k8s-infra.yaml"}
    assert not (ROOT / "platform/observability/k8s-infra.yaml").exists(), "k8s-infra must live in one row"


def test_the_store_row_waits_for_the_collector_so_the_handoff_relabels_before_prune():
    rows = _rows()
    assert "observability-collector" in [d["name"] for d in rows["observability"]["spec"]["dependsOn"]]


def test_each_row_owns_a_chart_source_in_its_own_namespace():
    col = next(d for d in _docs(ROOT / "platform/observability-collector/helmrepository.yaml") if d["kind"] == "HelmRepository")
    store = next(d for d in _docs(ROOT / "platform/observability/helmrepository.yaml") if d["kind"] == "HelmRepository")
    kust = yaml.safe_load((ROOT / "platform/observability-collector/kustomization.yaml").read_text())
    assert kust["namespace"] == "observability-agent"
    assert col["spec"]["url"] == store["spec"]["url"]
    hr = next(d for d in _docs(ROOT / "platform/observability-collector/k8s-infra.yaml") if d["kind"] == "HelmRelease")
    assert hr["metadata"]["namespace"] == "observability-agent"
    assert hr["spec"]["chart"]["spec"]["sourceRef"]["name"] == col["metadata"]["name"]


def test_the_register_can_select_traces_lean_now():
    reg = yaml.safe_load((ROOT / "platform/features/features.yaml").read_text())
    feat = next(f for f in reg["features"] if f["name"] == "traces")
    lean = next(t for t in feat["tiers"] if t["name"] == "lean")
    assert lean.get("status") in (None, "on", "trial"), lean
    assert lean["switches"] == ["observability-collector"]
