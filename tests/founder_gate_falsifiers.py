"""Optimus measure: founder_gate.falsifiers_declared.

Prints `optimus.founder_gate.falsifiers_declared=<n>`: the number of test functions declared
in tests/test_estate_founder_gate.py, the falsifiers of the founder admission gate (bin/estate-founder-gate): a FAILED or ACTION
message with no `Exhausted:` receipt is refused; a receipt that is not in the ledger is refused; a
receipt replayed for another instruction is refused; DONE is admitted without one. 0 when the file is
absent.

It COUNTS declared tests; it does not run them. That they pass is proved by the Greenlane
running tests/. Read this number as "the falsifier set exists and has not shrunk", never as
"the gate is operating": an operating gate refuses a real unproven handback on the send path.

Stdlib only.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SUITE = ROOT / "tests" / "test_estate_founder_gate.py"
# `def test_...` at the start of a line: not a mention in a comment or a string.
TEST_DEF = re.compile(r"^def test_\w+\(", re.MULTILINE)


def declared_falsifiers(suite: pathlib.Path = SUITE) -> int:
    if not suite.is_file():
        return 0
    return len(TEST_DEF.findall(suite.read_text(encoding="utf-8", errors="replace")))


def main() -> int:
    print(f"optimus.founder_gate.falsifiers_declared={declared_falsifiers()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
