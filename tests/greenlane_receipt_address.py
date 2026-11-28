#!/usr/bin/env python3
"""Reading for optimus.greenlane.receipt_404_per_tick (idp#8773).

WHY. Measured 2026-11-28, run 46137784537: one Greenlane tick logged ten receipts refused
with HTTP 404 at `repos//issues//comments` or `repos/chidionyema/issues/idp/<n>`, about 130 s
of a 197 s tick, and those lanes never left verifying. `report_operational` built the address
from `_claim_of`, which answers `(owner/repo, number)`: joining on "/" and turning the FIRST
"/" into "#" moved the repo into the number, so every address it built was one GitHub cannot
route.

WHAT IS MEASURED. The shipped `greenlane/github.py` is loaded and `report_operational` is
called for a tick's worth of receipts (ten by default, the number the 2026-11-28 tick
reported). `gh api` is replaced by a stand-in that routes exactly like GitHub's REST API:
`repos/<owner>/<repo>/issues/<n>/comments` is accepted, anything else answers 404 and raises
the same RuntimeError a refused `gh api` raises. The reading is the number of receipts that
got a 404 -- the defect itself, not a proxy for it.

    10  a tick's receipts land on an address GitHub cannot route (main before idp#8773)
     0  every receipt reaches `repos/<owner>/<repo>/issues/<n>/comments`
    exit 2, nothing on stdout
       the engine cannot be loaded here, so no receipt was judged: a broken measurement is
       BLIND, never a 0 that reads as a verdict

    python3 tests/greenlane_receipt_address.py
        -> optimus.greenlane.receipt_404_per_tick=0
    python3 tests/greenlane_receipt_address.py --engine /tmp/github-before-8773.py
        -> optimus.greenlane.receipt_404_per_tick=10   (the falsifier: main's pre-fix engine)
"""

from __future__ import annotations

import importlib
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "greenlane" / "github.py"
NAME = "optimus.greenlane.receipt_404_per_tick"
TICK = 10

# GitHub's own routing for the two writes `report_operational` makes.
COMMENT = re.compile(r"^repos/[^/]+/[^/]+/issues/[0-9]+/comments$")
LABELS = re.compile(r"^repos/[^/]+/[^/]+/issues/[0-9]+/labels$")


def _load(engine: Path | None):
    """Import `greenlane.github` from a copy of the package, optionally with another engine."""
    tmp = Path(tempfile.mkdtemp(prefix="greenlane-engine-"))
    shutil.copytree(ROOT / "greenlane", tmp / "greenlane")
    if engine is not None:
        shutil.copyfile(engine, tmp / "greenlane" / "github.py")
    sys.path.insert(0, str(tmp))
    for name in [
        n for n in sys.modules if n == "greenlane" or n.startswith("greenlane.")
    ]:
        del sys.modules[name]
    return importlib.import_module("greenlane.github")


def reading(engine: Path | None = None) -> int:
    """How many receipts in one tick land on an address GitHub answers with 404."""
    gh = _load(engine)
    refused: dict[str, int] = {"comments": 0, "labels": 0, "other": 0}

    def fake_run(*args, **_kwargs):
        path = (
            str(args[-1]) if args and str(args[0]) == "gh" else " ".join(map(str, args))
        )
        for arg in args:
            if str(arg).startswith("repos/"):
                path = str(arg)
                break
        if COMMENT.match(path):
            return ""
        if LABELS.match(path):
            refused["labels"] += 1
            return ""
        refused["comments" if path.endswith("/comments") else "other"] += 1
        # `gh api` on a path GitHub cannot route exits non-zero; _run turns that into this.
        raise RuntimeError(f"gh api {path} -> HTTP 404: Not Found")

    gh._run = fake_run
    # A head whose commit names a claim: the address must come from `_claim_of`, which is
    # exactly the code path the tick used.
    gh.GitHubBackend._claim_of = lambda self, head: ("chidionyema/idp", "8773")
    backend = object.__new__(gh.GitHubBackend)
    backend.repo = "chidionyema/idp"
    for i in range(TICK):
        backend.report_operational(
            f"lane/measured-{i}",
            {
                "head": "%040d" % i,
                "batch": "b6503",
                "tip": "%040d" % i,
            },
            "pass" if i % 2 else "fail",
            f"measured receipt {i}",
        )
    return refused["comments"]


def main() -> int:
    engine = None
    if "--engine" in sys.argv:
        engine = Path(sys.argv[sys.argv.index("--engine") + 1]).resolve()
        if not engine.is_file():
            print(f"BLIND {NAME}: --engine {engine} is not a file", file=sys.stderr)
            return 2
    try:
        count = reading(engine)
    except Exception as exc:  # noqa: BLE001 -- any load failure is BLIND, never a 0
        print(f"BLIND {NAME}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(f"{NAME}={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
