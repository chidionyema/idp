#!/usr/bin/env python3
"""Fast cluster health check: DNS, vault, Flux blocks, IMDS. No pod exec."""

import json, subprocess, sys


def run(*a, timeout=8):
    try:
        r = subprocess.run(a, capture_output=True, text=True, timeout=timeout)  # noqa: S603 -- argv built in this file, no shell
        return r.stdout.strip(), r.returncode == 0
    except subprocess.TimeoutExpired:
        return "TIMEOUT", False


results = {}
failures = []

# CoreDNS
r, ok = run(
    "kubectl",
    "get",
    "deploy",
    "coredns",
    "-n",
    "kube-system",
    "-o",
    "jsonpath={.status.readyReplicas}/{.status.replicas}",
)
print(f"CoreDNS: {r}")
results["coredns"] = r

# CoreDNS forward
r, ok = run(
    "kubectl",
    "get",
    "configmap",
    "coredns",
    "-n",
    "kube-system",
    "-o",
    "jsonpath={.data.Corefile}",
)
if ok and r:
    fwd = [
        l.strip()
        for l in r.splitlines()
        if "forward" in l and not l.strip().startswith("#")
    ]
    print(f"Forward: {' '.join(fwd[:2])}")
    results["forward"] = fwd

# CoreDNS NetPol egress
r, ok = run(
    "kubectl",
    "get",
    "networkpolicy",
    "allow-dns-egress",
    "-n",
    "kube-system",
    "-o",
    "json",
)
if ok:
    d = json.loads(r)
    cidrs = []
    for rule in d.get("spec", {}).get("egress", []):
        for t in rule.get("to", []):
            cidr = t.get("ipBlock", {}).get("cidr", "")
            if cidr:
                cidrs.append(cidr)
    has_10 = any(c.startswith("10.") for c in cidrs)
    print(f"DNS NetPol egress cidrs: {cidrs}")
    results["dns_netpol_cidrs"] = cidrs
    if not has_10:
        failures.append(
            "COREDNS NetPol: no RFC1918 cidr — service IP 10.96.0.10 blocked"
        )

# IMDS egress
r, ok = run(
    "kubectl",
    "get",
    "networkpolicy",
    "allow-metadata-egress",
    "-n",
    "external-secrets",
    "-o",
    "json",
)
if ok:
    d = json.loads(r)
    ports = [
        p.get("port") for p in d.get("spec", {}).get("egress", [{}])[0].get("ports", [])
    ]
    print(f"IMDS ports: {ports}")
    results["imds_ports"] = ports
    if 443 not in ports:
        failures.append(
            f"IMDS egress: port 443 missing (only {ports}) — OCI InstancePrincipal hangs"
        )
else:
    results["imds_ports"] = []

# ClusterSecretStores
print()
r, ok = run("kubectl", "get", "clustersecretstore", "-A", "-o", "json")
if ok:
    for store in json.loads(r).get("items", []):
        name = store["metadata"]["name"]
        cond = next(
            (
                c
                for c in store.get("status", {}).get("conditions", [])
                if c.get("type") == "SecretStoreReady"
            ),
            None,
        )
        if cond:
            ready = cond.get("status") == "True"
            icon = "OK" if ready else "FAIL"
            msg = cond.get("message", "")[:70]
            print(f"ClusterSecretStore {name}: {icon}  {msg}")
            if not ready:
                failures.append(f"ClusterSecretStore/{name}: {msg}")
        else:
            print(f"ClusterSecretStore {name}: no conditions")
else:
    print(f"ClusterSecretStore query failed: {r}")

# ExternalSecrets stuck
r, ok = run("kubectl", "get", "externalsecret", "-A", "-o", "json")
if ok:
    stuck = [
        e
        for e in json.loads(r).get("items", [])
        if e.get("metadata", {}).get("namespace") != "flux-system"
        and e.get("status", {}).get("status", "") in ("", "InProgress")
    ]
    print(f"\nExternalSecrets stuck: {len(stuck)}")
    for es in stuck[:5]:
        ns = es["metadata"]["namespace"]
        n = es["metadata"]["name"]
        print(f"  FAIL  {ns}/{n}")
        failures.append(f"ExternalSecret {ns}/{n} not ready")
    if len(stuck) > 5:
        print(f"  ... +{len(stuck) - 5} more")

# Flux blocked
print()
r, ok = run("kubectl", "get", "kustomization", "-n", "flux-system", "-o", "json")
if ok:
    blocked = 0
    for k in json.loads(r).get("items", []):
        ready = next(
            (
                c
                for c in k.get("status", {}).get("conditions", [])
                if c.get("type") == "Ready"
            ),
            None,
        )
        if ready and ready.get("status") == "False":
            name = k["metadata"]["name"]
            msg = ready.get("message", "")[:80]
            deps = [d["name"] for d in k.get("spec", {}).get("dependsOn", [])]
            dep_str = f" (deps:{','.join(deps)})" if deps else ""
            print(f"Flux {name}: BLOCKED{dep_str}")
            print(f"  -> {msg}")
            failures.append(f"Flux/{name} blocked: {msg}")
            blocked += 1
    if blocked == 0:
        print("Flux: all kustomizations ready")
    results["flux_blocked"] = blocked

# GitRepository
r, ok = run(
    "kubectl", "get", "gitrepository", "flux-system", "-n", "flux-system", "-o", "json"
)
if ok:
    d = json.loads(r)
    rev = d.get("status", {}).get("artifact", {}).get("revision", "?")
    print(f"\nGitRepository revision: {rev}")
    results["git_revision"] = rev

# SPIRE
r, ok = run("kubectl", "get", "spireagent", "-n", "spire-mgmt", "-o", "json")
if ok:
    agents = json.loads(r).get("items", [])
    ready = sum(
        1
        for a in agents
        if next(
            (
                c.get("status") == "True"
                for c in a.get("status", {}).get("conditions", [])
                if c.get("type") == "Ready"
            ),
            False,
        )
    )
    total = len(agents)
    print(f"\nSPIRE agents: {ready}/{total} ready")
    results["spire"] = f"{ready}/{total}"
else:
    print("\nSPIRE: no spireagent CRD (ok if not deployed)")
    results["spire"] = "n/a"

# Summary
print()
print("FAILURES:" if failures else "ALL OK")
for f in failures:
    print(f"  FAIL  {f}")

sys.exit(1 if failures else 0)
