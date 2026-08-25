# What a cluster costs

Written 2026-08-25 for the founder's question: *"lets get a real cost estinate of what we need to
run a cluster, cheapest possible lets be shrewd and clever"*, and its follow-ups: *"research wide
cheapest provider managed vs self provisioing"* and *"not just for today because we are expanding
but need to be tight with costs"*.

Every number here was either measured on this machine today or fetched from the vendor's own
pricing page today, and the source is next to it. Where a figure could not be sourced it says so
rather than guessing.

## The answer

**Run OKE Basic on Oracle's Always Free tier. It costs $0.00/month and it fits what we run today
with room to spare. Budget $14.60/month for the first top-up and about $94/month at three times
today's size.**

The single reason it wins is not the free VMs -- other people give away VMs. It is that **the
managed Kubernetes control plane is free**, and a self-managed control plane is the most expensive
thing in every alternative: k3s's own documentation measures a server node at 1,428-1,606 MB of RAM
before it runs any of our code, and an honest highly-available one needs three of them. On a 12 GB
free allowance, self-managing costs 13% of everything we have, to run Kubernetes rather than to run
the product.

**The risk, in two sentences, because one would be dishonest.** Oracle's free ARM capacity is
genuinely scarce -- "out of host capacity" is a well-documented, unacknowledged, longstanding
problem. And Oracle's own worker-node documentation neither confirms nor forbids running managed
OKE nodes on the free A1 shape, so step one is a check that costs an afternoon, with a known
fallback (k3s on the same free VMs) that is worse but certain and changes nothing else.

**What I am not doing:** provisioning anything. Ruling R14 says no paid infrastructure without your
sign-off and ruling R23 says local green first, then prepare, then move. This is the "prepare" step
and it cost nothing to produce.
## What we actually need, measured, not guessed

Every number below came from one command run on 2026-08-25 against the estate as it runs today.

```
$ docker stats --no-stream            # 16 containers
steady-state RSS total: 4220 MiB = 4.12 GiB
sum of CPU:             151.2% of one core = 1.51 cores
$ docker system df
Images        40   30.39 GB
Local Volumes 24    3.61 GB      <- the only data that must survive a node
Build Cache  169   15.44 GB      <- stays on the laptop, never ships
```

The workload is 4.12 GB of RAM and one and a half cores. The persistent data is 3.61 GB. The
30.39 GB of images is a per-node disk cost, not a storage cost, and it shrinks on a cluster
because nodes pull only what they run.

Add the control plane. k3s's own resource profiling page measures a server node at 1428-1606 MB
with no workload at all (docs.k3s.io/reference/resource-profiling, fetched 2026-08-25) -- three
times the 2 GB "minimum" the requirements page states, which is a floor and not a working size.

So the honest sizing, today:

| | measured | with control plane and headroom |
|---|---|---|
| RAM | 4.12 GB | **8 GB** |
| vCPU | 1.51 | **4** |
| persistent storage | 3.61 GB | **100 GB** |
| node disk for images | 30.39 GB | included in the above |
## Oracle, priced properly

Oracle is already the recorded target (ADR 0004, DECIDED 2026-08-24). Nobody had put a number on
it. Here it is, from Oracle's own list rates -- $0.01 per OCPU-hour, $0.0015 per GB-hour, $0.0255
per GB-month of block storage (oracle.com/cloud/price-list, fetched 2026-08-24) -- with the
arithmetic done in a script rather than in my head:

| | OCPU | RAM | disk | **on top of Always Free** | at full list price |
|---|---|---|---|---|---|
| today | 2 | 12 GB | 200 GB | **$0.00** | $32.84 |
| reference (4 vCPU / 8 GB) | 4 | 8 GB | 100 GB | **$14.60** | $40.51 |
| 3x growth | 12 | 24 GB | 500 GB | **$93.79** | $126.63 |
| 10x growth | 40 | 80 GB | 2 TB | **$397.76** | $430.60 |

Three things in that table are worth more than the numbers.

**The free allowance was halved on 2026-06-15**, from 4 OCPU / 24 GB to 2 OCPU / 12 GB, with no
announcement (docs.oracle.com Always Free Resources, fetched 2026-08-24; reported by InfoQ
2026-07-03). Oracle began terminating over-limit instances on 2026-08-18. Anything sized against
the old 4/24 figure is sized against a number that no longer exists.

