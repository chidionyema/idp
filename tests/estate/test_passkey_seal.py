"""Falsifiers for the passkey seal — the device-independent replacement for a key file.

The property: a commit is sealed only by a WebAuthn assertion from the keyring's key, over a
payload naming that exact commit, committed inside that commit, with a nonce never used for a
different commit before. Every refusal below is a real attack or a real mistake.

The assertion is a real WebAuthn one: authenticatorData (rpIdHash || flags || counter), a
clientDataJSON whose challenge is SHA-256 of the payload, and a P-256 signature over
authenticatorData || SHA-256(clientDataJSON) — the shape a passkey produces, never a raw
signature over the payload.
"""

from __future__ import annotations

import base64
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
SEAL = ROOT / "bin" / "idp-passkey-seal.mjs"
VERSION = "idp-founder-seal-v1"
RP_ID = "passkey.example"


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _openssl(*a, stdin: bytes | None = None) -> bytes:
    return subprocess.run(
        ["openssl", *a], input=stdin, capture_output=True, check=True
    ).stdout


def _keypair(tmp: Path) -> tuple[Path, str]:
    pem = tmp / ("founder-%s.pem" % uuid4().hex[:8])
    _openssl("ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", str(pem))
    spki = _openssl("ec", "-in", str(pem), "-pubout", "-outform", "DER")
    return pem, _b64url(spki)


def _git(repo: Path, *a: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *a], capture_output=True, text=True, check=True
    ).stdout.strip()


def _commit(repo: Path, message: str) -> str:
    (repo / "file.txt").write_text(message)
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", message)
    return _git(repo, "rev-parse", "HEAD")


def _assertion(
    pem: Path, cred_id: str, payload: bytes, *, signed_payload: bytes | None = None
) -> dict:
    auth = hashlib.sha256(RP_ID.encode()).digest() + bytes([0x05]) + b"\x00\x00\x00\x01"
    challenge = hashlib.sha256(
        payload if signed_payload is None else signed_payload
    ).digest()
    client = {
        "type": "webauthn.get",
        "challenge": _b64url(challenge),
        "origin": "https://" + RP_ID,
    }
    client_bytes = json.dumps(client, separators=(",", ":")).encode()
    sign_bytes = auth + hashlib.sha256(client_bytes).digest()
    sig = _openssl("dgst", "-sha256", "-sign", str(pem), stdin=sign_bytes)
    return {
        "credentialId": cred_id,
        "authenticatorData": _b64url(auth),
        "clientDataJSON": _b64url(client_bytes),
        "signature": _b64url(sig),
    }


def _setup(
    tmp: Path,
    *,
    signer: Path | None = None,
    target: str = "",
    nonce: str = "nonce-abcdefghijkl",
    paths=("bin/x", "tests/x"),
    assertion_for: bytes | None = None,
):
    repo = tmp / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _commit(repo, "base")
    pem, spki = _keypair(tmp)
    cred_id = _b64url(b"credential-id-" + uuid4().bytes[:8])
    (repo / "docs" / "keys").mkdir(parents=True)
    (repo / "docs" / "keys" / "founder-passkey.json").write_text(
        json.dumps(
            {
                "credentialId": cred_id,
                "publicKeySpki": spki,
                "rpId": RP_ID,
                "origin": "https://" + RP_ID,
                "enrollmentCommit": _git(repo, "rev-parse", "HEAD"),
            }
        )
    )
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "enrol")
    parent = _git(repo, "rev-parse", "HEAD")

    at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = "\n".join([VERSION, parent, nonce, at, *paths]).encode()
    challenge = hashlib.sha256(payload).hexdigest()
    assertion = _assertion(
        signer or pem, cred_id, payload, signed_payload=assertion_for
    )
    approvals = repo / "docs" / "keys" / "approvals"
    approvals.mkdir(parents=True)
    (approvals / (challenge + ".json")).write_text(json.dumps(assertion))
    _git(repo, "add", "-A")
    _git(
        repo,
        "-c",
        "user.email=a@b",
        "-c",
        "user.name=a",
        "commit",
        "-qm",
        "\n".join(
            [
                "sealed change",
                "",
                f"X-Idp-Seal-Nonce: {nonce}",
                f"X-Idp-Seal-At: {at}",
                f"X-Idp-Seal-Target: {target or parent}",
                f"X-Idp-Seal-Paths: {','.join(paths)}",
            ]
        ),
    )
    return repo, _git(repo, "rev-parse", "HEAD"), pem


