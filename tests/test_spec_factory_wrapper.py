"""The spec-factory door discovers the tool or says BLIND; it never invents one."""

import os
import subprocess
import tempfile
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin"
INTENTS = Path(__file__).resolve().parent.parent / "platform" / "estate" / "intents"


def _run(args, extra_env=None):
    with tempfile.TemporaryDirectory() as d:
        home = Path(d) / "home"
        home.mkdir()
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("ESTATE_SPEC_FACTORY", "ESTATE_ARGON")
        }
        env["HOME"] = str(home)
        env.update(extra_env or {})
        return subprocess.run(
            [str(BIN / "spec-factory"), *args],
            env=env,
            capture_output=True,
            text=True,
        )


def test_missing_tool_is_blind_not_an_invented_spec():
    r = _run(["types"])
    assert r.returncode == 2
    assert "BLIND   spec-factory" in r.stderr
    assert "no Estate Spec Factory tool found" in r.stderr


def test_explicit_tool_path_is_executed_with_arguments():
    with tempfile.TemporaryDirectory() as d:
        tool = Path(d) / "spec_factory.py"
        tool.write_text("import sys\nprint('TOOL:' + ','.join(sys.argv[1:]))\n")
        r = _run(["types", "extra"], {"ESTATE_SPEC_FACTORY": str(tool)})
        assert r.returncode == 0
        assert "TOOL:types,extra" in r.stdout


def test_broken_explicit_path_is_blind():
    r = _run(["types"], {"ESTATE_SPEC_FACTORY": "/nonexistent/spec_factory.py"})
    assert r.returncode == 2
    assert "BLIND" in r.stderr


def test_the_three_spec_intents_are_real_and_read_only_or_mutate():
    names = {"spec.types", "spec.generate", "spec.validate"}
    found = {}
    for path in INTENTS.glob("spec.*.yaml"):
        text = path.read_text()
        assert "name: " in text and "steps:" in text
        assert "class: read" in text or "class: mutate" in text
        found[path.stem] = text
    assert names.issubset(found)
    assert "class: mutate" in found["spec.generate"]
    assert "class: read" in found["spec.types"]
    assert "class: read" in found["spec.validate"]
