#!/usr/bin/env python3
"""The links the founder asks for, derived from the estate's own ledgers.

    plan            <-  instruction  (the intent the work goes through)
    plan            <-  founder prompt (the words that started it)
    founder prompt  <-  protocol      (exactly one, by the protocol kit's genesis rule)

WHAT THIS IS NOT. It is not a place an agent types the truth about its own links. The
instruction is what the intent door recorded under the session; the founder prompt is what the
prompt ledger recorded under the session; the protocol is derived from the prompt's own text by
the same deterministic rule the intake uses. A link that cannot be derived is reported as a
violation, not quietly filled in.

TWO CLASSES, DELIBERATELY.

  violation  the link is present and wrong: an instruction that resolves to no known intent, a
             founder prompt id that resolves to no record, a prompt bound to no protocol. These
             REFUSE (exit 4): a gate that cannot fail is not a gate.
  gap        the link is absent: no intent ran under the session, or no founder prompt was
             recorded for it. These are printed and counted, and they refuse only under
             --strict, because the estate is mid-rollout and a missing link is not yet a lie.

THE PROTOCOL KIT IS THE SOURCE OF THE PROTOCOL RULE. platform/estate/protocolkit is the
founder's own kit, vendored into the repository so it can no longer be lost with /tmp. The
genesis rule it states -- every founder prompt binds to exactly one protocol, and an unbound
prompt cannot be compiled -- is enforced here through the kit's own audit(), not re-implemented.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
KIT_DIR = os.path.join(REPO_ROOT, "platform", "estate", "protocolkit")


def _load_kit():
    """The founder's kit, loaded BY PATH.

    `import protocolkit` is not safe here: any sys.path entry holding a directory named
    `protocolkit` without an __init__.py (/tmp/protocolkit, where the kit was born) is a
    namespace package and wins the import, which is how the vendored kit silently became
    "unknown location". Loading it by file path removes the shadowing question entirely.
    """
    existing = sys.modules.get("protocolkit")
    if existing is not None and str(getattr(existing, "__file__", "")).startswith(
        KIT_DIR
    ):
        return existing
    pkg_dir = os.path.join(KIT_DIR, "protocolkit")
    spec = importlib.util.spec_from_file_location(
        "protocolkit",
        os.path.join(pkg_dir, "__init__.py"),
        submodule_search_locations=[pkg_dir],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(
            "the founder's protocol kit is missing from the repository: "
            f"{pkg_dir}/__init__.py could not be loaded"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules["protocolkit"] = module
    spec.loader.exec_module(module)
    return module


_kit = _load_kit()
FounderPrompt = _kit.FounderPrompt
ProtocolId = _kit.ProtocolId
kit_audit = _kit.audit

if os.path.join(REPO_ROOT, "platform", "estate") not in sys.path:
    sys.path.insert(0, os.path.join(REPO_ROOT, "platform", "estate"))

from governance import founder_intake  # noqa: E402

# The ledger files in the plans directory that are NOT a session's plan ledger.
NON_SESSION_LEDGERS = frozenset({"intents.jsonl", "observe.jsonl", "refusals.jsonl"})

INSTRUCTION_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")
PROMPT_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{3,120}$")


# --- where the estate keeps its ledgers ------------------------------------------------------


def estate_home() -> str:
    return os.environ.get("ESTATE_HOME") or os.path.expanduser("~/.estate")


def plans_dir() -> str:
    return os.environ.get("ESTATE_PLAN_LEDGER_DIR") or os.path.join(
        estate_home(), "plans"
    )


def prompts_path() -> str:
    return os.path.join(estate_home(), "state", "prompts.jsonl")


def intents_path() -> str:
    return os.path.join(plans_dir(), "intents.jsonl")


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row, dict):
                    out.append(row)
    except OSError:
        return out
    return out


# --- the intents the estate knows ------------------------------------------------------------


def known_intents() -> Dict[str, str]:
    """intent name -> where it came from. A name is known if an intent YAML with that name is
    installed in the estate or committed in this repository."""
    out: Dict[str, str] = {}
    dirs = [
        os.path.join(estate_home(), "intents"),
        os.path.join(REPO_ROOT, "platform", "estate", "intents"),
        os.path.join(REPO_ROOT, "intents"),
    ]
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith((".yaml", ".yml")):
                continue
            out.setdefault(fn.rsplit(".", 1)[0], d)
            try:
                with open(os.path.join(d, fn), encoding="utf-8") as fh:
                    for line in fh:
                        m = re.match(r"^name:\s*([A-Za-z0-9._-]{2,64})\s*$", line)
                        if m:
                            out.setdefault(m.group(1), d)
                            break
            except OSError:
                continue
    return out


# --- the plans --------------------------------------------------------------------------------


def session_ledgers() -> Dict[str, List[Dict[str, Any]]]:
    """session id -> the plan-tool calls its ledger holds."""
    out: Dict[str, List[Dict[str, Any]]] = {}
    d = plans_dir()
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".jsonl") or fn in NON_SESSION_LEDGERS:
            continue
        events = read_jsonl(os.path.join(d, fn))
        if not any(e.get("tool") in ("declare_plan", "revise_plan") for e in events):
            continue
        out[fn[: -len(".jsonl")]] = events
    return out


def declared_plan(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The plan the session last declared: goal, sub-goals, and the links it claimed."""
    plan: Dict[str, Any] = {"goal": "", "subgoals": [], "instruction": "", "prompt": ""}
    for e in events:
        if e.get("tool") not in ("declare_plan", "revise_plan"):
            continue
        args = e.get("args") if isinstance(e.get("args"), dict) else {}
        plan["goal"] = str(args.get("goal") or "")
        raw = args.get("subgoals")
        plan["subgoals"] = (
            [str(s.get("id") or "") for s in raw if isinstance(s, dict)]
            if isinstance(raw, list)
            else []
        )
        plan["instruction"] = str(args.get("instruction") or "")
        plan["prompt"] = str(args.get("prompt") or "")
    return plan


