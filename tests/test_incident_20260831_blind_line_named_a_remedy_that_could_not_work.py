"""A BLIND line must name the fault it found, and must never prescribe an action that cannot fix it.

2026-08-31: `bin/idp-kube get nodes` printed

    BLIND   kube  cluster list failed: BLIND   cloud  oci ce cluster list failed
                  -- refresh the session with bin/idp-oci-login

on a laptop whose session was irrelevant. The real answer, from the CLI's own 400 body, was
`InvalidParameter: compartmentId is not available` -- `--compartment-id` was the empty string,
because `oci_compartment` had sourced `bin/idp-oci-whoami`, that script had `exit 2`ed inside a
command substitution, and nothing checked the status. A browser login cannot supply a compartment
id, so the one instruction the operator was given was the one that could not work.

Three separate defects produced one sentence, and this file grades each of them:
  - the cause was thrown away    (`oci ... | jq` swallowed the body; the `||` bound to the pipeline)
  - the remedy was hardcoded     (idp-kube appended the session line to every failure)
  - the auth mode was hardcoded  (`security_token` on a laptop whose working profile is API-key)

Every case runs against a stub `oci` on PATH and a fixture ~/.oci/config, so the whole file is
cloud-free and runs on a bare runner.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLOUD = ROOT / "bin" / "idp-cloud"
KUBE = ROOT / "bin" / "idp-kube"

# The literal 400 body OCI returned on 2026-08-31, trimmed to the two keys the blind line quotes.
REAL_400 = """{
  "code": "InvalidParameter",
  "message": "compartmentId is not available",
  "status": 400,
  "target_service": "container_engine"
}"""

API_KEY_PROFILE = """[DEFAULT]
user=ocid1.user.oc1..fixture
fingerprint=aa:bb
key_file=/dev/null
tenancy=ocid1.tenancy.oc1..fixture
region=uk-london-1
"""

SESSION_PROFILE = """[otto]
security_token_file=/dev/null
key_file=/dev/null
tenancy=ocid1.tenancy.oc1..fixture
region=uk-london-1
"""


def _estate(
    tmp_path, *, oci_exit=0, oci_stdout="[]", config=API_KEY_PROFILE, tfvars=None
):
    """A throwaway checkout, HOME and PATH: a stub `oci`, a fixture ~/.oci/config, optional tfvars.

    The scripts take $IDP from their own location, so the fixture checkout is a directory of
    symlinks to the real bin/. That is what makes these cases independent of whether this machine
    happens to have a rendered platform/oci/terraform.tfvars -- the file is generated and
    gitignored, so a test that reads the real one passes or fails by accident.
    """
    idp = tmp_path / "checkout"
    (idp / "bin").mkdir(parents=True)
    for f in (ROOT / "bin").iterdir():
        if f.is_file() and f.name.startswith("idp-"):
            (idp / "bin" / f.name).symlink_to(f.resolve())
    if tfvars is not None:
        (idp / "platform" / "oci").mkdir(parents=True)
        (idp / "platform" / "oci" / "terraform.tfvars").write_text(tfvars)

    home = tmp_path / "home"
    (home / ".oci").mkdir(parents=True)
    (home / ".oci" / "config").write_text(config)

    bindir = tmp_path / "stub"
    bindir.mkdir()
    stub = bindir / "oci"
    # The stub answers, so the script under test reaches its own error handling rather than
    # dying on a missing binary. A failing call writes the body to stderr, as the real CLI does.
    stub.write_text(
        "#!/usr/bin/env bash\n"
        f"cat <<'EOF' >&{'2' if oci_exit else '1'}\n{oci_stdout}\nEOF\n"
        f"exit {oci_exit}\n"
    )
    stub.chmod(0o755)

    env = dict(os.environ)
    for k in (
        "OCI_CLI_PROFILE",
        "OCI_CLI_AUTH",
        "OCI_COMPARTMENT_OCID",
        "OCI_LAPTOP_KEY",
    ):
        env.pop(k, None)
    env["HOME"] = str(home)
    env["PATH"] = f"{bindir}:{env['PATH']}"
    env["IDP_CLOUD_BACKEND"] = "oci"
    env["_IDP_FIXTURE"] = str(idp)
    return env


def _cloud(env, *args):
    return subprocess.run(
        [str(Path(env["_IDP_FIXTURE"]) / "bin" / "idp-cloud"), *args],
        env=env,
        capture_output=True,
        text=True,
    )


def _shell_func(name, arg, env):
    """Call one function out of bin/idp-cloud without running the script's argument parser."""
    src = CLOUD.read_text()
    block = "\n".join(
        m.group(0)
        for m in re.finditer(
            r"^oci_(?:tfvar|auth_for_profile)\(\) \{.*?^\}", src, re.S | re.M
        )
    )
    assert "oci_auth_for_profile" in block, (
        "oci_auth_for_profile is no longer a top-level function"
    )
    script = f'IDP={env["_IDP_FIXTURE"]}\nblind() {{ printf "%s" "$1"; exit 2; }}\n{block}\n{name} "{arg}"\n'
    return subprocess.run(
        ["bash", "-c", script], env=env, capture_output=True, text=True
    ).stdout.strip()


