"""unittest for sovereign/trust/ (cp20). Run:
    ESTATE_HOME=<scratch> PYTHONPATH=<idp> \
      sovereign/.venv/bin/python -m unittest sovereign.trust.test_trust -v
"""
from __future__ import annotations

import unittest

from sovereign.trust.anchor import BACKENDS, HardwareTrustAnchor
from sovereign.trust.canonical import canonical_relpath


class CanonicalRelpathTest(unittest.TestCase):
    def test_windows_and_posix_separators_hash_identically(self) -> None:
        # cp20 "Windows paths do not change hashes": the same logical file
        # walked on Windows ("src\kernel\main.py") and on macOS
        # ("src/kernel/main.py") must canonicalize to the same string, so
        # a sha256 over it is identical too.
        windows_form = canonical_relpath("/repo", "/repo/src\\kernel\\main.py")
        posix_form = canonical_relpath("/repo", "/repo/src/kernel/main.py")
        self.assertEqual(windows_form, posix_form)
        self.assertEqual(windows_form, "src/kernel/main.py")

    def test_mixed_separators_in_one_path(self) -> None:
        self.assertEqual(canonical_relpath("/repo", "/repo/a\\b/c\\d.py"), "a/b/c/d.py")

    def test_relative_input_not_under_root_is_returned_canonicalized(self) -> None:
        self.assertEqual(canonical_relpath("/repo", "src\\a.py"), "src/a.py")

    def test_property_windows_relpath_equals_posix_relpath(self) -> None:
        # One property, many cases (How-to-test rung 2): for any sequence
        # of path segments, joining with "\\" and canonicalizing must
        # equal joining with "/" and canonicalizing, for every prefix
        # length used as the root.
        segments = ["repo", "pkg", "sub dir", "file-1.py"]
        posix_path = "/".join(segments)
        windows_path = "\\".join(segments)
        for split in range(len(segments)):
            root = "/".join(segments[:split]) or "/"
            self.assertEqual(
                canonical_relpath(root, posix_path),
                canonical_relpath(root, windows_path),
            )


class HardwareTrustAnchorTest(unittest.TestCase):
    def test_backend_is_one_of_the_four(self) -> None:
        self.assertIn(HardwareTrustAnchor().backend, BACKENDS)

    def test_pinned_backend_is_honored(self) -> None:
        for name in BACKENDS:
            self.assertEqual(HardwareTrustAnchor(backend=name).backend, name)

    def test_unknown_backend_falls_back_to_software_key(self) -> None:
        self.assertEqual(HardwareTrustAnchor(backend="quantum").backend, "software_key")

    def test_sign_returns_a_nonempty_signature_and_the_backend_that_produced_it(self) -> None:
        # Encoding differs by backend (software_key: hex HMAC; secure_enclave:
        # base64 CryptoKit signature) so only non-emptiness and backend
        # membership are asserted here, not a fixed alphabet.
        anchor = HardwareTrustAnchor()
        sig, used_backend = anchor.sign("deadbeef" * 8)
        self.assertTrue(sig)
        self.assertIsInstance(sig, str)
        self.assertIn(used_backend, BACKENDS)

    def test_software_key_sign_is_deterministic_for_the_same_digest(self) -> None:
        anchor = HardwareTrustAnchor(backend="software_key")
        sig1, backend1 = anchor.sign("cafebabe")
        sig2, backend2 = anchor.sign("cafebabe")
        self.assertEqual(sig1, sig2)
        self.assertEqual(backend1, backend2)
        self.assertEqual(backend1, "software_key")

    def test_software_key_verify_founder_presence_is_always_true(self) -> None:
        anchor = HardwareTrustAnchor(backend="software_key")
        self.assertTrue(anchor.verify_founder_presence("test"))

    def test_windows_hello_backend_without_winrt_denies_presence(self) -> None:
        # No winrt runtime exists on this (macOS) test host, so a pinned
        # windows_hello anchor must fail closed, not raise.
        anchor = HardwareTrustAnchor(backend="windows_hello")
        self.assertFalse(anchor.verify_founder_presence("test"))

    def test_fido2_backend_without_fido2_package_denies_presence(self) -> None:
        anchor = HardwareTrustAnchor(backend="fido2")
        self.assertFalse(anchor.verify_founder_presence("test"))


if __name__ == "__main__":
    unittest.main()
