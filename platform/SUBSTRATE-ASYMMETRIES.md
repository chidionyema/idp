# Substrate asymmetries: where dev is not prod

Founder directive, 2026-08-24: *"This laptop is a dev substrate. It must replicate
prod (k3s on Oracle Free Tier) as closely as mechanically possible. Any deviation
is drift; drift is a bug."*

This file is the register of the deviations we know about. A row exists so that the
next session starts from here rather than rediscovering it. Every row carries the
command that reads the property back, so no row has to be believed.

Measured 2026-08-24 on `chidis-MacBook-Pro` unless a row says otherwise.

---

## 1. CPU architecture — the largest one, and it is not in any plan yet

| | value | command |
|---|---|---|
| macOS host | `x86_64` | `uname -m` |
| colima VM | `x86_64 / linux` | `docker info --format '{{.Architecture}} / {{.OSType}}'` |
| k3s node | `amd64`, K3s v1.35.5+k3s1 | `kubectl get node -o jsonpath='{..architecture}'` |
| Oracle always-free compute | **arm64** (Ampere A1, `VM.Standard.A1.Flex`) | vendor documentation — **not measured here, no prod node exists yet** |

Dev is x86_64 from the laptop down to the kubelet. The target is ARM. Every image
this estate builds locally is single-arch amd64 and will not run there.

This is the row most likely to be found by someone else first. Settle it the moment
a prod node exists:

```
kubectl --context prod get node -o jsonpath='{.items[0].status.nodeInfo.architecture}'
```

If it returns `arm64`, every `docker build` in this estate needs `--platform
linux/amd64,linux/arm64` and a registry that holds a manifest list. Nothing has been
changed for this yet — recorded, not fixed.

## 2. `network.hostAddresses` voids Docker's loopback bindings

**Left at `false`. The exposure below is open, on purpose, by founder ruling R22
of 2026-08-24: "forgetthe drilfor noww, too risky".** He withdrew his own earlier
instruction to set it after seeing what applying it costs. Do not set it, do not
restart colima, do not edit `~/.colima/default/colima.yaml`. Reopening this is his
call alone.

```
grep -n 'hostAddresses' ~/.colima/default/colima.yaml
```

With `false`, lima cannot forward to a specific host IP. `docker run -p
127.0.0.1:80:80` is honoured inside the VM as `0.0.0.0` and republished on the Mac
as `*`, so **every "loopback-only" container port is on whatever network the laptop
is joined to**. Measured: `catalog/ports.yaml` declared `bind: 127.0.0.1` for 80 and
443, `docker port k3d-estate-serverlb` agreed, and `lsof` showed `limactl *:80` and
`limactl *:443`. Dialled from inside the colima VM — a genuinely different host —
`http://192.168.0.192/` accepted the TCP connection. The macOS Application Firewall
global state is `0`, disabled, so nothing was dropping it.

It was set to `true` earlier on 2026-08-24 and **reverted from backup when R22
landed**, verified byte-identical against the pre-edit copy, with colima never
restarted (`ps -o etime -p 76436` unbroken across the revert). An unapplied edit is
not harmless here: it makes the next `colima start` by anyone, for any reason,
silently perform the drill that was cancelled.

This asymmetry has no equivalent in prod: k3s on a Linux host binds what it is told
to bind. It is a property of the dev substrate only, which is why the fix — if it is
ever reinstated — lives in `~/.colima/`, never in a manifest.

`bin/bind-audit` and `bin/port-gate --live` both FAIL on 80 and 443, from two
independent readings, and **no allow-list row has been added for them**. That is
deliberate. An accepted risk and a closed finding are not the same thing, and an
exemption would record this as intended rather than as open. The gates are supposed
to stay red here.

If it is ever reinstated, this is the check that proves it, and Docker's own
reported bind address does not count:

```
lsof -nP -iTCP -sTCP:LISTEN | grep -E ':(80|443) '
bin/bind-audit && bin/port-gate --live
```

