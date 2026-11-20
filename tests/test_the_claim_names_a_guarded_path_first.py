"""A guarded path is named when the claim is opened, not after the build.

2026-11-19: claims were taken, work was built, and the refusal arrived from
bin/verify_three_proofs.py at commit time -- too late to choose different work.
"""

from __future__ import annotations

import importlib.machinery as M
import importlib.util as U
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def claim_open():
    p = REPO / "bin" / "claim-open"
    ld = M.SourceFileLoader("claim_open_under_test", str(p))
    mod = U.module_from_spec(U.spec_from_loader("claim_open_under_test", ld))
    ld.exec_module(mod)
    return mod


def test_a_guarded_path_is_named():
    m = claim_open()
    assert m.guarded_hits([".github/workflows/ci.yml", "bin/x"]) == [
        ".github/workflows/ci.yml"
    ]


def test_an_ordinary_path_is_not():
    m = claim_open()
    assert m.guarded_hits(["bin/x", "tests/test_y.py", "docs/a.md"]) == []
