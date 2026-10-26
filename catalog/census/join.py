"""The join: how a thing the census saw becomes a service the estate knows.

The estate has four naming schemes for one service (a k8s id, an image reference, a
label, a Backstage component) and no way to say they are the same thing. The join is
the table that says it, and it is the reason the catalog is worth building: a list of
workloads is a list; a workload that is known to BE the router, with the repo that
deploys it and the team that owns it, is knowledge.

The rules are the proposal's, in the proposal's order, and the order is the contract:
first match wins, and every match that was considered is kept as evidence. Rule 2
(the k8s name label) and rule 4 (the image repository name) are the two the Phase 0
acceptance bar names, because they are the two that work on a live cluster without
anyone writing anything down.

When two rules disagree the node is ambiguous and both candidates are kept. It is
not guessed: a wrong join is a lie the record then serves to every reader, and the
proposal's rule for that is an explicit ambiguity, not a coin toss.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from catalog.census.model import (
    RULE_ESTATE_YAML,
    RULE_IMAGE_REPO,
    RULE_K8S_LABEL,
    RULE_LAUNCHD_LABEL,
    RULE_OTEL_NAME,
    RULE_OVERRIDE,
    RULE_REPO_NAME,
    Join,
    Observation,
    is_service_alias,
)

# The rules that assert what a thing IS. A disagreement between two of these is an
# ambiguity. The repository-name rule and the manual override are not assertions
# about identity -- they are how a thing was found -- so they cannot contradict one.
IDENTITY_RULES = (
    RULE_ESTATE_YAML,
    RULE_K8S_LABEL,
    RULE_OTEL_NAME,
    RULE_IMAGE_REPO,
    RULE_LAUNCHD_LABEL,
)

# The rules that name the RUNNING SERVICE. Two of these disagreeing is a real
# ambiguity: the estate gave the same thing two different service names (the
# k8s label says estate-mcp, the telemetry says mcp-estate-refresh), and the
# record must not pick one.
#
# Rule 4 (the image's name) is deliberately NOT in this class. It names the
# thing that was BUILT, and the estate's images are named after components as
# often as after services: the idp repository builds an image called
# "estate-scheduler" and the service that runs it is called "dagster" (measured
# 2026-10-26, 139 long-lived workloads). Treating the two as rival identities
# would flag 29 workloads as ambiguous -- every one of them a case where the
# label is plainly right and the image is somebody else's component name. So
# rule 4 is the FALLBACK: it names the service when nothing else does, and it is
# recorded as evidence when something else does.
SERVICE_CLASS_RULES = (
    RULE_ESTATE_YAML,
    RULE_K8S_LABEL,
    RULE_OTEL_NAME,
    RULE_LAUNCHD_LABEL,
)


@dataclass
class RepoInfo:
    """A repository the census found, with what is known about who owns it."""

    id: str
    org: str
    name: str
    path: str | None = None
    owner: str | None = None
    deployable: bool = False
    codeowners: list[str] = field(default_factory=list)
    default_branch: str = ""

    @property
    def service_alias(self) -> str:
        return self.name


@dataclass
class JoinContext:
    """Everything the join needs to know that is not on the object itself."""

    repos: dict[str, RepoInfo] = field(default_factory=dict)
    # The images each repository builds, read from that repository's own
    # Dockerfiles (the rule bin/dockerfiles applies). This is what answers "which
    # repository builds ghcr.io/chidionyema/estate-scheduler", which the image
    # reference itself never says.
    images: dict[str, str] = field(default_factory=dict)
    # Rule 7: a manual override, with provenance. The only way to correct a wrong
    # join that is not editing a YAML file by hand.
    overrides: dict[str, str] = field(default_factory=dict)

    def repo_by_name(self, name: str) -> RepoInfo | None:
        if not name:
            return None
        return self.repos.get(name) or self.repos.get(name.lower())

    def repo_for_image(self, image: str) -> RepoInfo | None:
        """The repository behind an image, by the two ways one can be known.

        The first is direct: the repository's own Dockerfiles say which images it
        builds. The second is the image's own path segment, which is a name
        match and no more. The direct answer wins, because a Dockerfile is a
        measurement and a name match is a coincidence.
        """

        if not image:
            return None
        built_by = self.images.get(normalize_image(image))
        if built_by:
            repo = self.repo_by_name(built_by)
            if repo is not None:
                return repo
        return self.repo_by_name(image_repo_name(image))

    def is_known_artifact(self, image: str) -> bool:
        """Whether an image is one the estate builds.

        An artifact's name is the name of a Dockerfile, not of a service: the
        estate's idp repository builds an image called "estate-scheduler" and
        the service that runs it is called "dagster". Treating the artifact's
        name as a competing service identity would call the estate's own naming
        scheme an ambiguity, so an artifact name is evidence, not a rival.
        """

        return normalize_image(image) in self.images


def normalize_image(image: str) -> str:
    """An image reference without its tag or digest: ghcr.io/org/name."""

    if not image:
        return ""
    reference = image.split("@", 1)[0]
    parts = reference.split("/")
    last = parts[-1]
    if ":" in last:
        parts[-1] = last.split(":", 1)[0]
    return "/".join(parts)


@dataclass
class JoinOutcome:
    """What the join decided, and what it saw on the way."""

    alias: str | None = None
    rule: str | None = None
    candidates: list[Join] = field(default_factory=list)
    ambiguous: bool = False
    owner: str | None = None
    repo: RepoInfo | None = None

    @property
    def joined(self) -> bool:
        return bool(self.alias) and not self.ambiguous

    def as_dict(self) -> dict[str, Any]:
        return {
            "alias": self.alias,
            "rule": self.rule,
            "ambiguous": self.ambiguous,
            "owner": self.owner,
            "repo": self.repo.id if self.repo else None,
            "candidates": [c.as_dict() for c in self.candidates],
        }


def _image_parts(image: str) -> tuple[list[str], bool]:
    """The path segments of an image reference, and whether the first is a registry.

    ghcr.io/chidionyema/idp/router -> (["chidionyema", "idp", "router"], True)
    ghcr.io/chidionyema/estate-scheduler -> (["chidionyema", "estate-scheduler"], True)
    idp/router -> (["idp", "router"], False)

    A registry is a first segment with a dot or a port in it, which is Docker's own
    rule. Everything after it is the path; without a registry the first segment is
    a namespace.
    """

    if not image:
        return [], False
    reference = image.split("@", 1)[0]
    tail = reference.rsplit(":", 1)
    if len(tail) == 2 and "/" not in tail[1]:
        reference = tail[0]
    segments = [seg for seg in reference.split("/") if seg]
    if not segments:
        return [], False
    first = segments[0]
    if ("." in first or ":" in first) and len(segments) > 1:
        return segments[1:], True
    return segments, False


def image_repository_name(image: str) -> str:
    """The SERVICE name an image reference carries.

    ghcr.io/chidionyema/idp/router -> router
    ghcr.io/chidionyema/estate-scheduler -> estate-scheduler
    docker.io/library/nginx -> nginx

    This is rule 4's key. The estate publishes as <org>/<repo>/<service>, so a
    three-segment path names the service last; a two-segment path names the image
    itself, which is both the repository and the service.
    """

    parts, _ = _image_parts(image)
    if not parts:
        return ""
    if len(parts) >= 2:
        return parts[-1]
    return parts[0]


def image_repo_name(image: str) -> str:
    """The REPOSITORY that builds an image, when the image says so.

    ghcr.io/chidionyema/idp/router -> idp
    ghcr.io/chidionyema/estate-scheduler -> estate-scheduler

    The estate publishes as <org>/<repo>/<service>, so the second-to-last segment
    is the repository that builds the thing and the last is the service's name.
    Rule 4 joins on the service; this finds the repository; the difference is the
    whole reason an image can lead to a repo.
    """

    parts, _ = _image_parts(image)
    if not parts:
        return ""
    if len(parts) >= 3:
        return parts[-2]
    return parts[-1]


def image_registry_org(image: str) -> str:
    """ghcr.io/chidionyema/idp/router -> chidionyema. The org is the repo's owner."""

    if not image:
        return ""
    reference = image.split("@", 1)[0]
    segments = [seg for seg in reference.split("/") if seg]
    if len(segments) >= 2:
        return segments[-2]
    return ""


