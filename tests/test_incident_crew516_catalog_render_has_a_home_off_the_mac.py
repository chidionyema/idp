"""Incident test, crew#516 CP3 (2026-08-27): every consumer of the estate inventory read a Mac
path, so idp#431 graded the catalogue render `runs_on: mac`. Rule under test: the workflow that
renders off the Mac reads the inventory from the bucket object estate#9 publishes, checks crew
out beside idp for ESTATE_CODE, hands every Mac path to the tools by variable, and defaults to
--dry-run so the cloud render is measured before the Mac row is retired.
"""
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "catalog-render.yml"


def _wf():
    return yaml.safe_load(WF.read_text())


def _steps():
    return _wf()["jobs"]["render"]["steps"]


def test_incident_crew516_render_reads_the_bucket_object_estate9_writes():
    fetch = next(s for s in _steps() if "inventory from the bucket" in s.get("name", ""))
    assert "state/inventory/latest.json" in fetch["run"]    # the key estate#9 publishes
    ran = " ".join(str(s.get("run", "")) + " ".join(map(str, s.get("env", {}).values())) for s in _steps())
    assert "~/.estate" not in ran and "/Users/" not in ran   # no Mac path reaches a command, LAW 46
    render = next(s for s in _steps() if s.get("name") == "render")
    assert render["env"]["INV"].endswith("/inventory.json")
    assert "IDP_STATE_WORKTREE" in render["env"] and "ESTATE_CODE" in render["env"]


def test_incident_crew516_keys_reach_rclone_as_environment_never_argv():
    fetch = next(s for s in _steps() if "inventory from the bucket" in s.get("name", ""))
    assert "RCLONE_S3_ACCESS_KEY_ID" in fetch["env"] and "RCLONE_S3_SECRET_ACCESS_KEY" in fetch["env"]
    assert "secrets." not in fetch["run"]                  # values live in env, not the command


def test_incident_crew516_default_is_dry_run_and_commit_is_a_choice():
    wf = _wf()
    inputs = wf[True]["workflow_dispatch"]["inputs"]["mode"]   # yaml reads `on` as True
    assert inputs["default"] == "dry-run" and inputs["options"] == ["dry-run", "commit"]
    render = next(s for s in _steps() if s.get("name") == "render")
    assert re.search(r"dry-run.*--dry-run", render["run"])
    assert "58 1,7,13,19 * * *" in [c["cron"] for c in wf[True]["schedule"]]


def test_incident_crew516_the_mac_row_still_stands_until_parity():
    sched = yaml.safe_load((ROOT / "scheduler" / "schedule.yml").read_text())
    jobs = sched.get("jobs", sched)
    assert jobs["com.estate.catalog-render"]["runs_on"] == "mac"
