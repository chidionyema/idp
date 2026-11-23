"""Source-faithful instruction anatomy. Candidates are not verified outcomes."""
from __future__ import annotations
import datetime as dt
import hashlib
import re
from typing import Any

SCHEMA = "meridian.instruction-anatomy/1"


def clauses(raw: str) -> list[dict[str, Any]]:
    """Offsets index exact original Unicode text, without normalisation."""
    rows: list[dict[str, Any]] = []
    for match in re.finditer(r"[^\n]+", raw):
        line = match.group()
        for part in re.finditer(r"\S(?:.*?\S)?(?=(?:[.!?](?:\s|$))|$)", line):
            start, end = match.start() + part.start(), match.start() + part.end()
            quote = raw[start:end]
            if quote.strip():
                rows.append({"id": f"C{len(rows)+1:04d}", "start": start, "end": end,
                             "source_quote": quote, "intent": "UNINTERPRETED",
                             "acceptance_oracle": "UNBOUND", "bdd_status": "UNBOUND"})
    if not rows and raw.strip():
        start, end = len(raw) - len(raw.lstrip()), len(raw.rstrip())
        rows.append({"id": "C0001", "start": start, "end": end,
                     "source_quote": raw[start:end], "intent": "UNINTERPRETED",
                     "acceptance_oracle": "UNBOUND", "bdd_status": "UNBOUND"})
    return rows


def compile_instruction(raw: str) -> dict[str, Any]:
    """Do not hallucinate meaning, business value, or evidence."""
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("raw founder prompt required")
    sha = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    parts = clauses(raw)
    return {
        "schema": SCHEMA,
        "source_sha256": sha,
        "source_encoding": "utf-8",
        "span_units": "unicode-codepoints",
        "source_length": len(raw),
        "captured_at_observer_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds"),
        "clauses": parts,
        "bdd": {
            "admission_scenario": "python3 -m unittest discover -s tests -p test_instruction_spec_contract.py",
            "admission_status": "STRUCTURAL_CHECK_ONLY",
            "semantic_scenarios": [
                {"clause_id": p["id"], "source_sha256": sha,
                 "gherkin": "Given the cited founder clause; When the outcome is executed; Then the independently observed invariant must hold",
                 "runner": "UNBOUND", "status": "UNVERIFIED"} for p in parts
            ],
        },
        "value_anatomy": {
            "founder_intellectual_origin": sha,
            "principles_and_hypotheses": "UNINTERPRETED",
            "beneficiary": "UNKNOWN",
            "expected_business_or_operational_delta": "UNKNOWN",
            "state_before": "UNKNOWN",
            "state_after": "UNKNOWN",
            "counterfactual": "UNKNOWN",
            "resource_and_opportunity_cost": "UNKNOWN",
            "causal_attribution": "UNVERIFIED",
            "yield_receipt": "UNVERIFIED",
        },
        "execution": {"state": "UNASSIGNED", "owner": "UNKNOWN", "authority": "UNVERIFIED"},
        "assurance": "NOT_OPERATIONAL_YIELD",
    }


def verify_source(raw: str, packet: dict[str, Any]) -> bool:
    """Structural integrity only; never semantic or production certification."""
    if not isinstance(raw, str) or packet.get("schema") != SCHEMA:
        return False
    if packet.get("source_sha256") != hashlib.sha256(raw.encode("utf-8")).hexdigest():
        return False
    if packet.get("source_length") != len(raw) or packet.get("span_units") != "unicode-codepoints":
        return False
    cited = packet.get("clauses")
    if not isinstance(cited, list) or not cited:
        return False
    for i, item in enumerate(cited, 1):
        a, b = item.get("start"), item.get("end")
        if item.get("id") != f"C{i:04d}" or not isinstance(a, int) or not isinstance(b, int):
            return False
        if not 0 <= a < b <= len(raw) or raw[a:b] != item.get("source_quote"):
            return False
    bdd = packet.get("bdd", {})
    if {s.get("clause_id") for s in bdd.get("semantic_scenarios", [])} != {x["id"] for x in cited}:
        return False
    return True