## 3. macOS does not synthesise `*.localhost`

```
$ ping -c1 -W1 hello.localhost   ->  does not resolve
```

RFC 6761 reserves `.localhost`; Linux with systemd-resolved answers the whole tree,
macOS answers only the bare name. So `hello.localhost` and `backstage.localhost`
need real `/etc/hosts` lines here and none in prod, where the names are DNS records.

`sudo -n` fails on this machine — a password is required — so this is a genuine
founder-once task. It is asked **once, for every hostname the estate will ever
need**, generated from the Backstage catalog rather than typed, not once per
service.

## 4. `host.docker.internal` exists in compose and does not exist in Kubernetes

`llm/litellm.yml` pins it via `extra_hosts: ["host.docker.internal:host-gateway"]`,
which is the portable compose spelling — it works on colima, Docker Desktop and
Linux alike, so it is not a macOS conditional and does not violate the
no-environment-hacks rule. But it has no meaning inside a cluster. When LiteLLM and
Ollama move onto k3s, `http://host.docker.internal:11434` becomes a Service DNS
name, and that rewrite is part of the migration, not an afterthought.

Affected today: `llm/config.yaml:57`, `llm/litellm.yml:64,68`.

## 5. `lsof` truncates the COMMAND column to nine characters

`ControlCenter` reads as `ControlCe`. Any audit that keys on a process name is
matching a truncated string, and on this machine the name is a lie anyway: colima
republishes every container port under `limactl`. Both port instruments now key on
the **port** and consult `catalog/ports.yaml`, never on the process name.

```
lsof -nP -iTCP -sTCP:LISTEN | awk 'NR>1{print length($1), $1}' | sort -rn | head -1
```

## 6. Timings measured here are not prod timings

```
$ pmset -g therm
CPU_Speed_Limit = 60          # 39 earlier the same day
$ uptime
load averages: 24.67 22.83 31.32
```

The laptop thermally throttles under sustained load. The Traefik helm-install job
took 8m26s on this substrate. No wall-clock measured here transfers to prod, and any
number quoted from here carries the `CPU_Speed_Limit` reading at the time or it is
not evidence.

## 7. k3d is not k3s

Dev runs k3s **inside Docker** (k3d v5, `platform/k3d/estate.yaml`); prod runs k3s on
the host. The Kubernetes manifests under `platform/k8s/` are identical for both and
must stay that way — no colima flags, no macOS conditionals, no DNS workarounds. The
asymmetry is confined to cluster *creation*: `k3d cluster create` here, a k3s install
there. `--disable=metrics-server` is a memory decision for this laptop and does not
belong in a prod install.

---

## 8. The dev substrate is smaller than prod, and it is already full

**This is the one that broke something.** Measured 2026-08-24 23:43, while the k3s
apiserver was unreachable:

```
sysctl -n vm.swapusage        # total = 8192.00M  used = 7730.75M  free = 461.25M
vm_stat | head -2             # Pageins 45,944,929
pmset -g therm                # CPU_Speed_Limit = 39
uptime                        # load averages: 25.68, 19.75, 23.53
docker ps -q | wc -l          # 21
grep -E '^(cpu|memory):' ~/.colima/default/colima.yaml   # cpu: 4  memory: 8
sysctl -n hw.memsize          # 16 GB
```

**Do not quote that as a percentage.** macOS grows and shrinks the swap file, so
`used/total` divides by a moving denominator. Measured four minutes apart by two
sessions: total read 8192.00M and then 7168.00M, so the same conditions produce
different percentages while the machine is recovering. **The absolute free figure is
the honest one** — 461.25M free, then 1166.25M four minutes later — and the
direction it moves matters more than either reading.

A 4-CPU, 8GB VM on a 16GB host was running 21 containers —
langfuse (7), prospector (4), mcp (3), k3d (3), litellm (2), backstage (2) — and a
Kubernetes cluster had been added to it that day.

