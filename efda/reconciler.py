"""G3 -- the component registry and the coverage reconciler.

The registry is what makes "all" computable. It enumerates the estate's
components, says who owns each one, and says which pack covers it. Anything
observed in the cluster but absent from the registry is an ORPHAN, and the
reconciler resolves it within one pass by generating a baseline pack.

The reconciler also publishes two things the rest of the estate depends on:

  * the **registry snapshot** (a ConfigMap): class -> packs, versions, digests
  * the **NCWP gate** (a ValidatingAdmissionPolicy): the set of component
    classes that may be admitted

CEL cannot read a ConfigMap, so the gate's class list is written into the
policy expression by the reconciler and rewritten only when the set changes.
The gate is bound to namespaces labelled ``efda.estate/enforced=true`` -- no
estate namespace is exposed to it until it has been proven.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from .contract import digest_of
from .k8s import COMPONENT_CLASS_ANNOTATION
from .packs import baseline_pack, is_sunset, pack_spec

REGISTRY_GROUP = "efda.estate"
REGISTRY_VERSION = "v1"
SNAPSHOT_NAME = "efda-registry-snapshot"
NCWP_POLICY_NAME = "efda-ncwp"

TEAM_LABEL = "efda.estate/team"
OWNER_LABEL = "app.kubernetes.io/owner"
TENANT_LABEL = "efda.estate/tenant"
MIN_TIER_LABEL = "efda.estate/min-coverage-tier"

FALLBACK_TEAM = "platform-fallback"


def now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def owner_for(workload, namespace_labels):
    """Who owns this component.

    Namespace label, then the workload's own owner label, then the platform
    fallback queue. No component is ownerless.
    """
    team = namespace_labels.get(TEAM_LABEL) or workload.get("labels", {}).get(
        OWNER_LABEL
    )
    return team or FALLBACK_TEAM


def tenant_for(namespace_labels):
    return namespace_labels.get(TENANT_LABEL) or "default"


def min_tier_for(namespace_labels):
    tier = namespace_labels.get(MIN_TIER_LABEL) or "baseline"
    return tier if tier in ("baseline", "specialist") else "baseline"


def registration_name(workload):
    return workload["name"]


def build_registration(workload, namespace_labels, discovery_method="reconciler_scan"):
    """The ComponentRegistration for an observed workload."""
    team = owner_for(workload, namespace_labels)
    return {
        "apiVersion": f"{REGISTRY_GROUP}/{REGISTRY_VERSION}",
        "kind": "ComponentRegistration",
        "metadata": {
            "name": registration_name(workload),
            "namespace": workload["namespace"],
            "labels": {"efda.estate/component-class": workload["component_class"]},
        },
        "spec": {
            "componentClass": workload["component_class"],
            "componentKind": workload.get("kind", "workload"),
            "versionsInService": [],
            "owner": {"team": team, "escalation": ""},
            "tenantId": tenant_for(namespace_labels),
            "minCoverageTier": min_tier_for(namespace_labels),
            "discovery": {"method": discovery_method, "lastSeen": now_iso()},
        },
    }


def baseline_pack_for(workload, namespace_labels, namespace=None):
    return baseline_pack(
        workload["component_class"],
        component_kind=workload.get("kind", "workload"),
        namespace=namespace or workload["namespace"],
    )


def coverage_state(registration, pack, now=None):
    """The coverage state of one registration under its pack.

    The state machine is the spec's: ORPHAN, BASELINE, SPECIALIST, DEPRECATED,
    SUNSET_VIOLATION, DECOMMISSIONED.
    """
    now = now or datetime.now(timezone.utc)
    spec = (registration.get("spec") or {}) if registration else {}
    if spec.get("decommissioned"):
        return "DECOMMISSIONED", True
    if pack is None:
        return "ORPHAN", False
    if is_sunset(pack, now=now):
        return "SUNSET_VIOLATION", False
    pack_spec_ = pack_spec(pack)
    tier = pack_spec_.get("coverageTier", "baseline")
    deadline = pack_spec_.get("upgradeDeadline")
    if deadline:
        try:
            when = datetime.fromisoformat(str(deadline).replace("Z", "+00:00"))
        except ValueError:
            when = None
        if when and when <= now:
            return "DEPRECATED", tier == "baseline" or spec.get(
                "minCoverageTier"
            ) != "specialist"
    if tier == "specialist":
        return "SPECIALIST", True
    return "BASELINE", True


def collect_packs(kube):
    """Every SkillPack in the estate, keyed by name."""
    packs = {}
    for item in kube.list("skillpacks", all_namespaces=True):
        packs[(item.get("metadata") or {}).get("name", "")] = item
    return packs


def packs_for_class(packs, component_class):
    return [
        pack
        for pack in packs.values()
        if pack_spec(pack).get("componentClass") == component_class
    ]


def reconcile(kube, generate_baseline=True, namespace="efda-system", publish=True):
    """One reconcile pass: observe, register, cover, report.

    Returns a summary the caller can log or assert on.
    """
    summary = {
        "observed": 0,
        "registered": 0,
        "created": 0,
        "packs_created": 0,
        "orphans": 0,
        "states": {},
        "non_compliant": [],
        "classes": [],
    }

    namespace_labels = {}
    for name in kube.namespaces():
        namespace_labels[name] = _namespace_labels(kube, name)

    observed = kube.observed_workloads()
    summary["observed"] = len(observed)

    packs = collect_packs(kube)
    seen_names = set()

    for workload in observed:
        seen_names.add((workload["namespace"], workload["name"]))
        registration = kube.get(
            "componentregistrations",
            registration_name(workload),
            namespace=workload["namespace"],
        )
        if registration is None:
            registration = build_registration(
                workload, namespace_labels.get(workload["namespace"], {})
            )
            kube.apply(registration)
            summary["created"] += 1
        summary["registered"] += 1

        class_packs = packs_for_class(packs, workload["component_class"])
        chosen = None
        for candidate in class_packs:
            spec = pack_spec(candidate)
            if spec.get("coverageTier") == "specialist":
                chosen = candidate
                break
            chosen = chosen or candidate

        if chosen is None and generate_baseline:
            pack = baseline_pack_for(
                workload, namespace_labels.get(workload["namespace"], {})
            )
            kube.apply(pack)
            packs[(pack.get("metadata") or {}).get("name", "")] = pack
            chosen = pack
            summary["packs_created"] += 1

        state, compliant = coverage_state(registration, chosen)
        summary["states"][state] = summary["states"].get(state, 0) + 1
        if not compliant:
            summary["non_compliant"].append(
                {
                    "component": f"{workload['namespace']}/{workload['name']}",
                    "state": state,
                }
            )
        _write_status(kube, registration, chosen, state, compliant)

    # Registered but not observed: the component left the cluster.
    for item in kube.list("componentregistrations", all_namespaces=True):
        metadata = item.get("metadata") or {}
        key = (metadata.get("namespace", ""), metadata.get("name", ""))
        if key in seen_names:
            continue
        spec = item.get("spec") or {}
        if spec.get("decommissioned"):
            continue
        summary["orphans"] += 1
        summary["states"]["ORPHAN"] = summary["states"].get("ORPHAN", 0) + 1
        summary["non_compliant"].append(
            {"component": f"{key[0]}/{key[1]}", "state": "ORPHAN"}
        )
        # The registration is still in the cluster but its component is not.
        # The state is written down, so the gap is visible rather than a
        # stale "BASELINE" that says everything is fine.
        class_packs = packs_for_class(packs, spec.get("componentClass", ""))
        _write_status(
            kube, item, class_packs[0] if class_packs else None, "ORPHAN", False
        )

    if publish:
        snapshot = build_snapshot(packs)
        publish_snapshot(kube, snapshot, namespace)
        update_ncwp_policy(kube, sorted(snapshot.get("classes", {}).keys()), namespace)
        emit_coverage_report(kube, summary, namespace)

    summary["classes"] = sorted({w["component_class"] for w in observed})
    return summary


def _namespace_labels(kube, name):
    obj = kube.get("namespaces", name)
    if not obj:
        return {}
    return (obj.get("metadata") or {}).get("labels") or {}


def _write_status(kube, registration, pack, state, compliant):
    """Write the coverage state onto the registration's status."""
    if not registration:
        return
    updated = dict(registration)
    status = {
        "coverageState": state,
        "coverageTier": pack_spec(pack).get("coverageTier", "baseline")
        if pack
        else "baseline",
        "compliant": bool(compliant),
        "lastEvaluated": now_iso(),
    }
    if pack:
        status["packRef"] = "{}@{}#{}".format(
            (pack.get("metadata") or {}).get("name", ""),
            pack_spec(pack).get("version", ""),
            digest_of(pack),
        )
    updated.setdefault("status", {}).update(status)
    try:
        kube.update_status(updated)
    except Exception as exc:  # noqa: BLE001 -- status writes must not stop the pass
        # The pass continues, but the failure is said out loud: a status that
        # silently did not land is a coverage claim nobody can check.
        sys.stderr.write(
            f"efda: status write failed for {registration.get('metadata', {}).get('name')}: {exc}\n"
        )