# --- the remedy that could not work -------------------------------------------------------------


def test_the_relayed_cause_carries_no_remedy_of_its_own():
    """idp-kube must not append a fix to a failure it did not diagnose."""
    line = next(
        ln
        for ln in KUBE.read_text().splitlines()
        if "cluster list failed" in ln and "blind" in ln
    )
    assert "idp-oci-login" not in line, (
        "bin/idp-kube is again naming a remedy on a cause it did not read. It relays whatever "
        "bin/idp-cloud diagnosed; a session refresh cannot supply a compartment id.\n"
        + line
    )


def test_a_missing_compartment_is_named_as_a_missing_compartment(tmp_path):
    env = _estate(tmp_path, config=SESSION_PROFILE)
    env["OCI_CLI_PROFILE"] = "otto"
    env["OCI_COMPARTMENT_OCID"] = ""
    r = _cloud(env, "cluster", "list")
    assert r.returncode == 2
    assert "compartment" in r.stderr, r.stderr
    assert "session" not in r.stderr.lower(), (
        "an absent compartment id is being reported as a session problem again:\n"
        + r.stderr
    )


def test_a_missing_identity_is_named_as_a_missing_identity(tmp_path):
    """No profile anywhere: that IS the session case, and it may say so."""
    env = _estate(tmp_path, config="")
    (tmp_path / "home" / ".oci" / "sessions").mkdir()
    r = _cloud(env, "cluster", "list")
    assert r.returncode == 2
    assert "no OCI identity" in r.stderr, r.stderr
    assert "idp-oci-login" in r.stderr, (
        "the one case a login does fix must still say so"
    )


# --- the cause that was thrown away -------------------------------------------------------------


def test_the_cli_diagnosis_reaches_the_blind_line(tmp_path):
    env = _estate(tmp_path, oci_exit=1, oci_stdout=REAL_400)
    env["OCI_CLI_PROFILE"] = "DEFAULT"
    env["OCI_COMPARTMENT_OCID"] = "ocid1.compartment.oc1..fixture"
    r = _cloud(env, "cluster", "list")
    assert r.returncode == 2
    for owed in (
        "InvalidParameter",
        "compartmentId is not available",
        "DEFAULT",
        "api_key",
    ):
        assert owed in r.stderr, (
            f"the blind line no longer carries {owed!r}:\n{r.stderr}"
        )


def test_no_oci_call_pipes_its_failure_into_jq():
    """`oci ... | jq ... || blind` grades the pipeline and discards the body that said why."""
    offenders = [
        ln.strip()
        for ln in CLOUD.read_text().splitlines()
        if re.search(r"^\s*oci\s+\S+.*\|\s*jq", ln)
    ]
    assert not offenders, (
        "an OCI failure is being read through a pipe again:\n" + "\n".join(offenders)
    )


# --- the caller-killer, and the hardcoded auth mode ----------------------------------------------


def test_nothing_sources_idp_oci_whoami():
    """It ends in `exit 2`. Sourced, that kills the caller; sourced inside $(...) it kills the
    subshell and hands the caller a silent empty string, which is exactly how $C went empty."""
    hits = [
        f"{p.relative_to(ROOT)}:{i}"
        for p in sorted((ROOT / "bin").iterdir())
        if p.is_file() and not p.is_symlink()
        for i, ln in enumerate(p.read_text(errors="ignore").splitlines(), 1)
        if re.search(r"^\s*(source|\.)\s+.*idp-oci-whoami", ln)
    ]
    assert not hits, "idp-oci-whoami is being sourced again: " + ", ".join(hits)


@pytest.mark.parametrize(
    "config,profile,expected",
    [
        (API_KEY_PROFILE, "DEFAULT", "api_key"),
        (SESSION_PROFILE, "otto", "security_token"),
        ("", "DEFAULT", "api_key"),
    ],
)
def test_the_auth_mode_is_read_off_the_profile_not_assumed(
    tmp_path, config, profile, expected
):
    env = _estate(tmp_path, config=config)
    assert _shell_func("oci_auth_for_profile", profile, env) == expected