The failure it produced looked nothing like its cause. `kubectl` hung with
`TLS handshake timeout`, and the first reading, `certificate signed by unknown
authority`, pointed at a stale kubeconfig CA. Neither was the fault:

```
docker exec k3d-estate-server-0 netstat -lnt   # tcp 39 0 :::6443 LISTEN
docker inspect k3d-estate-server-0             # restarts=0 oomkilled=false
docker exec k3d-estate-server-0 kubectl --request-timeout=30s get ns   # nothing in 45s
```

39 connections in the accept queue. The container was healthy and had never
restarted; the process inside it could not keep up. k3s stores its state in kine on
sqlite, and the k3s log showed `Slow SQL ... duration=5.961745724s`, etcd
`DeadlineExceeded`, and `apiserver was unable to write a JSON response: http:
Handler timeout`. sqlite cannot commit on a host that is swapping, so handlers time
out, so the queue fills, so every client hangs. **`kubectl` failed identically from
inside the server container, which is what ruled out the load balancer** — one
reading from the host and one from inside the node, disagreeing with the kubeconfig
theory in the same direction.

Prod is not more spacious, and this was written wrongly here first. **Oracle halved
the Always Free Ampere A1 allowance from 4 OCPU / 24GB to 2 OCPU / 12GB, effective
2026-06-15**, with no blog post and no customer notification; it was found when
people's instances stopped. Oracle's own fine print adds that a terminated resource
"may not be possible to recreate ... above the updated Always Free limit", so any
grandfathering that exists does not survive a teardown — which is what a migration
is.

So the destination is **smaller in CPU than the dev VM already is**: colima runs
`cpu: 4`, always-free A1 now gives 2 OCPU. It is 12GB against colima's 8GB, and that
12GB has to cover whatever runs the control plane too.

**A capacity problem here is not evidence of one there, and a timing measured here
is not a prod timing (see 6)** — but neither is prod a way out of one. Check the
current published limit before sizing anything against it; this number moved once
without warning and the estate believed the old one for a day.

Two things follow, and they are the reason this section exists rather than a note in
an incident log:

- **Nothing measured on this substrate while it is swapping is a reading.** Check
  `vm.swapusage` and `CPU_Speed_Limit` before believing any latency, any timeout,
  any "the cluster is broken". Three separate symptoms above were all one cause.
- **Adding a service here is a capacity decision, not just a config change.** The
  cluster was added to a VM that was already at its limit. That is not a bug to
  debug; it is a thing that was decided without measuring first. It was the last
  straw and not the load: a substrate that cannot hold the compose estate plus one
  small cluster had no headroom before the cluster arrived.
- **Take a second reading before calling it a fire.** The numbers above were the
  peak. Four minutes later, unprompted, free swap had gone 461M to 1166M and load
  25.68 to 12.74. The capacity argument held on its own; "about to fall over" would
  not have.

### The recovery path is `stop`, never `delete`

```
k3d cluster stop estate     # keeps the containerd image store
k3d cluster start estate    # brings it back with those images
```

`make cluster-up` deletes and recreates, which throws the node's image store away.
That is normally fine and is not fine here: with registry egress dead (see 2), the
SPIRE and CSI images exist on this machine only because they were pulled on the host
and pushed in with `k3d image import`. A delete cannot pull them back. **The
rebuild-from-git drill is only safe while egress works.**

A second consequence of the same dead egress, measured independently: a `docker
buildx` sat at 0.0% CPU for 6.5 minutes doing a registry manifest check on a base
image that was already in the local cache. **With egress dead, any build without
`--pull=false` hangs before it does any work**, and it hangs silently, burning
nothing, which is why it reads as a slow build rather than a network failure.

## What is not in this file

Nothing about the substrate belongs only in a session's memory. If you find a
property of this machine that makes a result here differ from a result there, add a
row with its command before you move on.
