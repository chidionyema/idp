"""An idle OCI Run Command queue is idle, not BLIND (idp#7387).

The OCI CLI prints nothing on stdout when `--query 'data[].id'` finds no command
(oci_cli/cli_util.py sends "Query returned empty result, no output to show." to stderr).
`require_idle_command_queue` fed that empty stdout to json.loads and raised
`BLIND ... Expecting value: line 1 column 1 (char 0)`, which refused every daily recovery
run (45465084919, 45670865333, 45870698471, 46042527394) before any script was submitted.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HELPER = REPO / "platform" / "oci" / "recovery" / "run-command.py"


def load(source: Path = HELPER):
    spec = importlib.util.spec_from_file_location("run_command_empty_queue", source)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def judge(module, stdout: str) -> str:
    """'idle', 'blocked' or 'blind' for a queue whose OCI list prints `stdout`."""
    module._oci = lambda args, *, what: stdout
    module.say = lambda *a, **k: None
    try:
        module.require_idle_command_queue("ocid1.compartment.x", "ocid1.instance.x")
    except module.TransportError as exc:
        return "blind" if str(exc).startswith("BLIND") else "blocked"
    return "idle"


def test_an_empty_stdout_is_an_idle_queue():
    assert judge(load(), "") == "idle"


def test_an_empty_json_list_is_an_idle_queue():
    assert judge(load(), "[]") == "idle"


def test_a_pending_command_still_blocks():
    assert judge(load(), '["ocid1.instanceagentcommand.x"]') == "blocked"


def test_garbage_is_still_blind_and_names_the_bytes():
    module = load()
    module._oci = lambda args, *, what: "<html>proxy error</html>"
    with pytest.raises(module.TransportError, match="raw stdout '<html>proxy error"):
        module.require_idle_command_queue("c", "i")


def test_falsifier_the_unguarded_parse_calls_an_idle_queue_blind(tmp_path):
    text = HELPER.read_text()
    fixed = "commands = json.loads(raw) if raw else []"
    assert fixed in text, "the empty-queue line moved; update the falsifier"
    old = tmp_path / "run-command.py"
    old.write_text(text.replace(fixed, "commands = json.loads(raw)"))
    assert judge(load(old), "") == "blind"


if __name__ == "__main__":
    if "--optimus" not in sys.argv:
        sys.exit(
            "usage: python3 tests/estate/test_run_command_empty_queue.py --optimus [--source PATH]"
        )
    src = (
        Path(sys.argv[sys.argv.index("--source") + 1])
        if "--source" in sys.argv
        else HELPER
    )
    print(
        f"optimus.recovery.idle_queue_judged_blind={int(judge(load(src), '') == 'blind')}"
    )
