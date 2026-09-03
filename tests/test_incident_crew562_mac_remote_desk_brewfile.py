"""crew#562: the founder's iPhone-to-Mac remote desk is Jump Desktop (Fluid) — one bought
product replacing the Sunshine + DeskPad + Moonlight + Shortcut stitch (founder 2026-08-29:
"a much better experience ... heavenly setup"; THE HEADLINE, LAW 43). It lands as a `Brewfile`
and a checklist README, not a script (brew bundle is the mature tool for package provisioning).

Rule: the Brewfile parses as tap/brew/cask lines only, and the README carries the two required
sections plus the Phase 5 acceptance checklist, with no machine-specific literal (a home
directory path or a Tailscale CGNAT IP) ever committed (LAW 46, LAW 21). Proved both ways: the
files as shipped pass; a fixture Brewfile line or a README line carrying `/Users/` or a `100.`
prefix must fail here.

No network, no `brew` invocation — this only reads the two files this incident put in git."""

import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parents[1]
DOC_DIR = ROOT / "docs" / "founder" / "mac-remote-desk"
BREWFILE = DOC_DIR / "Brewfile"
README = DOC_DIR / "README.md"

LINE_RE = re.compile(r'^(tap|brew|cask)\s+"[^"]+"\s*$')

FORBIDDEN_LITERALS = ["/Users/", "100."]


def _brewfile_lines(text):
    return [ln for ln in text.splitlines() if ln.strip()]


def test_brewfile_exists():
    assert BREWFILE.exists(), f"missing {BREWFILE}"


def test_readme_exists():
    assert README.exists(), f"missing {README}"


def test_brewfile_has_exactly_the_one_expected_entry():
    """crew#562 (2026-08-29): the host side is Jump Desktop Connect and nothing else. Sunshine,
    DeskPad and the tailscale cask (the Mac runs the App Store Tailscale build, kb/1193) are
    the stitched version and must never come back into this file."""
    lines = _brewfile_lines(BREWFILE.read_text())
    assert lines == ['cask "jump-desktop-connect"']
    text = BREWFILE.read_text()
    for gone in ('"tailscale"', '"sunshine"', '"deskpad"', "LizardByte"):
        assert gone not in text, f"Brewfile brings back the stitched stack: {gone}"
