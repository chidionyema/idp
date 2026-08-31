"""The customer realm is graded against git, and an admin console change is caught.

Founder, 2026-08-30: "the realm's live state must be diffable against git in CI". These hold the
properties that make that sentence true rather than decorative -- above all that the check is
never quietly green: no export is BLIND, an unreadable placeholder is BLIND, and a secret is
compared by presence so its value can never reach a CI log (R49).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
DIFF = ROOT / "bin/idp-realm-diff"
REALM = ROOT / "platform/customer-identity/realm/shop.yaml"
EXPORT = ROOT / "tests/fixtures/shop-realm-export.json"

#: The values the placeholders in the git realm stand for. The fixture was built with these.
ENV = {
    "SHOP_REDIRECT_URI": "https://shop.mumchimp.com/api/auth/callback/keycloak",
    "SHOP_ORIGIN": "https://shop.mumchimp.com",
    "SHOP_BACKEND_CLIENT_SECRET": "a-value-no-test-may-ever-print",
}


def run(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(DIFF), *args],
        capture_output=True,
        text=True,
        env={**os.environ, **ENV, **(env or {})},
    )


def export(**changes) -> dict:
    """The shipped export, with an admin console change applied on top."""
    doc = json.loads(EXPORT.read_text())
    doc.update(changes)
    return doc


def graded(tmp_path: Path, doc: dict) -> subprocess.CompletedProcess:
    path = tmp_path / "export.json"
    path.write_text(json.dumps(doc))
    return run("--export", str(path))


def test_the_realm_git_holds_is_readable_and_is_the_shop() -> None:
    doc = yaml.safe_load(REALM.read_text())
    assert doc["realm"] == "shop"
    assert {c["clientId"] for c in doc["clients"]} == {
        "storefront",
        "storefront-backend",
    }


def test_a_realm_that_matches_git_is_ok() -> None:
    r = run("--export", str(EXPORT))
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.startswith("ok      realm-diff")


def test_no_export_is_blind_never_a_pass() -> None:
    r = run()
    assert r.returncode == 2, r.stdout + r.stderr
    assert r.stdout.startswith("BLIND   realm-diff")
    assert "not a pass" in r.stdout


@pytest.mark.parametrize(
    ("change", "named"),
    [
        ({"bruteForceProtected": False}, "bruteForceProtected"),
        ({"accessTokenLifespan": 86400}, "accessTokenLifespan"),
        ({"registrationEmailAsUsername": False}, "registrationEmailAsUsername"),
        ({"verifyEmail": False}, "verifyEmail"),
        ({"sslRequired": "external"}, "sslRequired"),
        ({"revokeRefreshToken": False}, "revokeRefreshToken"),
    ],
)
def test_a_console_change_to_a_key_git_declares_is_caught(
    tmp_path: Path, change: dict, named: str
) -> None:
    r = graded(tmp_path, export(**change))
    assert r.returncode == 1, r.stdout + r.stderr
    assert r.stdout.startswith("FAIL    realm-diff")
    assert named in r.stdout


def test_an_extra_redirect_uri_on_the_browser_client_is_caught(tmp_path: Path) -> None:
    """The one that steals tokens: an attacker's URL added to the client in the console."""
    doc = json.loads(EXPORT.read_text())
    for client in doc["clients"]:
        if client["clientId"] == "storefront":
            client["redirectUris"].append("https://evil.example/callback")
    r = graded(tmp_path, doc)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "redirectUris" in r.stdout and "evil.example" in r.stdout


def test_a_key_only_the_export_carries_is_not_drift(tmp_path: Path) -> None:
    """Keycloak fills in hundreds of defaults. Git is a subset on purpose."""
    r = graded(
        tmp_path, export(smtpServer={"host": "mail.example"}, loginTheme="keycloak")
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_the_order_of_clients_and_roles_is_not_drift(tmp_path: Path) -> None:
    doc = json.loads(EXPORT.read_text())
    doc["clients"] = list(reversed(doc["clients"]))
    doc["roles"]["realm"] = list(reversed(doc["roles"]["realm"]))
    r = graded(tmp_path, doc)
    assert r.returncode == 0, r.stdout + r.stderr


def test_a_placeholder_nothing_set_is_blind_never_a_wildcard(tmp_path: Path) -> None:
    """The silent-green case: with the hostname unread, everything would 'match'."""
    r = subprocess.run(
        [sys.executable, str(DIFF), "--export", str(EXPORT)],
        capture_output=True,
        text=True,
        env={k: v for k, v in {**os.environ, **ENV}.items() if k != "SHOP_ORIGIN"},
    )
    assert r.returncode == 2, r.stdout + r.stderr
    assert "SHOP_ORIGIN" in r.stdout and "not a match" in r.stdout


def test_the_client_secret_is_never_printed(tmp_path: Path) -> None:
    """R49: a secret value never appears anywhere it can be read again -- a CI log included."""
    doc = json.loads(EXPORT.read_text())
    for client in doc["clients"]:
        if client["clientId"] == "storefront-backend":
            client["secret"] = ""  # the realm carries none, which IS drift
    r = graded(tmp_path, doc)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "carries none" in r.stdout
    assert ENV["SHOP_BACKEND_CLIENT_SECRET"] not in (r.stdout + r.stderr)


def test_a_masked_secret_is_not_drift() -> None:
    """The admin API returns `**********`; an equality test on it would be red forever."""
    doc = json.loads(EXPORT.read_text())
    assert any(c.get("secret") == "**********" for c in doc["clients"])
    r = run("--export", str(EXPORT))
    assert r.returncode == 0, r.stdout + r.stderr


def test_no_hostname_is_a_literal_in_the_git_realm() -> None:
    """LAW 46: the file names no host. Staging and production read the same bytes."""
    text = REALM.read_text()
    literals = [
        line
        for line in text.splitlines()
        if re.search(r"https?://", line)
        and "$(env:" not in line
        and not line.lstrip().startswith("#")
    ]
    assert literals == [], f"a hostname is typed into the realm: {literals}"


def test_the_checker_never_needs_the_client_secret_to_run():
    """A drift check that demands a credential to run is a credential in one more place.

    Credential-valued keys are compared by presence, so their placeholder is never read.
    The check must reach `ok` with only the two public web addresses set.
    """
    public_only = {
        "SHOP_REDIRECT_URI": ENV["SHOP_REDIRECT_URI"],
        "SHOP_ORIGIN": ENV["SHOP_ORIGIN"],
    }
    r = run("--export", str(EXPORT), env=public_only)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.startswith("ok ")
