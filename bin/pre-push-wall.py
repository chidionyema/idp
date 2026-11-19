#!/usr/bin/env python3
"""pre-push-wall -- I-8107: one wall, six gates, identical at pre-push and in CI.

The founder, 2026-11-19: CI is the last stand, not the front line. Every gate that runs in
GitHub Actions runs from THIS executable in .git/hooks/pre-push, so a refusal happens before a
byte leaves the worktree.

GATES
  1. zero-advisory-ci         fails on any `continue-on-error: true` in .github/workflows
  2. darwin-thin-client       fails on added launchctl / LaunchAgents / LaunchDaemons / plistlib
                              / ~/.estate lines outside docs and this gate's own tests
  3. strict-intent-schema     requires .ci/intent-manifest.json, schema_strict true,
                              existing_assets_checked true, non-empty failure_modes_mapped
  4. differential-falsifier   runs bin/idp-differential-falsifier against .ci/proof-receipt.json:
                              base_exit_code != 0, head_exit_code == 0, >=1 mutation killed
  5. shadow-scope-integrity   refuses shadow-verify.yml that reads pull_request.base.sha with
                              no git-merge-base fallback (the silent skipped-matrix green)
  6. yield-first-moratorium   while the deploy pipeline is red, refuses changes that only touch
                              cage/ docs/ or catalog/ (governance without execution yield)

Every gate emits one JSONL record (stage, gate_id, exit_code, duration_ms, detail, advisory:false)
to .ci/ci-microscope.jsonl. The records are POSTed to the Genesis surface when
GENESIS_SURFACE_INGEST_URL and GENESIS_SURFACE_TOKEN are set; when they are not, the sink says
BLIND instead of pretending the surface was fed.

USAGE
  bin/pre-push-wall.py pre-push [base_ref]
  bin/pre-push-wall.py ci       [base_ref]
Exit 1 if any gate refuses.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess  # noqa: S404 - every call below is a constant argv, no shell
import sys
import time
import urllib.request

DARWIN_FORBIDDEN = (
    r"\blaunchctl\b",
    r"Library/LaunchAgents",
    r"Library/LaunchDaemons",
    r"\bplistlib\b",
    r"~/\.estate/",
)
META_PREFIXES = ("cage/", "docs/", "catalog/")
TELEMETRY = pathlib.Path(".ci") / "ci-microscope.jsonl"


def git(repo: pathlib.Path, *argv: str) -> str:
    return subprocess.check_output(  # noqa: S603 - constant argv, no shell
        ["/usr/bin/git", *argv], cwd=repo, text=True, stderr=subprocess.DEVNULL
    )


def emit(stage: str, gate_id: str, rc: int, ms: int, detail: str) -> dict:
    TELEMETRY.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "gate_id": gate_id,
        "stage": stage,
        "advisory": False,
        "exit_code": rc,
        "duration_ms": ms,
        "detail": detail[:400],
    }
    with TELEMETRY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
    return rec


class Refused(Exception):
    """A gate refused. The message is the refusal, not a stack trace."""


def changed(repo: pathlib.Path, base: str) -> list[str]:
    out = git(repo, "diff", "--name-only", f"{base}...HEAD")
    return [line for line in out.splitlines() if line.strip()]


def gate_zero_advisory(repo: pathlib.Path) -> str:
    wf = repo / ".github" / "workflows"
    hits = []
    if wf.exists():
        for f in sorted(wf.glob("*.y*ml")):
            for n, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
                if re.search(r"^\s*continue-on-error:\s*true\b", line):
                    hits.append(f"{f.relative_to(repo)}:{n}")
    if hits:
        raise Refused(f"ADVISORY_GATE_FORBIDDEN: {', '.join(hits[:6])}")
    return "0 advisory continue-on-error gates"


def gate_darwin(repo: pathlib.Path, base: str) -> str:
    diff = git(
        repo,
        "diff",
        "--unified=0",
        f"{base}...HEAD",
        "--",
        ":(exclude)docs/",
        ":(exclude)bin/pre-push-wall.py",
        ":(exclude)tests/test_i8107_zero_divergence_certification.py",
    )
    hits = []
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added = line[1:]
            for pat in DARWIN_FORBIDDEN:
                if re.search(pat, added):
                    hits.append(f"{pat} -> {added.strip()[:70]}")
    if hits:
        raise Refused(f"DARWIN_THIN_CLIENT_VIOLATION: {'; '.join(hits[:4])}")
    return "0 Zone A / launchd regressions"


def gate_intent(repo: pathlib.Path) -> str:
    manifest = repo / ".ci" / "intent-manifest.json"
    if not manifest.exists():
        raise Refused("MISSING_INTENT_MANIFEST: .ci/intent-manifest.json required")
    data = json.loads(manifest.read_text())
    required = {
        "instruction_id",
        "owner",
        "target_subsystems",
        "failure_modes_mapped",
        "existing_assets_checked",
        "schema_strict",
    }
    missing = required - set(data)
    if missing:
        raise Refused(f"LOOSE_MANIFEST_SCHEMA: missing {sorted(missing)}")
    if data.get("schema_strict") is not True:
        raise Refused("LOOSE_SCHEMA_FORBIDDEN: schema_strict must be true")
    if data.get("existing_assets_checked") is not True:
        raise Refused("EXISTING_ASSETS_UNCHECKED: existing_assets_checked must be true")
    if not data.get("failure_modes_mapped"):
        raise Refused("UNMAPPED_FAILURE_MODES: failure_modes_mapped is empty")
    return f"intent={data['instruction_id']} modes={len(data['failure_modes_mapped'])}"


def gate_falsifier(repo: pathlib.Path, base: str) -> str:
    gate = repo / "bin" / "idp-differential-falsifier"
    if not gate.exists():
        raise Refused("MISSING_PROOF_GATE: bin/idp-differential-falsifier not found")
    p = subprocess.run(  # noqa: S603 - constant argv, no shell
        [sys.executable, str(gate), base, str(repo / ".ci" / "proof-receipt.json")],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if p.returncode != 0:
        raise Refused((p.stdout or p.stderr).strip()[:400])
    return p.stdout.strip()[:200]


def gate_shadow_scope(repo: pathlib.Path) -> str:
    wf = repo / ".github" / "workflows" / "shadow-verify.yml"
    if not wf.exists():
        return "no shadow-verify workflow"
    text = wf.read_text(errors="replace")
    if "github.event.pull_request.base.sha" in text and "merge-base" not in text:
        raise Refused(
            "SHADOW_DISPATCH_BUG: pull_request.base.sha with no merge-base fallback"
        )
    return "shadow scope has a merge-base fallback"


def gate_moratorium(repo: pathlib.Path, base: str) -> str:
    red = os.environ.get("ESTATE_DEPLOY_PIPELINE_RED", "false").lower() == "true"
    labels = {
        s.strip() for s in os.environ.get("PR_LABELS", "").split(",") if s.strip()
    }
    if not red or "P0-DEPLOY-UNBLOCK" in labels:
        return "moratorium clear"
    blocked = [p for p in changed(repo, base) if p.startswith(META_PREFIXES)]
    if blocked:
        raise Refused(
            f"FC_GOVERNANCE_WITHOUT_EXECUTION_YIELD: deploy is red and this change only touches "
            f"{blocked[:4]}"
        )
    return "0 blocked meta paths"


def publish(records: list[dict]) -> None:
    url = os.environ.get("GENESIS_SURFACE_INGEST_URL", "").strip()
    token = os.environ.get("GENESIS_SURFACE_TOKEN", "").strip()
    if not url or not token:
        print("[SINK] genesis-surface: BLIND (GENESIS_SURFACE_INGEST_URL/TOKEN unset)")
        return
    req = urllib.request.Request(  # noqa: S310 - scheme is the operator's own https endpoint
        url,
        data=json.dumps({"records": records}).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        # one HTTP emit; a hang must not outlive the payload
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            print(f"[SINK] genesis-surface: HTTP {resp.status}")
    except OSError as exc:
        print(f"[SINK] genesis-surface: BLIND {exc}")


def main() -> int:
    stage = sys.argv[1] if len(sys.argv) > 1 else "pre-push"
    base = sys.argv[2] if len(sys.argv) > 2 else "origin/main"
    repo = pathlib.Path.cwd()
    gates = [
        ("zero-advisory-ci", lambda: gate_zero_advisory(repo)),
        ("darwin-thin-client", lambda: gate_darwin(repo, base)),
        ("strict-intent-schema", lambda: gate_intent(repo)),
        ("differential-falsifier", lambda: gate_falsifier(repo, base)),
        ("shadow-scope-integrity", lambda: gate_shadow_scope(repo)),
        ("yield-first-moratorium", lambda: gate_moratorium(repo, base)),
    ]
    records, failed = [], False
    for gate_id, fn in gates:
        t0 = time.monotonic()
        try:
            detail = fn()
            ms = int((time.monotonic() - t0) * 1000)
            records.append(emit(stage, gate_id, 0, ms, detail))
            print(f"[PASS] {gate_id:<24} ({ms:>4}ms) {detail}")
        except Refused as exc:
            ms = int((time.monotonic() - t0) * 1000)
            records.append(emit(stage, gate_id, 1, ms, str(exc)))
            print(f"[FAIL] {gate_id:<24} ({ms:>4}ms) {exc}", file=sys.stderr)
            failed = True
        except (OSError, ValueError, KeyError) as exc:
            ms = int((time.monotonic() - t0) * 1000)
            records.append(emit(stage, gate_id, 1, ms, f"{type(exc).__name__}: {exc}"))
            print(
                f"[FAIL] {gate_id:<24} ({ms:>4}ms) {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
            failed = True
    publish(records)
    print(f"=== {stage}: {'ALL 6 GATES PASS' if not failed else 'REFUSED'} ===")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
