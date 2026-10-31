# ruff: noqa
# fmt: off
"""Founder-prompt rule: every founder prompt must bind to exactly one protocol."""
from __future__ import annotations

from dataclasses import dataclass

from .model import ProtocolId
from .registry import REGISTRY


@dataclass(frozen=True)
class FounderPrompt:
    id: str
    text: str
    protocol_binding: ProtocolId | None = None


class GenesisError(Exception):
    pass


def validate(fp: FounderPrompt) -> list[str]:
    v = []
    if not fp.text.strip():
        v.append("founder prompt is empty")
    if fp.protocol_binding is None:
        v.append("missing Protocol_Binding")
    elif fp.protocol_binding not in REGISTRY:
        v.append(f"unknown protocol {fp.protocol_binding!r}")
    return v


def compile_system_prompt(fp: FounderPrompt) -> str:
    """Refuses to compile an unbound prompt, so an agent cannot be created without one."""
    problems = validate(fp)
    if problems:
        raise GenesisError(f"{fp.id}: " + "; ".join(problems))
    proto = REGISTRY[fp.protocol_binding]
    order = " -> ".join(s.value for s in proto.stages)
    return (
        f"Protocol_Binding: [{proto.id.value}]\n"
        f"Pipeline (enforced, no skipping): {order}\n"
        f"{proto.contract}\n\n{fp.text}"
    )


def audit(prompts: list[FounderPrompt]) -> dict[str, list[str]]:
    """Run in CI: returns {prompt_id: violations} for every non-compliant founder prompt."""
    return {p.id: v for p in prompts if (v := validate(p))}
