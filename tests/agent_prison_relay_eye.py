#!/usr/bin/env python3
"""Two-host GitHub Action eye-test: offline signed proposal, reconnect under revoked epoch.

The two jobs have isolated filesystems. Only an artifact crosses the boundary.
The effect is a harmless local file in the reconnect job, NOT estate production.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def cmd(*args):
    return subprocess.run(["openssl", *args], check=True, capture_output=True)


def bytes_of(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def offline():
    key, pub = Path("private.pem"), Path("public.pem")
    cmd("genpkey", "-algorithm", "Ed25519", "-out", str(key))
    cmd("pkey", "-in", str(key), "-pubout", "-out", str(pub))
    body = {
        "instruction_id": "founder-agent-prison-live-eye-20261110",
        "operation": "probe-write",
        "principal_key_fingerprint": hashlib.sha256(pub.read_bytes()).hexdigest(),
        "epoch": 1, "kind": "offline-proposal", "sequence": 1,
        "proposer": os.environ.get("GITHUB_JOB", "offline"),
    }
    raw = bytes_of(body)
    Path("payload.bin").write_bytes(raw)
    cmd("pkeyutl", "-sign", "-inkey", str(key), "-rawin", "-in", "payload.bin", "-out", "signature.bin")
    envelope = {
        "event": body,
        "payload_sha256": hashlib.sha256(raw).hexdigest(),
        "signature_b64": base64.b64encode(Path("signature.bin").read_bytes()).decode(),
        "public_key_pem": pub.read_text(),
        "source_job": os.environ.get("GITHUB_JOB", "offline"),
    }
    Path("offline-envelope.json").write_text(json.dumps(envelope, sort_keys=True, indent=2) + "\n")
    assert not Path("offline-envelope.json").read_text().find("PRIVATE KEY") >= 0
    print("OFFLINE_SIGNED_EVENT_PERSISTED", body["principal_key_fingerprint"][:16], body["epoch"])


def reconnect():
    begin = time.perf_counter()
    packet = json.loads(Path("offline-envelope.json").read_text())
    body = packet["event"]
    Path("reconnect-pub.pem").write_text(packet["public_key_pem"])
    sig = base64.b64decode(packet["signature_b64"])
    Path("reconnect-signature.bin").write_bytes(sig)
    original = bytes_of(body)
    Path("reconnect-message.bin").write_bytes(original)
    assert hashlib.sha256(original).hexdigest() == packet["payload_sha256"]
    assert body["principal_key_fingerprint"] == hashlib.sha256(
        Path("reconnect-pub.pem").read_bytes()).hexdigest()
    cmd("pkeyutl", "-verify", "-pubin", "-inkey", "reconnect-pub.pem", "-rawin",
        "-in", "reconnect-message.bin", "-sigfile", "reconnect-signature.bin")

    # Independent trusted action boundary has revocation epoch 2, after event was signed offline.
    current_epoch = 2
    effect_path = Path("protected-effect.txt")
    stale_refused = body["epoch"] != current_epoch
    if not stale_refused:
        effect_path.write_text("BAD_EFFECT")
    effect_absent = not effect_path.exists()
    # A signature on a changed epoch is not reusable for permission elevation.
    tampered = dict(body, epoch=2)
    Path("reconnect-message.bin").write_bytes(bytes_of(tampered))
    forgery_refused = subprocess.run(
        ["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", "reconnect-pub.pem",
         "-rawin", "-in", "reconnect-message.bin", "-sigfile", "reconnect-signature.bin"],
        capture_output=True).returncode != 0
    # New independently authorized effect (not promotion of old proposal).
    valid_new_epoch = 2
    effect_id = "current-epoch-probe"
    seen = set()

    def apply(effect_key, epoch):
        if epoch != current_epoch:
            return "DENIED"
        if effect_key in seen:
            return "DEDUPLICATED"
        seen.add(effect_key)
        with effect_path.open("a") as handle:
            handle.write(effect_key + "\n")
        return "WRITTEN"

    new_effect = apply(effect_id, valid_new_epoch)
    repeated = apply(effect_id, valid_new_epoch)
    count = len(effect_path.read_text().splitlines()) if effect_path.exists() else 0
    result = {
        "kind": "TWO_ISOLATED_GITHUB_RUNNERS_NOT_PRODUCTION",
        "signed_offline_envelope_verified_after_artifact_transfer": True,
        "stale_epoch_refused": stale_refused,
        "stale_protected_effect_absent": effect_absent,
        "tampered_epoch_signature_rejected": forgery_refused,
        "fresh_authorized_effect": new_effect,
        "duplicate_effect": repeated,
        "external_effect_count": count,
        "elapsed_ms": round((time.perf_counter() - begin) * 1000, 2),
        "source": packet["source_job"],
        "destination": os.environ.get("GITHUB_JOB", "reconnect"),
        "estate_operational_verified": False,
    }
    Path("reconnect-receipt.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    assert all([stale_refused, effect_absent, forgery_refused, new_effect == "WRITTEN",
                repeated == "DEDUPLICATED", count == 1])


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"offline", "reconnect"}:
        raise SystemExit("usage: agent_prison_relay_eye.py offline|reconnect")
    {"offline": offline, "reconnect": reconnect}[sys.argv[1]]()
