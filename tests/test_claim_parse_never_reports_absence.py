"""DBG-035's falsifier: a claim the gate cannot parse must never be reported as absent.

Measured on origin/main, bin/claim-gate matches a claim with

    ^CLAIM\\s+agent=(?P<agent>\\S+)\\s+(?:model=\\S+\\s+)?paths=(?P<paths>\\S+)\\s+heartbeat=(?P<hb>\\S+)\\s*$

while a newer bin/claim-open emits `CLAIM agent=<a> instruction=<INS> plan=<sha> paths=<p>
heartbeat=<t>`. The two do not agree, so the comment does not match, `claims` is empty, and the
gate's `if not claims:` branch prints "has no CLAIM comment" -- reporting absence when the real
fact is "a claim I could not parse".

This test reads the regex OUT OF the shipped gate. It does not inline a copy: a copy would
keep passing after the gate was fixed, and a falsifier that cannot notice the fix is a
paragraph with a pytest decorator.

It asserts both directions so it cannot pass by refusing everything:
  * the extended shape does NOT match the shipped regex  -> the gate cannot see it
  * the legacy shape DOES match                         -> the check is not vacuous
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import re
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
# CLAIM_GATE_PATH lets a falsifier-of-the-falsifier point this test at a mutated copy and
# prove it goes RED. Without an override the test always grades the shipped gate.
GATE = Path(os.environ.get("CLAIM_GATE_PATH") or (REPO / "bin" / "claim-gate"))

LEGACY = "CLAIM agent=estate-agent paths=bin/pin-open,tests/test_pin_open.py heartbeat=2026-11-11T01:28:41Z"
EXTENDED = (
    "CLAIM agent=estate-agent instruction=INS-00007 "
    "plan=fe65d1af3c4f6485ec3327e828c32578078a40469f51173360c00ce29d3b751a "
    "paths=bin/pin-open,tests/test_pin_open.py heartbeat=2026-11-11T01:28:41Z"
)


def _shipped_claim_regex() -> re.Pattern[str]:
    """Load the gate as a module and take ITS CLAIM pattern. Never a local copy."""
    # bin/claim-gate has no .py suffix, so spec_from_file_location returns None and no
    # loader exists. An extensionless shipped script needs SourceFileLoader named explicitly.
    loader = importlib.machinery.SourceFileLoader("claim_gate_under_test", str(GATE))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None:
        raise AssertionError(f"BLIND: cannot build a spec for {GATE}")
    module = importlib.util.module_from_spec(spec)
    try:
        loader.exec_module(module)
    except (
        SystemExit
    ) as exc:  # the gate guards its own argv; entry is not under test here
        if exc.code not in (0, None):
            raise
    pattern = getattr(module, "CLAIM", None)
    if not isinstance(pattern, re.Pattern):
        raise AssertionError(
            f"BLIND: {GATE} exposes no CLAIM regex, so nothing about its parsing was graded"
        )
    return pattern


def test_the_shipped_gate_cannot_parse_the_extended_claim_shape():
    pattern = _shipped_claim_regex()
    assert pattern.search(EXTENDED) is None, (
        "DBG-035 no longer reproduces: the shipped gate now parses the instruction=/plan= "
        "shape. Move the pack to `fixed` and keep this assertion inverted."
    )


def test_the_check_is_not_vacuous_a_legacy_claim_still_matches():
    pattern = _shipped_claim_regex()
    match = pattern.search(LEGACY)
    assert match is not None, (
        "the shipped gate no longer parses even the legacy claim shape -- the falsifier is "
        "grading the wrong thing, or the regex was broken wider than DBG-035"
    )
    assert match.group("agent") == "estate-agent"
    assert "bin/pin-open" in match.group("paths")


def test_an_unparsed_claim_is_what_prints_has_no_claim_comment():
    """The two facts that make this a defect, read out of the gate's own source."""
    src = GATE.read_text()
    assert "has no CLAIM comment" in src, "the message this pack is about is gone"
    assert "malformed" not in src, (
        "the gate now tracks malformed claims -- DBG-035 has been fixed, so re-grade it "
        "as `fixed` rather than leaving a pack that describes an old shape"
    )
