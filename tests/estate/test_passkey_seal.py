"""Falsifiers for the passkey seal — the device-independent replacement for a key file.

The property: a commit is sealed only by a signature from the keyring's key, over a payload
naming that exact commit, with a nonce never consumed before. Every refusal below is a real
attack or a real mistake, not a formatting check.
"""

from __future__ import annotations

import base64
import importlib.machinery
import importlib.util
import json
from datetime import datetime, timezone
from uuid import uuid4
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SEAL = ROOT / "bin" / "idp-passkey-seal.mjs"


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _openssl(*a, stdin: bytes | None = None) -> bytes:
    return subprocess.run(["openssl", *a], input=stdin, capture_output=True, check=True).stdout


def _keypair(tmp: Path) -> tuple[Path, str]:
    pem = tmp / ("founder-%s.pem" % uuid4().hex[:8])
    _openssl("ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", str(pem))
    spki = _openssl("ec", "-in", str(pem), "-pubout", "-outform", "DER")
    return pem, _b64url(spki)


def _git(repo: Path, *a: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=True).stdout.strip()


def _commit(repo: Path, message: str) -> str:
    (repo / "file.txt").write_text(message)
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", message)
    return _git(repo, "rev-parse", "HEAD")


def _sign(pem: Path, payload: bytes) -> str:
    return _b64url(_openssl("dgst", "-sha256", "-sign", str(pem), stdin=payload))


def _setup(tmp: Path, signer: Path | None = None, target: str = "", nonce: str = "nonce-abcdefghijkl"):
    repo = tmp / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    base = _commit(repo, "base")
    pem, spki = _keypair(tmp)
    (repo / "docs" / "keys").mkdir(parents=True)
    (repo / "docs" / "keys" / "founder-passkey.json").write_text(json.dumps({
        "credentialId": "A" * 32, "publicKeySpki": spki,
        "rpId": "passkey.example", "origin": "https://passkey.example",
        "enrollmentCommit": base,
    }))
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "enrol")
    parent = _git(repo, "rev-parse", "HEAD")
    at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = "\n".join(["idp-founder-seal-v1", parent, nonce, at, "bin/x", "tests/x"]).encode()
    sig = _sign(signer or pem, payload)
    sha = _commit(repo, "\n".join([
        "sealed change", "",
        f"X-Idp-Seal: {sig}", f"X-Idp-Seal-Nonce: {nonce}",
        f"X-Idp-Seal-At: {at}", f"X-Idp-Seal-Target: {target or parent}",
        "X-Idp-Seal-Paths: bin/x,tests/x",
    ]))
    return repo, sha, pem


def _seal(repo: Path, sha: str, ledger: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["node", str(SEAL), "--repo", str(repo), "--commit", sha],
        capture_output=True, text=True,
        env={**os.environ, "IDP_SEAL_LEDGER": str(ledger)},
    )


def test_a_signed_seal_over_this_commit_is_accepted_once(tmp_path: Path) -> None:
    repo, sha, _ = _setup(tmp_path)
    ledger = tmp_path / "nonces.jsonl"
    r = _seal(repo, sha, ledger)
    assert r.returncode == 0, r.stderr
    assert "ok passkey-seal" in r.stdout
    assert json.loads(ledger.read_text().strip())["sha"] == sha


def test_a_seal_reads_the_same_way_at_every_gate(tmp_path: Path) -> None:
    """pre-commit, pre-push and CI ask the same question; the answer must not change."""
    repo, sha, _ = _setup(tmp_path)
    ledger = tmp_path / "nonces.jsonl"
    assert _seal(repo, sha, ledger).returncode == 0
    again = _seal(repo, sha, ledger)
    assert again.returncode == 0, again.stderr
    assert "already sealed" in again.stdout
    assert len(ledger.read_text().strip().splitlines()) == 1, "the ledger must not grow"


def test_the_same_seal_cannot_be_carried_onto_another_commit(tmp_path: Path) -> None:
    repo, sha, _ = _setup(tmp_path)
    ledger = tmp_path / "nonces.jsonl"
    assert _seal(repo, sha, ledger).returncode == 0

    # A sibling of the sealed commit shares its parent, so the signed payload is byte-identical.
    # Only the recorded commit tells the two apart -- which is exactly why it is recorded.
    msg = _git(repo, "log", "-1", "--format=%B", sha)
    parent = _git(repo, "rev-parse", sha + "^")
    _git(repo, "checkout", "-q", parent)
    (repo / "sibling.txt").write_text("sibling")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", msg)
    sibling = _git(repo, "rev-parse", "HEAD")
    assert sibling != sha

    r = _seal(repo, sibling, ledger)
    assert r.returncode == 1, r.stdout
    assert "nonce already consumed" in r.stderr


