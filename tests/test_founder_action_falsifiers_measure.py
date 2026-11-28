"""Falsifier for the optimus measure founder_action.falsifiers_declared.

A measure that cannot read 0 for an absent suite, or that counts a mention as a test, would
report a falsifier set that does not exist. Each case is a known-bad input it must score 0 and
a known-good it must score exactly.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tests" / "founder_action_falsifiers.py"
NAME = "founder_action.falsifiers_declared"

_spec = importlib.util.spec_from_file_location("founder_action_measure", SCRIPT)
measure = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(measure)


def _suite(tmp_path: pathlib.Path, body: str) -> pathlib.Path:
    path = tmp_path / "suite.py"
    path.write_text(body)
    return path


def test_absent_suite_reads_zero(tmp_path):
    assert measure.declared_falsifiers(tmp_path / "missing.py") == 0


def test_counts_real_definitions_only(tmp_path):
    suite = _suite(
        tmp_path,
        "def test_a():\n    pass\n\n"
        "def test_b(x):\n    pass\n\n"
        "def helper():\n    pass\n\n"
        "# def test_in_a_comment():\n"
        "s = 'def test_in_a_string():'\n"
        "    def test_nested():\n        pass\n",
    )
    assert measure.declared_falsifiers(suite) == 2


def test_empty_suite_reads_zero(tmp_path):
    assert measure.declared_falsifiers(_suite(tmp_path, "")) == 0


def test_script_prints_the_optimus_line():
    out = subprocess.run(
        [sys.executable, str(SCRIPT)], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out.startswith(f"optimus.{NAME}=")
    assert out.split("=", 1)[1].isdigit()


def test_registry_entry_runs_this_script():
    registry = json.loads((ROOT / "catalog" / "optimus-metrics.json").read_text())
    entry = next(m for m in registry["metrics"] if m["name"] == NAME)
    assert entry["measure"] == ["python3", "tests/founder_action_falsifiers.py"]
    assert entry["better"] == "higher"