def session_intents(session: str) -> List[str]:
    """The intents the intent door recorded under this session, in order, without repeats."""
    out: List[str] = []
    for rec in read_jsonl(intents_path()):
        if str(rec.get("session") or "") != session:
            continue
        name = str(rec.get("intent") or "")
        if name and name not in out:
            out.append(name)
    return out


# --- the founder prompts ----------------------------------------------------------------------


def prompt_records() -> List[Dict[str, Any]]:
    return read_jsonl(prompts_path())


def prompt_for_session(session: str) -> Optional[Dict[str, Any]]:
    """The newest founder prompt recorded under this session."""
    found = None
    for rec in prompt_records():
        if str(rec.get("session") or "") == session:
            found = rec
    return found


def prompt_by_id(prompt_id: str) -> Optional[Dict[str, Any]]:
    """A founder prompt by its id or by its fingerprint."""
    if not prompt_id:
        return None
    for rec in prompt_records():
        if str(rec.get("id") or "") == prompt_id:
            return rec
    for rec in prompt_records():
        if str(rec.get("fingerprint") or "") == prompt_id:
            return rec
    return None


def protocol_of(rec: Dict[str, Any]) -> Optional[ProtocolId]:
    """The protocol a founder prompt binds to: the stored binding when it is one, the derived
    binding otherwise. Never None for a non-empty prompt: the kit's rule is exactly one."""
    raw = rec.get("protocol_binding")
    if not raw:
        try:
            raw = founder_intake.bind_protocol(str(rec.get("text") or ""))
        except Exception:  # noqa: BLE001 - a broken binder must not invent a protocol
            return None
    try:
        return ProtocolId(str(raw))
    except ValueError:
        return None


def prompt_audit(
    records: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, List[str]]:
    """The kit's own audit over the prompt ledger: {prompt id: violations}."""
    recs = prompt_records() if records is None else records
    prompts = []
    for rec in recs:
        prompts.append(
            FounderPrompt(
                id=str(rec.get("id") or ""),
                text=str(rec.get("text") or ""),
                protocol_binding=protocol_of(rec),
            )
        )
    return kit_audit(prompts)


# --- the links --------------------------------------------------------------------------------


