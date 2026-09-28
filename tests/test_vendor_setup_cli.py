"""Subprocess tests for bin/idp-vendor-setup: exercise the real script, no browser road."""

import pathlib
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLI = ROOT / "bin" / "idp-vendor-setup"

ROWS = {
    "fed": {
        "kind": "secret",
        "page": "https://example.invalid/fed",
        "store_default": "estate-vault",
        "targets": [],
        "setup": {"road": "oidc"},
    },
    "manual": {
        "kind": "secret",
        "page": "https://example.invalid/keys",
        "store_default": "human-vault",
        "targets": [{"ns": "llm", "field": "X"}],
    },
    "broken": {
        "kind": "secret",
        "store_default": "human-vault",
        "targets": [{"ns": "llm", "field": "X"}],
        "setup": {
            "road": "browser",
            "entry": "e",
            "steps": [{"capture": {"field": "X", "regex": "x"}}],
        },
        "verify": {"method": "GET", "url": "https://example.invalid"},
    },
}


def _run(vendor, tmp_path, extra_env=None):
    consoles = tmp_path / "consoles.yaml"
    consoles.write_text(yaml.safe_dump({"vendors": ROWS}))
    env = {
        **__import__("os").environ,
        "IDP_VENDOR_CONSOLES": str(consoles),
        "ESTATE_HOME": str(tmp_path / "estate"),
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(CLI), vendor],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_oidc_needs_no_key(tmp_path):
    r = _run("fed", tmp_path)
    assert r.returncode == 0
    assert "no key: identity federation" in r.stdout


def test_assisted_names_the_page(tmp_path):
    r = _run("manual", tmp_path)
    assert r.returncode == 3
    assert "https://example.invalid/keys" in r.stdout


def test_broken_row_fails_validation(tmp_path):
    r = _run("broken", tmp_path)
    assert r.returncode == 1
    assert "estate-vault" in r.stdout
    assert "broken" in r.stdout


def test_unknown_vendor_fails(tmp_path):
    r = _run("nope", tmp_path)
    assert r.returncode == 1
    assert "nope" in r.stdout


def test_help_exits_zero(tmp_path):
    r = subprocess.run(
        [sys.executable, str(CLI), "--help"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0
