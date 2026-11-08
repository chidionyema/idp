"""Router recovery declaration is the source of the generated workflow manifest.

Cutover is intentionally excluded until snapshot/reversal of the Cloudflare route,
vault and object have been exercised. Candidate restoration is not production cutover.
"""

from __future__ import annotations

from typing import Any


class RouterRecovery:
    ID = "router-recovery"
    VERSION = "1.0.0"
    OWNER = "estate/platform"
    SURFACES = ("cli", "mcp", "founder", "voice")
    SEARCH_TERMS = (
        "recover router",
        "restore model routing",
        "repair litellm",
        "router candidate",
    )
    INPUT_SCHEMA = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["repository", "candidate_url"],
        "properties": {
            "repository": {"const": "chidionyema/idp"},
            "candidate_url": {"const": "https://llm-recovery.mumchimp.com"},
            "cutover": {"const": False},
        },
    }
    OUTPUT_SCHEMA = {
        "type": "object",
        "required": ["status", "run_id", "plan_hash", "steps"],
        "properties": {
            "status": {"enum": ["verified", "failed", "denied", "blocked"]},
            "run_id": {"type": "string"},
            "plan_hash": {"type": "string"},
            "steps": {"type": "object"},
        },
    }

    @classmethod
    def authorized(cls, actor: str, inputs: dict[str, Any]) -> bool:
        # The caller MUST pass through an independently authenticated gateway.
        # This function is a second fence: only service identities can start
        # the workflow. No voice/client-provided actor bypasses gateway auth.
        return actor.startswith("svc:estate-") and inputs.get("cutover") is not True

    @classmethod
    def manifest(cls) -> dict[str, Any]:
        # This is created directly from the workflow class/step implementation.
        return {
            "id": cls.ID,
            "version": cls.VERSION,
            "owner": cls.OWNER,
            "summary": "Restore candidate LLM router and independently verify model completion",
            "surfaces": list(cls.SURFACES),
            "search_terms": list(cls.SEARCH_TERMS),
            "input_schema": cls.INPUT_SCHEMA,
            "output_schema": cls.OUTPUT_SCHEMA,
            "required_capabilities": [
                "github.actions.dispatch",
                "github.actions.read",
                "router.probe",
            ],
            "required_permissions": [
                "actions:write",
                "actions:read",
                "router:candidate-probe",
            ],
            "max_concurrency": 2,
            "cost_class": "metered",
            "latency_class": "minutes",
            "budget": {"max_model_output_tokens": 8, "max_wall_s": 1800},
            "verification": [
                "github-run-conclusion",
                "candidate-liveliness",
                "candidate-models",
                "candidate-completion",
            ],
            "rollback": {
                "supported": False,
                "reason": "existing GitHub action has no durable candidate snapshot/undo contract",
            },
            "examples": ["recover router", "restore LLM model routing"],
            "steps": [
                s["id"]
                for s in cls.compile_steps(
                    {
                        "repository": "chidionyema/idp",
                        "candidate_url": "https://llm-recovery.mumchimp.com",
                    }
                )
            ],
        }

    @classmethod
    def compile_steps(cls, inputs: dict[str, Any]) -> list[dict[str, Any]]:
        def node(
            id: str, action: str, deps: list[str], timeout: int = 45, attempts: int = 1
        ) -> dict[str, Any]:
            return {
                "id": id,
                "action": action,
                "deps": deps,
                "timeout_s": timeout,
                "max_attempts": attempts,
                "retry_class": "transient-read" if attempts > 1 else "none",
                "approval": False,
                "inputs": {
                    "repository": inputs["repository"],
                    "candidate_url": inputs["candidate_url"],
                },
            }

        # Two remote probes fan out after the external job completes. Completion
        # needs the model returned by the model-list probe, never a guessed model.
        return [
            node("dispatch", "github.router_dispatch", []),
            node("observe", "github.router_observe", ["dispatch"], timeout=600),
            node("health", "router.health", ["observe"], attempts=3),
            node("models", "router.models", ["observe"], attempts=3),
            node("completion", "router.completion", ["health", "models"], timeout=90),
        ]
