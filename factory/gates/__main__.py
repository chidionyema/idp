import sys
import importlib
import os


def main(argv):
    if len(argv) < 2:
        return 2
    gate_id = argv[1]
    if os.environ.get("NO_NETWORK") != "1":
        print("refused: sandbox requires NO_NETWORK=1", file=sys.stderr)
        return 3
    try:
        mod = importlib.import_module("factory.gates." + gate_id.replace(".", "_"))
    except ImportError:
        print(f"gate not found: {gate_id}", file=sys.stderr)
        return 4
    return int(mod.run())


if __name__ == "__main__":
    sys.exit(main(sys.argv))
