"""crew#503, 2026-08-27: two GitHub App manifest codes were exchanged (POST /app-manifests/{code}/conversions,
one-time, the private key returned exactly once) and the vault write that followed failed both times, first on
tofu state in a worktree, then on an unset OCI profile. The key was gone with the temp file.

Guard (LAW 45): `bin/idp-github-app convert <code>` proves the vault write path with the same read the write
needs BEFORE it touches GitHub, and a failed write after the exchange keeps the key on disk. Every external
binary is a stub on PATH here; nothing opens a socket.
"""
import os
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-github-app"


def _stub(d, name, body):
    p = d / name
    p.write_text("#!/usr/bin/env bash\n" + body)
    p.chmod(0o755)


def _run(tmp_path, oci_ok):
    bins = tmp_path / "bin"
    bins.mkdir()
    marker = tmp_path / "gh-was-called"
    _stub(bins, "gh", f'echo "$@" >> "{marker}"; echo \'{{}}\'; exit 0\n')
    _stub(bins, "tofu", 'echo ocid1.stub\n')
    _stub(bins, "oci", "exit 0\n" if oci_ok else 'echo "ServiceError: NotAuthenticated" >&2; exit 1\n')
    env = {**os.environ, "PATH": f"{bins}:{os.environ['PATH']}", "OCI_CLI_PROFILE": "stub",
           "OCI_COMPARTMENT_OCID": "ocid1.compartment.stub", "HOME": str(tmp_path)}
    r = subprocess.run([str(SCRIPT), "convert", "0" * 40], env=env, capture_output=True, text=True, cwd=ROOT)
    return r, marker


def test_incident_crew503_a_failed_vault_preflight_stops_before_github_is_asked(tmp_path):
    r, marker = _run(tmp_path, oci_ok=False)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "the code was NOT spent" in r.stderr, r.stderr
    assert not marker.exists(), f"gh was called although the vault was unreachable: {marker.read_text()}"


def test_incident_crew503_the_preflight_is_a_real_vault_read_not_a_tofu_check(tmp_path):
    # the second lost key: tofu answered, the OCI CLI did not. The pre-flight must run oci itself.
    r, marker = _run(tmp_path, oci_ok=False)
    assert "vault   not reachable" in r.stdout + r.stderr, r.stdout + r.stderr


def test_incident_crew503_a_failed_write_after_the_exchange_keeps_the_key(tmp_path):
    bins = tmp_path / "bin"
    bins.mkdir()
    # gh answers the conversion with an App; oci answers the pre-flight read but refuses the write
    _stub(bins, "gh", 'echo \'{"id":1,"slug":"stub","client_id":"c","pem":"-----BEGIN RSA PRIVATE KEY-----\\nstub\\n-----END RSA PRIVATE KEY-----"}\'\n')
    _stub(bins, "tofu", 'echo ocid1.stub\n')
    _stub(bins, "oci", 'case "$*" in *"secret list"*) echo 0; exit 0;; *) exit 1;; esac\n')
    env = {**os.environ, "PATH": f"{bins}:{os.environ['PATH']}", "OCI_CLI_PROFILE": "stub",
           "OCI_COMPARTMENT_OCID": "ocid1.compartment.stub", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)}
    r = subprocess.run([str(SCRIPT), "convert", "0" * 40], env=env, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode != 0
    assert "key is kept at" in r.stderr, r.stderr
    kept = pathlib.Path(re.search(r"key is kept at (\S+) ", r.stderr).group(1))
    assert kept.is_file(), f"the App key was deleted after a failed vault write ({kept})"
    assert "GITHUB_APP_PEM_B64=" in kept.read_text()
    assert oct(kept.stat().st_mode & 0o777) == "0o600"
    kept.unlink()
