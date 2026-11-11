"""A legacy CLAIM comment must not poison an issue forever.

The contract that a claim names an `instruction` and a `plan` arrived after thousands of claims
were already posted. The gate refuses a malformed CLAIM comment, so ONE comment written before
that contract made an issue permanently unclaimable: idp#7878 carried 10 legacy comments and one
valid current claim and still refused a lane that touched nothing but its own files.

The decision under test is the gate's own collection loop, EXTRACTED FROM bin/claim-gate and
executed -- not restated here. If the loop cannot be found the test fails BLIND rather than
passing on a guess.

  legacy only          -> REFUSED (nothing valid to land on: still a real failure)
  legacy, then current -> OK      (the newest claim is the claim of record)
  current, then legacy -> REFUSED (the newest claim is the broken one)
"""

import importlib.machinery
import importlib.util
import os
import re
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
# Overridable so this suite can be pointed at a mutant of the gate, which is how its own
# ability to FAIL is proven (see bin/gate-can-fail).
GATE = Path(os.environ.get("CLAIM_GATE_PATH") or (REPO / "bin" / "claim-gate"))

LEGACY = "CLAIM agent=estate-agent paths=bin/x,tests/x.py heartbeat=2026-11-10T23:15:20Z"
CURRENT = (
    "CLAIM agent=estate-agent instruction=INS-00007 "
    "plan=fe65d1af3c4f6485ec3327e828c32578078a40469f51173360c00ce29d3b751a "
    "paths=bin/x,tests/x.py heartbeat=2026-11-11T01:24:56Z"
)

# The gate's claim-collection block starts at this exact line; _extract_block finds it by
# indentation so the test grades the shipped body rather than a restatement of it.
LOOP_ANCHOR = "        claims = []"


def _load_gate():
    loader = importlib.machinery.SourceFileLoader("claim_gate_under_test", str(GATE))
    spec = importlib.util.spec_from_loader("claim_gate_under_test", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def _extract_block(src):
    """The gate's claim-collection block, taken from the file by indentation.

    The block runs from `claims = []` to (and including) the `if malformed:` / `if not claims:`
    guard that closes it. Everything after that point is the gate's comparison logic, which needs
    variables this test does not supply, so it must not be swept in.

    Returns the block at its original indentation, or None when it is not there.
    """
    lines = src.splitlines()
    for i, line in enumerate(lines):
        if line != LOOP_ANCHOR:
            continue
        block = [line]
        for nxt in lines[i + 1 :]:
            if not nxt.strip():
                block.append(nxt)
                continue
            if not nxt.startswith("        "):
                break
            block.append(nxt)
            stripped = nxt.strip()
            # The guard that closes the collection section, plus its body.
            if stripped in ("if malformed:", "if not claims:"):
                closing = stripped
                idx = len(block)
                for after in lines[i + 1 + idx :]:
                    if not after.strip():
                        block.append(after)
                        continue
                    if not after.startswith("            "):
                        break
                    block.append(after)
                assert closing  # the guard we stopped at
                return "\n".join(block) + "\n"
        return "\n".join(block) + "\n"
    return None


def _decision(bodies):
    """Run the GATE'S OWN collection loop over these comment bodies and return its verdict."""
    assert GATE.exists(), f"no gate at {GATE}"
    gate = _load_gate()

    block = _extract_block(GATE.read_text())
    assert block, (
        f"the claim-collection block was not found in {GATE}: this test can no longer read "
        "the gate's decision out of the gate, so it proves nothing"
    )

    # The block sits inside a `for comment in comments:` loop, so it is re-wrapped in the same
    # loop here: the gate's own body is executed, not a copy of it.
    source = "for comment in comments:\n" + block
    try:
        code = compile(source, str(GATE), "exec")
    except SyntaxError as exc:  # BLIND, not a pass
        pytest.fail(f"the extracted block does not compile: {exc}")

    ns = {
        "parse_claim_line": gate.parse_claim_line,
        "ClaimContractError": gate.ClaimContractError,
        "where": "#1",
        "comments": [{"body": b} for b in bodies],
        "claims": [],
        "problems": [],
        "malformed": [],
    }
    exec(code, ns)  # noqa: S102 -- executing the shipped gate's own block, by design

    claims = ns.get("claims") or []
    problems = ns.get("problems") or []
    return "OK" if (claims and not problems) else "REFUSED"


def test_a_legacy_claim_alone_still_refuses():
    """Nothing valid to land on is still a refusal, not a pass."""
    assert _decision([LEGACY]) == "REFUSED"


def test_a_current_claim_supersedes_a_legacy_comment():
    """THE DEFECT: the newest claim is the claim of record, so the legacy one is history."""
    assert _decision([LEGACY, CURRENT]) == "OK"


def test_a_legacy_comment_after_a_current_one_still_refuses():
    """Supersession runs one way only: a newer malformed claim is the one in force."""
    assert _decision([CURRENT, LEGACY]) == "REFUSED"


def test_the_gate_grades_the_claim_of_record():
    """The fix must be supersession, not 'ignore malformed comments'."""
    assert _decision([LEGACY, LEGACY, CURRENT]) == "OK"
    assert _decision([CURRENT, CURRENT]) == "OK"
