# 0034. Workloads are placed by the free tier, not by the cluster

- Status: DECIDED 2026-09-26. Founder: "we must never exceed the free tier", "mathematical
  guarantees only", "we lack creativity and common sense", "document this so this problem is
  solved forever".
- Date: 2026-09-26
- Deciders: founder
- Amends: [0004](0004-oracle-oke-is-the-kubernetes-target.md) (OKE on Always Free stays the
  target; this adds what may run on it and what may not)

## The problem

Everything the estate built went into the cluster. The cluster grew past the free tier, the
estate's own checks let it through, and it got stuck there:

| Fact | Measured |
|---|---|
| Tenancy upgraded to Pay As You Go ("Universal Credits") | 2026-08-24, now Suspended; cannot be downgraded |
| Worker pool | 2 × A1 6 OCPU / 24 GB = 12 OCPU / 48 GB against an allowance of 2 / 12 |
| Checks that passed it | tofu `capacity_cap` precondition, `policy/node_pool.rego`, `budget_monthly_usd: 50` (all deleted, PR #4368) |
| One workload's share | SigNoz ClickHouse used 2.0 of 2.6 cores in use (kubelet `/stats/summary`, 2026-09-26) |
| Everything else | ~0.2 cores of real use for Flux, traefik, coredns, KEDA, estate-db, NATS |
| Workloads at 0 replicas with nothing to wake them | 86 of 109 |
| New nodes | refused: `bootVolumeQuota Service limit reached` (2 × 100 GB boot = the 200 GB free total) |

The cluster was not short of capacity. Everything was placed in it by default.

## Decision

### 1. The ceiling is enforced by Oracle, not by us

`platform/oci/policy/free-tier-quota.statements.json` zeroes every compute quota and allows
A1 2 OCPU / 12 GB in AD-1 only. `bin/idp-oci-bootstrap --quota` applies it, and only the tenancy
owner can run that. No automated identity (estate-tofu, estate-ci, any agent) holds quota
permission, so nothing automated can raise its own ceiling. Budgets, alerts, rego and plan-time
checks detect; they are never called a gate.

### 2. Every workload is placed by this ladder, first rung that fits

| # | Question | Where it goes | Free allowance (hard-limited, no card) |
|---|---|---|---|
| 1 | Does anything use it? | **Delete it.** A workload at 0 that nothing wakes is deleted from git, not parked | — |
| 2 | Does it run on a schedule or as a batch? | **GitHub Actions** `schedule:` workflow | the CI the estate already runs |
| 3 | Is it telemetry (traces, logs, metrics, profiles)? | **Grafana Cloud free**, over OTLP | 10k series; 50 GB each of logs/traces/profiles a month; 14-day retention; over-limit data is dropped, never billed |
| 4 | Is it a small stateless HTTP handler (webhook, status page, redirect)? | **Cloudflare Workers free** | 100k requests/day, 10 ms CPU per request, 128 MB |
| 5 | Is it used only while the founder works (agent harnesses, LLM gateway, heavy tools)? | **The laptop**, reached over Tailscale, started just in time | the Mac (thermally limited, ADR 0004: never always-on) |
| 6 | Is it an HTTP service that is idle most of the time? | **The node, behind KEDA HTTP scale-to-zero** | 0 CPU while idle |
| 7 | Must it be always on, and does something else fail without it? | **The node** | see §3 |

Small databases that outgrow the node go to **Neon free** (0.5 GB and 100 CU-hours per project,
scales to zero, suspends at the limit). Rejected because they need a card or have no free tier:
GCP e2-micro and Cloud Run (billing account), AWS/Azure (credits that expire), Fly.io (no free
tier), Render (sleeps; fine for demos only).

### 3. The node, and what is allowed to stay on it

One worker, A1 2 OCPU / 12 GB (`platform/oci/variables.tf`). One node rather than two
1-OCPU nodes because every node pays the DaemonSet overhead again (~0.55 CPU requested:
calico, flannel, SPIRE, CSI, proxymux). One node leaves ~1.25 CPU for workloads; two leave ~0.7
in total, split. Two nodes only buy availability if workloads run two replicas, which the
allowance cannot hold. One node means a node reboot or failure is a full outage.

Always on: Flux, traefik, coredns, KEDA, estate-db (1 instance), NATS. Anything else on the
node justifies itself against rung 6 or 7 and states its CPU and memory **requests** in the PR
that adds it. The sum of requests on the node stays under 1.8 CPU.

### 4. Changes made directly in the cluster land in git in the same step

The founder authorised direct cluster changes (2026-09-26, "going through PR for everything
is wasteful") on one condition: the same change is committed to git in the same step. Flux has
no cluster→git sync, and HelmRelease drift detection is off by default, so a direct `kubectl
scale` persists and git drifts. That is how 86 workloads came to sit at 0 while git said 2. Planned:
gitops-reverser commits live changes to git, and Flux drift detection runs in `warn` or
ignores `/spec/replicas`, so the two do not fight.

### 5. Before any node reboot, resize or drain, calico-node must be Ready on every node

Every pod is Calico-addressed (33/33 on 2026-09-26). On 2026-09-26 calico-node crash-looped on
a hand-set `FELIX_INTERFACEPREFIX="cni|,flannel."`. Existing pods kept their routes; every new pod
got none. A reboot then would have left the whole cluster with no pod network.
Flannel is Oracle's add-on on a Basic cluster; it cannot be removed without the paid Enhanced
tier, and it stays.

## Status: built and operating, stated separately

| Part | State on 2026-09-26 |
|---|---|
| Quota file + `bootstrap --quota` | built (PR #4368); **not in force** until the owner runs it |
| SigNoz off | operating (suspended live and on main, b679856e) |
| One 2/12 node | **not done**: `/tmp/p0-calico.sh` then `/tmp/p0-shrink.sh`, founder-run |
| SigNoz → Grafana Cloud | not started |
| CronJobs → GitHub Actions | not started |
| gitops-reverser + drift `warn` | not started |
| Network policy: 300 per-namespace copies (orphaned; `ns-fences` is wired to no Flux Kustomization) → one Calico baseline tier, staged then enforced, with a probe that must be refused | not started |

Update this table as each row changes; a row is operating only when a production log line
shows it.