def _seal(
    repo: Path, sha: str, ledger: Path, files: str = "bin/x,tests/x"
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["node", str(SEAL), "--repo", str(repo), "--commit", sha, "--files", files],
        capture_output=True,
        text=True,
        env={**os.environ, "IDP_SEAL_LEDGER": str(ledger)},
    )


def test_a_passkey_assertion_over_this_commit_seals_it_once(tmp_path: Path) -> None:
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

    # A sibling of the sealed commit shares its parent, so the signed payload is byte-identical
    # and so is the committed assertion. Only the recorded commit tells the two apart.
    msg = _git(repo, "log", "-1", "--format=%B", sha)
    parent = _git(repo, "rev-parse", sha + "^")
    _git(repo, "checkout", "-q", parent)
    _git(repo, "checkout", "-q", sha, "--", "docs")
    (repo / "sibling.txt").write_text("a second child of the same parent")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", msg)
    sibling = _git(repo, "rev-parse", "HEAD")
    assert sibling != sha

    r = _seal(repo, sibling, ledger)
    assert r.returncode == 1, r.stdout
    assert "nonce already consumed" in r.stderr


def test_an_assertion_from_another_key_is_refused(tmp_path: Path) -> None:
    other, _ = _keypair(tmp_path)
    repo, sha, _ = _setup(tmp_path, signer=other)
    r = _seal(repo, sha, tmp_path / "l.jsonl")
    assert r.returncode == 1
    assert "signature invalid" in r.stderr


def test_an_assertion_for_another_payload_is_refused(tmp_path: Path) -> None:
    """The challenge must bind the exact bytes; a tap for something else signs something else."""
    repo, sha, _ = _setup(tmp_path, assertion_for=b"a different change entirely")
    r = _seal(repo, sha, tmp_path / "l.jsonl")
    assert r.returncode == 1
    assert "challenge not bound" in r.stderr


def test_a_seal_aimed_at_another_commit_is_refused(tmp_path: Path) -> None:
    repo, sha, _ = _setup(tmp_path, target="f" * 40)
    r = _seal(repo, sha, tmp_path / "l.jsonl")
    assert r.returncode == 1
    assert "seal targets" in r.stderr


def test_the_seal_cannot_be_widened_past_the_paths_it_signed(tmp_path: Path) -> None:
    """A tap for `bin/x,tests/x` must not lift the ceiling for a workflow rewrite."""
    repo, sha, _ = _setup(tmp_path)
    r = _seal(
        repo, sha, tmp_path / "l.jsonl", files="bin/x,.github/workflows/deploy.yml"
    )
    assert r.returncode == 1, r.stdout
    assert "does not cover .github/workflows/deploy.yml" in r.stderr


def test_an_assertion_that_is_not_in_the_commit_seals_nothing(tmp_path: Path) -> None:
    repo, sha, _ = _setup(tmp_path)
    # The same trailers on a fresh child of the same parent, with the assertion left out of the
    # commit: a seal must be part of what was committed, never a file lying around the worktree.
    msg = _git(repo, "log", "-1", "--format=%B", sha)
    parent = _git(repo, "rev-parse", sha + "^")
    _git(repo, "checkout", "-q", parent)
    (repo / "file.txt").write_text("the sealed change, minus its assertion")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", msg)
    r = _seal(repo, _git(repo, "rev-parse", "HEAD"), tmp_path / "l.jsonl")
    assert r.returncode == 1
    assert "no assertion committed" in r.stderr


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
    assert "no seal trailers" in r.stderr


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


def test_the_gate_admits_a_guarded_path_sealed_by_the_passkey(
    tmp_path: Path, monkeypatch
) -> None:
    repo, sha, _ = _setup(tmp_path)
    monkeypatch.setenv("IDP_SEAL_LEDGER", str(tmp_path / "nonces.jsonl"))
    gate = _gate()
    assert gate.seal_verified(str(repo), sha, ["bin/x", "tests/x"]) is True


def test_the_gate_refuses_a_guarded_path_when_neither_seal_verifies(
    tmp_path: Path, monkeypatch
) -> None:
    repo, _, _ = _setup(tmp_path)
    monkeypatch.setenv("IDP_SEAL_LEDGER", str(tmp_path / "nonces.jsonl"))
    (repo / "docs" / "keys" / "founder-passkey.json").unlink()
    unsealed = _commit(repo, "unsealed change")
    gate = _gate()
    sealed = gate.seal_verified(str(repo), unsealed, [".github/workflows/x.yml"])
    assert sealed is False, "no keyring and no signed trailer must never read as a seal"
    ok, report = gate.verify_proof_2_boundary_and_gate(
        "abc123", [".github/workflows/x.yml"], sealed
    )
    assert not ok
    assert "without Founder seal" in report["error"]
