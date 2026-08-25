"""`sb` subcommands for the shadow layer, registered through the plug-in
hook in sovereign/cli.py:

  sb branch  --task ... [--runner R] [--repo P] [--budget N] [--branches N] [--json]
  sb distill --task-class C [--no-train] [--json]
  sb preauth --session-id S --remaining N --costs a,b,c [--json]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from sovereign import config


def _emit(obj: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(obj, indent=2, sort_keys=True, default=str))
    else:
        for k, v in obj.items():
            print(f"{k}: {v}")


def cmd_branch(args: argparse.Namespace) -> int:
    from sovereign.shadow import branching

    budget_resolved = config.get("budget.default", cli_value=args.budget)
    if budget_resolved.value is None:
        print("budget required", file=sys.stderr)
        return config.CLI_EXIT_USAGE_ERROR
    res = asyncio.run(
        branching.start_on_estate(
            args.task, runner=args.runner, repo=args.repo, budget=int(budget_resolved.value), count=args.branches
        )
    )
    _emit(res, args.json)
    return 0


def cmd_distill(args: argparse.Namespace) -> int:
    from sovereign.shadow import distill

    res = distill.run(args.task_class, do_train=not args.no_train)
    res.pop("receipt", None)
    _emit(res, args.json)
    return 0


def cmd_preauth(args: argparse.Namespace) -> int:
    from sovereign.shadow import preauth

    costs = [int(c) for c in str(args.costs).split(",") if c.strip()]
    session = preauth.Session(args.session_id, int(args.remaining), costs)
    verdict = session.plan(args.op)
    out: dict[str, Any] = {"session_id": session.session_id, "status": session.status, "asking": session.asking}
    if isinstance(verdict, preauth.ShadowAuth):
        out.update({"verdict": "shadow_auth", "confidence": verdict.confidence, "refill": verdict.boundary.refill})
    elif isinstance(verdict, preauth.Ask):
        out.update({"verdict": "ask", "reason": verdict.reason})
    else:
        out["verdict"] = "no_boundary"
    _emit(out, args.json)
    return 0


def register(sub: Any) -> None:
    p = sub.add_parser("branch", help="R19 -- fork N silent Temporal child sessions on git branches and merge the winner")
    p.add_argument("--task", required=True)
    p.add_argument("--runner", default=config.get("runner.default").value)
    p.add_argument("--repo", default=None)
    p.add_argument("--budget", type=int, default=None)
    p.add_argument("--branches", type=int, default=None, help="default: config branch.count")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_branch)

    p = sub.add_parser("distill", help="R18/R20 -- train, grade and route one task class on a measured number")
    p.add_argument("--task-class", required=True, dest="task_class")
    p.add_argument("--no-train", action="store_true", help="grade and route without running the LoRA job")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_distill)

    p = sub.add_parser("preauth", help="R10/R21 -- run the shadow planning loop over predicted step costs")
    p.add_argument("--session-id", required=True, dest="session_id")
    p.add_argument("--remaining", type=int, required=True)
    p.add_argument("--costs", required=True, help="comma-separated predicted tokens per step")
    p.add_argument("--op", default=None, help="the op the next step asks for, if not a budget boundary")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_preauth)
