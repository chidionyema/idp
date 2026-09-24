#!/usr/bin/env python3
import os
import sys
import json
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from factory.registry import collect, save
from factory.resolver import resolve, Refuse
from factory.exec import run_dag
from factory.surfaces.registry import all_surfaces
from factory import ledger

ROOT = Path(os.environ.get("FACTORY_ROOT", Path.home() / "Documents" / "code"))
REGISTRY = ROOT / "idp" / "registry.json"


def cmd_collect(_):
    reg = collect(ROOT)
    save(reg, REGISTRY)
    print(f"collected {reg['count']} terminals from {reg['repos_seen']} repos")
    if reg["warnings"]:
        print(f"warnings: {len(reg['warnings'])}")
        for w in reg["warnings"][:10]:
            print(f"  {w}")


def cmd_run(_):
    reg = collect(ROOT)
    save(reg, REGISTRY)
    for s in all_surfaces():
        try:
            order = s.intake()
        except Exception as e:
            ledger.write(
                "errors", {"where": "intake", "surface": s.id, "err": str(e)[:200]}
            )
            continue
        if order is None:
            continue
        ledger.write(
            "orders",
            {
                "order_id": order["order_id"],
                "surface": s.id,
                "goal": order["goal"][:200],
            },
        )
        try:
            resolution = resolve(order, reg)
        except Refuse as e:
            ledger.write(
                "errors",
                {"where": "resolve", "order_id": order["order_id"], "err": str(e)},
            )
            s.deliver(order, f"REFUSED: {e}")
            continue
        ledger.write(
            "resolutions",
            {
                "order_id": order["order_id"],
                "resolved": [t["id"] for t in resolution["resolved"]],
                "unresolved": resolution["unresolved"],
                "chain_errors": resolution["chain_errors"],
            },
        )
        if resolution["chain_errors"]:
            print(f"[{s.id}] chain errors: {resolution['chain_errors']}")
            continue
        execution = run_dag(order, resolution["resolved"], ROOT)
        ledger.write(
            "executions",
            {
                "order_id": order["order_id"],
                "outcome": execution["outcome"],
                "runtime": execution["runtime"],
                "steps": len(execution["steps"]),
            },
        )
        final = execution.get("final", {})
        msg = final.get("alert")
        if not msg:
            msg = f"Order {order['order_id']} — {execution['outcome']}"
            if final.get("reason"):
                msg += f": {final['reason']}"
        s.deliver(order, msg)


def cmd_loop(args):
    end = time.time() + args.seconds if args.seconds else None
    while True:
        cmd_run(args)
        for s in all_surfaces():
            try:
                r = s.receipt()
                if r:
                    ledger.write("engagement", r)
            except Exception:
                pass
        if end and time.time() >= end:
            return
        time.sleep(args.interval)


def cmd_ledger(args):
    entries = ledger.read(args.stream)
    print(f"{len(entries)} entries in {args.stream}")
    for e in entries[-args.tail :]:
        print(json.dumps(e))


def main():
    ap = argparse.ArgumentParser(prog="factory")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("collect").set_defaults(fn=cmd_collect)
    sub.add_parser("run").set_defaults(fn=cmd_run)
    p = sub.add_parser("loop")
    p.add_argument("--seconds", type=int, default=0)
    p.add_argument("--interval", type=float, default=2.0)
    p.set_defaults(fn=cmd_loop)
    p = sub.add_parser("ledger")
    p.add_argument("stream")
    p.add_argument("--tail", type=int, default=20)
    p.set_defaults(fn=cmd_ledger)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
