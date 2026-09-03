"""The Superset features the ticket promised are guarded, not remembered (decision 0018;
founder 2026-09-03: "superset, we have it woring, just need the al the featiures that was ib
ticket"). Each row here pins one promise the audit of 2026-09-03 found unkept or unguarded:
the front door drill grades the Superset door, the runbook hands the founder no cluster
command, the onboarding names the datasets that exist, and the volume retirement is a
declared job with a role that can delete one claim and nothing else.
"""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DRILL = ROOT / "bin/idp-login-drill"
RUNBOOK = ROOT / "docs/runbooks/superset-dashboards.md"
ONBOARDING = ROOT / "docs/onboarding/superset.md"
DEMO = ROOT / "docs/demo/superset.md"
TAPE = ROOT / "demos/superset.tape"
RETIRE = ROOT / "platform/observability/metabase-volume-retire.yaml"
SEED = ROOT / "platform/observability/superset-boardroom-seed.yaml"


def test_the_login_drill_grades_the_superset_door():
    text = DRILL.read_text()
    start = text.index("OTHER_SURFACES = {")
    block = text[start : text.index("\n    }", start)]
    assert '"superset": f"https://superset.{ZONE}/"' in block, (
        "decision 0018 promises no second login on superset.<zone>; the hourly drill must grade it"
    )


def test_the_runbook_hands_the_founder_no_cluster_command():
    text = RUNBOOK.read_text()
    assert not re.search(r"kubectl\s+(-n\s+\S+\s+)?delete", text), (
        "LAW 31: the founder does not run scripts; the cleanup is a declared job, not a command"
    )
    assert "metabase-volume-retire" in text
    assert "ImportDashboardsCommand" in text, (
        "the runbook names the importer the seed calls"
    )
    assert "superset-httproute.yaml" in text, (
        "the sign-in pointer names Superset's own route file"
    )


def test_the_onboarding_names_the_seeded_datasets():
    text = ONBOARDING.read_text()
    seed = "\n".join(
        d["spec"]["template"]["spec"]["containers"][0]["args"][0]
        for d in yaml.safe_load_all(SEED.read_text())
        if d and d.get("kind") == "Job"
    )
    for dataset in re.findall(r'"table_name": "([a-z_]+)"', seed):
        assert f"`{dataset}`" in text, (
            f"the onboarding must name the seeded dataset {dataset}"
        )
    assert "events table" not in text, "no such table is seeded"


def test_the_demo_and_tape_carry_no_stale_file_count():
    assert "five declared files" not in DEMO.read_text()
    assert "five declared files" not in TAPE.read_text()


def _retire_docs():
    return [d for d in yaml.safe_load_all(RETIRE.read_text()) if d]


def test_the_volume_retire_role_can_delete_one_claim_and_nothing_else():
    role = next(d for d in _retire_docs() if d["kind"] == "Role")
    assert len(role["rules"]) == 1
    rule = role["rules"][0]
    assert rule["resources"] == ["persistentvolumeclaims"]
    assert rule["resourceNames"] == ["pgdata-metabase-db-0"]
    assert set(rule["verbs"]) <= {"get", "delete"}
    binding = next(d for d in _retire_docs() if d["kind"] == "RoleBinding")
    assert (
        binding["roleRef"]["kind"] == "Role"
        and binding["roleRef"]["name"] == role["metadata"]["name"]
    )


def test_the_volume_retire_job_has_the_estate_batch_shape():
    job = next(d for d in _retire_docs() if d["kind"] == "Job")
    spec = job["spec"]["template"]["spec"]
    assert (
        job["metadata"]["annotations"]["kustomize.toolkit.fluxcd.io/force"] == "Enabled"
    )
    assert spec["priorityClassName"] == "platform-batch"
    assert spec["serviceAccountName"] == "metabase-volume-retire"
    container = spec["containers"][0]
    cpu = container["resources"]["requests"]["cpu"]
    assert cpu.endswith("m") and int(cpu[:-1]) <= 225
    assert "." in container["image"].split("/")[0], "registry named in full"
    assert ":" in container["image"].rsplit("/", 1)[-1], "image tag pinned"
    assert job["spec"]["ttlSecondsAfterFinished"] >= 86400
    assert job["spec"]["activeDeadlineSeconds"] <= 900
    script = "\n".join(container["args"])
    assert "delete pvc pgdata-metabase-db-0" in script
    assert "$" not in RETIRE.read_text(), (
        "Flux strict envsubst demands a source for any $VAR"
    )


def test_the_volume_retire_job_waits_for_the_founders_merge():
    """Deleting a volume cannot be undone (LAW 11): the job is declared but wired into the
    observability kustomization only by the change the founder merges. Once wired, this row
    flips to require the wiring, so a later cleanup cannot silently unwire it."""
    kustomization = yaml.safe_load(
        (ROOT / "platform/observability/kustomization.yaml").read_text()
    )
    resources = kustomization["resources"]
    wired = "metabase-volume-retire.yaml" in resources
    marker = ROOT / "docs/runbooks/superset-dashboards.md"
    if wired:
        assert "retired on" in marker.read_text(), (
            "once the founder wires the retire job, the runbook records the date it ran"
        )
    else:
        assert "merges" in marker.read_text(), (
            "the runbook names the founder's merge as the gate"
        )
