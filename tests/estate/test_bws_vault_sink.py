"""Falsifiers for the propagation sink: a Bitwarden entry reaches the estate vault by name.

The CEO property this protects: a credential is approved once in Bitwarden and every consumer
picks it up by name. The two ways that becomes a lie, both refused here:

  * a value printed, or passed as argv, where `ps` and a job log can read it;
  * a plaintext file left on disk after the write;
  * propagation that fires for entries the founder never meant to publish (the default is OFF
    and the prefix is `estate-`, so a personal login in the same project is not copied).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "bin" / "estate-bws-sync"


def _module():
    spec = importlib.util.spec_from_loader(
        "bws_sync", importlib.machinery.SourceFileLoader("bws_sync", str(SCRIPT))
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def harness(tmp_path: Path):
    mod = _module()
    calls: list[list[str]] = []
    seen_files: list[str] = []

    def fake_vault_put(cfg, name, value):
        calls.append([name, value])
        return 0, ""

    mod.vault_put = fake_vault_put
    mod.token = lambda *a, **k: ("machine-token", "file")
    mod.auth = lambda *a, **k: ("session-token", "ok")
    mod.encrypt = lambda value, dest, rcpt: (
        dest.parent.mkdir(parents=True, exist_ok=True),
        dest.write_text("sops:{}"),
    )
    mod.audit = lambda *a, **k: None
    mod.fetch = lambda api, at, org: [
        {"key": "estate-edge-key", "value": "s3cr3t", "revisionDate": "r1"},
        {"key": "my-bank-login", "value": "personal", "revisionDate": "r1"},
    ]

    def cfg(**over):
        base = {
            "root": tmp_path / "bws",
            "identity": "i",
            "api": "a",
            "org": "o",
            "token_file": "",
            "token_sops": "",
            "recipient": "age1xxx",
            "vault": "/bin/true",
            "vault_sink": False,
            "only_prefix": "estate-",
        }
        base.update(over)
        return base

    return mod, calls, seen_files, cfg


def test_the_sink_is_off_by_default(harness) -> None:
    mod, calls, _, cfg = harness
    state = mod.cycle(cfg())
    assert state["state"] == "ok", state
    assert calls == [], "a run without --vault-sink must write nothing to the vault"


def test_only_the_prefix_propagates(harness) -> None:
    mod, calls, _, cfg = harness
    state = mod.cycle(cfg(vault_sink=True))
    assert state["state"] == "ok", state
    assert [c[0] for c in calls] == ["estate-edge-key"], calls
    assert state["vault_puts"] == 1


def test_an_unchanged_entry_is_not_rewritten_but_a_failed_put_is_named(harness) -> None:
    mod, calls, _, cfg = harness
    assert mod.cycle(cfg(vault_sink=True))["vault_puts"] == 1
    assert mod.cycle(cfg(vault_sink=True))["vault_puts"] == 0, (
        "a second run must not re-put"
    )

    def boom(cfg_, name, value):
        return 3, "Split"

    mod.vault_put = boom
    mod.fetch = lambda api, at, org: [
        {"key": "estate-edge-key", "value": "rotated", "revisionDate": "r2"}
    ]
    state = mod.cycle(cfg(vault_sink=True, only_prefix="estate-"))
    assert state["state"] == "vault_failed", state
    assert "estate-edge-key rc=3 Split" in state["reason"], state["reason"]


def test_the_value_never_reaches_argv_and_no_plaintext_is_left(tmp_path: Path) -> None:
    mod = _module()
    dump = tmp_path / "argv.json"
    stub = tmp_path / "vault"
    stub.write_text(
        '#!/bin/sh\nfor a in "$@"; do printf "%s\\n" "$a"; done > ' + str(dump) + "\n"
    )
    stub.chmod(0o755)

    real_put = mod.vault_put
    rc, why = real_put({"vault": str(stub)}, "estate-edge-key", "s3cr3t-value")
    assert (rc, why) == (0, ""), (rc, why)

    argv = dump.read_text()
    assert "secret\nput\nestate-edge-key\n" in argv, argv
    assert "s3cr3t-value" not in argv, f"the value was passed as an argument: {argv}"
    given = [ln for ln in argv.splitlines() if ".bws-" in ln]
    assert given, f"the value must travel a file: {argv}"
    assert not any(Path(p).exists() for p in given), (
        "the mode-600 plaintext file survived the write"
    )
