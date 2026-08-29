"""crew#562 path 1 (ADR 0009 founder-screen-access): the portal's /pair proxy sends a Basic-auth header
to Sunshine on the estate Mac, read from vault entry `sunshine-auth`. The Mac has no cloud identity and
the founder never pastes a secret (crew#66 root trust), so the credential is minted by CI
(bin/idp-bootstrap-sunshine, oke-check apply) and adopted on the Mac over the tailnet.

Rule: the bootstrapper mints once, keeps a complete entry, rotates only when asked, derives the
header from the pair it wrote, never prints a value, and runs on every oke-check apply. Rung 4,
one test per bug; the vault is bin/idp-cloud's file backend."""
import base64
import json
import os
import pathlib
import subprocess

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
BIN = ROOT / "bin" / "idp-bootstrap-sunshine"


def _env(tmp_path):
    return {**os.environ, "IDP_CLOUD_BACKEND": "file", "IDP_CLOUD_FILE_ROOT": str(tmp_path / "cloud"),
            "OCI_CLI_PROFILE": "test", "HOME": str(tmp_path)}


def _run(tmp_path, *argv):
    return subprocess.run([str(BIN), *argv], env=_env(tmp_path), capture_output=True, text=True)


def _entry(tmp_path):
    return json.loads((tmp_path / "cloud" / "secrets" / "sunshine-auth").read_text())


def test_mint_writes_username_password_and_the_derived_basic_header_and_prints_no_value(tmp_path):
    r = _run(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    e = _entry(tmp_path)
    assert e["username"] == "estate" and len(e["password"]) == 32
    assert e["authorization"] == "Basic " + base64.b64encode(f"estate:{e['password']}".encode()).decode()
    assert e["password"] not in r.stdout + r.stderr and e["authorization"] not in r.stdout + r.stderr


def test_a_complete_entry_is_kept_and_rotate_mints_anew(tmp_path):
    _run(tmp_path)
    first = _entry(tmp_path)
    r = _run(tmp_path)
    assert r.returncode == 0 and "kept" in r.stdout and _entry(tmp_path) == first
    r = _run(tmp_path, "--rotate")
    assert r.returncode == 0 and _entry(tmp_path)["password"] != first["password"]


def test_check_grades_absent_incomplete_and_complete(tmp_path):
    assert _run(tmp_path, "--check").returncode == 1
    sec = tmp_path / "cloud" / "secrets"; sec.mkdir(parents=True)
    (sec / "sunshine-auth").write_text(json.dumps({"username": "estate"}))
    assert _run(tmp_path, "--check").returncode == 1, "two keys missing is incomplete"
    _run(tmp_path)  # mint completes it (an incomplete entry is not kept)
    assert _run(tmp_path, "--check").returncode == 0


def test_adopt_refuses_without_the_mounted_pair(tmp_path):
    r = subprocess.run([str(BIN), "--adopt"], env={**_env(tmp_path), "SUNSHINE_CREDS_DIR": str(tmp_path / "none")},
                       capture_output=True, text=True)
    assert r.returncode == 1 and "username/password" in r.stdout


def test_oke_check_apply_runs_the_bootstrapper():
    wf = yaml.safe_load((ROOT / ".github" / "workflows" / "oke-check.yml").read_text())
    steps = [s for j in wf["jobs"].values() for s in j.get("steps", []) if "idp-bootstrap-sunshine" in str(s.get("run", ""))]
    assert steps, "no oke-check step runs bin/idp-bootstrap-sunshine"
    assert "inputs.mode == 'apply'" in steps[0]["if"]
