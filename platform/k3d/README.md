# The local cluster

A single-node Kubernetes cluster on this laptop, for £0. It exists so that the
manifests, admission policies and restore drills that will one day run on a
managed cluster can be proved before anyone pays for one.

`crew/docs/STANDARDS.md`, Substrate row, is what asks for it: the exit from
launchd is managed Kubernetes, and until that proof is finished everything is
proved locally on k3d, on free tiers, and on GitHub-hosted runners.

## Use it

```
make cluster-up       # create it, or say it is already there
make cluster-status   # nodes, pods, and what it costs the machine right now
make cluster-down     # delete it; nothing survives, by design
```

`cluster-up` prints the one line you need afterwards:

```
export KUBECONFIG=$(k3d kubeconfig write estate)
```

The API server listens on `127.0.0.1:6445` and nowhere else. k3d's default is to
publish it on `0.0.0.0` at a port the kernel picks, and on 2026-08-24 that is
exactly what this cluster did for 40 minutes: `docker port` read
`6443/tcp -> 0.0.0.0:53145`. Founder ruling R20 says the gateway is the only
process on this estate that binds a non-loopback address. `make cluster-up` now
ends by running `bin/bind-audit`, which reads back every listener on the machine
and fails on anything that is not on a written allow-list, so the same mistake
cannot be made quietly again.

```
```

## What is deliberately not in it

Traefik, servicelb and metrics-server are all switched off, and each one is
switched off for a reason written next to it in `estate.yaml`. If you need one,
turn it on there and say in the commit what you are proving with it — the file
is the record, not your shell history.

## What it cannot prove

Anything that needs more than one real machine. Node failure, rolling a node
pool, cross-zone traffic, a real load balancer, storage that outlives the host.
One Docker VM is one kernel and one disk, so a green run here is evidence about
the manifest, never about the cluster underneath it.

It also holds nothing. Delete it and it is gone, including any PersistentVolume
you created, because the storage is the VM's disk. Nothing that matters should
ever be in here.

## If it will not start

The cluster lives inside colima's Docker VM. That VM has 4 CPUs and 8 GB, and
it is shared with everything else running in Docker. `make cluster-status`
prints what is free. If memory is short, stop containers you are not using —
**do not restart colima**, which restarts every container on the machine.
