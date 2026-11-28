"""Falsifier for the optimus measure gemini_outbox.verifier_falsifiers_declared (claim idp#8702).

A measure that cannot read 0 for an absent crate, or that counts a mention as a test, would
report a falsifier set that does not exist. Each case here is a known-bad input it must score 0
and a known-good it must score exactly.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tests" / "gemini_outbox_verifier_falsifiers.py"
NAME = "gemini_outbox.verifier_falsifiers_declared"

_spec = importlib.util.spec_from_file_location("gemini_outbox_measure", SCRIPT)
measure = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(measure)


def _crate(tmp_path: pathlib.Path, files: dict) -> pathlib.Path:
    for rel, body in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    return tmp_path


def test_absent_crate_reads_zero(tmp_path):
    assert measure.declared_falsifiers(tmp_path / "missing") == 0


def test_counts_real_attributes_in_src_and_tests(tmp_path):
    crate = _crate(
        tmp_path,
        {
            "src/main.rs": "#[cfg(test)]\nmod t {\n    #[test]\n    fn a() {}\n    #[test]\n    fn b() {}\n}\n",
            "tests/more.rs": "#[test]\nfn c() {}\n",
        },
    )
    assert measure.declared_falsifiers(crate) == 3


def test_mentions_in_comments_and_strings_do_not_count(tmp_path):
    crate = _crate(
        tmp_path,
        {
            "src/lib.rs": '// #[test]\nlet s = "#[test]";\n/* #[test] */\n#[cfg(test)]\nmod t {}\n'
        },
    )
    assert measure.declared_falsifiers(crate) == 0


def test_output_line_is_the_exact_optimus_format():
    proc = subprocess.run(
        [sys.executable, "-I", str(SCRIPT)], capture_output=True, text=True, cwd=ROOT
    )
    assert proc.returncode == 0
    line = proc.stdout.strip()
    assert line.startswith(f"optimus.{NAME}=")
    assert int(line.split("=", 1)[1]) >= 0


def test_registered_with_the_argv_the_greenlane_will_run():
    reg = json.loads((ROOT / "catalog" / "optimus-metrics.json").read_text())
    entry = next(m for m in reg["metrics"] if m["name"] == NAME)
    assert entry["measure"] == ["python3", "tests/gemini_outbox_verifier_falsifiers.py"]
    assert (ROOT / entry["measure"][1]).is_file()
    assert entry["better"] == "higher"
