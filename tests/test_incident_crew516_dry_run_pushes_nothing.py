"""crew#516 CP3 (2026-08-27): `bin/catalog-render --dry-run` is meant to touch nothing on origin,
but `main()` called `bin/idp-catalog-push` unconditionally before the diff check, so dry-run
33106556071 pushed `ghcr.io/chidionyema/idp/estate-catalog:latest`. The push must sit behind an
`if not dry:` guard so a dry-run prints the named skip line and does not call the push at all;
the usage line promises "touch nothing on origin" and that contract is what the guard upholds.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RENDER = ROOT / "bin" / "catalog-render"
SKIP_LINE = "skip  catalog-render: catalogue push skipped in --dry-run (crew#516 CP3)"


def test_incident_crew516_dry_run_skips_the_catalogue_push():
    text = RENDER.read_text()
    assert re.search(r"if\s+not\s+dry\s*:\s*\n[^\n]*idp-catalog-push", text), (
        "idp-catalog-push must sit inside an `if not dry:` guard; dry-run 33106556071 pushed the artifact"
    )
    assert SKIP_LINE in text, "dry-run must print the named skip line, not be silent"


def test_incident_crew516_dry_run_usage_still_promises_to_touch_nothing():
    text = RENDER.read_text()
    assert "touch nothing on origin" in text, "the usage line is the contract a dry-run breaks"