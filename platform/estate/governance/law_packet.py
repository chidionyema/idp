"""Read-only governance/onboarding projection over IDP's existing authoritative sources.

This module DOES NOT grant identity, DoF, execution, approval or completion.
It refuses ambiguous legacy instructions rather than silently choosing their precedence.
The actual law enforcer remains governance.registry and the trusted action doors.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "genesis.governance.onboarding.v1"
LAW_PATH = Path("platform/estate/governance/laws.yaml")
AGENTS_PATH = Path("AGENTS.md")
FOUNDER_JUDGEMENTS_PATH = Path("docs/training/2026-10-30-founder-judgement.md")
WRAPPERS = ("CLAUDE.md", "GEMINI.md", ".agent.md")
# Skill assessments are examples requiring actual independent observed action;
# they cannot issue QUAD/DoF leases or certify operational capability.
DRILL_CATALOG = {
    "J1": ("Memory fallback only supports brief, not recall or remember", "REFUSE_PARTIAL_CONTRACT", "check every original operation through the same trusted door"),
    "J2": ("Multiple agents repeatedly hit the same Greenlane failure", "ELIMINATE_FAILURE_CLASS", "independent regression fails before correction and passes after"),
    "J3": ("Guardian is alive but disk usage is still critical", "VERIFY_GOAL_NOT_HEARTBEAT", "measure disk before and after the actual cleanup effect"),
    "J4": ("Required current runtime observation is missing", "REPORT_BLIND_AND_SCOPE", "restrict only unsafe actions and produce a verified remediation route"),
    "J5": ("Founder surface fails while lower-priority probes are healthy", "PRIORITIZE_FOUNDER_CRITICAL", "source-bound critical-function priority and actual repair yield"),
    "J6": ("A worker is idle while a verified high-priority incident is queued", "ASSIGN_ELIGIBLE_WORKER", "authorized claim and independently verified incident progress"),
    "J7": ("A previously reliable infrastructure assumption becomes false", "REVALIDATE_ASSUMPTION", "current source/observation and a regression detecting drift"),
    "J8": ("Founder manually calculates a repeated delivery metric", "AUTOMATE_MEASUREMENT", "rerunnable source event and independently recomputable value"),
}
LEGACY_COMMANDS = (
    (
        "LEGACY_INTENT_MANDATE",
        re.compile(
            r"(?im)^every action the agent performs goes through an \*\*intent YAML\*\*"
        ),
    ),
    (
        "LEGACY_INTENT_ONLY_RULE",
        re.compile(r"(?im)^\*\*rule: if an action is not a YAML intent"),
    ),
    (
        "LEGACY_INTENT_CREATION",
        re.compile(r"(?im)^to add a new capability: write .*intents/.*\.yaml"),
    ),
    (
        "STATIC_ESTATE_STATUS",
        re.compile(r"(?im)^## 13\. the estate's state right now\s*$"),
    ),
)
STRUCTURAL_CHECKS = frozenset(
    (
        "grep_present",
        "grep_absent",
        "file_exists",
        "file_absent",
        "yaml_key",
        "yaml_key_present",
        "workflow_strict",
    )
)


def _read(root: Path, relative: Path) -> tuple[str, str]:
    """No fallback and no implicit creation if a source is missing."""
    path = root / relative
    # A governance source may never silently dereference an untrusted symlink.
    if path.is_symlink() or any(
        parent.is_symlink()
        for parent in path.parents
        if parent != root and root in parent.parents
    ):
        return "", ""
    try:
        content = path.read_bytes()
        text = content.decode("utf-8")
    except (OSError, UnicodeError):
        return "", ""
    return text, hashlib.sha256(content).hexdigest()


def _active_wrapper(name: str, content: str) -> bool:
    """Harness compatibility is a pointer, never a second policy definition."""
    meaningful = [s.strip() for s in content.splitlines() if s.strip()]
    if name == "CLAUDE.md":
        return meaningful == ["@AGENTS.md"]
    return meaningful in (["@AGENTS.md"], ["See AGENTS.md"])


def _law_rows(raw: str) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    problems: list[dict[str, str]] = []
    try:
        import yaml  # already used by governance.registry; no new service

        data = yaml.safe_load(raw) if raw else None
    except (ImportError, ValueError, TypeError) as exc:
        data = None
        problems.append({"code": "LAW_SOURCE_UNREADABLE", "detail": type(exc).__name__})
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("laws"), list)
        or not data["laws"]
    ):
        problems.append(
            {"code": "LAW_SOURCE_MISSING_OR_EMPTY", "detail": str(LAW_PATH)}
        )
        return [], problems
    out: list[dict[str, Any]] = []
    ids: set[str] = set()
    for i, law in enumerate(data["laws"]):
        if not isinstance(law, dict):
            problems.append({"code": "INVALID_LAW", "detail": str(i)})
            continue
        identifier = law.get("id")
        if not isinstance(identifier, str) or not re.fullmatch(
            r"GOV-[0-9]+", identifier
        ):
            problems.append({"code": "INVALID_LAW_ID", "detail": str(identifier)})
            continue
        if identifier in ids:
            problems.append({"code": "DUPLICATE_LAW_ID", "detail": identifier})
            continue
        ids.add(identifier)
        check = law.get("check") or {}
        falsifier = law.get("falsifier")
        kind = check.get("type", "") if isinstance(check, dict) else ""
        if not kind or not isinstance(falsifier, dict):
            problems.append({"code": "UNDECIDABLE_LAW", "detail": identifier})
        link = law.get("founder_law")
        if link and (
            not isinstance(link, str) or not re.fullmatch(r"LAW-[0-9]+", link)
        ):
            problems.append({"code": "BAD_FOUNDER_LAW_REFERENCE", "detail": identifier})
        # GOV controls are not the original founding constitution. Source strings
        # are provenance *claims* until independently authenticated/ratified.
        out.append(
            {
                "id": identifier,
                "classification": "ESTATE_ENFORCEMENT_CONTROL",
                "founder_law_ref": link if isinstance(link, str) else None,
                "claimed_source": str(law.get("source", "")),
                "issuer_authenticated_by_packet": False,
                "check_type": kind,
                "check_grade": "STRUCTURAL_ONLY"
                if kind in STRUCTURAL_CHECKS
                else "EXECUTION_NOT_RUN",
                "falsifier_declared": isinstance(falsifier, dict),
                "runtime_enforcement_verified": False,
                "training_scenario": "FALSIFY_AT_REAL_EFFECT_DOOR"
                if falsifier
                else "MISSING_FALSIFIER",
            }
        )
    return out, problems


def _training_records(
    root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, str]], str]:
    """Extract founder judgement, retaining exact source provenance.

    This is a *training source*, not a ratified law and not proof that the
    founder personally authenticated every historical line. Every drill
    still requires a separately observed, applicable real action.
    """
    raw, digest = _read(root, FOUNDER_JUDGEMENTS_PATH)
    problems: list[dict[str, str]] = []
    if not raw:
        problems.append({
            "code": "FOUNDER_TRAINING_SOURCE_UNAVAILABLE",
            "detail": str(FOUNDER_JUDGEMENTS_PATH),
        })
        return [], problems, digest

    headers = list(re.finditer(r"(?m)^## J([1-9][0-9]*) -- (.+)$", raw))
    if not headers:
        problems.append({
            "code": "FOUNDER_TRAINING_HAS_NO_JUDGEMENTS",
            "detail": str(FOUNDER_JUDGEMENTS_PATH),
        })
        return [], problems, digest
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, heading in enumerate(headers):
        identifier = "J" + heading.group(1)
        if identifier in seen:
            problems.append({"code": "DUPLICATE_FOUNDER_JUDGEMENT", "detail": identifier})
            continue
        seen.add(identifier)
        end = headers[i + 1].start() if i + 1 < len(headers) else raw.find(
            "\n## ", heading.end()
        )
        if end < 0:
            end = len(raw)
        block = raw[heading.end():end]
        fields: dict[str, str] = {}
        for key in ("Rule", "Trigger", "Enforcement"):
            match = re.search(
                rf"(?ms)^\\*\\*{key}\\.\\*\\*\\s*(.*?)(?=^\\*\\*[A-Za-z][^*]*\\.\\*\\*|^## |\\Z)",
                block,
            )
            if match:
                fields[key.lower()] = " ".join(match.group(1).split())
        missing = [k for k in ("rule", "trigger", "enforcement") if not fields.get(k)]
        if missing:
            problems.append({
                "code": "INCOMPLETE_FOUNDER_JUDGEMENT",
                "detail": f"{identifier}: {','.join(missing)}",
            })
            continue
        drill = DRILL_CATALOG.get(identifier)
        if drill is None:
            problems.append({"code": "UNEXERCISED_FOUNDER_JUDGEMENT", "detail": identifier})
        records.append({
            "id": identifier,
            "classification": "FOUNDER_JUDGEMENT_TRAINING_RECORD",
            "title": heading.group(2).strip(),
            "source": str(FOUNDER_JUDGEMENTS_PATH),
            "source_line": raw.count("\n", 0, heading.start()) + 1,
            "source_digest": digest,
            "rule": fields["rule"],
            "applicability_trigger": fields["trigger"],
            "documented_enforcement": fields["enforcement"],
            "historical_issuer_authenticated": False,
            "constitutional_authority_granted": False,
            "drill": ({
                "scenario": drill[0],
                "expected_decision_class": drill[1],
                "independent_outcome_probe": drill[2],
                "execution_proof": None,
                "competence_certified": False,
            } if drill else None),
        })
    return records, problems, digest


def compile_packet(root: Path) -> dict[str, Any]:
    """Compile a bounded, deterministic report; NO invented live-status claims.

    Callers wanting a privileged capability must separately invoke current
    authenticated QUAD/DoF admission and independently verified runtime checks.
    """
    root = Path(root).resolve()
    agents, agents_digest = _read(root, AGENTS_PATH)
    laws, laws_digest = _read(root, LAW_PATH)
    problems: list[dict[str, str]] = []
    if not agents:
        problems.append(
            {"code": "AGENT_ENTRYPOINT_UNAVAILABLE", "detail": str(AGENTS_PATH)}
        )
    if agents:
        fence = chr(96) * 3
        blocks = re.findall(
            r"(?ms)^"
            + re.escape(fence)
            + r"toml\s*\n(.*?)^"
            + re.escape(fence)
            + r"\s*$",
            agents,
        )
        if len(blocks) != 1:
            problems.append(
                {
                    "code": "EMBEDDED_RUNTIME_POLICY_MISSING",
                    "detail": "sovereign/policy.py requires exactly one closed TOML block",
                }
            )
        else:
            try:
                import tomllib

                data = tomllib.loads(blocks[0])
                if not isinstance(data, dict) or not all(
                    k in data
                    for k in (
                        "capabilities",
                        "fsm",
                        "budget",
                        "cost",
                        "routing",
                        "merge",
                        "invariants",
                        "jev",
                    )
                ):
                    problems.append(
                        {
                            "code": "INCOMPLETE_RUNTIME_POLICY",
                            "detail": "missing required machine policy sections",
                        }
                    )
            except (ImportError, ValueError) as exc:
                problems.append(
                    {"code": "MALFORMED_RUNTIME_POLICY", "detail": type(exc).__name__}
                )
    if agents:
        for code, pattern in LEGACY_COMMANDS:
            if pattern.search(agents):
                problems.append(
                    {
                        "code": code,
                        "detail": "active AGENTS.md instruction is superseded by IDP #7794",
                    }
                )
    wrappers: dict[str, str] = {}
    for name in WRAPPERS:
        p = root / name
        if not p.is_file():
            wrappers[name] = "ABSENT"
            continue
        content, _ = _read(root, Path(name))
        wrappers[name] = (
            "POINTER_ONLY"
            if _active_wrapper(name, content)
            else "CONFLICTING_SECOND_INSTRUCTION_SURFACE"
        )
        if wrappers[name] != "POINTER_ONLY":
            problems.append({"code": "DUPLICATE_HARNESS_POLICY", "detail": name})
    rows, law_problems = _law_rows(laws)
    training, training_problems, training_digest = _training_records(root)
    problems += law_problems
    problems += training_problems
    # A success here certifies only the static document contract. All measured
    # enforcement, founder assent, provider health and admission remain external.
    status = "CONFLICTED" if problems else "SOURCE_CONSISTENT_UNVERIFIED_RUNTIME"
    return {
        "schema": SCHEMA,
        "status": status,
        "scope": "chidionyema/idp",
        "canonical_entrypoint": "AGENTS.md",
        "source_digests": {
            "AGENTS.md": agents_digest,
            str(LAW_PATH): laws_digest,
            str(FOUNDER_JUDGEMENTS_PATH): training_digest,
        },
        "runtime_machine_policy": "AGENTS.md#toml (must migrate transactionally before shrink)",
        "external_jurisdictions": {
            "argon": "NOT_FEDERATED",
            "argon-sync": "NOT_FEDERATED",
        },
        "law_category_meaning": {
            "FOUNDER_LAW": "Authenticated founder-issued directive (none authenticated by this read-only packet)",
            "ESTATE_CONSTITUTION": "Ratified estate-wide invariant (not inferred from GOV identifiers)",
            "ENGINEERING_STANDARD": "Versioned engineering prescription, possibly scoped by stack or hazard",
            "ESTATE_ENFORCEMENT_CONTROL": "Executable GOV gate (not its originating founder law)",
            "OPERATIONAL_POLICY": "Current environment-specific configuration with validity and expiry",
            "GENERAL_PRINCIPLE": "Evidence-backed, non-authorizing reasoning guidance",
            "HISTORY": "Superseded provenance, never privileged authority",
        },
        "laws": rows,
        "founder_judgement_training": training,
        "fleet_drills_executed": False,
        "competence_certified": False,
        "wrappers": wrappers,
        "problems": sorted(problems, key=lambda x: (x["code"], x["detail"])),
        "required_next_actions": [
            "Authenticate agent principal through QUAD / existing trusted gateway",
            "Fetch CURRENT Oracle + current topology + source/plan versions",
            "Obtain current scoped DoF lease and broker-side law decision before effects",
            "Verify real enforcement and restore path; never infer from this packet",
            "Train against applicable falsifiers before privilege promotion",
        ],
        "is_admission_decision": False,
        "grants_execution": False,
        "independent_law_effect_proof": "NOT_EXECUTED",
        "runtime_freshness": "BLIND",
    }


def encoded(packet: dict[str, Any]) -> str:
    """Stable machine-readable bytes, independently hashable but NOT signed."""
    return json.dumps(packet, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
