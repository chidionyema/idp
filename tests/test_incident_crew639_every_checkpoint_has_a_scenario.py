"""crew#639 CP1: the messaging day-0 design is graded before code.

Incident class: a checkpoint built from prose (summary-over-source). Every checkpoint on crew#639
has a feature file tagged with its number, and the ADR carries the eight decisions and the R1
ruling, so a worker session builds against a scenario and never against a paragraph.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROSE = ROOT / "docs" / "prose"
ADR = ROOT / "docs" / "decisions" / "0012-messaging-day-0.md"
CHECKPOINTS = range(1, 11)


def test_every_checkpoint_has_a_tagged_feature_file():
    missing = [
        n
        for n in CHECKPOINTS
        if not (PROSE / f"messaging-cp{n}.feature").exists()
        or f"@cp{n}\n" not in (PROSE / f"messaging-cp{n}.feature").read_text()
    ]
    assert missing == [], f"checkpoints without a tagged scenario: {missing}"


def test_every_feature_file_has_at_least_one_scenario_with_a_then():
    for n in CHECKPOINTS:
        text = (PROSE / f"messaging-cp{n}.feature").read_text()
        assert re.search(r"^\s+Scenario: ", text, re.M), f"cp{n} has no scenario"
        assert re.search(r"^\s+Then ", text, re.M), f"cp{n} grades nothing"


def test_the_eight_acceptance_tests_of_section_11_are_scenarios():
    text = "\n".join((PROSE / f"messaging-cp{n}.feature").read_text() for n in CHECKPOINTS)
    found = {int(m) for m in re.findall(r"§11 test (\d)", text)}
    assert found == set(range(1, 9)), f"§11 tests without a scenario: {sorted(set(range(1, 9)) - found)}"


def test_the_adr_records_the_eight_decisions_and_the_r1_ruling():
    text = ADR.read_text()
    for d in ("D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8"):
        assert f"| {d} |" in text, f"{d} missing from the ADR"
    assert "R1 on day 0" in text
