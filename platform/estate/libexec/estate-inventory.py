#!/usr/bin/env python3
"""estate-inventory -- every platform/ component on three tiers: declared, deployed, running.

usage: estate-inventory.py [json]       (IDP_REPO, IDP_REF override where "declared" is read)

"Merged" is not "deployed" and "deployed" is not "running". Since c96359f4 (2026-09-26) most
platform/ paths have no Flux row: their objects keep running, frozen, and a merged change to
them never lands. get_estate_inventory (mcp/plugins/estate_inventory.py) answers from the hourly
crew/STATE.md snapshot and is forbidden to probe; this is the live read it cannot do.

  declared   main's clusters/oke/*.yaml: the Flux Kustomization rows and the path each applies
  deployed   the live Kustomization covering the path: Ready, and on the source's revision?
  running    Deployments/StatefulSets/DaemonSets owned by that row (kustomize label, or a
             HelmRelease the row owns): ready/desired

Status per component: operating, degraded, frozen (runs, no live row: git changes never land),
declared-not-deployed, code-only. When the cluster cannot be read the live tiers are UNKNOWN --
never "absent": a read that failed proved nothing.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(os.environ.get("IDP_REPO", Path.home() / "Documents/code/idp"))
REF = os.environ.get("IDP_REF", "origin/main")
KL = "kustomize.toolkit.fluxcd.io/name"
HL = "helm.toolkit.fluxcd.io/name"


def git(*a: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO), *a], capture_output=True, text=True, timeout=30
    ).stdout


def kubectl(*a: str) -> dict | None:
    try:
        r = subprocess.run(
            ["kubectl", "--request-timeout=20s", *a, "-o", "json"],
            capture_output=True,
            text=True,
            timeout=40,
        )
        return json.loads(r.stdout) if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None


def declared_rows() -> dict[str, str]:
    """name -> path for every Flux Kustomization row in main's clusters/oke."""
    rows = {}
    for f in git("ls-tree", "--name-only", f"{REF}:clusters/oke").split():
        if not f.endswith(".yaml"):
            continue
        for doc in git("show", f"{REF}:clusters/oke/{f}").split("\n---"):
            if (
                "kind: Kustomization" not in doc
                or "kustomize.toolkit.fluxcd.io" not in doc
            ):
                continue
            name = re.search(r"^  name: (\S+)", doc, re.M)
            path = re.search(r"^  path: (\S+)", doc, re.M)
            if name and path:
                rows[name.group(1)] = path.group(1)
    return rows


def component_of(path: str) -> str | None:
    m = re.match(r"\./platform/([^/]+)", path or "")
    return m.group(1) if m else None


