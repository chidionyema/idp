"""voice-router's launcher points the laptop router at unified estate memory, as the cluster pod is.

The router reads its key from ESTATE_MCP_KEY_FILE on every call (internal/estatemem), so the
launcher writes the vault's dev/MCP_GATEWAY_KEY to a 0600 file and names the door from the same
manifest the Mac bridge reads. No key or no manifest: the router starts ungrounded, as before.
"""

from __future__ import annotations

import json
import runpy
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAUNCHER = ROOT / "bin/voice-router-launchd"
URL = "https://door.example/estate/mcp"


def _mod(monkeypatch, secret_load: Path):
    monkeypatch.setenv("ESTATE_SECRET_LOAD", str(secret_load))
    # set, then delete: monkeypatch only undoes a variable it saw, so the launcher's writes are undone
    for name in ("MCP_GATEWAY_KEY", "ESTATE_MCP_URL", "ESTATE_MCP_KEY_FILE"):
        monkeypatch.setenv(name, "")
        monkeypatch.delenv(name)
    return runpy.run_path(str(LAUNCHER), run_name="voice_router_launchd")


def _manifest(tmp_path: Path) -> Path:
    m = tmp_path / "runtimes.json"
    m.write_text(
        json.dumps(
            {
                "door": {
                    "url": URL,
                    "key_env": "MCP_GATEWAY_KEY",
                    "vault_entry": ["dev", "MCP_GATEWAY_KEY", "MCP_GATEWAY_KEY"],
                }
            }
        )
    )
    return m


def test_the_vault_key_lands_in_a_private_file_the_router_is_pointed_at(
    tmp_path, monkeypatch
):
    fake = tmp_path / "secret-load"
    fake.write_text(
        '[ "$*" = "dev MCP_GATEWAY_KEY MCP_GATEWAY_KEY" ] && printf mcp-fake\n'
    )
    mod = _mod(monkeypatch, fake)
    key_file = tmp_path / "state/estate-mcp.key"
    assert mod["estate_memory"]([_manifest(tmp_path)], key_file) is True
    assert key_file.read_text() == "mcp-fake"
    assert stat.S_IMODE(key_file.stat().st_mode) == 0o600
    env = mod["os"].environ
    assert env["ESTATE_MCP_URL"] == URL
    assert env["ESTATE_MCP_KEY_FILE"] == str(key_file)


def test_a_vault_that_cannot_answer_leaves_the_router_ungrounded(tmp_path, monkeypatch):
    fake = tmp_path / "secret-load"
    fake.write_text("echo 'sops: cannot decrypt' >&2; exit 1\n")
    mod = _mod(monkeypatch, fake)
    key_file = tmp_path / "estate-mcp.key"
    assert mod["estate_memory"]([_manifest(tmp_path)], key_file) is False
    assert not key_file.exists()
    assert "ESTATE_MCP_URL" not in mod["os"].environ


def test_no_manifest_leaves_the_router_ungrounded(tmp_path, monkeypatch):
    mod = _mod(monkeypatch, tmp_path / "never-called")
    assert mod["estate_memory"]([tmp_path / "missing.json"], tmp_path / "k") is False


def test_the_checkout_manifest_is_the_one_the_bridge_reads(tmp_path, monkeypatch):
    mod = _mod(monkeypatch, tmp_path / "unused")
    want = ROOT / "platform/estate/memory/runtimes.json"
    assert want in mod["MANIFESTS"]
    assert json.loads(want.read_text())["door"]["key_env"] == "MCP_GATEWAY_KEY"
