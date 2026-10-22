"""The Claude Code compact window and the router's input ceiling are ONE decision.

2026-10-22: CLAUDE_CODE_AUTO_COMPACT_WINDOW was set to 100000 in ~/.estate/harness/cc/settings.json
(and the launcher ceiling to 128000 to match) with no measurement of what a session's fixed prompt
costs. Claude Code then compacted on every turn ("autocompact is thrashing: the context refilled to
the limit within 3 turns of the previous compact") in every session on the laptop. The window was
put back to 200000, the value that had run before.

Two failures are possible and this pins both:
  * window above the ceiling: the router refuses a long session before its own compaction fires;
  * window at or below the value measured to thrash: every turn compacts.

The window lives outside the repo (the estate harness), so the live check skips where that file is
absent (CI). The invariant itself is a pure function with its own tests, which run everywhere and
fail on both bad pairs.
"""

import json
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
LAUNCHER = REPO / "bin" / "litellm-local"
HARNESS_SETTINGS = pathlib.Path.home() / ".estate" / "harness" / "cc" / "settings.json"

# Measured 2026-10-22: a 100000 window thrashed (compaction every turn). Anything at or under it is
# a value already known to fail.
THRASH_WINDOW = 100_000

_CEILING_LINE = re.compile(
    r'export ESTATE_MAX_INPUT_TOKENS="\$\{ESTATE_MAX_INPUT_TOKENS:-(\d+)\}"'
)


def launcher_ceiling(text):
    """The default ceiling the launcher exports, or None when the line is not there."""
    m = _CEILING_LINE.search(text)
    return int(m.group(1)) if m else None


def window_problem(window, ceiling):
    """Why this (window, ceiling) pair is wrong, or None when it is not."""
    if window <= THRASH_WINDOW:
        return f"window {window:,} is at or under {THRASH_WINDOW:,}, the value measured to thrash"
    if window > ceiling:
        return f"window {window:,} is above ceiling {ceiling:,}: a long session is refused before it compacts"
    return None


def test_the_thrashing_window_is_rejected():
    assert window_problem(100_000, 128_000)
    assert window_problem(80_000, 200_000)


def test_a_window_above_the_ceiling_is_rejected():
    assert window_problem(200_000, 128_000)


def test_the_pair_that_ran_before_the_incident_passes():
    assert window_problem(200_000, 200_000) is None


def test_the_launcher_line_is_parseable_today():
    assert launcher_ceiling(LAUNCHER.read_text()) is not None, (
        "bin/litellm-local no longer exports ESTATE_MAX_INPUT_TOKENS in the expected form; "
        "this gate cannot read the ceiling"
    )


def test_the_live_window_fits_the_launcher_ceiling():
    if not HARNESS_SETTINGS.exists():
        pytest.skip(f"{HARNESS_SETTINGS} absent: the window is not on this machine")
    window = int(
        json.loads(HARNESS_SETTINGS.read_text())["env"][
            "CLAUDE_CODE_AUTO_COMPACT_WINDOW"
        ]
    )
    ceiling = launcher_ceiling(LAUNCHER.read_text())
    problem = window_problem(window, ceiling)
    assert problem is None, (
        f"{problem} (settings.json window={window:,}, launcher ceiling={ceiling:,})"
    )
