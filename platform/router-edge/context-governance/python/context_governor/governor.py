"""Deterministic Estate-Wide Context Governance Engine (Zero External Dependencies).

Guards against all 10 production context failure modes:
  1. Streaming mid-generation cutoff (strictly ingress-evaluated; never cuts mid-stream)
  2. Atomic critical-section interruption (bounded non-renewable +15% / 2-turn lease)
  3. Cross-provider tokenizer drift (conservative multiplier + provider usage calibration)
  4. KV-cache prefix thrashing (prefix_sha256 immutability check; tail/header directives)
  5. Multimodal/base64 explosion (image tile accounting + automatic N>1 image externalization)
  6. Sub-agent/Legion fan-out amplification (hierarchical mission aggregate budget tree)
  7. Reasoning effort bloat (role-based reasoning_effort + max_tokens clamping)
  8. Storage/DO outage self-inflicted interruption (degraded fail-open for telemetry)
  9. Lossy compaction invariant amnesia (mandatory handoff validator + failure-trace pinning)
 10. Memory probe pollution & retired decision leakage (CURRENT authority + namespace filter)
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

REASONING_ORDER = {"minimal": 0, "low": 1, "medium": 2, "high": 3}


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def estimate_text_tokens(text: str, multiplier: float = 1.15) -> int:
    """Conservative upper-bound token estimator safe for code, JSON, and Unicode."""
    if not text:
        return 0
    utf8_len = len(text.encode("utf-8"))
    # Dense code/JSON/punctuation averages ~3.2 bytes/token; apply provider safety factor.
    return max(1, int(math.ceil((utf8_len / 3.2) * multiplier)))


def estimate_messages_tokens(
    messages: Sequence[Dict[str, Any]],
    tools: Optional[Sequence[Dict[str, Any]]] = None,
    multiplier: float = 1.15,
    calibration_ratio: float = 1.0,
) -> Dict[str, Any]:
    """Estimate prompt tokens including multimodal images and tool schemas."""
    effective_mult = multiplier * max(0.85, min(2.0, calibration_ratio))
    tool_tokens = (
        estimate_text_tokens(canonical_json(tools), effective_mult) if tools else 0
    )
    text_tokens = 0
    image_tokens = 0
    image_count = 0

    for msg in messages:
        text_tokens += 6  # per-message framing overhead
        content = msg.get("content")
        if isinstance(content, str):
            text_tokens += estimate_text_tokens(content, effective_mult)
        elif isinstance(content, list):
            for part in content:
                if not isinstance(part, dict):
                    continue
                ptype = part.get("type", "")
                if ptype == "text":
                    text_tokens += estimate_text_tokens(
                        str(part.get("text", "")), effective_mult
                    )
                elif ptype in ("image_url", "image"):
                    image_count += 1
                    url_val = ""
                    if isinstance(part.get("image_url"), dict):
                        url_val = str(part["image_url"].get("url", ""))
                    elif isinstance(part.get("image_url"), str):
                        url_val = part["image_url"]
                    # Base64/high-res screenshot conservative tile estimate (1,600 to 6,400 tokens)
                    if url_val.startswith("data:image"):
                        raw_bytes = len(url_val) * 3 // 4
                        image_tokens += min(8192, max(1600, raw_bytes // 128))
                    else:
                        image_tokens += 1600
                else:
                    text_tokens += estimate_text_tokens(
                        canonical_json(part), effective_mult
                    )
        if msg.get("tool_calls"):
            text_tokens += estimate_text_tokens(
                canonical_json(msg["tool_calls"]), effective_mult
            )

    total = tool_tokens + text_tokens + image_tokens
    return {
        "total_tokens": total,
        "tool_schema_tokens": tool_tokens,
        "text_tokens": text_tokens,
        "image_tokens": image_tokens,
        "image_count": image_count,
    }


def compute_prefix_hash(
    messages: Sequence[Dict[str, Any]],
    tools: Optional[Sequence[Dict[str, Any]]] = None,
) -> str:
    """Stable hash of immutable Turn-1 prefix (system prompt + sorted tools)."""
    system_msgs = [m for m in messages if m.get("role") == "system"]
    stable_tools = sorted([canonical_json(t) for t in (tools or [])])
    return sha256_hex(canonical_json({"system": system_msgs, "tools": stable_tools}))


@dataclass
class ContextPolicy:
    raw: Dict[str, Any]

    @classmethod
    def from_file(cls, path: Path) -> "ContextPolicy":
        return cls(json.loads(path.read_text(encoding="utf-8")))

    @property
    def phase(self) -> str:
        return str(self.raw.get("rollout_phase", "SHADOW"))

    @property
    def invariants(self) -> Dict[str, Any]:
        return self.raw["global_invariants"]

    def role_config(self, role: str) -> Dict[str, Any]:
        roles = self.raw["roles"]
        if role in roles:
            return roles[role]
        # Unknown role fails safely to strictest operational ceiling.
        return roles["role:ops-dispatch"]

    def tokenizer_multiplier(self, model_name: str) -> float:
        m = (model_name or "").lower()
        mults = self.raw.get("tokenizer_safety_multipliers", {})
        for family, val in mults.items():
            if family != "default" and family in m:
                return float(val)
        return float(mults.get("default", 1.15))


@dataclass
class SessionState:
    session_id: str
    mission_id: str
    role: str
    turn_count: int = 0
    initial_prefix_hash: str = ""
    prefix_mutations: int = 0
    soft_warnings_issued: int = 0
    critical_section_turns_used: int = 0
    critical_section_nonce: Optional[str] = None
    calibration_ratio: float = 1.0
    total_prompt_tokens: int = 0
    cached_prompt_tokens: int = 0


class MissionBudgetLedger:
    """In-memory / DO-compatible hierarchical mission & session budget ledger."""

    def __init__(self, simulate_storage_outage: bool = False):
        self.sessions: Dict[str, SessionState] = {}
        self.mission_tokens: Dict[str, int] = {}
        self.simulate_storage_outage = simulate_storage_outage

    def get_or_create_session(
        self, session_id: str, mission_id: str, role: str
    ) -> SessionState:
        if self.simulate_storage_outage:
            raise RuntimeError("BUDGET_LEDGER_DO_TIMEOUT")
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionState(
                session_id=session_id, mission_id=mission_id, role=role
            )
        return self.sessions[session_id]

    def record_provider_usage(
        self,
        session_id: str,
        estimated_tokens: int,
        actual_prompt_tokens: int,
        cached_prompt_tokens: int = 0,
    ) -> None:
        if self.simulate_storage_outage or session_id not in self.sessions:
            return
        st = self.sessions[session_id]
        st.total_prompt_tokens += actual_prompt_tokens
        st.cached_prompt_tokens += cached_prompt_tokens
        self.mission_tokens[st.mission_id] = (
            self.mission_tokens.get(st.mission_id, 0) + actual_prompt_tokens
        )
        if estimated_tokens > 0 and actual_prompt_tokens > 0:
            observed_ratio = actual_prompt_tokens / float(estimated_tokens)
            # Exponential moving average calibration prevents sudden tokenizer cliff
            st.calibration_ratio = round(
                0.7 * st.calibration_ratio + 0.3 * observed_ratio, 4
            )

    def mission_total(self, mission_id: str) -> int:
        if self.simulate_storage_outage:
            raise RuntimeError("BUDGET_LEDGER_DO_TIMEOUT")
        return self.mission_tokens.get(mission_id, 0)


@dataclass
class IngressDecision:
    allowed: bool
    http_status: int
    directive: str
    headers: Dict[str, str]
    clamped_request: Dict[str, Any]
    telemetry: Dict[str, Any]
    degradations: List[str] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ContextGovernor:
    """Stateless ingress policy evaluator backed by MissionBudgetLedger."""

    def __init__(self, policy: ContextPolicy, ledger: MissionBudgetLedger):
        self.policy = policy
        self.ledger = ledger

    def evaluate_ingress(
        self,
        request: Dict[str, Any],
        *,
        session_id: str,
        mission_id: str,
        role: str,
        critical_section_nonce: Optional[str] = None,
        is_subagent: bool = False,
    ) -> IngressDecision:
        phase = self.policy.phase
        rcfg = self.policy.role_config(role)
        inv = self.policy.invariants
        degradations: List[str] = []
        violations: List[str] = []

        # Edge Case 8: Degraded fail-open on DO/ledger outage (never cause self-inflicted outage)
        session: Optional[SessionState] = None
        mission_spent = 0
        try:
            session = self.ledger.get_or_create_session(session_id, mission_id, role)
            mission_spent = self.ledger.mission_total(mission_id)
        except Exception:
            degradations.append("budget_ledger_unavailable_fail_open")

        model = str(request.get("model", ""))
        messages = list(request.get("messages") or [])
        tools = list(request.get("tools") or [])

        # Edge Case 7: Transparent role clamping (reasoning_effort + max_tokens)
        clamped = dict(request)
        if phase in ("SOFT_ROTATE", "ENFORCE"):
            req_effort = str(request.get("reasoning_effort", "")).lower()
            clamp_effort = str(rcfg["reasoning_effort_clamp"]).lower()
            if not req_effort or REASONING_ORDER.get(
                req_effort, 99
            ) > REASONING_ORDER.get(clamp_effort, 1):
                clamped["reasoning_effort"] = clamp_effort
                degradations.append(f"reasoning_effort_clamped_to_{clamp_effort}")

            max_out_clamp = int(rcfg["max_output_tokens_clamp"])
            req_max_out = request.get("max_tokens") or request.get(
                "max_completion_tokens"
            )
            if req_max_out is None or int(req_max_out) > max_out_clamp:
                clamped["max_tokens"] = max_out_clamp
                degradations.append(f"max_tokens_clamped_to_{max_out_clamp}")

        # Edge Case 3 & 5: Hybrid calibrated + multimodal token estimation
        mult = self.policy.tokenizer_multiplier(model)
        cal = session.calibration_ratio if session else 1.0
        est = estimate_messages_tokens(
            messages, tools=tools, multiplier=mult, calibration_ratio=cal
        )
        used_tokens = est["total_tokens"]

        # Edge Case 4: KV-cache prefix immutability tracking
        prefix_hash = compute_prefix_hash(messages, tools=tools)
        kv_cache_state = "COLD_TURN_1"
        if session is not None:
            session.turn_count += 1
            if session.turn_count == 1:
                session.initial_prefix_hash = prefix_hash
                if used_tokens > int(rcfg["turn_1_prefix_cap"]):
                    violations.append("ERR_TURN1_PREFIX_CAP_EXCEEDED")
            else:
                if prefix_hash != session.initial_prefix_hash:
                    session.prefix_mutations += 1
                    kv_cache_state = "PREFIX_MUTATED_THRASH"
                    violations.append("ERR_KV_PREFIX_THRASH")
                else:
                    kv_cache_state = "PREFIX_STABLE"

        # Always-on MCP tool ceiling check
        if len(tools) > int(inv["max_always_on_mcp_tools"]):
            violations.append("ERR_MCP_TOOL_CEILING_EXCEEDED")

        # Edge Case 6: Sub-agent brief isolation & hierarchical mission fan-out budget
        if is_subagent and session is not None and session.turn_count == 1:
            if used_tokens > int(inv["subagent_max_brief_tokens"]):
                violations.append("ERR_SUBAGENT_BRIEF_CAP_EXCEEDED")

        if mission_spent + used_tokens > int(rcfg["mission_aggregate_cap"]):
            violations.append("ERR_MISSION_AGGREGATE_BUDGET_EXCEEDED")

        soft_cap = int(rcfg["soft_context_cap"])
        hard_cap = int(rcfg["hard_context_cap"])
        max_grace = int(rcfg["max_grace_turns_after_soft"])

        # Edge Case 2: Bounded non-renewable Critical-Section Lease (+15% headroom, max 2 turns)
        lease_active = False
        effective_hard_cap = hard_cap
        if critical_section_nonce:
            max_cs_turns = int(inv["critical_section_max_turns"])
            headroom = float(inv["critical_section_max_headroom_ratio"])
            if session is not None:
                if session.critical_section_nonce is None:
                    session.critical_section_nonce = critical_section_nonce
                # Non-renewable: changing nonce cannot reset turn count!
                if session.critical_section_turns_used < max_cs_turns:
                    session.critical_section_turns_used += 1
                    lease_active = True
                    effective_hard_cap = int(math.ceil(hard_cap * (1.0 + headroom)))
                else:
                    violations.append("ERR_CRITICAL_SECTION_LEASE_EXHAUSTED")
            else:
                # Stateless fallback during DO outage
                lease_active = True
                effective_hard_cap = int(math.ceil(hard_cap * (1.0 + headroom)))

        # Edge Case 1: Streaming-safe ingress decision (soft-rotate before hard-stop)
        directive = "ALLOW"
        allowed = True
        http_status = 200

        if used_tokens >= soft_cap:
            directive = "CHECKPOINT_AND_ROTATE"
            if session is not None:
                session.soft_warnings_issued += 1

        if phase == "ENFORCE":
            grace_exhausted = (
                session is None or session.soft_warnings_issued > max_grace
            )
            if (
                "ERR_MISSION_AGGREGATE_BUDGET_EXCEEDED" in violations
                and not lease_active
            ):
                allowed = False
                http_status = 429
                directive = "HARD_STOP_MISSION_BUDGET_EXHAUSTED"
            elif used_tokens > effective_hard_cap:
                allowed = False
                http_status = 429
                directive = "HARD_STOP_CONTEXT_CAP_EXCEEDED"
            elif used_tokens >= hard_cap and not lease_active and grace_exhausted:
                allowed = False
                http_status = 429
                directive = "HARD_STOP_ROTATION_IGNORED"

        shadow_would_directive = directive
        if phase == "SHADOW":
            directive = "ALLOW"

        headers = {
            "X-Meridian-Context-Phase": phase,
            "X-Meridian-Context-Directive": directive,
            "X-Meridian-Context-Tokens": str(used_tokens),
            "X-Meridian-Context-Soft-Cap": str(soft_cap),
            "X-Meridian-Context-Hard-Cap": str(effective_hard_cap),
            "X-Meridian-Prefix-Cache-State": kv_cache_state,
            "X-Meridian-Critical-Section-Lease": "ACTIVE" if lease_active else "NONE",
        }

        telemetry = {
            "schema": "urn:estate:memory:context:v1",
            "shadow_would_directive": shadow_would_directive
            if phase == "SHADOW"
            else None,
            "mission_id": mission_id,
            "session_id": session_id,
            "role": role,
            "used_tokens": used_tokens,
            "budget_tokens": hard_cap,
            "mission_aggregate_used_tokens": mission_spent + used_tokens,
            "mission_aggregate_budget_tokens": int(rcfg["mission_aggregate_cap"]),
            "token_measurement_method": "provider_usage_calibrated"
            if (session and session.total_prompt_tokens > 0)
            else "conservative_upper_bound",
            "prefix_sha256": prefix_hash,
            "kv_cache_state": kv_cache_state,
            "image_count": est["image_count"],
            "image_tokens": est["image_tokens"],
            "tool_schema_tokens": est["tool_schema_tokens"],
            "degradations": degradations,
            "violations": violations,
            "complete": len(degradations) == 0,
            "freshness_as_of": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        }

        return IngressDecision(
            allowed=allowed,
            http_status=http_status,
            directive=directive,
            headers=headers,
            clamped_request=clamped,
            telemetry=telemetry,
            degradations=degradations,
            violations=violations,
        )


def externalize_and_compact_history(
    messages: Sequence[Dict[str, Any]],
    *,
    artifact_dir: Path,
    externalize_threshold_bytes: int = 4096,
    keep_recent_verbatim_turns: int = 4,
    keep_recent_images: int = 1,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Recoverable pointer compression that NEVER strips failure traces or system prompts.

    - Leaves system prompt untouched (protects KV-cache prefix).
    - Leaves last `keep_recent_verbatim_turns` turns untouched.
    - For older tool results > threshold: writes full raw payload to `artifact_dir` and replaces
      with a recoverable pointer (`uri`, `sha256`, `bytes`) PLUS preserves the last 15 lines
      if the tool result contains failure markers (`exit_code!=0`, `error`, `525`, `403`, `402`).
    - Replaces multimodal images older than `keep_recent_images` with recoverable hash pointers.
    """
    artifact_dir.mkdir(parents=True, exist_ok=True)
    compacted: List[Dict[str, Any]] = []
    omissions: List[Dict[str, Any]] = []

    total = len(messages)
    cutoff_idx = max(0, total - keep_recent_verbatim_turns)

    # Identify image indices so only the newest `keep_recent_images` stay inline.
    image_msg_indices = []
    for idx, m in enumerate(messages):
        c = m.get("content")
        if isinstance(c, list) and any(
            isinstance(p, dict) and p.get("type") in ("image_url", "image") for p in c
        ):
            image_msg_indices.append(idx)
    keep_img_set = (
        set(image_msg_indices[-keep_recent_images:])
        if keep_recent_images > 0
        else set()
    )

    failure_markers = (
        "error",
        "failed",
        "exception",
        "exit_code",
        "traceback",
        " 525",
        " 403",
        " 402",
    )

    for idx, msg in enumerate(messages):
        role = msg.get("role", "")
        if role == "system" or idx >= cutoff_idx:
            # Even inside recent window, strip older images beyond keep_img_set
            if idx in image_msg_indices and idx not in keep_img_set:
                new_parts = []
                for p in msg["content"]:
                    if isinstance(p, dict) and p.get("type") in ("image_url", "image"):
                        raw_s = canonical_json(p)
                        digest = sha256_hex(raw_s)
                        out_p = artifact_dir / f"img_{digest[:16]}.json"
                        out_p.write_text(raw_s, encoding="utf-8")
                        new_parts.append(
                            {
                                "type": "text",
                                "text": f"[EXTERNALIZED_IMAGE sha256={digest} uri={out_p.name}]",
                            }
                        )
                        omissions.append(
                            {
                                "index": idx,
                                "kind": "image_externalized",
                                "sha256": digest,
                                "uri": out_p.name,
                            }
                        )
                    else:
                        new_parts.append(p)
                compacted.append({**msg, "content": new_parts})
            else:
                compacted.append(msg)
            continue

        # Older tool result compression with failure-trace retention
        if role == "tool" and isinstance(msg.get("content"), str):
            raw_body = msg["content"]
            raw_bytes = len(raw_body.encode("utf-8"))
            if raw_bytes > externalize_threshold_bytes:
                digest = sha256_hex(raw_body)
                out_p = artifact_dir / f"tool_{digest[:16]}.txt"
                out_p.write_text(raw_body, encoding="utf-8")
                lower_body = raw_body.lower()
                is_failure = any(mk in lower_body for mk in failure_markers)
                if is_failure:
                    tail = "\n".join(raw_body.splitlines()[-15:])
                    replacement = (
                        f"[EXTERNALIZED_FAILURE_TRACE bytes={raw_bytes} sha256={digest} uri={out_p.name}]\n"
                        f"--- LAST_15_LINES_PINNED ---\n{tail}"
                    )
                else:
                    replacement = f"[EXTERNALIZED_TOOL_RESULT bytes={raw_bytes} sha256={digest} uri={out_p.name}]"
                omissions.append(
                    {
                        "index": idx,
                        "kind": "tool_result_externalized",
                        "failure_trace_pinned": is_failure,
                        "bytes": raw_bytes,
                        "sha256": digest,
                        "uri": out_p.name,
                    }
                )
                compacted.append({**msg, "content": replacement})
                continue

        # Strip older images beyond keep_img_set
        if idx in image_msg_indices and idx not in keep_img_set:
            new_parts = []
            for p in msg["content"]:
                if isinstance(p, dict) and p.get("type") in ("image_url", "image"):
                    raw_s = canonical_json(p)
                    digest = sha256_hex(raw_s)
                    out_p = artifact_dir / f"img_{digest[:16]}.json"
                    out_p.write_text(raw_s, encoding="utf-8")
                    new_parts.append(
                        {
                            "type": "text",
                            "text": f"[EXTERNALIZED_IMAGE sha256={digest} uri={out_p.name}]",
                        }
                    )
                    omissions.append(
                        {
                            "index": idx,
                            "kind": "image_externalized",
                            "sha256": digest,
                            "uri": out_p.name,
                        }
                    )
                else:
                    new_parts.append(p)
            compacted.append({**msg, "content": new_parts})
            continue

        compacted.append(msg)

    return compacted, omissions


