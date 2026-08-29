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

import pytest

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


def test_brewfile_every_line_is_tap_brew_or_cask():
    lines = _brewfile_lines(BREWFILE.read_text())
    assert lines, "Brewfile has no content"
    for ln in lines:
        assert LINE_RE.match(ln), f"Brewfile line is not tap/brew/cask: {ln!r}"


def test_brewfile_has_exactly_the_one_expected_entry():
    """crew#562 (2026-08-29): the host side is Jump Desktop Connect and nothing else. Sunshine,
    DeskPad and the tailscale cask (the Mac runs the App Store Tailscale build, kb/1193) are
    the stitched version and must never come back into this file."""
    lines = _brewfile_lines(BREWFILE.read_text())
    assert lines == ['cask "jump-desktop-connect"']
    text = BREWFILE.read_text()
    for gone in ('"tailscale"', '"sunshine"', '"deskpad"', "LizardByte"):
        assert gone not in text, f"Brewfile brings back the stitched stack: {gone}"


def test_readme_has_run_once_section():
    text = README.read_text()
    assert "Run once (any session)" in text
    assert "brew bundle --file docs/founder/mac-remote-desk/Brewfile" in text


def test_readme_has_founder_one_sitting_section():
    """The founder's hands do only what a pipeline cannot: two privacy grants and a vendor
    sign-in. The stitched stack's steps (Sunshine admin password, PIN, Moonlight, Shortcut)
    must not be asked of him again."""
    text = README.read_text()
    assert "Founder, one sitting" in text
    for item in [
        "Privacy & Security",
        "Screen Recording",
        "Accessibility",
        "Remote Login",
        "sudo pmset -a disablesleep 0 sleep 0 womp 1",
        "Tailscale",
        "Jump Desktop Connect",
        "Add Remote Access User",
        "Sign in",
        "Single Virtual Display",
        "Match Display Resolution",
        "Keep After Disconnect",
    ]:
        assert item in text, f"README founder section missing {item!r}"
    section = text[text.index("## Founder, one sitting") : text.index("## Phase 5")]
    for gone in [
        "4-digit PIN",
        "Moonlight app",
        "Encoder =",
        "Target FPS",
        "Sunshine Web UI",
    ]:
        assert gone not in section, f"founder section still asks for {gone!r}"


def test_readme_names_the_risk_and_what_stays():
    text = README.read_text()
    assert "## The risk, in one sentence" in text
    assert "Teams Enterprise" in text
    assert "tag:k8s" in text and "22" in text, (
        "Otto's own road to the Mac must be named as independent of Jump"
    )


def test_readme_has_phase_5_acceptance_checklist():
    text = README.read_text()
    assert "Phase 5" in text
    for item in [
        "Cold Wake Test",
        "Aspect Ratio Check",
        "Network Portability",
        "Latency Verification",
        "Otto Parity",
    ]:
        assert item in text, f"README Phase 5 checklist missing {item!r}"


@pytest.mark.parametrize("path", [BREWFILE, README])
def test_no_machine_specific_literal_committed(path):
    text = path.read_text()
    for literal in FORBIDDEN_LITERALS:
        assert literal not in text, f"{path} carries forbidden literal {literal!r}"


def test_fixture_literal_is_actually_caught_by_the_check():
    """Proves the forbidden-literal check itself fails on a fixture that repeats the shape."""
    fixture = "host path is /Users/example/host\n"
    with pytest.raises(AssertionError):
        for literal in FORBIDDEN_LITERALS:
            assert literal not in fixture, (
                f"fixture carries forbidden literal {literal!r}"
            )
