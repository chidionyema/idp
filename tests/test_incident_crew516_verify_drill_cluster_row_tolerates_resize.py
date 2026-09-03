"""crew#516 CP1 / crew#539 CP4: every run of verify-drill.yml on 2026-08-28 went red on the
cluster row "1/2 node pool(s) ACTIVE" while the only non-ACTIVE pool was a1-spot in UPDATING
(the autoscaler resizing it). bin/idp-oke-rebuild already grades a resize in flight as ok and
names the pool (idp#507); bin/idp-verify-drill did not, so the hourly drill could never be
green for 24h. Proved through shims (no network): UPDATING -> ok naming the pool; a DELETING
pool -> FAIL naming pool(STATE); all ACTIVE -> ok with the count."""

import base64
import json
import os
import pathlib
import shutil
import stat
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "bin" / "idp-verify-drill"


def _shim(d, name, body):
    p = d / name
    p.write_text("#!/bin/sh\n" + body)
    p.chmod(p.stat().st_mode | stat.S_IXUSR)


def _run(tmp_path, pools):
    b = tmp_path / "idp" / "bin"
    b.mkdir(parents=True)
    shutil.copy(SCRIPT, b / "idp-verify-drill")
    (b / "idp-verify-drill").chmod(0o755)
    _shim(
        b,
        "idp-cloud",
        'case "$2" in list) echo "c1 ACTIVE";; nodepools) printf \'%s\' "$FAKE_POOLS";; *) exit 1;; esac\n',
    )
    _shim(b, "idp-cluster-state", 'echo "ok cluster-state stub"\n')
    shims = tmp_path / "shims"
    shims.mkdir()
    _shim(shims, "oci", "echo estate-ci\n")
    seg = (
        base64.urlsafe_b64encode(
            json.dumps(
                {"sub": "ocid1.user.x", "ttype": "te", "iat": 0, "exp": 3600}
            ).encode()
        )
        .decode()
        .rstrip("=")
    )
    tok = tmp_path / "token"
    tok.write_text(f"h.{seg}.s")
    cfg = tmp_path / "config"
    cfg.write_text(f"[DEFAULT]\nsecurity_token_file={tok}\n")
    env = dict(
        os.environ,
        PATH=f"{shims}:{os.environ['PATH']}",
        FAKE_POOLS=pools,
        OCI_CLI_AUTH="security_token",
        OCI_CLI_CONFIG_FILE=str(cfg),
    )
    return subprocess.run(
        [str(b / "idp-verify-drill")],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )


def _cluster_row(r):
    rows = [ln for ln in r.stdout.splitlines() if ln.split()[1:2] == ["cluster"]]
    assert len(rows) == 1, r.stdout + r.stderr
    return rows[0]


def test_incident_crew516_other_state_is_red_and_named(tmp_path):
    row = _cluster_row(_run(tmp_path, "amd-std ACTIVE\na1-spot DELETING\n"))
    assert row.startswith("FAIL ") and "a1-spot(DELETING)" in row, row
