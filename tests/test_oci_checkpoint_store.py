"""Hermetic tests exercise real AES-GCM and read-after-write, not cloud tenancy."""
import base64
import hashlib
import importlib.util
import json
import os
import pathlib
import unittest
from types import SimpleNamespace

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

source = pathlib.Path(__file__).resolve().parents[1] / "platform/queue/oci_checkpoint_store.py"
spec = importlib.util.spec_from_file_location("oci_checkpoint_store", source)
import sys
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


class Model:
    def __init__(self, **args):
        self.__dict__.update(args)


class FakeModels:
    EncryptDataDetails = Model
    DecryptDataDetails = Model


class FakeKMS:
    def __init__(self):
        self.key = AESGCM.generate_key(bit_length=256)
        self.enc_count = self.dec_count = 0

    def encrypt(self, *, encrypt_data_details):
        self.enc_count += 1
        request = encrypt_data_details
        assert request.key_id == "ocid1.key.oc1.test"
        assert request.encryption_algorithm == "AES_256_GCM"
        nonce = os.urandom(12)
        context = json.dumps(request.associated_data, sort_keys=True).encode()
        ciphertext = AESGCM(self.key).encrypt(
            nonce, base64.b64decode(request.plaintext), context
        )
        return SimpleNamespace(data=SimpleNamespace(
            ciphertext=base64.b64encode(nonce + ciphertext).decode(),
            key_version_id="ocid1.keyversion.oc1.test",
        ))

    def decrypt(self, *, decrypt_data_details):
        self.dec_count += 1
        request = decrypt_data_details
        data = base64.b64decode(request.ciphertext)
        context = json.dumps(request.associated_data, sort_keys=True).encode()
        payload = AESGCM(self.key).decrypt(data[:12], data[12:], context)
        return SimpleNamespace(data=SimpleNamespace(
            plaintext=base64.b64encode(payload).decode(),
        ))


