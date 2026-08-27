"""Incident crew#300 / crew#516 CP8, 2026-08-27: recovery existed as prose and a Mac-side escrow
job (~/.claude/scripts/estate/estate_bundle_push.sh) that nobody had ever restored from on a
machine without the laptop's keys. The rule (rung 4, incident test): a weekly GitHub job with no
static credential clones the load-bearing repositories on an App token narrowed to a read-only
lane, reads back and verifies the escrow bundles with the R2 keys taken from the vault on the OIDC
identity, and boots the platform's own drill from the fresh clone; it is catalogued with its own
cron and it never asks a person for anything. Offline: the script is exercised with stubbed
binaries and no network."""
import json
import os
import re
import stat
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "recover-drill.yml"
SCRIPT = ROOT / "bin" / "idp-recover-drill"
TOKEN_EXCHANGE = "gtrevorrow/oci-token-exchange-action"


def test_recover_drill_is_weekly_on_the_exchanged_oidc_session_with_no_static_credential() -> None:
    wf = yaml.safe_load(WF.read_text())
    assert [s["cron"] for s in wf[True]["schedule"]] == ["41 4 * * 0"]
    assert "workflow_dispatch" in wf[True] and SCRIPT.relative_to(ROOT).as_posix() in wf[True]["pull_request"]["paths"]
    assert wf["permissions"] == {"id-token": "write", "contents": "read"}
    steps = wf["jobs"]["recover"]["steps"]
    assert any(TOKEN_EXCHANGE in s.get("uses", "") for s in steps), "no token exchange step"
    drill = next(s for s in steps if "bin/idp-recover-drill" in s.get("run", ""))
    assert drill["env"]["OCI_CLI_AUTH"] == "security_token"
    assert "GH_TOKEN" not in drill["env"], "the clones must use the App lane, not the job's own token"
    text = WF.read_text()
    assert not re.search(r"OCI_(API|PRIVATE)_KEY|FINGERPRINT|PASSWORD|R2_|RCLONE_", text), "a static credential on the recovery path"
    assert any(s.get("name") == "recover-receipt" for s in (st.get("with", {}) for st in steps)), "no receipt artifact"


def test_recover_drill_is_catalogued_with_its_own_cron_verbatim() -> None:
    drills = {d["name"]: d for d in yaml.safe_load((ROOT / "drills" / "catalogue.yaml").read_text())["drills"]}
    row = drills["recover-clean-machine"]
    assert row["workflow"] == "recover-drill.yml" and "pending" not in row
    wf = yaml.safe_load((ROOT / ".github" / "workflows" / row["workflow"]).read_text())
    assert row["schedule"] == wf[True]["schedule"][0]["cron"]
    assert 168 < row["max_age_hours"] <= 194, "a weekly drill: seven days plus GitHub's scheduling slack"


def test_the_recovery_lane_can_only_read_and_the_vault_is_found_by_name_not_tofu_state() -> None:
    lanes = json.loads((ROOT / "platform" / "github-app" / "lanes.json").read_text())
    assert lanes["recovery"] == {"metadata": "read", "contents": "read"}, lanes["recovery"]
    app = (ROOT / "bin" / "idp-github-app").read_text()
    assert app.count("V=${ESTATE_VAULT_OCID:-$(cd") == 2, "both vault lookups must accept the override a runner without tofu state needs"
    script = SCRIPT.read_text()
    assert "tofu output" not in script and "oci kms management vault list" in script
    assert 'ESTATE_VAULT_OCID="$V"' in script
    assert "sops" not in script and "~/.oci" not in script and "age-key" not in script
    assert not re.search(r"ocid1\.[a-z]+\.oc1\.[a-z0-9.-]*\.[a-z0-9]{20,}", script), "an OCID literal (LAW 46)"
    assert SCRIPT.stat().st_mode & stat.S_IXUSR


def _run(env: dict, tmp: Path) -> subprocess.CompletedProcess:
    stubs = tmp / "stubs"; stubs.mkdir(exist_ok=True)
    for name in ("oci", "rclone"):
        s = stubs / name
        s.write_text("#!/bin/sh\necho stub-$0 >> \"$STUB_LOG\"\nexit 1\n"); s.chmod(0o755)
    full = {"PATH": f"{stubs}:{os.environ['PATH']}", "HOME": str(tmp), "STUB_LOG": str(tmp / "calls"),
            "RECOVER_WORK": str(tmp / "work"), "RECOVER_RECEIPT_DIR": str(tmp / "receipt"), **env}
    return subprocess.run([str(SCRIPT)], env=full, capture_output=True, text=True, timeout=60)


def test_without_an_exchanged_session_the_drill_is_blind_and_touches_no_network(tmp_path: Path) -> None:
    r = _run({"OCI_COMPARTMENT_OCID": "ocid1.compartment.oc1..stub"}, tmp_path)
    assert r.returncode == 2, r.stdout + r.stderr
    assert r.stdout.startswith("BLIND   recover-drill"), r.stdout
    assert not (tmp_path / "calls").exists(), "a blind drill must not call oci or rclone"
    assert (tmp_path / "receipt" / "rows.txt").read_text() == r.stdout, "the receipt is the rows, verbatim"


def test_when_the_vault_cannot_be_listed_the_drill_is_blind_not_red(tmp_path: Path) -> None:
    r = _run({"OCI_COMPARTMENT_OCID": "ocid1.compartment.oc1..stub", "OCI_CLI_AUTH": "security_token"}, tmp_path)
    assert r.returncode == 2 and "BLIND   vault" in r.stdout, r.stdout + r.stderr
    assert (tmp_path / "calls").read_text().count("oci") == 1, "one vault listing, nothing after a blind vault"
