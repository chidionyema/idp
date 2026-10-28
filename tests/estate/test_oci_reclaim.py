"""The OCI reclaim door's rules, proved offline (idp#7318).

The estate hit its OCI volume quota on 2026-09-07 and could not create a volume since: the
bridge instance's boot volume was refused, the control plane became unreachable, and the
cluster's LiteLLM -- the cloud route of the estate's router -- answered 503 for every caller.
The capacity was held by 14 CSI volumes, every one of them AVAILABLE with no attachment.

Freeing them is a deletion, so the rules that choose them have to be provable without OCI and
without the estate's data. These tests are that proof: the selection is a filter over the OCI
answer, and a filter can be read.

THE TWO-WAY PROOF. A gate that cannot fail is not a gate (AGENTS.md section 3). So each rule is
also shown refusing a volume that must not be touched: an attached volume, a volume in use, a
volume that is not a CSI volume, a volume without the estate's tag, a volume created an hour
ago, and the oldest volume, which a long-lived PersistentVolume may still point at.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
HELPER = REPO / "platform" / "estate" / "libexec" / "oci-reclaim.py"
SCRIPT = REPO / "platform" / "estate" / "libexec" / "oci-reclaim.sh"
INTENT = REPO / "platform" / "estate" / "intents" / "oci-reclaim.yaml"

NOW = "2026-10-28T04:00:00Z"


def _volume(ocid: str, name: str, **over):
    volume = {
        "id": ocid,
        "display-name": name,
        "lifecycle-state": "AVAILABLE",
        "size-in-gbs": 50,
        "time-created": "2026-08-25T04:14:03Z",
        "freeform-tags": {"role": "persistent_volume", "state_id": "tiafzl"},
        "volume-attachments": None,
    }
    volume.update(over)
    return volume


def _select(volumes, tmp_path, keep_oldest=1, older_than_hours=24):
    """Run the real helper over a fixture and return the OCIDs it chose.

    The fixture and the id file live in this test's own directory: the suite runs under xdist,
    and a shared path would make one worker's cleanup delete another worker's answer.
    """
    fixture = tmp_path / "oci-reclaim-fixture.json"
    fixture.write_text(json.dumps({"data": volumes}))
    ids = tmp_path / "oci-reclaim-ids.txt"
    proc = subprocess.run(
        [
            "python3",
            str(HELPER),
            "--volumes",
            str(fixture),
            "--keep-oldest",
            str(keep_oldest),
            "--older-than-hours",
            str(older_than_hours),
            "--ids-out",
            str(ids),
            "--now",
            NOW,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return [line for line in ids.read_text().splitlines() if line], proc.stdout


def test_an_unattached_old_csi_volume_is_reclaimable(tmp_path) -> None:
    # keep_oldest=0: this volume is the oldest there is, so the default would keep it. The rule
    # under test is the attachment, not the age.
    chosen, out = _select(
        [_volume("ocid1.volume.1", "csi-aaaa")], tmp_path, keep_oldest=0
    )
    assert chosen == ["ocid1.volume.1"], out
    assert "RECLAIM" in out


def test_a_volume_that_is_attached_is_kept(tmp_path) -> None:
    attached = _volume(
        "ocid1.volume.2",
        "csi-bbbb",
        **{
            "volume-attachments": [
                {
                    "instance-id": "ocid1.instance.1",
                    "device": "/dev/oracleoci/oraclevdb",
                }
            ]
        },
    )
    chosen, out = _select([attached], tmp_path)
    assert chosen == [], out
    assert "attached to an instance" in out


def test_a_volume_in_use_is_kept(tmp_path) -> None:
    chosen, out = _select(
        [_volume("ocid1.volume.3", "csi-cccc", **{"lifecycle-state": "IN_USE"})],
        tmp_path,
    )
    assert chosen == [], out
    assert "not AVAILABLE" in out


def test_a_volume_that_is_not_a_csi_volume_is_kept(tmp_path) -> None:
    """A boot volume, or one the estate declared in terraform, must never be selected."""
    chosen, out = _select([_volume("ocid1.volume.4", "estate-bridge-boot")], tmp_path)
    assert chosen == [], out
    assert "not a CSI volume" in out


def test_a_volume_without_the_estates_tag_is_kept(tmp_path) -> None:
    chosen, out = _select(
        [_volume("ocid1.volume.5", "csi-dddd", **{"freeform-tags": {}})], tmp_path
    )
    assert chosen == [], out
    assert "role=persistent_volume" in out


def test_a_volume_created_an_hour_ago_is_kept(tmp_path) -> None:
    young = _volume(
        "ocid1.volume.6", "csi-eeee", **{"time-created": "2026-10-28T03:00:00Z"}
    )
    chosen, out = _select([young], tmp_path)
    assert chosen == [], out
    assert "younger than" in out


def test_the_oldest_volume_is_kept_because_a_persistent_volume_may_point_at_it(
    tmp_path,
) -> None:
    """The conservative choice, and the reason the door has a knob at all."""
    old = _volume(
        "ocid1.volume.7", "csi-oldest", **{"time-created": "2026-08-01T00:00:00Z"}
    )
    newer = _volume(
        "ocid1.volume.8", "csi-newer", **{"time-created": "2026-09-01T00:00:00Z"}
    )
    chosen, out = _select([old, newer], tmp_path, keep_oldest=1)
    assert chosen == ["ocid1.volume.8"], out
    assert "oldest kept volumes" in out


def test_the_fourteen_volumes_of_the_estate_leave_three_kept_and_eleven_reclaimable(
    tmp_path,
) -> None:
    """The estate's own state, measured: 14 CSI volumes, 700GB, all unattached."""
    volumes = [
        _volume(
            f"ocid1.volume.{i:02d}",
            f"csi-{i:04d}",
            **{"time-created": f"2026-08-{(i % 9) + 1:02d}T04:14:03Z"},
        )
        for i in range(14)
    ]
    chosen, out = _select(volumes, tmp_path, keep_oldest=3)
    assert len(chosen) == 11, out
    assert "11 volume(s) reclaimable, 550GB" in out


