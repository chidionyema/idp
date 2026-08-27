"""Incident test, crew#524 CP1 (2026-08-27): four cluster-state receipts (runs 33121853794,
33123127717, 33123602285) said HelmRelease hindsight/hindsight "reconciliation in progress" since
20:17Z while the Kustomization above it said 'HelmRelease status: Failed'. The collector read only
the Ready condition, which for a release stuck in install/remediate says nothing about why. Rule: a
HelmRelease row carries the last Released/Remediated/TestSuccess condition (`last_attempt`) and the
failure counters, so the receipt names the helm error without a kubectl. Both ways: a release with
only a Ready condition gains nothing; a failing one names its last attempt and its counters.
"""
import ast
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/state/cluster-state.yaml"


def _fn(name):
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    src = next(d["data"]["collect.py"] for d in docs if d.get("kind") == "ConfigMap" and "collect.py" in d.get("data", {}))
    tree = ast.parse(src)
    ns: dict = {}
    for want in ("flux_message", name):
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == want)
        exec(compile(ast.Module(body=[fn], type_ignores=[]), "collect.py", "exec"), ns)
    return ns[name]


def test_a_failing_release_names_its_last_attempt_and_its_counters():
    hla = _fn("helm_last_attempt")
    st = {
        "failures": 7, "installFailures": 3,
        "conditions": [
            {"type": "Ready", "status": "False", "message": "reconciliation in progress",
             "lastTransitionTime": "2026-08-27T20:17:15Z"},
            {"type": "Released", "status": "False", "reason": "InstallFailed",
             "message": "Helm install failed for release hindsight/hindsight with chart hindsight@0.9.2: "
                        "context deadline exceeded",
             "lastTransitionTime": "2026-08-27T20:32:15Z"},
            {"type": "Remediated", "status": "True", "reason": "UninstallSucceeded",
             "message": "Helm uninstall succeeded for release hindsight/hindsight.v1",
             "lastTransitionTime": "2026-08-27T20:32:20Z"},
        ],
    }
    row = hla(st)
    assert row["last_attempt"].startswith("Remediated=True: Helm uninstall succeeded"), "the newest non-Ready condition"
    assert row["failures"] == 7 and row["installFailures"] == 3
    assert "upgradeFailures" not in row


def test_the_install_error_itself_is_the_row_when_it_is_the_newest():
    hla = _fn("helm_last_attempt")
    st = {"installFailures": 1, "conditions": [
        {"type": "Ready", "status": "False", "message": "reconciliation in progress", "lastTransitionTime": "2026-08-27T20:17:15Z"},
        {"type": "Released", "status": "False", "message": "Helm install failed: context deadline exceeded",
         "lastTransitionTime": "2026-08-27T20:32:15Z"},
    ]}
    assert hla(st)["last_attempt"] == "Released=False: Helm install failed: context deadline exceeded"


def test_a_healthy_release_gains_nothing():
    hla = _fn("helm_last_attempt")
    assert hla({"conditions": [{"type": "Ready", "status": "True", "message": "Helm install succeeded"}]}) == {}
    assert hla({}) == {}


def test_the_row_is_wired_for_helmreleases_only():
    src = MANIFEST.read_text()
    assert 'if kind == "HelmRelease":' in src and "row.update(helm_last_attempt(st))" in src
