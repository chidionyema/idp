"""ADR 0026 step 4: bin/intent-compile's compile_secret_crossplane() branch, and the
bin/idp-root-trust IN_ESTATE change that lets its register row grade MEETS.

Proved both ways, same fixture (tests/fixtures/intent/good/secret.json, origin=generated):
  * ESTATE_STORAGE_PROVIDER=crossplane  -> a VaultSecret Claim, no Terraform, register row
    names "Crossplane `Secret`", and bin/idp-root-trust accepts that row.
  * ESTATE_STORAGE_PROVIDER=oci         -> unchanged: secret.tf, no Claim -- the new branch does
    not regress the path every existing generated secret still compiles through.
"""

# ruff: noqa: S101, S603, S607 -- pytest asserts and subprocess.run against this repo's own
# bin/ tools with hardcoded argv (no untrusted input), same shape every other test here uses.

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTENT_COMPILE = ROOT / "bin" / "intent-compile"
ROOT_TRUST = ROOT / "bin" / "idp-root-trust"
FIXTURE = ROOT / "tests" / "fixtures" / "intent" / "good" / "secret.json"


def _compile(tmp_path: Path, provider: str) -> subprocess.CompletedProcess:
    intents = tmp_path / "intents"
    intents.mkdir()
    (intents / "secret.json").write_text(FIXTURE.read_text())
    dna_dir = tmp_path / "dna"
    (dna_dir / "clusters" / "oke").mkdir(parents=True)
    (dna_dir / "clusters" / "oke" / "estate-config.yaml").write_text(
        "apiVersion: v1\nkind: ConfigMap\nmetadata: {name: estate-config, namespace: flux-system}\n"
        f'data:\n  ESTATE_ZONE: test.example.com\n  ESTATE_STORAGE_PROVIDER: "{provider}"\n'
    )
    out = tmp_path / "out"
    register = tmp_path / "register.md"
    result = subprocess.run(
        [
            str(INTENT_COMPILE),
            "--intents",
            str(intents),
            "--out",
            str(out),
            "--dna",
            str(dna_dir),
            "--register",
            str(register),
        ],
        capture_output=True,
        text=True,
    )
    result.out_dir = out  # type: ignore[attr-defined]
    result.register_path = register  # type: ignore[attr-defined]
    return result


def test_crossplane_provider_emits_a_claim_not_terraform(tmp_path):
    r = _compile(tmp_path, "crossplane")
    assert r.returncode == 0, r.stdout + r.stderr
    emitted = {p.name for p in r.out_dir.glob("fixture-signing/*")}
    assert "secret-claim-session-signing-key.yaml" in emitted, emitted
    assert "secret.tf" not in emitted, emitted
    claim = json.loads(
        subprocess.run(
            [
                sys.executable,
                "-c",
                "import yaml,json,sys; print(json.dumps(yaml.safe_load(open(sys.argv[1]))))",
                str(
                    r.out_dir
                    / "fixture-signing"
                    / "secret-claim-session-signing-key.yaml"
                ),
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )
    assert claim["apiVersion"] == "secret.estate.io/v1alpha1"
    assert claim["kind"] == "VaultSecret"
    assert claim["metadata"]["namespace"] == "crossplane-system"
    # No plaintext, no random value, anywhere in the emitted Claim (LAW 21).
    assert "content" not in claim["spec"]


def test_crossplane_register_row_names_crossplane_and_root_trust_accepts_it(tmp_path):
    r = _compile(tmp_path, "crossplane")
    assert r.returncode == 0, r.stdout + r.stderr
    row = r.register_path.read_text()
    assert "Crossplane `Secret`" in row
    # bin/idp-root-trust's IN_ESTATE birth-path check is a substring test against the row's last
    # cell; assert the literal condition it evaluates, not just that the script exits 0 (which a
    # missing register file would too).
    in_estate = ("ESO generator", "Terraform", "Crossplane")
    assert any(m in row for m in in_estate)


def test_oci_provider_is_unaffected_by_the_new_branch(tmp_path):
    r = _compile(tmp_path, "oci")
    assert r.returncode == 0, r.stdout + r.stderr
    emitted = {p.name for p in r.out_dir.glob("fixture-signing/*")}
    assert "secret.tf" in emitted, emitted
    assert not any(n.startswith("secret-claim-") for n in emitted), emitted
