# 0035. The DROS kernel enforcer runs as one node DaemonSet; session pods stay restricted

- Status: PROPOSED 2026-09-30 (crew#987 CP7, piece 5). Founder decides.
- Date: 2026-09-30
- Deciders: founder
- Relates to: the Quad (idp #4764, docs/tickets/2026-09-28-sovereign-identity-substrate-dros.md),
  [0034](0034-workloads-are-placed-by-the-free-tier-not-by-the-cluster.md)

## The problem

The Quad's layer 4 (DROS) loads a BPF LSM program on `security_socket_connect` so an agent process
that is not going through its Elpis proxy gets `-EPERM` from the kernel. Loading a BPF LSM program
needs host-level privilege. `deploy/production-agent-pod.yaml` put `dros-daemon` as a
`privileged: true` sidecar inside every agent pod, in a namespace labelled PSS `restricted`, which
Kyverno and PSS refuse. The question was whether kernel egress enforcement can exist at all without
breaking the restricted posture of the pods it guards.

## What was measured (2026-09-30)

- **BPF LSM is active on both OKE nodes.** `/sys/kernel/security/lsm` reads
  `lockdown,capability,yama,selinux,bpf` on 10.0.148.221 and 10.0.159.197 (read through the
  privileged `calico-node` pods), and `/sys/kernel/btf/vmlinux` exists (CO-RE works). Kernel
  5.15.0-322.203.3.5.el8uek.aarch64. No reboot and no boot-parameter change is needed.
- **Privileged namespaces already exist** for node agents: `calico-system`, `coroot`,
  `observability-agent`, `tailscale`, `tigera-operator` carry `pod-security.kubernetes.io/enforce=privileged`.
- **The BPF program has two bypasses** (`bpf/dros_enforce.bpf.c` on main):
  1. It keys `agent_process_status` on the host **PID** (tgid) and lets any unregistered PID through
     (step 6, "Unknown process: allow"). Any subprocess an agent spawns (`git`, `curl`, `python`)
     has a new PID, is unregistered, and connects freely. A sidecar also sees container PIDs, not
     the host PIDs `bpf_get_current_pid_tgid()` returns, so `/register?pid=` cannot match.
  2. It returns 0 for every non-`AF_INET` socket (step 2), so an IPv6 `connect()` is never checked.
- The program allows only `127.0.0.1:8080`; a session pod has two Elpis listeners (8080 lane-writer,
  8081 model), so 8081 is refused.

## Decision

1. **One enforcer per node, not per pod.** `dros-daemon` runs as a DaemonSet in its own namespace
   `dros-system`, labelled PSS `privileged` like `calico-system`, and is the only workload there.
   Session pods and their namespace stay PSS `restricted`; nothing in a session pod is privileged.
   Its privilege is scoped: `privileged: false`, `capabilities.add: [BPF, PERFMON, SYS_RESOURCE,
   MAC_ADMIN]`, `hostPID: false`, read-only root, `/sys/fs/bpf` and `/sys/fs/cgroup` mounted
   read-only except the bpffs pin path. If the loader proves it needs `SYS_ADMIN` on UEK 5.15, add
   that one capability, never `privileged: true`. Its control socket is a Unix socket reachable only
   by the session-controller (the node-local API that registers and revokes sessions).
2. **Key on the cgroup, not the PID.** Replace the PID map with a map keyed by
   `bpf_get_current_cgroup_id()`. A session is registered by the cgroup id of its `agent-core`
   container, which the daemon resolves from the pod UID and container id under `/sys/fs/cgroup`.
   Every process in that container, including every subprocess, shares the cgroup, so the
   subprocess bypass closes. Revocation writes `REVOKED` for the cgroup id: the next `connect()` from
   any process in it gets `-EPERM`.
3. **Default deny for managed cgroups on every family.** For a registered cgroup: allow only
   `127.0.0.1:{8080,8081}` (Elpis), `AF_UNIX` (the SPIRE workload socket), and nothing on
   `AF_INET6` or any other family. Unregistered cgroups stay allowed, because DROS does not govern
   the rest of the node.
4. **Today, before DROS is live: a NetworkPolicy fallback.** Session pods get an egress policy that
   allows only the lane-writer, the in-cluster LiteLLM, SPIRE/OIDC discovery, the session-controller
   (`/attest`) and DNS. This is pod-level, not process-level: `agent-core` could reach LiteLLM
   without its Elpis signature. It cannot write anything, though, because the lane-writer refuses
   every unsigned request and the pod holds no git credential. DROS closes the remaining gap, which
   is unsigned model calls.

## Placement (ADR 0034)

The DaemonSet requests `10m` CPU / `32Mi` per node, 20m / 64Mi across both nodes. Session pods are
governed by the session cap, not by this ADR.

## What is not decided here

The founder's ADR 0034 CPU ceiling (1.8 CPU of node requests) and whether sessions use the
`/attest` ephemeral key (piece 4) are separate founder decisions on crew#987.

## Proof that would make this operating

A session pod whose `agent-core` runs `python3 -c "import socket; socket.create_connection(('1.1.1.1', 443))"`,
and the same from a `sh -c` subprocess and over IPv6, each gets `PermissionError` (`EPERM`), while
the same container reaches `127.0.0.1:8080`. Revoking the session makes the next Elpis-bound
connect fail too. All of it is shown live on /fleet.
