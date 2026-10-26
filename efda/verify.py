"""The verification playbook: six phases, each one a gate.

    1  L1 checkpoint   a killed run left a checkpoint and a hard_kill artifact
    2  L2 evidence     the gate refuses an uncovered class, and an artifact exists
    3  L3 registry     a registered component is covered by a pack
    4  L4 factory      the pack factory produced a pack for a discovered class
    5  L5 reasoning    a real artifact produced a DiagnosticReport
    6  L6 remediation  the executor refuses what the allowlist does not name

Every phase prints PASS or FAIL with the evidence it looked at, and exits
non-zero on the first failure. A phase that cannot fail is not a phase.
"""

from __future__ import annotations

import json
import os

from .executor import decide, load_allowlist
from .k8s import KubeClient, KubeError
from .packs import pack_spec
from .reasoning import reason
from .reconciler import SNAPSHOT_NAME
from .store import ArtifactStore, RedisClient, RedisError

RED = "\033[0;31m"
GREEN = "\033[0;32m"
NC = "\033[0m"


def _pass(message):
    print(f"{GREEN}PASS{NC} {message}")


def _fail(message):
    print(f"{RED}FAIL{NC} {message}")


def phase1(store, kube, namespace):
    """A killed run left a checkpoint and a hard_kill artifact."""
    runner_id = os.environ.get("EFDA_TEST_RUNNER", "")
    if not runner_id:
        _fail("phase 1 needs EFDA_TEST_RUNNER (the runner id of the killed process)")
        return 1
    checkpoint = None
    try:
        checkpoint = store.redis.get(f"efda:ckpt:{runner_id}")
    except (RedisError, OSError) as exc:
        _fail(f"the checkpoint sink is unreachable: {exc}")
        return 1
    if not checkpoint:
        _fail(f"no checkpoint at efda:ckpt:{runner_id}")
        return 1
    _pass(f"checkpoint at efda:ckpt:{runner_id} holds {len(checkpoint)} bytes")

    artifact = store.read_by_key(
        f"efda:evidence:oke:default:efda-test-agent:{runner_id}:artifact"
    )
    if artifact is None:
        for key in store.redis.keys("efda:evidence:*:artifact"):
            candidate = store.read_by_key(key)
            if (
                candidate
                and (candidate.get("identity") or {}).get("runner_id") == runner_id
            ):
                artifact = candidate
                break
    if artifact is None:
        _fail(f"no artifact for runner {runner_id}")
        return 1
    failure_class = (artifact.get("failure_boundary") or {}).get("failure_class")
    if failure_class != "hard_kill":
        _fail(
            f"the artifact's failure_class is {failure_class!r}, expected 'hard_kill'"
        )
        return 1
    _pass(f"artifact failure_class=hard_kill at {store.address_of(artifact)}")
    return 0


def phase2(store, kube, namespace):
    """The gate refuses an uncovered class, and evidence lands at an address."""
    manifest = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": "efda-uncovered-probe",
            "namespace": namespace,
            "annotations": {"efda.estate/component-class": "efda-uncovered-class"},
        },
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app": "efda-uncovered-probe"}},
            "template": {
                "metadata": {"labels": {"app": "efda-uncovered-probe"}},
                "spec": {
                    "containers": [{"name": "c", "image": "registry.k8s.io/pause:3.10"}]
                },
            },
        },
    }
    try:
        kube.run(["apply", "-f", "-", "--dry-run=server"], stdin=json.dumps(manifest))
    except KubeError as exc:
        if "efda.estate/component-class" in str(
            exc
        ) or "not in the EFDA registry" in str(exc):
            _pass("the NCWP gate refused an uncovered component class")
        else:
            _fail(f"the dry-run failed for another reason: {exc}")
            return 1
    else:
        _fail("the NCWP gate admitted an uncovered component class")
        return 1

    keys = store.redis.keys("efda:evidence:*:artifact") if store.redis else []
    if not keys:
        _fail("no artifact has been written at any deterministic address")
        return 1
    _pass(f"{len(keys)} artifact(s) exist at deterministic addresses")
    return 0


