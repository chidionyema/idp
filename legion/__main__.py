"""python -m legion — validate | proof | scorecard."""

from __future__ import annotations

import argparse
import json
import sys

from .manifest import ManifestError, load_manifest, validate
from .proof import run_proof, verify_chain
from .scorecard import ScorecardError, build_scoreboard


def _cmd_validate(args: argparse.Namespace) -> int:
    try:
        manifest = load_manifest(args.manifest)
    except (ManifestError, FileNotFoundError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    errors = validate(manifest)
    if errors:
        for e in errors:
            print(f"INVALID: {e}", file=sys.stderr)
        return 1
    print(f"VALID: {manifest.get('name')} (legion {manifest.get('legion')})")
    return 0


def _cmd_proof(args: argparse.Namespace) -> int:
    if args.verify:
        problems = verify_chain(args.manifest)
        if problems:
            for p in problems:
                print(f"CHAIN-BROKEN: {p}", file=sys.stderr)
            return 1
        print("CHAIN-OK")
        return 0
    record = run_proof(args.manifest)
    state = "PROOF-OK" if record["ok"] else "PROOF-FAILED"
    print(
        f"{state}: {record['legion']} exit={record['exit']} {record['duration_ms']}ms"
    )
    return 0 if record["ok"] else 1


def _cmd_scorecard(args: argparse.Namespace) -> int:
    weights = None
    if args.weights:
        try:
            weights = json.loads(args.weights)
        except json.JSONDecodeError as exc:
            print(f"bad --weights JSON: {exc}", file=sys.stderr)
            return 1
    try:
        board = build_scoreboard(args.metrics_dir, weights)
    except ScorecardError as exc:
        print(f"SCORECARD-ERROR: {exc}", file=sys.stderr)
        return 1
    text = json.dumps(board, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="legion")
    sub = parser.add_subparsers(dest="cmd", required=True)

    pv = sub.add_parser("validate", help="validate a legion manifest")
    pv.add_argument("manifest")
    pv.set_defaults(fn=_cmd_validate)

    pp = sub.add_parser("proof", help="run a legion's proof command (chained evidence)")
    pp.add_argument("manifest", help="legion manifest, or chain file with --verify")
    pp.add_argument(
        "--verify", action="store_true", help="verify a proof chain instead"
    )
    pp.set_defaults(fn=_cmd_proof)

    ps = sub.add_parser("scorecard", help="compute the legion scoreboard")
    ps.add_argument("metrics_dir")
    ps.add_argument("--weights", help="JSON object overriding default weights")
    ps.add_argument("--out", help="write scoreboard JSON here instead of stdout")
    ps.set_defaults(fn=_cmd_scorecard)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
