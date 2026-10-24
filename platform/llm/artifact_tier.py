"""Deterministic artifact-class routing; no model classifies the request.

The policy assigns capability tiers, never vendors. LiteLLM aliases are resolved from
this file's canonical YAML and the existing lane registry owns health. Legacy aliases
outside the policy retain their old routing behaviour.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_POLICY_PATH = Path(__file__).with_name("artifact-tier.yaml")
POLICY_ENV = "ESTATE_ARTIFACT_TIER_POLICY"
TIERS = ("none", "cheap", "mid", "frontier")
REASONING = ("standard", "deep")
RISK = ("standard", "high")


class ArtifactRoutingError(ValueError):
    """The routing contract is unknown or unsafe; never guess a weaker tier."""


@dataclass(frozen=True)
class RoutingRequest:
    artifact_class: str
    reasoning: str = "standard"
    risk: str = "standard"
    deterministic_gate: bool = True


@dataclass(frozen=True)
class RoutingDecision:
    artifact_class: str
    tier: str
    alias: str | None
    reasons: tuple[str, ...]
    policy_version: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class ArtifactPolicy:
    def __init__(self, document: dict[str, Any], source: Path):
        self.source = source
        self.document = document
        validate_schema(document)
        raw = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
        self.version = hashlib.sha256(raw).hexdigest()[:16]
        self._alias_tiers = {
            alias: tier
            for tier, spec in document["tiers"].items()
            for alias in spec["aliases"]
        }

    @classmethod
    def load(cls, path: str | os.PathLike[str] | None = None) -> "ArtifactPolicy":
        source = Path(
            path or os.environ.get(POLICY_ENV) or DEFAULT_POLICY_PATH
        ).expanduser()
        try:
            document = yaml.safe_load(source.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise ArtifactRoutingError(
                f"artifact policy unreadable: {source}: {exc}"
            ) from exc
        if not isinstance(document, dict):
            raise ArtifactRoutingError("artifact policy must be a mapping")
        return cls(document, source)

    def request(self, *args, **kwargs) -> RoutingRequest:
        return RoutingRequest(*args, **kwargs)

    def route(self, request: RoutingRequest) -> RoutingDecision:
        if request.reasoning not in REASONING:
            raise ArtifactRoutingError(f"unknown reasoning: {request.reasoning!r}")
        if request.risk not in RISK:
            raise ArtifactRoutingError(f"unknown risk: {request.risk!r}")
        spec = self.document["artifact_classes"].get(request.artifact_class)
        if spec is None:
            raise ArtifactRoutingError(
                f"unknown artifact class: {request.artifact_class!r}"
            )
        tier = spec["tier"]
        reasons = [f"artifact:{request.artifact_class}"]
        if tier == "none":
            reasons.append("deterministic:no-model")
        elif request.reasoning == "deep" or request.risk == "high":
            tier = spec.get("escalated_tier", "frontier")
            reasons.append(f"escalated:{request.reasoning}/{request.risk}")
        elif spec.get("requires_deterministic_gate") and not request.deterministic_gate:
            tier = spec["ungated_tier"]
            reasons.append("ungated:cheap-refused")
        elif spec.get("requires_deterministic_gate"):
            reasons.append("deterministic-gate:present")
        aliases = self.document["tiers"][tier]["aliases"]
        return RoutingDecision(
            artifact_class=request.artifact_class,
            tier=tier,
            alias=aliases[0] if aliases else None,
            reasons=tuple(reasons),
            policy_version=self.version,
        )

    def tier_of(self, alias: str) -> str | None:
        return self._alias_tiers.get(alias)

    def rescue_aliases(self, alias: str) -> tuple[str, tuple[str, ...]] | None:
        """Return only same-tier rescue groups; None means a legacy alias."""
        tier = self.tier_of(alias)
        if tier is None:
            return None
        return tier, tuple(
            candidate
            for candidate in self.document["tiers"][tier]["aliases"]
            if candidate != alias
        )

    def replan_after_failures(
        self, request: RoutingRequest, failed_attempts: int
    ) -> RoutingDecision | None:
        """The third cheap attempt must be preceded by frontier re-planning."""
        if failed_attempts < self.document["gated_attempts_before_replan"]:
            return None
        if request.artifact_class not in ("build", "edit", "author"):
            return None
        decision = self.route(RoutingRequest("plan", "deep", "high"))
        reasons = decision.reasons + (f"gated-failures:{failed_attempts}",)
        return RoutingDecision(
            decision.artifact_class,
            decision.tier,
            decision.alias,
            reasons,
            decision.policy_version,
        )


def validate_schema(document: dict[str, Any]) -> None:
    if document.get("version") != 1:
        raise ArtifactRoutingError("artifact policy version must be 1")
    bound = document.get("gated_attempts_before_replan")
    if not isinstance(bound, int) or isinstance(bound, bool) or bound < 1:
        raise ArtifactRoutingError(
            "gated_attempts_before_replan must be a positive integer"
        )
    tiers = document.get("tiers")
    if not isinstance(tiers, dict) or set(tiers) != set(TIERS):
        raise ArtifactRoutingError(f"tiers must be exactly {TIERS}")
    seen: dict[str, str] = {}
    for tier in TIERS:
        spec = tiers[tier]
        aliases = spec.get("aliases") if isinstance(spec, dict) else None
        if not isinstance(aliases, list) or not all(
            isinstance(alias, str) and alias for alias in aliases
        ):
            raise ArtifactRoutingError(f"{tier}.aliases must be a list of names")
        if (tier == "none") != (not aliases):
            raise ArtifactRoutingError("only the none tier may have no aliases")
        for alias in aliases:
            if alias in seen:
                raise ArtifactRoutingError(
                    f"alias {alias!r} occurs in both {seen[alias]} and {tier}"
                )
            seen[alias] = tier
    floor = document.get("local_floor")
    if floor not in tiers["cheap"]["aliases"]:
        raise ArtifactRoutingError("local_floor must be a cheap-tier alias")
    if tiers["cheap"]["aliases"][-1] != floor:
        raise ArtifactRoutingError("local_floor must be the final cheap-tier alias")
    artifacts = document.get("artifact_classes")
    if not isinstance(artifacts, dict) or not artifacts:
        raise ArtifactRoutingError("artifact_classes must be a non-empty mapping")
    for name, spec in artifacts.items():
        if not isinstance(name, str) or not isinstance(spec, dict):
            raise ArtifactRoutingError("each artifact class must have a mapping")
        tier = spec.get("tier")
        if tier not in TIERS:
            raise ArtifactRoutingError(f"{name}: unknown tier {tier!r}")
        for key in ("ungated_tier", "escalated_tier"):
            if key in spec and spec[key] not in TIERS[1:]:
                raise ArtifactRoutingError(f"{name}: invalid {key}")
        if spec.get("requires_deterministic_gate") and "ungated_tier" not in spec:
            raise ArtifactRoutingError(f"{name}: gated class needs ungated_tier")


def validate_configured_aliases(
    policy: ArtifactPolicy, config_path: str | os.PathLike[str]
) -> None:
    """Fail closed when policy names a group the router does not actually serve."""
    try:
        config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ArtifactRoutingError(f"router config unreadable: {exc}") from exc
    configured = {
        row.get("model_name")
        for row in config.get("model_list") or []
        if isinstance(row, dict)
    }
    missing = sorted(set(policy._alias_tiers) - configured)
    if missing:
        raise ArtifactRoutingError(
            f"policy aliases missing from router config: {missing}"
        )


_default_policy: ArtifactPolicy | None = None
_default_stamp: tuple[str, int] | None = None


def default_policy() -> ArtifactPolicy:
    """Cache the compiled policy; a policy file replacement is picked up on mtime."""
    global _default_policy, _default_stamp
    path = Path(os.environ.get(POLICY_ENV) or DEFAULT_POLICY_PATH).expanduser()
    try:
        stamp = (str(path), path.stat().st_mtime_ns)
    except OSError as exc:
        raise ArtifactRoutingError(
            f"artifact policy unreadable: {path}: {exc}"
        ) from exc
    if _default_policy is None or _default_stamp != stamp:
        _default_policy = ArtifactPolicy.load(path)
        _default_stamp = stamp
    return _default_policy
