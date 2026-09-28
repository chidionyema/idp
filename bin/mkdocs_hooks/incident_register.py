"""mkdocs hook: write docs/reference/incident-register.yaml at every docs build (crew#679 CP2).

The register used to be committed and graded by `bin/incident-register --check` in the fast gate.
Two green pull requests that each added an incident test left main with a stale file three times
on 2026-08-30 (idp#918, #921, #922): each branch's file was right against its own base and wrong
against the other's. A generated file that is never committed cannot be stale, so the docs build
writes it and git ignores it. Wired in mkdocs.yml `hooks:`; the CI docs rung (`bin/idp-ci` 8c,
`mkdocs build --strict`) proves it.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "bin" / "incident-register"


def _generator():
    loader = importlib.machinery.SourceFileLoader("incident_register", str(TOOL))
    spec = importlib.util.spec_from_loader("incident_register", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def write_register() -> Path:
    gen = _generator()
    gen.OUT.parent.mkdir(parents=True, exist_ok=True)
    gen.OUT.write_text(gen.render(gen.rows()))
    return gen.OUT


def on_pre_build(config, **kwargs) -> None:  # noqa: ARG001 - mkdocs hook signature
    out = write_register()
    print(f"incident-register: wrote {out.relative_to(ROOT)}")
