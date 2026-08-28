"""Incident test (rung 4): 2026-08-26 02:26Z, bin/idp-flux-bootstrap repointed flux-system/estate-vars
at a freshly created empty vault while 10 secrets lived in the old one. Rule: a vault switch is
refused (rc 3) while the current vault still holds ACTIVE secrets; an empty old vault switches;
an unreadable count is BLIND (rc 2, never a count of 0). crew#66 CP5b: the count comes through
bin/idp-cloud, not the oci CLI."""
import os, re, stat, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "bin" / "idp-flux-bootstrap").read_text()
BLOCK = re.search(r'CUR=\$\(kubectl.*?\nfi\n', SRC, re.S).group(0)

def _fake(b: Path, name: str, body: str) -> None:
    f = b / name; f.write_text("#!/usr/bin/env bash\n" + body); f.chmod(f.stat().st_mode | stat.S_IEXEC)

def _fake_cloud(b: Path, count: str) -> None:
    # the layer reads compartment itself; the test only grades how the script reacts to layer exit
    # codes (0 with N names on stdout, non-zero on a BLIND).
    body = f'''case "$1 $2 $3" in
  "secret list --vault")
    case "{count}" in
      BLIND) echo "compartment unreadable from this identity" >&2; exit 3;;
      *) i=0; while [ "$i" -lt "{count}" ]; do printf "s%s\\n" "$i"; i=$((i+1)); done; exit 0;;
    esac;;
esac
echo "unexpected: $*" >&2; exit 9
'''
    _fake(b, "idp-cloud", body)

def _run(tmp: Path, count: str) -> subprocess.CompletedProcess:
    b = tmp / "bin"; b.mkdir(exist_ok=True); idp = tmp / "idp"; idp.mkdir(exist_ok=True)
    idp_bin = idp / "bin"; idp_bin.mkdir(exist_ok=True)
    _fake_cloud(idp_bin, count)
    (idp / "platform" / "oci").mkdir(parents=True, exist_ok=True)
    (idp / "platform" / "oci" / "terraform.tfvars").write_text('compartment_ocid = "ocid1.compartment.oc1..t"\n')
    _fake(b, "kubectl", 'echo ocid1.vault.old')
    env = {**os.environ, "PATH": f"{b}:{os.environ['PATH']}"}
    return subprocess.run(["bash", "-c", f'IDP="{tmp}/idp"; VAULT_ID=ocid1.vault.new\n{BLOCK}\necho "VAULT_ID=$VAULT_ID"'], env=env, capture_output=True, text=True)

def test_incident_estate_vars_repointed_at_empty_vault(tmp_path: Path) -> None:
    r = _run(tmp_path, "10"); assert r.returncode == 3 and "REFUSE" in r.stdout
    r = _run(tmp_path, "0"); assert r.returncode == 0 and "switching" in r.stdout and "VAULT_ID=ocid1.vault.new" in r.stdout
    r = _run(tmp_path, "BLIND"); assert r.returncode == 2 and "BLIND" in r.stdout and "flux" in r.stdout