def build_snapshot(packs):
    """The registry snapshot: class -> the packs that cover it."""
    classes = {}
    for pack in packs.values():
        spec = pack_spec(pack)
        component_class = spec.get("componentClass")
        if not component_class:
            continue
        entry = classes.setdefault(
            component_class,
            {
                "componentClass": component_class,
                "componentKind": spec.get("componentKind", "workload"),
                "packs": [],
            },
        )
        entry["packs"].append(
            {
                "name": (pack.get("metadata") or {}).get("name", ""),
                "version": spec.get("version", ""),
                "tier": spec.get("coverageTier", "baseline"),
                "appliesToVersions": spec.get("appliesToVersions", "*"),
                "digest": digest_of(pack),
                "sunsetAt": (spec.get("deprecation") or {}).get("sunsetAt"),
            }
        )
    for entry in classes.values():
        entry["packs"].sort(key=lambda p: (p["tier"] != "specialist", p["name"]))
    return {"generatedAt": now_iso(), "classes": classes}


def publish_snapshot(kube, snapshot, namespace="efda-system"):
    configmap = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"name": SNAPSHOT_NAME, "namespace": namespace},
        "data": {"registry.json": json.dumps(snapshot, indent=2, sort_keys=True)},
    }
    kube.apply(configmap)
    return configmap


