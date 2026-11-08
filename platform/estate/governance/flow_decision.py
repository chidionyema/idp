#!/usr/bin/env python3
"""FLOW deterministic work selector, backed by the estate's R-14 incident scorer.

This is a PURE decision core, NOT a new scheduler, queue or privilege source.
An existing authenticated off-host supervisor must observe runtime facts,
run this selector, verify the plan, and wake the already-existing hosted
agent-sandbox workflow through its approved action door. Agents cannot
self-assign urgency, bypass admission or assert their own completed effects.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
INCIDENT = ROOT / "platform/estate/libexec/incident-loop.py"
SCHEMA = "flow.machine-decision.v1"
STATES = {"READY", "RUNNING", "VERIFYING", "WAITING", "BLOCKED", "VERIFIED", "CLOSED"}
DONE = {"VERIFIED", "CLOSED"}
ACTIVE = {"RUNNING", "VERIFYING"}
KINDS = {"build", "repair", "recover", "review", "verify", "observe", "science"}
PROTOCOL = {
    "build": "EXECUTE_EXISTING_GOVERNED_PLAN",
    "repair": "SCOPED_INCIDENT_REPAIR",
    "recover": "APPLY_VERIFIED_FAILURE_CLASS",
    "review": "INDEPENDENT_REVIEW",
    "verify": "INDEPENDENT_EFFECT_VERIFICATION",
    "observe": "MEASURE_TRUSTED_STATE",
    "science": "PREREGISTER_AND_RUN_SAFE_EXPERIMENT",
}
REMOTE = {"github_actions", "cloudflare_free", "oci_e2_existing", "oci_a1_existing", "other_remote_free"}
MAX_NODES = 256
EVIDENCE_MAX_AGE_S = 900
STAGNATION_S = 600


def _when(raw):
    if not isinstance(raw, str):
        raise ValueError("missing timestamp")
    x = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if x.tzinfo is None:
        raise ValueError("timestamp lacks UTC offset")
    return x.astimezone(timezone.utc)


def _age(raw, now):
    value = (now - _when(raw)).total_seconds()
    if value < 0:
        raise ValueError("timestamp lies in the future")
    return value


def _scorer():
    """Reuse EXACTLY the canonical R-14 priority function; never copy its weights."""
    spec = importlib.util.spec_from_file_location("estate_incident_loop_for_flow", INCIDENT)
    if spec is None or spec.loader is None:
        raise ValueError("canonical incident scorer unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.load_policy(), module.score_incident


def _check_graph(items):
    seen, visiting = set(), set()
    def visit(key):
        if key in visiting:
            raise ValueError("dependency cycle at " + key)
        if key in seen:
            return
        visiting.add(key)
        for dep in items[key]["depends_on"]:
            if dep not in items:
                raise ValueError("missing dependency " + dep)
            visit(dep)
        visiting.remove(key)
        seen.add(key)
    for key in sorted(items):
        visit(key)


def _proof_ok(item, now):
    proof = item.get("evidence")
    if not isinstance(proof, dict):
        return False
    if not all(isinstance(proof.get(x), str) and proof[x].strip()
               for x in ("observed_at", "observer", "ref", "source_sha")):
        return False
    try:
        return _age(proof["observed_at"], now) <= EVIDENCE_MAX_AGE_S
    except ValueError:
        return False


def select(snapshot, *, now=None, policy=None, score_fn=None):
    """Return ordered typed work orders only; all side effects remain trusted-door controlled."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must have timezone")
    now = now.astimezone(timezone.utc)
    if not isinstance(snapshot, dict) or snapshot.get("schema") != SCHEMA:
        raise ValueError("unsupported snapshot schema")
    if not isinstance(snapshot.get("nodes"), list) or len(snapshot["nodes"]) > MAX_NODES:
        raise ValueError("unbounded/invalid nodes")
    if policy is None or score_fn is None:
        policy, score_fn = _scorer()

    observed = snapshot.get("observed_at")
    if _age(observed, now) > EVIDENCE_MAX_AGE_S:
        return {"state": "BLIND", "reason": "stale supervisor snapshot",
                "wake": [], "recovery": [], "waiting": [], "release_authority": False}
    capacity = snapshot.get("capacity")
    if not isinstance(capacity, dict) or isinstance(capacity.get("remote_slots"), bool):
        raise ValueError("missing remote worker capacity")
    slots = capacity.get("remote_slots")
    if not isinstance(slots, int) or not 0 <= slots <= 64:
        raise ValueError("invalid remote worker slots")
    if not isinstance(capacity.get("evidence"), dict) or not _proof_ok({"evidence": capacity["evidence"]}, now):
        return {"state": "BLIND", "reason": "unverified remote worker capacity",
                "wake": [], "recovery": [], "waiting": [], "release_authority": False}
    nodes = {}
    for row in snapshot["nodes"]:
        if not isinstance(row, dict):
            raise ValueError("node must be an object")
        key = row.get("id")
        if not isinstance(key, str) or not key or len(key) > 120 or key in nodes:
            raise ValueError("missing/duplicate/long node ID")
        if row.get("state") not in STATES or row.get("kind") not in KINDS:
            raise ValueError("invalid node phase or protocol " + key)
        if row.get("severity") not in policy["severities"] or row.get("blast") not in policy["blast_radius"]:
            raise ValueError("unknown incident class " + key)
        deps, resources = row.get("depends_on"), row.get("resources")
        if not isinstance(deps, list) or any(not isinstance(x, str) for x in deps) or len(deps) != len(set(deps)):
            raise ValueError("dependencies invalid " + key)
        if not isinstance(resources, list) or any(not isinstance(x, str) or not x for x in resources) or len(resources) != len(set(resources)):
            raise ValueError("resource fences invalid " + key)
        if not isinstance(row.get("owner"), str) or not row["owner"]:
            raise ValueError("owner missing " + key)
        if row.get("placement") not in REMOTE or row.get("requires_founder_device") is not False:
            raise ValueError("retired/local deployment path " + key)
        if type(row.get("incremental_monthly_gbp")) not in (int, float) or not math.isfinite(row["incremental_monthly_gbp"]) or row["incremental_monthly_gbp"] != 0:
            raise ValueError("unauthorized infra cost " + key)
        if type(row.get("attempts")) is not int or not 0 <= row["attempts"] <= 100:
            raise ValueError("missing/invalid attempt history " + key)
        if not isinstance(row.get("issue"), str) or not row["issue"].startswith("https://github.com/"):
            raise ValueError("no source-of-record GitHub issue " + key)
        _when(row.get("last_progress_at"))
        nodes[key] = row
    _check_graph(nodes)

    scores = {}
    for key, row in nodes.items():
        age_hours = min(_age(row["last_progress_at"], now) / 3600, 24 * 365)
        score, label = score_fn(policy, row["severity"], row["blast"], age_hours=age_hours)
        scores[key] = {"score": float(score), "label": label}
    # Inherit urgency along dependencies. An otherwise low-priority prerequisite
    # can become the highest-value thing when a P0 is blocked behind it.
    effective = {key: x["score"] for key, x in scores.items()}
    for _ in range(len(nodes)):
        changed = False
        for key, row in nodes.items():
            for dep in row["depends_on"]:
                if effective[dep] < effective[key]:
                    effective[dep] = effective[key]
                    changed = True
        if not changed:
            break

    active_resources = set()
    for row in nodes.values():
        if row["state"] in ACTIVE:
            active_resources.update(row["resources"])
    ready, recovery, waiting = [], [], []
    for key, row in nodes.items():
        phase, kind = row["state"], row["kind"]
        if phase in DONE:
            continue
        if not _proof_ok(row, now):
            waiting.append({"id": key, "state": "OBSERVE", "reason": "stale or missing independently attributable evidence"})
            continue
        if phase in ACTIVE:
            if _age(row["last_progress_at"], now) >= STAGNATION_S:
                recovery.append({"id": key, "state": "RECOVERY_PENDING",
                                 "protocol": "FENCED_CHECKPOINT_AND_PEER_TAKEOVER",
                                 "reason": "600s without independently evidenced progress",
                                 "owner": row["owner"], "source": row["issue"]})
            continue
        if row["attempts"] >= 2:
            waiting.append({"id": key, "state": "FAILURE_CLASS_ESCALATION",
                            "reason": "retry budget exhausted; change hypothesis/executor"})
            continue
        outstanding = [x for x in row["depends_on"] if nodes[x]["state"] not in DONE]
        if outstanding:
            waiting.append({"id": key, "state": "WAIT_DEPENDENCY", "depends_on": sorted(outstanding)})
            continue
        if phase != "READY":
            waiting.append({"id": key, "state": "WAIT_PHASE", "phase": phase})
            continue
        ready.append((key, row))
    # One stable, deterministic total order (scores from one policy; IDs break ties).
    ready.sort(key=lambda x: (-effective[x[0]], -scores[x[0]]["score"], x[0]))
    wake = []
    preempt = []  # REQUESTS only: trusted runtime must checkpoint/fence before releasing a lease.
    resources = set(active_resources)
    for key, row in ready:
        locks = set(row["resources"])
        if len(wake) >= slots:
            # A true emergency outranks maintenance; never simply kill a
            # worker. PREEMPT_REQUEST first proves remote checkpoint,
            # independent fence and available alternate execution authority.
            # The active worker is NOT freed in this planning pass.
            candidates = []
            if scores[key]["label"] == "P0":
                for active_key, running in nodes.items():
                    if running["state"] not in ACTIVE or not running.get("preemptible"):
                        continue
                    if not _proof_ok({"evidence": running.get("checkpoint_evidence")}, now):
                        continue
                    if effective[active_key] < effective[key]:
                        candidates.append((effective[active_key], active_key))
            if candidates:
                _, victim = min(candidates)
                if not any(x["victim"] == victim for x in preempt):
                    preempt.append({"victim": victim, "for": key,
                                    "state": "FENCED_PREEMPTION_REQUEST",
                                    "protocol": "CHECKPOINT_FENCE_REASSIGN_THEN_REEVALUATE",
                                    "release_authority": False})
                waiting.append({"id": key, "state": "WAIT_FENCED_PREEMPTION", "for": victim})
            else:
                waiting.append({"id": key, "state": "WAIT_CAPACITY", "reason": "no verified remote execution slot"})
            continue
        if locks & resources:
            waiting.append({"id": key, "state": "SERIAL_RESOURCE_WAIT",
                            "locks": sorted(locks & resources)})
            continue
        resources.update(locks)
        wake.append({
            "id": key, "issue": row["issue"], "owner": row["owner"],
            "urgency": scores[key]["label"], "score": scores[key]["score"],
            "effective_score": effective[key], "protocol": PROTOCOL[row["kind"]],
            "placement": row["placement"], "resources": sorted(locks),
            "action": "WAKE_EXISTING_HOSTED_AGENT_SANDBOX",
            "admission": "EXISTING_TRUSTED_GATE_MUST_RECHECK",
            "completion": "INDEPENDENT_OPERATIONAL_EFFECT_REQUIRED",
            "evidence_ref": row["evidence"]["ref"],
        })
    return {
        "schema": SCHEMA, "state": "PLAN_ONLY",
        "release_authority": False,
        "priority_policy": str(INCIDENT_POLICY.relative_to(ROOT)),
        "wake": wake,
        "recovery": sorted(recovery, key=lambda x: (-effective[x["id"]], x["id"])),
        "preempt_requests": preempt,
        "waiting": sorted(waiting, key=lambda x: x["id"]),
        "parallel_width": len(wake), "remote_capacity": slots,
        "generated_at": now.isoformat(),
        "note": "Existing authenticated executor must dispatch; a plan grants zero capabilities",
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, help="trusted observed JSON snapshot")
    args = parser.parse_args(argv)
    try:
        with open(args.snapshot, encoding="utf-8") as fh:
            snapshot = json.load(fh)
        result = select(snapshot)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["state"] == "PLAN_ONLY" else 2
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"state": "BLIND", "release_authority": False,
                          "wake": [], "reason": f"{type(exc).__name__}: {exc}"}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
