"""crew#679 CP2. Incident, 2026-08-30 02:5xZ to 03:3xZ: main went red three times in one hour
(idp#918, #921, #922) on `bin/incident-register --check`. Each branch had regenerated the register
against its own base; two green pull requests merged together left main's committed copy stale,
and every open pull request inherited the red. Fault class: ci-pipeline. Guard: the register is
written by a mkdocs hook at every docs build and git ignores it; the fast gate has no `--check`
rung, so there is no committed copy to be stale. Founder, 2026-08-30 on crew#679: incidents are
the input to the guards.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "bin" / "mkdocs_hooks" / "incident_register.py"


def _hook():
    import importlib.util

    path = ROOT / "bin" / "mkdocs_hooks" / "incident_register.py"
    spec = importlib.util.spec_from_file_location("incident_register_hook", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_mkdocs_runs_the_hook_and_the_file_is_never_tracked() -> None:
    cfg = yaml.safe_load((ROOT / "mkdocs.yml").read_text())
    assert "bin/mkdocs_hooks/incident_register.py" in cfg.get("hooks", []), (
        "mkdocs.yml does not run the hook"
    )
    assert HOOK.exists()
    tracked = subprocess.run(
        ["git", "ls-files", "docs/reference/incident-register.yaml"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert tracked == "", (
        "the register is committed again; it must be generated at docs build"
    )
    assert "docs/reference/incident-register.yaml" in (ROOT / ".gitignore").read_text()


def test_the_hook_writes_one_row_per_incident_test(tmp_path: Path) -> None:
    write_register = _hook().write_register

    out = write_register()
    body = yaml.safe_load(out.read_text())
    tests = sorted(
        p.stem.removeprefix("test_incident_")
        for p in (ROOT / "tests").glob("test_incident_*.py")
    )
    assert [r["id"] for r in body["rows"]] == tests
