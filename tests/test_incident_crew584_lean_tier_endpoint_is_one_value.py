"""crew#584 traces/lean, follow-up to idp#702: a lean estate installs the node agent and no store,
so the agent's destination must be one value the estate sets, never a literal in a platform file.
The value lives in clusters/oke/estate-config.yaml (LAW 46) and reaches the HelmRelease by Flux
postBuild on the observability-collector row."""
import json
import pathlib
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _docs(p):
    return [d for d in yaml.safe_load_all(p.read_text()) if d]


def test_the_agent_takes_its_endpoint_from_estate_config():
    hr = next(d for d in _docs(ROOT / "platform/observability-collector/k8s-infra.yaml") if d["kind"] == "HelmRelease")
    assert hr["spec"]["values"]["otelCollectorEndpoint"] == "${OTLP_ENDPOINT}"
    cfg = next(d for d in _docs(ROOT / "clusters/oke/estate-config.yaml") if d["kind"] == "ConfigMap")
    value = cfg["data"]["OTLP_ENDPOINT"]
    assert value.startswith(("http://", "https://")) and ":4317" not in value, value


def test_the_collector_row_substitutes_from_estate_config():
    rows = {d["metadata"]["name"]: d for d in _docs(ROOT / "clusters/oke/platform.yaml") if d.get("kind") == "Kustomization"}
    subs = rows["observability-collector"]["spec"]["postBuild"]["substituteFrom"]
    assert {"kind": "ConfigMap", "name": "estate-config"} in subs, subs


def test_no_platform_file_names_the_store_endpoint_for_the_agent():
    """The literal may only appear in estate-config; a platform file that names it again is the
    lean tier silently pinned to a store it does not install."""
    hits = [p for p in (ROOT / "platform/observability-collector").rglob("*.yaml")
            if "signoz-otel-collector.observability.svc" in json.dumps(_docs(p))]  # values, not comments
    assert hits == [], hits
