"""Reuse the real suite's pending hooks here, so this fixture directory is
judged by the same rule the suite is and not by a copy of it."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sovereign.tests.bdd.conftest import (  # noqa: E402,F401
    pytest_collection_modifyitems,
    pytest_configure,
    pytest_runtest_setup,
    pytest_terminal_summary,
)
