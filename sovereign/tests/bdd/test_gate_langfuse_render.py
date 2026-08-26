"""Binds features/gates/langfuse-traces.feature (crew#286 CP6, crew#297). The step runs
bin/idp-kyverno-render platform/observability for real: helm template plus the HelmRelease's
postRenderers, judged by the Kyverno CLI against the cluster's ClusterPolicies."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, scenarios, then, when

scenarios("features/gates/langfuse-traces.feature")

IDP = Path(__file__).resolve().parents[3]
OBS = IDP / "platform" / "observability"


@pytest.fixture
def state() -> dict:
    return {}


@given("platform/observability carries the langfuse HelmRelease and its values")
def _release(state: dict) -> None:
    docs = [d for d in yaml.safe_load_all((OBS / "langfuse.yaml").read_text()) if isinstance(d, dict)]
    hr = [d for d in docs if d.get("kind") == "HelmRelease" and d["metadata"]["name"] == "langfuse"]
    spec = hr[0]["spec"] if hr else {}
    assert spec.get("values") or spec.get("valuesFrom"), "no langfuse HelmRelease with values or valuesFrom"


@when("bin/idp-kyverno-render platform/observability runs")
def _render(state: dict) -> None:
    for tool in ("helm", "kyverno"):
        assert shutil.which(tool), f"{tool} is not installed; the bdd job installs it"
    state["run"] = subprocess.run([str(IDP / "bin" / "idp-kyverno-render"), "platform/observability"],
                                  cwd=IDP, capture_output=True, text=True)


@then("every rendered workload passes the restricted profile and it exits 0")
def _passes(state: dict) -> None:
    r = state["run"]
    assert r.returncode == 0, r.stdout + r.stderr
    row = re.search(r"^ok\s+render\s+langfuse .*fail: (\d+), warn: \d+, error: (\d+)", r.stdout, re.M)
    assert row, r.stdout
    assert row.group(1) == "0" and row.group(2) == "0", row.group(0)
