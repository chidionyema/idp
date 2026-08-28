"""crew#503: bin/idp-vault-put set `name=$1` and then sourced bin/idp-oci-whoami,
whose profile loop assigned `name` too. The github-app vault entry was created as
"DEFAULT" (vault-seed run 33089277235: `vault DEFAULT created (4 keys)`), and the
oke-check installation step found no `github-app` secret (run 33092297081).

The test sources the real whoami under a fake HOME with one session profile and
a stub `oci` on PATH, then reads back the caller's variables. No socket."""
import os
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
WHOAMI = ROOT / "bin" / "idp-oci-whoami"
VAULT_PUT = ROOT / "bin" / "idp-vault-put"


def _source_and_echo(tmp_path, assignments, echo):
    home = tmp_path / "home"
    (home / ".oci" / "sessions" / "DEFAULT").mkdir(parents=True)
    (home / ".oci" / "sessions" / "DEFAULT" / "token").write_text("t")
    stub = tmp_path / "bin"
    stub.mkdir()
    (stub / "oci").write_text("#!/usr/bin/env bash\nexit 0\n")
    (stub / "oci").chmod(0o755)
    env = dict(os.environ, HOME=str(home), PATH=f"{stub}:{os.environ['PATH']}")
    env.pop("OCI_CLI_PROFILE", None)
    script = assignments + f'\nsource "{WHOAMI}" >/dev/null 2>&1\necho "{echo}"'
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env).stdout.strip()


def test_callers_name_survives_sourcing_whoami(tmp_path):
    out = _source_and_echo(tmp_path, 'name=github-app; mtime=7; newest_mtime=9', "$name $mtime $newest_mtime")
    assert out == "github-app 7 9"


def test_whoami_still_finds_the_live_profile(tmp_path):
    assert _source_and_echo(tmp_path, "", "$OCI_CLI_PROFILE") == "DEFAULT"


def test_whoami_declares_no_bare_lowercase_temporaries():
    """Everything whoami assigns besides its exports must carry the _ow_ prefix
    or be one of the two documented outputs (live, SESSIONS_DIR)."""
    import re
    assigned = set(re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*)=", WHOAMI.read_text(), re.M))
    allowed = {"SESSIONS_DIR", "live", "OCI_CLI_PROFILE"}
    bare = {v for v in assigned if not v.startswith("_ow_")} - allowed
    assert not bare, bare


def test_vault_put_reads_the_secret_name_into_a_distinct_variable():
    body = VAULT_PUT.read_text()
    assert "SECRET_NAME=$1" in body
    assert "\nname=$1" not in body
