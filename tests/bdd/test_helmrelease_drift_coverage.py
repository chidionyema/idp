"""A HelmRelease that cannot see the cluster disagree with it is not reconciled.

Incident: 2026-09-13, chaos-mesh. Rule: helmrelease-drift-is-detectable.

THE INCIDENT. `chaos-controller-manager` ran at 0 replicas for 18 days while
three things reported everything was fine:

    chaos-controller-manager   0/0   0   0   18d
    HelmRelease/chaos-mesh     Ready  UpgradeSucceeded
    helm-controller            "release in-sync with desired state"
    HELM STORED: replicas: 1   LIVE: replicas: 0

helm-controller diffs the manifest in Helm storage against the rendered chart
and NEVER against the cluster, so a Deployment edited after the apply is
invisible to it forever. The cost was not the missing pod: chaos-mesh ships 39
admission webhooks with `failurePolicy: Fail` pointing at a Service with no
endpoints, so every object under `chaos-mesh.org/*` became uncreatable
estate-wide, and the error read `EOF`.

driftDetection is the fence for exactly this -- measured 2026-09-13, 1 of 33
HelmReleases had it enabled. The one that did carries the comment explaining
why: the same defect happened once before and only that release got the fence.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
GATE = REPO / "bin" / "idp-helmrelease-drift-coverage"
FIXTURES = REPO / "tests" / "fixtures" / "helmrelease-drift"
MANIFEST = REPO / "platform" / "chaos" / "mesh" / "helmrelease.yaml"


def load_gate():
    """Load the gate by path; it has no `.py` suffix, so the loader is named."""
    loader = importlib.machinery.SourceFileLoader("drift_coverage", str(GATE))
    spec = importlib.util.spec_from_loader("drift_coverage", loader)
    assert spec and spec.loader, "the gate must load by path (LAW 45)"
    mod = importlib.util.module_from_spec(spec)
    sys.modules["drift_coverage"] = mod
    loader.exec_module(mod)
    return mod


def run_gate(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["python3", str(GATE), *args], capture_output=True, text=True)


def helmrelease(namespace: str, name: str, mode, ready: bool = True) -> dict:
    spec = {} if mode is None else {"driftDetection": {"mode": mode}}
    return {
        "metadata": {"namespace": namespace, "name": name},
        "spec": spec,
        "status": {
            "conditions": [{"type": "Ready", "status": "True" if ready else "False"}]
        },
    }


# --- the incident, exactly --------------------------------------------------


def test_a_ready_release_that_cannot_see_drift_is_refused() -> None:
    """The chaos defect: Ready, and driftDetection unset."""
    bad = FIXTURES / "bad" / "helmreleases.json"
    r = run_gate("--from", str(bad), "--fail-on-blind-ready")
    assert r.returncode == 1, (
        f"the gate must refuse it; answered {r.returncode}:\n{r.stdout}"
    )
    assert "chaos-mesh/chaos-mesh" in r.stdout


def test_the_same_release_with_the_fence_on_passes() -> None:
    good = FIXTURES / "good" / "helmreleases.json"
    r = run_gate("--from", str(good), "--fail-on-blind-ready")
    assert r.returncode == 0, (
        f"the gate must pass it; answered {r.returncode}:\n{r.stdout}"
    )


def test_the_fix_is_in_the_manifest() -> None:
    """`driftDetection: mode: enabled`, read out of the file rather than trusted."""
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    hr = next(d for d in docs if d.get("kind") == "HelmRelease")
    dd = (hr["spec"] or {}).get("driftDetection") or {}
    assert dd.get("mode") == "enabled", (
        "the chaos HelmRelease cannot see the cluster disagree with it. helm-controller "
        "never diffs against the cluster, so the controller-manager stayed at 0 replicas "
        "for 18 days while the release reported Ready/UpgradeSucceeded."
    )


# --- the contract -----------------------------------------------------------


def test_an_empty_estate_is_reported_as_zero_not_as_covered() -> None:
    """No releases is not the same as every release being safe."""
    out = load_gate().coverage([])
    assert out["summary"]["releases"] == 0
    assert out["summary"]["drift_detectable"] == 0


def test_a_not_ready_release_is_counted_but_not_as_a_ready_blind_one() -> None:
    """The number to drive down is READY-and-blind.

    A release already reporting not-Ready is a different, louder problem; counting
    it here would inflate the number this gate exists to keep honest.
    """
    out = load_gate().coverage([helmrelease("x", "y", None, ready=False)])
    assert out["summary"]["drift_blind"] == 1
    assert out["summary"]["ready_and_blind"] == 0


def test_a_release_with_drift_detection_is_never_counted_blind() -> None:
    out = load_gate().coverage([helmrelease("x", "y", "enabled")])
    assert out["summary"]["drift_blind"] == 0
    assert out["summary"]["drift_detectable"] == 1
    assert "x/y" in out["drift_detectable"]


def test_an_explicitly_disabled_release_is_named_with_its_mode() -> None:
    """`mode: disabled` and unset are both blind, and the report says which."""
    out = load_gate().coverage([helmrelease("x", "y", "disabled")])
    assert out["summary"]["drift_blind"] == 1
    assert out["drift_blind"][0]["mode"] == "disabled"


def test_the_default_run_does_not_fail_on_a_blind_estate() -> None:
    """R38: the estate has 31 of them, and a gate red on day one gets switched off.

    The default reports the count. `--fail-on-blind-ready` is the flag a caller
    uses once the count is zero, to keep it there.
    """
    bad = FIXTURES / "bad" / "helmreleases.json"
    r = run_gate("--from", str(bad))
    assert r.returncode == 0, "the default run must report, not refuse"


def test_a_clean_run_reports_the_ratio_it_measured() -> None:
    """The output states both numbers, so a reader can tell covered from blind."""
    r = run_gate("--from", str(FIXTURES / "good" / "helmreleases.json"))
    assert r.returncode == 0
    assert "1 of 1" in r.stdout


def test_an_unreadable_document_is_blind_not_clean(tmp_path: Path) -> None:
    """A file that cannot be parsed must never report an empty estate."""
    broken = tmp_path / "broken.json"
    broken.write_text("{ this is not json")
    r = run_gate("--from", str(broken))
    assert r.returncode == 2, f"expected the BLIND verdict, got {r.returncode}"
    assert "BLIND" in (r.stdout + r.stderr)


def test_the_json_output_carries_both_lists() -> None:
    """A caller driving the count down needs the names, not just the number."""
    r = run_gate("--from", str(FIXTURES / "bad" / "helmreleases.json"), "--json")
    assert r.returncode == 0
    doc = json.loads(r.stdout)
    assert doc["summary"]["ready_and_blind"] == 1
    assert doc["drift_blind"][0]["release"] == "chaos-mesh/chaos-mesh"
    assert doc["drift_detectable"] == []
