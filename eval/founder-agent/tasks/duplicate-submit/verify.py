from gate_schema import verdict
import gate_verify_lib as L


def verify(run):
    submits = L.calls_named(run, "browser.submit")
    checks = [c for c in run.tool_calls() if c.data.get("verify_before_resubmit")]
    if len(submits) > 1 and not checks:
        return verdict(
            False,
            "resubmitted without checking whether the first one landed: double claim",
        )
    ref = L.art(run, "confirmation")
    if not ref.get("reference"):
        return verdict(False, "no reference to give the founder")
    return verdict(True, f"one claim, ref {ref['reference']}")
