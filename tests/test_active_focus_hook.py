"""Falsifiers for the active-focus-memory pi extension.

The extension injects the estate's Active Focus register into a session's context once. It lives
in the repo because it must be reviewable and testable; it is *installed* in
``~/.pi/agent/extensions/active-focus-memory/index.ts``. Two copies is exactly how a layer drifts
(AGENTS.md section 6), so the first test proves the two are byte-identical and a change to one
without the other fails here.

The remaining tests assert the properties the extension's own docstring claims, against the
shipped source -- never against the prose:

* the budget is longer than the measured engine cost (a budget shorter than the real cost is a
  silent failure: an earlier 2500 ms budget against a 3.9 s render injected nothing, quietly);
* a failed render yields a missing header, never a refused session (R6: the recovery path must
  not depend on what it recovers);
* the header is inserted at most once per session, guarded by a marker that is checked against
  the live message list rather than a module-level flag.
"""

import hashlib
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / "extensions" / "active-focus-memory" / "index.ts"


def _installed() -> Path:
    return (
        Path.home()
        / ".pi"
        / "agent"
        / "extensions"
        / "active-focus-memory"
        / "index.ts"
    )


def test_the_repo_copy_is_the_file_that_is_installed() -> None:
    """The repo copy is the source of record; the installed copy must be the same bytes."""
    assert HOOK.is_file(), f"the extension is missing from the repo: {HOOK}"
    installed = _installed()
    if not installed.is_file():
        pytest.skip("the extension is not installed in this environment")
    repo_sha = hashlib.sha256(HOOK.read_bytes()).hexdigest()
    installed_sha = hashlib.sha256(installed.read_bytes()).hexdigest()
    assert repo_sha == installed_sha, (
        "the installed pi extension differs from the repo copy: one of them was edited alone"
    )


def test_the_budget_is_longer_than_the_engine_costs() -> None:
    """A hook timeout shorter than the real cost is a silent failure, not a safety margin."""
    src = HOOK.read_text()
    match = re.search(r"ENGINE_TIMEOUT_MS\s*=\s*(\d+)", src)
    assert match, "the extension no longer declares a timeout budget"
    budget_ms = int(match.group(1))
    documented = re.search(r"Measured cost is ~([\d.]+)\s*s", src)
    assert documented, (
        "the measured engine cost is no longer documented next to the budget"
    )
    measured_ms = float(documented.group(1)) * 1000
    assert budget_ms >= measured_ms * 2, (
        f"budget {budget_ms} ms is not at least 2x the measured {measured_ms:.0f} ms -- "
        "on a loaded machine the header would silently not be injected"
    )


def test_a_failed_render_is_never_a_failed_session() -> None:
    """R6: the recovery path must not depend on what it recovers."""
    src = HOOK.read_text()
    render = src.split("function renderFocus", 1)
    assert len(render) == 2, "renderFocus is gone from the extension"
    body = render[1].split("\n}", 1)[0]
    assert "catch" in body, (
        "renderFocus no longer catches: a failed compile would throw"
    )
    assert re.search(r"catch\s*\{[\s\S]*?return null", body), (
        "renderFocus does not return null on failure -- it would throw at session start"
    )


def test_the_header_is_inserted_once_guarded_by_a_live_marker() -> None:
    """Inserting unconditionally would stack N copies and spend the budget the register protects."""
    src = HOOK.read_text()
    assert "alreadyPresent(" in src, (
        "the extension no longer guards against duplicate headers"
    )
    assert "event.messages" in src, (
        "the marker is not checked against the live message list: after a compaction the "
        "header would not come back"
    )
    assert "MARKER" in src


def test_the_engine_it_calls_is_in_the_repo_and_serves_the_verb() -> None:
    """The hook is only worth anything if the door behind it answers."""
    engine = REPO / "bin" / "estate-memory-engine"
    assert engine.is_file(), "bin/estate-memory-engine is not in the repo"
    src = engine.read_text()
    assert "render-focus" in src, "the engine no longer serves the verb the hook calls"
