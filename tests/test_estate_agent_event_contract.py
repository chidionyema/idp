"""MUM-287 / MUM-286: the estate.agent.event contract is one schema, refused both ways.

docs/specs/2026-09-08-fleetview-live-mind-steering-and-the-board-view.md ("one subject family,
one schema"): every runtime's session record must emit a row this schema accepts, and an adapter
that emits a row the schema refuses fails CI. This test grades that contract the way an adapter
would be graded -- through check-jsonschema (or the jsonschema lib if the CLI is absent) over
real rows -- so the typed agreement CP6 names is enforced, not just documented.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "platform" / "event-bus" / "contract" / "estate.agent.event.json"
CLI = shutil.which("check-jsonschema")


def load() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def validate(row: dict) -> tuple[bool, str]:
    if not CLI:
        raise RuntimeError(
            "check-jsonschema is required to grade the estate agent contract"
        )
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(row, fh)
        path = fh.name
    try:
        p = subprocess.run(
            [CLI, "--schemafile", str(SCHEMA), str(path)],
            capture_output=True,
            text=True,
        )
        return p.returncode == 0, (p.stdout + p.stderr).strip()[-200:]
    finally:
        try:
            Path(path).unlink()
        except OSError:
            pass


def test_the_schemas_own_examples_validate():
    """Every example the schema ships is a row a conforming adapter may emit."""
    schema = load()
    assert schema.get("additionalProperties") is False
    assert len(schema.get("examples", [])) >= 2
    for example in schema["examples"]:
        ok, err = validate(example)
        assert ok, f"schema example refused by its own contract: {err}"


def test_a_row_the_contract_does_not_know_is_refused():
    """additionalProperties:false -- a field the adapter invented is not silently dropped; the
    adapter fails CI (the estate's doctrine, CP6)."""
    ok, _ = validate(
        {
            "session_id": "s-1",
            "runtime": "claude-code",
            "kind": "tool",
            "at": "2026-09-09T21:40:00Z",
            "phase": "executing",
            "tool": {"name": "read", "target": "auth/config.py"},
            "I_invented_this": True,
        }
    )
    assert ok is False


def test_an_unknown_runtime_is_refused():
    ok, _ = validate(
        {
            "session_id": "s-1",
            "runtime": "a-runtime-the-estate-does-not-run",
            "kind": "phase",
            "at": "2026-09-09T21:40:00Z",
            "phase": "planning",
        }
    )
    assert ok is False


def test_a_tool_row_must_name_a_target_and_never_carry_output():
    ok, _ = validate(
        {
            "session_id": "s-1",
            "runtime": "otto",
            "kind": "tool",
            "at": "2026-09-09T21:40:00Z",
            "phase": "executing",
            "tool": {"name": "bash", "target": "kubectl get pods"},
            "output": "pod/foo 1/1 Running",  # the schema must not hold tool output
        }
    )
    assert ok is False
