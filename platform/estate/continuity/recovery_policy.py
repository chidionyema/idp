"""Failure-domain admission for existing FLOW/Legion recovery, not a new scheduler.

The caller's trusted topology/evidence adapter must authenticate the ENTIRE
snapshot, including its completeness, capability offers and proof semantics.
This module neither grants capabilities nor interprets strings as commands.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass

SHA = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"[0-9a-f]{64}")
MAX_AGE = 120.0
MAX_SNAPSHOT_BYTES = 131072

# These are capability requirements, not executable commands. An unavailable
# or unregistered capability cannot become an offer through this policy.
RULES = {
    "RETIRED_DECLARATION": ("lane-submit", ("lifecycle_retired", "consumer_cutover", "rollback")),
    "VERIFIED_ORPHAN": ("prune-verified-orphan", ("inventory_complete", "applied_revision", "prior_flux_ownership", "uid_cas", "consumers_drained", "stateless", "prune_authorized")),
    "BASE_RED": ("lane-submit", ("base_failure_reproduced", "exact_candidate", "differential_checks", "unchanged_gates", "rollback")),
    "DB_UNAVAILABLE": ("k8s-diag", ("dependency_identity", "database_failure")),
    "FLUX_STALLED": ("flux-doctor", ("exact_source_revision", "dependency_failure", "controller_generation")),
    "UNRELATED_CRASH": ("lane-submit", ("base_failure_reproduced", "exact_candidate", "differential_checks", "unchanged_gates", "rollback")),
    "CRASHLOOP": ("k8s-diag", ("workload_identity", "repeated_restart", "dependency_identity")),
    "GREENLANE_DOWN": ("recovery-executor", ("pipeline_failure", "recovery_permit", "unchanged_gates", "rollback")),
    "CLUSTER_DOWN": ("cluster-recovery", ("control_plane_failure", "current_substrate", "recovery_permit", "restore_verified", "rollback")),
    "WORKER_LOST": ("mission-resume", ("attempt_identity", "checkpoint_verified", "effect_inventory")),
}
ORPHAN_KINDS = frozenset({"Deployment", "DaemonSet", "Job", "CronJob"})
ROLE_FIELDS = ("agent_adapter", "provider", "model", "execution_host", "failure_domain", "worktree_id", "base_sha")


class RecoveryRefused(ValueError):
    """Missing or invalid evidence: do not act, retain the obligation."""


def _require(condition, message):
    if not condition:
        raise RecoveryRefused(message)


def _name(value):
    return isinstance(value, str) and 0 < len(value) <= 256 and value.strip() == value


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _proofs(proofs, required):
    _require(isinstance(proofs, dict), "missing authenticated proofs")
    _require(all(isinstance(proofs.get(k), str) and DIGEST.fullmatch(proofs[k]) for k in required), "missing required proof digest")


def _fresh(observed, expires, now):
    return all(_number(x) for x in (observed, expires, now)) and observed <= now < expires and now - observed <= MAX_AGE and expires - observed <= MAX_AGE


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class Plan:
    mission_id: str
    fault_id: str
    kind: str
    mandate_version: int
    revocation_epoch: int
    lease_epoch: int
    attempt_id: str | None
    action: str
    revision: str
    key: str
    target: dict
    executor: dict
    verifier: dict
    expires_at: float

    @property
    def worker(self):
        return {key: self.executor[key] for key in ROLE_FIELDS}


def _usable(nodes, root, excluded, now):
    """Complete transitive closure, including credentials, storage and scheduler."""
    visiting, visited, domains = set(), set(), set()
    expiries = []

    def walk(name):
        if name in visiting:
            return False
        if name in visited:
            return True
        node = nodes.get(name)
        if not isinstance(node, dict):
            return False
        domain = node.get("domain")
        deps = node.get("requires")
        if (not _name(domain) or domain in excluded or name in excluded
                or node.get("host_kind") not in {"cloud", "service", "external"}
                or node.get("health") != "OK"
                or not _fresh(node.get("observed_at"), node.get("expires_at"), now)
                or not isinstance(deps, list) or len(deps) > 64
                or not all(_name(d) for d in deps)):
            return False
        visiting.add(name)
        if not all(walk(d) for d in deps):
            return False
        visiting.remove(name)
        visited.add(name)
        domains.add(domain)
        expiries.append(node["expires_at"])
        return True

    return (domains, min(expiries)) if walk(root) else None


def plan_recovery(snapshot, authenticate, *, now, mission_id, max_cost=0.0):
    """Return a bounded plan; the existing executor must still check its permit."""
    try:
        raw = _canonical(snapshot)
        _require(len(raw.encode()) <= MAX_SNAPSHOT_BYTES, "oversize recovery snapshot")
        s = json.loads(raw)
        _require(isinstance(s, dict) and authenticate(json.loads(raw)) is True, "unverified recovery snapshot")
        _require(_fresh(s.get("observed_at"), s.get("expires_at"), now), "stale recovery snapshot")
        _require(_name(mission_id) and s.get("mission_id") == mission_id, "wrong mission")
        kind, fault_id, rev = s.get("kind"), s.get("fault_id"), s.get("revision")
        _require(isinstance(kind, str) and kind in RULES and _name(fault_id) and isinstance(rev, str) and SHA.fullmatch(rev), "unclassified fault or revision")
        authority = tuple(s.get(k) for k in ("mandate_version", "revocation_epoch", "lease_epoch"))
        _require(all(type(v) is int and v >= 0 for v in authority) and (s.get("attempt_id") is None or _name(s["attempt_id"])), "missing authority epoch")
        action, required = RULES[kind]
        _proofs(s.get("proofs"), ("topology_complete", "current_authority", "scope_authorized", *required))
        target, excluded = s.get("target"), s.get("failed_domains")
        _require(isinstance(target, dict) and _name(target.get("identity")), "missing target identity")
        _require(isinstance(excluded, list) and 0 < len(excluded) <= 64 and all(_name(x) for x in excluded), "unknown failure domain")
        excluded = set(excluded)
        if kind == "VERIFIED_ORPHAN":
            _require(target.get("kind") in ORPHAN_KINDS and all(_name(target.get(k)) for k in ("namespace", "name", "uid", "resource_version")), "orphan is not an exact stateless workload")
            _require(target["namespace"] not in {"kube-system", "flux-system", "default"}, "protected namespace")
        if kind == "CLUSTER_DOWN":
            _require(target.get("substrate") == "arm-k3s", "target is not current ARM k3s")
        nodes, offers = s.get("nodes"), s.get("offers")
        _require(isinstance(nodes, dict) and 0 < len(nodes) <= 128 and isinstance(offers, list) and len(offers) <= 128, "unbounded or missing topology")
        _require(_number(max_cost) and max_cost >= 0, "unknown recovery cost ceiling")
        admitted = []
        for offer in offers:
            if not isinstance(offer, dict) or not all(_name(offer.get(k)) for k in ("principal", "node", "failure_domain", "capability")):
                continue
            if not _fresh(offer.get("observed_at"), offer.get("expires_at"), now):
                continue
            if not _number(offer.get("cost")) or offer["cost"] < 0:
                continue
            if offer.get("capacity") is not True or offer.get("authorized") is not True or offer["failure_domain"] in excluded:
                continue
            if not isinstance(nodes.get(offer["node"]), dict) or nodes[offer["node"]].get("domain") != offer["failure_domain"]:
                continue
            closure = _usable(nodes, offer["node"], excluded, now)
            if closure is not None:
                admitted.append((offer, closure))
        pairs = []
        for worker, (wdeps, wexpiry) in admitted:
            if worker.get("role") != "executor" or worker["capability"] != action or not all(_name(worker.get(k)) for k in ROLE_FIELDS) or worker["base_sha"] != rev:
                continue
            for verifier, (vdeps, vexpiry) in admitted:
                if verifier.get("role") != "verifier" or verifier["capability"] != action:
                    continue
                if worker["principal"] == verifier["principal"] or worker["failure_domain"] == verifier["failure_domain"]:
                    continue
                if worker["failure_domain"] in vdeps or verifier["failure_domain"] in wdeps:
                    continue
                if worker["cost"] + verifier["cost"] <= max_cost:
                    pairs.append((worker["cost"] + verifier["cost"], worker["principal"], verifier["principal"], worker, verifier, min(wexpiry, vexpiry)))
        _require(bool(pairs), "no independent authorized recovery and verification pair")
        _, _, _, worker, verifier, dependency_expiry = min(pairs, key=lambda x: x[:3])
        # Stable across worker replacement / new observations; exact target and
        # revision remain bound. An effect receipt must be reconciled before retry.
        key = hashlib.sha256(_canonical([mission_id, fault_id, kind, rev, target, action, *authority[:2]]).encode()).hexdigest()
        return Plan(mission_id, fault_id, kind, *authority, s.get("attempt_id"), action, rev, key, target, worker, verifier,
                    min(s["expires_at"], worker["expires_at"], verifier["expires_at"], dependency_expiry))
    except RecoveryRefused:
        raise
    except Exception as exc:
        raise RecoveryRefused("malformed or unauthenticated recovery snapshot") from exc