def link_rows(session: Optional[str] = None) -> List[Dict[str, Any]]:
    """One row per session that declared a plan: the plan, its instruction, its founder prompt
    and the protocol that prompt is bound to."""
    rows: List[Dict[str, Any]] = []
    intents = known_intents()
    for sid, events in sorted(session_ledgers().items()):
        if session and sid != session:
            continue
        plan = declared_plan(events)
        observed = session_intents(sid)
        declared_instruction = plan["instruction"]
        declared_prompt = plan["prompt"]
        prompt = prompt_by_id(declared_prompt) if declared_prompt else None
        if prompt is None and not declared_prompt:
            prompt = prompt_for_session(sid)
        binding = protocol_of(prompt) if prompt else None
        rows.append(
            {
                "session": sid,
                "goal": plan["goal"],
                "subgoals": plan["subgoals"],
                "declared_instruction": declared_instruction,
                "observed_instructions": observed,
                "declared_prompt": declared_prompt,
                "founder_prompt": prompt,
                "prompt_id": str(prompt.get("id")) if prompt else "",
                "protocol": binding.value if binding else "",
                "known_intents": intents,
            }
        )
    return rows


def row_violations(row: Dict[str, Any]) -> List[str]:
    """The links that are present and WRONG. Absent links are gaps, not violations."""
    out: List[str] = []
    sid = row["session"]
    declared = row["declared_instruction"]
    if declared:
        if not INSTRUCTION_RE.match(declared):
            out.append(f"{sid}: instruction '{declared}' is not an intent name")
        elif declared not in row["known_intents"]:
            out.append(f"{sid}: instruction '{declared}' resolves to no known intent")
    if row["declared_prompt"]:
        if not PROMPT_ID_RE.match(row["declared_prompt"]):
            out.append(
                f"{sid}: prompt '{row['declared_prompt']}' is not a founder prompt id"
            )
        elif not row["founder_prompt"]:
            out.append(
                f"{sid}: prompt '{row['declared_prompt']}' resolves to no founder prompt"
            )
    if row["founder_prompt"] and not row["protocol"]:
        out.append(
            f"{sid}: founder prompt '{row['prompt_id']}' is bound to no protocol"
        )
    return out


def row_gaps(row: Dict[str, Any]) -> List[str]:
    """The links that are absent. Counted, printed, and refusing only under --strict."""
    out: List[str] = []
    sid = row["session"]
    if not row["declared_instruction"] and not row["observed_instructions"]:
        out.append(f"{sid}: no instruction linked to this plan")
    if not row["founder_prompt"]:
        out.append(f"{sid}: no founder prompt linked to this plan")
    return out


def audit(session: Optional[str] = None) -> Dict[str, Any]:
    """The whole picture: the rows, the violations, the gaps and the kit's prompt audit."""
    rows = link_rows(session)
    violations: List[str] = []
    gaps: List[str] = []
    for row in rows:
        violations.extend(row_violations(row))
        gaps.extend(row_gaps(row))
    prompts = prompt_audit()
    for pid, problems in sorted(prompts.items()):
        for p in problems:
            violations.append(f"{pid}: {p}")
    return {
        "rows": rows,
        "violations": violations,
        "gaps": gaps,
        "prompt_audit": prompts,
        "sessions": len(rows),
    }


