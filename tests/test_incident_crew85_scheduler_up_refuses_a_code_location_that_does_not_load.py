"""crew#85, 2026-08-27 07:45Z: the webserver served a code location that no longer imported and
`bin/scheduler-up` said "already up". Rung 4, incident, both ways: a workspace whose locations
load is 0; a PythonError location, a GraphQL error, a timeout's empty body, or a non-workspace
reply is 1 with the reason named."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scheduler"))
from reload_check import verdict  # noqa: E402

LOADED = {
    "data": {
        "reloadWorkspace": {
            "__typename": "Workspace",
            "locationEntries": [
                {
                    "name": "definitions.py:defs",
                    "locationOrLoadError": {"__typename": "RepositoryLocation"},
                }
            ],
        }
    }
}
BROKEN = {
    "data": {
        "reloadWorkspace": {
            "__typename": "Workspace",
            "locationEntries": [
                {
                    "name": "definitions.py:defs",
                    "locationOrLoadError": {
                        "__typename": "PythonError",
                        "message": "DagsterImportError: No module named 'load_gate'\nmore",
                    },
                }
            ],
        }
    }
}


def test_a_workspace_whose_locations_load_is_zero():
    assert verdict(json.dumps(LOADED)) == (0, [])


def test_a_graphql_error_a_timeout_and_a_non_workspace_are_stated_refusals_not_tracebacks():
    assert verdict(json.dumps({"errors": [{"message": "boom"}]})) == (
        1,
        ["reloadWorkspace refused: boom"],
    )
    assert verdict("")[0] == 1 and "not JSON" in verdict("")[1][0]
    rc, lines = verdict(
        json.dumps(
            {"data": {"reloadWorkspace": {"__typename": "PythonError", "message": "x"}}}
        )
    )
    assert rc == 1 and "PythonError" in lines[0]
    assert (
        verdict(
            json.dumps(
                {
                    "data": {
                        "reloadWorkspace": {
                            "__typename": "Workspace",
                            "locationEntries": [],
                        }
                    }
                }
            )
        )[0]
        == 1
    )


def test_the_script_is_the_same_verdict_on_stdin():
    p = subprocess.run(
        [sys.executable, str(ROOT / "scheduler/reload_check.py")],
        input=json.dumps(BROKEN),
        capture_output=True,
        text=True,
    )
    assert p.returncode == 1 and "does not load" in p.stdout
