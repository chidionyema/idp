"""Incident crew#483 (run 33160603986, 2026-08-28 09:44-09:45Z): the k8s-infra HelmRelease's
otelCollectorEndpoint value (signoz-otel-collector.observability.svc:4317, the OTLP-gRPC port
with no scheme) was fed verbatim into OTEL_EXPORTER_OTLP_ENDPOINT and taken verbatim by the
chart's otlphttp exporter (templates/_config.tpl:327 `endpoint: ${env:OTEL_EXPORTER_OTLP_ENDPOINT}`;
presets.otlphttpExporter.enabled defaults true and presets.otlpExporter.enabled defaults false --
`helm show values signoz/k8s-infra --version 0.17.0`, 2026-08-28). Every export from both
k8s-infra components then failed: 'failed to make an HTTP request: Post
"signoz-otel-collector.observability.svc:4317/v1/metrics": unsupported protocol scheme
"signoz-otel-collector.observability.svc"' -- ClickHouse saw logs=0 metrics=0 for the same 15
minutes traces=272 kept landing, because the workloads that already emit traces
(litellm, agentgateway, estate-mcp, github-mcp) use the working form: http://...:4318.

Rule (read-only, no sockets, no cluster access): any OTLP endpoint declared under platform/ --
a HelmRelease's spec.values.otelCollectorEndpoint, or a Deployment container's
OTEL_EXPORTER_OTLP_ENDPOINT env value -- that targets the collector's HTTP port 4318 must carry
an http(s):// scheme, and no HelmRelease whose otlphttp exporter is on (the signoz k8s-infra
chart default, unless explicitly disabled) may point that endpoint at the bare gRPC port 4317."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "platform"


def _yaml_docs(path: Path):
    for doc in yaml.safe_load_all(path.read_text()):
        if doc:
            yield doc


def _helmrelease_otel_endpoints():
    """(file, endpoint, otlphttp_enabled) for every HelmRelease under platform/ that sets
    spec.values.otelCollectorEndpoint. otlphttp_enabled follows the signoz k8s-infra chart's own
    default (presets.otlphttpExporter.enabled: true, presets.otlpExporter.enabled: false)
    unless the release's own values explicitly override it."""
    out = []
    for f in sorted(PLATFORM.rglob("*.yaml")):
        if "otelCollectorEndpoint" not in f.read_text():
            continue
        for doc in _yaml_docs(f):
            if doc.get("kind") != "HelmRelease":
                continue
            values = (doc.get("spec") or {}).get("values") or {}
            endpoint = values.get("otelCollectorEndpoint")
            if not endpoint:
                continue
            presets = values.get("presets") or {}
            otlphttp_enabled = ((presets.get("otlphttpExporter") or {}).get("enabled", True))
            out.append((f, endpoint, otlphttp_enabled))
    return out


def _deployment_otlp_env_endpoints():
    """(file, container-name, endpoint) for every container env entry named
    OTEL_EXPORTER_OTLP_ENDPOINT under a Deployment in platform/."""
    out = []
    for f in sorted(PLATFORM.rglob("*.yaml")):
        if "OTEL_EXPORTER_OTLP_ENDPOINT" not in f.read_text():
            continue
        for doc in _yaml_docs(f):
            if doc.get("kind") != "Deployment":
                continue
            containers = (((doc.get("spec") or {}).get("template") or {}).get("spec") or {}).get("containers") or []
            for c in containers:
                for env in c.get("env") or []:
                    if env.get("name") == "OTEL_EXPORTER_OTLP_ENDPOINT":
                        out.append((f, c.get("name"), env.get("value")))
    return out


def test_helmrelease_otel_endpoints_exist() -> None:
    # proves the scan isn't green by vacuity -- a future rename that drops otelCollectorEndpoint
    # from every platform/ file would otherwise leave every check below trivially passing.
    assert _helmrelease_otel_endpoints(), "no HelmRelease under platform/ declares spec.values.otelCollectorEndpoint"


def test_deployment_otlp_env_endpoints_exist() -> None:
    assert _deployment_otlp_env_endpoints(), "no Deployment under platform/ sets OTEL_EXPORTER_OTLP_ENDPOINT"


def test_4318_endpoints_carry_an_http_scheme() -> None:
    bad = []
    for f, endpoint, _ in _helmrelease_otel_endpoints():
        if ":4318" in endpoint and not endpoint.startswith(("http://", "https://")):
            bad.append(f"{f}: otelCollectorEndpoint={endpoint!r}")
    for f, name, endpoint in _deployment_otlp_env_endpoints():
        if endpoint and ":4318" in endpoint and not endpoint.startswith(("http://", "https://")):
            bad.append(f"{f} ({name}): OTEL_EXPORTER_OTLP_ENDPOINT={endpoint!r}")
    assert not bad, (
        "port 4318 is the collector's HTTP receiver; without http(s):// the otlphttp exporter "
        "rejects every request with 'unsupported protocol scheme':\n" + "\n".join(bad)
    )


def test_no_helmrelease_pairs_the_otlphttp_exporter_with_a_bare_grpc_port() -> None:
    # crew#483's exact regression shape: otlphttp exporter on (chart default) and
    # otelCollectorEndpoint left at the bare gRPC host:port with no scheme -- the chart takes it
    # verbatim (templates/_config.tpl:327) and every export then fails.
    bad = []
    for f, endpoint, otlphttp_enabled in _helmrelease_otel_endpoints():
        if not otlphttp_enabled:
            continue
        has_scheme = endpoint.startswith(("http://", "https://"))
        if not has_scheme:
            bad.append(f"{f}: otelCollectorEndpoint={endpoint!r} (otlphttp exporter needs http(s)://)")
        elif ":4317" in endpoint:
            bad.append(f"{f}: otelCollectorEndpoint={endpoint!r} (4317 is the gRPC port, not the HTTP one)")
    assert not bad, "\n".join(bad)


def test_k8s_infra_endpoint_is_the_working_http_form() -> None:
    # pins the exact fixed value so a future edit that regresses the scheme or the port is caught
    # by name, not only by the generic scan above.
    f, endpoint, otlphttp_enabled = next(
        (f, e, o) for f, e, o in _helmrelease_otel_endpoints() if f.name == "k8s-infra.yaml"
    )
    assert otlphttp_enabled is True
    assert endpoint == "http://signoz-otel-collector.observability.svc:4318", endpoint
