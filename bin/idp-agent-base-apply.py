#!/usr/bin/env python3
"""Apply a sealed cloud-agent patch at the exact commit it was made against.

Trusted submit-lane stage only. A busy main cannot discard a successful agent
execution: apply its patch at its own ancestor, then let the existing Greenlane
perform the independently checked rebase and landing. No force-push, no merge,
no model-authored self-attestation, no alternative queue or state database.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from verify_three_proofs import verify_proof_2_boundary_and_gate

SHA = re.compile(r"[0-9a-f]{40}\Z")
MAX_PATCH_BYTES = 4 * 1024 * 1024


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], capture_output=True, check=check)


def policy_digest() -> str:
    # Read the trusted policy before moving the checkout to the agent's base.
    own = Path(__file__).resolve()
    return hashlib.sha256(
        own.read_bytes() + b"\0" + own.with_name("verify_three_proofs.py").read_bytes()
    ).hexdigest()


def validate_scope(base: str, paths: list[str]) -> None:
    if not SHA.fullmatch(base):
        raise ValueError("BLIND: scope base is not one 40-digit SHA")
    if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
        raise ValueError("BLIND: scope paths must be a JSON string array")
    for path in paths:
        if (
            not path
            or any(c in path for c in ("\\", ":", ","))
            or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in path)
            or any(
                part.casefold() in ("", ".", "..", ".git") for part in path.split("/")
            )
        ):
            raise ValueError("REFUSED: noncanonical repository path")
    if len(paths) != len(set(paths)):
        raise ValueError("REFUSED: duplicate scope paths")
    prohibited = [
        p
        for p in paths
        if p in (".github", ".githooks") or p.startswith((".github/", ".githooks/"))
    ]
    if prohibited:
        raise ValueError(
            "REFUSED: untrusted agent patch modifies protected paths: "
            + ", ".join(prohibited[:8])
        )
    ok, proof = verify_proof_2_boundary_and_gate(base, paths, False)
    if not ok:
        raise ValueError(proof["error"])


def admit(paths: list[str]) -> dict:
    base = git("rev-parse", "HEAD").stdout.decode().strip()
    if git("status", "--porcelain").stdout:
        raise ValueError("BLIND: trusted admission checkout is not clean")
    validate_scope(base, paths)
    return {"base": base, "paths": sorted(paths), "policy_sha256": policy_digest()}


def load_scope(base: str, scope_file: Path, expected_digest: str) -> set[str]:
    raw = scope_file.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_digest:
        raise ValueError("REFUSED: trusted scope digest mismatch")
    scope = json.loads(raw)
    if not isinstance(scope, dict) or set(scope) != {"base", "paths", "policy_sha256"}:
        raise ValueError("BLIND: invalid scope envelope")
    if scope["base"] != base or scope["policy_sha256"] != policy_digest():
        raise ValueError("REFUSED: scope base or policy changed")
    validate_scope(base, scope["paths"])
    return set(scope["paths"])


def apply(
    base_file: Path,
    patch_file: Path,
    scope_file: Path | None = None,
    expected_digest: str | None = None,
) -> dict:
    base = base_file.read_text(encoding="ascii").strip()
    if not SHA.fullmatch(base):
        raise ValueError("BLIND: sealed agent base is not one 40-digit SHA")
    if not patch_file.is_file() or not 0 < patch_file.stat().st_size <= MAX_PATCH_BYTES:
        raise ValueError("BLIND: sealed patch missing, empty or over 4 MiB")
    if git("status", "--porcelain").stdout:
        raise ValueError("BLIND: trusted checkout is not clean")
    main = git("rev-parse", "origin/main").stdout.decode().strip()
    if git("cat-file", "-e", f"{base}^{{commit}}", check=False).returncode:
        raise ValueError("BLIND: agent base commit is not fetchable")
    if git("merge-base", "--is-ancestor", base, main, check=False).returncode:
        raise ValueError("BLIND: agent base does not belong to current main history")
    allowed = None
    if scope_file is not None or expected_digest is not None:
        if scope_file is None or expected_digest is None:
            raise ValueError(
                "BLIND: both trusted scope and trusted digest are required"
            )
        allowed = load_scope(base, scope_file, expected_digest)
    # The trusted checkout may be far ahead of the agent's source snapshot.
    # Reconstruct at the exact recorded base; do NOT edit the sealed patch
    # or try to make it apply by changing the expected outcome.
    git("checkout", "--detach", "--quiet", base)
    result = subprocess.run(
        ["git", "apply", "--index", "--3way", str(patch_file.resolve())],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise ValueError(
            "BLIND: sealed patch does not apply to its declared base: "
            + result.stderr.strip()[:240]
        )
    paths = [
        p
        for p in git("diff", "--cached", "--name-only", "--no-renames", "-z", "HEAD")
        .stdout.decode("utf-8", errors="strict")
        .split("\0")
        if p
    ]
    if not paths:
        raise ValueError("BLIND: sealed patch produced zero staged changes")
    validate_scope(base, paths)
    if allowed is not None and not set(paths).issubset(allowed):
        raise ValueError("REFUSED: staged delta exceeds admitted scope")
    staged = git("diff", "--cached", "--binary", "HEAD").stdout
    return {
        "decision": "STAGED_FOR_GREENLANE_NOT_LANDED",
        "agent_base": base,
        "trusted_main_at_submission": main,
        "changed_files": paths,
        "staged_sha256": hashlib.sha256(staged).hexdigest(),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-file", type=Path)
    ap.add_argument("--patch", type=Path)
    ap.add_argument("--admit-paths-json")
    ap.add_argument("--scope-file", type=Path)
    ap.add_argument("--scope-sha256")
    args = ap.parse_args()
    try:
        if args.admit_paths_json is not None:
            if any(
                v is not None
                for v in (
                    args.base_file,
                    args.patch,
                    args.scope_file,
                    args.scope_sha256,
                )
            ):
                raise ValueError("BLIND: admission and submission are separate")
            result = admit(json.loads(args.admit_paths_json))
        else:
            if args.base_file is None or args.patch is None:
                raise ValueError("BLIND: base and patch required")
            result = apply(
                args.base_file, args.patch, args.scope_file, args.scope_sha256
            )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
