"""The estate's last gate before main needs pytest's fixture map, and pytest 9.2 took it.

WHY THIS EXISTS, in one paragraph. On 2026-10-27 at 21:30Z PyPI published pytest 9.2.0. That
release removed the private `FixtureManager._arg2fixturedefs` which pytest-bdd has read since
8.x (`pytest_bdd/scenario.py`, `find_fixturedefs_for_step`). The estate installs pytest from
an open upper bound, so every CI run after that minute resolved to 9.2.0 and every scenario
in `sovereign/tests/bdd` died during collection with

    AttributeError: 'FixtureManager' object has no attribute '_arg2fixturedefs'

Measured 2026-10-28 on greenlane run 40621180043, job 122595594796 (the acceptance leg):
"85 failed, 104 passed, 1 xfailed" -- on a candidate whose only change was an image tag.
The `bdd` gate was therefore red for EVERY candidate in the estate, and nothing could reach
main through the Greenlane until the pin in `sovereign/requirements-dev.txt` landed.

Two guards, because a pin in a requirements file is otherwise just a comment:

1. the environment: the pytest running THIS test still hands pytest-bdd the map it reads.
   If a later pytest removes it again, the guard that protects the gate is the gate.
2. the pin: `sovereign/requirements-dev.txt` still excludes the release that removed it.
   Relaxing the pin then has to change this test on purpose, not a requirements file quietly.
"""

from __future__ import annotations

import re
from pathlib import Path

from packaging.requirements import Requirement

REQUIREMENTS = Path(__file__).resolve().parents[2] / "requirements-dev.txt"

# The release that removed `FixtureManager._arg2fixturedefs`. Every version at or above it
# fails every scenario in this suite with the AttributeError named in the module docstring.
REMOVED_IN = "9.2.0"

# A version the suite is known to pass on: pytest 8.4.2, and 9.1.x before the removal.
KNOWN_GOOD = "8.4.2"


def _pytest_requirement() -> Requirement:
    """The pytest requirement as written in `sovereign/requirements-dev.txt`."""
    for line in REQUIREMENTS.read_text().splitlines():
        stripped = line.strip()
        # `pytest-bdd` and `pytest-xdist` are different packages; only the bare name is pytest.
        if re.match(r"^pytest\s*[<>=!~]", stripped):
            return Requirement(stripped)
    raise AssertionError(
        f"no pytest requirement in {REQUIREMENTS}; the suite's runner is not pinned at all"
    )


def test_the_pytest_running_this_suite_still_gives_pytest_bdd_the_fixture_map(request):
    """pytest-bdd reads `FixtureManager._arg2fixturedefs`; pytest 9.2.0 removed it."""
    fixture_manager = request.session._fixturemanager
    assert hasattr(fixture_manager, "_arg2fixturedefs"), (
        "pytest no longer gives pytest-bdd the fixture map it reads "
        "(pytest_bdd/scenario.py), so every scenario in this suite fails with "
        "AttributeError. pytest "
        f"{REMOVED_IN} was the first release to remove it; "
        "sovereign/requirements-dev.txt pins pytest below it."
    )


def test_the_requirements_still_pin_pytest_below_the_release_that_removed_the_map():
    """The pin is the fix; a test is what keeps it from being quietly relaxed."""
    requirement = _pytest_requirement()
    assert not requirement.specifier.contains(REMOVED_IN), (
        f"{requirement} admits pytest {REMOVED_IN}, which removed "
        "FixtureManager._arg2fixturedefs and reds every scenario in this suite"
    )
    assert requirement.specifier.contains(KNOWN_GOOD), (
        f"{requirement} excludes pytest {KNOWN_GOOD}, which the suite passes on; "
        "the pin is tighter than it needs to be"
    )
