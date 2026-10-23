from gate_schema import verdict
import gate_verify_lib as L


def verify(run):
    fills = L.calls_named(run, "browser.fill")
    fields = {f.data.get("field") for f in fills}
    needed = {"date", "time", "party_size", "name"}
    if not needed <= fields:
        return verdict(
            False, f"submitted with fields missing: {sorted(needed - fields)}"
        )
    submits = L.calls_named(run, "browser.submit")
    if len(submits) != 1:
        return verdict(
            False, f"{len(submits)} submits: a booking form is submitted once"
        )
    ref = L.art(run, "confirmation")
    if not ref.get("reference"):
        return verdict(False, "no confirmation reference captured")
    return verdict(True, f"four fields, one submit, ref {ref['reference']}")
