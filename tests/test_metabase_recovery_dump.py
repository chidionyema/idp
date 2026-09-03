"""The recovery job reads the old dashboard volume and changes nothing.

Guards the class: a one-shot job against irreplaceable data must be loud,
query-only, and mount the exact surviving claim (crew ruling: silent-green,
and the decision-0018 swap that migrated no content).
"""

from pathlib import Path

import yaml

MANIFEST = (
    Path(__file__).parent.parent
    / "platform"
    / "observability"
    / "metabase-recovery-dump.yaml"
)


def _job():
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    jobs = [d for d in docs if d.get("kind") == "Job"]
    assert len(jobs) == 1, "exactly one Job in the recovery manifest"
    return jobs[0]


def _script(job):
    (container,) = job["spec"]["template"]["spec"]["containers"]
    return "\n".join(container["args"]), container


def test_job_mounts_the_surviving_claim_and_runs_as_the_database_user():
    job = _job()
    pod = job["spec"]["template"]["spec"]
    claims = [
        v["persistentVolumeClaim"]["claimName"]
        for v in pod["volumes"]
        if "persistentVolumeClaim" in v
    ]
    assert claims == ["pgdata-metabase-db-0"], (
        "the job must mount the old server's exact volume"
    )
    assert pod["securityContext"]["runAsUser"] == 70, (
        "same uid as the old server, or the data dir refuses"
    )
    _, container = _script(job)
    assert container["image"].startswith("docker.io/"), (
        "image names its registry in full"
    )


def test_job_is_loud_query_only_and_bounded():
    job = _job()
    script, _ = _script(job)
    assert "set -e" in script, "a failed query must fail the job, never read green"
    for word in ("DROP ", "DELETE ", "TRUNCATE", "UPDATE ", "INSERT ", "ALTER "):
        assert word not in script, f"recovery is read-only; found {word!r}"
    assert "report_card" in script and "report_dashboard" in script
    assert job["spec"]["backoffLimit"] == 0, "no retry hammering the volume"
    assert job["spec"]["activeDeadlineSeconds"] <= 900
    assert job["spec"]["ttlSecondsAfterFinished"] >= 86400, (
        "the log is the receipt; keep it at least a day"
    )