def test_the_door_is_wired_an_intent_that_runs_this_script() -> None:
    """The rules are only a capability when something can be asked to run them."""
    assert SCRIPT.exists(), "the script the intent calls is missing"
    assert INTENT.exists(), "the intent is missing"
    body = INTENT.read_text()
    assert "name: oci-reclaim" in body
    assert "oci-reclaim.sh" in body
    # The dry run is the default: a door that deletes without being asked is not a door.
    # The argument is a string, not a bool: the executor's resolve_args coerces int and string
    # only, so a bool would arrive as the word "False" and the door would read that as a yes.
    assert 'apply: {type: string, default: "false"}' in body


# The node mode. OKE will not remove a node from a pool that is already over the free tier's
# node limit ("LimitExceeded: nodes-per-node-pool limit has been exceeded", oke-check run
# 40650458830), so the compute API is the door that can. The rule that keeps it honest is that
# only a node that is not running is ever a candidate.


def _node_verdict(state: str, tmp_path) -> str:
    fixture = tmp_path / f"node-fixture-{state}.json"
    fixture.write_text(
        json.dumps(
            {
                "data": {
                    "id": "ocid1.instance.1",
                    "lifecycle-state": state,
                    "boot-volume-id": "ocid1.bootvolume.1",
                }
            }
        )
    )
    proc = subprocess.run(
        ["python3", str(HELPER), "--node-instance", str(fixture)],
        capture_output=True,
        text=True,
        check=False,
    )
    fixture.unlink(missing_ok=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout.strip()


def test_a_stopped_node_is_the_one_that_may_be_terminated(tmp_path) -> None:
    out = _node_verdict("STOPPED", tmp_path)
    assert out.startswith("TERMINE ocid1.instance.1"), out


def test_a_running_node_is_never_terminated(tmp_path) -> None:
    out = _node_verdict("RUNNING", tmp_path)
    assert out.startswith("REFUSE"), out
    assert "running node is never terminated" in out


def test_a_node_in_an_unknown_state_is_refused_not_guessed(tmp_path) -> None:
    out = _node_verdict("PROVISIONING", tmp_path)
    assert out.startswith("REFUSE"), out
    assert "not a state this door acts on" in out


def test_a_node_that_is_already_going_is_refused(tmp_path) -> None:
    out = _node_verdict("TERMINATED", tmp_path)
    assert out.startswith("REFUSE"), out
    assert "already going or gone" in out


def test_the_door_refuses_a_what_it_does_not_know() -> None:
    proc = subprocess.run(
        ["bash", str(SCRIPT), "plan", "3", "24", "", "everything"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "what must be volumes or node" in proc.stdout


def test_the_intent_carries_the_node_mode() -> None:
    body = INTENT.read_text()
    assert 'what: {type: string, default: "volumes"}' in body
    assert 'node_id: {type: string, default: ""}' in body
    assert "{{what}} {{node_id}}" in body
