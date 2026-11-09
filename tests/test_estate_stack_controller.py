"""The stack controller's falsifier: yield closes ONLY on verified user-path.

The controller (bin/estate-stack-controller) turns an approved stack intent into one
signed stack receipt. Its single safety-critical invariant is that the yield must NOT
close unless the user-path stages (deploy-router, deploy-dsh, verify-doors) measured ok
on their real path. This test proves that by driving the controller against fakes and
asserting the receipt verdict is `open` when the user path is not verified.
"""

import importlib.util
import json
import os
import sys
from importlib.machinery import SourceFileLoader


def _load_controller():
    path = os.path.join(
        os.path.dirname(__file__), "..", "bin", "estate-stack-controller"
    )
    spec = importlib.util.spec_from_loader(
        "estate_stack_controller", SourceFileLoader("estate_stack_controller", path)
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["estate_stack_controller"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_yield_stays_open_when_user_path_is_not_verified(monkeypatch, tmp_path):
    mod = _load_controller()

    # Fake a present gate that approves; the controller will call it by path.
    gate = tmp_path / "idp-stack-gate"
    gate.write_text("#!/bin/sh\nexit 0\n")
    gate.chmod(0o755)
    monkeypatch.setattr(mod, "STACK_GATE", str(gate))

    # Fake the rebuild primitive: approve plan and policy.
    rebuild = tmp_path / "idp-oke-rebuild"
    rebuild.write_text("#!/bin/sh\nexit 0\n")
    rebuild.chmod(0o755)
    monkeypatch.setattr(mod, "REBUILD", str(rebuild))

    # Fake the homes primitive to report a board where the doors are NOT verified
    # (zero lanes measured OK -> the door stage returns rc=1).
    homes = tmp_path / "idp-estate-homes"
    homes.write_text('#!/bin/sh\necho \'{"lanes": [{"verdict": "MEASURED_FAIL"}]}\'\n')
    homes.chmod(0o755)
    monkeypatch.setattr(mod, "HOMES", str(homes))

    # Router answers 200 (so one user-path stage is ok), but doors do NOT -> yield open.
    monkeypatch.setattr(
        mod, "_curl_ok", lambda url: (0, "HTTP 200") if url else (2, "BLIND")
    )
    monkeypatch.setattr(mod, "DSH_HEALTH", "")

    receipt = tmp_path / "receipt.json"
    # Call main with argv directly.
    sys.argv = [
        "estate-stack-controller",
        "approve-intent",
        "--verify-only",
        "--receipt",
        str(receipt),
    ]
    exit_code = mod.main()

    doc = json.loads(receipt.read_text())
    # The doors stage reported zero lanes OK -> user path not verified -> open.
    assert doc["verdict"] == "open", doc
    assert exit_code == 1


def test_yield_closes_when_user_path_is_verified(monkeypatch, tmp_path):
    mod = _load_controller()

    gate = tmp_path / "idp-stack-gate"
    gate.write_text("#!/bin/sh\nexit 0\n")
    gate.chmod(0o755)
    monkeypatch.setattr(mod, "STACK_GATE", str(gate))

    rebuild = tmp_path / "idp-oke-rebuild"
    rebuild.write_text("#!/bin/sh\nexit 0\n")
    rebuild.chmod(0o755)
    monkeypatch.setattr(mod, "REBUILD", str(rebuild))

    homes = tmp_path / "idp-estate-homes"
    homes.write_text('#!/bin/sh\necho \'{"lanes": [{"verdict": "MEASURED_OK"}]}\'\n')
    homes.chmod(0o755)
    monkeypatch.setattr(mod, "HOMES", str(homes))

    monkeypatch.setattr(
        mod, "_curl_ok", lambda url: (0, "HTTP 200") if url else (2, "BLIND")
    )
    monkeypatch.setattr(
        mod, "DSH_HEALTH", "https://dsh.example/health"
    )  # provisioned -> 200

    receipt = tmp_path / "receipt.json"
    sys.argv = [
        "estate-stack-controller",
        "approve-intent",
        "--verify-only",
        "--receipt",
        str(receipt),
    ]
    exit_code = mod.main()

    doc = json.loads(receipt.read_text())
    assert doc["verdict"] == "closed", doc
    assert exit_code == 0
