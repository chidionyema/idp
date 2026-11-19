"""Ownership transitions must never launder a producer into its own verifier."""

import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "platform/estate/karma/contracts.py"
spec = importlib.util.spec_from_file_location("karma_contract", PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

A = "urn:agent:producer"
B = "urn:agent:successor"
V = "urn:agent:independent-verifier"
DIGEST = "b" * 64


def event(eid, kind, actor, parent=None, **fields):
    return dict(
        event_id=eid, kind=kind, agent_urn=actor, instruction_id="I-1",
        recorded_at="2026-11-19T09:00:00Z",
        parent_event_ids=[parent] if parent else [], **fields,
    )


class YieldAuthorityTests(unittest.TestCase):
    def test_producer_identity_survives_handover_and_resubmission(self):
        accepted = event("1", "INSTRUCTION_ACCEPTED", A, expected_outcome_digest="a" * 64)
        submitted = event("2", "YIELD_SUBMITTED", A, "1", evidence_digest=DIGEST)
        handed = event("3", "OWNERSHIP_HANDBACK", A, "2", successor_agent_urn=B)
        resubmitted = event("5", "YIELD_SUBMITTED", B, "3", evidence_digest=DIGEST)
        unknown = event("7", "YIELD_SUBMITTED", "UNKNOWN", "1", evidence_digest=DIGEST)
        cases = [
            ("producer after handoff", [submitted, handed], A, "3", DIGEST, False),
            ("oracle after handoff", [submitted, handed], V, "3", DIGEST, True),
            ("current owner", [submitted], A, "2", DIGEST, False),
            ("unknown verifier", [submitted], "UNKNOWN", "2", DIGEST, False),
            ("different digest", [submitted], V, "2", "c" * 64, False),
            ("oracle", [submitted], V, "2", DIGEST, True),
            ("laundered resubmission", [submitted, handed, resubmitted], A, "5", DIGEST, False),
            ("oracle after resubmission", [submitted, handed, resubmitted], V, "5", DIGEST, True),
            ("unknown producer", [unknown], V, "7", DIGEST, False),
        ]
        for name, history, actor, parent, digest, expected in cases:
            with self.subTest(name=name):
                verdict = event("9", "YIELD_INDEPENDENTLY_VERIFIED", actor, parent, evidence_digest=digest)
                # Deliberately permissive test-only oracle exercises the reducer's
                # structural checks; this is not an authenticated QUAD receipt.
                result = mod.project([accepted, *history, verdict], lambda _: True)
                self.assertEqual(result["obligations"]["I-1"]["verified_yield"], expected)
                self.assertEqual(not result["unresolved"], expected)
