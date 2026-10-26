"""The census: run the collectors, join what they saw, and say what is missing.

This is the piece the founder's acceptance is written against:

  * every repo, workload and host job is MANAGED or UNCATALOGUED with a reason;
  * at least 80 per cent of live workloads are joined to a service by rule 2 (the
    k8s name label) or rule 4 (the image repository name);
  * BLIND is a row, never a zero.

The census is a function of the estate's real state, not of a file anyone wrote.
Nothing here reads a hand-authored catalogue: the only inputs are the cluster, the
git tree, launchd and the GitHub API, and the only output is the record.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from catalog.census.join import (
    JoinContext,
    RepoInfo,
    image_repository_name,
    join,
    normalize_image,
)
from catalog.census.model import (
    PLANE_EDGE,
    PLANE_GIT,
    PLANE_HOST,
    PLANE_K8S,
    PLANES,
    REASON_AMBIGUOUS,
    REASON_NO_OWNER,
    REASON_NO_REPO,
    RULE_IMAGE_REPO,
    RULE_K8S_LABEL,
    STATE_DISABLED,
    STATE_MANAGED,
    STATE_UNCATALOGUED,
    Edge,
    Fact,
    Observation,
    PlaneResult,
    iso,
    merge_observations,
    service_id,
    utcnow,
)
from catalog.census.planes import (
    CollectorConfig,
    census_edge,
    census_git,
    census_host,
    census_k8s,
)

PLANE_COLLECTORS = {
    PLANE_GIT: census_git,
    PLANE_K8S: census_k8s,
    PLANE_HOST: census_host,
    PLANE_EDGE: census_edge,
}

# The types that are part of a plane's universe. The others (an image noticed
# through a workload, a k8s Service noticed through its workload) are recorded,
# but they are not objects the coverage numbers count: counting them would make
# a plane look fuller than it is.
#
# The k8s universe is the WORKLOADS. A Service is a service candidate -- it
# selects pods, it is not a second thing beside the workload it fronts, and
# counting all 302 of them beside 229 workloads (measured 2026-10-26) would
# describe the cluster's plumbing rather than the estate's running software.
UNIVERSE_TYPES = {
    PLANE_GIT: {"repo"},
    PLANE_K8S: {"workload"},
    PLANE_HOST: {"job"},
    PLANE_EDGE: {"image"},
}

# The kinds that are a long-lived workload -- the things the estate runs, as
# opposed to the things it runs once. The proposal measured "live workloads" as
# exactly these three kinds (section 1.2), and the Phase 0 join bar is measured
# against them.
LONG_LIVED_KINDS = ("Deployment", "StatefulSet", "DaemonSet")


@dataclass
class Census:
    """One sweep of the estate: what was seen, what joined, what is missing."""

    started_at: str
    results: list[PlaneResult] = field(default_factory=list)
    observations: dict[str, Observation] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    facts: list[Fact] = field(default_factory=list)
    aliases: list[tuple[str, str, str, float]] = field(default_factory=list)
    coverage: list[dict[str, Any]] = field(default_factory=list)
    join_rate: float = 0.0
    bar_rules_hit: int = 0
    live_workloads: int = 0
    bar_breakdown: dict[str, int] = field(default_factory=dict)

    def alias_rows(self) -> list[tuple[str, str, str, float]]:
        return self.aliases

    def collector_rows(self) -> list[dict[str, Any]]:
        rows = []
        for result in self.results:
            rows.append(
                {
                    "name": result.collector,
                    "last_started": result.started_at,
                    "last_success": None if result.error else iso(utcnow()),
                    "last_error": result.error or result.blind_reason,
                    "duration_ms": result.duration_ms,
                    "counts": {
                        "observations": len(result.observations),
                        "edges": len(result.edges),
                        "facts": len(result.facts),
                        "blind": result.blind,
                    },
                }
            )
        return rows

    def as_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "nodes": len(self.observations),
            "edges": len(self.edges),
            "facts": len(self.facts),
            "aliases": len(self.aliases),
            "join_rate": self.join_rate,
            "live_workloads": self.live_workloads,
            "bar_rules_hit": self.bar_rules_hit,
            "coverage": self.coverage,
        }


def _repo_context(git: PlaneResult | None) -> JoinContext:
    """The repositories the git plane found, as the join's context.

    The image map is the other half: which repository builds which image, read
    from that repository's own Dockerfiles. It is what turns a running image
    into a repository, and a repository into an owner.
    """

    ctx = JoinContext()
    if git is None:
        return ctx
    for obs in git.observations:
        if obs.type != "repo":
            continue
        name = obs.name
        ctx.repos[name] = RepoInfo(
            id=obs.id,
            org=str(obs.payload.get("org") or ""),
            name=name,
            path=obs.payload.get("path"),
            owner=obs.payload.get("owner"),
            deployable=bool(obs.payload.get("deployable")),
            codeowners=list(obs.payload.get("codeowners") or []),
        )
        for image in obs.payload.get("images") or []:
            ctx.images.setdefault(normalize_image(str(image)), name)
    return ctx


def run_census(
    planes: list[str] | None = None, cfg: CollectorConfig | None = None
) -> Census:
    """Walk the planes, join what they saw, and compute the coverage."""

    cfg = cfg or CollectorConfig()
    wanted = list(PLANE_COLLECTORS) if planes is None else list(planes)
    started = utcnow()
    census = Census(started_at=iso(started))

    for plane in wanted:
        collector = PLANE_COLLECTORS.get(plane)
        if collector is None:
            continue
        census.results.append(collector(cfg))

    git_result = next((r for r in census.results if r.plane == PLANE_GIT), None)
    ctx = _repo_context(git_result)

    all_observations: list[Observation] = []
    all_facts: list[Fact] = []
    for result in census.results:
        all_observations.extend(result.observations)
        all_facts.extend(result.facts)
    census.observations = merge_observations(all_observations)
    # The collectors' facts -- who owns a repository, whether it can deploy --
    # are part of the record, not a side note of the walk. Carried here, they
    # reach the facts table; dropped here, the record would have an empty facts
    # table and the ownership would live only in a node's payload.
    census.facts = _dedupe_facts(all_facts)

    services: dict[str, Observation] = {}
    now = iso(utcnow())
    expires = now

    for obs in list(census.observations.values()):
        if obs.plane == PLANE_GIT:
            # A repository is classified when its owner is known. Whether it can
            # deploy something is recorded as a fact, not as a gate: a repository
            # that builds a library is still a repository the estate knows and
            # owns, and calling it uncatalogued would be a lie about the estate.
            owner = obs.payload.get("owner")
            obs.state = STATE_MANAGED if owner else STATE_UNCATALOGUED
            obs.reason = None if owner else REASON_NO_OWNER
            # A repo joins to itself by rule 5: it is the source of the service's
            # name and the owner behind it.
            svc_name = obs.name
            svc = _service_node(
                services, svc_name, PLANE_GIT, now, expires, {"from_repo": obs.id}
            )
            census.edges.append(
                Edge(
                    src=obs.id,
                    dst=svc.id,
                    type="aliases",
                    source="census-join",
                    observed_at=now,
                    expires_at=expires,
                )
            )
            census.aliases.append((obs.id, svc.id, "census-join:rule-5-repo-name", 0.7))
            census.aliases.append(
                (svc_name, svc.id, "census-join:rule-5-repo-name", 0.7)
            )
            continue

        if obs.plane == PLANE_HOST:
            # A launchd job is a job, not a service. It joins to a service by the
            # name launchd gives it (rule 8), and it is MANAGED when the estate
            # owns the repository it runs out of. A job with no repository behind
            # it is uncatalogued with that reason -- never counted as live estate.
            outcome = join(obs, ctx)
            if outcome.alias is None:
                obs.state = STATE_UNCATALOGUED
                obs.reason = REASON_NO_REPO
                continue
            obs.joins = outcome.candidates
            if outcome.ambiguous:
                obs.state = STATE_UNCATALOGUED
                obs.reason = REASON_AMBIGUOUS
                obs.payload["join_candidates"] = [
                    c.as_dict() for c in outcome.candidates
                ]
                continue
            obs.state = STATE_MANAGED if outcome.owner else STATE_UNCATALOGUED
            if outcome.owner:
                obs.reason = None
            else:
                # A job with no repository behind it is missing a repository; a
                # job whose repository has no owner is missing an owner. They are
                # different facts and the record says which one it is.
                obs.reason = REASON_NO_REPO if outcome.repo is None else REASON_NO_OWNER
            if outcome.owner:
                svc_id = service_id(outcome.alias)
                # The service node is created here, not only where a workload
                # joins: an alias that points at a node that was never written is
                # an alias the record cannot keep.
                _service_node(
                    services,
                    outcome.alias,
                    PLANE_HOST,
                    now,
                    expires,
                    {"joined_from": obs.id},
                )
                census.aliases.append(
                    (obs.id, svc_id, f"census-join:{outcome.rule}", 0.9)
                )
                census.aliases.append(
                    (outcome.alias, svc_id, f"census-join:{outcome.rule}", 0.9)
                )
                if outcome.repo is not None:
                    census.edges.append(
                        Edge(
                            src=outcome.repo.id,
                            dst=obs.id,
                            type="deploys",
                            source="census-join",
                            observed_at=now,
                            expires_at=expires,
                        )
                    )
            continue

        outcome = join(obs, ctx)
        obs.joins = outcome.candidates

        if outcome.alias is None:
            obs.state = STATE_UNCATALOGUED
            obs.reason = REASON_NO_REPO if obs.plane == PLANE_K8S else REASON_NO_OWNER
            continue
        if not outcome.ambiguous:
            # The identity the join settled on, kept on the node so the coverage
            # numbers can be argued with: which rule named this thing.
            obs.payload["joined_alias"] = outcome.alias
            obs.payload["join_rule"] = outcome.rule

        svc_id = service_id(outcome.alias)
        svc = _service_node(
            services, outcome.alias, obs.plane, now, expires, {"joined_from": obs.id}
        )

        if outcome.ambiguous:
            obs.state = STATE_UNCATALOGUED
            obs.reason = "ambiguous_join"
            obs.payload["join_candidates"] = [c.as_dict() for c in outcome.candidates]
            continue

        # The workload is joined. It is MANAGED when the estate owns the
        # repository behind it; otherwise it is uncatalogued with the reason that
        # is missing -- never silently dropped.
        repo = outcome.repo
        owner = outcome.owner
        if obs.plane == PLANE_K8S:
            if repo is None:
                obs.state = STATE_UNCATALOGUED
                obs.reason = REASON_NO_REPO
            elif not owner:
                obs.state = STATE_UNCATALOGUED
                obs.reason = REASON_NO_OWNER
            else:
                obs.state = STATE_MANAGED
                obs.reason = None
                census.edges.append(
                    Edge(
                        src=repo.id,
                        dst=obs.id,
                        type="deploys",
                        source="census-join",
                        observed_at=now,
                        expires_at=expires,
                    )
                )
                census.aliases.append(
                    (
                        obs.id,
                        svc_id,
                        f"census-join:{outcome.rule}",
                        outcome.candidates[0].confidence,
                    )
                )
                census.aliases.append(
                    (
                        outcome.alias,
                        svc_id,
                        f"census-join:{outcome.rule}",
                        outcome.candidates[0].confidence,
                    )
                )
                if owner:
                    owner_id = f"owner:{owner}"
                    census.aliases.append(
                        (owner, svc_id, "census-join:rule-6-codeowners", 0.8)
                    )
                    if owner_id not in census.observations:
                        census.observations[owner_id] = Observation(
                            id=owner_id,
                            type="owner",
                            name=owner,
                            plane=obs.plane,
                            source="census-join",
                            observed_at=now,
                            expires_at=expires,
                            payload={"owner": owner},
                        )
                    census.edges.append(
                        Edge(
                            src=owner_id,
                            dst=svc_id,
                            type="owns",
                            source="census-join",
                            observed_at=now,
                            expires_at=expires,
                        )
                    )
        else:
            obs.state = STATE_MANAGED
            obs.reason = None
            census.aliases.append(
                (
                    obs.id,
                    svc_id,
                    f"census-join:{outcome.rule}",
                    outcome.candidates[0].confidence,
                )
            )
            census.aliases.append(
                (
                    outcome.alias,
                    svc_id,
                    f"census-join:{outcome.rule}",
                    outcome.candidates[0].confidence,
                )
            )

        if obs.plane == PLANE_K8S:
            census.edges.append(
                Edge(
                    src=svc_id,
                    dst=obs.id,
                    type="contains",
                    source="census-join",
                    observed_at=now,
                    expires_at=expires,
                )
            )
        if obs.plane == PLANE_EDGE and obs.type == "image":
            svc_name = image_repository_name(str(obs.payload.get("image") or ""))
            if svc_name:
                _service_node(
                    services, svc_name, PLANE_EDGE, now, expires, {"from_image": obs.id}
                )
                census.aliases.append(
                    (
                        obs.id,
                        service_id(svc_name),
                        "census-join:rule-4-image-repository",
                        0.9,
                    )
                )

    for svc in services.values():
        census.observations.setdefault(svc.id, svc)

    census.edges = _dedupe_edges(census.edges)
    census.aliases = _dedupe_aliases(census.aliases)

    validate(census)

    census.coverage = build_coverage(census)
    (
        census.join_rate,
        census.bar_rules_hit,
        census.live_workloads,
        census.bar_breakdown,
    ) = _join_bar(census)
    return census


def _dedupe_facts(facts: list[Fact]) -> list[Fact]:
    """One fact per id. The same fact can be seen from two planes."""

    seen: dict[str, Fact] = {}
    for fact in facts:
        seen.setdefault(fact.id, fact)
    return list(seen.values())


def _dedupe_edges(edges: list[Edge]) -> list[Edge]:
    """One edge per (src, dst, type).

    Two planes can see the same relation -- a repository and the workload it
    deploys is seen from both the git and the k8s side -- and the record's
    primary key says one relation is one row. The first sighting wins, because
    it is the one that carries the observation's own timestamp.
    """

    seen: dict[tuple[str, str, str], Edge] = {}
    for edge in edges:
        seen.setdefault((edge.src, edge.dst, edge.type), edge)
    return list(seen.values())


def _dedupe_aliases(
    aliases: list[tuple[str, str, str, float]],
) -> list[tuple[str, str, str, float]]:
    """One alias per (alias, node_id). The same name can be produced by two rules."""

    seen: dict[tuple[str, str], tuple[str, str, str, float]] = {}
    for row in aliases:
        seen.setdefault((row[0], row[1]), row)
    return list(seen.values())


def validate(census: Census) -> None:
    """The record's own integrity, checked before anything is written.

    Every alias and every edge points at a node. If one points at a node the
    census did not write, the record's foreign keys refuse the whole sweep --
    which is the right refusal, but it happens at the far end of a long write.
    Checking here turns a late, opaque failure into an early, named one: the
    alias that names a node nobody wrote.
    """

    ids = set(census.observations)
    dangling_aliases = [
        f"{alias}->{node_id}"
        for alias, node_id, _src, _conf in census.aliases
        if node_id not in ids
    ]
    dangling_edges = [
        edge for edge in census.edges if edge.src not in ids or edge.dst not in ids
    ]
    if dangling_aliases or dangling_edges:
        raise ValueError(
            "the census would write an alias or an edge that points at a node it did not write: "
            f"aliases={dangling_aliases[:5]} edges={[e.id for e in dangling_edges[:5]]}"
        )


def _service_node(
    services: dict[str, Observation],
    alias: str,
    plane: str,
    now: str,
    expires: str,
    payload: dict[str, Any] | None = None,
) -> Observation:
    """The canonical service node for a name, created once per sweep.

    A canonical service is a node, not a label: the names the estate calls one
    thing by hang off it as aliases. Every branch that writes an alias creates
    the node it points at, because an alias that points at a node that was never
    written is an alias the record cannot keep -- the foreign key says so, and
    it is right to.
    """

    svc_id = service_id(alias)
    svc = services.get(svc_id)
    if svc is None:
        svc = Observation(
            id=svc_id,
            type="service",
            name=alias,
            plane=plane,
            source="census-join",
            observed_at=now,
            expires_at=expires,
            payload=dict(payload or {}),
        )
        services[svc_id] = svc
    else:
        for key, value in (payload or {}).items():
            svc.payload.setdefault(key, value)
    return svc


def _join_bar(census: Census) -> tuple[float, int, int, dict[str, int]]:
    """The Phase 0 bar: 80 per cent of live workloads joined by rule 2 or rule 4.

    A workload counts only when the join actually SUCCEEDED on it and the rule
    that won is rule 2 (the k8s name label) or rule 4 (the image repository
    name). A candidate that was considered and rejected -- an ambiguous join --
    is not a join, and counting it would be the same defect the previous
    catalog shipped: a number that cannot fail.

    The denominator is the LONG-LIVED workloads -- Deployments, StatefulSets and
    DaemonSets -- because that is what the proposal itself measured as "live
    workloads" (138: 111 Deployments + 13 StatefulSets + 14 DaemonSets,
    proposal section 1.2). A Job is an execution of something, not the something;
    67 of the cluster's 226 workloads are Jobs, most of them one-shot dagster
    runs, and counting them would make the bar a measurement of the scheduler.

    The breakdown is returned with the rate, because a bare percentage cannot be
    argued with: it says which rule did the joining, how many were ambiguous,
    and how many could not be named at all.
    """

    live = [
        obs
        for obs in census.observations.values()
        if obs.plane == PLANE_K8S
        and obs.type == "workload"
        and obs.state != STATE_DISABLED
        and obs.payload.get("kind") in LONG_LIVED_KINDS
    ]
    breakdown = {"rule-2-label": 0, "rule-4-image": 0, "ambiguous": 0, "unnamed": 0}
    if not live:
        return 0.0, 0, 0, breakdown
    hit = 0
    for obs in live:
        if obs.reason == REASON_AMBIGUOUS:
            breakdown["ambiguous"] += 1
            continue
        winning = next(
            (c.rule for c in obs.joins if c.alias == _winning_alias(obs)), None
        )
        if winning == RULE_K8S_LABEL:
            breakdown["rule-2-label"] += 1
            hit += 1
        elif winning == RULE_IMAGE_REPO:
            breakdown["rule-4-image"] += 1
            hit += 1
        else:
            breakdown["unnamed"] += 1
    return hit / len(live), hit, len(live), breakdown


def _winning_alias(obs: Observation) -> str | None:
    """The alias the join settled on, which the record keeps in the node payload."""

    alias = obs.payload.get("joined_alias")
    return str(alias) if alias else None


def build_coverage(census: Census) -> list[dict[str, Any]]:
    """One row per plane: the universe, what was classified, what was not, blind.

    BLIND is a row, never a zero. A plane that could not be read has a blind count
    of 1 and a reason, and the number of objects it did not classify is not
    presented as a clean zero. A plane that was not walked at all is BLIND too,
    with the reason "not walked in this sweep" -- a plane nobody looked at is
    not a plane with nothing in it.
    """

    rows: list[dict[str, Any]] = []
    for plane in PLANES:
        result = next((r for r in census.results if r.plane == plane), None)
        wanted = UNIVERSE_TYPES.get(plane, set())
        objects = [
            obs
            for obs in census.observations.values()
            if obs.plane == plane and obs.type in wanted
        ]
        classified = [obs for obs in objects if obs.state == STATE_MANAGED]
        uncatalogued = [obs for obs in objects if obs.state == STATE_UNCATALOGUED]
        if result is None:
            rows.append(
                {
                    "plane": plane,
                    "universe": 0,
                    "classified": 0,
                    "uncatalogued": 0,
                    "blind": 1,
                    "last_run": census.started_at,
                    "detail": {
                        "collector": None,
                        "blind_reason": "the plane was not walked in this sweep",
                        "error": None,
                        "reasons": {},
                        "examples": [],
                    },
                }
            )
            continue
        blind = 1 if result.blind else 0
        reasons: dict[str, int] = {}
        for obs in uncatalogued:
            reason = obs.reason or "unknown"
            reasons[reason] = reasons.get(reason, 0) + 1
        rows.append(
            {
                "plane": plane,
                "universe": len(objects),
                "classified": len(classified),
                "uncatalogued": len(uncatalogued),
                "blind": blind,
                "last_run": census.started_at,
                "detail": {
                    "collector": result.collector,
                    "blind_reason": result.blind_reason,
                    "error": result.error,
                    "reasons": reasons,
                    "examples": [obs.id for obs in uncatalogued[:5]],
                },
            }
        )
    return rows
