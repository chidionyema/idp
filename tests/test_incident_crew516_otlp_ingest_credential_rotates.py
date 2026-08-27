"""crew#516 CP5 slice 3 (idp#436 review): the edge credential for the collector's ingest door.

platform/oci/otlp-ingest.tf writes `science:<bcrypt>` to the vault. bcrypt() salts anew on every
plan, so the entry needs ignore_changes on its content; with only that, tainting the password
would never reach the vault and every tick would 401 against the old line. Both lifecycle rules
must be present, and the users line and the plain password must derive from the same password.
Refused shapes: ignore_changes alone, replace_triggered_by alone, two different passwords.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

TF = Path(__file__).resolve().parents[1] / "platform" / "oci" / "otlp-ingest.tf"
USERS = re.compile(r'resource "oci_vault_secret" "otlp_ingest_users" \{(?P<body>.*?)\n\}', re.S)


def rotation_ok(text: str) -> tuple[bool, str]:
    m = USERS.search(text)
    if not m:
        return False, "no oci_vault_secret.otlp_ingest_users"
    body = "\n".join(line.split("#", 1)[0] for line in m.group("body").splitlines())
    if "ignore_changes" not in body or "secret_content" not in body.split("ignore_changes", 1)[1].split("]", 1)[0]:
        return False, "the users entry does not ignore its own bcrypt re-salt; every apply rewrites it"
    if "replace_triggered_by" not in body or "random_password.otlp_ingest" not in body.split("replace_triggered_by", 1)[1].split("]", 1)[0]:
        return False, "the users entry is not replaced when the password is; a rotation never reaches the vault"
    if "bcrypt(random_password.otlp_ingest.result)" not in body:
        return False, "the users line is not the bcrypt of the same password the sender reads"
    return True, "the users line re-salt is ignored, a new password replaces the entry"


def test_the_committed_file_rotates() -> None:
    ok, why = rotation_ok(TF.read_text())
    assert ok, why
    assert "otlp-ingest-password" in TF.read_text() and "base64encode(random_password.otlp_ingest.result)" in TF.read_text()


@pytest.mark.parametrize(
    "broken",
    [
        'resource "oci_vault_secret" "otlp_ingest_users" {\n  secret_content {\n    content = base64encode("science:${bcrypt(random_password.otlp_ingest.result)}")\n  }\n  lifecycle {\n    ignore_changes = [secret_content]\n  }\n}',
        'resource "oci_vault_secret" "otlp_ingest_users" {\n  secret_content {\n    content = base64encode("science:${bcrypt(random_password.otlp_ingest.result)}")\n  }\n  lifecycle {\n    replace_triggered_by = [random_password.otlp_ingest]\n  }\n}',
        'resource "oci_vault_secret" "otlp_ingest_users" {\n  secret_content {\n    content = base64encode("science:${bcrypt(random_password.other.result)}")\n  }\n  lifecycle {\n    ignore_changes = [secret_content]\n    replace_triggered_by = [random_password.otlp_ingest]\n  }\n}',
    ],
    ids=["ignore-only", "replace-only", "other-password"],
)
def test_the_refused_shapes(broken: str) -> None:
    assert not rotation_ok(broken)[0]
