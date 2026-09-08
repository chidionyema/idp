"""The claimant for tests/fixtures/graded-by-segments, and it never spells that path flat.

This file exists to be read by bin/idp-rule-coverage's textual scan, not to be run: it is the
regression for the trap that fixture pairs reached only through `ROOT / "a" / "b"` were
reported as graded by nothing. The whole proof is the spelling below.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAD = ROOT / "tests" / "fixtures" / "graded-by-segments" / "bad.yaml"
GOOD = ROOT / "tests" / "fixtures" / "graded-by-segments" / "good.yaml"


def test_the_pair_exists():
    assert BAD.exists() and GOOD.exists()
