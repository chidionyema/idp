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


def test_incident_crew516_both_checkouts_sit_inside_the_workspace():
    # actions/checkout refuses "Repository path ... is not under GITHUB_WORKSPACE": a `../crew`
    # path killed the job at step 2 on every tick (idp#445 review). Both repos are siblings
    # under the workspace and the render runs from idp/.
    outs = [s for s in _steps() if "actions/checkout" in str(s.get("uses", ""))]
    paths = [str(s.get("with", {}).get("path", "")) for s in outs]
    assert sorted(paths) == ["crew", "idp"], paths
    assert not any(".." in x for x in paths)
    render = next(s for s in _steps() if s.get("name") == "render")
    assert render.get("working-directory") == "idp"
    assert render["env"]["ESTATE_CODE"] == "${{ github.workspace }}"    # the dir holding crew/


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


def test_incident_crew516_the_mac_row_is_retired_and_the_workflow_has_a_schedule():
    """Parity reached 2026-08-27: the workflow renders the same pages from the bucket copies, so the
    Mac row is retired (not deleted: the launchd job is booted out by the scheduler reconcile)."""
    sched = yaml.safe_load((ROOT / "scheduler" / "schedule.yml").read_text())
    jobs = sched.get("jobs", sched)
    assert jobs["com.estate.catalog-render"]["runs_on"] == "retire"
    assert jobs["com.estate.catalog-render"]["runs_on_ref"] == "crew#516 CP3"
    assert _wf()[True]["schedule"], "the cloud render must run on a cron, not only on dispatch"


def test_incident_crew516_the_runner_carries_flux_and_reads_the_feed_from_the_bucket():
    """First dry-run (33099170685): `BLIND flux missing` and NEXT.md 123 lines short because the
    feed lived only on the Mac. The runner installs the pinned flux CLI and takes the feed
    estate#10 publishes; ESTATE_FEED points the render at that copy."""
    steps = _steps()
    flux = [s for s in steps if "fluxcd/flux2/action@" in str(s.get("uses", ""))]
    assert len(flux) == 1 and re.search(r"@[0-9a-f]{40}", flux[0]["uses"]), "flux action missing or not sha-pinned"
    fetch = next(s for s in steps if "inventory from the bucket" in s.get("name", ""))
    assert "state/feed/latest.md" in fetch["run"]                       # the key estate#10 writes
    assert "not in the bucket yet" in fetch["run"], "a missing feed must be a named line, not a dead job"
    render = next(s for s in steps if s.get("name") == "render")
    assert render["env"]["ESTATE_FEED"].endswith("/feed.md")


def test_incident_crew516_the_feed_receipt_is_the_file_and_the_push_needs_no_vault_beside_a_token():
    """Second dry-run (33102084969): the summary said `feed taken, last handoff ` with no file,
    because rclone copyto exits 0 for an absent object; and the catalogue push graded
    `BLIND sops missing` with a valid GH_TOKEN in the environment, because the push demanded the
    vault decryptor before asking gh. The file is the receipt; sops is required only when gh
    holds no token; the job may write packages so the push is real and not BLIND."""
    fetch = next(s for s in _steps() if "inventory from the bucket" in s.get("name", ""))
    assert re.search(r'\[ -s "\$RUNNER_TEMP/feed\.md" \]', fetch["run"]), "feed taken must be gated on a non-empty file"
    assert _wf()["permissions"].get("packages") == "write"
    push = (ROOT / "bin" / "idp-catalog-push").read_text()
    assert "for t in flux kubectl git; do" in push, "sops must not be a hard requirement"
    assert re.search(r"gh auth token >/dev/null 2>&1 \|\| command -v sops", push), "sops is the fallback after gh"
