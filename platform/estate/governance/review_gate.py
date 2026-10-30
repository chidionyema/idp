#!/usr/bin/env python3
"""review_gate.py -- the decision core of the forced-review gate.

THE GATE, IN ONE SENTENCE.
A change that touches a founder surface or a critical service does not land unless a review
receipt exists for that exact commit, and the receipt says the review passed.

WHY THIS IS A DECISION CORE AND NOT A SCRIPT.
The estate already has a review engine: `platform/estate/intents/code-review.yaml` runs the four
tier pipeline (T0 lint, T1 heuristics, T2 LLM, T3 deterministic verification). Writing a second
review engine here would be the stitching the estate laws forbid. So this module decides one
thing only -- *is this change allowed to land without a passing review?* -- and consumes the
engine's output as a receipt.

THE FAIL-CLOSED RULE, STATED AS THE INVENTORY OF UNKNOWNS.
Every way of not knowing is a refusal, never a pass:

  * the base ref does not resolve            -> refuse
  * the changed-file set cannot be computed  -> refuse
  * the inventory is missing or unreadable   -> refuse
  * a guarded path is touched and there is
    no receipt                               -> refuse
  * the receipt is for a different commit    -> refuse (replay)
  * the receipt is for a different base      -> refuse (the review covered other changes)
  * the receipt is malformed                 -> refuse
  * the receipt's digest does not match      -> refuse (it was edited after the fact)
  * the receipt says "pass" but carries a
    high, critical or verified finding       -> refuse (the receipt contradicts itself)

The last one is the anti-lie check, and it is the reason the receipt carries counts instead of
just a word.

WHAT IS NOT IN HERE, AND WHY.
  * no network, no credentials, no executor access -- the gate reads a repository and a file.
  * no second review implementation -- the four tier pipeline is the engine.
  * no mutable policy: the inventory is read from the BASE ref, so a change cannot weaken the
    list of guarded paths in the same change that touches them.

USAGE
    python3 platform/estate/governance/review_gate.py --base origin/main [--head HEAD]
                                                             [--receipt <path>]
    exit 0 = the change may land; exit 1 = refused.

The module is import-safe and side-effect free: `decide()` returns a Decision and prints
nothing; `main()` is the CLI wrapper.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

INVENTORY_PATH = "platform/estate/governance/founder-surfaces.yaml"
RECEIPT_SCHEMA = "estate.review-receipt.v1"
DEFAULT_RECEIPT_DIR = Path(
    os.environ.get("ESTATE_REVIEW_RECEIPTS")
    or (Path.home() / ".estate/review/receipts")
)
# Findings that make a "pass" impossible. Medium and low are advisory; high and critical are not.
BLOCKING_SEVERITIES = ("critical", "high")


class GateError(RuntimeError):
    """Anything the gate cannot decide. Every GateError is a refusal, never a pass."""


# --------------------------------------------------------------------------------------
# The inventory
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Surface:
    id: str
    kind: str
    reason: str
    paths: Tuple[str, ...]


@dataclass(frozen=True)
class Inventory:
    version: int
    surfaces: Tuple[Surface, ...]

    def match(self, path: str) -> Optional[Surface]:
        """The first surface that claims this path, or None.

        A pattern matches an exact path, a directory prefix, or a glob. `dir/**` matches
        everything under `dir`; `dir` matches `dir` and everything under it.
        """
        for surface in self.surfaces:
            for pattern in surface.paths:
                if _pattern_matches(pattern, path):
                    return surface
        return None


def _pattern_matches(pattern: str, path: str) -> bool:
    pattern = pattern.rstrip("/")
    if pattern.endswith("/**"):
        prefix = pattern[:-3].rstrip("/")
        return path == prefix or path.startswith(prefix + "/")
    if pattern == path:
        return True
    if fnmatch.fnmatch(path, pattern):
        return True
    # A pattern naming a directory claims everything under it.
    if "/" not in pattern and not any(ch in pattern for ch in "*?["):
        return path.startswith(pattern + "/")
    if not any(ch in pattern for ch in "*?["):
        return path.startswith(pattern.rstrip("/") + "/")
    return False


def parse_inventory(text: str) -> Inventory:
    """Parse the inventory YAML. A malformed inventory is an error, not an empty inventory."""
    try:
        import yaml  # type: ignore
    except (
        Exception
    ) as exc:  # pragma: no cover - PyYAML is a hard dependency of the estate
        raise GateError(
            f"PyYAML is not importable, so the inventory cannot be read: {exc}"
        ) from exc
    try:
        raw = yaml.safe_load(text)
    except Exception as exc:
        raise GateError(f"the inventory is not valid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise GateError("the inventory is not a mapping")
    surfaces = raw.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        raise GateError("the inventory declares no surfaces")
    parsed: List[Surface] = []
    for entry in surfaces:
        if not isinstance(entry, dict):
            raise GateError("an inventory entry is not a mapping")
        sid = str(entry.get("id") or "").strip()
        kind = str(entry.get("kind") or "").strip()
        paths = entry.get("paths")
        if not sid:
            raise GateError("an inventory entry has no id")
        if kind not in ("founder_surface", "critical_service"):
            raise GateError(f"inventory entry '{sid}' has an unknown kind '{kind}'")
        if not isinstance(paths, list) or not paths:
            raise GateError(f"inventory entry '{sid}' declares no paths")
        parsed.append(
            Surface(
                id=sid,
                kind=kind,
                reason=str(entry.get("reason") or "").strip(),
                paths=tuple(str(p) for p in paths),
            )
        )
    return Inventory(version=int(raw.get("version") or 1), surfaces=tuple(parsed))


# --------------------------------------------------------------------------------------
# Git facts
# --------------------------------------------------------------------------------------


def _git(root: Path, args: Sequence[str]) -> str:
    # The argv is fixed by this module: the git executable is resolved once, and every argument
    # is a literal this module wrote. No caller string ever reaches this call.
    git = shutil.which("git")
    if not git:
        raise GateError("git is not on PATH, so no repository fact can be established")
    proc = subprocess.run(  # noqa: S603 - fixed argv, no shell, git resolved to an absolute path
        [git, *args], cwd=str(root), capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        raise GateError(
            f"git {' '.join(args)} failed ({proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}"
        )
    return proc.stdout


def resolve_commit(root: Path, ref: str) -> str:
    out = _git(root, ["rev-parse", "--verify", f"{ref}^{{commit}}"]).strip()
    if not out:
        raise GateError(f"cannot resolve '{ref}' to a commit")
    return out


def merge_base(root: Path, base_ref: str, head: str) -> str:
    out = _git(root, ["merge-base", base_ref, head]).strip()
    if not out:
        raise GateError(f"cannot compute the merge base of '{base_ref}' and '{head}'")
    return out


def changed_paths(root: Path, base: str, head: str) -> List[str]:
    out = _git(root, ["diff", "--name-only", f"{base}...{head}"])
    return [line.strip() for line in out.splitlines() if line.strip()]


def load_inventory(root: Path, base_ref: str) -> Inventory:
    """The inventory is read from the BASE ref, never from the tree under judgement."""
    text = _git(root, ["show", f"{base_ref}:{INVENTORY_PATH}"])
    return parse_inventory(text)


# --------------------------------------------------------------------------------------
# The receipt
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Receipt:
    schema: str
    sha: str
    base: str
    verdict: str
    tiers: Tuple[str, ...]
    findings: Dict[str, int]
    verified: int
    generated_at: str
    digest: str


def receipt_digest(payload: Dict[str, Any]) -> str:
    """The digest covers every field except the digest itself."""
    body = {k: v for k, v in payload.items() if k != "digest"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_receipt(text: str) -> Receipt:
    try:
        raw = json.loads(text)
    except Exception as exc:
        raise GateError(f"the receipt is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise GateError("the receipt is not an object")
    schema = str(raw.get("schema") or "")
    if schema != RECEIPT_SCHEMA:
        raise GateError(
            f"the receipt schema is '{schema}', expected '{RECEIPT_SCHEMA}'"
        )
    for field_name in ("sha", "base", "verdict", "digest"):
        if not str(raw.get(field_name) or "").strip():
            raise GateError(f"the receipt has no '{field_name}'")
    verdict = str(raw.get("verdict")).strip().lower()
    if verdict not in ("pass", "fail"):
        raise GateError(f"the receipt verdict '{verdict}' is neither pass nor fail")
    findings = raw.get("findings") or {}
    if not isinstance(findings, dict):
        raise GateError("the receipt findings are not a mapping")
    tiers = raw.get("tiers") or []
    if not isinstance(tiers, list):
        raise GateError("the receipt tiers are not a list")
    return Receipt(
        schema=schema,
        sha=str(raw["sha"]).strip(),
        base=str(raw["base"]).strip(),
        verdict=verdict,
        tiers=tuple(str(t) for t in tiers),
        findings={str(k): int(v) for k, v in findings.items()},
        verified=int(raw.get("verified") or 0),
        generated_at=str(raw.get("generated_at") or "").strip(),
        digest=str(raw["digest"]).strip(),
    )


def verify_receipt(
    receipt: Receipt, expected_sha: str, expected_base: str
) -> Optional[str]:
    """Return None when the receipt is acceptable, or the reason it is not."""
    if receipt.sha != expected_sha:
        return (
            f"the receipt is for commit {receipt.sha[:12]}, not the commit under judgement "
            f"{expected_sha[:12]}; a review of one commit is not a review of another"
        )
    if receipt.base != expected_base:
        return (
            f"the receipt was taken against base {receipt.base[:12]}, not "
            f"{expected_base[:12]}; it covered different changes"
        )
    # The canonical payload is rebuilt from the parsed fields, so the digest is recomputed from
    # the values the gate actually read, not from whatever the file happened to contain.
    payload = {
        "schema": receipt.schema,
        "sha": receipt.sha,
        "base": receipt.base,
        "verdict": receipt.verdict,
        "tiers": list(receipt.tiers),
        "findings": receipt.findings,
        "verified": receipt.verified,
        "generated_at": receipt.generated_at,
    }
    if receipt_digest(payload) != receipt.digest:
        return "the receipt digest does not match its contents; it was edited after it was written"
    if receipt.verdict == "fail":
        return "the review receipt records a failing review"
    blocking = {s: receipt.findings.get(s, 0) for s in BLOCKING_SEVERITIES}
    if any(v > 0 for v in blocking.values()):
        return "the receipt claims to pass but carries blocking findings " + ", ".join(
            f"{k}={v}" for k, v in blocking.items() if v
        )
    if receipt.verified > 0:
        return (
            f"the receipt claims to pass but Tier 3 verified {receipt.verified} finding(s); "
            "a verified finding is a real finding"
        )
    return None


# --------------------------------------------------------------------------------------
# The decision
# --------------------------------------------------------------------------------------


@dataclass
class Decision:
    verdict: str  # "pass" or "refuse"
    reason: str
    head: str = ""
    base: str = ""
    matched: List[Dict[str, str]] = field(default_factory=list)
    changed: List[str] = field(default_factory=list)


def decide(
    root: Path,
    base_ref: str = "origin/main",
    head_ref: str = "HEAD",
    receipt_text: Optional[str] = None,
) -> Decision:
    """Decide whether the change may land. Every unknown is a refusal."""
    root = Path(root)
    try:
        head = resolve_commit(root, head_ref)
        base = merge_base(root, base_ref, head)
        inventory = load_inventory(root, base_ref)
        changed = changed_paths(root, base, head)
    except GateError as exc:
        return Decision(verdict="refuse", reason=str(exc))

    matched: List[Dict[str, str]] = []
    for path in changed:
        surface = inventory.match(path)
        if surface is not None:
            matched.append({"path": path, "surface": surface.id, "kind": surface.kind})

    if not matched:
        return Decision(
            verdict="pass",
            reason="no founder surface or critical service is touched",
            head=head,
            base=base,
            changed=changed,
        )

    if receipt_text is None:
        return Decision(
            verdict="refuse",
            reason=(
                "the change touches "
                + ", ".join(sorted({m["surface"] for m in matched}))
                + " and no review receipt was supplied"
            ),
            head=head,
            base=base,
            matched=matched,
            changed=changed,
        )

    try:
        receipt = parse_receipt(receipt_text)
    except GateError as exc:
        return Decision(
            verdict="refuse",
            reason=f"the review receipt is unusable: {exc}",
            head=head,
            base=base,
            matched=matched,
            changed=changed,
        )

    problem = verify_receipt(receipt, head, base)
    if problem:
        return Decision(
            verdict="refuse",
            reason=problem,
            head=head,
            base=base,
            matched=matched,
            changed=changed,
        )

    return Decision(
        verdict="pass",
        reason=(
            "a passing review receipt covers "
            + ", ".join(sorted({m["surface"] for m in matched}))
        ),
        head=head,
        base=base,
        matched=matched,
        changed=changed,
    )


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


def _read_receipt(args: argparse.Namespace, head: str) -> Optional[str]:
    if args.receipt:
        path = Path(args.receipt)
        if not path.exists():
            raise GateError(f"the receipt file '{path}' does not exist")
        return path.read_text(encoding="utf-8")
    candidate = DEFAULT_RECEIPT_DIR / f"{head}.json"
    if candidate.exists():
        return candidate.read_text(encoding="utf-8")
    return None


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Fail-closed forced-review gate")
    parser.add_argument(
        "--base", default="origin/main", help="the base ref (default: origin/main)"
    )
    parser.add_argument("--head", default="HEAD", help="the commit under judgement")
    parser.add_argument(
        "--receipt",
        default=None,
        help="path to a review receipt JSON (default: <receipts dir>/<head sha>.json)",
    )
    parser.add_argument("--root", default=None, help="repository root (default: cwd)")
    args = parser.parse_args(list(argv) if argv is not None else None)

    root = Path(args.root) if args.root else Path.cwd()
    try:
        head = resolve_commit(root, args.head)
        receipt_text = _read_receipt(args, head)
    except GateError as exc:
        print(f"FAIL  review-gate  {exc}")
        return 1

    decision = decide(
        root, base_ref=args.base, head_ref=args.head, receipt_text=receipt_text
    )

    if decision.verdict == "pass":
        print(f"ok    review-gate  {decision.reason}")
        for match in decision.matched:
            print(
                f"      reviewed      {match['kind']} {match['surface']} -- {match['path']}"
            )
        return 0

    print(f"FAIL  review-gate  {decision.reason}")
    for match in decision.matched:
        print(
            f"      guarded       {match['kind']} {match['surface']} -- {match['path']}"
        )
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