def main() -> None:
    if REF.startswith("origin/"):
        subprocess.run(
            ["git", "-C", str(REPO), "fetch", "-q", "origin", REF[7:]], timeout=60
        )
    comps = {
        c: {} for c in git("ls-tree", "-d", "--name-only", f"{REF}:platform").split()
    }
    decl = declared_rows()

    ks = kubectl("get", "kustomizations.kustomize.toolkit.fluxcd.io", "-A")
    hrs = kubectl("get", "helmreleases.helm.toolkit.fluxcd.io", "-A")
    wls = kubectl("get", "deployments,statefulsets,daemonsets", "-A")
    src = kubectl("-n", "flux-system", "get", "gitrepository", "flux-system")
    live_ok = None not in (ks, hrs, wls)
    head = ((src or {}).get("status") or {}).get("artifact", {}).get("revision", "")

    live = {}
    for k in (ks or {}).get("items", []):
        ready = next(
            (
                c
                for c in k.get("status", {}).get("conditions", [])
                if c["type"] == "Ready"
            ),
            {},
        )
        applied = k.get("status", {}).get("lastAppliedRevision", "")
        live[k["metadata"]["name"]] = {
            "path": k["spec"].get("path", ""),
            "ready": ready.get("status", "Unknown"),
            "stale": bool(
                head
                and k["spec"]["sourceRef"].get("name") == "flux-system"
                and applied != head
            ),
            "applied": applied.split(":")[-1][:8],
        }
    hr_owner = {
        (h["metadata"]["namespace"], h["metadata"]["name"]): h["metadata"]
        .get("labels", {})
        .get(KL)
        for h in (hrs or {}).get("items", [])
    }

    def comp_for_owner(owner: str) -> str:
        row = live.get(owner) or ({"path": decl[owner]} if owner in decl else None)
        c = component_of(row["path"]) if row else None
        # a live row outside platform/ (flux-system -> ./clusters/oke) is its own component;
        # "?" marks an owner that is neither a live row nor a platform/ directory
        return c or (owner if owner in comps or owner in live else f"?{owner}")

    for c in comps:
        comps[c] = {
            "declared": sorted(n for n, p in decl.items() if component_of(p) == c),
            "deployed": sorted(
                n for n, r in live.items() if component_of(r["path"]) == c
            ),
            "owners": set(),
            "ready": 0,
            "desired": 0,
            "not_ready": [],
        }
    for w in (wls or {}).get("items", []):
        md = w["metadata"]
        labels = md.get("labels", {})
        owner = labels.get(KL) or hr_owner.get((md["namespace"], labels.get(HL)))
        if not owner:
            continue
        c = comp_for_owner(owner)
        e = comps.setdefault(
            c,
            {
                "declared": [owner] if owner in decl else [],
                "deployed": [owner] if owner in live else [],
                "owners": set(),
                "ready": 0,
                "desired": 0,
                "not_ready": [],
            },
        )
        e["owners"].add(owner)
        st, spec = w.get("status", {}), w.get("spec", {})
        if w["kind"] == "DaemonSet":
            want, have = st.get("desiredNumberScheduled", 0), st.get("numberReady", 0)
        else:
            want, have = spec.get("replicas", 1), st.get("readyReplicas", 0)
        e["desired"] += want
        e["ready"] += have
        if have < want:
            e["not_ready"].append(f"{md['namespace']}/{md['name']} {have}/{want}")

    out = []
    for c, e in sorted(comps.items()):
        rows = [live[n] for n in e["deployed"]]
        orphans = sorted(o for o in e["owners"] if o not in live)
        if not live_ok:
            status = "UNKNOWN"
        elif rows:
            ok = all(r["ready"] == "True" and not r["stale"] for r in rows)
            status = "operating" if ok and not e["not_ready"] else "degraded"
        elif e["owners"]:  # scaled to zero still runs frozen objects
            status = "frozen"
        elif e["declared"]:
            status = "declared-not-deployed"
        else:
            status = "code-only"
        out.append(
            {
                "component": c,
                "status": status,
                "declared": e["declared"],
                "deployed": "UNKNOWN"
                if not live_ok
                else [
                    f"{n} ready={live[n]['ready']} rev={live[n]['applied'] or '-'}"
                    + (" STALE" if live[n]["stale"] else "")
                    for n in e["deployed"]
                ],
                "running": "UNKNOWN" if not live_ok else f"{e['ready']}/{e['desired']}",
                "orphan_owners": orphans,
                "not_ready": e["not_ready"],
            }
        )

    if sys.argv[1:] in (["json"], ["True"], ["true"]):
        print(
            json.dumps(
                {"head": head, "live_read": live_ok, "components": out}, indent=2
            )
        )
    else:
        print(
            f"declared from {REF}; live source revision {head.split(':')[-1][:8] or '-'}"
        )
        if not live_ok:
            print("!! cluster read failed: deployed/running are UNKNOWN, not absent")
        for r in out:
            if r["status"] == "code-only":
                continue
            dep = (
                r["deployed"]
                if isinstance(r["deployed"], str)
                else "; ".join(r["deployed"])
            )
            print(
                f"{r['status']:22} {r['component']:24} declared={','.join(r['declared']) or '-'}"
                f"  deployed={dep or '-'}  running={r['running']}"
                + (
                    f"  orphan-owner={','.join(r['orphan_owners'])}"
                    if r["orphan_owners"]
                    else ""
                )
            )
            for n in r["not_ready"][:5]:
                print(f"{'':24} not ready: {n}")
        counts: dict[str, int] = {}
        for r in out:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        print("summary: " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))


if __name__ == "__main__":
    main()
