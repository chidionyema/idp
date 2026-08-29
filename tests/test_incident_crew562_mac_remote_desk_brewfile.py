"""crew#562 CP1: the founder's iPhone-to-Mac remote desk spec (Tailscale + Sunshine + DeskPad +
Moonlight) landed as a `Brewfile` and a checklist README, not a script (LAW 43 — brew bundle is
the mature tool for package provisioning; nothing here wraps it).

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


def test_brewfile_has_exactly_the_three_expected_entries():
    """crew#561: the Mac runs the App Store Tailscale build (measured 2026-08-29, kb/1193 applies
    to it). `cask "tailscale"` is the standalone build; installing it beside the App Store one is
    two clients fighting for one tunnel, so the Brewfile never names it."""
    lines = _brewfile_lines(BREWFILE.read_text())
    assert lines == [
        'tap "LizardByte/homebrew"',
        'brew "sunshine"',
        'cask "deskpad"',
    ]
    assert 'cask "tailscale"' not in BREWFILE.read_text()


def test_brewfile_fixture_with_bad_line_fails_the_line_check():
    """Proves the regex actually rejects a malformed entry, not just accepts the real file."""
    bad_lines = _brewfile_lines(
        'tap "LizardByte/homebrew"\n'
        "sh install.sh\n"  # not tap/brew/cask -> must fail
    )
    with pytest.raises(AssertionError):
        for ln in bad_lines:
            assert LINE_RE.match(ln), f"Brewfile line is not tap/brew/cask: {ln!r}"


def test_readme_has_run_once_section():
    text = README.read_text()
    assert "Run once (any session)" in text
    assert "brew bundle --file docs/founder/mac-remote-desk/Brewfile" in text


def test_readme_has_founder_one_sitting_section():
    text = README.read_text()
    assert "Founder, one sitting" in text
    for item in [
        "Privacy & Security",
        "Remote Login",
        "sudo pmset -a disablesleep 0 sleep 0 womp 1",
        "Tailscale",
        "SSO",
        "Sunshine",
        "admin",
        "FPS",
        "Encoder",
        "Moonlight",
        "PIN",
        "iOS Shortcut",
    ]:
        assert item in text, f"README founder section missing {item!r}"


def test_readme_has_phase_5_acceptance_checklist():
    text = README.read_text()
    assert "Phase 5" in text
    for item in [
        "Cold Wake Test",
        "Aspect Ratio Check",
        "Network Portability",
        "Latency Verification",
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
            assert literal not in fixture, f"fixture carries forbidden literal {literal!r}"