def phase3(kube, namespace):
    """A registered component is covered by a pack."""
    registrations = kube.list("componentregistrations", all_namespaces=True)
    if not registrations:
        _fail("no ComponentRegistration exists")
        return 1
    covered = 0
    for item in registrations:
        status = item.get("status") or {}
        if status.get("coverageState") in ("BASELINE", "SPECIALIST"):
            covered += 1
    if not covered:
        _fail(f"{len(registrations)} registrations, none covered")
        return 1
    _pass(f"{covered} of {len(registrations)} registrations are covered")
    report = kube.get("coveragereports", "latest", namespace=namespace)
    if not report:
        _fail("no CoverageReport")
        return 1
    _pass("the CoverageReport is published")
    return 0


def phase4(kube, namespace):
    """The pack factory produced a pack for a discovered class."""
    packs = kube.list("skillpacks", all_namespaces=True)
    if not packs:
        _fail("no SkillPack exists")
        return 1
    baselines = [p for p in packs if pack_spec(p).get("coverageTier") == "baseline"]
    if not baselines:
        _fail("no baseline pack exists")
        return 1
    _pass(f"{len(baselines)} baseline pack(s), {len(packs)} pack(s) in total")
    snapshot = kube.get("configmaps", SNAPSHOT_NAME, namespace=namespace)
    if not snapshot:
        _fail("the registry snapshot is not published")
        return 1
    _pass("the registry snapshot is published")
    return 0


def phase5(store, kube, namespace):
    """A real artifact produced a DiagnosticReport."""
    from .cli import _load_registry
    from .packs import effective_pack, select_packs

    keys = store.redis.keys("efda:evidence:*:artifact") if store.redis else []
    if not keys:
        _fail("no artifact to reason over")
        return 1
    artifact = store.read_by_key(keys[0])
    packs = {}
    for item in kube.list("skillpacks", all_namespaces=True):
        packs[(item.get("metadata") or {}).get("name", "")] = item
    identity = artifact.get("identity") or {}
    candidates = select_packs(list(packs.values()), identity.get("component_class", ""))
    if not candidates:
        _fail(f"no pack covers {identity.get('component_class')!r}")
        return 1
    pack = candidates[0]
    spec = effective_pack(pack, packs)
    report = reason(
        artifact,
        {"metadata": pack.get("metadata"), "spec": spec},
        registry=_load_registry(kube, namespace),
    )
    if report.get("status") not in ("DIAGNOSED", "NEEDS_HUMAN"):
        _fail(f"the report says {report.get('status')}: {report.get('warnings')}")
        return 1
    _pass(
        "DiagnosticReport status={status} cause={cause!r} confidence={confidence}".format(
            status=report.get("status"),
            cause=report.get("cause"),
            confidence=report.get("confidence"),
        )
    )
    return 0


def phase6(kube, namespace):
    """The executor refuses what the allowlist does not name."""
    allowlist = load_allowlist()
    report = {
        "signatureId": "efda-phase6-probe",
        "componentClass": "efda-test-agent",
        "confidence": 0.99,
        "remediation": {
            "tier": "T1",
            "safetyProof": "risk=low;capabilities=[annotation:patch];rollback=defined",
        },
    }
    decision = decide(report, allowlist)
    if decision.get("outcome") == "EXECUTE":
        _fail("the executor executed an action the allowlist does not name")
        return 1
    _pass(f"the executor refused: {decision.get('reason')}")
    return 0


def run_phase(phase: int, namespace="efda-system"):
    kube = KubeClient(namespace=namespace)
    redis = RedisClient()
    store = ArtifactStore(redis)
    phases = {
        1: lambda: phase1(store, kube, namespace),
        2: lambda: phase2(store, kube, namespace),
        3: lambda: phase3(kube, namespace),
        4: lambda: phase4(kube, namespace),
        5: lambda: phase5(store, kube, namespace),
        6: lambda: phase6(kube, namespace),
    }
    handler = phases.get(phase)
    if handler is None:
        print(f"usage: efda verify --phase {{1..6}} (got {phase})")
        return 2
    try:
        code = handler()
    except (KubeError, RedisError) as exc:
        _fail(f"phase {phase} could not run: {exc}")
        return 1
    finally:
        redis.close()
    return code