def filter_authoritative_memories(
    records: Sequence[Dict[str, Any]],
    *,
    policy: ContextPolicy,
    limit: int = 10,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Pre-slice authoritative memory filter (fixes Nov 15 memory-audit crowdout bugs).

    Filters BEFORE slicing to `limit`, quarantines self-test probe namespaces, and drops
    SUPERSEDED / HISTORICAL / CONFLICTED records while recording explicit omissions.
    """
    inv = policy.invariants
    quarantined = set(inv["quarantined_memory_namespaces"])
    allowed_status = set(inv["allowed_memory_authority_statuses"])

    kept: List[Dict[str, Any]] = []
    dropped: List[Dict[str, Any]] = []

    for rec in records:
        ns = str(rec.get("namespace", "")).lower()
        status = str(rec.get("authority_status", "UNRESOLVED")).upper()
        if any(q in ns for q in quarantined):
            dropped.append(
                {"id": rec.get("id"), "reason": f"quarantined_namespace:{ns}"}
            )
            continue
        if status not in allowed_status:
            dropped.append(
                {"id": rec.get("id"), "reason": f"non_current_authority:{status}"}
            )
            continue
        kept.append(rec)

    if len(kept) > limit:
        for extra in kept[limit:]:
            dropped.append({"id": extra.get("id"), "reason": "budget_limit_sliced"})
        kept = kept[:limit]

    return kept, dropped


def validate_handoff_packet(packet: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Defeats invariant amnesia on CHECKPOINT_AND_ROTATE session rotation."""
    errors: List[str] = []
    required_fields = (
        "mission_id",
        "target_repo",
        "target_sha",
        "acceptance_receipt_contract",
        "next_discriminating_step",
        "pinned_failure_receipts",
    )
    for f in required_fields:
        val = packet.get(f)
        if val is None or (isinstance(val, str) and not val.strip()):
            errors.append(f"ERR_HANDOFF_MISSING_{f.upper()}")

    # Block retired Zone A paths from sneaking across rotations
    serialized = canonical_json(packet)
    for bad in ("~/.estate", "launchctl", "LaunchAgents", "LaunchDaemons"):
        if bad in serialized:
            errors.append(f"ERR_HANDOFF_ZONE_A_REGRESSION:{bad}")

    # Block TIER_2 agent inferences labeled as primary proof
    for r in packet.get("pinned_failure_receipts", []):
        if (
            isinstance(r, dict)
            and r.get("tier") == "TIER_2_AGENT_INFERENCE"
            and r.get("used_as_primary_fact")
        ):
            errors.append("ERR_HANDOFF_EPISTEMIC_LAUNDERING")

    return len(errors) == 0, sorted(set(errors))
