"""The binding half of ADR 0046: a verified artifact is bound to a commit by a receipt.

WHAT THIS IS. The executable half of "0046 -- NSVEE verification is enforced at the commit
boundary". NSVEE is the verifier (`nsvee/engine.py`); this module is the BINDING: what a
receipt must contain, how a receipt is validated, and which surfaces of the estate must enforce
it. It is deliberately deterministic -- no network, no model, no clock -- because a gate that
can only fail when the model is happy is not a gate.

THE RECEIPT. A receipt says: this tree, at this commit, was verified, and here is the evidence.

    {
      "schema": "estate.nsvee.receipt/1",
      "commit": "<40 hex>",
      "artifact_digest": "<64 hex>",
      "verifier": "nsvee",
      "status": "VERIFIED",
      "report": {...},
      "oracle": "..."
    }

Only VERIFIED passes. HUMAN_INPUT_REQUIRED, EXHAUSTED, SANDBOX_DEGRADED and FORMALIZATION_ERROR
are the gate FAILING, and a missing receipt is a failure too -- the gate fails closed.

WHY THE RECEIPT IS NOT COMMITTED. A receipt that names the commit it describes cannot live
inside that commit: adding the file changes the tree, which changes the sha, which invalidates
the receipt. So the receipt travels with the CI run for that commit, and the merge gate reads it
from the run.

THE CHECKER. `python3 platform/estate/nsvee_enforcement.py --check` reports, per surface,
whether the estate enforces the receipt, and exits 1 naming the surfaces that do not. It exits 1
today: ADR 0046 is the contract, and the enforcement lands in phases (see the ADR). A checker
that cannot fail is not a checker.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = "estate.nsvee.receipt/1"
PASSING_STATUS = "VERIFIED"

#: Every terminal status `nsvee/engine.py` can put in a `PipelineReport`. Only PASSING_STATUS
#: is a pass; the rest are the gate failing.
STATUSES = (
    "VERIFIED",
    "HUMAN_INPUT_REQUIRED",
    "EXHAUSTED",
    "SANDBOX_DEGRADED",
    "FORMALIZATION_ERROR",
)

REQUIRED_FIELDS = ("schema", "commit", "artifact_digest", "verifier", "status")
OPTIONAL_FIELDS = ("report", "oracle", "created_at", "tool_version")

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ReceiptError(ValueError):
    """A receipt that does not bind what it claims to bind."""


@dataclass(frozen=True)
class Surface:
    """One place in the estate where the receipt has to be enforced.

    `markers` are the strings a real implementation of this surface must contain. They are a
    coarse detector on purpose: the checker's job is to say "this surface does not enforce the
    receipt yet", not to parse somebody's shell. They are deliberately distinctive -- a marker
    that a file happens to contain by accident (the word "receipt" alone was in `ci.yml` for
    unrelated reasons) would report a surface as enforced that enforces nothing, which is worse
    than reporting nothing.
    """

    id: str
    path: str
    markers: tuple[str, ...]
    why: str


#: The surfaces ADR 0046 names. The ADR carries the same list in a machine-readable block, and
#: `tests/test_nsvee_estate_enforcement.py` proves the two never drift.
SURFACES: tuple[Surface, ...] = (
    Surface(
        id="pre-commit",
        path=".githooks/pre-commit",
        markers=("nsvee_enforcement",),
        why="the early refusal: a change that cannot be verified is caught before it is a commit",
    ),
    Surface(
        id="ci-verification",
        path=".github/workflows/verifier.yml",
        markers=("nsvee_enforcement", "receipt"),
        why="the verification run: it verifies the tree and publishes the receipt for the commit",
    ),
    Surface(
        id="merge-gate",
        path=".github/workflows/ci.yml",
        markers=("nsvee_enforcement", "receipt"),
        why="the mandatory bound: main takes a commit only when that commit carries a receipt",
    ),
)


def file_digest(path: Path) -> str:
    """sha256 of one file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(root: Path, paths: list[str] | None = None) -> str:
    """sha256 over a tree: every path, sorted, with the sha256 of its bytes.

    `paths` restricts the digest to the changed files (the artifact under verification); with
    `paths=None` the whole tree is digested. Either way the digest changes if a byte changes,
    which is what makes it a binding and not a decoration.
    """
    root = Path(root)
    if paths is None:
        files = sorted(
            p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts
        )
    else:
        files = sorted(root / p for p in paths)
    digest = hashlib.sha256()
    for file in files:
        rel = file.relative_to(root).as_posix()
        digest.update(rel.encode())
        digest.update(b"\0")
        digest.update(file_digest(file).encode())
        digest.update(b"\n")
    return digest.hexdigest()


