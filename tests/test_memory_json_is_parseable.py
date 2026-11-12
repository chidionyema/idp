"""`--json` is a contract: stdout is one JSON document and nothing else.

Why this exists (root cause, 2026-11-12): bin/estate-memory-required printed its JSON report and
then, when the memory door was not OK, appended the human repair guidance to the SAME stream. Every
strict reader therefore failed with `JSONDecodeError: Extra data` at exactly the moment the report
mattered -- and bin/idp-ci's memreq rung reads this script with --json, so the gate went red for a
reason that looked like broken code but was a broken output contract.

The first version of this file only exercised the healthy door, so the defect could be put back and
the tests still passed: an OK verdict prints no guidance, so nothing was ever appended. That is a
test that cannot fail, which is not a test (AGENTS.md section 9, principle 1). Every case below
therefore drives a NOT-OK verdict, which is where the guidance is printed.

Proven capable of failing: put `guide = sys.stdout` back and both not-OK cases raise
"Extra data" / "guidance leaked onto stdout under --json".
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ROOT / "bin" / "estate-memory-required"


def _run(extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = {"PATH": "/usr/bin:/bin", "HOME": str(Path.home())}
    env.update(extra_env or {})
    return subprocess.run(
        [sys.executable, str(REQUIRED), "--json"],
        capture_output=True,
        text=True,
        timeout=90,
        env=env,
        cwd=str(ROOT),
    )


def _force_broken_memory(tmp_path: Path) -> Path:
    """A memory dir whose door cannot import: verdict() returns BROKEN, never OK."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    (memory_dir / "door.py").write_text(
        "import local_store  # deleted: the 2026-11-10 bug\n"
    )
    return memory_dir


def test_a_broken_door_still_emits_exactly_one_json_document(tmp_path: Path) -> None:
    """The failure path is where the bug was: stdout must still be one parseable document.

    json.loads over the WHOLE of stdout -- "Extra data" is the exact failure this guards.
    """
    r = _run({"ESTATE_MEMORY_DIR": str(_force_broken_memory(tmp_path))})
    payload = json.loads(r.stdout)
    assert isinstance(payload, dict), r.stdout[:400]
    assert "verdict" in payload, payload


def test_guidance_never_leaks_onto_stdout_under_json(tmp_path: Path) -> None:
    """Whatever the verdict, the human guidance must not appear on the JSON stream."""
    r = _run({"ESTATE_MEMORY_DIR": str(_force_broken_memory(tmp_path))})
    json.loads(r.stdout)
    assert "Repair it first" not in r.stdout, "guidance leaked onto stdout under --json"


def test_the_healthy_door_is_also_one_document() -> None:
    """And the OK case, so the contract holds in both directions."""
    r = _run()
    payload = json.loads(r.stdout)
    assert payload.get("verdict"), payload