def candidates_for(obs: Observation, ctx: JoinContext) -> list[Join]:
    """Every candidate join for one object, in the rule order, with its evidence."""

    found: list[Join] = []
    payload = obs.payload or {}

    # Rule 1: an explicit estate.yaml in the repo. Optional, and only for the cases
    # where a derived fact is wrong.
    explicit = payload.get("estate_yaml_service")
    if explicit and is_service_alias(str(explicit)):
        found.append(Join(str(explicit), RULE_ESTATE_YAML, 1.0, "estate.yaml"))

    # Rule 2: the k8s name label.
    labels = payload.get("labels") or {}
    label_name = labels.get("app.kubernetes.io/name")
    if label_name and is_service_alias(str(label_name)):
        found.append(
            Join(str(label_name), RULE_K8S_LABEL, 0.95, "app.kubernetes.io/name")
        )

    # Rule 3: the telemetry identity, when the workload declares one.
    otel = payload.get("otel_service_name") or payload.get("service.name")
    if otel and is_service_alias(str(otel)):
        found.append(Join(str(otel), RULE_OTEL_NAME, 0.9, "OTEL_SERVICE_NAME"))

    # Rule 4: the image repository name.
    repo_name = image_repository_name(str(payload.get("image") or ""))
    if repo_name and is_service_alias(repo_name):
        found.append(Join(repo_name, RULE_IMAGE_REPO, 0.9, str(payload.get("image"))))

    # Rule 8: the host's own name for the thing. The launchd label's suffix is
    # the service, the way app.kubernetes.io/name is the service on the cluster.
    launchd_label = str(payload.get("label") or "")
    if launchd_label and "." in launchd_label:
        suffix = launchd_label.rsplit(".", 1)[-1]
        if suffix and is_service_alias(suffix):
            found.append(Join(suffix, RULE_LAUNCHD_LABEL, 0.9, launchd_label))

    # Rule 5: the repo name, for a repo-shaped object. A workload's repository is
    # found through the image, not through its own name, so this rule does not fire
    # on a workload -- a workload whose repo is called "idp" is not a service called
    # "idp", and a rule that said so would drown the real identity in noise.
    if obs.type == "repo":
        declared_repo = payload.get("repo")
        if declared_repo and is_service_alias(str(declared_repo)):
            found.append(Join(str(declared_repo), RULE_REPO_NAME, 0.7, "repo name"))

    # Rule 7: a manual override, applied last and overriding everything before it,
    # because a human said so and a human can be wrong in a way a rule cannot.
    for alias in found:
        override = ctx.overrides.get(alias.alias)
        if override:
            found.append(
                Join(override, RULE_OVERRIDE, 1.0, f"override for {alias.alias}")
            )
            break

    return found


