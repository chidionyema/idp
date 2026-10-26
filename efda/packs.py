"""Interface 2 -- the SkillPack model, the baseline generator, composition.

A SkillPack is the thing that makes a component covered. It says which
component class it covers, which versions it applies to, what it costs to
run, how it is isolated, and which signatures it can match.

Two rules carry most of the weight:

  * **Existence is mandatory, quality is a tier.** The baseline generator
    emits a valid, cheap, T0-only pack for any component class the moment it
    is discovered. The invariant ("every component has a valid pack") is
    satisfied by generation, never by exception.
  * **A composed pack cannot smuggle power.** The composed budget is the
    minimum of the chain, a child's capabilities must be a subset of what its
    ancestors provide, and a circular ``extends`` is refused.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from . import INTERFACE_VERSION

BASELINE_SIGNATURES = (
    ("crashloop", "crashloop", "the container is restarting"),
    ("oomkill", "oomkill", "the container was OOMKilled"),
    ("image_pull_failure", "image_pull_failure", "the image could not be pulled"),
    ("scheduling_failure", "scheduling_failure", "no node could run the pod"),
    ("probe_failure", "probe_failure", "a liveness or readiness probe failed"),
    ("connection_refused", "connection_refused", "a dependency refused the connection"),
    ("dependency_timeout", "dependency_timeout", "a dependency did not answer in time"),
    ("tls_error", "tls_error", "the TLS handshake failed"),
    (
        "permission_denied",
        "permission_denied",
        "the process was not allowed to do something",
    ),
    ("exit_nonzero", "exit_nonzero", "the process exited non-zero"),
    ("stall", "stall", "the process made no progress within the threshold"),
    ("hard_kill", "hard_kill", "the process was SIGKILLed"),
)

BASELINE_BUDGET = {
    "maxCpuMillicores": 100,
    "maxMemoryMib": 128,
    "maxWallClockMs": 2000,
    "maxRegexComplexity": "low",
}

BASELINE_ISOLATION = {
    "sandbox": "wasm",
    "network": "none",
    "filesystem": "none",
}

_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)")


def _parse_version(version: str):
    match = _VERSION_RE.match(str(version or ""))
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def version_matches(version_range: str, version: str) -> bool:
    """Does ``version`` fall inside ``version_range``?

    The range language is deliberately small: ``*``, an exact version, or a
    comma-separated list of comparators (``>=1.2.0``, ``<2.0.0``). An
    unparseable range matches nothing -- a pack that cannot say which
    versions it covers does not cover them.
    """
    version_range = (version_range or "").strip()
    if version_range in ("", "*"):
        return True
    parsed = _parse_version(version)
    if parsed is None:
        return False
    for clause in version_range.split(","):
        clause = clause.strip()
        if not clause:
            continue
        match = re.match(r"^(>=|<=|>|<|=)?\s*(\d+\.\d+\.\d+.*)$", clause)
        if not match:
            return False
        operator = match.group(1) or "="
        bound = _parse_version(match.group(2))
        if bound is None:
            return False
        if operator == ">=" and parsed < bound:
            return False
        if operator == "<=" and parsed > bound:
            return False
        if operator == ">" and parsed <= bound:
            return False
        if operator == "<" and parsed >= bound:
            return False
        if operator == "=" and parsed[: len(bound)] != bound:
            return False
    return True


def baseline_signatures() -> list:
    """The technology-agnostic signatures every baseline pack carries.

    Low confidence on purpose (0.35): a baseline pack is meant to say "this
    is the shape of the failure", never "this is the cause". It reports; it
    never remediates.
    """
    signatures = []
    for identifier, failure_class, symptom in BASELINE_SIGNATURES:
        signatures.append(
            {
                "id": f"baseline-{identifier}",
                "symptom": symptom,
                "diagnosticQuestions": [],
                "matchLogic": f'failure_boundary.failure_class == "{failure_class}"',
                "cause": f"possible {identifier}",
                "confidenceBase": 0.35,
                "remediation": {"tier": "T0"},
            }
        )
    return signatures


def baseline_pack(
    component_class: str,
    component_kind: str = "workload",
    version: str = "0.1.0",
    namespace: str = "efda-system",
    generated_by: str = "factory-baseline@v1",
) -> dict:
    """The generated pack that makes a newly discovered class compliant.

    It applies to every version (a baseline pack is the floor, not a pin),
    costs the least the platform allows, and may only report.
    """
    deadline = datetime.now(timezone.utc) + timedelta(days=90)
    return {
        "apiVersion": "efda.estate/v1",
        "kind": "SkillPack",
        "metadata": {
            "name": f"{component_class}-v0",
            "namespace": namespace,
            "labels": {"efda.estate/coverage-tier": "baseline"},
        },
        "spec": {
            "componentClass": component_class,
            "componentKind": component_kind,
            "appliesToVersions": "*",
            "version": version,
            "interfaceVersion": INTERFACE_VERSION,
            "coverageTier": "baseline",
            "generatedBy": generated_by,
            "owner": {"team": "platform-fallback", "escalation": ""},
            "capabilitiesRequired": ["EvidenceRead"],
            "executionBudget": dict(BASELINE_BUDGET),
            "isolation": dict(BASELINE_ISOLATION),
            "upgradeDeadline": deadline.replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "deprecation": {
                "deprecatedAt": None,
                "sunsetAt": None,
                "replacementUri": None,
                "severity": "info",
            },
            "signatures": baseline_signatures(),
        },
    }


def pack_spec(pack: dict) -> dict:
    return pack.get("spec") or {}


def pack_name(pack: dict) -> str:
    return ((pack.get("metadata") or {}).get("name")) or ""


def select_packs(packs, component_class: str, component_version: str = ""):
    """Every pack that claims this class at this version.

    A specialist pack must pin a range; a baseline pack applies to
    everything. Order is by tier (specialist first) so the reviewer sees the
    pack that carries the authority.
    """
    matches = []
    for pack in packs:
        spec = pack_spec(pack)
        if spec.get("componentClass") != component_class:
            continue
        if not version_matches(spec.get("appliesToVersions", "*"), component_version):
            continue
        matches.append(pack)
    matches.sort(
        key=lambda p: (pack_spec(p).get("coverageTier") != "specialist", pack_name(p))
    )
    return matches


def compose(chain) -> dict:
    """Compose a chain of packs (parent first) into one effective pack.

    * parent signatures first, the child overrides a signature with the same id
    * the composed budget is the minimum of the chain, field by field
    * a child's capabilities must be a subset of what the ancestors provide
    """
    if not chain:
        raise ValueError("cannot compose an empty chain")
    if len(chain) > 1:
        ancestors = set()
        for pack in chain[:-1]:
            ancestors.update(pack_spec(pack).get("capabilitiesRequired") or [])
        child_caps = set(pack_spec(chain[-1]).get("capabilitiesRequired") or [])
        extra = child_caps - ancestors
        if extra:
            raise ValueError(
                f"child pack requires capabilities its ancestors do not provide: {sorted(extra)}"
            )

    base = pack_spec(chain[0])
    composed = dict(base)
    signatures = {}
    capabilities = set()
    budget = dict(base.get("executionBudget") or {})
    for pack in chain:
        spec = pack_spec(pack)
        for signature in spec.get("signatures") or []:
            signatures[signature.get("id")] = signature
        capabilities.update(spec.get("capabilitiesRequired") or [])
        for key, value in (spec.get("executionBudget") or {}).items():
            if key in budget:
                if key == "maxRegexComplexity":
                    order = {"low": 0, "moderate": 1, "high": 2}
                    budget[key] = min(budget[key], value, key=order.get)
                else:
                    budget[key] = min(budget[key], value)
            else:
                budget[key] = value
    composed["signatures"] = list(signatures.values())
    composed["capabilitiesRequired"] = sorted(capabilities)
    composed["executionBudget"] = budget
    composed["composedFrom"] = [pack_name(p) for p in chain]
    return composed


def resolve_chain(packs_by_name: dict, pack: dict) -> list:
    """Walk ``extends`` up to the root, refusing a cycle.

    The chain comes back parent-first, which is the order ``compose`` wants.
    """
    chain = []
    seen = []
    current = pack
    while current is not None:
        name = pack_name(current)
        if name in seen:
            raise ValueError(f"circular pack composition: {' -> '.join(seen + [name])}")
        seen.append(name)
        chain.append(current)
        parent_ref = pack_spec(current).get("extends")
        if not parent_ref:
            break
        parent_name = str(parent_ref).split("@", 1)[0]
        parent = packs_by_name.get(parent_name)
        if parent is None:
            raise ValueError(f"pack {name} extends {parent_name}, which does not exist")
        current = parent
    chain.reverse()
    return chain


def effective_pack(pack: dict, packs_by_name: dict) -> dict:
    """The pack as it behaves: composed with its ancestors."""
    chain = resolve_chain(packs_by_name, pack)
    if len(chain) == 1:
        return pack_spec(pack)
    return compose(chain)


def is_sunset(pack: dict, now=None) -> bool:
    """Has this pack passed its sunset date?"""
    spec = pack_spec(pack)
    sunset = (spec.get("deprecation") or {}).get("sunsetAt")
    if not sunset:
        return False
    now = now or datetime.now(timezone.utc)
    try:
        when = datetime.fromisoformat(str(sunset).replace("Z", "+00:00"))
    except ValueError:
        return False
    return when <= now
