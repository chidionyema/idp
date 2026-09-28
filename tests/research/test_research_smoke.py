"""Smoke test that the research build imports cleanly (crew#396 step 3)."""

from __future__ import annotations

import contract  # noqa: F401
import db  # noqa: F401
import engine  # noqa: F401
import profiles  # noqa: F401
import scripts  # noqa: F401


def test_research_modules_import() -> None:
    """Each top-level research package can be imported without error."""
    assert contract.__name__ == "contract"
    assert db.__name__ == "db"
    assert engine.__name__ == "engine"
    assert profiles.__name__ == "profiles"
    assert scripts.__name__ == "scripts"
