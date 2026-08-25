"""Incident 2026-08-25: bin/idp-oci-bootstrap wrote an objects policy with a quoted
where clause; OCI stored it unquoted and estate-tofu got 404 on every PutObject,
found only when an apply could not save state. Rule: bootstrap exercises the
policy it writes with a real PutObject as estate-tofu, and only as estate-tofu
(idp#119 review: a probe as the tenancy owner passes regardless of the policy).
Rung 4 (incident test), driven both ways through a fake `oci` on PATH."""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOFU = "ocid1.user.oc1..tofu"
OWNER = "ocid1.user.oc1..owner"
FN = ('source <(sed -n "/^probe_state_write()/,/^}/p" bin/idp-oci-bootstrap); '
      f'probe_state_write estate-tofu-state {TOFU}')


def _run(tmp_path: Path, put_rc: int, profile_user: str | None = TOFU) -> subprocess.CompletedProcess:
    fake = tmp_path / "oci"
    fake.write_text(
        "#!/usr/bin/env bash\n"
        'echo "$*" >> "$FAKE_LOG"\n'
        f'case "$*" in *"object put"*) exit {put_rc};; *) exit 0;; esac\n'
    )
    fake.chmod(0o755)
    cfg = tmp_path / "config"
    cfg.write_text(f"[DEFAULT]\nuser={profile_user}\nregion=x\n" if profile_user else "[estate-bootstrap]\nuser=z\n")
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}",
           "OCI_CLI_CONFIG_FILE": str(cfg), "FAKE_LOG": str(tmp_path / "log")}
    env.pop("OCI_TOFU_PROFILE", None)
    return subprocess.run(["bash", "-c", FN], cwd=ROOT, env=env, capture_output=True, text=True)


def test_must_fail_when_put_object_is_refused(tmp_path: Path) -> None:
    r = _run(tmp_path, put_rc=1)
    assert r.returncode == 1 and "FAIL    state-write probe" in r.stderr


def test_must_pass_when_put_object_succeeds_as_estate_tofu(tmp_path: Path) -> None:
    r = _run(tmp_path, put_rc=0)
    assert r.returncode == 0 and "state-write probe ok" in r.stdout
    assert "--profile DEFAULT" in (tmp_path / "log").read_text()


def test_blind_when_profile_is_not_estate_tofu(tmp_path: Path) -> None:
    r = _run(tmp_path, put_rc=0, profile_user=OWNER)
    assert r.returncode == 0 and "BLIND" in r.stdout and "not estate-tofu" in r.stdout
    assert not (tmp_path / "log").exists()  # no PutObject as the wrong identity


def test_blind_without_profile_permits_and_says_so(tmp_path: Path) -> None:
    r = _run(tmp_path, put_rc=1, profile_user=None)
    assert r.returncode == 0 and "BLIND" in r.stdout
