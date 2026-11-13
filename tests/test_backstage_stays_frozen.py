"""The falsifier for the Backstage freeze (idp#8000).

A gate that cannot fail is not a gate (AGENTS.md section 9, law 1). So this test proves BOTH
halves of `bin/backstage-refused`:

  * it REFUSES Backstage, in every shape an install path actually names it;
  * it ACCEPTS everything that is not Backstage, because a guard that refuses correct work is an
    outage (section 12), and a door that says no to `npm i date-fns` would be worse than no door.

It also proves the local install the founder deleted is still absent, so "frozen" means frozen and
not "frozen until someone's bootstrap runs".
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DOOR = REPO / "bin" / "backstage-refused"
RECORD = REPO / "docs" / "decisions" / "2026-11-12-backstage-is-frozen-history.md"


def run_door(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    """Call the door the way an install path does: argv, plus optionally a piped script body."""
    return subprocess.run(  # noqa: S603 - fixed argv, the door under test
        [str(DOOR), *args],
        input=stdin if stdin is not None else "",
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_the_door_exists_and_is_executable():
    assert DOOR.is_file(), "bin/backstage-refused is the door this test grades; it is missing"
    assert os.access(DOOR, os.X_OK), "the door is not executable, so no install path can call it"


@pytest.mark.parametrize(
    "argv",
    [
        ("backstage",),
        ("install", "backstage"),
        ("npm", "install", "backstage"),
        ("yarn", "add", "@backstage/core-app-api"),
        ("git", "clone", "https://github.com/backstage/backstage"),
        ("npx", "@backstage/cli", "new"),
        ("/Users/x/.estate/frontend/idp/backstage",),
        ("https://backstage.io/docs/getting-started",),
    ],
)
def test_the_door_refuses_backstage(argv):
    """Every shape a real install path uses to name Backstage must be refused."""
    out = run_door(*argv)
    assert out.returncode != 0, (
        "the door ACCEPTED a Backstage fetch: " + " ".join(argv) + "\n"
        "It must refuse, or the 2.4 GB install the founder deleted comes back."
    )
    # A refusal that does not say why is a mystery, and mystery is how a lesson rots.
    assert "frozen history" in out.stderr.lower()
    assert RECORD.name in out.stderr, (
        "the refusal must name the decision record so the next agent can read the reason"
    )


def test_the_door_refuses_backstage_named_in_a_piped_install_script():
    """An install script often names its package in its body, not its argv."""
    script = "#!/usr/bin/env bash\nnpm install --prefix ./backstage @backstage/cli\n"
    out = run_door("bash", stdin=script)
    assert out.returncode != 0
    assert RECORD.name in out.stderr


@pytest.mark.parametrize(
    "argv",
    [
        (),  # nothing asked: nothing to refuse
        ("npm", "install", "date-fns"),
        ("npm", "ci"),
        ("yarn", "add", "@backstagexyz/not-a-thing"),  # a scoped org that merely starts alike
        ("git", "clone", "https://github.com/chidionyema/idp"),
        ("python3", "-m", "pytest", "tests/test_backstage_stays_frozen.py"),
        ("/Users/x/Documents/code/idp/platform/estate/libexec/aei-to-optimus.py",),
        # False refusals this test exists to catch. A bare word that merely CONTAINS or IS the
        # word outside an install shape is not a Backstage fetch, and blocking it is an outage.
        ("echo", "the backdrop is not the backstage"),
        ("echo", "backstage is frozen history"),
        ("grep", "-r", "backstage", "docs/"),
        ("/Users/x/Documents/code/idp/docs/decisions/2026-11-12-backstage-is-frozen-history.md",),
    ],
)
def test_the_door_accepts_everything_else(argv):
    """No false refusals. A door that blocks correct work is an outage, not a safeguard."""
    out = run_door(*argv)
    assert out.returncode == 0, (
        "the door refused work that does not involve Backstage: "
        + " ".join(argv)
        + "\nstderr:\n"
        + out.stderr
    )


def test_the_local_install_the_founder_deleted_is_still_absent():
    """The 2.4 GB install stays gone. This is the measurement, not the memory of one."""
    local = Path.home() / ".estate" / "frontend" / "idp" / "backstage"
    assert not local.exists(), (
        str(local)
        + " exists again. The founder deleted it on 2026-11-12 (2,419 MB, unused by Genesis). "
        "Removing it is not a suggestion -- see "
        + str(RECORD)
    )


def test_the_decision_record_is_present_and_carries_the_measurement():
    """The lesson survives as a record with its numbers, so it cannot rot into 'we just did not'."""
    assert RECORD.is_file(), "the frozen decision record is missing: the lesson would rot"
    body = RECORD.read_text()
    assert "2,419 MB" in body, "the record must carry the measured cost it was decided on"
    assert "value-tradeoff" in body, "the record must name its irreducible judgement (section 12)"
    assert "do not install a layer until a real caller" in body.lower(), (
        "the record must state the lesson it exists to teach"
    )
