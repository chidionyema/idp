"""The law gate: the registry, the runner, the falsifier, and the audit for what is missing.

WHAT THE FOUNDER ASKED FOR (2026-10-29): "my laws need to be gated", "every session must be
looking for flaws or unenforced laws and gates", "a gate that cannot fail is not a gate",
"any tiny flow where cosmetic or technical we not letting in", "CI is too loose".

THE REGISTRY. laws.yaml holds the laws the founder has stated, each with the machine decision
that decides it and a falsifier: a known-bad fixture the check MUST reject. specs.yaml holds
the founder's specs, each with the proof command that decides it.

THE RUNNER. For every law:

    verdict  = run the check
    falsifier = run the check against a known-bad fixture; it MUST fail

A law whose check passes but whose falsifier also passes is not a gate: the law is reported
as UNENFORCED and blocks. That is R2 from AGENTS.md section 9, made executable.

THE AUDIT. Every session must hunt for the flaws, so the audit is part of the gate's output:

    prose-only laws   a LAW the founder's own documents state, with no executable check
    unfalsified gates a registered law with no falsifier: it cannot be proven to fail
    advisory gates    a CI job that continues on error

SPEC STATUS. A spec is done when its proof exits zero, and not before. The status command
reports every spec with its acceptance criteria, its proof and the proof's exit status.
"""

from __future__ import annotations

import os
import re
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from . import checks

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LAWS_FILE = os.path.join(HERE, "laws.yaml")
SPECS_FILE = os.path.join(HERE, "specs.yaml")

AGENTS_FILES = [
    "AGENTS.md",
    "docs/AGENTS.md",
    "platform/AGENTS.md",
    "platform/estate/AGENTS.md",
]


def _load(path: str) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError:
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def laws() -> List[Dict[str, Any]]:
    rows = (_load(LAWS_FILE).get("laws") or [])
    return [r for r in rows if isinstance(r, dict)]


def specs() -> List[Dict[str, Any]]:
    rows = (_load(SPECS_FILE).get("specs") or [])
    return [r for r in rows if isinstance(r, dict)]


def component_map() -> Dict[str, str]:
    """path pattern -> the spec id that governs it, for the spec-trace check."""
    out: Dict[str, str] = {}
    for row in specs():
        component = row.get("component")
        if not component:
            continue
        out[str(component)] = str(row.get("id", ""))
    return out


# --- running one law ---------------------------------------------------------------------------


