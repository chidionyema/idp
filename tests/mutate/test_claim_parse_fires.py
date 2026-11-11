"""DBG-035 falsifier-of-the-falsifier, kept in the tree so it can be re-run by anyone.

The falsifier asserts the shipped gate CANNOT parse the `instruction=`/`plan=` claim shape.
If that assertion would still pass after the gate was fixed, it grades nothing.

So: copy the gate to a throwaway path, fix the CLAIM regex in the copy, point the test at it
via CLAIM_GATE_PATH, and require the test to go RED. The mutant is EXECUTED, not described.

Exit contract:
  0  FIRES        -- the test accepts the shipped gate and rejects the repaired one
  1  SURVIVED     -- the test still passes against the fix; it grades nothing
  2  BLIND        -- the mutant could not be built or run, so nothing was proved
A crash is exit 2. It is never reported as FIRES: "fired" means an observed difference.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GATE = REPO / "bin" / "claim-gate"
TEST = "tests/test_claim_parse_never_reports_absence.py"

EXIT_OK = 0
EXIT_DISQUALIFIED = 1
EXIT_BLIND = 2

# The repair DBG-035 asks for: allow instruction=/plan= (and any other key=value) between
# agent= and paths=, so a newer claim-open's output parses.
UNFIXED = re.compile(r"agent=\(\?P<agent>\\S\+\)\\s\+\(\?:model=\\S\+\\s\+\)\?paths=")
REPAIRED = r"agent=(?P<agent>\\S+)\\s+(?:(?:model|instruction|plan)=\\S+\\s+)*paths="


def run_pytest(env_extra: dict[str, str]) -> tuple[int, str]:
    p = subprocess.run(
        [sys.executable, "-m", "pytest", TEST, "-q", "-p", "no:warnings"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=280,
        env={**os.environ, **env_extra},
    )
    return p.returncode, p.stdout + p.stderr


def main() -> int:
    if not GATE.exists():
        print(f"BLIND: {GATE} missing")
        return EXIT_BLIND

    src = GATE.read_text()
    fixed, n = UNFIXED.subn(REPAIRED, src)
    if n == 0:
        print(
            "BLIND: the CLAIM regex was not found in the gate, so no mutant was produced. "
            "A mutation that applies nowhere proves nothing."
        )
        return EXIT_BLIND

    with tempfile.TemporaryDirectory() as td:
        mutant = Path(td) / "claim-gate"
        mutant.write_text(fixed)

        real_rc, real_out = run_pytest({})
        if real_rc != EXIT_OK:
            print("BLIND: the falsifier does not pass against the REAL gate:")
            print(real_out[-1500:])
            return EXIT_BLIND

        mut_rc, mut_out = run_pytest({"CLAIM_GATE_PATH": str(mutant)})

    if mut_rc == EXIT_OK:
        print("MUTANT SURVIVED: the test passes against a gate whose regex parses the")
        print("extended claim shape -- it is not grading the defect it names.")
        print(mut_out[-1500:])
        return EXIT_DISQUALIFIED

    print("FIRES: the falsifier accepts the shipped gate and rejects the repaired one.")
    print(f"  shipped gate : exit {real_rc}")
    print(f"  repaired gate: exit {mut_rc}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
