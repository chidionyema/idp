"""Regression for IDP #7739: no caller-selected privileged one-shot Greenlane.

This covers the concrete legacy route. It is not a substitute for the broader
estate App/ruleset bypass audit tracked in #7739.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
INPUT_REF = re.compile(
    r"\bref:\s*['\"]?\$\{\{\s*(?:github\.event\.)?inputs\.[A-Za-z0-9_-]+"
)


def privileged_caller_selected_tick(text: str) -> bool:
    """Detect the exact trust-boundary class behind greenlane-land.yml."""
    return (
        "github-app-token" in text
        and "idp-greenlane tick" in text
        and bool(INPUT_REF.search(text))
    )


class PrivilegedSideDoorRegression(unittest.TestCase):
    def test_obsolete_greenlane_land_workflow_is_removed(self) -> None:
        path = WORKFLOWS / "greenlane-land.yml"
        self.assertFalse(
            path.exists(),
            "P0: obsolete workflow allows caller-selected code to run with the "
            "estate App credentials; use governed greenlane.yml instead",
        )

    def test_no_dispatch_selected_privileged_tick_in_any_workflow(self) -> None:
        offenders = []
        for path in sorted(WORKFLOWS.glob("*.y*ml")):
            if privileged_caller_selected_tick(path.read_text(encoding="utf-8")):
                offenders.append(path.name)
        self.assertEqual(
            offenders, [],
            "P0: privileged Greenlane tick from caller-selected ref: "
            + ", ".join(offenders),
        )

    def test_adversarial_fixture_is_rejected(self) -> None:
        vulnerable = """
on:
  workflow_dispatch:
    inputs:
      lane:
        type: string
jobs:
  land:
    steps:
      - uses: actions/checkout@v7
        with:
          ref: ${{ inputs.lane }}
      - uses: ./.github/actions/github-app-token
      - run: python3 bin/idp-greenlane tick
"""
        self.assertTrue(privileged_caller_selected_tick(vulnerable))
        self.assertFalse(
            privileged_caller_selected_tick(
                vulnerable.replace("ref: ${{ inputs.lane }}", "ref: main")
            )
        )


if __name__ == "__main__":
    unittest.main()
