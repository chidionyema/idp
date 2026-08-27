"""crew#85, 2026-08-27 05:02Z: idp#316 merged and the Dagster daemon on the Mac died on
`ModuleNotFoundError: No module named 'load_gate'`. The daemon loads definitions.py with
`-f definitions.py -d scheduler/`, so the module is a bare file: the relative import fails
and `scheduler/` (not `scheduler/estate_scheduler/`) is on sys.path. Rule: definitions.py
loads the way the daemon loads it. Rung 4, incident test; the package import is the
must-pass control the old test already covers."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_definitions_loads_as_a_bare_file_the_way_dagster_daemon_loads_it(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scheduler"))
    for name in ("load_gate", "describe", "definitions"):
        sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(
        "definitions", ROOT / "scheduler/estate_scheduler/definitions.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.defs.jobs
