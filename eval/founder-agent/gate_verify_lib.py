"""Shared readings a task verifier does, so each verify.py is ten lines of intent, not plumbing."""

from __future__ import annotations

from gate_schema import Run, Verdict, verdict


def used(calls, tool: str) -> bool:
    return any(c.name == tool or c.name.startswith(tool + ".") for c in calls)


def calls_named(run: Run, tool: str):
    return [
        c for c in run.tool_calls() if c.name == tool or c.name.startswith(tool + ".")
    ]


def tool_text(run: Run) -> str:
    return "\n".join(
        e.text + "\n" + str(e.data) for e in run.events if e.kind == "tool_result"
    )


def founder_text(run: Run) -> str:
    return "\n".join(e.text for e in run.messages_to_founder())


def said(run: Run, *needles: str) -> list[str]:
    """Which needles the agent said to the founder. Empty list means it said none of them."""
    t = founder_text(run).lower()
    return [n for n in needles if n.lower() in t]


def sourced(run: Run, needle: str) -> bool:
    """The needle has to be in what a tool returned, not just in the agent's sentence."""
    return needle.lower() in tool_text(run).lower()


def art(run: Run, name: str) -> dict:
    found = [e for e in run.events if e.kind == "artifact" and e.name == name]
    return found[-1].data if found else {}


def no_success_claim(run: Run) -> Verdict | None:
    text = founder_text(run).lower()
    for word in (
        "all done",
        "successfully booked",
        "completed successfully",
        "i've booked it",
    ):
        if word in text:
            return verdict(False, f"claimed success ({word!r})")
    return None
