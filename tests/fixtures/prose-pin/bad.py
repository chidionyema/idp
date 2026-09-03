# must-fail fixture for the R76 prose_pin_scan gate: every assert pins wording.
import pathlib


def test_the_comment_still_says_the_magic_sentence() -> None:
    text = pathlib.Path("some/config.yaml").read_text()
    assert "a new provider never means re-seeding every key" in text
    assert "GROQ" not in text
