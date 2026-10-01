#!/usr/bin/env python3
"""silence-audit -- every workload on the estate, and whether its failure would be heard.

Founder law, 2026-09-30: nothing runs without monitoring and alerts; nothing fails silently; a
workload that cannot be heard is better off not running. This is the audit that law names. It
reads the cluster once (kubectl JSON, no other dependency) and grades three things:

  1. The alert pipeline itself: Prometheus, Alertmanager, kube-state-metrics, the operator.
     If any of these is not Ready, every rule on the cluster is unevaluated and EVERY workload
     is silent, whatever its own row says. Measured 2026-09-30: all four at 0/0 replicas since
     2026-09-26T10:01Z; 126 alert rules defined, none evaluated, and nobody was told.
  2. Every Deployment / StatefulSet / DaemonSet / CronJob: its state (ok, zero, pending,
     crashloop, stale-cron, never-ran), whether a Flux row owns it (else ORPHAN: nothing
     converges it), and whether a PrometheusRule names its namespace or name (else UNWATCHED).
  3. Flux Kustomizations not Ready, and platform/<dir>s on disk that no row deploys.

Verdict per workload: HEARD, SILENT (running with no rule or no pipeline), or DEAD (should run,
does not). Exit 1 when anything is SILENT or the pipeline is down: a green audit that cannot
fail is not an audit. JSON with --json for the collector and /fleet.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

SYSTEM_NS = {"kube-system", "kube-public", "kube-node-lease"}
PIPELINE = [  # (namespace, kind, name)
    ("monitoring", "statefulset", "prometheus-kps"),
    ("monitoring", "statefulset", "alertmanager-kps"),
    ("monitoring", "deployment", "kps-operator"),
    ("monitoring", "deployment", "kube-prometheus-stack-kube-state-metrics"),
]


def kget(kind: str, ns: str | None = None) -> list[dict]:
    cmd = ["kubectl", "get", kind, "-o", "json"]
    cmd += ["-n", ns] if ns else ["-A"]
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, check=True
        ).stdout  # noqa: S603  # fixed argv: kubectl get <kind> -o json, no shell
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(
            f"BLIND   silence-audit  kubectl get {kind}: {getattr(e, 'stderr', e)}",
            file=sys.stderr,
        )
        sys.exit(2)
    return json.loads(out).get("items", [])


def flux_owner(meta: dict) -> str:
    lab = meta.get("labels") or {}
    return lab.get("kustomize.toolkit.fluxcd.io/name") or (
        "helm:" + lab["helm.toolkit.fluxcd.io/name"]
        if "helm.toolkit.fluxcd.io/name" in lab
        else ""
    )


def rule_index(rules: list[dict]) -> tuple[set[str], set[str]]:
    """Namespaces and workload names any alert expression or label mentions."""
    ns_hits, name_hits = set(), set()
    for r in rules:
        blob = json.dumps(r.get("spec", {}))
        ns_hits.add(r["metadata"]["namespace"])
        for token in (
            blob.replace('"', " ")
            .replace("'", " ")
            .replace("{", " ")
            .replace("}", " ")
            .split()
        ):
            for part in (
                token.replace("=", " ").replace(",", " ").replace("~", " ").split()
            ):
                if part and part[0].isalpha() and "-" in part:
                    name_hits.add(part.strip('"'))
    return ns_hits, name_hits


def audit(repo: Path | None) -> dict:
    now = time.time()
    pods = kget("pods")
    pods_by_ns: dict[str, list[dict]] = {}
    for p in pods:
        pods_by_ns.setdefault(p["metadata"]["namespace"], []).append(p)

    # 1. pipeline
    pipeline = []
    alive = True
    for ns, kind, name in PIPELINE:
        items = [i for i in kget(kind, ns) if i["metadata"]["name"] == name]
        if not items:
            pipeline.append(
                {"name": name, "ready": 0, "wanted": None, "state": "absent"}
            )
            alive = False
            continue
        st = items[0].get("status", {})
        ready, wanted = (
            st.get("readyReplicas", 0) or 0,
            items[0]["spec"].get("replicas"),
        )
        ok = bool(ready) and ready == wanted
        alive &= ok
        pipeline.append(
            {
                "name": name,
                "ready": ready,
                "wanted": wanted,
                "state": "ok" if ok else "down",
            }
        )

    # a zero that is meant: a KEDA ScaledObject parks it, or its Flux row is on-demand / none
    parked = {
        (so["metadata"]["namespace"], so["spec"]["scaleTargetRef"]["name"])
        for so in kget("scaledobjects")
    }
    ks_all = kget("kustomizations")
    parked_rows = {
        k["metadata"]["name"]
        for k in ks_all
        if (k["metadata"].get("annotations") or {}).get("idp.estate.io/runtime")
        in ("on-demand", "none")
    }

    rules = kget("prometheusrules")
    n_alerts = sum(
        1
        for r in rules
        for g in r["spec"].get("groups", [])
        for a in g.get("rules", [])
        if "alert" in a
    )
    ns_hits, name_hits = rule_index(rules)

    # 2. workloads
    rows = []

    def grade(ns: str, kind: str, name: str, state: str, meta: dict) -> None:
        owner = flux_owner(meta)
        watched = ns in ns_hits or name in name_hits
        if state == "parked":
            verdict = "PARKED"
        elif state in ("zero", "never-ran", "stale-cron", "pending"):
            verdict = "DEAD"
        elif not alive or not watched:
            verdict = "SILENT"
        else:
            verdict = "HEARD"
        rows.append(
            {
                "namespace": ns,
                "kind": kind,
                "name": name,
                "state": state,
                "owner": owner or "ORPHAN",
                "watched": watched,
                "verdict": verdict,
            }
        )

    for kind in ("deployments", "statefulsets"):
        for w in kget(kind):
            m, ns = w["metadata"], w["metadata"]["namespace"]
            if ns in SYSTEM_NS:
                continue
            want, ready = (
                w["spec"].get("replicas", 1),
                (w.get("status", {}).get("readyReplicas") or 0),
            )
            if want == 0 and (
                (ns, m["name"]) in parked or flux_owner(m) in parked_rows
            ):
                state = "parked"
            elif want == 0:
                state = "zero"
            elif ready < want:
                crash = any(
                    cs.get("state", {}).get("waiting", {}).get("reason")
                    == "CrashLoopBackOff"
                    for p in pods_by_ns.get(ns, [])
                    if p["metadata"]["name"].startswith(m["name"])
                    for cs in p.get("status", {}).get("containerStatuses", [])
                )
                state = "crashloop" if crash else "pending"
            else:
                state = "ok"
            grade(ns, kind[:-1], m["name"], state, m)
    for w in kget("daemonsets"):
        m, ns = w["metadata"], w["metadata"]["namespace"]
        if ns in SYSTEM_NS:
            continue
        st = w.get("status", {})
        state = (
            "ok"
            if st.get("numberReady", 0) == st.get("desiredNumberScheduled", 0)
            else "pending"
        )
        grade(ns, "daemonset", m["name"], state, m)
    for w in kget("cronjobs"):
        m, ns = w["metadata"], w["metadata"]["namespace"]
        if ns in SYSTEM_NS:
            continue
        if w["spec"].get("suspend"):
            state = "zero"
        else:
            last = w.get("status", {}).get("lastScheduleTime")
            if not last:
                state = "never-ran"
            else:
                age = (
                    now
                    - time.mktime(time.strptime(last, "%Y-%m-%dT%H:%M:%SZ"))
                    + time.timezone
                )
                state = "stale-cron" if age > 2 * 86400 else "ok"
            # a run that exists but never left Pending is a run that did not happen
            if any(
                p["status"].get("phase") == "Pending"
                and (m["name"] in p["metadata"]["name"])
                for p in pods_by_ns.get(ns, [])
            ):
                state = "pending"
        grade(ns, "cronjob", m["name"], state, m)

    # 3. flux
    flux = []
    ks = ks_all
    row_paths = {(k["spec"].get("path") or "").strip("./") for k in ks}
    for k in ks:
        conds = {c["type"]: c for c in k.get("status", {}).get("conditions", [])}
        ready = conds.get("Ready", {}).get("status")
        if ready != "True":
            flux.append(
                {
                    "row": k["metadata"]["name"],
                    "ready": ready,
                    "reason": conds.get("Ready", {}).get("message", "")[:160],
                }
            )
    rowless = []
    if repo and (repo / "platform").is_dir():
        for d in sorted((repo / "platform").iterdir()):
            if (
                d / "kustomization.yaml"
            ).is_file() and f"platform/{d.name}" not in row_paths:
                rowless.append(d.name)

    parked_n = sum(1 for r in rows if r["verdict"] == "PARKED")
    silent = [r for r in rows if r["verdict"] == "SILENT"]
    dead = [r for r in rows if r["verdict"] == "DEAD"]
    orphans = [r for r in rows if r["owner"] == "ORPHAN"]
    return {
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        "pipeline": {
            "alive": alive,
            "components": pipeline,
            "alert_rules_defined": n_alerts,
        },
        "workloads": rows,
        "flux_not_ready": flux,
        "platform_dirs_without_row": rowless,
        "summary": {
            "workloads": len(rows),
            "heard": len(rows) - len(silent) - len(dead) - parked_n,
            "parked": parked_n,
            "silent": len(silent),
            "dead": len(dead),
            "orphans": len(orphans),
            "flux_not_ready": len(flux),
            "rowless_dirs": len(rowless),
        },
        "verdict": "SILENT" if (not alive or silent) else ("DEAD" if dead else "HEARD"),
    }


def render(a: dict) -> str:
    s, p = a["summary"], a["pipeline"]
    out = [f"silence-audit  {a['measured_at']}  verdict={a['verdict']}"]
    out.append(
        f"pipeline  {'ALIVE' if p['alive'] else 'DOWN'}  rules_defined={p['alert_rules_defined']}  "
        + "  ".join(f"{c['name']}={c['ready']}/{c['wanted']}" for c in p["components"])
    )
    if not p["alive"]:
        out.append(
            "          every rule below is unevaluated: the whole estate is silent until this is up"
        )
    out.append(
        f"workloads {s['workloads']}  heard={s['heard']}  silent={s['silent']}  dead={s['dead']}  parked={s['parked']}  "
        f"orphans={s['orphans']}  flux_not_ready={s['flux_not_ready']}  rowless_dirs={s['rowless_dirs']}"
    )
    out.append(
        f"{'VERDICT':7} {'STATE':10} {'NAMESPACE':18} {'KIND':11} {'NAME':44} OWNER"
    )
    order = {"DEAD": 0, "SILENT": 1, "PARKED": 2, "HEARD": 3}
    for r in sorted(
        a["workloads"], key=lambda r: (order[r["verdict"]], r["namespace"], r["name"])
    ):
        if r["verdict"] in ("HEARD", "PARKED"):
            continue
        out.append(
            f"{r['verdict']:7} {r['state']:10} {r['namespace']:18} {r['kind']:11} {r['name'][:44]:44} {r['owner']}"
        )
    for f in a["flux_not_ready"]:
        out.append(f"FLUX    {str(f['ready']):10} {f['row']:30} {f['reason']}")
    if a["platform_dirs_without_row"]:
        out.append(
            "ROWLESS platform/ dirs no Kustomization deploys: "
            + " ".join(a["platform_dirs_without_row"])
        )
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument(
        "--json-flag",
        default="false",
        help="the intent engine passes a bool as true/false",
    )
    ap.add_argument(
        "--repo",
        default="",
        help="idp checkout; enables the rowless platform/ dir check",
    )
    args = ap.parse_args()
    repo = Path(args.repo).expanduser() if args.repo else None
    a = audit(repo)
    as_json = args.json or args.json_flag.lower() == "true"
    print(json.dumps(a, indent=1) if as_json else render(a))
    return 0 if a["verdict"] == "HEARD" else 1


if __name__ == "__main__":
    sys.exit(main())
