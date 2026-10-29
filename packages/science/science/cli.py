import argparse, json, sys
from .core import Registry


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="output/science.sqlite3")
    s = p.add_subparsers(dest="command", required=True)
    x = s.add_parser("register")
    x.add_argument("protocol")
    x = s.add_parser("show")
    x.add_argument("id")
    x = s.add_parser("transition")
    x.add_argument("id")
    x.add_argument("state")
    x.add_argument("receipt")
    x = s.add_parser("append")
    x.add_argument("id")
    x.add_argument("kind")
    x.add_argument("payload")
    x = s.add_parser("events")
    x.add_argument("id")
    a = p.parse_args()
    r = Registry(a.db)
    try:
        if a.command == "register":
            result = r.register(json.load(open(a.protocol)))
        elif a.command == "show":
            result = r.get(a.id)
        elif a.command == "transition":
            result = {"state": r.transition(a.id, a.state, json.load(open(a.receipt)))}
        elif a.command == "append":
            result = r.append(a.id, a.kind, json.load(open(a.payload)))
        else:
            result = r.events(a.id)
        print(json.dumps(result, indent=2))
    except (ValueError, KeyError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
