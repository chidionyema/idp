"""Incident test (rung 4), crew#325, 2026-08-26: llm./langfuse. answered 404 on the gateway for 30+
minutes after the secret-store fix merged, and no session could say whether external-secrets was
reading the vault, because a runner has no kube path and the estate had no row for the vault's own
door. bin/idp-vault-reads grades OCI Audit for GetSecretBundle calls. Both ways in one run: calls
present is ok and names the principal; none is FAIL; an unreadable audit is BLIND, never a verdict."""
import json, os, stat, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "bin" / "idp-vault-reads"


def _run(tmp: Path, events, rc: int = 0) -> subprocess.CompletedProcess:
    b = tmp / "bin"; b.mkdir(exist_ok=True)
    fake = b / "oci"
    fake.write_text("#!/usr/bin/env bash\ncase \"$*\" in *\"audit event list\"*) printf '%s' '"
                    + json.dumps({"data": events}).replace("'", "'\\''") + f"'; exit {rc};; *) echo unexpected >&2; exit 9;; esac\n")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    env = {**os.environ, "PATH": f"{b}:{os.environ['PATH']}", "OCI_COMPARTMENT_OCID": "ocid1.compartment.oc1..test"}
    return subprocess.run(["bash", str(GUARD)], env=env, capture_output=True, text=True)


def _ev(name: str, who: str, t: str) -> dict:
    return {"event-time": t, "data": {"event-name": name, "identity": {"principal-name": who}}}


def test_reads_present_name_the_principal(tmp_path: Path) -> None:
    r = _run(tmp_path, [_ev("GetSecretBundle", "oke-workers", "2026-08-26T20:41:03.000Z"),
                        _ev("GetSecretBundleByName", "oke-workers", "2026-08-26T20:51:03.000Z"),
                        _ev("ListSecrets", "estate-operators", "2026-08-26T20:52:00.000Z")])
    assert r.returncode == 0 and r.stdout.startswith("ok      vault-reads  2 GetSecretBundle call(s)"), r.stdout + r.stderr
    assert "oke-workers" in r.stdout and "last 20:51Z" in r.stdout and "estate-operators" not in r.stdout


def test_no_reads_is_a_fail_that_names_the_cause(tmp_path: Path) -> None:
    r = _run(tmp_path, [_ev("ListSecrets", "estate-operators", "2026-08-26T20:52:00.000Z")])
    assert r.returncode == 1 and r.stdout.startswith("FAIL    vault-reads  0 GetSecretBundle"), r.stdout + r.stderr
    assert "external-secrets is not reading the vault" in r.stdout


def test_unreadable_audit_is_blind(tmp_path: Path) -> None:
    r = _run(tmp_path, [], rc=1)
    assert r.returncode == 2 and r.stdout.startswith("BLIND   vault-reads"), r.stdout + r.stderr


def test_incident_crew584_the_vault_audit_is_not_in_oke_check() -> None:
    """founder 2026-08-29: the row paged 90 min of OCI Audit inside oke-check on every pull request
    (352-433s, 7 of 9 minutes, run 33237964214 and the five before it). Removed from the check."""
    src = (ROOT / "bin" / "idp-oke-rebuild").read_text()
    assert "step vault-reads" not in src and '"$IDP/bin/idp-vault-reads"' not in src
    statements = json.loads((ROOT / "platform" / "oci" / "policy" / "estate-operators.statements.json").read_text())
    assert "Allow group estate-operators to read audit-events in compartment estate" in statements
