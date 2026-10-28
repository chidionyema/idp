import argparse, json, sys
from .core import Ledger, Refused
from .policy import authorize, compare


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Estate stewardship: evidence, delegated authority, verification"
    )
    p.add_argument("--db", default="output/stewardship.sqlite3")
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("record")
    a.add_argument("case")
    a.add_argument("kind")
    a.add_argument("--actor", required=True)
    a.add_argument("--payload", required=True)
    a.add_argument("--classification", default="internal")
    a = sub.add_parser("cases")
    a = sub.add_parser("events")
    a.add_argument("case")
    a.add_argument("--clearance", default="internal")
    sub.add_parser("verify")
    a = sub.add_parser("authorize")
    a.add_argument("change")
    a.add_argument("policy")
    a = sub.add_parser("compare")
    a.add_argument("before")
    a.add_argument("after")
    args = p.parse_args(argv)
    try:
        if args.command == "authorize":
            d = authorize(json.load(open(args.change)), json.load(open(args.policy)))
            print(json.dumps(d.__dict__, indent=2))
            return 0 if d.allowed else 3
        if args.command == "compare":
            print(
                json.dumps(
                    compare(json.load(open(args.before)), json.load(open(args.after))),
                    indent=2,
                )
            )
            return 0
        ledger = Ledger(args.db)
        if args.command == "record":
            result = ledger.append(
                args.case,
                args.kind,
                args.actor,
                json.loads(args.payload),
                args.classification,
            )
        elif args.command == "cases":
            result = ledger.cases()
        elif args.command == "events":
            result = ledger.events(args.case, args.clearance)
        else:
            result = {"chain_valid": ledger.verify()}
        print(json.dumps(result, indent=2))
        return 0 if args.command != "verify" or result["chain_valid"] else 4
    except (Refused, ValueError, OSError) as e:
        print("REFUSED: " + str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
