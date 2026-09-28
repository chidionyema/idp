#!/usr/bin/env python3
"""triage-verdict -- read a hypotheses-race result, ask Jev yes/no on the top fix, print one verdict.

usage: triage-verdict.py <spec.json> <race-result.json>

Deterministic evidence first, Jev second: a hypothesis the probes falsified is never offered, and a
hypothesis with no fix intent is reported as "no governed fix" rather than improvised. Jev fails
closed: no key or no SDK -> escalated, and the verdict says the founder decides.
"""

import json
import sys
from pathlib import Path

REPO = Path.home() / "Documents" / "code" / "idp"
sys.path.insert(0, str(REPO / "mcp" / "plugins"))

spec = json.loads(Path(sys.argv[1]).read_text())
race = json.loads(Path(sys.argv[2]).read_text())
by_id = {h["id"]: h for h in spec["hypotheses"]}
falsified = {r["id"] for r in race["results"] if r["falsified"]}
# a probe that errored proved nothing either way: never offered as a cause, never counted as ruled out
unknown = {r["id"] for r in race["results"] if r.get("unknown")}
supported = [h for h in race["ranked"] if h not in falsified and h not in unknown]

print("evidence (posterior, supported=probe found it, unknown=probe could not look):")
for hid in race["ranked"]:
    mark = (
        "unknown"
        if hid in unknown
        else "falsified"
        if hid in falsified
        else "SUPPORTED"
    )
    print(
        f"  {race['posteriors'][hid]:.3f}  {mark:9}  {hid}: {by_id[hid]['statement']}"
    )

if not supported and unknown:
    print(
        f"VERDICT abstain: evidence unavailable for {', '.join(sorted(unknown))} -- "
        "re-gather; nothing is proposed from a probe that could not look"
    )
    sys.exit(2)
if not supported:
    print(
        "VERDICT none: every hypothesis falsified -- the fault is outside this model; widen the spec"
    )
    sys.exit(2)

if unknown:
    print(f"  ?? unknown, not ruled out: {', '.join(sorted(unknown))}")
fixable = [h for h in supported if by_id[h].get("fix")]
for h in supported:
    if not by_id[h].get("fix"):
        print(
            f"  !! {h} is supported but has no governed fix intent -- write one, do not improvise"
        )
if not fixable:
    print("VERDICT none: supported causes have no fix intent")
    sys.exit(2)

top = fixable[0]
fix, verify = by_id[top]["fix"], by_id[top]["verify"]
try:
    import jev

    ans = jev.jev_choice(
        repo="idp",
        layer="triage",
        decision_id=f"{spec.get('_id', Path(sys.argv[1]).stem)}:{top}",
        context={
            "hypothesis": by_id[top]["statement"],
            "posterior": race["posteriors"][top],
            "supported": supported,
            "fix_intent": fix,
            "verify_intent": verify,
        },
        question=f"Apply estate intent {fix} to repair: {by_id[top]['statement']}?",
        options=["yes", "no"],
    )
except Exception as e:  # noqa: BLE001 -- Jev unreachable is an escalation, never a yes
    ans = {"escalated": True, "_fallback": f"jev_error:{type(e).__name__}"}

if ans.get("escalated") or ans.get("choice") is None:
    print(
        f"VERDICT escalate: jev {ans.get('_fallback', 'below confidence floor')} -- founder decides: "
        f"estate-execute {fix}  then  estate-execute {verify}"
    )
elif ans["choice"] == "yes":
    print(
        f"VERDICT yes (jev conf {ans.get('confidence')}): estate-execute {fix}  then  estate-execute {verify}"
    )
else:
    print(f"VERDICT no (jev conf {ans.get('confidence')}): do not apply {fix}")
