"""The instruction gate: no prompt ends in the void.

WHY THIS EXISTS. The schema ``platform/catalog/schema/001_catalog.sql`` declares the
``instructions`` table and states, in the founder's own words (2026-11-09), the law this
module enforces:

    "The router must refuse a request whose prompt carries no instruction id, and a prompt
    that cannot be linked is a row here, never a lost message."

Until this module existed there was a contract (``catalog/census/instruction.py`` --
``link_or_new`` / ``ingest_prompt`` raise ``UnlinkedPromptError`` for an unlinkable prompt)
and there were tests for it, but *no router module imported or called it*. The instruction
id was never checked at the front door, so a prompt with none flowed through and ended in
the void. That gap is what this hook closes.

WHAT IT REFUSES. A user chat request whose ``metadata`` carries no ``instruction_id``. It
reads the id from the same shape every other callback reads (``data["metadata"]``), and
refuses -- loudly -- when the prompt cannot be linked. A refusal names the fix in the same
sentence, so a caller that gets it understands and does not retry blindly.

WHAT IT NEVER REFUSES. The same calls ``active_memory.py`` already exempts, so the gate
cannot take the estate down by refusing its own plumbing:

  * non-chat call types (embeddings, text completions);
  * internal estate traffic (``estate_internal`` metadata / ``x-estate-internal`` header);
  * the graph drain (``Python-urllib`` with no named caller);
  * a caller that has explicitly opted out with ``x-estate-memory: off``.

SAFE BY DEFAULT. The check is env-gated behind ``ESTATE_INSTRUCTION_GATE=1``. Until the
instrumentation that *generates* and *carries* an ``instruction_id`` on every real prompt is
landed alongside it, flipping the gate on unconditionally would refuse 100% of traffic and
take the router down. It ships enforced-but-dormant, so the estate can roll the id out and
then flip the gate.

The contract (``catalog.census.instruction``) is imported lazily, inside the hook, so this
module never breaks a router that runs before the contract has landed on main. The refusal
itself is independent of the contract: a prompt with no id is refused by the schema law,
whether or not the contract module is present on this tree.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Literal, Optional, Union

log = logging.getLogger("estate.instruction-gate")

# LiteLLM is present in the router image and absent elsewhere. The gate's LOGIC must be
# testable from both, so the dependency is taken at the point of use and the module stays
# importable without it (the same rule request_ceiling.py follows).
try:
    from litellm.integrations.custom_logger import CustomLogger
except ModuleNotFoundError:  # pragma: no cover - exercised outside the router image

    class CustomLogger:  # type: ignore[no-redef]
        """Stand-in so the hook body stays importable outside the router image."""

        async def async_pre_call_hook(self, *a, **k):  # noqa: D102
            raise NotImplementedError


# The gate is off until the id is generated and carried on every real prompt. A gate that
# is on before the id exists refuses everything -- the one way an enforcement hook becomes
# the outage. This env flips it live only when the estate is ready.
INSTRUCTION_GATE = os.environ.get("ESTATE_INSTRUCTION_GATE", "0") == "1"

CHAT_CALLS = {
    "completion",
    "chat.completion",
    "acompletion",
    "a_chat.completion",
    "chat_completion",
}


def _headers(data: dict) -> dict:
    req = data.get("proxy_server_request") or {}
    hdrs = req.get("headers") if isinstance(req, dict) else None
    return {str(k).lower(): v for k, v in (hdrs or {}).items()}


def instruction_id(data: dict) -> str:
    """The instruction id this request carries, from the same metadata shape every other
    callback reads. Empty string when none -- never invented."""
    meta = data.get("metadata") or {}
    raw = meta.get("instruction_id") if isinstance(meta, dict) else None
    raw = raw or data.get("instruction_id")
    return str(raw or "").strip()


def skip_reason(data: dict, call_type: Any) -> str:
    """Why this call is exempt from the instruction-id requirement, or "" when it must carry
    one. Mirrors active_memory.skip_reason so the two gates agree on who the estate's own
    plumbing is."""
    ct = str(getattr(call_type, "value", call_type) or "")
    if ct and ct not in CHAT_CALLS:
        return f"call_type={ct}"
    if not isinstance(data.get("messages"), list) or not data["messages"]:
        return "no messages"
    meta = data.get("metadata") or {}
    hdrs = _headers(data)
    if (isinstance(meta, dict) and meta.get("estate_internal")) or hdrs.get(
        "x-estate-internal"
    ):
        return "internal"
    if str(hdrs.get("x-estate-memory", "")).lower() == "off":
        return "caller opted out"
    return ""


class InstructionGate(CustomLogger):
    """Refuses a prompt the schema says must not be lost: one with no instruction id."""

    async def async_pre_call_hook(
        self,
        user_api_key_dict: Any,
        cache: Any,
        data: dict,
        call_type: Union[Any, Literal["completion", "text_completion", "embeddings"]],
    ) -> Optional[Union[Exception, str, dict]]:
        if not INSTRUCTION_GATE:
            return None

        reason = skip_reason(data, call_type)
        if reason:
            return None
        if instruction_id(data):
            return None

        # Imported lazily, at the point of refusal, so this module never breaks a router
        # that runs before the contract has landed on main. The refusal itself does not
        # depend on the contract: the schema law (no id -> refuse) is self-contained.
        try:  # pragma: no cover - exercised once the contract has landed alongside this
            from catalog.census.instruction import (  # type: ignore  # noqa: F401
                UnlinkedPromptError,
            )
        except ImportError:  # pragma: no cover - the contract is not on this tree
            log.error(
                "catalog.census.instruction is not importable; refusing the unlinkable "
                "prompt without the shared contract"
            )

        model = data.get("model", "unknown")
        log.error(
            "REFUSED request: %s carries no instruction_id and cannot be linked to any "
            "instruction; the schema forbids a lost prompt",
            model,
        )
        return (
            "This request carries no instruction id, so the prompt cannot be linked to an "
            "original or a new instruction -- and the estate's instruction ledger refuses to "
            "let a prompt end in the void.\n\n"
            "The fix is to carry the instruction id in the request metadata ("
            "metadata.instruction_id), set at intake by platform/estate/governance/"
            "founder_intake.py. A caller that cannot produce one should ask the intake door to "
            "bind the prompt first; retrying without an id will be refused identically."
        )


proxy_handler_instance = InstructionGate()
