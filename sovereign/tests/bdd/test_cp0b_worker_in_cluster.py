"""Binds features/sovereign-bus/cp0b_worker_in_cluster.feature (crew#396 step 2). Rung 1/4:
the invariants (worker on the image list, Deployment on the frontend Service, probes on the
ready file, pull secret mirrored) and one behaviour: ready exists only while polling."""
import asyncio
import subprocess
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, scenarios, then, when

scenarios("features/sovereign-bus/cp0b_worker_in_cluster.feature")
IDP = Path(__file__).resolve().parents[3]
READY = "/tmp/estate/sovereign/worker.ready"


@pytest.fixture
def state() -> dict:
    return {}


@given("bin/dockerfiles")
def _list(state: dict) -> None:
    r = subprocess.run([str(IDP / "bin/dockerfiles")], capture_output=True, text=True, check=True)
    state["rows"] = {l.split()[0]: l.split() for l in r.stdout.splitlines() if l.strip()}


@then("it lists sovereign-worker built from sovereign/sovereign-worker.Dockerfile")
def _listed(state: dict) -> None:
    assert state["rows"].get("sovereign-worker") == ["sovereign-worker", "sovereign/sovereign-worker.Dockerfile", "sovereign"], state["rows"]


@then("the Dockerfile runs python -m sovereign.engine.worker as a non-root user")
def _dockerfile() -> None:
    lines = [l.strip() for l in (IDP / "sovereign/sovereign-worker.Dockerfile").read_text().splitlines() if l.strip() and not l.startswith("#")]
    assert lines[-1] == 'CMD ["python", "-m", "sovereign.engine.worker"]', lines[-1]
    assert any(l.startswith("USER ") and l != "USER root" for l in lines), lines


@when("platform/temporal is built with kustomize")
def _build(state: dict) -> None:
    r = subprocess.run(["kubectl", "kustomize", str(IDP / "platform/temporal")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    state["docs"] = [d for d in yaml.safe_load_all(r.stdout) if d]
    state["dep"] = next(d for d in state["docs"] if d["kind"] == "Deployment" and d["metadata"]["name"] == "sovereign-worker")
    state["c"] = state["dep"]["spec"]["template"]["spec"]["containers"][0]


@then("a Deployment sovereign-worker points TEMPORAL_HOST at the chart's frontend Service")
def _host(state: dict) -> None:
    env = {e["name"]: e.get("value") for e in state["c"]["env"]}
    hr = next(d for d in state["docs"] if d["kind"] == "HelmRelease")
    assert env["TEMPORAL_HOST"] == f"{hr['metadata']['name']}-frontend.temporal.svc", env
    assert env["TEMPORAL_NAMESPACE"] in {n["name"] for n in hr["spec"]["values"]["server"]["config"]["namespaces"]["namespace"]}, env


@then("its image is ghcr.io/chidionyema/sovereign-worker on a tag the image policy rewrites")
def _image(state: dict) -> None:
    name, tag = state["c"]["image"].rsplit(":", 1)
    assert name == "ghcr.io/chidionyema/sovereign-worker" and tag != "latest", state["c"]["image"]
    kz = (IDP / "platform/temporal/kustomization.yaml").read_text()
    assert '{"$imagepolicy": "flux-system:sovereign-worker:tag"}' in kz
    ia = [d for d in yaml.safe_load_all((IDP / "platform/image-automation/sovereign-worker.yaml").read_text()) if d]
    assert {d["kind"] for d in ia} == {"ImageRepository", "ImagePolicy", "ImageUpdateAutomation"}
    assert next(d for d in ia if d["kind"] == "ImageUpdateAutomation")["spec"]["update"]["path"] == "./platform/temporal"


@then("every probe tests the ready file the worker writes only while polling")
def _probes(state: dict) -> None:
    for probe in ("startupProbe", "readinessProbe", "livenessProbe"):
        assert state["c"][probe]["exec"]["command"] == ["test", "-f", READY], (probe, state["c"].get(probe))
    env = {e["name"]: e.get("value") for e in state["c"]["env"]}
    assert READY.startswith(env["ESTATE_HOME"] + "/sovereign/"), env


@then("the namespace mirrors ghcr-pull through the ghcr-pull ClusterSecretStore")
def _pull(state: dict) -> None:
    es = next(d for d in state["docs"] if d["kind"] == "ExternalSecret" and d["metadata"]["name"] == "ghcr-pull")
    assert es["spec"]["secretStoreRef"] == {"kind": "ClusterSecretStore", "name": "ghcr-pull"}, es["spec"]
    assert es["spec"]["target"]["template"]["type"] == "kubernetes.io/dockerconfigjson"
    assert {p["name"] for p in state["dep"]["spec"]["template"]["spec"]["imagePullSecrets"]} == {"ghcr-pull"}
    store = [d for d in yaml.safe_load_all((IDP / "platform/image-automation/pull-secret.yaml").read_text())
             if d and d["kind"] == "ClusterSecretStore"]
    assert store and store[0]["spec"]["provider"]["kubernetes"]["remoteNamespace"] == "backstage", store


@given("a worker connected to a fake frontend")
def _fake(state: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from sovereign import config
    from sovereign.engine import worker as worker_mod

    home = tmp_path / "sovereign"
    monkeypatch.setattr(config, "SOVEREIGN_HOME", home)
    monkeypatch.setattr(config, "ESTATE_HOME", tmp_path)
    monkeypatch.setattr(config, "ESTATE_ALERT_INBOX", tmp_path / "inbox" / "alerts")
    seen: dict = {}

    class FakeWorker:
        def __init__(self, *a, **k) -> None:
            pass

        async def __aenter__(self):
            seen["in"] = (home / "worker.ready").exists()
            return self

        async def __aexit__(self, *a):
            return None

    class FakeClient:
        @staticmethod
        async def connect(*a, **k):
            return object()

    monkeypatch.setattr(worker_mod, "Worker", FakeWorker)
    monkeypatch.setattr(worker_mod, "Client", FakeClient)

    async def run() -> None:
        task = asyncio.create_task(worker_mod.run_worker())
        for _ in range(200):
            await asyncio.sleep(0.01)
            if (home / "worker.ready").exists():
                break
        seen["while_polling"] = (home / "worker.ready").read_text() if (home / "worker.ready").exists() else None
        import os
        import signal
        os.kill(os.getpid(), signal.SIGTERM)
        await asyncio.wait_for(task, 5)
        seen["after"] = (home / "worker.ready").exists()

    asyncio.run(run())
    state["seen"] = seen


@then("worker.ready appears after the Worker starts and is gone after it stops")
def _ready(state: dict) -> None:
    s = state["seen"]
    assert s["in"] is False and s["while_polling"] and s["after"] is False, s