def validate_receipt(receipt: Any, *, commit: str | None = None) -> dict:
    """Return the receipt if it binds what it claims, else raise ReceiptError.

    `commit`, when given, is the commit the receipt is being checked against: a receipt for a
    different commit is a receipt for someone else's work, and it fails.
    """
    if not isinstance(receipt, dict):
        raise ReceiptError(f"a receipt is an object, not {type(receipt).__name__}")
    missing = [f for f in REQUIRED_FIELDS if f not in receipt]
    if missing:
        raise ReceiptError(f"receipt is missing {', '.join(missing)}")
    if receipt["schema"] != SCHEMA:
        raise ReceiptError(
            f"unknown receipt schema {receipt['schema']!r}, expected {SCHEMA!r}"
        )
    if not _HEX40.match(str(receipt["commit"])):
        raise ReceiptError(f"commit {receipt['commit']!r} is not a 40-hex sha")
    if not _HEX64.match(str(receipt["artifact_digest"])):
        raise ReceiptError(
            f"artifact_digest {receipt['artifact_digest']!r} is not a 64-hex sha256"
        )
    if not str(receipt["verifier"]).strip():
        raise ReceiptError("receipt names no verifier")
    status = receipt["status"]
    if status not in STATUSES:
        raise ReceiptError(
            f"status {status!r} is not an NSVEE terminal status ({', '.join(STATUSES)})"
        )
    if status != PASSING_STATUS:
        raise ReceiptError(
            f"status {status} is not a pass: a receipt binds only a {PASSING_STATUS} artifact"
        )
    if commit is not None and receipt["commit"] != commit:
        raise ReceiptError(f"receipt is for commit {receipt['commit']}, not {commit}")
    return receipt


def check_receipt_against_tree(receipt: Any, tree: Path) -> str:
    """Bind a receipt to the tree it claims to describe.

    `validate_receipt` proves a receipt is well formed. This proves it is TRUE of this tree: the
    digest inside the receipt must be the digest of the tree at the named commit. A receipt that
    is well formed but describes an older tree is worse than no receipt, because it looks like a
    proof.
    """
    validate_receipt(receipt)
    actual = tree_digest(tree)
    if receipt["artifact_digest"] != actual:
        raise ReceiptError(
            "the receipt does not describe this tree: "
            f"receipt says {receipt['artifact_digest']}, this tree is {actual}"
        )
    return actual


def check_surfaces(repo_root: Path) -> list[dict]:
    """Report, per surface, whether the estate enforces the receipt there."""
    repo_root = Path(repo_root)
    report: list[dict] = []
    for surface in SURFACES:
        path = repo_root / surface.path
        found: list[str] = []
        absent: list[str] = []
        if path.is_file():
            text = path.read_text(errors="replace").lower()
            for marker in surface.markers:
                (found if marker.lower() in text else absent).append(marker)
        else:
            absent = list(surface.markers)
        report.append(
            {
                "id": surface.id,
                "path": surface.path,
                "present": path.is_file() and not absent,
                "found": found,
                "absent": absent,
                "why": surface.why,
            }
        )
    return report


def check_enforcement(repo_root: Path) -> dict:
    """The whole enforcement state: every surface, and whether any of them is missing."""
    surfaces = check_surfaces(repo_root)
    missing = [s["id"] for s in surfaces if not s["present"]]
    return {
        "ok": not missing,
        "missing": missing,
        "surfaces": surfaces,
    }


def _read_receipt(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ReceiptError(f"{path} is not JSON: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    repo_root = Path(__file__).resolve().parents[2]

    if "--print-contract" in argv:
        print(
            json.dumps({"schema": SCHEMA, "required": list(REQUIRED_FIELDS)}, indent=2)
        )
        return 0

    if "--receipt" in argv:
        i = argv.index("--receipt")
        if i + 1 >= len(argv):
            print("nsvee-enforcement: --receipt needs a file", file=sys.stderr)
            return 2
        receipt_path = Path(argv[i + 1])
        commit = None
        if "--commit" in argv:
            commit = argv[argv.index("--commit") + 1]
        try:
            receipt = validate_receipt(_read_receipt(receipt_path), commit=commit)
        except ReceiptError as exc:
            print(f"nsvee-enforcement: receipt refused: {exc}", file=sys.stderr)
            return 1
        print(
            f"nsvee-enforcement: receipt ok commit={receipt['commit']} "
            f"status={receipt['status']} digest={receipt['artifact_digest'][:12]}"
        )
        return 0

    if "--verify-receipt" in argv:
        i = argv.index("--verify-receipt")
        if i + 1 >= len(argv):
            print("nsvee-enforcement: --verify-receipt needs a file", file=sys.stderr)
            return 2
        receipt_path = Path(argv[i + 1])
        tree = Path(argv[argv.index("--tree") + 1]) if "--tree" in argv else repo_root
        try:
            receipt = validate_receipt(_read_receipt(receipt_path))
            digest = check_receipt_against_tree(receipt, tree)
        except ReceiptError as exc:
            print(f"nsvee-enforcement: receipt refused: {exc}", file=sys.stderr)
            return 1
        print(
            f"nsvee-enforcement: receipt ok commit={receipt['commit']} digest={digest[:12]}"
        )
        return 0

    state = check_enforcement(repo_root)
    for surface in state["surfaces"]:
        mark = "ok  " if surface["present"] else "MISS"
        detail = (
            f"markers {','.join(surface['found'])}"
            if surface["present"]
            else f"missing {','.join(surface['absent'])}"
        )
        print(f"{mark} {surface['id']:<16} {surface['path']}  ({detail})")
        print(f"     why: {surface['why']}")
    if state["ok"]:
        print("nsvee-enforcement: every surface enforces the receipt")
        return 0
    print(
        "nsvee-enforcement: the receipt is not enforced at: "
        + ", ".join(state["missing"]),
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
