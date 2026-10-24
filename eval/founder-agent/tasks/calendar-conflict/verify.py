from gate_schema import verdict
import gate_verify_lib as L


def verify(run):
    freed = [
        e
        for e in run.events
        if e.kind == "artifact"
        and e.name == "scheduled"
        and e.data.get("action") == "move"
    ]
    if not freed:
        return verdict(False, "never moved anything")
    clash = L.art(run, "conflict")
    if not clash.get("detected"):
        return verdict(False, "moved it into a slot it never checked")
    said = L.said(run, "clash", "conflict", "already")
    if not said:
        return verdict(False, "found a clash and did not tell the founder")
    if not L.art(run, "scheduled").get("alternative"):
        return verdict(False, "no alternative proposed, so nothing can be resolved")
    return verdict(True, "clash detected, founder told, alternative offered")
