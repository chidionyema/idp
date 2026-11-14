"""Engineer packet integrity checks; NOT evidence of deployment or assignment."""
from __future__ import annotations

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/specs/2026-11-14-engineering-delivery-and-ownership.json"
SOURCES = (
    ROOT / "docs/specs/2026-11-14-machine-first-execution-requirements.json",
    ROOT / "docs/specs/2026-11-14-pedantic-schema-first-class.json",
    ROOT / "docs/specs/2026-11-14-meridian-short-domain-acquisition.json",
    ROOT / "docs/specs/2026-11-14-concierge-domain-procurement.json",
)


def expand_req(value: str) -> list[str]:
    if ".." not in value:
        return [value]
    start, end = value.split("..", 1)
    prefix, count = start.rsplit("-", 1)
    end_prefix, end_count = end.rsplit("-", 1)
    if prefix != end_prefix:
        raise ValueError("cross-prefix range")
    return [f"{prefix}-{i:0{len(count)}d}" for i in range(int(count), int(end_count)+1)]


class EngineerPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(SPEC.read_text())
        cls.sources = [json.loads(x.read_text()) for x in SOURCES]
        cls.req_ids = {
            row["id"] for src in cls.sources for row in src["requirements"]
        }

    def test_six_unique_packets(self):
        packets = self.doc["packets"]
        self.assertEqual(len(packets), 6)
        self.assertEqual(len({p["packet"] for p in packets}), 6)

    def test_existing_authority_reconciliation_is_explicit(self):
        text = json.dumps(self.doc)
        for issue in ("#7940", "#7794", "#8111", "#7089", "#7838", "#7771", "#7222"):
            self.assertIn(issue, text)
        self.assertIn("legacy", text.lower())
        self.assertIn("Pydantic", text)

    def test_every_packet_has_owner_scope_and_adversarial_acceptance(self):
        for p in self.doc["packets"]:
            with self.subTest(p=p["packet"]):
                for name in ("issue", "leader_capability", "paths_read",
                             "paths_own", "engineering_steps", "positive",
                             "negative", "release_receipts", "depends_on"):
                    self.assertTrue(p.get(name), name)

    def test_every_required_id_has_an_original_contract(self):
        for p in self.doc["packets"]:
            for requirement in p["required_ids"]:
                for name in expand_req(requirement):
                    self.assertIn(name, self.req_ids, f"{p['packet']}: {name}")

    def test_no_duplicate_contract_identifiers(self):
        for s in self.sources:
            ids = [r["id"] for r in s["requirements"]]
            self.assertEqual(len(ids), len(set(ids)))

    def test_no_side_effect_dispatch_in_spec(self):
        self.assertIn("NOT_FLEET_DISPATCHED", self.doc["status"])
        self.assertIn("founder-passkey", self.doc["assignment_contract"]["promotion"])

    def test_cross_packet_mapping(self):
        packet_ids = {x["packet"] for x in self.doc["packets"]}
        mapped = set()
        for item in self.doc["single_source_owner_index"]:
            mapped.update(item["packets"])
        self.assertEqual(mapped, packet_ids)

    def test_existing_claim_and_queued_runner_are_not_dropped(self):
        rows = {x["issue"]: x for x in self.doc["assignment_observations"]}
        self.assertEqual(rows["#8111"]["actor"], "claude")
        self.assertEqual(rows["#7838"]["observed_status"], "queued")
        self.assertIn("Do not", rows["#8111"]["instruction"])

    def test_native_source_and_portable_schema_requirements_preserved(self):
        p = next(x for x in self.doc["packets"] if x["packet"] == "ENG-03")
        self.assertIn("#8111", p["issue"])
        self.assertIn("Pydantic", json.dumps(p))
        self.assertIn("Rust", json.dumps(p))

if __name__ == "__main__":
    unittest.main()
