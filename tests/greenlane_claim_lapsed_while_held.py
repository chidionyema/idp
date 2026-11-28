"""Optimus measure: optimus.greenlane.claim_lapsed_while_held (idp#8742).

WHAT IS MEASURED. The Greenlane holds a lane's claim while the lane waits ("idp#5758 -- the
machine keeps the claim alive it is working on"). `bin/claim-gate` lapses that claim 15 minutes
after its heartbeat and then refuses the work as stale, so a held lane whose claim is left past
that window loses its paths to any rival that posts a claim. The reading is how many minutes of
a held lane's life the claim sat past the gate's lapse.

HOW IT IS READ. The shipped `Engine._heartbeat_lanes` and the shipped
`GitHubBackend.heartbeat` are driven, once per simulated minute, over a lane that is held for
`HOLD_MIN`. The only thing faked is the clock: the backend's comment store is a stub that
answers like the GitHub API (a POST appends, a PATCH edits, a GET lists), so the cadence, the
STAMP_AFTER refusal and the lapse all come from the code under measurement. The lapse window
itself is parsed from `bin/claim-gate`'s own `MAX_AGE`, never restated here.

    0   the machine's cadence always beat the gate's lapse: no held minute was stale
    n   n held minutes had a claim the gate would have refused as lapsed

    exit 2, nothing on stdout
        the lapse or the shipped cadence cannot be read here, so nothing was judged: a broken
        measurement is BLIND, never a 0 that reads as a clean window

    python3 tests/greenlane_claim_lapsed_while_held.py --optimus
        -> optimus.greenlane.claim_lapsed_while_held=0
"""

from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "optimus.greenlane.claim_lapsed_while_held"
HOLD_MIN = 180  # a lane held three hours: longer than any queue wait measured this year
CLAIM_ISSUE = "5755"
HEAD = "h" * 40


def _lapse_minutes() -> int:
    """`bin/claim-gate`'s own MAX_AGE, in minutes. Missing means BLIND, not 0."""
    source = (ROOT / "bin" / "claim-gate").read_text()
    hit = re.search(r"^MAX_AGE\s*=\s*timedelta\(minutes=(\d+)\)", source, re.M)
    if not hit:
        print(
            f"BLIND {NAME}: bin/claim-gate no longer declares MAX_AGE in minutes",
            file=sys.stderr,
        )
        raise SystemExit(2)
    return int(hit.group(1))


def _stub_module(backend_cls):
    """A GitHub backend whose comment store behaves like the API, and whose clock we move."""

    class _Datetime(dt.datetime):
        minutes = 0.0

        @classmethod
        def now(cls, tz=None):  # noqa: N805 - datetime's own classmethod signature
            return dt.datetime(2026, 11, 28, tzinfo=dt.timezone.utc) + dt.timedelta(
                minutes=cls.minutes
            )

    class Stub(backend_cls):
        def __init__(self) -> None:
            self.repo = "Mumchimp/idp"
            self.app_login = "idp-app[bot]"
            self.minutes = 0.0
            self.next_id = 1000
            now = _Datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            self.comments: list[dict] = [
                {"id": 1, "body": f"CLAIM agent=opencode paths=bin/x heartbeat={now}"}
            ]

        def now(self) -> float:
            return self.minutes

        def git(self, *args, check=True):
            if args[:2] == ("merge-base", "origin/main"):
                return "base"
            if args[:1] == ("log",):
                return f"fix: x\n\nClaim: Mumchimp/idp#{CLAIM_ISSUE}\nAgent: opencode\n"
            return ""

        def gh(self, path, method="GET", fields=None):
            body = (fields or {}).get("body", "")
            if method == "POST":
                self.comments.append({"id": self.next_id, "body": body})
                self.next_id += 1
                return {}
            if method == "PATCH":
                cid = int(path.rsplit("/", 1)[-1])
                for c in self.comments:
                    if c["id"] == cid:
                        c["body"] = body
                        return {"id": cid}
                return None
            if path == f"issues/{CLAIM_ISSUE}":
                return {"state": "open"}
            if path == f"issues/{CLAIM_ISSUE}/comments?per_page=100":
                return list(self.comments)
            return None

    return Stub, _Datetime


def measure() -> int:
    lapse = _lapse_minutes()
    sys.path.insert(0, str(ROOT))
    try:
        from greenlane import engine as E
        from greenlane import github as G
    except (
        Exception
    ) as exc:  # the shipped package cannot be imported here: nothing is judged
        print(f"BLIND {NAME}: greenlane will not import: {exc}"[:300], file=sys.stderr)
        raise SystemExit(2) from exc
    Stub, Datetime = _stub_module(G.GitHubBackend)
    G.datetime = Datetime  # the shipped heartbeat stamps from this name
    stub = Stub()
    state = E.State(lanes={"lane/x": E.Lane("lane/x", HEAD, seq=1)})
    green = E.Engine(stub, state, batch_size=1)
    epoch = dt.datetime(2026, 11, 28, tzinfo=dt.timezone.utc)

    def heartbeat_age(minute: float) -> float:
        newest = None
        for c in stub.comments:
            for line in (c.get("body") or "").splitlines():
                hit = re.match(r"^CLAIM .*heartbeat=(\S+)$", line.strip())
                if not hit:
                    continue
                when = dt.datetime.fromisoformat(hit.group(1).replace("Z", "+00:00"))
                newest = when if newest is None or when > newest else newest
        if newest is None:
            raise SystemExit(f"BLIND {NAME}: no CLAIM heartbeat was ever written"[:300])
        return (epoch + dt.timedelta(minutes=minute) - newest) / dt.timedelta(minutes=1)

    worst = 0.0
    lapsed = 0
    for minute in range(HOLD_MIN + 1):
        stub.minutes = float(minute)
        Datetime.minutes = float(minute)
        green._heartbeat_lanes()
        age = heartbeat_age(minute)
        worst = max(worst, age)
        if age > lapse:
            lapsed += 1
    print(
        f"  held {HOLD_MIN} min, lapse {lapse} min, oldest claim {worst:.0f} min, "
        f"stale for {lapsed} min",
        file=sys.stderr,
    )
    return lapsed


if __name__ == "__main__":
    if "--optimus" in sys.argv:
        print(f"{NAME}={measure()}")
    else:
        raise SystemExit(measure())
