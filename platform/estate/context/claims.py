"""claims -- the broker reads the SAME claim record CI reads, at request time.

WHY. AGENTS.md 5 says no work happens without a claim, and bin/claim-gate checks that in CI --
which is a check on the way to main, not a fence on the way to the context. The broker closes
that gap: a context request carries the caller's claim (issue and agent), the broker reads the
issue's CLAIM comments from the estate's own record, and refuses a request for a path the
caller does not hold.

ONE SOURCE OF TRUTH. The claim of record is the GitHub issue (AGENTS.md 5.1). The broker does
not keep a second ledger, and it does not trust the caller to describe its own claim: the paths
come from the issue, and the caller's only claim is "this is mine".

THE SAME REGEX AS THE GATE. The pattern below is bin/claim-gate's, copied rather than imported
because the gate is a script and the broker is a service; tests/test_estate_context_claims.py
reads bin/claim-gate and fails if the two drift apart, so the copy cannot rot silently.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import re
from typing import Iterable, Mapping, Sequence

from .broker import Decision, path_allowed

# bin/claim-gate's CLAIM, verbatim (line 71). Kept in step by a test that reads the gate.
CLAIM = re.compile(
    r"^CLAIM\s+agent=(?P<agent>\S+)\s+(?:model=\S+\s+)?paths=(?P<paths>\S+)\s+"
    r"heartbeat=(?P<hb>\S+)\s*$",
    re.M,
)

# The heartbeat's own rule, from bin/claim-gate: two hours is the life of a claim. A claim with
# no heartbeat for that long is released, and the next agent may take the issue.
HEARTBEAT_MAX_AGE = dt.timedelta(hours=2)


@dataclasses.dataclass(frozen=True)
class Claim:
    """One CLAIM comment: who, which paths, and when it was last alive."""

    agent: str
    paths: tuple[str, ...]
    heartbeat: dt.datetime | None
    raw: str = ""

    @property
    def alive(self) -> bool:
        """True while the heartbeat is inside its two hours."""
        if self.heartbeat is None:
            return False
        return dt.datetime.now(dt.timezone.utc) - self.heartbeat < HEARTBEAT_MAX_AGE


def parse_claims(text: str) -> list[Claim]:
    """Every CLAIM comment in a body of comment text."""
    out: list[Claim] = []
    for m in CLAIM.finditer(text or ""):
        hb: dt.datetime | None = None
        try:
            hb = dt.datetime.fromisoformat(m.group("hb").replace("Z", "+00:00"))
            if hb.tzinfo is None:
                hb = hb.replace(tzinfo=dt.timezone.utc)
        except ValueError:
            hb = None
        out.append(
            Claim(
                agent=m.group("agent"),
                paths=tuple(p for p in m.group("paths").split(",") if p),
                heartbeat=hb,
                raw=m.group(0),
            )
        )
    return out


def paths_held_by(claims: Iterable[Claim], agent: str) -> list[str]:
    """The union of the paths an agent holds across all of its claims.

    The union, not the newest: an agent that posts a second CLAIM with more paths holds both
    sets until it says otherwise. That is how bin/claim-gate reads it too.
    """
    held: list[str] = []
    for c in claims:
        if c.agent != agent:
            continue
        for p in c.paths:
            if p not in held:
                held.append(p)
    return held


def paths_held_by_others(claims: Iterable[Claim], agent: str) -> list[str]:
    """The paths another LIVE agent holds. A request for one of these is a collision.

    LIVE, and only live: AGENTS.md 5.4 -- "A claim with no heartbeat for 2 hours is released;
    the next agent may take the issue." A dead agent's claim holds nothing, so it cannot fence
    the door forever. Measured 2026-10-28: issue #7262 carried a claim from `pi` whose last
    heartbeat was 17 hours old, and the door refused the live holder's own request because of
    it. A claim that is not alive is not a holder.
    """
    held: list[str] = []
    for c in claims:
        if c.agent == agent or not c.alive:
            continue
        for p in c.paths:
            if p not in held:
                held.append(p)
    return held


def holder_of(claims: Iterable[Claim], path: str, agent: str) -> Claim | None:
    """The live claim of ANOTHER agent that holds `path`; the newest such claim wins.

    Newest first, because that is the order the estate reads claims in: bin/claim-gate looks
    at the newest CLAIM comment on the issue and the change must belong to that agent. The
    door reads it the same way, so the gate and the door cannot disagree about who holds a
    file.
    """
    for c in reversed(list(claims)):
        if c.agent == agent or not c.alive:
            continue
        if any(path_allowed(path, [p]) for p in c.paths):
            return c
    return None


def verify_claim(
    *,
    issue_state: str,
    issue_comments: str,
    agent: str,
    requested_paths: Sequence[str] = (),
    issue_number: int | None = None,
) -> Decision:
    """Is this caller allowed to read what it asked for?

    The rules, in the order they bite:

    1. The issue must be OPEN. A closed issue released its claim (AGENTS.md 5.6).
    2. The agent must hold a claim on it. No claim, no context.
    3. The requested paths must be inside the claim. All-or-nothing: a request that names one
       path outside is refused whole, because a partially served request is how a boundary
       leaks.
    4. Another LIVE agent holding the same path is a collision, and the request is refused --
       the founder's rule is that two agents never work the same files, and that must hold at
       the door as well as in CI. LIVE is what makes it a collision: a claim whose heartbeat
       lapsed is released (AGENTS.md 5.4) and holds nothing, so it cannot fence the door. A
       caller's OWN lapsed claim does not refuse either, exactly as bin/claim-gate stopped
       doing on 2026-10-14: the heartbeat is what makes a claim live, and until somebody else
       claims the files, nobody else holds them.
    """
    if issue_state.lower() != "open":
        return Decision(
            False,
            "PATH_REFUSED",
            f"issue #{issue_number} is {issue_state}; a closed issue released its claim",
            {"issue": issue_number, "state": issue_state},
        )
    claims = parse_claims(issue_comments)
    mine = paths_held_by(claims, agent)
    if not mine:
        return Decision(
            False,
            "PATH_REFUSED",
            f"agent {agent} holds no claim on issue #{issue_number}",
            {"issue": issue_number, "agent": agent},
        )
    theirs = paths_held_by_others(claims, agent)
    for path in requested_paths:
        if not path_allowed(path, mine):
            return Decision(
                False,
                "PATH_REFUSED",
                f"{path} is not inside the claim {agent} holds on issue #{issue_number}",
                {"issue": issue_number, "agent": agent, "path": path, "claimed": mine},
            )
        if any(path_allowed(path, [t]) for t in theirs):
            holder = holder_of(claims, path, agent)
            return Decision(
                False,
                "PATH_REFUSED",
                f"{path} is claimed by another agent on issue #{issue_number}",
                {
                    "issue": issue_number,
                    "agent": agent,
                    "path": path,
                    "holder": holder.agent if holder else None,
                    "holder_heartbeat": holder.heartbeat.isoformat()
                    if holder and holder.heartbeat
                    else None,
                },
            )
    return Decision(
        True,
        "ALLOW",
        f"agent {agent} holds the claim on issue #{issue_number}",
        {
            "issue": issue_number,
            "agent": agent,
            "claimed": mine,
            "requested": list(requested_paths),
        },
    )


def claim_state(
    *,
    issue_state: str,
    issue_comments: str,
    agent: str,
    issue_number: int | None = None,
) -> dict[str, object]:
    """A small status block the broker's status tool returns: who holds what, and until when."""
    claims = parse_claims(issue_comments)
    mine = [c for c in claims if c.agent == agent]
    return {
        "issue": issue_number,
        "issue_state": issue_state,
        "agent": agent,
        "holds": paths_held_by(claims, agent),
        "others_hold": paths_held_by_others(claims, agent),
        "heartbeat": mine[-1].heartbeat.isoformat()
        if mine and mine[-1].heartbeat
        else None,
        "alive": bool(mine and mine[-1].alive),
    }


def github_comment_bodies(comments: Sequence[Mapping[str, object]]) -> str:
    """The bodies of the issue's comments, joined for the regex to run over."""
    return "\n".join(str(c.get("body") or "") for c in comments)
