"""crew#66, 2026-08-29: the founder refused the paste prompt five times.

Root trust (R46, 2026-08-28): the founder never copies, pastes or types a secret. The 2026-08-28
design (30bd2bf0) opened real Chrome and read the generated pair off the console page; 00cc57d9
replaced it with `read -r -s`. This pins the page-reading road: no hidden prompt, a Chrome driver
that reads the vendor's two key formats, the pair proved by token exchange before the vault write.
"""

from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "idp-bootstrap-tailscale"


def _seed_block() -> str:
    text = SCRIPT.read_text()
    start = text.index('if [ "$MODE" = --seed ]; then')
    return text[start : text.index("\nfi\n", start)]


def test_the_seed_road_has_no_paste_prompt():
    assert "read -r -s" not in SCRIPT.read_text()
    assert "read -r -p" not in SCRIPT.read_text()


def test_the_seed_road_drives_real_chrome_on_the_estate_profile():
    block = _seed_block()
    assert 'channel="chrome"' in block, (
        "Google SSO refuses the bundled Chromium (idp#619)"
    )
    assert "launch_persistent_context" in block, (
        "the founder's SSO session must persist"
    )
    assert "tailscale-browser" in block


def test_the_pair_is_read_from_the_page_and_proved_before_the_vault():
    block = _seed_block()
    assert "tskey-client-" in block, (
        "the secret is read off the page by the vendor's format"
    )
    proved = block.index("token_for")
    written = block.index('vault_write "$SEED"')
    assert proved < written, "the pair is proved by token exchange before it is stored"
    assert "unset cid csec" in block
