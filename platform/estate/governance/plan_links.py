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
