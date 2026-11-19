"""A declaration kept as `<label>.plist.tmpl` must grade MANAGED, not ORPHAN.

Measured 2026-11-19: `bin/idp-inventory --plane mac` graded MANAGED 5 / ORPHAN 72
while `launchd/` in this repo tracks the same labels as `.plist.tmpl`. The match
was the literal `<label>.plist`, so a declared job was reported unowned.
"""

import importlib.util
import importlib.machinery
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-inventory"


def load_module():
    loader = importlib.machinery.SourceFileLoader("idp_inventory", str(SCRIPT))
    spec = importlib.util.spec_from_loader("idp_inventory", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


LAUNCHCTL = (
    "PID\tStatus\tLabel\n"
    "-\t0\tai.estate.declared-by-template\n"
    "-\t0\tai.estate.never-declared\n"
)


def fake_run(cmd, timeout=180, env=None, stdin=None):
    if cmd[:2] == ["launchctl", "list"]:
        return 0, LAUNCHCTL, ""
    return 0, "", ""


def test_template_declaration_is_managed(monkeypatch):
    mod = load_module()
    monkeypatch.setattr(mod.sys, "platform", "darwin")
    monkeypatch.setattr(mod, "run", fake_run)
    monkeypatch.setattr(
        mod, "tracked_files", lambda: {"ai.estate.declared-by-template.plist.tmpl"}
    )

    verdicts = {r["id"]: r["verdict"] for r in mod.plane_mac([])}
    assert verdicts["ai.estate.declared-by-template"] == "MANAGED"
    assert verdicts["ai.estate.never-declared"] == "ORPHAN"
