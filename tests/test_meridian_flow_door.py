"""bin/meridian-flow is the door that makes the engine's decision reachable and logged.

The wrapper is tested against a stub cargo so the test needs no build: it proves the door refuses an
empty task, passes a decision line through, appends it to the durable log, and refuses an engine
that prints nothing. The engine's own decisions are proved by tests/test_meridian_estate_engine.py.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOOR = ROOT / "platform" / "estate" / "libexec" / "meridian-flow.py"
INTENT = ROOT / "platform" / "estate" / "intents" / "flow-decide.yaml"


def _run(
    tmp: Path, stub_body: str, *args: str, index_body: str | None = None
) -> subprocess.CompletedProcess:
    stub = tmp / "cargo"
    stub.write_text("#!/bin/sh\n" + stub_body)
    stub.chmod(0o755)
    index = tmp / "capability-index"
    index.write_text(
        index_body if index_body is not None else "import sys\nsys.exit(3)\n"
    )
    env = {
        **os.environ,
        "HOME": str(tmp),
        "CARGO": str(stub),
        "ESTATE_CAPABILITY_INDEX": str(index),
    }
    return subprocess.run(
        [sys.executable, str(DOOR), *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_empty_task_is_refused(tmp_path: Path) -> None:
    done = _run(tmp_path, "exit 0\n")
    assert done.returncode == 2
    assert json.loads(done.stdout)["event"] == "meridian.flow.refused"


def test_decision_is_printed_and_appended_to_the_log(tmp_path: Path) -> None:
    line = '{"event":"meridian.flow.decision","decision":"IMPLEMENT_NEW","capability":null}'
    done = _run(tmp_path, f"echo '{line}'\n", "something", "new")
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["decision"] == "IMPLEMENT_NEW"
    logged = (tmp_path / ".estate/results/flow-decide.jsonl").read_text().splitlines()
    assert len(logged) == 1 and json.loads(logged[0])["at"] > 0


def test_silent_engine_is_refused_not_passed(tmp_path: Path) -> None:
    done = _run(tmp_path, "exit 0\n", "agent invoke")
    assert done.returncode == 2
    assert "meridian.flow.refused" in done.stdout


def test_engine_crash_is_refused(tmp_path: Path) -> None:
    done = _run(tmp_path, "echo boom >&2; exit 101\n", "agent invoke")
    assert done.returncode == 2 and "101" in done.stdout


def test_engine_that_overruns_its_bound_is_refused_with_the_prebuild_command(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("ESTATE_FLOW_ENGINE_TIMEOUT", "1")
    done = _run(tmp_path, "exec sleep 5\n", "agent invoke")
    assert done.returncode == 2
    assert "meridian.flow.refused" in done.stdout
    assert "cargo build --locked -p meridian-army" in done.stdout


def test_declared_door_fits_the_estate_ceiling_and_the_bounds_inside_it() -> None:
    intent = yaml.safe_load(INTENT.read_text())
    assert intent["door_s"] <= 100
    src = DOOR.read_text()
    live = int(src.split('"ESTATE_FLOW_LIVE_TIMEOUT", "')[1].split('"')[0])
    engine = int(src.split('"ESTATE_FLOW_ENGINE_TIMEOUT", "')[1].split('"')[0])
    assert live + engine < intent["door_s"]


def test_intent_is_read_only_and_names_the_door() -> None:
    intent = yaml.safe_load(INTENT.read_text())
    assert intent["class"] == "read"
    assert "libexec/meridian-flow.py" in intent["steps"][0]["cmd"]


# --- the source of the registry: the live store, never the frozen snapshot, never silently ---------

COUNTING_CARGO = """exec python3 -c '
import json, sys
a = sys.argv
rows = json.load(open(a[a.index("--registry") + 1]))["records"]
n = sum(1 for r in rows if r["health"]["state"] == "operating")
print(json.dumps({"event": "meridian.flow.decision", "decision": "X", "registry_operating": n}))
' "$@"
"""


def _rows(*states: str, tombstoned: bool = False) -> str:
    rows = [
        {
            "id": f"cap:intent/thing{i}",
            "path": "p",
            "tombstoned": tombstoned,
            "health": {"state": s},
        }
        for i, s in enumerate(states)
    ]
    return "import json\nprint(json.dumps(%r))\n" % rows


def test_live_store_is_what_the_engine_reads(tmp_path: Path) -> None:
    done = _run(
        tmp_path,
        COUNTING_CARGO,
        "thing",
        index_body=_rows("operating", "declared", "operating"),
    )
    assert done.returncode == 0, done.stderr
    out = json.loads(done.stdout)
    assert out["registry_source"] == "live" and out["registry_operating"] == 2
    assert "live_error" not in out


def test_tombstoned_records_are_not_offered(tmp_path: Path) -> None:
    stub = 'echo \'{"event":"meridian.flow.decision"}\'\n'
    done = _run(tmp_path, stub, "thing", index_body=_rows("operating", tombstoned=True))
    assert done.returncode == 0, done.stdout + done.stderr
    out = json.loads(done.stdout)
    assert out["registry_source"] == "snapshot" and "tombstoned" in out["live_error"]


def test_failed_live_read_falls_back_loudly_and_is_labelled(tmp_path: Path) -> None:
    line = '{"event":"meridian.flow.decision","decision":"DECLARED_NOT_VERIFIED"}'
    done = _run(tmp_path, f"echo '{line}'\n", "thing")  # default stub index exits 3
    assert done.returncode == 0
    out = json.loads(done.stdout)
    assert out["registry_source"] == "snapshot" and "no records" in out["live_error"]
    assert "falling back to the committed snapshot" in done.stderr