def _same_thing(names: list[str]) -> bool:
    """Whether two candidate names are one thing at two granularities.

    "cert-manager" and "cert-manager-controller" are the same product; so are
    "cainjector" and "cert-manager-cainjector". A name that contains the other
    is not a competing identity -- it is the same thing, named at a different
    depth -- so the join keeps the first match and records both. Two names that
    share no part ("rotation-canary" and "oci-cli") ARE competing identities,
    and the node is ambiguous.
    """

    for index, first in enumerate(names):
        for second in names[index + 1 :]:
            if first in second or second in first:
                return True
    return False


def join(obs: Observation, ctx: JoinContext) -> JoinOutcome:
    """Join one observation to a service, and say how sure we are."""

    candidates = candidates_for(obs, ctx)
    outcome = JoinOutcome(candidates=candidates)
    if not candidates:
        return outcome
    payload = obs.payload or {}

    outcome.alias = candidates[0].alias
    outcome.rule = candidates[0].rule

    # The service class decides the identity, and its disagreements are the
    # ambiguities. The artifact class (the image's name) is the fallback for a
    # thing nothing else names.
    service_candidates = [c for c in candidates if c.rule in SERVICE_CLASS_RULES]
    artifact_candidates = [c for c in candidates if c.rule == RULE_IMAGE_REPO]
    if service_candidates:
        outcome.alias = service_candidates[0].alias
        outcome.rule = service_candidates[0].rule
        distinct = {c.alias for c in service_candidates}
        if len(distinct) > 1 and not _same_thing(sorted(distinct)):
            outcome.ambiguous = True
    elif artifact_candidates:
        outcome.alias = artifact_candidates[0].alias
        outcome.rule = artifact_candidates[0].rule
    override = next((c for c in candidates if c.rule == RULE_OVERRIDE), None)
    if override is not None:
        outcome.alias = override.alias
        outcome.rule = override.rule
        outcome.ambiguous = False

    # Rule 6: the owner, and the repo behind the service.
    image = str(payload.get("image") or "")
    declared = str(payload.get("repo") or "")
    repo = ctx.repo_by_name(declared) or ctx.repo_for_image(image)
    if repo is None:
        org = image_registry_org(image)
        repo = ctx.repo_by_name(org) if org else None
    if repo is not None:
        outcome.repo = repo
        outcome.owner = repo.owner
    return outcome
