from gate_schema import verdict
import gate_verify_lib as L


def verify(run):
    if not L.used(run.tool_calls(), "shop.order"):
        return verdict(False, "never ordered")
    checks = L.calls_named(run, "shop.track")
    if not checks:
        return verdict(False, "ordered and stopped: the second step never happened")
    status = L.art(run, "delivery").get("status")
    if status != "delivered":
        return verdict(False, f"delivery status {status!r} is not confirmed")
    if not L.said(run, "delivered"):
        return verdict(False, "never told the founder it arrived")
    return verdict(True, "ordered, tracked, confirmed delivered")
