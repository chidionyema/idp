"""crew#66 follow-up row (2026-08-27, from idp#465): bin/idp-cluster-state read the receipt with
`2>/dev/null`, so a failed `object get` was an empty body and the grade was FAIL "receipt does not
start with ok: ''" — a FAIL the cluster did nothing to earn, and the error that would have named the
cause thrown away. A read that fails is BLIND (exit 2) and carries the error. Both ways."""
import json
import os
import pathlib
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
HEAD = json.dumps({"last-modified": "Thu, 27 Aug 2026 19:00:03 GMT", "date": "Thu, 27 Aug 2026 19:00:05 GMT", "content-length": "10"})


def _tree(tmp_path, get_script):
    idp = tmp_path / "idp"; (idp / "bin").mkdir(parents=True)
    shutil.copy(ROOT / "bin" / "idp-cluster-state", idp / "bin" / "idp-cluster-state")
    shutil.copytree(ROOT / "bin" / "lib", idp / "bin" / "lib")
    shim = idp / "bin" / "idp-cloud"
    shim.write_text("#!/bin/sh\ncase \"$*\" in\n  *\"object head\"*) printf '%s' '" + HEAD + "';;\n  *\"object get\"*) " + get_script + ";;\nesac\n")
    shim.chmod(0o755)
    return idp


def _grade(idp):
    env = {**os.environ, "CLUSTER_STATE_MAX_AGE_MIN": "999999999"}
    return subprocess.run([str(idp / "bin" / "idp-cluster-state")], capture_output=True, text=True, env=env)


def test_a_failed_read_is_blind_and_names_the_error(tmp_path):
    r = _grade(_tree(tmp_path, "echo 'ServiceError: NotAuthenticated' >&2; exit 1"))
    assert r.returncode == 2, r.stdout + r.stderr
    assert "BLIND   cluster-state  object get failed: ServiceError: NotAuthenticated" in r.stdout, r.stdout


def test_an_empty_read_is_blind_not_fail(tmp_path):
    r = _grade(_tree(tmp_path, "true"))
    assert r.returncode == 2 and "object get returned an empty body" in r.stdout, r.stdout + r.stderr


def test_a_real_receipt_still_grades(tmp_path):
    body = 'ok cluster-state at 2026-08-27T19:00:03Z nodes=1 ready=1\\n{"at":"2026-08-27T19:00:03Z","nodes":[]}'
    r = _grade(_tree(tmp_path, "printf '" + body + "\\n'"))
    # the read succeeded, so the grade is about the receipt's content, never about the read
    assert r.returncode != 2 and "object get" not in r.stdout, r.stdout + r.stderr
    assert "ok cluster-state at 2026-08-27T19:00:03Z" in r.stdout, r.stdout