**Oracle's own two pages disagree about what we would get.** The price list still says a *paid*
tenancy gets 3,000 OCPU-hours and 18,000 GB-hours free; the Always Free page says 1,500 and 9,000.
That is the difference between 4 OCPU and 2. If we upgrade to Pay-As-You-Go the higher figure may
apply, and support has reportedly given inconsistent answers. **This is worth about $30/month and
one email to Oracle to settle before we size anything.**

**OKE Basic is a free managed control plane, and that is the whole reason to be here.** Basic
clusters cost $0.00/hour; Enhanced is $0.10/hour, which is $73.00/month for an SLA we do not need
yet (oracle.com/cloud/cloud-native/kubernetes-engine/pricing). The free control plane is not a
rounding error: k3s's own resource profiling measures a self-managed server node at 1,428-1,606 MB
before any workload runs. On a 12 GB allowance, self-managing the control plane spends 13% of
everything we have on running Kubernetes rather than running the product. **OKE Basic hands that
back.**

### What else Always Free includes, verified on the page itself

Fetched from docs.oracle.com's Always Free Resources page on 2026-08-25, quoting its own wording:

- **One Flexible Load Balancer** -- but "minimum and maximum bandwidth set to 10 Mbps". That is the
  single hardest constraint in this whole document and it is not a price, it is a ceiling. 10 Mbps
  is fine for the estate's own traffic and thin for a buyer demo. The answer if it bites is a
  paid-shape load balancer, not a different cloud.
- **200 GB of combined boot and block volume storage**, with a 47 GB minimum boot volume per
  instance -- so the 30.39 GB of images we measured fits, but only just, on one node.
- **10 TB per month of outbound data.**
- **20 GB of Object Storage** plus 50,000 API requests per month, on an Always-Free-only account.

### The thing I could not confirm, and it matters

The recommendation rests on OKE Basic worker nodes being Always Free A1 shapes. Oracle's own
"Supported Images and Shapes for Worker Nodes" page (docs.oracle.com, fetched 2026-08-25) **does
not say that they are.** It names `Pod.Standard.A1.Flex` for *virtual* nodes and lists what is not
supported for managed nodes -- dedicated VM hosts, micro VM shapes, HPC bare metal, burstable
flexible shapes. `VM.Standard.A1.Flex` appears in neither list. It adds only: "you might be unable
to select some shapes in your particular tenancy due to service limits and compartment quotas".

So the honest position is: not forbidden, not confirmed. Working community OpenTofu/Terraform
modules exist that build exactly this (github.com/ystory/terraform-oci-always-free-oke), which is
evidence it works, and evidence is not a vendor guarantee.

Two things follow. First, **virtual nodes are not the free answer** -- they are $0.015 per node per
hour, about $11/month each, so an OKE deployment that quietly lands on virtual nodes stops being
free. Second, **the fallback is already known**: k3s on the same Always Free A1 VMs. It costs
1,428-1,606 MB of the 12 GB to self-manage the control plane and it is a worse answer, but it is a
worse answer that definitely works, and it does not change the cloud, the region, the images or the
GitOps.

This is the one question in this document that a single capacity-and-feasibility check answers, and
it is already step 1 of ADR 0004.

### The two risks, named

**Capacity.** "Out of host capacity" for A1 shapes is a well-documented, longstanding problem, bad
enough that people write retry bots for it (github.com/hitrov/oci-arm-host-capacity). No official
Oracle statement acknowledges it. Multi-availability-domain regions are reported as easier;
uk-london-1 is single-AD. This is the risk that could cost us weeks, and it is why ADR 0004 step 1
is a capacity check before a single line of OpenTofu.

**Idle reclamation.** Oracle reclaims Always Free instances where, over a 7-day period, CPU at the
95th percentile is under 20%, network is under 20%, **and** memory is under 20% (that last clause
applies to A1 shapes specifically). All three must be true, and measured we are clear on two of
them: 1.51 cores against 2 OCPU is 75%, and 4.12 GB against 12 GB is 34%. Worth knowing it exists before someone "optimises" the cluster into being
reclaimed.
## ARM is the cheapest single decision available, and we are one step from it

Every cheap option on the table -- Oracle's Always Free A1, Hetzner's CAX line -- is ARM. ARM is
where the free and near-free capacity is. So the question that decides whether any of this is real
is: does our stack run on it?

I checked rather than assumed. Every third-party image the estate runs, queried against its own
registry manifest on 2026-08-25:

```
clickhouse/clickhouse-server:25.12               amd64,arm64
postgres:17-alpine                               386,amd64,arm,arm64,ppc64le,riscv64,s390x
redis:7                                          386,amd64,arm,arm64,ppc64le
caddy:2.10-alpine                                amd64,arm,arm64,ppc64le,riscv64,s390x
otel/opentelemetry-collector-contrib:0.159.0     386,amd64,arm,arm64,ppc64le,riscv64,s390x
docker.langfuse.com/langfuse/langfuse:4          amd64,arm64
ghcr.io/berriai/litellm-database:v1.98.0         amd64,arm64
ghcr.io/agentgateway/agentgateway:v1.4.1         amd64,arm64
ghcr.io/github/github-mcp-server:v1.10.1         amd64,arm64
cgr.dev/chainguard/minio                         amd64,arm64
```

**Ten out of ten.** Not one bought-in component blocks the move.

The four that do are ours:

```
$ docker image inspect <ours> --format '{{.Os}}/{{.Architecture}}'
prospector-engine:local                     linux/amd64
prospector-store-api:local                  linux/amd64
prospector-store-web:local                  linux/amd64
idp/estate-mcp:datasette-...                linux/amd64
```

That is the entire ARM migration: **four of our own images need to be built for two architectures
instead of one.** Ruling R24 already requires exactly this, and `bin/multiarch-gate` already
enforces it -- it just reports `0 findings across 1 root(s)` because it has only ever been pointed
at `idp`, and the images above are built in `prospector`. Pointing the existing gate at the other
roots is the work, and it is a day, not a project.

This is worth saying plainly because it inverts the usual advice. The reason to be shrewd about ARM
is not ideology, it is that ARM is where the free tier lives -- and we are four Dockerfiles away
from being able to use it.
## Egress, the line item that decides this

Egress is where cheap hosting stops being cheap, so it is worth measuring rather than assuming.

```
$ netstat -ib | awk '$1 ~ /^en[0-9]/ && $3 ~ /Link/ {ib+=$7; ob+=$10} END {...}'
in: 13.00 GB   out: 4.24 GB   since boot
$ uptime
up 8:29
```

4.24 GB out in 8 hours 29 minutes is roughly 12 GB a day, about 360 GB a month. That is an
**upper bound on the estate**, not a measurement of it: the figure includes the founder's own
browser, every Claude API call, and every git push made from this laptop. Real cluster egress
will be a fraction of it.

Against that, the allowances:

| | included egress | cost of the first TB over |
|---|---|---|
| Oracle Always Free | **10 TB/month** | $0.0085/GB = $8.70 |
| AWS / GCP | 100 GB/month account-wide | $0.09/GB = ~$92 |

At 360 GB a month we are inside every free allowance on the market, including AWS's. Egress is
therefore **not** what makes this decision today -- but it is what makes it at 10x, which is why
the table below prices 20 TB as well as 1 TB.
## The line items nobody puts in the estimate

A cluster bill is never just the machine. These are the four that turn a £5 plan into a £40 one,
priced from the vendors' own pages on 2026-08-25.

**Backups.** Our persistent data is 3.61 GB today; price it at 100 GB so growth is covered.

| | store 100 GB/month | restore 100 GB once |
|---|---|---|
| Backblaze B2 | $0.70 | $0.00 (free egress up to 3x stored) |
| Cloudflare R2 | $1.50 | **$0.00, at any volume** |
| Hetzner Storage Box BX11 | €3.20 flat, up to 1 TB | $0.00, unlimited traffic |
| AWS S3 Standard | $2.30 | $0.00 *only if* nothing else used the account's shared 100 GB/month egress pool -- otherwise ~$9.00 |

The S3 row is the trap. Its "free" egress is a single 100 GB monthly pool shared across the whole
AWS account, so one disaster-recovery drill can silently make every other transfer that month
billable. R2 is the only one where a restore is free at any size, and a backup you are financially
discouraged from testing is not a backup.

**Load balancer.** A managed one is €7.49/month at Hetzner (raised from €5.39 in April 2026) and
$12/month per node at DigitalOcean. The free path is real: k3s ships ServiceLB, and MetalLB or
kube-vip with a single floating IP (€3.00/month at Hetzner) does the same job. On Oracle, the
Always Free tier includes a load balancer.

