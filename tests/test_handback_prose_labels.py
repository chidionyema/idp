"""A phrase in a table row is a label, not a hand-back.

Measured 2026-11-27: the stop hook blocked a status report because a table column
was headed "Still open". The founder's rule is about what a turn DOES -- returning
work to the reader -- so a phrase inside a table row, a code fence or an inline
code span is not evidence of handing work back. Headings and prose are untouched.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform/estate/memory"))

import handback  # noqa: E402


def test_a_phrase_inside_a_table_row_is_a_label_not_a_handback():
    report = "| Seam | State |\n|---|---|\n| Still open | needs the Allow click |\n"
    assert not handback.judge(report)["block"]


def test_a_phrase_inside_a_code_fence_is_not_a_handback():
    assert not handback.judge("```\nStill open: example\n```")["block"]


def test_a_real_handback_still_blocks_after_the_label_exemption():
    assert handback.judge("Done. Still open: the deploy.")["block"]
    assert handback.judge("Want me to continue?")["block"]