def ncwp_expression(classes):
    """The CEL expression of the NCWP gate.

    A workload in an enforced namespace must carry a component class, and that
    class must be one the registry knows. The class list is written into the
    expression because CEL cannot read the ConfigMap the snapshot lives in.
    """
    allowed = ", ".join("'%s'" % c.replace("'", "\\'") for c in classes)
    if not allowed:
        allowed = "''"
    return (
        "has(object.metadata.annotations) && "
        "'%s' in object.metadata.annotations && "
        "(object.metadata.annotations['%s'] in [%s])"
        % (COMPONENT_CLASS_ANNOTATION, COMPONENT_CLASS_ANNOTATION, allowed)
    )


def update_ncwp_policy(kube, classes, namespace="efda-system"):
    """Write the class list into the gate, but only when it changed."""
    policy = kube.get("validatingadmissionpolicies", NCWP_POLICY_NAME)
    if not policy:
        return None
    expression = ncwp_expression(classes)
    validations = policy.get("spec", {}).get("validations") or []
    if validations and validations[0].get("expression") == expression:
        return policy
    updated = dict(policy)
    updated["spec"] = dict(policy.get("spec") or {})
    updated["spec"]["validations"] = [
        {
            "expression": expression,
            "message": "component class '%s' is not in the EFDA registry; no pack covers it"
            % COMPONENT_CLASS_ANNOTATION,
            "reason": "Invalid",
        }
    ]
    kube.apply(updated)
    return updated


def emit_coverage_report(kube, summary, namespace="efda-system"):
    """The CoverageReport: what the estate covers, and what it does not."""
    report = {
        "apiVersion": f"{REGISTRY_GROUP}/{REGISTRY_VERSION}",
        "kind": "CoverageReport",
        "metadata": {"name": "latest", "namespace": namespace},
        "spec": {
            "generatedAt": now_iso(),
            "counts": {
                "observed": summary.get("observed", 0),
                "registered": summary.get("registered", 0),
                "orphans": summary.get("orphans", 0),
                "packsCreated": summary.get("packs_created", 0),
                **{
                    state: count
                    for state, count in (summary.get("states") or {}).items()
                },
            },
            "nonCompliant": summary.get("non_compliant", []),
        },
    }
    kube.apply(report)
    return report


def enforced_namespaces(kube):
    return kube.namespaces(enforced_only=True)
