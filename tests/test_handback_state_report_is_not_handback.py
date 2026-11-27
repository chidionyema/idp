"""A state report on a tracked object is not a hand-back (idp#8622).

AGENTS.md section 2: "Open the PR, then STOP ... merge-when-green lands it." The Stop hook's
hand-back judge (platform/estate/memory/handback.py) refused any `still open` in prose, so the
report section 2 requires -- "PR #8618 is still open; Greenlane owns it" -- was refused as handing
work back, and a status-table cell reading "still open" trapped the session in a retry. A line that
names what holds the work (an issue or PR number, a pull/issues URL, a lane branch) is state; an
unreferenced "still open" and a "Still open:" list are still hand-backs.

    python3 tests/test_handback_state_report_is_not_handback.py --optimus
        -> optimus.handback.state_reports_refused=<n>   (main: 4, the fix: 0)
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "platform", "estate", "memory"))
import handback  # noqa: E402

STATE_REPORTS = (
    "Opened PR #8618. It is still open; Greenlane owns it from here.",
    "| #8611 | headless lane | PR #8618 still open, lane adopts it |",
    "https://github.com/chidionyema/idp/pull/8621 is still open and queued behind the dispatch run.",
    "The lane lane/fix/catalog-keyed-merge is still open until it is green on main.",
)

HANDBACKS = (
    "Landed the hook. The router wiring is still open.",
    "Landed the hook.\n\nStill open:\n- wire the router",
    "Still open: #8618 -- want me to merge it?",
    "Merged #8604. Still-open work: the router, which you will need to wire.",
)


def refused(text: str) -> bool:
    return handback.judge(text)["block"]


def test_a_state_report_on_a_tracked_object_is_allowed():
    for text in STATE_REPORTS:
        assert not refused(text), text


def test_an_unreferenced_still_open_is_still_a_handback():
    for text in HANDBACKS:
        assert refused(text), text


def test_a_reference_on_another_line_does_not_excuse_it():
    assert refused("Merged #8604.\nThe router wiring is still open.")


def test_a_small_number_is_not_a_reference():
    assert refused("Item #2 is still open.")


if __name__ == "__main__":
    if "--optimus" in sys.argv:
        print(
            f"optimus.handback.state_reports_refused={sum(map(refused, STATE_REPORTS))}"
        )
        raise SystemExit(0)
    raise SystemExit("run under pytest, or with --optimus")
