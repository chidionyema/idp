"""crew#684 CP6, closed the other way on the founder's ruling (2026-09-03).

The original check failed a page whose body carried the phrase "could not be read".
Run 33710834723 showed why that is the banned wording class through the back door:
the tools page carries the phrase as tile explainer copy, and the ops page carries it
truthfully quoting the inventory's own blind planes -- both pages answered. Founder
ruling: a drill grades whether a path answers, never any sentence on it. This file
keeps the one property that survives: a drill row is a bare path.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRILL = ROOT / "bin/idp-login-drill"


def test_no_drill_row_grades_a_selector_or_a_test_id():
    """Founder 2026-09-03: and never wording either -- rows are bare paths only."""
    src = DRILL.read_text()
    table = src[src.index("PUBLISHED = (") : src.index("broken = []")]
    assert "text=" not in table and "must_see" not in src
    for path in re.findall(r'"([^"]+)"', table):
        assert re.fullmatch(r"[a-z][a-z-]*", path), f"{path}: not a bare path"


def test_the_drill_greps_no_phrase_out_of_a_page_body():
    """No sentence-grep may come back: answering is load + 200 + no 404 shell + no JS error."""
    src = DRILL.read_text()
    loop = src[
        src.index("for path in PUBLISHED:") : src.index("published paths answer")
    ]
    assert "UNREAD" not in loop and "could not be read" not in loop
