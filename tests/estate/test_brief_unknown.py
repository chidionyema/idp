"""The brief says UNKNOWN with its cause, instead of returning nothing.

Measured 2026-11-28: `bin/estate-state-page` died with `TypeError: 'NoneType' object is not
iterable`, and `bin/estate-brief.state_section()` caught it and returned "". Every session in
every runtime then started with no estate state at all and nothing said why -- a failed
measurement served as "there is no state", which reads as healthy (AGENTS.md section 3, R1).

The session must still never be blocked, so the assertion is not "raise": it is "say UNKNOWN and
name the cause".
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import types

REPO = pathlib.Path(__file__).resolve().parents[2]


# 3. The consumer: a failed measurement says so, instead of returning nothing.
def _estate_brief():
    spec = importlib.util.spec_from_loader(
        "estate_brief_under_test",
        importlib.machinery.SourceFileLoader(
            "estate_brief_under_test", str(REPO / "bin" / "estate-brief")
        ),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_brief_says_unknown_when_the_page_cannot_be_measured(monkeypatch):
    brief = _estate_brief()
    broken = types.ModuleType("governance.state_page")

    def current(root=""):  # noqa: ARG001 - the stub's signature is the contract
        raise TypeError("'NoneType' object is not iterable")

    broken.current = current
    monkeypatch.setitem(sys.modules, "governance.state_page", broken)
    import governance

    # `state_section` does `from governance import state_page`, which reads the package
    # attribute rather than sys.modules, so the stub has to be installed in both places.
    monkeypatch.setattr(governance, "state_page", broken, raising=False)

    section = brief.state_section()
    assert section.strip(), (
        "a measurement failure was rendered as silence (fail-open, R1)"
    )
    assert "UNKNOWN" in section
    assert "TypeError" in section


def test_brief_returns_the_page_when_it_measures(monkeypatch):
    brief = _estate_brief()
    working = types.ModuleType("governance.state_page")
    working.current = lambda root="": (
        "# Estate state\n\nmeasured at 2026-11-28T00:00:00Z\n"
    )
    monkeypatch.setitem(sys.modules, "governance.state_page", working)
    import governance

    monkeypatch.setattr(governance, "state_page", working, raising=False)

    assert "Estate state" in brief.state_section()
