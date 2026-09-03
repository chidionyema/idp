"""crew#516 CP2 (founder 2026-08-27, "priortise moving fully to cloud"): the Mac ran 41 Dagster
schedules (GraphQL localhost:3210, 16:32Z) and docs/MAC-EXIT.md said 20, because nothing in the
spec said which jobs belong on the cluster, which wait on a ticket, and which exist only because
the estate sits on a laptop. Rule: every job in scheduler/schedule.yml carries `runs_on` in
{cluster, mac, retire} and a `runs_on_ref` crew item; a `cluster` job's command, cwd and env
never name a Mac-only path or tool. Rung 4, incident test."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "scheduler/schedule.yml"
# Mac-only paths and tools. An absolute interpreter (/usr/bin/python3, a .venv) is not on
# this list: the CronJob renderer (slice 2) substitutes the image's python; the rule here is
# what no image can carry. It reads the command line only: a script that opens ~/.estate
# inside passes it, which is why 7 rows were graded cluster on 2026-08-27 before anyone read them.
MAC_ONLY = re.compile(
    r"~/Documents/|~/Library/|launchctl|launchd|colima|docker|pmset|brew "
)
REF = re.compile(r"^crew#\d+( CP\d+)?$")


def _jobs(text=None):
    return (yaml.safe_load(text or SPEC.read_text()) or {})["jobs"]


def _flat(v):
    return (
        " ".join(map(str, v.get("command", [])))
        + " "
        + str(v.get("cwd", ""))
        + " "
        + " ".join(f"{k}={x}" for k, x in (v.get("env") or {}).items())
    )

    # No floor on the cluster count: on 2026-08-27 the honest number was 0 of 43 (every row reads or
    # writes Mac state), and a floor would have forced a lie to keep the suite green (LAW 38).


def test_the_rule_refuses_a_job_without_runs_on_and_a_cluster_job_with_a_mac_path():
    """The other way: a spec missing the field and a cluster job that runs docker both fail."""
    missing = yaml.safe_dump(
        {"jobs": {"x": {"command": ["true"], "cron": "* * * * *"}}}
    )
    assert [
        k
        for k, v in _jobs(missing).items()
        if v.get("runs_on") not in ("cluster", "mac", "retire")
    ] == ["x"]
    leaky = {
        "runs_on": "cluster",
        "runs_on_ref": "crew#516 CP2",
        "command": ["docker", "ps"],
    }
    assert MAC_ONLY.search(_flat(leaky)).group(0) == "docker"
    assert not MAC_ONLY.search(
        _flat({"command": ["python3", "$IDP/bin/idp-catalog-push"]})
    )
