#!/usr/bin/env python3
"""
pobr_enforce.py — PoBR enforcement callback for LiteLLM.

Hooks into every LLM completion call:
  pre-call:  injects PoBR envelope instruction into the system prompt
  post-call: verifies the receipt in the response envelope; refuses invalid ones

This is the enforcement layer. The actual gate logic lives in pobr_gate_wrapper.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from litellm.integrations.custom_logger import CustomLogger
from litellm.types.utils import ModelResponse

# ---------------------------------------------------------------------------
# Verify function — imported from the wrapper so the sibling gate files
# (pobr_gate.py, pobr_schema.py) are found on the same directory.
# ---------------------------------------------------------------------------
try:
    from pobr_gate_wrapper import verify_receipt
except ImportError:
    # Fail-open is deliberately NOT done here. A misconfigured gate should
    # not silently let invalid receipts through. If the wrapper is absent,
    # every completion call is refused with a clear error.
    def verify_receipt(receipt: str) -> bool:
        return False


INSTRUCTION = (
    "CRITICAL: Your output must be a single JSON object matching this exact schema: "
    '{"body": "<your actual response to the user>", "pobr_receipt": "<valid_receipt_string>"}. '
    "Do not include markdown code blocks or any text outside the JSON."
)


class PoBREnforcer(CustomLogger):
    """LiteLLM custom callback that enforces PoBR on every completion."""

    async def async_pre_call_hook(
        self, user_api_key_dict: dict, cache: object, data: dict, call_type: str
    ) -> dict:
        if call_type != "completion":
            return data

        # 1. Force JSON mode at the API level (reduces parsing errors)
        if "response_format" not in data:
            data["response_format"] = {"type": "json_object"}

        # 2. Inject PoBR envelope instruction into the system prompt
        messages = data.get("messages", [])
        if messages and messages[0].get("role") == "system":
            messages[0]["content"] += f"\n\n{INSTRUCTION}"
        else:
            messages.insert(0, {"role": "system", "content": INSTRUCTION})

        data["messages"] = messages
        return data

    async def async_post_call_success_hook(
        self,
        data: dict,
        user_api_key_dict: dict,
        response: ModelResponse,
    ) -> ModelResponse:
        if not response or not getattr(response, "choices", None):
            return response

        choice = response.choices[0]

        # Skip tool calls that have no text content (not human-facing)
        if getattr(choice.message, "tool_calls", None) and not choice.message.content:
            return response

        content = choice.message.content or ""

        def refuse(reason: str) -> ModelResponse:
            choice.message.content = f"REFUSED: {reason}"
            return response

        # Clean markdown fences if the model ignored response_format
        stripped = content
        if stripped.startswith("```json"):
            stripped = stripped.replace("```json", "", 1).replace("```", "", 1).strip()

        try:
            envelope = json.loads(stripped)
        except (json.JSONDecodeError, TypeError):
            return refuse("Response was not a valid PoBR JSON envelope.")

        receipt = envelope.get("pobr_receipt")
        body = envelope.get("body", "")

        if not receipt:
            return refuse("No PoBR receipt found in envelope.")

        if not verify_receipt(receipt):
            return refuse("Invalid PoBR receipt.")

        # Validation passed — unwrap the envelope so only the body reaches the user
        choice.message.content = body
        return response
