"""crew#684 CP6: the login drill grades the tiles a page shows, not its heading.

The class of mistake (crew#684, 2026-08-30): the drill graded /ops green while every tile on
it could say "could not be read"; only the heading was waited for. A page that renders its
frame and none of its numbers is the instrument-nobody-reads class (LAW 28) wearing a green
badge. The drill now fails a published path whose body carries the phrase the Ops page prints
when a source cannot be read, and this test pins that phrase to every error tile in the module,
so the drill and the page can never drift apart silently (R53: a sentence a person reads, never
a selector or a test id).
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRILL = ROOT / "bin/idp-login-drill"
OPS = ROOT / "backstage/packages/app/src/modules/home/Ops.tsx"
UNREAD = "could not be read"


def test_the_drill_fails_a_page_whose_tile_could_not_read_its_source():
    src = DRILL.read_text()
    assert f'UNREAD = "{UNREAD}"' in src
    loop = src[
        src.index("for path in PUBLISHED:") : src.index("published paths answer")
    ]
    assert "if UNREAD in shown.lower():" in loop
    assert "a tile could not read its source" in loop


def test_every_error_tile_on_the_ops_page_says_the_phrase_the_drill_grades():
    src = OPS.read_text()
    # Every sentence that says a source is unknown carries the graded phrase; a tile that
    # words it differently would read green in the drill.
    unknowns = re.findall(r"[^.{}\n]*\bunknown\b[^.{}\n]*", src)
    assert unknowns, "the Ops page has no error tile"
    for sentence in unknowns:
        assert UNREAD in sentence.lower(), sentence


def test_no_drill_row_grades_a_selector_or_a_test_id():
    """Founder 2026-09-03: and never wording either -- rows are bare paths only."""
    src = DRILL.read_text()
    table = src[src.index("PUBLISHED = (") : src.index("broken = []")]
    assert "text=" not in table and "must_see" not in src
    for path in re.findall(r'"([^"]+)"', table):
        assert re.fullmatch(r"[a-z][a-z-]*", path), f"{path}: not a bare path"
