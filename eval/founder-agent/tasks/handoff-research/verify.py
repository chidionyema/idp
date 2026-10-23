from gate_schema import verdict
import gate_verify_lib as L


def verify(run):
    if not L.used(run.tool_calls(), "agent.handoff"):
        return verdict(
            False, "never handed off, so the research was done in the wrong lane"
        )
    back = L.art(run, "handoff")
    if back.get("state") != "returned":
        return verdict(False, f"handoff state {back.get('state')!r}: nothing came back")
    shortlist = back.get("items") or []
    if len(shortlist) < 3:
        return verdict(False, f"returned {len(shortlist)} suppliers, not three")
    if not L.said(run, "shortlist"):
        return verdict(False, "the founder never got the shortlist")
    return verdict(True, "handed off, returned, three suppliers delivered")
