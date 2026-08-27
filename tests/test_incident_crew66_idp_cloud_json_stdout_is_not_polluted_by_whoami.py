"""Incident 2026-08-27 21:19Z (oke-check run 33117168909, and every run on main since #476 merged):
`bin/idp-identity-apply plan` died with `jq: parse error: Invalid numeric literal at line 1, column 3`.
`bin/idp-cloud secret describe` sources bin/idp-oci-whoami when OCI_CLI_PROFILE is unset, and whoami
prints `ok      oci-whoami: live profile is ...` on stdout, so the JSON callers parse arrived as
`ok ...\n{...}`. Guard: with a whoami that talks on stdout and an oci CLI that answers one ACTIVE
secret, `secret describe` must still print parseable JSON and nothing else (LAW 45, crew#66 CP5)."""
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _tree(tmp_path: Path) -> Path:
    idp = tmp_path / "idp"
    (idp / "bin").mkdir(parents=True)
    shutil.copy(ROOT / "bin" / "idp-cloud", idp / "bin" / "idp-cloud")
    whoami = idp / "bin" / "idp-oci-whoami"
    whoami.write_text("#!/usr/bin/env bash\nexport OCI_CLI_PROFILE=stub\necho 'ok      oci-whoami: live profile is stub'\n")
    subprocess.run(["git", "init", "-q", str(idp)], check=True)
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    oci = stubs / "oci"
    oci.write_text(
        "#!/usr/bin/env bash\n"
        'printf \'%s\' \'[{"id":"ocid1.vaultsecret.stub","vault-id":"ocid1.vault.stub","key-id":"ocid1.key.stub"}]\'\n'
    )
    for p in (whoami, oci):
        p.chmod(p.stat().st_mode | stat.S_IXUSR)
    return idp


def _run(tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
    idp = _tree(tmp_path)
    env = {k: v for k, v in os.environ.items() if k != "OCI_CLI_PROFILE"}
    env["PATH"] = f"{tmp_path / 'stubs'}:{env['PATH']}"
    env["OCI_COMPARTMENT_OCID"] = "ocid1.compartment.stub"
    env["IDP_CLOUD_BACKEND"] = "oci"
    return subprocess.run([str(idp / "bin" / "idp-cloud"), *args], env=env, capture_output=True, text=True)


def test_secret_describe_stdout_is_one_json_object(tmp_path):
    r = _run(tmp_path, "secret", "describe", "oauth2-proxy-client-id")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == {
        "id": "ocid1.vaultsecret.stub",
        "vault-id": "ocid1.vault.stub",
        "key-id": "ocid1.key.stub",
    }, r.stdout


def test_whoami_line_moved_to_stderr_not_dropped(tmp_path):
    r = _run(tmp_path, "secret", "describe", "oauth2-proxy-client-id")
    assert "oci-whoami: live profile is stub" in r.stderr


def test_every_whoami_source_in_idp_cloud_keeps_stdout_clean():
    text = (ROOT / "bin" / "idp-cloud").read_text()
    sites = [l for l in text.splitlines() if 'source "$IDP/bin/idp-oci-whoami"' in l]
    assert sites, "idp-cloud no longer sources whoami; retire this test"
    assert all(">&2" in l for l in sites), [l.strip() for l in sites if ">&2" not in l]
