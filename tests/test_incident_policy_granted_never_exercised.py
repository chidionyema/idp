"""Incident 2026-08-25: bin/idp-oci-bootstrap wrote an objects policy with a quoted
where clause; OCI stored it unquoted and estate-tofu got 404 on every PutObject,
found only when an apply could not save state. Rule: bootstrap exercises the
policy it writes with a real PutObject as estate-tofu. Rung 4 (incident test),
driven both ways through a fake `oci` on PATH."""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FN = 'source <(sed -n "/^probe_state_write()/,/^}/p" bin/idp-oci-bootstrap); probe_state_write estate-tofu-state'


def _run(tmp_path: Path, put_rc: int, bucket_rc: int = 0) -> subprocess.CompletedProcess:
    fake = tmp_path / "oci"
    fake.write_text(
        "#!/usr/bin/env bash\n"
        f'case "$*" in *"object put"*) exit {put_rc};; *"bucket get"*) exit {bucket_rc};; *) exit 0;; esac\n'
    )
    fake.chmod(0o755)
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"}
    return subprocess.run(["bash", "-c", FN], cwd=ROOT, env=env, capture_output=True, text=True)


def test_must_fail_when_put_object_is_refused(tmp_path: Path) -> None:
    r = _run(tmp_path, put_rc=1)
    assert r.returncode == 1 and "FAIL    state-write probe" in r.stderr


def test_must_pass_when_put_object_succeeds(tmp_path: Path) -> None:
    r = _run(tmp_path, put_rc=0)
    assert r.returncode == 0 and "state-write probe ok" in r.stdout


def test_blind_without_profile_permits_and_says_so(tmp_path: Path) -> None:
    r = _run(tmp_path, put_rc=1, bucket_rc=1)
    assert r.returncode == 0 and "BLIND" in r.stdout
