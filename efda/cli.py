"""The EFDA command line -- the doors the estate calls.

efda reconcile            one reconcile pass (or a loop with --interval)
efda baseline             generate the baseline packs the registry needs
efda snapshot             print the registry snapshot
efda reason               Reason(artifact, pack) -> DiagnosticReport
efda execute              run a report through the remediation gates
efda validate             the five adversarial checks over a pack
efda synthesize           observed failures -> a candidate pack
efda register             self-register an agent or a script
efda wrapper -- CMD       run a child under the L1 wrapper
efda drain                push the local WAL into the sink
efda verify --phase N     the verification playbook
efda describe             print what this build is wired to
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

from .contract import FailureClassRegistry
from .executor import decide, execute, load_allowlist
from .k8s import KubeClient, KubeError
from .packs import effective_pack, select_packs
from .reasoning import reason
from .reconciler import reconcile as run_reconcile
from .store import ArtifactStore, CheckpointStore, RedisClient, RedisError
from .synth import corpus_from_artifacts, synthesize
from .validation import validate_pack
from .wrapper import main as wrapper_main


# The file the readiness probe looks for. It is written after the FIRST COMPLETE PASS, not at
# start-up: a process that has started but has not yet talked to the cluster or to the sink has
# not proved it can do the work, and a probe that answers "the process exists" is a probe that
# cannot fail. spine/bridge.py holds the same contract for the event spine.
READY_FILE = os.environ.get("EFDA_READY_FILE", "/tmp/efda.ready")  # noqa: S108 - pod-local marker


def _write_ready_file(path: str | None = None) -> None:
    """Mark this container ready. A failure to write is a warning, not a crash: the probe reads
    the file, and a container that cannot write it is one the readiness probe keeps reporting as
    not-ready until the pod is restarted. The path is resolved at call time, not at import time,
    so a test can move it and a pod can move it with EFDA_READY_FILE."""
    target = path or READY_FILE
    try:
        with open(target, "w", encoding="utf-8") as handle:
            handle.write("ready\n")
    except OSError as exc:  # pragma: no cover - a read-only /tmp is a broken pod
        print(f"could not write the ready file {target}: {exc}", file=sys.stderr)


def _kube(args):
    return KubeClient(
        kubeconfig=getattr(args, "kubeconfig", ""),
        namespace=getattr(args, "namespace", "efda-system"),
    )


def _store():
    redis = RedisClient()
    return ArtifactStore(redis), CheckpointStore(redis), redis


def _load_registry(kube, namespace="efda-system"):
    """The failure-class registry the sink validates against."""
    configmap = kube.get("configmaps", "failure-class-registry", namespace=namespace)
    data = {}
    if configmap:
        raw = (configmap.get("data") or {}).get("classes.json") or "{}"
        try:
            data = json.loads(raw)
        except ValueError:
            data = {}
    if not data:
        data = {"version": "v1", "classes": [{"id": "v1-fallback"}]}
    return FailureClassRegistry.from_dict(data)


def cmd_reconcile(args):
    kube = _kube(args)
    if args.interval:
        while True:
            summary = run_reconcile(kube, namespace=args.namespace)
            print(json.dumps(summary, sort_keys=True))
            _write_ready_file()
            time.sleep(args.interval)
    summary = run_reconcile(kube, namespace=args.namespace)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def cmd_baseline(args):
    kube = _kube(args)
    summary = run_reconcile(kube, generate_baseline=True, namespace=args.namespace)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def cmd_snapshot(args):
    from .reconciler import build_snapshot, collect_packs

    kube = _kube(args)
    snapshot = build_snapshot(collect_packs(kube))
    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0


def cmd_reason(args):
    kube = _kube(args)
    store, _, redis = _store()
    artifact = None
    if args.artifact_ref:
        artifact = store.read_by_key(args.artifact_ref)
    elif args.artifact_file:
        with open(args.artifact_file, "r", encoding="utf-8") as handle:
            artifact = json.load(handle)
    if artifact is None:
        print("no artifact to reason over", file=sys.stderr)
        return 2

    packs = {}
    for item in kube.list("skillpacks", all_namespaces=True):
        packs[(item.get("metadata") or {}).get("name", "")] = item

    identity = artifact.get("identity") or {}
    component_class = identity.get("component_class", "")
    candidates = select_packs(
        list(packs.values()), component_class, identity.get("component_version", "")
    )
    if args.pack_ref:
        candidates = [
            p
            for p in candidates
            if (p.get("metadata") or {}).get("name") == args.pack_ref
        ]
    if not candidates:
        report = {
            "status": "COVERAGE_VIOLATION",
            "cause": "",
            "confidence": 0.0,
            "packRef": "",
            "signatureId": "",
            "evidenceRefs": [],
            "questionsAsked": [],
            "warnings": [f"no pack covers class {component_class!r}"],
        }
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1

    pack = candidates[0]
    spec = effective_pack(pack, packs)
    registry = _load_registry(kube, args.namespace)
    report = reason(
        artifact, {"metadata": pack.get("metadata"), "spec": spec}, registry=registry
    )
    report["componentClass"] = component_class
    runner_id = identity.get("runner_id") or "unknown"
    report["runnerId"] = runner_id
    if args.store:
        store.write_report(report, runner_id)
        diagnostic = {
            "apiVersion": "efda.estate/v1",
            "kind": "DiagnosticReport",
            "metadata": {
                "name": f"{component_class}-{runner_id}".lower().replace("_", "-")[:253]
            },
            "spec": {
                key: value for key, value in report.items() if not key.startswith("_")
            },
        }
        try:
            kube.apply(diagnostic)
        except KubeError as exc:
            print(f"the report was stored but not published: {exc}", file=sys.stderr)
    print(json.dumps(report, indent=2, sort_keys=True))
    redis.close()
    return 0 if report.get("status") == "DIAGNOSED" else 1


def cmd_execute(args):
    allowlist = load_allowlist(args.allowlist)
    if args.watch:
        return _execute_watch(args, allowlist)
    with open(args.report, "r", encoding="utf-8") as handle:
        report = json.load(handle)
    decision = decide(report, allowlist)
    kube = _kube(args)
    artifact = execute(decision, kube)
    print(json.dumps(artifact, indent=2, sort_keys=True))
    return 0 if decision.get("outcome") == "EXECUTE" else 1


def _execute_watch(args, allowlist):
    """The executor loop: read the reports, run them through the gates."""
    kube = _kube(args)
    store, _, redis = _store()
    while True:
        for report in store.list_reports():
            runner_id = report.get("runnerId") or report.get("runner_id") or "unknown"
            if store.remediated(runner_id):
                continue
            decision = decide(report, allowlist)
            artifact = execute(decision, kube)
            spec = artifact.get("spec") or {}
            spec["runnerId"] = runner_id
            artifact["spec"] = spec
            store.write_remediation(artifact, runner_id)
            try:
                kube.apply(
                    {
                        "apiVersion": "efda.estate/v1",
                        "kind": "RemediationArtifact",
                        "metadata": {
                            "name": f"{spec.get('signatureId', 'unknown')}-{runner_id}".lower()[
                                :253
                            ]
                        },
                        "spec": spec,
                    }
                )
            except KubeError as exc:
                print(
                    f"the remediation artifact was stored but not published: {exc}",
                    file=sys.stderr,
                )
            print(
                json.dumps({"runner": runner_id, "outcome": spec.get("outcome")}),
                flush=True,
            )
        _write_ready_file()
        time.sleep(args.interval)


def cmd_validate(args):
    with open(args.pack, "r", encoding="utf-8") as handle:
        pack = json.load(handle)
    corpus = []
    if args.corpus:
        with open(args.corpus, "r", encoding="utf-8") as handle:
            corpus = json.load(handle)
    report = validate_pack(pack, corpus, allowlist=load_allowlist(args.allowlist))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("ok") else 1


def cmd_synthesize(args):
    with open(args.corpus, "r", encoding="utf-8") as handle:
        artifacts = json.load(handle)
    corpus = corpus_from_artifacts(artifacts)
    candidate = synthesize(corpus, args.component_class, namespace=args.namespace)
    print(json.dumps(candidate, indent=2, sort_keys=True))
    return 0


def cmd_register(args):
    """Self-registration: an agent or a script declares itself."""
    kube = _kube(args)
    registration = {
        "apiVersion": "efda.estate/v1",
        "kind": "ComponentRegistration",
        "metadata": {
            "name": args.component_id,
            "namespace": args.namespace,
            "labels": {"efda.estate/component-class": args.component_class},
        },
        "spec": {
            "componentClass": args.component_class,
            "componentKind": args.component_kind,
            "versionsInService": [],
            "owner": {"team": args.team, "escalation": ""},
            "tenantId": args.tenant,
            "minCoverageTier": "baseline",
            "discovery": {"method": "wrapper_self_register", "lastSeen": _now()},
        },
    }
    kube.apply(registration)
    print(json.dumps(registration, indent=2, sort_keys=True))
    return 0


def _now():
    from .contract import now_iso

    return now_iso()


def cmd_drain(args):
    """Push the local WAL into the sink that came back."""
    store, _, redis = _store()
    if args.wal_dir:
        store.wal_dir = args.wal_dir
    drained = store.wal_drain_all()
    print(json.dumps(drained, indent=2, sort_keys=True))
    redis.close()
    return 0


def cmd_wrapper(args, rest):
    return wrapper_main(rest)


def cmd_verify(args):
    from .verify import run_phase

    return run_phase(args.phase, namespace=args.namespace)


def cmd_describe(args):
    """What this build is wired to, and nothing else.

    The liveness probe runs this. It answers the only question a liveness probe can ask that
    is worth asking: can this process still load itself and name the sink it talks to? It
    touches neither the cluster nor the sink, so a probe that ran the whole reconcile pass
    would fail for reasons that are not liveness (an API server blip is availability, not
    death).
    """
    wiring = {
        "namespace": args.namespace,
        "sink": {
            "host": os.environ.get("EFDA_REDIS_HOST", ""),
            "port": os.environ.get("EFDA_REDIS_PORT", ""),
        },
        "allowlist": getattr(args, "allowlist", "")
        or os.environ.get("EFDA_ALLOWLIST_PATH", ""),
        "ready_file": READY_FILE,
    }
    print(json.dumps(wiring, indent=2, sort_keys=True))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="efda", description="the estate's universal coverage layer"
    )
    parser.add_argument(
        "--namespace", default=os.environ.get("EFDA_NAMESPACE", "efda-system")
    )
    parser.add_argument("--kubeconfig", default=os.environ.get("KUBECONFIG", ""))
    sub = parser.add_subparsers(dest="command")

    reconcile = sub.add_parser("reconcile", help="observe, register, cover, report")
    reconcile.add_argument("--interval", type=int, default=0)
    reconcile.set_defaults(func=cmd_reconcile)

    baseline = sub.add_parser("baseline", help="generate the baseline packs")
    baseline.set_defaults(func=cmd_baseline)

    snapshot = sub.add_parser("snapshot", help="print the registry snapshot")
    snapshot.set_defaults(func=cmd_snapshot)

    reason_parser = sub.add_parser("reason", help="reason over an artifact")
    reason_parser.add_argument("--artifact-ref", default="")
    reason_parser.add_argument("--artifact-file", default="")
    reason_parser.add_argument("--pack-ref", default="")
    reason_parser.add_argument(
        "--store", action="store_true", help="publish the report for the executor"
    )
    reason_parser.set_defaults(func=cmd_reason)

    execute_parser = sub.add_parser(
        "execute", help="run a report through the remediation gates"
    )
    execute_parser.add_argument("--report", default="")
    execute_parser.add_argument("--allowlist", default="")
    execute_parser.add_argument(
        "--watch", action="store_true", help="watch for reports and gate them"
    )
    execute_parser.add_argument("--interval", type=int, default=15)
    execute_parser.set_defaults(func=cmd_execute)

    validate_parser = sub.add_parser("validate", help="the five adversarial checks")
    validate_parser.add_argument("--pack", required=True)
    validate_parser.add_argument("--corpus", default="")
    validate_parser.add_argument("--allowlist", default="")
    validate_parser.set_defaults(func=cmd_validate)

    synth_parser = sub.add_parser(
        "synthesize", help="observed failures -> a candidate pack"
    )
    synth_parser.add_argument("--corpus", required=True)
    synth_parser.add_argument("--component-class", required=True)
    synth_parser.set_defaults(func=cmd_synthesize)

    register = sub.add_parser("register", help="self-register an agent or a script")
    register.add_argument("--component-id", required=True)
    register.add_argument("--component-class", required=True)
    register.add_argument("--component-kind", default="agent")
    register.add_argument("--team", default="platform-fallback")
    register.add_argument("--tenant", default="default")
    register.set_defaults(func=cmd_register)

    verify = sub.add_parser("verify", help="the verification playbook")
    verify.add_argument("--phase", type=int, required=True)
    verify.set_defaults(func=cmd_verify)

    drain = sub.add_parser("drain", help="push the local WAL into the sink")
    drain.add_argument("--wal-dir", default=os.environ.get("EFDA_WAL_DIR", ""))
    drain.set_defaults(func=cmd_drain)

    describe = sub.add_parser("describe", help="print what this build is wired to")
    describe.set_defaults(func=cmd_describe)

    return parser


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "wrapper":
        return wrapper_main(argv[1:])
    if argv and argv[0] == "wrapper-observe":
        return wrapper_main(argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 2
    try:
        return args.func(args)
    except KubeError as exc:
        print(f"kubernetes error: {exc}", file=sys.stderr)
        return 3
    except RedisError as exc:
        print(f"store error: {exc}", file=sys.stderr)
        return 4


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
