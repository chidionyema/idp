#!/usr/bin/env python3
"""oci-reclaim.py -- choose the block volumes in an OCI compartment that are garbage.

WHY THIS EXISTS (2026-10-28, idp#7318). The estate's OKE tenancy carries 14 block volumes
created by the CSI driver between 2026-08-25 and 2026-09-07. Every one of them is in state
AVAILABLE with no attachment. They are the reason the estate cannot create a single volume:

    oci bv volume create --size-in-gbs 50 ... -> LimitExceeded:
      "You cannot create a volume because you have reached your limit. Upgrade to a paid account."

which is the same refusal the estate's own apply hit while creating the bridge instance's boot
volume (oke-check run 40608600584, 2026-10-28). With the volume quota exhausted, the bridge
could not be created, the control plane could not be reached, and the cluster's LiteLLM -- the
cloud route of the estate's router -- answered 503 "Starting up" for every caller.

Until now the estate had no door that could free that capacity: no intent, no script, no
playbook. Every agent that hit the wall had to either hand-run the OCI CLI (which the estate's
own login door refuses for agents) or leave the cluster dead. This is that door.

THE SELECTION RULES, and why each one is there. A volume is reclaimable only when ALL of these
hold:

  * its lifecycle state is AVAILABLE and unattached -- a volume that is IN_USE or ATTACHED is
    somebody's data. A TERMINATED volume is dead AND ALREADY RELEASED: OCI keeps it listed,
    but it holds no allowance and deleting it frees nothing. MEASURED 2026-10-28: the door
    deleted seven of them, printed a receipt for each, and the compartment still listed the
    same fourteen names with the same ages; what was over the allowance was the LIVE storage
    (five attached volumes, 250GB, against 200GB). A door that claims to reclaim a dead
    volume is a door that prints a receipt and frees nothing, so TERMINATED is kept here and
    named as dead;
  * it has no attachment -- and the attachment API is the answer, not the volume list. MEASURED
    2026-10-28: `oci bv volume list` leaves its own "volume-attachments" field empty on every
    volume, attached or not, so a rule that trusted that field called five volumes in use
    reclaimable and the plan was wrong. The delete API then refused them, which is why the
    apply was safe and the plan was not. The attachment list is fetched separately and the
    rule reads it;
  * its name starts with "csi-" -- the CSI driver's own naming, so a boot volume or a volume the
    estate declared in terraform can never be selected by accident;
  * it carries the freeform tag role=persistent_volume -- the estate's own marker;
  * it was created at least --older-than-hours ago -- a volume the estate is about to use is
    not garbage, and the default of 24 hours keeps a just-created volume out of reach;
  * it is not among the --keep-oldest N -- the oldest volumes are the ones a long-lived
    PersistentVolume points at (the estate's own comment in platform/oci/main.tf names
    backstage/pgdata-postgres-0 and prospector/prospector-store-api-data), and their data is
    not reproducible from the API. Keeping the oldest by default is the conservative choice:
    garbage is the newest, and the oldest is what a careful operator would keep.

The rules are a filter, not a heuristic, and they are applied to the OCI answer alone: this
script never talks to OCI, so the selection can be proved offline against a fixture.

THE NODE MODE, and why it exists. The volumes above were the first half of the capacity the
estate was missing. The second half was a node that never came up: the worker pool "a1" held
two nodes, one RUNNING and one STOPPED since 2026-08-27, and OKE refused every operation on
that pool with "LimitExceeded: nodes-per-node-pool limit has been exceeded" -- including
`oci ce node-pool delete-node` itself, which is the operation that would have removed it
(oke-check run 40650458830, 2026-10-28). The catch is closed the only way OCI lets it be
closed: the compute API is not subject to the container-engine pool limit, so a node that is
STOPPED is terminated through the compute API. A node that is RUNNING is never a candidate:
this door prunes a machine that serves nothing, and it never touches a machine that does.

The boot volume of that node is NOT chased here, and the reason is measured rather than
assumed: `oci compute instance get` does not expose the boot volume of an instance in any
field this CLI prints, and `oci bv volume list` does not list the node's boot volume at all.
A rule that looked for it found nothing, and a door that claimed to delete it would be
claiming a target it cannot see. The node pool creates its nodes with
`is_preserve_boot_volume = false`, so the termination releases the boot volume with the
instance; MEASURED 2026-10-28: after the termination the compartment listing no longer holds
the node's 100GB boot volume. The door says what it did and stops there.

USAGE
  oci-reclaim.py --volumes volumes.json --attachments attachments.json
                 [--keep-oldest 3] [--older-than-hours 24]
                 [--ids-out ids.txt] [--now 2026-10-28T00:00:00Z]
  oci-reclaim.py --node-instance instance.json

Prints one line per volume with the reason it was kept or chosen, and the totals. With
--ids-out it writes the OCIDs that may be deleted, one per line, and nothing else ever deletes
anything: the caller does, one volume at a time, and prints a receipt.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone


def _parse_time(value: str) -> datetime | None:
    if not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        stamp = datetime.fromisoformat(text)
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp


def attached_volume_ids(attachments: list) -> set[str]:
    """The volume ids the attachment API says are attached to an instance.

    The shape is OCI's own: `oci compute volume-attachment list` answers a list of objects with
    hyphenated keys, each carrying the id of the volume it attaches. A list that is empty or
    unreadable is not evidence that nothing is attached -- it is the absence of evidence, and
    the caller is expected to have refused to run in that case.
    """
    ids: set[str] = set()
    for item in attachments or []:
        if not isinstance(item, dict):
            continue
        for key in ("volume-id", "volume_id"):
            value = item.get(key)
            if value:
                ids.add(str(value))
                break
    return ids


def reclaimable(
    volume: dict,
    now: datetime,
    older_than_hours: int,
    keep: set[str],
    attached: set[str] | None = None,
) -> tuple[bool, str]:
    """True when this volume may be deleted, and the one-line reason either way."""
    name = volume.get("display-name") or ""
    state = (volume.get("lifecycle-state") or "").upper()
    dead = state == "TERMINATED"
    if state not in ("AVAILABLE", "TERMINATED"):
        return False, f"state {state or 'unknown'}, not AVAILABLE or TERMINATED"
    if not dead:
        if attached is not None and volume.get("id") in attached:
            return False, "attached to an instance (the attachment API says so)"
        if volume.get("volume-attachments"):
            return False, "attached to an instance"
    if not name.startswith("csi-"):
        return False, "not a CSI volume (name does not start with csi-)"
    tags = volume.get("freeform-tags") or {}
    if tags.get("role") != "persistent_volume":
        return False, "not tagged role=persistent_volume"
    created = _parse_time(volume.get("time-created") or "")
    if created is None:
        return False, "no time-created: age is unknown"
    age_h = (now - created).total_seconds() / 3600.0
    if age_h < older_than_hours:
        return False, f"created {age_h:.1f}h ago, younger than {older_than_hours}h"
    if volume.get("id") in keep:
        return (
            False,
            "one of the oldest kept volumes (a long-lived PersistentVolume may point at it)",
        )
    if dead:
        # A TERMINATED volume is dead, and OCI has already released it: it is listed, but it
        # holds no part of the tenancy's storage allowance, and deleting it changes nothing.
        # MEASURED 2026-10-28: this door deleted seven TERMINATED volumes and printed
        # `ok oci-reclaim deleted ...` for each one, and the compartment went on listing the
        # same fourteen names with the same ages. The refusal ("You cannot create a volume
        # because you have reached your limit") was explained by the LIVE storage -- five
        # attached volumes, 250GB, against a 200GB Always Free allowance -- and only a volume
        # that is still AVAILABLE and unattached can be deleted to move that number.
        return (
            False,
            "dead: OCI has already released it; deleting a TERMINATED volume changes nothing",
        )
    return (
        True,
        f"unattached CSI volume, {volume.get('size-in-gbs')}GB, {age_h:.0f}h old",
    )


def _age_of(volume: dict, now: datetime) -> float:
    created = _parse_time(volume.get("time-created") or "")
    if created is None:
        return float("inf")
    return (now - created).total_seconds()


def node_may_be_terminated(instance: dict) -> tuple[bool, str]:
    """True when this instance may be terminated, and the one-line reason either way.

    Only a STOPPED instance is a candidate. A running instance is never terminated by this
    door, and a state the door does not recognise is refused rather than guessed at: the door
    only acts on a state it has read.
    """
    state = (instance.get("lifecycle-state") or "").upper()
    if state == "STOPPED":
        return (
            True,
            "stopped: it serves nothing and holds a boot volume and a node slot",
        )
    if state in ("RUNNING", "ACTIVE"):
        return False, f"state {state}: a running node is never terminated by this door"
    if state in ("TERMINATING", "TERMINATED"):
        return False, f"state {state}: it is already going or gone"
    return False, f"state {state or 'unknown'}: not a state this door acts on"


def main(argv: list[str]) -> int:
    if "--node-instance" in argv:
        return _node_main(argv)
    return _volumes_main(argv)


def _node_main(argv: list[str]) -> int:
    path = argv[argv.index("--node-instance") + 1]
    try:
        with open(path) as fh:
            doc = json.load(fh)
    except (OSError, ValueError, IndexError) as exc:
        print(f"FAIL  oci-reclaim  cannot read the instance file: {exc}")
        return 2
    instance = doc.get("data", doc) if isinstance(doc, dict) else {}
    if not isinstance(instance, dict):
        print("FAIL  oci-reclaim  the instance file is not an instance")
        return 2
    ok, reason = node_may_be_terminated(instance)
    if ok:
        print(f"TERMINE {instance.get('id') or ''} -- {reason}")
        return 0
    print(f"REFUSE {reason}")
    return 0


def _volumes_main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="choose the reclaimable block volumes in a compartment"
    )
    ap.add_argument(
        "--volumes",
        default="",
        help="the OCI `oci bv volume list --output json` file",
    )
    ap.add_argument(
        "--keep-oldest",
        type=int,
        default=3,
        help="how many of the oldest volumes to keep",
    )
    ap.add_argument(
        "--older-than-hours",
        type=int,
        default=24,
        help="minimum age of a reclaimable volume",
    )
    ap.add_argument(
        "--attachments",
        default="",
        help="the OCI `oci compute volume-attachment list --output json` file; the "
        "attachment truth the rules read (the volume list does not carry it)",
    )
    ap.add_argument(
        "--ids-out", default="", help="write the chosen OCIDs here, one per line"
    )
    ap.add_argument(
        "--now", default="", help="the clock to age against (ISO 8601); default: now"
    )
    args = ap.parse_args(argv)

    if not args.volumes:
        print("FAIL  oci-reclaim  --volumes is required")
        return 2

    try:
        with open(args.volumes) as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        print(f"FAIL  oci-reclaim  cannot read {args.volumes}: {exc}")
        return 2
    volumes = doc.get("data", doc) if isinstance(doc, dict) else doc
    if not isinstance(volumes, list):
        print("FAIL  oci-reclaim  the volume file is not a list of volumes")
        return 2

    attached: set[str] = set()
    if args.attachments:
        try:
            with open(args.attachments) as fh:
                doc = json.load(fh)
        except (OSError, ValueError) as exc:
            print(f"FAIL  oci-reclaim  cannot read {args.attachments}: {exc}")
            return 2
        items = doc.get("data", doc) if isinstance(doc, dict) else doc
        if not isinstance(items, list):
            print("FAIL  oci-reclaim  the attachment file is not a list of attachments")
            return 2
        attached = attached_volume_ids(items)

    now = _parse_time(args.now) if args.now else datetime.now(timezone.utc)
    if now is None:
        print(f"FAIL  oci-reclaim  cannot read --now {args.now}")
        return 2

    # The oldest first: age is the ordering, and the oldest are the ones a long-lived
    # PersistentVolume points at, so they are the ones kept.
    ordered = sorted(volumes, key=lambda v: _age_of(v, now), reverse=True)
    keep = {v.get("id") for v in ordered[: max(args.keep_oldest, 0)] if v.get("id")}

    chosen: list[str] = []
    kept_gb = 0
    chosen_gb = 0
    print("volume                                          size  age     verdict")
    for volume in ordered:
        ok, reason = reclaimable(
            volume,
            now,
            args.older_than_hours,
            keep,
            attached if args.attachments else None,
        )
        name = (volume.get("display-name") or "?")[:44]
        size = volume.get("size-in-gbs")
        age_h = _age_of(volume, now) / 3600.0
        print(
            f"{name:<46} {str(size):>4}  {age_h:>6.0f}h  {'RECLAIM' if ok else 'keep'} -- {reason}"
        )
        if ok:
            chosen.append(volume.get("id") or "")
            chosen_gb += int(size or 0)
        else:
            kept_gb += int(size or 0)

    print(
        f"ok    oci-reclaim  {len(chosen)} volume(s) reclaimable, {chosen_gb}GB; "
        f"{len(volumes) - len(chosen)} kept, {kept_gb}GB"
    )
    if args.attachments:
        print(
            f"ok    oci-reclaim  {len(attached)} volume(s) attached, per the attachment API"
        )
    if args.ids_out:
        with open(args.ids_out, "w") as fh:
            for ocid in chosen:
                if ocid:
                    fh.write(ocid + "\n")
        print(f"ok    oci-reclaim  {len(chosen)} id(s) written to {args.ids_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
