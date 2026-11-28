#!/usr/bin/env python3
"""Reading for optimus.legion.launch_refusals_named (idp#8772).

WHY. Measured 2026-11-28: runs 46137092198 and 46137271107 both ended `harness exit 2
launcher_refusals=1 files_changed=0`, and the only line was the folded
`REFUSED: provider admission invalid` -- many causes, one sentence, so neither run named which
refusal it was. This reads the shipped launcher on the exact path the cloud executor uses
(`--launch-admitted <record> --session-dir <dir>`), one admission record per refusal cause, and
grades one thing: does every refusal carry a fixed token that names its own class?

    1  every case ends on a line `REFUSED: <TOKEN>`
    0  a case folded its cause into a sentence (main before idp#8772), or ended on a traceback
       instead of a refusal at all -- an unnamed refusal either way
    exit 2, nothing on stdout
       the launcher cannot run in this checkout at all (`--help` fails: a missing interpreter
       module), so no case was judged: a broken measurement is BLIND, never a 0 that reads as
       a verdict

No provider is contacted: every case here refuses before egress.

    python3 tests/legion_launch_refusal_named.py
        -> optimus.legion.launch_refusals_named=1
    python3 tests/legion_launch_refusal_named.py --launcher /tmp/legion-admit-before-8772
        -> optimus.legion.launch_refusals_named=0    (the falsifier: the pre-fix launcher)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADMIT = ROOT / "bin" / "legion-admit"
TOKEN = re.compile(r"^REFUSED: [A-Z][A-Z0-9_]*$")
NAME = "optimus.legion.launch_refusals_named"

# One record per refusal cause the executor can hand the launcher. None of them admits:
# no route at all, and a route whose cost is not proved free at egress.
CASES = {
    "unrouted record": {"decision": "REFUSED"},
    "unproved cost": {
        "route": {"provider": "google", "model": "gemini-3", "billing": "metered"},
        "decision": "ADMITTED",
    },
}


def _run(launcher: Path, argv: list[str], env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(launcher), *argv],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def reading(launcher: Path) -> int:
    """1 when every launch refusal names its own class, 0 when any of them does not."""
    env = {**os.environ, "TASK": "measure a launch refusal"}
    started = _run(launcher, ["--help"], env)
    if started.returncode != 0:
        detail = (started.stderr or "").strip().splitlines()
        print(
            f"BLIND {NAME}: {launcher} cannot run here: "
            + (detail[-1] if detail else "no output")[:200],
            file=sys.stderr,
        )
        raise SystemExit(2)
    with tempfile.TemporaryDirectory(prefix="legion-refusal-") as tmp:
        root = Path(tmp)
        named = 0
        for label, record in CASES.items():
            path = root / f"{label.replace(' ', '-')}.json"
            path.write_text(json.dumps(record))
            run = _run(
                launcher,
                [
                    "--out",
                    str(root / "out"),
                    "--launch-admitted",
                    str(path),
                    "--session-dir",
                    str(root / "session"),
                ],
                env,
            )
            lines = [ln.strip() for ln in (run.stdout or "").splitlines() if ln.strip()]
            ok = bool(lines) and bool(TOKEN.match(lines[-1]))
            print(
                f"  {'NAMED' if ok else 'UNNAMED'}  {label}: "
                + (lines[-1] if lines else "no line printed (traceback on stderr)")
            )
            named += 1 if ok else 0
    return 1 if named == len(CASES) else 0


def main() -> int:
    launcher = ADMIT
    if "--launcher" in sys.argv:
        launcher = Path(sys.argv[sys.argv.index("--launcher") + 1]).resolve()
        if not launcher.is_file():
            print(f"BLIND {NAME}: --launcher {launcher} is not a file", file=sys.stderr)
            return 2
    print(f"{NAME}={reading(launcher)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
