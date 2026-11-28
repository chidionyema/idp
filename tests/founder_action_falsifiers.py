"""Optimus measure: founder_action.falsifiers_declared.

Prints `optimus.founder_action.falsifiers_declared=<n>`: the number of test functions declared
in tests/test_founder_action_buttons.py, the falsifiers of the founder-action door (one message
with buttons; a tap counts only from the founder's chat; unknown decision, unknown key, other
chat and repeat taps record nothing; an action without proof is refused). 0 when the file is
absent.

It COUNTS declared tests; it does not run them. That they pass is proved by the Greenlane
running tests/. Read this number as "the falsifier set exists and has not shrunk", never as
"the door is operating": an operating door is a real tap recorded from the founder's phone.

Stdlib only.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SUITE = ROOT / "tests" / "test_founder_action_buttons.py"
# `def test_...` at the start of a line: not a mention in a comment or a string.
TEST_DEF = re.compile(r"^def test_\w+\(", re.MULTILINE)


def declared_falsifiers(suite: pathlib.Path = SUITE) -> int:
    if not suite.is_file():
        return 0
    return len(TEST_DEF.findall(suite.read_text(encoding="utf-8", errors="replace")))


def main() -> int:
    print(f"optimus.founder_action.falsifiers_declared={declared_falsifiers()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
