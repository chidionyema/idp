"""OCI Object Storage + Vault KMS envelope-encrypted mission checkpoints.

An infrastructure adapter only, not an execution/authorization door. OCI
instance/OKE-workload principals must be provided by trusted runtime identity;
no API-key fallback. Encryption with random AES-256-GCM DEK, wrapped by the
tenant's pinned Vault KMS master key. AES-GCM AAD binds mission+object+schema.
The OCI object is write-once and integrity-checked on read.

The manifest contains source SHA and resume cursor, never elevated privileges.
Decryption, correct identity and object integrity do NOT prove completion.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
import uuid
from dataclasses import dataclass
from urllib.parse import urlsplit

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SCHEMA = "genesis.mission.checkpoint.v1"
ENVELOPE = "genesis.oci.envelope.v1"
MAX_PLAINTEXT_BYTES = 1_048_576
MAX_OBJECT_BYTES = 3_000_000
MISSION_ID = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")
SOURCE_SHA = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
REGION = re.compile(r"^[a-z0-9-]{5,40}$")
BUCKET = re.compile(r"^[a-zA-Z0-9_.-]{3,255}$")
PREFIX = re.compile(r"^[a-zA-Z0-9/_-]{1,160}$")


class CheckpointRefused(RuntimeError):
    """Refused operation; never transmute this into a success receipt."""


@dataclass(frozen=True)
class CheckpointReference:
    uri: str
    sha256: str
    etag: str
    source_sha: str


def _json(data: dict) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def _decode(value: str, name: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except (TypeError, ValueError) as exc:
        raise CheckpointRefused(f"INVALID_BASE64_{name}") from exc


def _validate_mission(mission_id: str):
    if not isinstance(mission_id, str) or not MISSION_ID.fullmatch(mission_id):
        raise CheckpointRefused("INVALID_MISSION_ID")


def _validate_manifest(mission_id: str, document: dict) -> dict:
    if not isinstance(document, dict):
        raise CheckpointRefused("INVALID_CHECKPOINT_MANIFEST")
    if document.get("schema") != SCHEMA or document.get("mission_id") != mission_id:
        raise CheckpointRefused("CROSS_MISSION_OR_SCHEMA_MISMATCH")
    source = document.get("source_sha")
    cursor = document.get("resume_cursor")
    if not isinstance(source, str) or not SOURCE_SHA.fullmatch(source):
        raise CheckpointRefused("UNPINNED_SOURCE_SHA")
    if not isinstance(cursor, str) or not 0 < len(cursor) <= 1024:
        raise CheckpointRefused("INVALID_RESUME_CURSOR")
    if document.get("authorized") or document.get("operating"):
        raise CheckpointRefused("CHECKPOINT_CANNOT_GRANT_AUTHORITY")
    return document


class OCIEncryptedCheckpointStore:
    """Bounded OCI client; production factory uses only workload/instance principal.

    Injecting clients is for hermetic testing; this is not live tenancy proof.
    """

    def __init__(self, *, storage, kms, oci_models, namespace: str,
                 bucket: str, prefix: str, kms_key_id: str):
        if not isinstance(prefix, str) or not isinstance(kms_key_id, str):
            raise CheckpointRefused("INVALID_PINNED_CHECKPOINT_CONFIG")
        prefix = prefix.strip("/")
        if (not isinstance(namespace, str) or not BUCKET.fullmatch(namespace)
                or not isinstance(bucket, str) or not BUCKET.fullmatch(bucket)
                or not PREFIX.fullmatch(prefix)
                or any(x in ("", ".", "..") for x in prefix.split("/"))
                or not kms_key_id.startswith("ocid1.key.")):
            raise CheckpointRefused("INVALID_PINNED_CHECKPOINT_CONFIG")
        self.storage = storage
        self.kms = kms
        self.oci_models = oci_models
        self.namespace = namespace
        self.bucket = bucket
        self.prefix = prefix
        self.kms_key_id = kms_key_id

    @classmethod
    def from_runtime(cls, env=None):
        """Resolve real OCI identity, fail closed on missing SDK or untrusted mode."""
        cfg = os.environ if env is None else env
        mode = cfg.get("GENESIS_OCI_PRINCIPAL")
        region = cfg.get("GENESIS_OCI_REGION", "")
        url = cfg.get("GENESIS_OCI_KMS_CRYPTO_ENDPOINT", "")
        if mode not in ("instance", "oke-workload") or not REGION.fullmatch(region):
            raise CheckpointRefused("UNTRUSTED_OCI_IDENTITY_CONFIGURATION")
        parsed = urlsplit(url)
        host = parsed.hostname or ""
        if (parsed.scheme != "https" or parsed.username or parsed.password
                or parsed.port not in (None, 443) or parsed.path not in ("", "/")
                or parsed.query or parsed.fragment
                or not host.endswith(f"-crypto.kms.{region}.oci.oraclecloud.com")
                or host == f"-crypto.kms.{region}.oci.oraclecloud.com"):
            raise CheckpointRefused("UNPINNED_KMS_ENDPOINT")
        try:
            import oci
            if mode == "instance":
                signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
            else:
                signer = oci.auth.signers.get_oke_workload_identity_resource_principal_signer()
            storage = oci.object_storage.ObjectStorageClient(
                {"region": region}, signer=signer
            )
            kms = oci.key_management.KmsCryptoClient(
                {"region": region}, service_endpoint=url, signer=signer
            )
        except Exception as exc:
            raise CheckpointRefused("OCI_AUTH_OR_SDK_UNAVAILABLE") from exc
        return cls(storage=storage, kms=kms, oci_models=oci.key_management.models,
                   namespace=cfg.get("GENESIS_OCI_NAMESPACE", ""),
                   bucket=cfg.get("GENESIS_OCI_CHECKPOINT_BUCKET", ""),
                   prefix=cfg.get("GENESIS_OCI_CHECKPOINT_PREFIX", ""),
                   kms_key_id=cfg.get("GENESIS_OCI_KMS_KEY_ID", ""))

    def _aad(self, mission_id: str, name: str) -> bytes:
        return _json({"mission_id": mission_id, "object_name": name, "schema": SCHEMA})

    def _kms_context(self, mission_id: str, name: str) -> dict:
        return {"mission_id": mission_id, "object_name": name, "schema": SCHEMA}

    def _name(self, uri: str, mission_id: str | None = None) -> str:
        if not isinstance(uri, str):
            raise CheckpointRefused("INVALID_CHECKPOINT_URI")
        try:
            parsed = urlsplit(uri)
            port = parsed.port
        except ValueError as exc:
            raise CheckpointRefused("INVALID_CHECKPOINT_URI") from exc
        if (parsed.scheme != "oci" or parsed.netloc != self.bucket
                or parsed.query or parsed.fragment or parsed.username
                or parsed.password or port):
            raise CheckpointRefused("CHECKPOINT_BUCKET_SCOPE_VIOLATION")
        name = parsed.path.lstrip("/")
        expected = (f"{self.prefix}/{mission_id}/"
                    if mission_id is not None else f"{self.prefix}/")
        if (not name.startswith(expected) or ".." in name.split("/")
                or any(ord(c) < 33 or ord(c) > 126 for c in name)):
            raise CheckpointRefused("CHECKPOINT_PREFIX_SCOPE_VIOLATION")
        return name

    def write(self, mission_id: str, manifest: dict) -> CheckpointReference:
        """Create a fresh immutable checkpoint and independently read back bytes."""
        _validate_mission(mission_id)
        body = _json(_validate_manifest(mission_id, manifest))
        if len(body) > MAX_PLAINTEXT_BYTES:
            raise CheckpointRefused("CHECKPOINT_TOO_LARGE")
        name = f"{self.prefix}/{mission_id}/{uuid.uuid4().hex}.checkpoint"
        dek, nonce = secrets.token_bytes(32), secrets.token_bytes(12)
        cipher = AESGCM(dek).encrypt(nonce, body, self._aad(mission_id, name))
        wrapped = self.kms.encrypt(
            encrypt_data_details=self.oci_models.EncryptDataDetails(
                key_id=self.kms_key_id,
                plaintext=base64.b64encode(dek).decode("ascii"),
                encryption_algorithm="AES_256_GCM",
                associated_data=self._kms_context(mission_id, name),
            )
        ).data
        if not wrapped.ciphertext:
            raise CheckpointRefused("KMS_KEY_WRAP_MISSING")
        envelope = _json({
            "schema": ENVELOPE,
            "mission_id": mission_id,
            "object_name": name,
            "kms_key_id": self.kms_key_id,
            "key_version_id": wrapped.key_version_id,
            "wrapped_key": wrapped.ciphertext,
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(cipher).decode("ascii"),
        })
        if len(envelope) > MAX_OBJECT_BYTES:
            raise CheckpointRefused("ENCRYPTED_CHECKPOINT_TOO_LARGE")
        digest = hashlib.sha256(envelope).hexdigest()
        uri = f"oci://{self.bucket}/{name}"
        response = self.storage.put_object(
            self.namespace, self.bucket, name, envelope,
            if_none_match="*", opc_sse_kms_key_id=self.kms_key_id,
            opc_client_request_id=uuid.uuid4().hex,
        )
        self._read_exact(uri, expected_digest=digest)
        return CheckpointReference(
            uri=uri, sha256=digest, etag=response.headers.get("etag", ""),
            source_sha=manifest["source_sha"],
        )

    def _read_exact(self, uri: str, expected_digest: str = "") -> bytes:
        name = self._name(uri)
        if expected_digest and not DIGEST.fullmatch(expected_digest):
            raise CheckpointRefused("INVALID_EXPECTED_DIGEST")
        try:
            head = self.storage.head_object(self.namespace, self.bucket, name)
        except Exception as exc:
            raise CheckpointRefused("REMOTE_CHECKPOINT_NOT_READABLE") from exc
        try:
            size = int(head.headers.get("content-length", -1))
        except (ValueError, TypeError) as exc:
            raise CheckpointRefused("UNKNOWN_OBJECT_SIZE") from exc
        if size < 1 or size > MAX_OBJECT_BYTES:
            raise CheckpointRefused("OBJECT_SIZE_NOT_SAFE")
        try:
            response = self.storage.get_object(
                self.namespace, self.bucket, name,
                if_match=head.headers.get("etag"),
            )
        except Exception as exc:
            raise CheckpointRefused("REMOTE_CHECKPOINT_NOT_READABLE") from exc
        data = response.data
        if hasattr(data, "raw") and hasattr(data.raw, "read"):
            payload = data.raw.read(MAX_OBJECT_BYTES + 1)
        else:
            payload = data.content
        if not isinstance(payload, bytes) or len(payload) != size:
            raise CheckpointRefused("OBJECT_TRUNCATED_OR_OVERSIZED")
        if expected_digest and hashlib.sha256(payload).hexdigest() != expected_digest:
            raise CheckpointRefused("CHECKPOINT_DIGEST_MISMATCH")
        return payload

    def read_ciphertext(self, uri: str) -> bytes:
        """Read only objects under the configured scope; verify digest at caller."""
        return self._read_exact(uri)

    def decrypt_and_validate(self, mission_id: str, uri: str,
                             ciphertext: bytes) -> dict:
        _validate_mission(mission_id)
        name = self._name(uri, mission_id)
        if not isinstance(ciphertext, bytes) or not 0 < len(ciphertext) <= MAX_OBJECT_BYTES:
            raise CheckpointRefused("INVALID_ENVELOPE_BYTES")
        try:
            env = json.loads(ciphertext)
        except (UnicodeError, ValueError) as exc:
            raise CheckpointRefused("INVALID_ENVELOPE_JSON") from exc
        if not isinstance(env, dict) or (
                env.get("schema") != ENVELOPE
                or env.get("mission_id") != mission_id
                or env.get("object_name") != name
                or env.get("kms_key_id") != self.kms_key_id):
            raise CheckpointRefused("UNTRUSTED_CHECKPOINT_METADATA")
        nonce = _decode(env.get("nonce"), "NONCE")
        blob = _decode(env.get("ciphertext"), "CIPHER")
        if len(nonce) != 12 or len(blob) < 16 or len(blob) > MAX_OBJECT_BYTES:
            raise CheckpointRefused("INVALID_GCM_PARAMETERS")
        data = self.kms.decrypt(
            decrypt_data_details=self.oci_models.DecryptDataDetails(
                key_id=self.kms_key_id,
                key_version_id=env.get("key_version_id"),
                ciphertext=env.get("wrapped_key"),
                encryption_algorithm="AES_256_GCM",
                associated_data=self._kms_context(mission_id, name),
            )
        ).data
        dek = _decode(data.plaintext, "DEK")
        if len(dek) != 32:
            raise CheckpointRefused("INVALID_DECRYPTED_DATA_KEY")
        try:
            decoded = AESGCM(dek).decrypt(
                nonce, blob, self._aad(mission_id, name)
            )
            manifest = json.loads(decoded)
        except Exception as exc:
            raise CheckpointRefused("CHECKPOINT_AUTHENTICATION_FAILED") from exc
        return _validate_manifest(mission_id, manifest)
