"""Executable integrity contract for the machine-first requirements register.

These tests validate requirements *data*, not operational deployment or release approval.
"""
from __future__ import annotations

import copy
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
REGISTER = (
    ROOT / "docs/specs/2026-11-14-machine-first-execution-requirements.json"
)


def validate(record: dict) -> list[str]:
    problems: list[str] = []
    if record.get("schema") != "estate.deterministic-workforce-requirements.v1":
        problems.append("schema")
    rows = record.get("requirements")
    if not isinstance(rows, list) or not rows:
        return problems + ["requirements missing"]
    ids: set[str] = set()
    for row in rows:
        rid = row.get("id", "")
        if not rid.startswith("DET-"):
            problems.append("invalid requirement id")
        if rid in ids:
            problems.append(f"duplicate requirement {rid}")
        ids.add(rid)
        if row.get("decision") not in ("machine", "model", "judgment"):
            problems.append(f"{rid}: invalid decision")
        if row.get("priority") not in ("P0", "P1", "P2"):
            problems.append(f"{rid}: invalid priority")
        if row.get("classification") not in (
            "code_present", "observed_failure", "historical_proposal", "integration_gap"
        ):
            problems.append(f"{rid}: invalid evidence classification")
        for field in ("owner", "phase", "contract", "positive", "negative"):
            if not row.get(field):
                problems.append(f"{rid}: missing {field}")
        for field in ("source", "measure"):
            if not isinstance(row.get(field), list) or not row[field]:
                problems.append(f"{rid}: missing {field}")
        if row.get("decision") == "machine" and not row.get("negative"):
            problems.append(f"{rid}: machine has no falsifier")
    waves = record.get("operational_sequence") or []
    covered: list[str] = []
    for wave in waves:
        covered.extend(wave.get("requirements", []))
    if set(covered) != ids:
        problems.append("wave coverage mismatch")
    if len(covered) != len(set(covered)):
        problems.append("requirements assigned to multiple waves")
    if not record.get("release_gates"):
        problems.append("release gates missing")
    if not record.get("cross_repository_review", {}).get("surveyed"):
        problems.append("cross-repository review absent")
    return problems


class RequirementRegisterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.register = json.loads(REGISTER.read_text())

    def test_schema_and_complete_coverage(self) -> None:
        self.assertEqual(validate(self.register), [])

    def test_no_unaccountable_agent_actions(self) -> None:
        for req in self.register["requirements"]:
            self.assertTrue(req["owner"] and req["decision"] and req["negative"])

    def test_critical_admission_and_capacity_examples_captured(self) -> None:
        all_text = json.dumps(self.register)
        for piece in (
            "8105", "43629366222", "429", "20", "founder-passkey",
            "BLIND", "Greenlane", "Hermes",
        ):
            self.assertIn(piece, all_text)

    def test_canonical_agent_entry_points_to_register(self) -> None:
        text = (ROOT / "AGENTS.md").read_text()
        self.assertIn(REGISTER.name, text)

    def test_duplicate_requirement_is_rejected(self) -> None:
        mutant = copy.deepcopy(self.register)
        mutant["requirements"].append(copy.deepcopy(mutant["requirements"][0]))
        self.assertTrue(any("duplicate requirement" in x for x in validate(mutant)))

    def test_orphan_requirement_is_rejected(self) -> None:
        mutant = copy.deepcopy(self.register)
        mutant["operational_sequence"][0]["requirements"].pop()
        self.assertIn("wave coverage mismatch", validate(mutant))

    def test_falsifier_removed_is_rejected(self) -> None:
        mutant = copy.deepcopy(self.register)
        mutant["requirements"][0]["negative"] = ""
        self.assertTrue(any("missing negative" in x for x in validate(mutant)))

    def test_unclassified_machine_decider_is_rejected(self) -> None:
        mutant = copy.deepcopy(self.register)
        mutant["requirements"][0]["decision"] = "vibes"
        self.assertTrue(any("invalid decision" in x for x in validate(mutant)))


if __name__ == "__main__":
    unittest.main()