def trace_instruction(instruction_id: str, mission_db: Optional[str] = None) -> Dict[str, Any]:
    """Read-only, bounded reconstruction from real founder-plan and FLOW mission stores.

    A mission event's incrementing DB key is NOT a cross-host causal parent, and
    an external-effect receipt in SQLite is NOT a live independent readback.
    Missing sources remain visible; no event is created or settled here.
    """
    if not isinstance(instruction_id, str) or not PROMPT_ID_RE.fullmatch(instruction_id):
        raise ValueError("instruction id must be a non-empty bounded identifier")
    links = []
    for row in link_rows():
        if instruction_id not in [row["declared_instruction"], *row["observed_instructions"]]:
            continue
        prompt = row.get("founder_prompt") or {}
        links.append(
            {
                "session": row["session"],
                "instruction": instruction_id,
                "link_type": (
                    "DECLARED_PLAN_LINK"
                    if row["declared_instruction"] == instruction_id
                    else "OBSERVED_INTENT_LINK"
                ),
                "prompt_id": row.get("prompt_id") or None,
                "prompt_fingerprint": prompt.get("fingerprint"),
                "protocol": row.get("protocol") or None,
                "prompt_verified": False,
            }
        )
    result = {
        "schema": "estate.instruction-trace.v1",
        "instruction_id": instruction_id,
        "authority": "READ_ONLY_FEDERATED_SOURCE_PROJECTION",
        "operational_yield": "NOT_INDEPENDENTLY_VERIFIED",
        "clock_accuracy": "UNVERIFIED; Unix REAL fractions are not certified milliseconds",
        "links": links,
        "missions": [],
        "attempts": [],
        "transitions": [],
        "external_effects": [],
        "checkpoints": [],
        "gaps": [],
    }
    gaps = result["gaps"]
    if not links:
        gaps.append({"reason": "FOUNDER_PROMPT_LINK_NOT_OBSERVED"})
    if not mission_db:
        gaps.append({"reason": "CONTINUITY_DATABASE_NOT_SUPPLIED"})
        result["state"] = "BLIND"
        return result
    from pathlib import Path
    import sqlite3

    # URI mode=ro is a mandatory read-only trust boundary; never instantiate
    # MissionStore, because opening it executes schema migrations.
    uri = Path(mission_db).expanduser().resolve().as_uri() + "?mode=ro"
    try:
        db = sqlite3.connect(uri, uri=True, timeout=3.0)
    except sqlite3.Error:
        gaps.append({"reason": "CONTINUITY_DATABASE_UNAVAILABLE"})
        result["state"] = "BLIND"
        return result
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA query_only=ON")
        # Follow only the authoritative parent_mission_id edges, never a
        # timestamp-neighbour or matching GitHub SHA as a guessed parent.
        rows = db.execute(
            "WITH RECURSIVE family(mission_id) AS ("
            " SELECT mission_id FROM missions WHERE instruction_id=?"
            " UNION"
            " SELECT m.mission_id FROM missions m JOIN family f"
            " ON m.parent_mission_id=f.mission_id)"
            " SELECT m.* FROM missions m JOIN family f ON f.mission_id=m.mission_id"
            " ORDER BY m.created_at, m.mission_id LIMIT 129",
            (instruction_id,),
        ).fetchall()
        if len(rows) > 128:
            gaps.append({"reason": "MISSION_DESCENDANTS_TRUNCATED", "limit": 128})
            rows = rows[:128]
        mids = {r["mission_id"] for r in rows}
        if not mids:
            gaps.append({"reason": "DURABLE_MISSION_NOT_FOUND"})
        for r in rows:
            result["missions"].append(
                {
                    "mission_id": r["mission_id"],
                    "parent_mission_id": r["parent_mission_id"],
                    "instruction_id": r["instruction_id"],
                    "mandate_id": r["mandate_id"],
                    "mandate_version": r["mandate_version"],
                    "owner": r["authoritative_owner"],
                    "state": r["state"],
                    "current_attempt_id": r["current_attempt_id"],
                    "lease_epoch": r["current_lease_epoch"],
                    "acceptance_contract_digest": r["acceptance_contract_digest"],
                    "created_at_unix": r["created_at"],
                    "clock_precision": "UNVERIFIED_SOURCE_CLOCK",
                }
            )
            if r["parent_mission_id"] and r["parent_mission_id"] not in mids:
                gaps.append(
                    {"mission_id": r["mission_id"], "reason": "PARENT_MISSION_NOT_IN_PROJECTION"}
                )
            mission_id = r["mission_id"]
            for a in db.execute(
                "SELECT attempt_id, mission_id, agent_adapter, provider, model,"
                " execution_host, failure_domain, base_sha, candidate_sha,"
                " started_at, lease_epoch, state, failure_class"
                " FROM mission_attempts WHERE mission_id=? ORDER BY started_at, attempt_id",
                (mission_id,),
            ):
                result["attempts"].append(dict(a))
            observed = list(
                db.execute(
                    "SELECT event_id, mission_id, attempt_id, lease_epoch,"
                    " from_state, to_state, actor, cause, evidence, created_at"
                    " FROM mission_events WHERE mission_id=? ORDER BY event_id",
                    (mission_id,),
                )
            )
            if not observed:
                gaps.append({"mission_id": mission_id, "reason": "TRANSITION_HISTORY_MISSING"})
            previous = None
            for e in observed:
                if previous is not None and e["from_state"] != previous:
                    gaps.append(
                        {
                            "mission_id": mission_id,
                            "event_id": e["event_id"],
                            "reason": "TRANSITION_REPLAY_MISMATCH",
                        }
                    )
                if e["to_state"] is not None:
                    previous = e["to_state"]
                evidence = e["evidence"] or ""
                result["transitions"].append(
                    {
                        "event_id": f"continuity:{mission_id}:{e['event_id']}",
                        "local_event_id": e["event_id"],
                        "mission_id": mission_id,
                        "attempt_id": e["attempt_id"],
                        "lease_epoch": e["lease_epoch"],
                        "from_state": e["from_state"],
                        "to_state": e["to_state"],
                        "actor": e["actor"],
                        "cause_sha256": hashlib.sha256(
                            (e["cause"] or "").encode()
                        ).hexdigest(),
                        "evidence_sha256": hashlib.sha256(evidence.encode()).hexdigest(),
                        "effect_ref": evidence if evidence.startswith("effect:") else None,
                        "created_at_unix": e["created_at"],
                        "clock_precision": "UNVERIFIED_SOURCE_CLOCK",
                        "parent_event_ids": None,
                    }
                )
            if previous != r["state"]:
                gaps.append({"mission_id": mission_id, "reason": "PROJECTED_STATE_MISMATCH"})
            for effect in db.execute(
                "SELECT effect_id, mission_id, attempt_id, lease_epoch,"
                " state, operation, target, intent_digest, external_transaction_ref,"
                " external_receipt, observed_at, verified_by, reconciliation_status"
                " FROM external_effects WHERE mission_id=? ORDER BY effect_id",
                (mission_id,),
            ):
                receipt = effect["external_receipt"]
                result["external_effects"].append(
                    {
                        "effect_id": effect["effect_id"],
                        "mission_id": mission_id,
                        "attempt_id": effect["attempt_id"],
                        "lease_epoch": effect["lease_epoch"],
                        "state": effect["state"],
                        "operation": effect["operation"],
                        "target_sha256": hashlib.sha256(
                            effect["target"].encode()
                        ).hexdigest(),
                        "intent_digest": effect["intent_digest"],
                        "external_transaction_ref": effect["external_transaction_ref"],
                        "receipt_sha256": hashlib.sha256(receipt.encode()).hexdigest()
                        if receipt
                        else None,
                        "observed_at_unix": effect["observed_at"],
                        "verified_by_claim": effect["verified_by"],
                        "reconciliation_status": effect["reconciliation_status"],
                        "independently_rechecked": False,
                    }
                )
            for chk in db.execute(
                "SELECT checkpoint_id, mission_id, attempt_id, sequence,"
                " content_digest, created_at FROM mission_checkpoints"
                " WHERE mission_id=? ORDER BY sequence",
                (mission_id,),
            ):
                result["checkpoints"].append(dict(chk))
        result["state"] = "PARTIAL_UNVERIFIED" if mids else "BLIND"
        if mids:
            gaps.append({"reason": "CROSS_SYSTEM_CAUSAL_PARENTS_UNOBSERVED"})
            gaps.append({"reason": "INDEPENDENT_LIVE_EFFECT_READBACK_MISSING"})
    except (sqlite3.Error, TypeError, ValueError):
        gaps.append({"reason": "CONTINUITY_READ_OR_SCHEMA_BLIND"})
        result["state"] = "BLIND"
        for key in ("missions", "attempts", "transitions", "external_effects", "checkpoints"):
            result[key] = []
    finally:
        db.close()
    result["coverage"] = {
        "missions": len(result["missions"]),
        "attempts": len(result["attempts"]),
        "transition_events": len(result["transitions"]),
        "external_effect_intents": len(result["external_effects"]),
        "verified_live_effects": 0,
    }
    return result
