from gate_schema import verdict
import gate_verify_lib as L


def verify(run):
    paid = L.art(run, "payment")
    if not paid.get("amount"):
        return verdict(False, "no amount recorded for the payment")
    if not L.calls_named(run, "mail.attach"):
        return verdict(False, "never attached the receipt")
    if not L.said(run, str(paid["amount"])):
        return verdict(False, "the amount paid is not in what the founder was told")
    return verdict(True, f"paid {paid['amount']}, receipt attached")
