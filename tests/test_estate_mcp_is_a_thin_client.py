"""estate-mcp is a thin client: no laptop door, in manifest or code.

idp#8061.
"""

import importlib.util
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/mcp/estate-mcp.yaml"
PLUGIN = ROOT / "mcp/plugins/estate_mcp.py"


def _plugin():
    spec = importlib.util.spec_from_file_location("estate_mcp", PLUGIN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_manifest_has_no_laptop_door():
    text = MANIFEST.read_text()
    assert "ESTATE_LAPTOP_INTENT_URL" not in text
    assert "fleetview-mac" not in text


def test_no_cloud_door_refuses_blind(monkeypatch):
    monkeypatch.delenv("ESTATE_CLOUD_INTENT_URL", raising=False)
    out = _plugin()._invoke_cloud("pr.list", [], "", 5)
    assert out.startswith("BLIND"), out


def test_a_configured_door_is_used(monkeypatch):
    mod = _plugin()
    monkeypatch.setenv("ESTATE_CLOUD_INTENT_URL", "https://x/invoke")
    monkeypatch.setattr(mod, "_invoke_remote", lambda *a: "OK")
    assert mod._invoke_cloud("pr.list", [], "", 5) == "OK"
