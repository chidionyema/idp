"""crew#163 residual / crew#345 box 3 (measured 2026-08-27): the Mac has no OCI identity, so
bin/idp-hc-enroll's only door (the vault) was BLIND and hc-wrap pinged 127.0.0.1:8000 for weeks.
The fix is a second door: bin/idp-hc-publish leaves the key in the receipts bucket encrypted to
platform/healthchecks/mac.recipients; enrol falls back to it. Both ways on the file backend."""
import os
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(shutil.which("age") is None, reason="age missing: ci.yml installs it; a laptop without it must not pass silently")


def _env(tmp_path, home):
    return {**os.environ, "IDP_CLOUD_BACKEND": "file", "IDP_CLOUD_FILE_ROOT": str(tmp_path / "cloud"),
            "HOME": str(home), "ESTATE_ZONE": "example.test", "HC_RECIPIENTS": str(tmp_path / "recipients")}


def _keys(tmp_path, home):
    ident = home / ".config/prospector/age-key.txt"; ident.parent.mkdir(parents=True)
    subprocess.run(["age-keygen", "-o", str(ident)], check=True, capture_output=True)
    pub = subprocess.run(["age-keygen", "-y", str(ident)], check=True, capture_output=True, text=True).stdout
    (tmp_path / "recipients").write_text("# test recipient\n" + pub)


def test_publish_then_enrol_through_the_bucket_when_the_vault_is_unreadable(tmp_path):
    home = tmp_path / "home"; home.mkdir(); _keys(tmp_path, home)
    env = _env(tmp_path, home)
    sec = tmp_path / "cloud/secrets"; sec.mkdir(parents=True); (sec / "healthchecks-ping-key").write_text("0123456789abcdef-ping")
    pub = subprocess.run([str(ROOT / "bin/idp-hc-publish")], capture_output=True, text=True, env=env)
    assert pub.returncode == 0 and pub.stdout.startswith("ok      hc-publish"), pub.stdout + pub.stderr
    assert "recipients=1" in pub.stdout and "ping" not in pub.stdout.split("bytes=")[1]
    blob = (tmp_path / "cloud/objects/estate-drill-receipts/healthchecks/ping_key.age").read_bytes()
    assert b"0123456789abcdef" not in blob, "the bucket object must be ciphertext"
    assert blob.startswith(b"-----BEGIN AGE ENCRYPTED FILE-----"), "armored: a raw blob has NUL bytes no shell pipeline keeps (found 2026-08-27, 3 of 6 runs)"
    (sec / "healthchecks-ping-key").unlink()  # the Mac's situation: no vault door
    enr = subprocess.run([str(ROOT / "bin/idp-hc-enroll")], capture_output=True, text=True, env=env)
    assert enr.returncode == 0 and "via=bucket" in enr.stdout, enr.stdout + enr.stderr
    assert (home / ".estate/healthchecks/ping_key").read_text() == "0123456789abcdef-ping\n"
    assert (home / ".estate/healthchecks/base").read_text() == "https://hc.example.test/ping\n"
    assert "0123456789abcdef-ping" not in enr.stdout


def test_enrol_is_blind_not_silent_when_neither_door_opens(tmp_path):
    home = tmp_path / "home"; home.mkdir(); _keys(tmp_path, home)
    env = {**_env(tmp_path, home), "ESTATE_SECRETS": str(tmp_path / "no-envelope")}
    (tmp_path / "cloud/secrets").mkdir(parents=True)
    enr = subprocess.run([str(ROOT / "bin/idp-hc-enroll")], capture_output=True, text=True, env=env)
    assert enr.returncode == 2 and enr.stdout.startswith("BLIND   hc-enroll"), enr.stdout + enr.stderr
    assert not (home / ".estate/healthchecks/ping_key").exists()


def test_the_vault_door_still_comes_first(tmp_path):
    home = tmp_path / "home"; home.mkdir(); _keys(tmp_path, home)
    env = _env(tmp_path, home)
    sec = tmp_path / "cloud/secrets"; sec.mkdir(parents=True); (sec / "healthchecks-ping-key").write_text("vault-key-value")
    enr = subprocess.run([str(ROOT / "bin/idp-hc-enroll")], capture_output=True, text=True, env=env)
    assert enr.returncode == 0 and "via=vault" in enr.stdout, enr.stdout + enr.stderr


def test_publish_runs_hourly_and_ci_has_age():
    oke = (ROOT / ".github/workflows/oke-check.yml").read_text()
    assert "bin/idp-hc-publish" in oke and "apt-get install -y -q age" in oke
    assert "age" in (ROOT / ".github/workflows/ci.yml").read_text().split("shellcheck jq sqlite3")[1].split("\n")[0]
    rec = (ROOT / "platform/healthchecks/mac.recipients").read_text().split()
    assert rec and all(r.startswith("age1") for r in rec), "recipients are public age keys only"
