"""L3 -- the synthesizer: observed failures in, candidate packs out.

The factory's synthesis stage turns an evidence corpus into candidate
signatures. This implementation is **evidence-driven and deterministic**: it
reads what actually happened, groups it by failure class, and writes a
signature per class that the validator then tries to break.

The spec allows an LLM to do this, constrained to the schema. That path is a
pluggable adapter, not a dependency: a candidate pack must be reproducible
from its provenance hash, and a free-text model cannot promise that. The
interface the adapter would implement is the same one this module implements
-- ``synthesize(corpus, component_class) -> candidate pack`` -- so the
constrained-LLM stage can be added without touching the validator, the
promoter or the registry.

A synthesized pack is T0 by construction. Authority is earned later, per
signature, through a reviewed ``safetyProof`` and an allowlist entry.
"""

from __future__ import annotations

from .contract import digest_of
from .packs import baseline_pack

MIN_EVENTS = 3

QUESTIONS_BY_CLASS = {
    "crashloop": ("describe the container's last termination state",),
    "oomkill": ("describe the container's memory limit and last termination state",),
    "image_pull_failure": ("describe the pod's events",),
    "scheduling_failure": ("describe the pod's scheduling events",),
    "probe_failure": ("describe the pod's probe events",),
    "connection_refused": ("describe the dependency service's endpoints",),
    "dependency_timeout": ("describe the dependency service's endpoints",),
    "tls_error": ("describe the serving certificate's issuer",),
    "permission_denied": ("describe the pod's service account bindings",),
    "exit_nonzero": ("read the container's last log tail",),
    "stall": ("read the checkpoint of the last run",),
    "hard_kill": ("read the checkpoint of the last run",),
}


def corpus_from_artifacts(artifacts):
    """Turn artifacts into the corpus shape the validator reads.

    Every artifact in the corpus is a positive for its own failure class; the
    negative side is the artifacts of every *other* class, which is what the
    "must not fire on a sample of non-failures from the same component" check
    replays against.
    """
    corpus = []
    for artifact in artifacts:
        boundary = artifact.get("failure_boundary") or {}
        corpus.append(
            {
                "artifact": artifact,
                "positive": True,
                "failure_class": boundary.get("failure_class", ""),
                "runner_id": (artifact.get("identity") or {}).get("runner_id", ""),
            }
        )
    return corpus


def group_by_failure_class(corpus):
    grouped = {}
    for item in corpus:
        failure_class = item.get("failure_class") or ""
        if not failure_class:
            continue
        grouped.setdefault(failure_class, []).append(item)
    return grouped


def synthesize(
    corpus, component_class, component_kind="workload", namespace="efda-system"
):
    """The candidate pack for one component class.

    A class seen fewer than ``MIN_EVENTS`` times does not get a candidate:
    three observations is the floor at which a pattern is a pattern.
    """
    grouped = group_by_failure_class(corpus)
    signatures = []
    provenance = {"corpusDigest": digest_of(corpus), "events": len(corpus)}

    for failure_class, items in sorted(grouped.items()):
        if len(items) < MIN_EVENTS:
            continue
        confidence = round(min(0.85, 0.40 + 0.05 * len(items)), 2)
        signature = {
            "id": f"synth-{failure_class}",
            "symptom": f"{failure_class} observed {len(items)} times",
            "diagnosticQuestions": list(QUESTIONS_BY_CLASS.get(failure_class, ())),
            "matchLogic": f'failure_boundary.failure_class == "{failure_class}"',
            "cause": f"{failure_class} (observed {len(items)} times in the window)",
            "confidenceBase": confidence,
            "remediation": {"tier": "T0"},
            "provenance": {
                "expectedFailureClass": failure_class,
                "events": len(items),
                "corpusDigest": provenance["corpusDigest"],
                "generatedBy": "factory-synthesis@v1",
            },
        }
        signatures.append(signature)

    candidate = baseline_pack(
        component_class,
        component_kind=component_kind,
        version="0.2.0",
        namespace=namespace,
        generated_by="factory-synthesis@v1",
    )
    spec = candidate["spec"]
    spec["coverageTier"] = "specialist"
    spec["signatures"] = signatures
    spec["extends"] = f"{component_class}-v0"
    spec["provenance"] = provenance
    candidate["metadata"]["name"] = f"{component_class}-v1"
    candidate["metadata"]["labels"]["efda.estate/coverage-tier"] = "specialist"
    return candidate


def candidate_usable(report) -> bool:
    """Did the candidate pass every check the validator ran?"""
    return bool(report.get("ok"))
