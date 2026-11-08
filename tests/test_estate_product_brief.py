"""Product priority is available in one hop and cannot claim market readiness.

Source from the SAME existing buyer catalogue, not a second product registry.
"""
import importlib.machinery
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "bin/estate-product-brief"
loader = importlib.machinery.SourceFileLoader("estate_product_brief", str(ENTRY))
spec = importlib.util.spec_from_loader(loader.name, loader)
mod = importlib.util.module_from_spec(spec)
loader.exec_module(mod)


class ProductOnboardingTests(unittest.TestCase):
    def test_six_waves_from_existing_canonical_source(self):
        item = mod.source_packet()
        self.assertEqual(tuple(item["waves"]), mod.STAGES)
        self.assertEqual(item["status"], "SOURCE_PROPOSAL_NOT_VERIFIED")
        self.assertFalse(item["release_authority"])
        self.assertEqual(item["source_file"], "docs/marketing/index.md")
        self.assertTrue(item["section_sha256"])

    def test_concise_must_prioritize_product_and_proof(self):
        out = mod.concise(mod.source_packet())
        for token in ("P0", "P1", "P2", "P3", "P4", "P5", "NOT FOR SALE",
                      "no founder-local infrastructure", "no retired OKE",
                      "no unapproved paid", "not independently verified",
                      "Funding/grants", "UNKNOWN", "Source SHA256"):
            with self.subTest(token=token):
                self.assertIn(token.lower(), out.lower())

    def test_cli_machine_json_is_source_only(self):
        result = subprocess.run([sys.executable, str(ENTRY), "--json"],
                                capture_output=True, text=True, check=True)
        packet = json.loads(result.stdout)
        self.assertFalse(packet["release_authority"])
        self.assertNotIn("source_text", packet)
        self.assertEqual(packet["funding_priority"], "P5_AFTER_PRODUCT_PROOF")

    def test_check_proves_only_document_contract(self):
        result = subprocess.run([sys.executable, str(ENTRY), "--check"],
                                capture_output=True, text=True, check=True)
        self.assertIn("NOT verified", result.stdout)

    def test_missing_canonical_roadmap_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.md"
            path.write_text("# old sales catalogue\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                mod.source_packet(path)

    def test_missing_product_proof_wave_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.md"
            original = mod.CATALOGUE.read_text(encoding="utf-8")
            modified = "\n".join(
                line for line in original.splitlines() if not line.startswith("| **P2")
            )
            path.write_text(modified, encoding="utf-8")
            with self.assertRaises(ValueError):
                mod.source_packet(path)

    def test_removed_no_local_constraint_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.md"
            original = mod.CATALOGUE.read_text(encoding="utf-8")
            # Remove the only verified "zero" term and the other known-constraints
            # so this packet cannot represent a silently weakened constitution.
            segment = original[original.index(mod.START):original.index(mod.END)]
            damaged = segment.replace("zero", "").replace("unverified", "")
            path.write_text(original.replace(segment, damaged), encoding="utf-8")
            with self.assertRaises(ValueError):
                mod.source_packet(path)


if __name__ == "__main__":
    unittest.main()
