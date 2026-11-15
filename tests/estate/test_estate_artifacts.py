"""Shape tests for the estate assurance plane scripts.

The live falsifiers (dispatch battery, sync benches, grade bench) run on the host; these tests keep
the repository copy honest in CI: every script is present, executable and compiles.
"""

import py_compile
from pathlib import Path

IDP = Path(__file__).resolve().parents[2]
FILES = [
    "bin/estate-dispatch-action",
    "bin/estate-bws-sync",
    "bin/estate-bws-check",
    "bin/estate-bws-adopt",
    "bin/estate-topology",
    "bin/estate-debug-pack",
    "bin/estate-service-grade",
    "bin/estate-itest",
    "bin/estate-metrics-push",
    "bin/estate-assurance-selftest",
    "bin/estate-certify",
]


def test_scripts_present_and_executable():
    for rel in FILES:
        p = IDP / rel
        assert p.is_file(), rel
        assert p.stat().st_mode & 0o111, rel


def test_scripts_compile(tmp_path):
    for rel in FILES:
        out = tmp_path / (Path(rel).name + ".pyc")
        py_compile.compile(str(IDP / rel), cfile=str(out), doraise=True)
