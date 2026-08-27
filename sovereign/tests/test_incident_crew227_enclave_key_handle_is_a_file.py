"""Incident, crew#227 CP5 (2026-08-27): `estate-presence --pubkey` hung (rc=124) on the founder's Mac
because the Secure Enclave key handle lived in the login keychain, and every ad hoc rebuild of the
helper was a new identity to the keychain ACL, so macOS raised a consent dialog nobody was at the
screen to click. Rule (rung 4): the key handle is a 0600 file under $ESTATE_HOME/sovereign, named by
config, and the helper is told where it is on every call, so no keychain and no dialog is involved."""
import os
from pathlib import Path

import pytest

from sovereign.trust import anchor
from sovereign.trust import config_keys as ck


def test_key_handle_path_is_config_named_under_estate_home(monkeypatch, tmp_path):
    monkeypatch.setenv("ESTATE_HOME", str(tmp_path))
    p = anchor._enclave_key_path()
    assert p == tmp_path / ck.get("trust.sovereign_dirname") / ck.get("trust.enclave_key_filename")
    assert p.name == "enclave.key"


def test_helper_is_told_the_key_file_on_every_call(monkeypatch, tmp_path):
    monkeypatch.setenv("ESTATE_HOME", str(tmp_path))
    helper = tmp_path / "bin" / "estate-presence"
    monkeypatch.setattr(anchor, "_ensure_swift_helper_compiled", lambda: helper)
    seen = {}

    def run(cmd, **kw):
        seen["cmd"], seen["env"] = cmd, kw.get("env") or {}
        return type("R", (), {"stdout": '{"ok":true}'})()

    monkeypatch.setattr(anchor.subprocess, "run", run)
    assert anchor._run_helper(["--pubkey"], timeout=1) == {"ok": True}
    assert seen["cmd"][0] == str(helper)
    assert seen["env"]["SOVEREIGN_ENCLAVE_KEY_FILE"] == str(anchor._enclave_key_path())
    assert "PATH" in seen["env"], "the helper keeps the caller's environment, only the key file is added"


def test_helper_source_never_touches_the_keychain():
    src = Path(anchor.__file__).with_name("presence_helper.swift").read_text()
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("//"))
    assert "SecItem" not in code and "kSecClass" not in code
    assert "SOVEREIGN_ENCLAVE_KEY_FILE" in code
