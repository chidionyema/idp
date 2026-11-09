"""Advisory Ferrari planning through the estate's *existing* Jev decision layer.

This module does not choose GitHub's required checks. It reuses Jev impact
analysis + pre-push risk and emits a conservative plan. Missing model, invalid
input, or an escalated decision runs ALL configured impacted suites. The same
mandatory trusted checks remain required even for "low" risk.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SHA = re.compile(r"^[0-9a-f]{40}$")


def load_jev():
    path = ROOT / "mcp/plugins/jev.py"
    spec = importlib.util.spec_from_file_location("idp_ferrari_jev", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Jev layer source is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def required_checks(path: Path | None = None) -> list[str]:
    file = path or ROOT / "platform/github/ruleset.idp.required-checks.json"
    spec = json.loads(file.read_text(encoding="utf-8"))
    rules = [
        r
        for r in spec.get("rules", [])
        if isinstance(r, dict) and r.get("type") == "required_status_checks"
    ]
    if len(rules) != 1:
        raise ValueError("canonical required-context policy absent/ambiguous")
    checks = rules[0]["parameters"]["required_status_checks"]
    names = [c["context"] for c in checks]
    if not names or any(not isinstance(n, str) or not n for n in names):
        raise ValueError("invalid required contexts")
    return names


def consolidate(
    affected: dict[str, Any], risk: dict[str, Any], mandatory: list[str]
) -> dict:
    tasks = affected.get("tasks")
    if not isinstance(tasks, list) or any(
        not isinstance(t, dict) or not isinstance(t.get("name"), str) for t in tasks
    ):
        raise ValueError("Jev impact decision is not well-formed")
    uncertain = any(
        [
            affected.get("escalated"),
            affected.get("config_error"),
            affected.get("diff_error"),
            risk.get("escalated"),
            risk.get("config_error"),
            risk.get("diff_error"),
            risk.get("tier") not in ("low", "medium", "high"),
            any(t.get("probability") is None and not t.get("run") for t in tasks),
        ]
    )
    # Model scores are suggestions. An uncertain decision has no waiver authority.
    chosen = [t["name"] for t in tasks if uncertain or t.get("run") is True]
    return {
        "advisory_risk": risk.get("tier") if not uncertain else "UNKNOWN",
        "jev_state": "ESCALATED" if uncertain else "ASSESSED",
        "impacted_tasks": sorted(set(chosen)),
        "mandatory_required_checks": sorted(set(mandatory)),
        "authorizes_merge": False,
        "admission_rule": "all mandatory contexts remain required at the exact source SHA",
        "reason": "Jev uncertain: conservative full suite"
        if uncertain
        else "Jev impact plan; mandatory protections unchanged",
    }


def plan(repo: Path, base: str, head: str) -> dict:
    if not SHA.fullmatch(base) or not SHA.fullmatch(head):
        raise ValueError("exact 40-char base/head required")
    actual = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    ).stdout.strip()
    if actual != head:
        raise ValueError("Jev plan must match the exact checked-out candidate HEAD")
    mandatory = required_checks()
    try:
        jev = load_jev()
        affected = jev.jev_affected(str(repo), base, None)
        risk = jev.jev_pr_risk(str(repo), base)
        return {"base": base, "head": head, **consolidate(affected, risk, mandatory)}
    except Exception as error:
        # An unavailable decision layer NEVER downgrades a change to low risk.
        return {
            "base": base,
            "head": head,
            "advisory_risk": "UNKNOWN",
            "jev_state": "BLIND",
            "impacted_tasks": ["ALL_CONFIGURED"],
            "mandatory_required_checks": mandatory,
            "authorizes_merge": False,
            "reason": f"Jev unavailable: {type(error).__name__}; run full suite",
        }


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=str(ROOT))
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    args = ap.parse_args()
    print(json.dumps(plan(Path(args.repo), args.base, args.head), sort_keys=True))


if __name__ == "__main__":
    main()