class FakeStorage:
    def __init__(self):
        self.objects = {}
        self.requests = []

    def put_object(self, namespace, bucket, name, body, **kwargs):
        assert kwargs["if_none_match"] == "*"
        assert kwargs["opc_sse_kms_key_id"] == "ocid1.key.oc1.test"
        assert (bucket, name) not in self.objects
        self.objects[bucket, name] = body
        self.requests.append((namespace, bucket, name, kwargs))
        return SimpleNamespace(headers={"etag": hashlib.sha256(body).hexdigest()})

    def head_object(self, namespace, bucket, name):
        body = self.objects[bucket, name]
        return SimpleNamespace(headers={
            "content-length": str(len(body)),
            "etag": hashlib.sha256(body).hexdigest(),
        })

    def get_object(self, namespace, bucket, name, **kwargs):
        body = self.objects[bucket, name]
        assert kwargs["if_match"] == hashlib.sha256(body).hexdigest()
        return SimpleNamespace(data=SimpleNamespace(content=body))


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.storage = FakeStorage()
        self.kms = FakeKMS()
        self.store = m.OCIEncryptedCheckpointStore(
            storage=self.storage, kms=self.kms, oci_models=FakeModels,
            namespace="estate_namespace", bucket="estate-checkpoints",
            prefix="idp_7790", kms_key_id="ocid1.key.oc1.test",
        )
        self.manifest = {
            "schema": m.SCHEMA,
            "mission_id": "mission-1",
            "source_sha": "a" * 40,
            "resume_cursor": "step-7",
            "info": "confidential-checkpoint",
        }

    def test_encrypt_write_then_decrypt_restore(self):
        ref = self.store.write("mission-1", self.manifest)
        self.assertEqual(ref.source_sha, "a" * 40)
        self.assertTrue(ref.uri.startswith("oci://estate-checkpoints/idp_7790/mission-1/"))
        content = self.store.read_ciphertext(ref.uri)
        self.assertEqual(hashlib.sha256(content).hexdigest(), ref.sha256)
        self.assertEqual(self.store.decrypt_and_validate("mission-1", ref.uri, content),
                         self.manifest)
        self.assertNotIn(b"confidential-checkpoint", content)
        self.assertEqual((self.kms.enc_count, self.kms.dec_count), (1, 1))

    def test_ciphertext_digest_detects_modified_object(self):
        ref = self.store.write("mission-1", self.manifest)
        key = next(iter(self.storage.objects))
        self.storage.objects[key] += b"tamper"
        with self.assertRaisesRegex(m.CheckpointRefused, "CHECKPOINT_DIGEST_MISMATCH"):
            self.store._read_exact(ref.uri, ref.sha256)

    def test_bucket_prefix_and_path_scope_refused(self):
        bad = ("oci://another/idp_7790/mission-1/blob",
               "oci://estate-checkpoints/other/mission-1/blob",
               "https://estate-checkpoints/idp_7790/mission-1/blob",
               "oci://estate-checkpoints/idp_7790/mission-1/../blob")
        for uri in bad:
            with self.subTest(uri=uri), self.assertRaises(m.CheckpointRefused):
                self.store.read_ciphertext(uri)

    def test_wrong_mission_refused_before_kms(self):
        ref = self.store.write("mission-1", self.manifest)
        with self.assertRaises(m.CheckpointRefused):
            self.store.decrypt_and_validate("mission-2", ref.uri,
                                            self.store.read_ciphertext(ref.uri))
        self.assertEqual(self.kms.dec_count, 0)

    def test_reject_key_substitution_before_kms(self):
        ref = self.store.write("mission-1", self.manifest)
        obj = json.loads(self.store.read_ciphertext(ref.uri))
        obj["kms_key_id"] = "ocid1.key.oc1.attacker"
        with self.assertRaisesRegex(m.CheckpointRefused, "UNTRUSTED_CHECKPOINT_METADATA"):
            self.store.decrypt_and_validate("mission-1", ref.uri, m._json(obj))
        self.assertEqual(self.kms.dec_count, 0)

    def test_aead_detects_modified_ciphertext(self):
        ref = self.store.write("mission-1", self.manifest)
        obj = json.loads(self.store.read_ciphertext(ref.uri))
        obj["ciphertext"] = base64.b64encode(b"0" * 40).decode()
        with self.assertRaisesRegex(m.CheckpointRefused, "CHECKPOINT_AUTHENTICATION_FAILED"):
            self.store.decrypt_and_validate("mission-1", ref.uri, m._json(obj))

    def test_invalid_manifest_is_refused_before_write(self):
        for change in ({"source_sha": "da1536c7"}, {"operating": True},
                       {"mission_id": "other"}, {"resume_cursor": ""}):
            with self.subTest(change=change), self.assertRaises(m.CheckpointRefused):
                self.store.write("mission-1", dict(self.manifest, **change))
        self.assertEqual(len(self.storage.objects), 0)

    def test_two_writes_have_distinct_write_once_names(self):
        first = self.store.write("mission-1", self.manifest)
        second = self.store.write("mission-1", self.manifest)
        self.assertNotEqual(first.uri, second.uri)
        self.assertEqual(len(self.storage.objects), 2)

    def test_kms_sse_header_is_mandatory(self):
        self.store.write("mission-1", self.manifest)
        self.assertEqual(self.storage.requests[0][3]["opc_sse_kms_key_id"],
                         "ocid1.key.oc1.test")

    def test_no_api_key_or_untrusted_vault_endpoint(self):
        with self.assertRaisesRegex(m.CheckpointRefused,
                                    "UNTRUSTED_OCI_IDENTITY_CONFIGURATION"):
            m.OCIEncryptedCheckpointStore.from_runtime({
                "GENESIS_OCI_PRINCIPAL": "api-key",
                "GENESIS_OCI_REGION": "uk-london-1",
            })
        with self.assertRaisesRegex(m.CheckpointRefused, "UNPINNED_KMS_ENDPOINT"):
            m.OCIEncryptedCheckpointStore.from_runtime({
                "GENESIS_OCI_PRINCIPAL": "instance",
                "GENESIS_OCI_REGION": "uk-london-1",
                "GENESIS_OCI_KMS_CRYPTO_ENDPOINT": "https://attacker.invalid",
            })

    def test_oversize_and_missing_object_are_refused(self):
        with self.assertRaises(m.CheckpointRefused):
            self.store.write("mission-1", dict(self.manifest,
                                               blob="x" * m.MAX_PLAINTEXT_BYTES))
        with self.assertRaises(m.CheckpointRefused):
            self.store.read_ciphertext("oci://estate-checkpoints/idp_7790/nope")

    def test_no_untrusted_prefix_or_key_config(self):
        with self.assertRaisesRegex(m.CheckpointRefused,
                                    "INVALID_PINNED_CHECKPOINT_CONFIG"):
            m.OCIEncryptedCheckpointStore(
                storage=self.storage, kms=self.kms, oci_models=FakeModels,
                namespace="namespace", bucket="bucket", prefix="../unsafe",
                kms_key_id="ocid1.key.oc1.test",
            )


if __name__ == "__main__":
    unittest.main()
