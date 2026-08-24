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

**Must be `true`.** Set 2026-08-24. **Applies at the next `colima start`, which is
not run as a side effect of other work** — restarting colima restarts every
container on this machine, which is what caused the load-255 incident.

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

This asymmetry has no equivalent in prod: k3s on a Linux host binds what it is told
to bind. It is a property of the dev substrate only, which is why the fix lives in
`~/.colima/`, never in a manifest.

**After the restart**, this is the check that proves it, and Docker's own reported
bind address does not count:

```
lsof -nP -iTCP -sTCP:LISTEN | grep -E ':(80|443) '
bin/bind-audit && bin/port-gate --live
```

Until then `bin/bind-audit` and `bin/port-gate --live` both FAIL on 80 and 443, from
two independent readings, and no allow-list row has been added for them. An
exemption would record the exposure as intended rather than as open.

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

## What is not in this file

Nothing about the substrate belongs only in a session's memory. If you find a
property of this machine that makes a result here differ from a result there, add a
row with its command before you move on.
