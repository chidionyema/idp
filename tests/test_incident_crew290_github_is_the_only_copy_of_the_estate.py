"""crew#290 layer 4: every load-bearing repository had one remote, GitHub, and the only escrow
writer was a launchd job on the founder's Mac whose bundles for a repo with a remote were
incremental (recover-drill run 33131027676 restored 8 of 24). The 2026-08-26 plan needed the
founder to open a Codeberg account, so nothing was ticked for two days. bin/idp-escrow runs on a
GitHub runner over the exchanged OIDC session, mints a read-only App token, and writes a full
`git bundle --all` of every repository the installation sees to R2, reading each one back.

These tests pin the shape that made it deliverable with no founder hand: no static credential in
the workflow, a read-only lane, BLIND (never a call to the world) without the exchanged session,
the catalogue row copied from the cron, and the Mac's bundles/ prefix never written."""

import json
import os
import re
import stat
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-escrow"
WORKFLOW = ROOT / ".github" / "workflows" / "estate-escrow.yml"
CATALOGUE = ROOT / "drills" / "catalogue.yaml"
LANES = ROOT / "platform" / "github-app" / "lanes.json"


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text())


def _cron() -> str:
    wf = _workflow()
    return (
        wf[True]["schedule"][0]["cron"]
        if True in wf
        else wf["on"]["schedule"][0]["cron"]
    )


def test_script_is_executable_and_parses():
    assert SCRIPT.stat().st_mode & stat.S_IXUSR
    subprocess.run(["bash", "-n", str(SCRIPT)], check=True)


def test_catalogue_row_copies_the_workflow_cron():
    rows = {d["name"]: d for d in yaml.safe_load(CATALOGUE.read_text())["drills"]}
    row = rows["estate-escrow"]
    assert row["workflow"] == "estate-escrow.yml"
    assert row["schedule"] == _cron() == "29 */6 * * *"
    assert row["max_age_hours"] == 13  # six-hourly plus GitHub's scheduling slack
    assert "pending" not in row


def test_workflow_carries_no_static_credential_and_only_asks_for_an_oidc_token():
    text = WORKFLOW.read_text()
    assert not re.search(
        r"OCI_(API|PRIVATE)_KEY|FINGERPRINT|PASSWORD|R2_|RCLONE_", text
    ), text
    wf = _workflow()
    assert wf["permissions"] == {"id-token": "write", "contents": "read"}
    steps = wf["jobs"]["escrow"]["steps"]
    assert any("oci-token-exchange-action" in s.get("uses", "") for s in steps)
    run = next(s for s in steps if "bin/idp-escrow" in s.get("run", ""))
    assert run["env"]["OCI_CLI_AUTH"] == "security_token"


def test_recovery_lane_is_read_only():
    lanes = json.loads(LANES.read_text())
    assert lanes["recovery"] == {"metadata": "read", "contents": "read"}
    assert "token recovery" in SCRIPT.read_text()


def test_script_never_names_an_ocid_or_a_bucket_literal_and_never_touches_mac_bundles():
    text = SCRIPT.read_text()
    assert not re.search(r"ocid1\.[a-z]+\.oc1\.", text)
    assert "ESCROW_PREFIX:-mirrors" in text
    assert "bundles/" not in re.sub(
        r"^#.*$", "", text, flags=re.M
    )  # only the header may mention the Mac prefix


def test_blind_without_exchanged_session_makes_no_call_to_the_world(tmp_path):
    b = tmp_path / "bin"
    b.mkdir()
    log = tmp_path / "calls.log"
    for tool in ("oci", "rclone", "curl", "git"):
        (b / tool).write_text(f"#!/bin/sh\necho {tool} \"$@\" >> '{log}'\nexit 1\n")
        (b / tool).chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{b}:{os.environ['PATH']}",
        "OCI_COMPARTMENT_OCID": "x",
        "ESCROW_WORK": str(tmp_path / "w"),
        "ESCROW_RECEIPT_DIR": str(tmp_path / "r"),
    }
    env.pop("OCI_CLI_AUTH", None)
    (tmp_path / "w").mkdir()
    p = subprocess.run([str(SCRIPT)], env=env, capture_output=True, text=True)
    assert p.returncode == 2, p.stdout + p.stderr
    assert p.stdout.startswith("BLIND") and "security_token" in p.stdout
    assert not log.exists(), log.read_text()


def test_blind_when_vault_is_absent_before_any_github_or_r2_call(tmp_path):
    b = tmp_path / "bin"
    b.mkdir()
    log = tmp_path / "calls.log"
    (b / "oci").write_text("#!/bin/sh\necho null\n")
    for tool in ("rclone", "curl"):
        (b / tool).write_text(f"#!/bin/sh\necho {tool} >> '{log}'\nexit 1\n")
    for f in b.iterdir():
        f.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{b}:{os.environ['PATH']}",
        "OCI_COMPARTMENT_OCID": "x",
        "OCI_CLI_AUTH": "security_token",
        "ESCROW_WORK": str(tmp_path / "w"),
        "ESCROW_RECEIPT_DIR": str(tmp_path / "r"),
    }
    (tmp_path / "w").mkdir()
    p = subprocess.run([str(SCRIPT)], env=env, capture_output=True, text=True)
    assert p.returncode == 2
    assert "BLIND" in p.stdout and "estate-secrets" in p.stdout
    assert not log.exists()
