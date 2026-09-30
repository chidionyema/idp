"""Binds features/sovereign-bus/cp0_temporal_in_cluster.feature (crew#396 step 1). Rung 1/4:
the invariants a redesign keeps (chart pinned, hooks off, one Postgres, nothing bundled)."""

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, scenarios, then, when

scenarios("features/sovereign-bus/cp0_temporal_in_cluster.feature")
IDP = Path(__file__).resolve().parents[3]


@pytest.fixture
def state() -> dict:
    return {}


@given("the Flux row temporal in clusters/oke/platform.yaml")
def _row(state: dict) -> None:
    docs = [
        d
        for d in yaml.safe_load_all((IDP / "clusters/oke/platform.yaml").read_text())
        if d
    ]
    row = next(
        d
        for d in docs
        if d["kind"] == "Kustomization" and d["metadata"]["name"] == "temporal"
    )
    assert (
        row["spec"]["path"] == "./platform/temporal" and row["spec"]["prune"] is True
    ), row


@when("platform/temporal is built with kustomize")
def _build(state: dict) -> None:
    r = subprocess.run(
        ["kubectl", "kustomize", str(IDP / "platform/temporal")],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    state["docs"] = [d for d in yaml.safe_load_all(r.stdout) if d]
    state["hr"] = next(d for d in state["docs"] if d["kind"] == "HelmRelease")


@then(
    "the HelmRelease uses chart temporal from https://go.temporal.io/helm-charts at a pinned version"
)
def _pinned(state: dict) -> None:
    spec = state["hr"]["spec"]["chart"]["spec"]
    repo = next(d for d in state["docs"] if d["kind"] == "HelmRepository")
    assert spec["chart"] == "temporal" and spec["version"].count(".") == 2, spec
    assert repo["spec"]["url"] == "https://go.temporal.io/helm-charts", repo


@then("Helm hooks are off so Flux owns the schema and namespace jobs")
def _hooks(state: dict) -> None:
    v = state["hr"]["spec"]["values"]
    assert v["schema"]["useHelmHooks"] is False
    assert v["server"]["config"]["namespaces"]["useHelmHooks"] is False


@then(
    "both persistence stores point at the estate database with a password from the vault Secret"
)
def _stores(state: dict) -> None:
    ds = state["hr"]["spec"]["values"]["server"]["config"]["persistence"]["datastores"]
    es = next(
        d
        for d in state["docs"]
        if d["kind"] == "ExternalSecret" and d["metadata"]["name"] == "temporal-db"
    )
    for name in ("default", "visibility"):
        sql = ds[name]["sql"]
        # There is one Postgres in the estate; this row no longer carries a server of its own.
        assert sql["connectAddr"] == "estate-rw.estate-db.svc.cluster.local:5432", sql
        assert sql["existingSecret"] == es["spec"]["target"]["name"], (sql, es)
        assert "password" not in sql, "a password literal in values (LAW 21)"


@then("every bundled store and metrics stack is disabled")
def _bundled(state: dict) -> None:
    v = state["hr"]["spec"]["values"]
    for k in (
        "cassandra",
        "mysql",
        "postgresql",
        "elasticsearch",
        "prometheus",
        "grafana",
    ):
        assert k not in v, (
            f"{k}: chart 1.x refuses the removed sub-chart key (templates/validations.yaml)"
        )
    ds = v["server"]["config"]["persistence"]["datastores"]
    assert set(ds) == {"default", "visibility"} and all(
        "sql" in ds[k] and "elasticsearch" not in ds[k] for k in ds
    ), ds
    assert v["admintools"]["enabled"] is False
    # crew#396: the node runtime enforces short-name mode, so every chart image names its registry
    for k in ("admintools", "web", "server"):
        assert v[k]["image"]["repository"].startswith("docker.io/temporalio/"), k


@given("the launchd template for the Temporal server")
def _plist(state: dict) -> None:
    state["path"] = IDP / "launchd/ai.estate.temporal.plist.tmpl"


@then("it is gone and bin/idp-install-launchd says why")
def _retired(state: dict) -> None:
    assert not state["path"].exists(), "the Mac still owns the engine (crew#396)"
    assert "crew#396" in (IDP / "bin/idp-install-launchd").read_text()


@given("the chart rendered with the HelmRelease values")
def _render(state: dict, tmp_path: Path) -> None:
    for tool in ("helm", "kyverno", "kubectl"):
        if not shutil.which(tool):
            pytest.skip(
                f"{tool} is not installed; the bdd job installs kyverno and kubectl, helm renders the chart"
            )
    r = subprocess.run(
        ["kubectl", "kustomize", str(IDP / "platform/temporal")],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    ours = [d for d in yaml.safe_load_all(r.stdout) if d]
    hr = next(d for d in ours if d["kind"] == "HelmRelease")
    repo = next(d for d in ours if d["kind"] == "HelmRepository")
    values = tmp_path / "values.yaml"
    values.write_text(yaml.safe_dump(hr["spec"]["values"]))
    spec = hr["spec"]["chart"]["spec"]
    h = subprocess.run(
        [
            "helm",
            "template",
            "temporal",
            spec["chart"],
            "--repo",
            repo["spec"]["url"],
            "--version",
            spec["version"],
            "-n",
            "temporal",
            "-f",
            str(values),
        ],
        capture_output=True,
        text=True,
    )
    assert h.returncode == 0, h.stderr[:600]
    # helm-test hooks (the cluster-health Pod) are never applied by Flux (HelmRelease spec.test is off).
    rendered = [
        d
        for d in yaml.safe_load_all(h.stdout)
        if d
        and "test"
        not in (d.get("metadata", {}).get("annotations") or {}).get("helm.sh/hook", "")
    ] + ours
    for d in rendered:
        d.setdefault("metadata", {}).setdefault("namespace", "temporal")
    (tmp_path / "objects.yaml").write_text(
        yaml.safe_dump_all([d for d in rendered if d["kind"] != "PolicyException"])
    )
    # The exceptions live in platform/edge (namespace kyverno is the only one Kyverno reads, crew#325);
    # platform/temporal's kustomization would stamp `namespace: temporal` on them.
    exceptions = [
        d
        for d in yaml.safe_load_all(
            (IDP / "platform/edge/temporal-exception.yaml").read_text()
        )
        if d
    ]
    assert exceptions and all(
        d["metadata"]["namespace"] == "kyverno" for d in exceptions
    ), exceptions
    (tmp_path / "exceptions.yaml").write_text(yaml.safe_dump_all(exceptions))
    pol = subprocess.run(
        ["kubectl", "kustomize", str(IDP / "tests/fixtures/kyverno/upstream")],
        capture_output=True,
        text=True,
    )
    assert pol.returncode == 0, pol.stderr
    (tmp_path / "policies.yaml").write_text(pol.stdout)
    state["dir"] = tmp_path


@when("Kyverno judges every rendered object with the two scoped exceptions")
def _judge(state: dict) -> None:
    d = state["dir"]
    out = subprocess.run(
        [
            "kyverno",
            "apply",
            str(d / "policies.yaml"),
            "--resource",
            str(d / "objects.yaml"),
            "--exception",
            str(d / "exceptions.yaml"),
        ],
        capture_output=True,
        text=True,
    )
    state["out"] = out.stdout + out.stderr


@then("nothing fails")
def _clean(state: dict) -> None:
    failed = [
        l
        for l in state["out"].splitlines()
        if l.startswith("policy ") and "failed" in l
    ]
    assert not failed, "\n".join(failed[:12])
    assert "fail: 0" in state["out"].replace(",", ""), state["out"][-300:]
