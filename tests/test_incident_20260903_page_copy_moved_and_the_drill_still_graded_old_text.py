"""Incident 2026-09-03 (crew#816 window): the Tools redesign (#1191) changed the page's
wording, the login drill still graded /tools by the old sentence, and the founder's state
page branded a working page broken after rollout. Founder: content changes all the time; a
checker pinning hand-copied copy is drift waiting to happen.

The guard: every first-party path marker in the drill's PUBLISHED tuple must still appear in
the portal's own source. A PR that rewords a page without moving the drill's marker goes red
here, at PR time, in the repo where the wording changed -- never on the live state page.

Vendor-rendered paths (catalog, docs, create, ...) are excluded: their text comes from the
pinned Backstage packages and moves only on an upgrade, which ships its own drill sweep.
"""

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
DRILL = ROOT / "bin" / "idp-login-drill"
APP_SRC = ROOT / "backstage" / "packages" / "app" / "src"

FIRST_PARTY = {"tools", "ops", "reports", "pair", "estate"}
ROW = re.compile(r'\("(?P<path>[a-z-]+)", "text=(?P<marker>[^"]+)"\)')


def published_rows() -> dict[str, str]:
    body = DRILL.read_text()
    rows = {m.group("path"): m.group("marker") for m in ROW.finditer(body)}
    assert FIRST_PARTY <= set(rows), (
        f"drill PUBLISHED tuple no longer lists {sorted(FIRST_PARTY - set(rows))}; "
        "if a path was renamed or retired, retire it here too"
    )
    return rows


def source_files() -> list[pathlib.Path]:
    return [
        p
        for p in APP_SRC.rglob("*")
        if p.suffix in {".ts", ".tsx"} and ".test." not in p.name and p.is_file()
    ]


def test_every_first_party_marker_still_appears_in_the_pages_own_source() -> None:
    rows = published_rows()
    sources = source_files()
    assert sources, f"no portal source found under {APP_SRC}"
    for path in sorted(FIRST_PARTY):
        marker = rows[path]
        hits = [p for p in sources if marker in p.read_text()]
        assert hits, (
            f"the drill grades /{path} by the text {marker!r}, but no file under "
            f"{APP_SRC} says it any more. The page was reworded without moving the "
            "drill's marker (the #1191 mistake): update the tools row in "
            "bin/idp-login-drill in the same pull request as the wording change."
        )


def test_the_stale_marker_that_caused_the_incident_stays_dead() -> None:
    assert "Every tool we use" not in DRILL.read_text(), (
        "the drill grades a page by the pre-#1191 Tools sentence again; "
        "that text no longer exists on the page"
    )
