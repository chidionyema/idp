#!/usr/bin/env python3
"""Print the Optimus bound for the genesis v1 harness's protected-path set.

Declared in catalog/optimus-metrics.json as harness.protected_paths_covered and measured from
main by the Greenlane, never from what an author says. Plan door: declare_plan is held.
"""

import pathlib
import re

SRC = pathlib.Path(__file__).resolve().parents[1] / "src" / "tools.rs"


def main() -> int:
    try:
        text = SRC.read_text()
    except OSError:
        print("optimus.harness.protected_paths_covered=0")
        return 0
    m = re.search(r"PROTECTED_PATH_PREFIXES[^=]*=\s*&\[(.*?)\];", text, re.S)
    count = len(re.findall(r'"[^"]+"', m.group(1))) if m else 0
    print(f"optimus.harness.protected_paths_covered={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