def run_falsifier(law: Dict[str, Any], root: str = REPO_ROOT) -> Tuple[bool, str]:
    """Run the law's falsifier. It must FAIL: a falsifier that passes proves nothing.

    The falsifier is a check plus the fixture files that make it fail. The fixture is written
    into a temporary tree and the check runs there, so the real repository is never touched.
    """
    falsifier = law.get("falsifier")
    if not falsifier:
        return False, f"law {law.get('id')} has no falsifier: it cannot be proven to fail"
    fixture = falsifier.get("files") or {}
    spec = falsifier.get("check")
    if not spec:
        return False, f"law {law.get('id')} has a falsifier with no check"
    with tempfile.TemporaryDirectory(prefix="law-falsifier-") as tmp:
        for name, content in fixture.items():
            path = os.path.join(tmp, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        ok, detail = checks.run_check(tmp, spec)
    if ok:
        return False, (
            f"law {law.get('id')} cannot fail: its falsifier passed ({detail}). "
            "A gate that cannot fail is not a gate."
        )
    return True, f"falsifier rejected the known-bad fixture ({detail})"


def evaluate_law(law: Dict[str, Any], root: str = REPO_ROOT) -> Dict[str, Any]:
    """One law, one verdict."""
    law_id = law.get("id", "?")
    severity = law.get("severity", "block")
    spec = law.get("check") or {}
    ok, detail = checks.run_check(root, spec)
    verdict = "pass" if ok else ("fail" if severity == "block" else "warn")
    result: Dict[str, Any] = {
        "id": law_id,
        "law": law.get("law", ""),
        "source": law.get("source", ""),
        "severity": severity,
        "check": spec.get("type", "?"),
        "verdict": verdict,
        "detail": detail,
    }
    if law.get("falsify", True):
        fals_ok, fals_detail = run_falsifier(law, root)
        result["falsifier"] = "pass" if fals_ok else "fail"
        result["falsifier_detail"] = fals_detail
        if not fals_ok:
            result["verdict"] = "fail"
    else:
        result["falsifier"] = "skipped"
    return result


def evaluate_all(root: str = REPO_ROOT) -> Dict[str, Any]:
    """Every law, one verdict each, plus the audit of what is missing."""
    results = [evaluate_law(law, root) for law in laws()]
    failing = [r for r in results if r["verdict"] == "fail"]
    warning = [r for r in results if r["verdict"] == "warn"]
    audit = audit(root)
    return {
        "results": results,
        "failing": failing,
        "warning": warning,
        "audit": audit,
        "ok": not failing,
    }


# --- the audit: what is missing -----------------------------------------------------------------


PROSE_SOURCES = [
    "AGENTS.md",
    "docs/FOUNDER.md",
    "docs/NEXT.md",
    "docs/estate",
    "docs/decisions",
    "docs/specs",
    "platform/estate",
]


def _prose_hits(root: str) -> Dict[str, List[str]]:
    """Every 'LAW n' the estate's own documents state, and where."""
    hits: Dict[str, List[str]] = {}
    try:
        import subprocess  # noqa: S404 - fixed argv

        proc = subprocess.run(  # noqa: S603
            [
                "rg",
                "-o",
                "--no-messages",
                "--no-heading",
                "-g",
                "*.md",
                "LAW [0-9]+",
                *(s for s in PROSE_SOURCES if os.path.exists(os.path.join(root, s))),
            ],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        for line in proc.stdout.splitlines():
            path, _, match = line.partition(":")
            found = re.search(r"LAW\s+(\d+)", match or line)
            if not found:
                continue
            hits.setdefault(f"LAW-{found.group(1)}", []).append(path)
    except Exception:  # noqa: BLE001 - the audit must not depend on rg
        for rel in PROSE_SOURCES:
            base = os.path.join(root, rel)
            paths = (
                [base]
                if os.path.isfile(base)
                else [
                    os.path.join(d, f)
                    for d, _dirs, files in os.walk(base)
                    for f in files
                    if f.endswith(".md")
                ]
                if os.path.isdir(base)
                else []
            )
            for path in paths:
                try:
                    with open(path, encoding="utf-8", errors="replace") as f:
                        text = f.read()
                except OSError:
                    continue
                for match in re.finditer(r"LAW\s+(\d+)", text, re.IGNORECASE):
                    hits.setdefault(f"LAW-{match.group(1)}", []).append(
                        os.path.relpath(path, root)
                    )
    return hits


def prose_laws(root: str = REPO_ROOT) -> List[Dict[str, str]]:
    """The laws the founder's own documents state that no executable check decides."""
    registered = {str(law.get("id", "")).upper() for law in laws()}
    hits = _prose_hits(root)
    out = []
    for law_id, where in hits.items():
        if law_id.upper() in registered:
            continue
        out.append(
            {
                "id": law_id,
                "where": ", ".join(sorted(set(where))[:3]),
                "state": (
                    "prose-only: the estate states it in "
                    f"{len(set(where))} place(s) and no executable check decides it"
                ),
            }
        )
    return sorted(out, key=lambda r: int(r["id"].split("-")[1]))


def unfalsified_laws() -> List[Dict[str, str]]:
    out = []
    for law in laws():
        if not law.get("falsifier"):
            out.append(
                {
                    "id": str(law.get("id", "?")),
                    "state": "no falsifier: this gate cannot be proven to fail",
                }
            )
    return out


def advisory_gates(root: str = REPO_ROOT) -> List[Dict[str, str]]:
    """CI jobs or steps that continue on error: gates that fail open."""
    out = []
    workflows_dir = os.path.join(root, ".github", "workflows")
    if not os.path.isdir(workflows_dir):
        return out
    for name in sorted(os.listdir(workflows_dir)):
        if not name.endswith((".yml", ".yaml")):
            continue
        rel = os.path.join(".github", "workflows", name)
        for row in checks.advisory_gates_in(root, rel):
            out.append(
                {
                    "workflow": row["workflow"],
                    "job": row["job"],
                    "state": f"{row['where']} sets continue-on-error: this gate fails open",
                }
            )
    return out


def audit(root: str = REPO_ROOT) -> Dict[str, Any]:
    """The flaw hunt every session inherits: what is prose, what cannot fail, what fails open."""
    prose = prose_laws(root)
    unfalsified = unfalsified_laws()
    advisory = advisory_gates(root)
    return {
        "prose_only_laws": prose,
        "unfalsified_gates": unfalsified,
        "advisory_gates": advisory,
        "count": len(prose) + len(unfalsified) + len(advisory),
    }


# --- the founder's specs -----------------------------------------------------------------------


def run_proof(spec: Dict[str, Any], root: str = REPO_ROOT) -> Tuple[bool, str]:
    proof = spec.get("proof") or {}
    if proof.get("check"):
        return checks.run_check(root, proof["check"])
    argv = proof.get("argv")
    if argv:
        return checks.check_command(root, {"argv": argv, "cwd": root})
    return False, f"spec {spec.get('id')} has no proof"


def evaluate_spec(spec: Dict[str, Any], root: str = REPO_ROOT) -> Dict[str, Any]:
    ok, detail = run_proof(spec, root)
    return {
        "id": spec.get("id", "?"),
        "title": spec.get("title", ""),
        "component": spec.get("component", ""),
        "source_spec": spec.get("source_spec", ""),
        "acceptance": spec.get("acceptance") or [],
        "status": "done" if ok else "open",
        "proof": detail,
        "state": detail,
    }


def evaluate_specs(root: str = REPO_ROOT) -> Dict[str, Any]:
    rows = [evaluate_spec(spec, root) for spec in specs()]
    open_rows = [r for r in rows if r["status"] != "done"]
    return {
        "specs": rows,
        "open": open_rows,
        "done": [r for r in rows if r["status"] == "done"],
        "ok": not open_rows,
    }
