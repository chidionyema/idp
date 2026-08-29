"""Incident: login-drill run 33251546897 (crew#459, 2026-08-29).

The new front page answered 200 and drew nothing. The drill's whole verdict was
"no nav in the page": it had collected every uncaught JavaScript error and printed
none, and its screenshot step sat after the fail. The fix makes the blank-page
branch print the errors, the page's own words, and the screenshot. This pins it.
"""

import pathlib
import re

DRILL = pathlib.Path(__file__).resolve().parents[1] / "bin" / "idp-login-drill"


def _blank_page_branch() -> str:
    text = DRILL.read_text()
    m = re.search(
        r"except PWError:\n(.*?no Backstage shell rendered.*?)\n\n", text, re.S
    )
    assert m, "the blank-page failure branch is gone from bin/idp-login-drill"
    return m.group(1)


def test_the_blank_page_verdict_carries_the_javascript_errors():
    branch = _blank_page_branch()
    assert "page_errors" in branch, (
        "run 33251546897: a blank page must name its uncaught errors"
    )
    assert "page errors:" in branch


def test_the_blank_page_verdict_carries_the_pages_own_words():
    branch = _blank_page_branch()
    assert "inner_text" in branch, (
        "run 33251546897: a blank page must quote what it did draw"
    )
    assert "(empty body)" in branch


def test_the_blank_page_is_photographed_before_the_fail():
    branch = _blank_page_branch()
    assert "page.screenshot" in branch and "DRILL_SHOT" in branch
