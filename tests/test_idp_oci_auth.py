"""OCI auth is selected from the profile that actually exists, never guessed."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-oci-auth"


def _run(tmp_path: Path, profile: str) -> subprocess.CompletedProcess:
    config = tmp_path / "config"
    config.write_text(
        """
[DEFAULT]
user=ocid1.user.oc1..example
fingerprint=aa:bb
tenancy=ocid1.tenancy.oc1..example
region=uk-london-1
key_file=/tmp/example.pem

[estate-bootstrap]
user=ocid1.user.oc1..example
fingerprint=aa:bb
tenancy=ocid1.tenancy.oc1..example
region=uk-london-1
security_token_file=/tmp/token
"""
    )
    return subprocess.run(
        [str(SCRIPT), profile],
        env={"HOME": str(tmp_path), "OCI_CONFIG_FILE": str(config), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_api_key_profile_is_not_forced_into_a_security_token(tmp_path):
    out = _run(tmp_path, "DEFAULT")
    assert out.returncode == 0
    assert out.stdout.strip() == "api_key"


def test_security_token_profile_stays_a_security_token(tmp_path):
    out = _run(tmp_path, "estate-bootstrap")
    assert out.returncode == 0
    assert out.stdout.strip() == "security_token"


def test_missing_profile_is_loud(tmp_path):
    out = _run(tmp_path, "not-a-profile")
    assert out.returncode != 0
    assert "not-a-profile" in out.stderr
