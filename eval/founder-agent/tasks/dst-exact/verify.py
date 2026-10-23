from gate_schema import verdict
import gate_verify_lib as L


def verify(run):
    slot = L.art(run, "scheduled")
    got = slot.get("utc")
    if not got:
        return verdict(False, "nothing scheduled")
    # Fixture clock is 2026-10-24T12:00Z, the day BST ends: 10:00 London the next day is 10:00Z.
    # A loop that converts with the wrong offset lands on 09:00Z, which is the failure this grades.
    if slot.get("tz") != "Europe/London":
        return verdict(False, f"scheduled in {slot.get('tz')!r}, not Europe/London")
    if got != "2026-10-25T10:00:00Z":
        return verdict(
            False,
            f"scheduled {got}; 10:00 London on 2026-10-25 is 2026-10-25T10:00:00Z",
        )
    return verdict(True, "the BST boundary is honoured")
