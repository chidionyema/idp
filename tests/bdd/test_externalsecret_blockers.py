"""An ExternalSecret that cannot sync is a founder action, or a silent hole.

Incident: 2026-09-13, cyrus. Rule: externalsecret-blockers-are-loud.

THE INCIDENT. `cyrus` sat HealthCheckFailed for days, and the reason was buried
three layers down:

    cluster:  cyrus  Ready=Unknown  "Reconciliation in progress"
    flux:     "health check failed after 10m: timeout waiting for:
               [ExternalSecret/cyrus/cyrus-linear-oauth status: 'InProgress']"
    ESO:      "Ready=False / SecretSyncedError -- could not get secret data from provider"

The bottom line is not something anyone can fix in code. The vault entries
`cyrus-linear-client-id` and `cyrus-linear-client-secret` are born in a BROWSER --
Linear publishes no API to create an OAuth application -- so the pair can only be
typed by a person. R47 says a founder blocker is loud and one action; a blocker
that reads "Reconciliation in progress" is neither.

Measured 2026-09-13: 5 of 138 ExternalSecrets cannot sync, every one of them
waiting on a value only a person can produce.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GATE = REPO / "bin" / "idp-externalsecret-blockers"
FIXTURES = REPO / "tests" / "fixtures" / "secret-blockers"


def load_gate():
    loader = importlib.machinery.SourceFileLoader("secret_blockers", str(GATE))
    spec = importlib.util.spec_from_loader("secret_blockers", loader)
    assert spec and spec.loader, "the gate must load by path (LAW 45)"
    mod = importlib.util.module_from_spec(spec)
    sys.modules["secret_blockers"] = mod
    loader.exec_module(mod)
    return mod


def run_gate(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["python3", str(GATE), *args], capture_output=True, text=True)


def es(ns, name, keys, reason, ready="False", store="human-vault", message=""):
    return {
        "metadata": {"namespace": ns, "name": name},
        "spec": {
            "secretStoreRef": {"kind": "ClusterSecretStore", "name": store},
            "data": [{"secretKey": k, "remoteRef": {"key": k}} for k in keys],
        },
        "status": {
            "conditions": [
                {"type": "Ready", "status": ready, "reason": reason, "message": message}
            ]
        },
    }


# --- the incident, exactly --------------------------------------------------


def test_the_cyrus_blocker_is_refused_and_names_its_vault_keys() -> None:
    bad = FIXTURES / "bad" / "externalsecrets.json"
    r = run_gate("--from", str(bad), "--fail-on-blocker")
    assert r.returncode == 1, (
        f"the gate must refuse it; answered {r.returncode}:\n{r.stdout}"
    )
    assert "cyrus/cyrus-linear-oauth" in r.stdout
    assert "cyrus-linear-client-id" in r.stdout
    assert "FOUNDER ACTION" in r.stdout


def test_the_same_secret_synced_passes() -> None:
    good = FIXTURES / "good" / "externalsecrets.json"
    r = run_gate("--from", str(good), "--fail-on-blocker")
    assert r.returncode == 0, (
        f"the gate must pass it; answered {r.returncode}:\n{r.stdout}"
    )


# --- the contract -----------------------------------------------------------


def test_a_missing_provider_entry_is_marked_for_a_person() -> None:
    """`SecretSyncedError` is "the value is not there yet", which a person fixes."""
    out = load_gate().blockers([es("x", "y", ["K"], "SecretSyncedError")])
    assert out["summary"]["waiting_on_a_person"] == 1
    assert out["blockers"][0]["needs_a_person"] is True


def test_a_different_failure_is_not_reported_as_a_founder_action() -> None:
    """An unreachable store is an estate defect and must not be dressed as a person's step.

    Reporting an infrastructure failure as "wait for the founder" is how a real
    defect waits a week for a human who cannot fix it.
    """
    out = load_gate().blockers([es("x", "y", ["K"], "SecretStoreUnreachable")])
    assert out["summary"]["other_failures"] == 1
    assert out["summary"]["waiting_on_a_person"] == 0
    assert out["blockers"][0]["needs_a_person"] is False


def test_every_blocker_names_the_vault_key_it_needs() -> None:
    """The key is the actionable half; "InProgress" is not a step anyone can take."""
    out = load_gate().blockers(
        [es("cyrus", "cyrus-linear-oauth", ["a", "b"], "SecretSyncedError")]
    )
    assert out["blockers"][0]["vault_keys"] == ["a", "b"]


def test_a_synced_secret_is_not_a_blocker() -> None:
    out = load_gate().blockers([es("x", "y", ["K"], "SecretSynced", ready="True")])
    assert out["summary"]["blocked"] == 0
    assert out["blockers"] == []


def test_an_empty_estate_is_zero_not_broken() -> None:
    out = load_gate().blockers([])
    assert out["summary"]["externalsecrets"] == 0
    assert out["summary"]["blocked"] == 0


def test_the_default_run_reports_without_refusing() -> None:
    """R38: the estate has 5, and a gate red from day one gets switched off."""
    bad = FIXTURES / "bad" / "externalsecrets.json"
    r = run_gate("--from", str(bad))
    assert r.returncode == 0, "the default run must report, not refuse"


def test_an_unreadable_document_is_blind_not_clean(tmp_path: Path) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{ not json")
    r = run_gate("--from", str(broken))
    assert r.returncode == 2, f"expected the BLIND verdict, got {r.returncode}"
    assert "BLIND" in (r.stdout + r.stderr)


def test_the_json_output_names_the_store_as_well_as_the_key() -> None:
    """A key lives in a store; naming one without the other is half an instruction."""
    r = run_gate("--from", str(FIXTURES / "bad" / "externalsecrets.json"), "--json")
    assert r.returncode == 0
    doc = json.loads(r.stdout)
    assert doc["blockers"][0]["store"] == "human-vault"
    assert doc["summary"]["blocked"] == 1
