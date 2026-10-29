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
import os
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


def _select(volumes, tmp_path, keep_oldest=1, older_than_hours=24, attached=()):
    """Run the real helper over a fixture and return the OCIDs it chose.

    The fixture and the id file live in this test's own directory: the suite runs under xdist,
    and a shared path would make one worker's cleanup delete another worker's answer.

    `attached` is the volume ids the ATTACHMENT API says are attached to an instance -- the
    truth the rules read, fetched separately from the volume list (MEASURED 2026-10-28: the
    volume list leaves its own "volume-attachments" field empty on every volume, attached or
    not, so a rule that trusted that field called five volumes in use reclaimable).
    """
    fixture = tmp_path / "oci-reclaim-fixture.json"
    fixture.write_text(json.dumps({"data": volumes}))
    attachments = tmp_path / "oci-reclaim-attachments.json"
    attachments.write_text(
        json.dumps(
            {
                "data": [
                    {
                        "id": f"ocid1.volumeattachment.{i}",
                        "volume-id": volume_id,
                        "instance-id": "ocid1.instance.1",
                        "lifecycle-state": "ATTACHED",
                    }
                    for i, volume_id in enumerate(attached)
                ]
            }
        )
    )
    ids = tmp_path / "oci-reclaim-ids.txt"
    proc = subprocess.run(
        [
            "python3",
            str(HELPER),
            "--volumes",
            str(fixture),
            "--attachments",
            str(attachments),
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


def test_a_volume_the_attachment_api_says_is_attached_is_kept(tmp_path) -> None:
    """The regression for the measured defect: the volume list does not carry the attachment.

    The list answers "volume-attachments": null for a volume that IS attached to a node, so a
    rule that trusted the list called five volumes in use reclaimable. The attachment API is
    the truth about an attachment, and the rule reads it.
    """
    chosen, out = _select(
        [_volume("ocid1.volume.9", "csi-ffff")],
        tmp_path,
        keep_oldest=0,
        attached=["ocid1.volume.9"],
    )
    assert chosen == [], out
    assert "the attachment API says so" in out


def test_a_volume_the_attachment_api_does_not_list_is_reclaimable(tmp_path) -> None:
    chosen, out = _select(
        [_volume("ocid1.volume.10", "csi-gggg")],
        tmp_path,
        keep_oldest=0,
        attached=["ocid1.volume.other"],
    )
    assert chosen == ["ocid1.volume.10"], out
    assert "RECLAIM" in out


def test_a_volume_in_use_is_kept(tmp_path) -> None:
    chosen, out = _select(
        [_volume("ocid1.volume.3", "csi-cccc", **{"lifecycle-state": "IN_USE"})],
        tmp_path,
    )
    assert chosen == [], out
    assert "not AVAILABLE or TERMINATED" in out


def test_a_terminated_volume_is_kept_because_it_is_already_released(tmp_path) -> None:
    """A terminated volume is dead, and OCI has already released it.

    MEASURED 2026-10-28: the door deleted seven TERMINATED volumes, printed a receipt for each
    one, and the compartment went on listing the same fourteen names with the same ages. The
    refusal was explained by the LIVE storage -- five attached volumes, 250GB, against a 200GB
    Always Free allowance -- and only a volume that is still AVAILABLE and unattached can be
    deleted to move that number. A door that claims to reclaim a dead volume prints a receipt
    and frees nothing, which is the defect this test now refuses.
    """
    dead = _volume("ocid1.volume.11", "csi-hhhh", **{"lifecycle-state": "TERMINATED"})
    chosen, out = _select([dead], tmp_path, keep_oldest=0)
    assert chosen == [], out
    assert "already released" in out


def test_a_terminated_volume_is_never_mistaken_for_an_attached_one(tmp_path) -> None:
    """A dead volume is not attached, and the rule does not need the attachment API to say so."""
    dead = _volume("ocid1.volume.12", "csi-iiii", **{"lifecycle-state": "TERMINATED"})
    chosen, out = _select([dead], tmp_path, keep_oldest=0, attached=["ocid1.volume.12"])
    assert chosen == [], out
    assert "already released" in out


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


# THE TWO DEFECTS MEASURED 2026-10-29, both falsified here.
#
# 1. An attachment row in lifecycle state DETACHED is not an attachment. MEASURED 2026-10-29:
#    the compartment held 8 rows in state DETACHED whose volumes were AVAILABLE, and the rule
#    read every row's volume-id as "attached", so live volumes were reported as in use.
# 2. The OCI CLI answers an EMPTY collection with exit status 0 and ZERO BYTES on stdout --
#    not an error, not "[]". MEASURED 2026-10-29 on the estate's own compartment:
#      $ oci compute volume-attachment list --compartment-id <compartment> --all ... --output json
#      rc=0
#      $ wc -c < att.json
#      0
#    The door fed that to json.load, so it refused the whole compartment:
#      FAIL  oci-reclaim  cannot read .../oci-reclaim-attachments.XXXXXX: Expecting value: line 1 column 1 (char 0)
#      exit 2
#    Both defects are conservative -- a false keep and a refusal -- which is why they survived:
#    they block the door instead of breaking it.


def _select_with_attachment_rows(volumes, tmp_path, rows, keep_oldest=0):
    """Run the real helper over a fixture whose attachment rows are given verbatim.

    The rows are the OCI answer as the API prints it, so a test can put a row in the
    lifecycle state the API actually reports.
    """
    fixture = tmp_path / "oci-reclaim-rows-volumes.json"
    fixture.write_text(json.dumps({"data": volumes}))
    attachments = tmp_path / "oci-reclaim-rows-attachments.json"
    attachments.write_text(json.dumps({"data": rows}))
    ids = tmp_path / "oci-reclaim-rows-ids.txt"
    proc = subprocess.run(
        [
            "python3",
            str(HELPER),
            "--volumes",
            str(fixture),
            "--attachments",
            str(attachments),
            "--keep-oldest",
            str(keep_oldest),
            "--older-than-hours",
            "24",
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


def test_a_detached_attachment_row_does_not_count_as_attached(tmp_path) -> None:
    """A DETACHED row is not an attachment: the volume it names is free to be reclaimed."""
    rows = [
        {
            "id": "ocid1.volumeattachment.1",
            "volume-id": "ocid1.volume.20",
            "instance-id": "ocid1.instance.1",
            "lifecycle-state": "DETACHED",
        }
    ]
    chosen, out = _select_with_attachment_rows(
        [_volume("ocid1.volume.20", "csi-detached")], tmp_path, rows
    )
    assert chosen == ["ocid1.volume.20"], out
    assert "RECLAIM" in out


def test_an_attached_attachment_row_still_counts_as_attached(tmp_path) -> None:
    """The fix reads the row's own state, so an ATTACHED row keeps its volume."""
    rows = [
        {
            "id": "ocid1.volumeattachment.2",
            "volume-id": "ocid1.volume.21",
            "instance-id": "ocid1.instance.1",
            "lifecycle-state": "ATTACHED",
        }
    ]
    chosen, out = _select_with_attachment_rows(
        [_volume("ocid1.volume.21", "csi-attached")], tmp_path, rows
    )
    assert chosen == [], out
    assert "the attachment API says so" in out


def test_an_attachment_row_with_no_lifecycle_state_is_treated_as_attached(
    tmp_path,
) -> None:
    """A row whose state the door cannot read is a keep, not a guess.

    The door only acts on a state it has read. A row with no state is the absence of evidence,
    and the absence of evidence keeps the volume.
    """
    rows = [{"id": "ocid1.volumeattachment.3", "volume-id": "ocid1.volume.22"}]
    chosen, out = _select_with_attachment_rows(
        [_volume("ocid1.volume.22", "csi-unknown-state")], tmp_path, rows
    )
    assert chosen == [], out
    assert "the attachment API says so" in out


def test_an_empty_attachment_collection_is_an_empty_collection_not_a_parse_failure(
    tmp_path,
) -> None:
    """Zero bytes from a successful list is the empty collection it is.

    The CLI writes nothing at all for an empty collection, so the file is empty. The door must
    read that as "nothing is attached" -- not as a broken file, and not as a refusal of the
    whole compartment.
    """
    fixture = tmp_path / "oci-reclaim-empty-volumes.json"
    fixture.write_text(
        json.dumps({"data": [_volume("ocid1.volume.23", "csi-empty-list")]})
    )
    attachments = tmp_path / "oci-reclaim-empty-attachments.json"
    attachments.write_text("")
    ids = tmp_path / "oci-reclaim-empty-ids.txt"
    proc = subprocess.run(
        [
            "python3",
            str(HELPER),
            "--volumes",
            str(fixture),
            "--attachments",
            str(attachments),
            "--keep-oldest",
            "0",
            "--older-than-hours",
            "24",
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
    assert [line for line in ids.read_text().splitlines() if line] == [
        "ocid1.volume.23"
    ]
    assert "0 volume(s) attached" in proc.stdout


def test_the_door_reclaims_when_the_attachment_collection_is_empty(tmp_path) -> None:
    """The whole door, end to end, with the OCI CLI answering an empty collection.

    This is the estate's own compartment as measured on 2026-10-29: the attachment collection
    is empty and the CLI prints nothing for it. Before the fix the door refused the
    compartment with a JSON parse failure and could not reclaim a single volume.
    """
    stub = tmp_path / "bin"
    stub.mkdir()
    (stub / "oci").write_text(
        "#!/usr/bin/env bash\n"
        "# A stub OCI: one AVAILABLE CSI volume, and an EMPTY attachment collection printed as\n"
        "# zero bytes with exit status 0 -- exactly what the real CLI does.\n"
        "if [ \"$1 $2\" = 'compute volume-attachment' ]; then exit 0; fi\n"
        "if [ \"$1 $2\" = 'bv volume' ] && [ \"$3\" = 'list' ]; then\n"
        "  cat <<'JSON'\n"
        '{"data": [{"id": "ocid1.volume.30", "display-name": "csi-stub", '
        '"lifecycle-state": "AVAILABLE", "size-in-gbs": 50, '
        '"time-created": "2026-08-25T04:14:03Z", '
        '"freeform-tags": {"role": "persistent_volume"}, "volume-attachments": null}]}\n'
        "JSON\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n"
    )
    (stub / "oci").chmod(0o755)
    env = dict(os.environ)
    env["PATH"] = f"{stub}:{env['PATH']}"
    proc = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "plan",
            "0",
            "24",
            "ocid1.compartment.oc1..test",
            "volumes",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "1 volume(s) would be deleted" in proc.stdout, proc.stdout


def _node_verdict(state: str, tmp_path) -> str:
    fixture = tmp_path / f"node-fixture-{state}.json"
    fixture.write_text(
        json.dumps(
            {
                "data": {
                    "id": "ocid1.instance.1",
                    "lifecycle-state": state,
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


def test_the_door_does_not_claim_a_boot_volume_it_cannot_see() -> None:
    """The door may not name a volume OCI does not show it.

    MEASURED 2026-10-28: `oci compute instance get` prints no boot-volume field for an
    instance and `oci bv volume list` does not list the node's boot volume, so the old
    extraction path could only ever produce an empty id. A door that promised to delete a
    boot volume it cannot name is a promise it cannot keep.
    """
    body = SCRIPT.read_text()
    assert "boot-volume-id" not in body
    assert "is_preserve_boot_volume = false" in body
    helper = HELPER.read_text()
    assert "def node_boot_volume" not in helper