**IPv4.** Increasingly its own line item: €0.50/month at Hetzner Cloud, €1.70 on their dedicated
servers, and $0.005/hour -- about $3.60/month, $43.20/year -- for *every* public IPv4 at AWS,
including one per EKS node.

**Certificates.** cert-manager and Let's Encrypt are genuinely free, with one rate limit that will
bite us specifically: **5 certificates per identical hostname set per 7 days**. A cluster that gets
torn down and rebuilt against the same hostname -- which is exactly what the rebuild-from-git drill
does -- burns that in an afternoon. The fix is the Let's Encrypt staging endpoint for drills, and it
costs nothing as long as somebody knows before the drill rather than after.

## What self-managing actually costs beyond the invoice

The honest counterweight to "k3s on a cheap VPS is £4":

- **A single-server k3s cluster has no control-plane redundancy.** API server, scheduler and the
  SQLite datastore all die with the node. HA needs **three server nodes minimum, and an odd
  number** -- four buys no extra fault tolerance over three (docs.k3s.io/datastore/ha-embedded).
  So the honest self-managed HA cluster is 3 nodes, not 1, and that is where the price triples.
- **etcd is brutally sensitive to disk fsync latency**, which is precisely what a cheap
  shared-disk VPS does not guarantee. The documented failure mode is control-plane nodes flapping
  Ready/NotReady, and there is a k3s issue where one misbehaving node corrupted the datastore for
  the whole cluster (k3s-io/k3s#5576).
- A published, itemised build of a 3-master/3-worker HA k3s cluster on Hetzner came to
  **€59.92/month before VAT, €72.50 with it** -- not the "a few euros a node" figure people quote,
  because the load balancers and six public IPs are on the bill too.

That is the number that matters: the moment self-managed Kubernetes is done *properly*, it costs
more than the managed control plane we can have for nothing.
## Not just today: where the price bends

You said we are expanding, so the number that matters is not this month's bill, it is the shape of
the curve. There are three bends in it and only one of them is the compute price.

**Bend 1, at roughly 2x: we leave the free tier.** Today's 4.12 GB fits inside 12 GB with the
control plane free. Double the workload and it still fits. Triple it and it does not -- and the
first top-up is small: **$14.60/month** buys two more OCPUs. This bend is gentle and it is the one
everybody worries about.

**Bend 2, at 3x: the free tier stops being the cheap answer.** At 12 OCPU / 24 GB / 500 GB, Oracle
on top of the free allowance is **$93.79/month**. That is the point where a plain ARM VM elsewhere,
running the same OKE-shaped workloads, is worth pricing properly -- and where the honest comparison
must include the three control-plane nodes that a self-managed HA cluster needs, not one. A
published, itemised 3-master/3-worker HA k3s build on Hetzner came to **€59.92/month before VAT,
€72.50 with it**, load balancers and six public IPs included. So the two are within noise of each
other at 3x, and Oracle wins on operational load rather than price.

**Bend 3, the one that actually bites: egress.** Measured, the whole laptop pushes about 360 GB a
month, and that upper bound includes your browser. Every option is free at that volume. But the
per-TB price after the allowance differs by a factor of ten between vendors, and on AWS the free
allowance is 100 GB *account-wide* at $0.09/GB after -- so a single 1 TB month is about $92 there
versus $8.70 on Oracle. If the product grows into serving real traffic, this line, not the CPU
line, becomes the bill.

**The bend that is not about money at all:** Oracle's free load balancer is fixed at 10 Mbps. That
is enough for the estate and thin for a buyer demo, and the fix is a paid load balancer shape
rather than a change of cloud. Worth knowing now rather than the week someone important is watching.

### What "tight with costs" should mean here

- **Do not buy an SLA we cannot use.** OKE Enhanced is $73.00/month for a 99.95% guarantee on a
  cluster whose workloads currently run on one laptop. Basic is $0.00 and identical Kubernetes.
- **Do not buy a managed load balancer while a floating IP costs €3.00** and k3s ships ServiceLB.
- **Do not pay for backup egress.** Cloudflare R2 charges nothing to download at any volume; AWS
  charges enough that people quietly stop testing restores. A backup you are discouraged from
  testing is not a backup.
- **Settle the 2-versus-4 OCPU question with one email.** Oracle's own two pages disagree about
  whether a Pay-As-You-Go tenancy keeps the old 4 OCPU / 24 GB allowance. It is worth about
  $30/month and it is a question, not a project.