def test_a_signature_from_another_key_is_refused(tmp_path: Path) -> None:
    other, _ = _keypair(tmp_path)
    repo, sha, _ = _setup(tmp_path, signer=other)
    r = _seal(repo, sha, tmp_path / "l.jsonl")
    assert r.returncode == 1
    assert "does not verify" in r.stderr


def test_a_seal_aimed_at_another_commit_is_refused(tmp_path: Path) -> None:
    repo, sha, _ = _setup(tmp_path, target="f" * 40)
    r = _seal(repo, sha, tmp_path / "l.jsonl")
    assert r.returncode == 1
    assert "seal targets" in r.stderr


def test_without_a_keyring_nothing_is_sealed(tmp_path: Path) -> None:
    repo, sha, _ = _setup(tmp_path)
    (repo / "docs" / "keys" / "founder-passkey.json").unlink()
    r = _seal(repo, sha, tmp_path / "l.jsonl")
    assert r.returncode == 2
    assert "no keyring" in r.stderr


def test_a_commit_with_no_trailers_is_refused(tmp_path: Path) -> None:
    repo, _, _ = _setup(tmp_path)
    sha = _commit(repo, "no trailers here")
    r = _seal(repo, sha, tmp_path / "l.jsonl")
    assert r.returncode == 1


# --- gate integration: the seal the gate actually calls ------------------------------
#
# bin/idp-passkey-seal.mjs is worthless if bin/verify_three_proofs.py never asks it, so the
# guarded-path exemption is exercised through the gate's own entry point.

GATE = ROOT / "bin" / "verify_three_proofs.py"


def _gate():
    spec = importlib.util.spec_from_loader(
        "three_proofs", importlib.machinery.SourceFileLoader("three_proofs", str(GATE))
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_gate_admits_a_guarded_path_sealed_by_the_passkey(tmp_path: Path, monkeypatch) -> None:
    repo, sha, _ = _setup(tmp_path)
    monkeypatch.setenv("IDP_SEAL_LEDGER", str(tmp_path / "nonces.jsonl"))
    gate = _gate()
    assert gate.seal_verified(str(repo), sha) is True


def test_the_gate_refuses_a_guarded_path_when_neither_seal_verifies(tmp_path: Path, monkeypatch) -> None:
    repo, _, _ = _setup(tmp_path)
    monkeypatch.setenv("IDP_SEAL_LEDGER", str(tmp_path / "nonces.jsonl"))
    (repo / "docs" / "keys" / "founder-passkey.json").unlink()
    unsealed = _commit(repo, "unsealed change")
    gate = _gate()
    sealed = gate.seal_verified(str(repo), unsealed)
    assert sealed is False, "no keyring and no signed trailer must never read as a seal"
    ok, report = gate.verify_proof_2_boundary_and_gate(
        "abc123", [".github/workflows/x.yml"], sealed
    )
    assert not ok
    assert "without Founder seal" in report["error"]


def test_the_seal_cannot_be_widened_past_the_paths_it_signed(tmp_path: Path) -> None:
    """A tap for `bin/x,tests/x` must not lift the ceiling for a workflow rewrite."""
    repo, sha, _ = _setup(tmp_path)
    ledger = tmp_path / "nonces.jsonl"
    env = {**os.environ, "IDP_SEAL_LEDGER": str(ledger)}
    inside = subprocess.run(
        ["node", str(SEAL), "--repo", str(repo), "--commit", sha,
         "--files", "bin/x,tests/x"],
        capture_output=True, text=True, env=env,
    )
    assert inside.returncode == 0, inside.stderr
    outside = subprocess.run(
        ["node", str(SEAL), "--repo", str(repo), "--commit", sha,
         "--files", "bin/x,.github/workflows/deploy.yml"],
        capture_output=True, text=True, env=env,
    )
    assert outside.returncode == 1, outside.stdout
    assert "does not cover .github/workflows/deploy.yml" in outside.stderr
