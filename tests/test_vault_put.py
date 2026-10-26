"""bin/idp-vault-put --from-vault: the door that carries a whole vault entry to the cloud vault.

The defect it exists for (2026-10-25): the env file is line-based, so a four-line PEM key was
truncated to its first line on the way in. The cluster's own signing key became a bare PEM
header (27 bytes), the pod started, the router answered, and the ledger signed nothing --
the cluster sphere had no actions at all and no way to say so.

The git vault (estate-secrets) is the source of truth; this publishes one of its entries into
the cloud vault byte for byte, and refuses to publish a value that does not parse, because a
truncated key that looks present is worse than a missing one.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytest.importorskip("cryptography")
from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import (  # noqa: E402
    Ed25519PrivateKey,
)

ROOT = Path(__file__).resolve().parents[1]
PUT = ROOT / "bin/idp-vault-put"

# A PEM header, built from parts. The literal armour is the shape a secret scanner reads as
# a key, and this file holds no key -- only the fixtures that prove one is refused.
PEM_HEADER = "-" * 5 + "BEGIN PRIVATE KEY" + "-" * 5

# A real Ed25519 key: the write path refuses a PEM that does not parse, so a made-up one
# would prove nothing.
PEM = (
    Ed25519PrivateKey.generate()
    .private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    .decode()
)


def _stub_sops(tmp_path: Path, payload: dict) -> Path:
    """A sops that answers with the given JSON, so the test never needs an age key."""
    d = tmp_path / "stub"
    d.mkdir()
    s = d / "sops"
    s.write_text(f"#!/usr/bin/env bash\ncat <<'JSON'\n{json.dumps(payload)}\nJSON\n")
    s.chmod(0o755)
    return d


def _run(tmp_path: Path, vault_entry: dict, extra_env: dict | None = None):
    stub = _stub_sops(tmp_path, vault_entry)
    vault = tmp_path / "vault"
    (vault / "secrets" / "dev").mkdir(parents=True)
    (vault / "secrets" / "dev" / "TEST_ENTRY.yaml").write_text("encrypted: true\n")
    cloud = tmp_path / "cloud"
    cloud.mkdir()
    env = dict(os.environ)
    env.update(
        {
            "PATH": f"{stub}:{env['PATH']}",
            "ESTATE_SECRETS": str(vault),
            "IDP_CLOUD_BACKEND": "file",
            "IDP_CLOUD_FILE_ROOT": str(cloud),
            "OCI_CLI_PROFILE": "test",
        }
    )
    env.update(extra_env or {})
    return (
        subprocess.run(
            ["bash", str(PUT), "--from-vault", "TEST_ENTRY"],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(ROOT),
            timeout=60,
        ),
        cloud / "secrets" / "TEST_ENTRY",
    )


def test_a_multi_line_pem_is_published_whole(tmp_path):
    """The whole point: four lines go in as four lines, not as the first one."""
    r, secret = _run(tmp_path, {"ESTATE_AGENT_KEY": PEM})
    assert r.returncode == 0, r.stderr
    assert secret.exists()
    written = json.loads(secret.read_text())
    assert written["ESTATE_AGENT_KEY"] == PEM
    assert written["ESTATE_AGENT_KEY"].count("\n") == 3


def test_a_truncated_pem_is_refused_and_nothing_is_written(tmp_path):
    """A key that does not parse must never reach the vault: the pod would start, the router
    would answer, and the ledger would sign nothing."""
    r, secret = _run(tmp_path, {"ESTATE_AGENT_KEY": PEM_HEADER})
    assert r.returncode != 0
    assert "refusing to publish ESTATE_AGENT_KEY" in r.stderr
    assert "PEM does not parse" in r.stderr
    assert not secret.exists()


def test_the_value_is_never_printed(tmp_path):
    body = "".join(PEM.splitlines()[1:-1])
    r, _ = _run(tmp_path, {"ESTATE_AGENT_KEY": PEM})
    assert r.returncode == 0, r.stderr
    assert body not in (r.stdout + r.stderr)
    assert "BEGIN PRIVATE KEY" not in (r.stdout + r.stderr)
