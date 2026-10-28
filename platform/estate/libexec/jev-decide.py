#!/usr/bin/env python3
"""jev-decide -- ask the estate's one decision layer a bounded question, from an intent.

WHY THIS EXISTS. ADR 0030 puts one decision layer in front of every "should I / is this / which
of these" in the estate, and `sovereign/policy.py`'s [jev] block already sets
`force_on_decisions = true`. What was missing is a DOOR every agent already has: an intent. An
agent cannot import `mcp/plugins/jev.py` (the intent rule: an action that is not a YAML intent is
an action the agent cannot take), so without this the layer was only callable from three
hard-coded binaries -- one of which nothing invoked.

WHAT IT RETURNS, and what it does NOT. A typed answer plus `confidence` plus `escalated`:

    jev.decide: decision=True confidence=0.83 escalated=False latency_ms=241
    jev.decide: escalated=True _fallback=jev_unavailable confidence=None
        -- the layer was consulted and could not answer; that is an ESCALATION, not a "no"

It never refuses anything and never exits non-zero on a decision (a decision is not a failure).
Exit 2 is reserved for a usage error. When `escalated` is true the caller must route to human
review or deeper analysis, exactly as ADR 0030's escalation table says -- do not read a null
confidence as evidence for either side.

Every call is recorded in `estate.db jev_decisions` (the Fleet page's database) by the layer
itself, so a decision made here is visible on the board: repo, layer, decision_id, answer,
confidence, escalated, latency.

    jev-decide --question "Is this change safe to land?" --id greenlane.land
    jev-decide --kind choice --question "Which lane?" --options cheap,default \
        --id routing.lane --layer agent
    jev-decide --kind score --question "How risky is this diff?" --levels low,medium,high
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path


def _load_layer(repo: str):
    """Load the layer by path -- the same way bin/idp-affected and bin/idp-pr-risk do."""
    path = Path(repo).expanduser() / "mcp" / "plugins" / "jev.py"
    if not path.is_file():
        raise SystemExit(f"jev-decide: no decision layer at {path}")
    spec = importlib.util.spec_from_file_location("estate_jev_layer", path)
    if not spec or not spec.loader:
        # Never an assert: an assert is stripped under -O, and this is a resolution failure the
        # caller has to see (ruff S101 refused it in the fast gate, 2026-10-18).
        raise SystemExit(f"jev-decide: {path} has no importable loader")
    module = importlib.util.module_from_spec(spec)
    sys.modules["estate_jev_layer"] = module
    spec.loader.exec_module(module)
    return module


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="ask the Jev decision layer one bounded question"
    )
    ap.add_argument(
        "--repo", default=os.environ.get("IDP", str(Path.home() / "Documents/code/idp"))
    )
    ap.add_argument(
        "--layer", default="agent", help="guard|agent|hook|consensus|verifier"
    )
    ap.add_argument(
        "--id", dest="decision_id", required=True, help="names the decision"
    )
    ap.add_argument("--question", required=True)
    ap.add_argument("--kind", default="noul", choices=("noul", "choice", "score"))
    ap.add_argument("--options", default="", help="comma-separated, for --kind choice")
    ap.add_argument("--levels", default="", help="comma-separated, for --kind score")
    ap.add_argument("--threshold", type=float, default=None, help="escalate below this")
    ap.add_argument(
        "--context", default="{}", help="JSON object of evidence; never secrets"
    )
    ap.add_argument(
        "--json", action="store_true", help="full response, machine-readable"
    )
    args = ap.parse_args(argv)

    # The context is validated BEFORE the layer is loaded. A malformed context is a usage error:
    # it must not cost a call, a vendor round trip, or a row in jev_decisions, and it must not
    # be mistakable for an unavailable decision layer (measured 2026-10-27, when a context closed
    # before its last member died deep inside the call and the caller could not tell the two
    # apart). The message never echoes the context -- the context is evidence, and evidence can
    # be sensitive.
    try:
        context = json.loads(args.context)
    except json.JSONDecodeError as exc:
        print(
            f"jev-decide: --context is not JSON: {exc}. "
            'Pass it as a JSON-encoded string, e.g. --context \'{"k":"v"}\'',
            file=sys.stderr,
        )
        return 2
    if not isinstance(context, dict):
        print(
            "jev-decide: --context must be a JSON object, encoded as a string",
            file=sys.stderr,
        )
        return 2

    jev = _load_layer(args.repo)
    threshold = args.threshold if args.threshold is not None else jev.DEFAULT_FLOOR

    if args.kind == "choice":
        options = [o for o in (x.strip() for x in args.options.split(",")) if o]
        if not options:
            print("jev-decide: --kind choice needs --options", file=sys.stderr)
            return 2
        result = jev.jev_choice(
            repo="idp",
            layer=args.layer,
            decision_id=args.decision_id,
            context=context,
            question=args.question,
            options=options,
            required_confidence=threshold,
        )
        answer = result.get("choice")
    elif args.kind == "score":
        levels = [x.strip() for x in args.levels.split(",") if x.strip()]
        if not levels:
            print("jev-decide: --kind score needs --levels", file=sys.stderr)
            return 2
        result = jev.jev_score(
            repo="idp",
            layer=args.layer,
            decision_id=args.decision_id,
            context=context,
            question=args.question,
            levels=levels,
            required_confidence=threshold,
        )
        answer = result.get("level", result.get("score"))
    else:
        result = jev.jev_noul(
            repo="idp",
            layer=args.layer,
            decision_id=args.decision_id,
            context=context,
            question=args.question,
            threshold=threshold,
        )
        answer = result.get("decision")

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    fields = [f"answer={answer}", f"confidence={result.get('confidence')}"]
    if result.get("_fallback"):
        fields.insert(0, f"_fallback={result['_fallback']}")
    fields.append(f"escalated={bool(result.get('escalated'))}")
    if answer is None and bool(result.get("escalated")):
        # ADR 0030: an escalation is not an answer. A null answer with escalated=true means the
        # layer was consulted and could not answer -- it says so on the line, so a caller that
        # reads answer=None cannot mistake the absence of a verdict for a verdict of absence.
        fields.append("route=human_review")
    if result.get("latency_ms") is not None:
        fields.append(f"latency_ms={result['latency_ms']:.0f}")
    print(f"jev.decide[{args.layer}:{args.decision_id}]: " + " ".join(fields))
    return 0


if __name__ == "__main__":
    sys.exit(main())
