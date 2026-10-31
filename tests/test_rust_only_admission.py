"""The Rust-only admission gate must be able to fail.

A gate that cannot fail is not a gate (estate law, section 9 principle 1). This is the
falsifier: a known-bad Python service must be refused with the exact message, a known-good
Rust service must be admitted, a legacy image must be admitted only when it carries a
recorded grandfather entry, and the estate's own images must not be broken by the gate.

The founder's ruling (2026-10-31): the Oracle k3s spine is Rust-only. Any service
containing Python is rejected at the admission gate.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(ROOT, "platform", "estate", "libexec", "rust-only-admission.py")
FIXTURES = os.path.join(ROOT, "tests", "fixtures", "rust-only")
DENY_MESSAGE = "ADMISSION DENIED: Services targeting the k3s spine must be written in Rust."


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, ENGINE, *args], cwd=ROOT,
                          capture_output=True, text=True, timeout=120)


def _scan(fixture: str, *extra: str) -> subprocess.CompletedProcess:
    context = os.path.join(FIXTURES, fixture)
    dockerfile = os.path.join(context, "Dockerfile")
    return _run("--repo-root", ROOT, "--context", context, "--dockerfile", dockerfile,
                "--image", fixture, "--allowlist", os.path.join(FIXTURES, "no-allowlist.json"),
                *extra)


def test_the_message_is_exactly_what_the_ruling_says() -> None:
    """The refusal text is the contract; a rewording is a regression."""
    spec = importlib.util.spec_from_file_location("rust_only_admission", ENGINE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.DENY_MESSAGE == DENY_MESSAGE


def test_a_known_bad_python_service_is_denied() -> None:
    p = _scan("bad-python-service")
    assert p.returncode == 4, p.stdout + p.stderr
    assert p.stdout.splitlines()[0] == DENY_MESSAGE


def test_a_known_good_rust_service_is_admitted() -> None:
    p = _scan("good-rust-service")
    assert p.returncode == 0, p.stdout + p.stderr
    assert "ADMISSION OK" in p.stdout


def test_a_python_base_image_is_denied_even_with_no_python_file() -> None:
    p = _scan("bad-python-base")
    assert p.returncode == 4, p.stdout + p.stderr
    assert p.stdout.splitlines()[0] == DENY_MESSAGE
    assert "python_base_image" in p.stdout


def test_a_grandfathered_legacy_image_is_admitted() -> None:
    allowlist = os.path.join(FIXTURES, "allowlist.json")
    p = _run("--repo-root", ROOT, "--context", os.path.join(FIXTURES, "bad-python-service"),
             "--dockerfile", os.path.join(FIXTURES, "bad-python-service", "Dockerfile"),
             "--image", "bad-python-service", "--allowlist", allowlist)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "grandfathered" in p.stdout


def test_an_allowlist_entry_without_a_reason_does_not_grandfather() -> None:
    allowlist = os.path.join(FIXTURES, "allowlist-no-reason.json")
    p = _run("--repo-root", ROOT, "--context", os.path.join(FIXTURES, "bad-python-service"),
             "--dockerfile", os.path.join(FIXTURES, "bad-python-service", "Dockerfile"),
             "--image", "bad-python-service", "--allowlist", allowlist)
    assert p.returncode == 4, p.stdout + p.stderr
    assert p.stdout.splitlines()[0] == DENY_MESSAGE


def test_the_estates_own_images_are_not_broken_by_the_gate() -> None:
    """Every image the estate builds today is either Rust or explicitly grandfathered."""
    p = _run("--repo-root", ROOT)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "ADMISSION OK" in p.stdout


def test_the_policy_allowlist_records_owner_reason_and_expiry() -> None:
    with open(os.path.join(ROOT, "policy", "rust-only-allowlist.json"), encoding="utf-8") as fh:
        doc = json.load(fh)
    assert doc["denial_message"] == DENY_MESSAGE
    assert doc["allow"], "the legacy allowlist must not be empty"
    for entry in doc["allow"]:
        for key in ("image", "reason", "owner", "expires"):
            assert entry.get(key), f"allowlist entry {entry} is missing {key}"
