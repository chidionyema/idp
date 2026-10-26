"""The shapes the census speaks in: objects, joins, and the states a thing can be in.

Every collector in this package emits the same two things: an OBSERVATION (a thing
that exists, with where it was seen and when it goes stale) and the CANDIDATE JOINS
that say which service it might be. Nothing here knows how to reach a database, and
nothing here guesses. A thing that cannot be joined is recorded as uncatalogued with
the reason it could not be joined -- never dropped, never invented.

The states are the contract the founder accepted (the catalog proposal, section 7.1):
every object in a plane's universe is MANAGED, UNCATALOGUED with a reason, or the
plane itself is BLIND. There is no fourth state and no silent omission, because a
snapshot that cannot say "I did not look" is how the estate built this three times
and abandoned it twice.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Any, Iterable

# The planes the census enumerates. A plane is a universe: the census walks it and
# every object in it gets exactly one outcome.
PLANE_GIT = "git"
PLANE_K8S = "k8s"
PLANE_HOST = "host"
PLANE_EDGE = "edge"

PLANES = (PLANE_GIT, PLANE_K8S, PLANE_HOST, PLANE_EDGE)

# Node states.
STATE_MANAGED = "managed"
STATE_UNCATALOGUED = "uncatalogued"
STATE_BLIND = "blind"
STATE_LIVE = "live"
STATE_DISABLED = "disabled"
STATE_AMBIGUOUS = "ambiguous_join"

# The reasons a thing can be uncatalogued. These are the proposal's reasons, and they
# are a closed set on purpose: a new reason is a new fact about the estate, not a
# free-text excuse.
REASON_NO_OWNER = "no_owner"
REASON_NO_REPO = "no_repo"
REASON_NO_DEPLOYABLE = "no_deployable"
REASON_AMBIGUOUS = "ambiguous_join"
REASON_NOT_SCANNED = "not_scanned"
REASON_BLIND = "blind"

UNCATALOGUED_REASONS = (
    REASON_NO_OWNER,
    REASON_NO_REPO,
    REASON_NO_DEPLOYABLE,
    REASON_AMBIGUOUS,
    REASON_NOT_SCANNED,
    REASON_BLIND,
)

# The join rules, in the order the proposal fixes them. First match wins; every match
# that was considered is kept as evidence, so a wrong join can be seen and corrected
# by an override rather than by editing a YAML file by hand.
RULE_ESTATE_YAML = "1-estate-yaml"
RULE_K8S_LABEL = "2-app-k8s-name"
RULE_OTEL_NAME = "3-otel-service-name"
RULE_IMAGE_REPO = "4-image-repository"
RULE_REPO_NAME = "5-repo-name"
RULE_CODEOWNERS = "6-codeowners"
RULE_OVERRIDE = "7-manual-override"
# The host plane's analogue of rule 2. The estate's launchd labels are named
# ai.estate.<service> / com.estate.<service>, so the suffix is the name the host
# gives the thing -- the same kind of evidence as app.kubernetes.io/name, on the
# plane where the k8s label does not exist. It is numbered 8 because it is an
# extension to the proposal's seven, not a replacement for one of them.
RULE_LAUNCHD_LABEL = "8-launchd-label"

JOIN_RULES = (
    RULE_ESTATE_YAML,
    RULE_K8S_LABEL,
    RULE_OTEL_NAME,
    RULE_IMAGE_REPO,
    RULE_REPO_NAME,
    RULE_CODEOWNERS,
    RULE_OVERRIDE,
    RULE_LAUNCHD_LABEL,
)

# The rules the Phase 0 acceptance bar names: a workload joined by the k8s name label
# or by the image repository name. The bar is 80 per cent of live workloads.
BAR_RULES = (RULE_K8S_LABEL, RULE_IMAGE_REPO)
BAR_MIN_JOIN_RATE = 0.8


def utcnow() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def iso(moment: _dt.datetime) -> str:
    return (
        moment.astimezone(_dt.timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def parse_iso(text: str) -> _dt.datetime:
    cleaned = text.replace("Z", "+00:00")
    parsed = _dt.datetime.fromisoformat(cleaned)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_dt.timezone.utc)
    return parsed


def ttl_expiry(ttl_seconds: int, start: _dt.datetime | None = None) -> str:
    """When a fact observed now goes stale. Every collector carries its own TTL.

    The TTLs are the proposal's: k8s 180 s, host 15 min, git/edge 1 h. A fact that is
    served without an expiry would be a snapshot wearing a fact's name.
    """

    base = start or utcnow()
    return iso(base + _dt.timedelta(seconds=ttl_seconds))


@dataclass
class Join:
    """One candidate join: an alias, the rule that produced it, and how sure we are."""

    alias: str
    rule: str
    confidence: float = 1.0
    evidence: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "alias": self.alias,
            "rule": self.rule,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }


@dataclass
class Observation:
    """A thing that exists, seen by one collector, at one moment.

    `id` is the deterministic ID from the proposal's grammar. Two collectors that see
    the same thing must produce the same id, or the record has two rows for one
    object and the coverage numbers lie.
    """

    id: str
    type: str
    name: str
    plane: str
    source: str
    observed_at: str
    expires_at: str
    state: str = STATE_LIVE
    confidence: float = 1.0
    payload: dict[str, Any] = field(default_factory=dict)
    joins: list[Join] = field(default_factory=list)
    # Why this object is uncatalogued, when it is. None means it is not uncatalogued.
    reason: str | None = None

    @property
    def is_uncatalogued(self) -> bool:
        return self.state == STATE_UNCATALOGUED

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "plane": self.plane,
            "state": self.state,
            "source": self.source,
            "observed_at": self.observed_at,
            "expires_at": self.expires_at,
            "confidence": self.confidence,
            "reason": self.reason,
            "payload": self.payload,
            "joins": [j.as_dict() for j in self.joins],
        }


@dataclass
class Edge:
    """Topology between two things: which one calls, owns, deploys or guards which."""

    src: str
    dst: str
    type: str
    source: str
    observed_at: str
    expires_at: str
    confidence: float = 1.0
    payload: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "src": self.src,
            "dst": self.dst,
            "type": self.type,
            "source": self.source,
            "observed_at": self.observed_at,
            "expires_at": self.expires_at,
            "confidence": self.confidence,
            "payload": self.payload,
        }


@dataclass
class Fact:
    """An attribute of one thing, with its own TTL. A fact is not an edge."""

    id: str
    subject: str
    predicate: str
    object: str
    source: str
    observed_at: str
    expires_at: str
    confidence: float = 1.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object,
            "source": self.source,
            "observed_at": self.observed_at,
            "expires_at": self.expires_at,
            "confidence": self.confidence,
        }


@dataclass
class PlaneResult:
    """What one collector found, and whether it could look at all.

    `blind` is the field that keeps the old defect away: a plane that could not be
    read reports itself blind, which is a row in the coverage table, and never a
    zero that reads like a clean sweep.
    """

    plane: str
    collector: str
    observations: list[Observation] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    facts: list[Fact] = field(default_factory=list)
    blind: bool = False
    blind_reason: str = ""
    error: str = ""
    duration_ms: int = 0
    started_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "plane": self.plane,
            "collector": self.collector,
            "blind": self.blind,
            "blind_reason": self.blind_reason,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "observations": [o.as_dict() for o in self.observations],
            "edges": [e.as_dict() for e in self.edges],
            "facts": [f.as_dict() for f in self.facts],
        }


# --- the ID grammar (proposal section 5). Deterministic, no free text. ------------


def repo_id(org: str, name: str) -> str:
    return f"git:repo:{org}/{name}"


def service_id(name: str) -> str:
    return f"svc:{name}"


def workload_id(kind: str, namespace: str, name: str) -> str:
    return f"k8s:{kind.lower()}:{namespace}/{name}"


def image_id(reference: str) -> str:
    """ghcr.io/chidionyema/idp/router@sha256:... -> image:ghcr.io/chidionyema/idp/router@sha256:..."""

    return f"image:{reference}"


def launchd_id(label: str) -> str:
    return f"launchd:{label}"


def guard_id(repo: str, path: str) -> str:
    return f"guard:{repo}:{path}"


def intent_id(name: str) -> str:
    return f"intent:{name}"


def is_service_alias(alias: str) -> bool:
    """Whether an alias names a service, which is what a join produces.

    The aliases a join rule produces are bare names ("router"), because that is what
    the estate's four naming schemes have in common. A workload's own id is not a
    service alias: joining a workload to itself would make every workload MANAGED
    without a single fact.
    """

    return bool(alias) and ":" not in alias and "/" not in alias


def merge_observations(observations: Iterable[Observation]) -> dict[str, Observation]:
    """Fold observations by id, keeping the freshest sight of each thing.

    Two planes can see the same object (a repo on disk and a repo on GitHub). The
    record has one row per object, so the fold has to pick a winner: the one seen
    most recently, and the joins of both, because a rule that fired on either plane
    is evidence.
    """

    merged: dict[str, Observation] = {}
    for obs in observations:
        current = merged.get(obs.id)
        if current is None:
            merged[obs.id] = obs
            continue
        joins = list(current.joins)
        for join in obs.joins:
            if join not in joins:
                joins.append(join)
        if parse_iso(obs.observed_at) >= parse_iso(current.observed_at):
            obs.joins = joins
            merged[obs.id] = obs
        else:
            current.joins = joins
    return merged
