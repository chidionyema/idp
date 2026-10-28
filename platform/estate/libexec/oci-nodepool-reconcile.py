#!/usr/bin/env python3
"""oci-nodepool-reconcile rules (idp#7343). Pure functions, proved offline.

An OKE node pool can hold node records for instances that are gone (measured 2026-10-28: pool
a1 size 2, both instances TERMINATED, NODEPOOL_RECONCILE work request FAILED). The instance's
own lifecycle state is the truth, never the pool record. A node is a phantom only when its
instance is TERMINATED/TERMINATING or absent. Anything else is kept, and an unknown state is
kept too (a door that cannot see must not delete).
"""

from __future__ import annotations

import argparse
import json
import sys

DEAD = {"TERMINATED", "TERMINATING"}
ABSENT = "ABSENT"


def classify(pool_nodes, instances):
    """pool_nodes: list of {id, lifecycle-state, ...}; instances: {instance_id: state}.
    Returns a list of verdicts {node_id, pool_says, instance_says, verdict, reason}."""
    out = []
    for node in pool_nodes or []:
        nid = node.get("id") or ""
        pool_says = node.get("lifecycle-state") or "?"
        inst = instances.get(nid, ABSENT) if nid else ABSENT
        if inst in DEAD or inst == ABSENT:
            verdict, reason = "phantom", f"instance is {inst}"
        else:
            verdict, reason = "keep", f"instance is {inst}"
        out.append(
            {
                "node_id": nid,
                "pool_says": pool_says,
                "instance_says": inst,
                "verdict": verdict,
                "reason": reason,
            }
        )
    return out


def phantoms(verdicts):
    return [v for v in verdicts if v["verdict"] == "phantom"]


def render(pool_name, pool_id, verdicts):
    lines = [f"pool {pool_name} ({pool_id}) nodes={len(verdicts)}"]
    if not verdicts:
        lines.append("  (empty pool)")
        return "\n".join(lines)
    lines.append(f"  {'node id':<48} {'pool says':<12} {'instance says':<14} verdict")
    for v in verdicts:
        lines.append(
            f"  {v['node_id']:<48} {v['pool_says']:<12} {v['instance_says']:<14} {v['verdict']}"
        )
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pools", required=True, help="json: [{id,name,nodes:[...]}]")
    ap.add_argument("--instances", required=True, help="json: {instance_id: state}")
    ap.add_argument("--ids-out", required=True)
    a = ap.parse_args(argv)
    pools = json.load(open(a.pools))
    instances = json.load(open(a.instances))
    todo = []
    for p in pools:
        vs = classify(p.get("nodes") or [], instances)
        print(render(p.get("name") or "?", p["id"], vs))
        todo += [f"{p['id']} {v['node_id']}" for v in phantoms(vs) if v["node_id"]]
    open(a.ids_out, "w").write("".join(t + "\n" for t in todo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
