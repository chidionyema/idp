import hashlib
import importlib.util
import io
import json
import unittest
import zipfile
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "web_agent_bridge",
    Path(__file__).resolve().parents[1] / "bin" / "web_agent_bridge.py",
)
BRIDGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIDGE)


def fixture(path="platform/example.txt", content=b"example\n", extra=None):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr(path, content)
        archive.writestr(
            "DROP_MANIFEST.json",
            json.dumps(
                {
                    "files": [
                        {"path": path, "sha256": hashlib.sha256(content).hexdigest()}
                    ]
                }
            ),
        )
        if extra:
            archive.writestr(extra, b"unexpected")
    data = out.getvalue()
    release = {
        "repo": "chidionyema/idp",
        "public_release": True,
        "base_sha": "a" * 40,
        "archive_sha256": hashlib.sha256(data).hexdigest(),
        "paths": [path],
        "claim_issue": 7760,
        "agent": "web-fixture",
        "drive_file_id": "fixture",
        "source": "drive",
    }
    return data, release


class BridgeTests(unittest.TestCase):
    def check(self, data, release):
        return BRIDGE.validate_zip(data, BRIDGE.approval(release))

    def test_approved_exact_bytes(self):
        self.assertEqual(
            self.check(*fixture()), {"platform/example.txt": (b"example\n", False)}
        )

    def test_refuse_unapproved_archive(self):
        data, release = fixture()
        release["archive_sha256"] = "0" * 64
        with self.assertRaises(BRIDGE.BridgeError):
            self.check(data, release)

    def test_refuse_manifest_self_authorization(self):
        data, release = fixture()
        release["public_release"] = False
        with self.assertRaises(BRIDGE.BridgeError):
            self.check(data, release)

    def test_refuse_unsafe_paths(self):
        for path in (
            "src/../bad",
            ".github/workflows/test.yml",
            "bin/idp-auth",
            "platform/.env",
            "platform/private/key",
        ):
            with self.subTest(path=path), self.assertRaises(BRIDGE.BridgeError):
                self.check(*fixture(path))

    def test_refuse_unmanifested_entry(self):
        with self.assertRaises(BRIDGE.BridgeError):
            self.check(*fixture(extra="platform/extra.txt"))

    def test_refuse_secret_and_binary(self):
        for content in (b"sk-EXAMPLESECRET1234567890", b"\x00"):
            with self.subTest(content=content), self.assertRaises(BRIDGE.BridgeError):
                self.check(*fixture(content=content))

    def test_refuse_mock(self):
        with self.assertRaises(BRIDGE.BridgeError):
            self.check(*fixture("src/generalPurposePersonaData.ts"))


if __name__ == "__main__":
    unittest.main()
