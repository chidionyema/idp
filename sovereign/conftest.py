"""`sovereign/pytest.ini` makes this directory its own pytest root, so the repository's root
`conftest.py` (suite priority, and the git config that keeps the operator's hooks out of fixture
repositories, idp#786) is not loaded when only sovereign tests are collected. The pre-push hook
runs exactly that (2026-08-29 12:4xZ: `sovereign/tests/bdd/test_gate_spec_gate.py` and
`sovereign/tests/test_incident_r29_spec_gate.py` red on the Mac, green with the root loaded).
Run the root conftest here so every root has the same suite environment."""

import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parent.parent / "conftest.py"))
