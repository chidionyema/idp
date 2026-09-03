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


def test_every_feature_file_has_at_least_one_scenario_with_a_then():
    for n in CHECKPOINTS:
        text = (PROSE / f"messaging-cp{n}.feature").read_text()
        assert re.search(r"^\s+Scenario: ", text, re.M), f"cp{n} has no scenario"
        assert re.search(r"^\s+Then ", text, re.M), f"cp{n} grades nothing"
