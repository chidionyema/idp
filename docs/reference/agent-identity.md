# Agent cluster identity — zero-trust read access (WJ.1)

Agents are not founders. They do not hold OCI credentials, do not have a kubeconfig, and cannot
`kubectl apply` anything. What they CAN do is read cluster state — pods, logs, events — through
the JIT broker, using a one-hour read-only token minted on demand.

## The path (three steps)

```
agent session
  └─▶ bin/idp-kube get pods -n llm
        └─▶ bin/idp-jit identity          # step 1: present the agent key
              └─▶ jit-broker /identity    # step 2: broker validates + mints agent-reader token
                    └─▶ kubectl (read-only KUBECONFIG written to tmp) # step 3: read
```

`bin/idp-kube` wraps `bin/idp-jit identity` transparently. Agents only need to know `bin/idp-kube`.

## What agents may read

```bash
bin/idp-kube get pods -n <namespace>
bin/idp-kube get pods -A                          # all namespaces
bin/idp-kube logs -n <namespace> deployment/<name> --tail=100
bin/idp-kube get events -n <namespace> --sort-by=.lastTimestamp
bin/idp-kube describe deployment/<name> -n <namespace>
bin/idp-kube get externalsecrets -A
```

The `agent-reader` ServiceAccount is bound to a ClusterRole that grants `get`, `list`, `watch`
on most resource types. It cannot `create`, `update`, `delete`, `exec`, or `port-forward`.

## The agent key

The key lives at `$XDG_STATE_HOME/idp/agent-key` (default: `~/.local/state/idp/agent-key`).
It can also be set via `JIT_AGENT_KEY` environment variable. The broker validates it and returns
a Kubernetes ServiceAccount token — the key itself never leaves the Mac.

`bin/idp-jit identity` prints "BLOCKED" if the key is absent:
```
BLOCKED  this device holds no agent key. Set JIT_AGENT_KEY, or put it in
         $XDG_STATE_HOME/idp/agent-key
```

## Provisioning on a new machine (founder action — not automatable from an agent session)

The key is stored in the estate vault under entry `jit-broker`, field `JIT_AGENT_KEY`. Delivery
requires an active OCI session (the vault is in OCI Secrets Manager):

```bash
# Step 1 — one-time browser authentication (interactive, founder only)
bin/idp-oci-bootstrap

# Step 2 — deliver the key without printing it (LAW 54: no paste)
bin/idp-mac-secret-deliver \
  --entry jit-broker \
  --key JIT_AGENT_KEY \
  --out ~/.local/state/idp/agent-key \
  --service local
```

`bin/idp-mac-secret-deliver` will not run from an agent session — by design. It requires
the `idp-cloud` OCI identity, which agents do not hold.

## Why agents don't get write access

WJ.1 (2026-09-17 founder ruling): "the agent's identity is minted by the broker, not by the
founder's OCI principal." The broker mints the weakest token that unblocks the read operation.
A write capability would need quorum + hardware signature (see `[capabilities]` in AGENTS.md).
The read path is the diagnostic path — agents read, then propose fixes via PRs.

## Kyverno injection exception (2026-09-17 incident)

The `inject-otel-endpoint` ClusterPolicy (platform/edge/inject-otel-endpoint.yaml) injects
`OTEL_EXPORTER_OTLP_ENDPOINT` into every container at admission. `jit-broker` already declares
this variable inline AND has a `valueFrom` fieldRef in the same env list (POD_NAMESPACE).
Kyverno's strategic merge patch conflicts with mixed value/valueFrom entries, producing an
invalid object the k8s API rejects.

**Fix (PR #3711):** added `jit-broker` and `idp-engine` to the injection exclusion list.
Any workload that has BOTH an inline `OTEL_EXPORTER_OTLP_ENDPOINT` AND a `valueFrom` entry in
the same container env list must be added to the exclusion list in
`platform/edge/inject-otel-endpoint.yaml` — or the inline declaration must be removed and
Kyverno trusted to inject it.

## Related files

| File | Purpose |
|---|---|
| `bin/idp-kube` | Thin wrapper — calls idp-jit identity then runs kubectl |
| `bin/idp-jit` | JIT broker client — identity, ask, state, grants |
| `platform/jit/deployment.yaml` | The broker Deployment in namespace `jit` |
| `platform/jit/rbac.yaml` | agent-reader ClusterRole + RoleBindings |
| `platform/jit/grants.yaml` | The closed set of namespaces agents may ask about |
| `platform/edge/inject-otel-endpoint.yaml` | OTel injection policy (exclusion list here) |
| `bin/idp-mac-secret-deliver` | Secret delivery tool (founder-only, needs OCI session) |
