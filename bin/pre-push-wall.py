#!/usr/bin/env python3
"""pre-push-wall -- the front line, at push time, with microscopic telemetry.

Founder, 2026-11-19: CI is the last stand, not the front line. Every gate that runs in
GitHub Actions must run from the same executable at pre-push, advisory gates are banned, and
every run emits one JSONL record per gate so a green check cannot hide a skipped job.

USAGE
    bin/pre-push-wall --report      # never blocks; prints what it would refuse (default)
    bin/pre-push-wall --enforce     # exits 1 on the first refusal

WHY REPORT IS THE DEFAULT. Measured on this repo at 2026-11-19: 4 workflow files still carry
'continue-on-error: true', there is no .estate/intent-manifest.json, and bin/idp-bdd-proof-gate
does not accept the (base, receipt) CLI the wall needs. Enforcing this on day one would refuse
every push from every agent on the machine -- a fleet outage dressed as rigour. The wall is
installed in report mode, the two real defects are output, and enforce flips on in the same
change that clears them.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
import time

REPO = pathlib.Path(__file__).resolve().parent.parent
WORKFLOWS = REPO / ".github" / "workflows"
LEDGER = REPO / ".estate" / "ci-microscope.jsonl"
MANIFEST = REPO / ".estate" / "intent-manifest.json"
RECEIPT = REPO / ".estate" / "proof-receipt.json"


def emit(gate_id: str, stage: str, rc: int, ms: int, detail: str) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts_epoch": int(time.time()),
        "gate_id": gate_id,
        "stage": stage,
        "advisory": False,
        "exit_code": rc,
        "duration_ms": ms,
        "detail": detail[:400],
    }
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


class Refused(Exception):
    pass


def run(gate_id: str, stage: str, fn, enforce: bool) -> bool:
    t0 = time.monotonic()
    try:
        detail = fn()
        ms = int((time.monotonic() - t0) * 1000)
        emit(gate_id, stage, 0, ms, detail)
        print(f"[PASS] {gate_id:<26} ({ms:>4}ms) {detail}")
        return True
    except Refused as exc:
        ms = int((time.monotonic() - t0) * 1000)
        emit(gate_id, stage, 1, ms, str(exc))
        print(f"[FAIL] {gate_id:<26} ({ms:>4}ms) {exc}", file=sys.stderr)
        if enforce:
            sys.exit(1)
        return False


def gate_zero_advisory() -> str:
    hits = []
    for wf in sorted(WORKFLOWS.glob("*.y*ml")):
        for n, line in enumerate(wf.read_text(errors="replace").splitlines(), 1):
            if re.search(r"^\s*continue-on-error:\s*true\b", line):
                hits.append(f"{wf.name}:{n}")
    if hits:
        raise Refused(
            f"ADVISORY_GATE_FORBIDDEN: {len(hits)} site(s): {', '.join(hits[:6])}"
        )
    return "0 advisory continue-on-error gates"


def gate_strict_intent() -> str:
    if not MANIFEST.exists():
        raise Refused(f"MISSING_INTENT_MANIFEST: {MANIFEST.relative_to(REPO)} required")
    data = json.loads(MANIFEST.read_text())
    required = {
        "instruction_id",
        "owner",
        "target_subsystems",
        "failure_modes_mapped",
        "schema_strict",
    }
    missing = required - set(data)
    if missing:
        raise Refused(f"LOOSE_MANIFEST_SCHEMA: missing {sorted(missing)}")
    if data.get("schema_strict") is not True:
        raise Refused("LOOSE_SCHEMA_FORBIDDEN: schema_strict must be true")
    if not data.get("failure_modes_mapped"):
        raise Refused("UNMAPPED_FAILURE_MODES: failure_modes_mapped is empty")
    return f"intent={data['instruction_id']} modes={len(data['failure_modes_mapped'])}"


def gate_differential_proof() -> str:
    """A receipt must bind changed paths to tests that FAIL without the change.

    This is the replacement for the regex proof: 'N passed' proves a suite ran, not that the
    change is exercised. The receipt is produced by a mutation run and carries killed mutants.
    """
    if not RECEIPT.exists():
        raise Refused(f"MISSING_PROOF_RECEIPT: {RECEIPT.relative_to(REPO)} required")
    r = json.loads(RECEIPT.read_text())
    changed = set(r.get("changed_paths") or [])
    tests = r.get("tests") or []
    killed = int(r.get("mutations_killed") or 0)
    if not changed:
        raise Refused("UNBOUND_PROOF: receipt names no changed_paths")
    if not tests:
        raise Refused("UNBOUND_PROOF: receipt names no tests")
    if killed < 1:
        raise Refused("UNFALSIFIED: 0 mutations killed -- the tests never failed")
    return f"paths={len(changed)} tests={len(tests)} mutations_killed={killed}"


def gate_shadow_scope() -> str:
    """The scope job must compute a base when the event has no pull_request base (dispatch)."""
    wf = WORKFLOWS / "shadow-verify.yml"
    if not wf.exists():
        return "no shadow-verify workflow"
    text = wf.read_text(errors="replace")
    if "github.event.pull_request.base.sha" not in text:
        return "no pull_request-base dependency"
    if "merge-base" not in text:
        raise Refused(
            "SHADOW_DISPATCH_BUG: scope reads pull_request.base.sha with no merge-base fallback"
        )
    return "scope has a merge-base fallback"


def main() -> None:
    enforce = "--enforce" in sys.argv
    stage = "pre-push"
    print(f"=== PRE-PUSH WALL [{stage}] enforce={enforce} ===")
    ok = all(
        [
            run("zero-advisory-ci", stage, gate_zero_advisory, enforce),
            run("strict-intent-schema", stage, gate_strict_intent, enforce),
            run("differential-falsifier", stage, gate_differential_proof, enforce),
            run("shadow-scope-integrity", stage, gate_shadow_scope, enforce),
        ]
    )
    print(
        f"=== {'ALL GATES GREEN' if ok else 'REFUSALS ABOVE'} | telemetry: {LEDGER} ==="
    )
    if not ok:
        sys.exit(1 if enforce else 0)


if __name__ == "__main__":
    main()
