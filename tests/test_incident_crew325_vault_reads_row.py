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


def test_the_row_runs_where_flux_is_blind_and_the_policy_allows_it() -> None:
    src = (ROOT / "bin" / "idp-oke-rebuild").read_text()
    blind = src[src.index("no kube path from this host"):]
    assert "step vault-reads vault_reads_result" in blind.split("\nfi\n", 1)[0], "vault-reads row must sit in the no-kube branch"
    statements = json.loads((ROOT / "platform" / "oci" / "policy" / "estate-operators.statements.json").read_text())
    assert "Allow group estate-operators to read audit-events in compartment estate" in statements


def test_incident_crew584_vault_reads_starts_before_the_plan_not_after_it() -> None:
    """founder 2026-08-29 "why 25 minutes": vault-reads took 352-433s serially (7 of 9 minutes, runs
    33237964214 and the five before it). It starts right after login and is collected where its row
    prints, so its wall clock overlaps the tofu plan instead of adding to it."""
    src = (ROOT / "bin" / "idp-oke-rebuild").read_text()
    start = src.index('"$IDP/bin/idp-vault-reads" >"$VR_OUT"')
    plan = src.index("step tofu-plan")
    collect = src.index("step vault-reads vault_reads_result")
    assert start < plan < collect, "the audit paging must run alongside the plan, not after it"
    assert src.count("bin/idp-vault-reads\"") == 1, "one launch, no second serial call"
    assert 'VR_PID=$!' in src and 'wait "$VR_PID"' in src


def test_incident_crew584_vault_reads_result_carries_the_rc_and_the_text(tmp_path: Path) -> None:
    out = tmp_path / "vr.out"; out.write_text("FAIL    vault-reads  0 GetSecretBundle calls in 90 min\n"); (tmp_path / "vr.out.rc").write_text("1\n")
    script = f'VR_OUT="{out}"; VR_PID=""; vault_reads_result() {{ wait "$VR_PID" 2>/dev/null; cat "$VR_OUT"; return "$(cat "$VR_OUT.rc" 2>/dev/null || echo 2)"; }}; vault_reads_result; echo rc=$?'
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    assert "0 GetSecretBundle" in r.stdout and r.stdout.strip().endswith("rc=1"), r.stdout + r.stderr
