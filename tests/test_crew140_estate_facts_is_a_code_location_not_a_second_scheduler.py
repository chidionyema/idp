"""crew#140: the crew fact-file assets run on the one scheduler as a registered code location.

The founder's headline is one platform. The first cut of crew#140 was a standalone Dagster
project started with `dagster dev` in the crew repo, i.e. a second scheduler. This asserts the
shape that replaces it: workspace.yaml names the location, by a path relative to this
directory (LAW 46: no home, no absolute path), and bin/scheduler-up refuses to start over a
location that does not import. When the crew checkout is beside this one, the location is
loaded for real on this interpreter.
"""
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "scheduler" / "workspace.yaml"


def _locations() -> dict[str, dict]:
    doc = yaml.safe_load(WORKSPACE.read_text())
    return {e["python_file"]["location_name"]: e["python_file"] for e in doc["load_from"]}


def test_workspace_names_both_locations_by_relative_path():
    locs = _locations()
    assert set(locs) == {"estate-scheduler", "estate-facts"}
    facts = locs["estate-facts"]
    assert facts["attribute"] == "defs"
    for key in ("relative_path", "working_directory"):
        assert not facts[key].startswith(("/", "~")), facts[key]
        assert "Users" not in facts[key]
    assert facts["relative_path"] == "../../crew/science/scheduler/estate_dagster/facts.py"


def test_scheduler_up_refuses_a_missing_or_broken_facts_location():
    text = (ROOT / "bin" / "scheduler-up").read_text()
    assert 'crew/science/scheduler"' in text and "idp-repo-root" in text
    assert "from estate_dagster.facts import defs" in text
    # the refusal path is a stated FAIL with exit 1, before the daemon is started
    assert text.index("code location estate-facts") < text.index("dagster-daemon\" run")


def test_facts_location_loads_on_this_interpreter_when_the_crew_checkout_is_beside_idp():
    facts = _locations()["estate-facts"]
    wd = (WORKSPACE.parent / facts["working_directory"]).resolve()
    if not (wd / "estate_dagster" / "facts.py").exists():
        # CI checks out idp alone; the runtime proof is bin/scheduler-up's own load line and
        # reload_check.py on the live webserver, which name this location by name.
        import pytest

        pytest.skip(f"no crew checkout at {wd}; scheduler-up proves this on the estate")
    r = subprocess.run(
        [sys.executable, "-c", "from estate_dagster.facts import defs, SPECS; print(len(SPECS))"],
        cwd=wd, capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(wd)},
    )
    assert r.returncode == 0, r.stderr
    assert int(r.stdout.strip()) > 0
