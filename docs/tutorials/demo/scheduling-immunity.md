# Demo: scheduling immunity (crew#539)

On 2026-08-27 the oke-check surge swapped the node, the survivor was CPU-starved, telemetry-coverage,
cluster-state and the gateway sat Pending on `Insufficient cpu`, langfuse answered 503 for nine
minutes and nothing paged. Founder: "how come monitoring and alerts and traces didn't detect this,
what happened to autoscaling". The answer is three Kubernetes-native primitives and a guard, for $0.

## 1. Balloon pods: headroom the scheduler hands over in milliseconds

`platform/scheduling/balloon.yaml` runs two `pause` pods at 300m each (15 % of the 4 OCPU node)
under PriorityClass `balloon` (value −1). A real pod that needs CPU preempts a balloon instead of
waiting for a VM.

```
$ kubectl get priorityclass balloon infrastructure-critical
NAME                      VALUE     GLOBAL-DEFAULT   AGE
balloon                   -1        false            …
infrastructure-critical   1000000   false            …
$ kubectl get deploy -n scheduling balloon
NAME      READY   UP-TO-DATE   AVAILABLE
balloon   2/2     2            2
```

Drill: schedule any pod requesting 600m on the full node → it runs, `kubectl get pod -n scheduling`
shows one balloon `Pending` (the preemption event names it). Until CP4 (OKE Cluster Autoscaler)
lands, that Pending balloon is a standing reservation, not a node boot.

## 2. The radio room floods last

`infrastructure-critical` is on exactly six workloads: langfuse-web, langfuse-worker,
mcp/agentgateway, hermes-agent-gateway, telemetry-coverage, cluster-state.

```
$ kubectl get deploy,cronjob -A -o custom-columns='NS:.metadata.namespace,NAME:.metadata.name,PRIO:.spec.template.spec.priorityClassName,CRON:.spec.jobTemplate.spec.template.spec.priorityClassName' | grep -c infrastructure-critical
6
```

Under CPU pressure Kubernetes evicts runners and app pods to seat these; you may lose a background
job, you never lose the receipt or the route.

## 3. The dead-man's switch lives outside the blast radius

`.github/workflows/ping.yml` probes every portal surface from a GitHub runner every five minutes
(GET, the same list oke-check's founder-links job derives) and posts to the Telegram bot the estate
already runs on any failure, then again on recovery.

```
$ gh workflow run ping.yml -R chidionyema/idp
$ gh run list -R chidionyema/idp --workflow ping.yml --limit 1
```

Drill: `kubectl scale deploy -n observability langfuse-web --replicas 0` → 🔴 in Telegram inside
ten minutes → scale back → 🟢 on the next tick.

## 4. The guard (LAW 45)

`platform/scheduling/require-priority-class.yaml`: a Kyverno ClusterPolicy. Any of the six that
drops the class is refused at admission (Enforce); every other platform workload without a class is
a PolicyReport row (Audit, flipped to Enforce after a zero-violation pass, the crew#341 way).

```
$ kubectl get policyreport -A | grep require-priority-class
```

Proof of all four: `bin/idp-kyverno-render platform/scheduling` renders every workload the way helm-controller will and judges it with the cluster's own policies, `require-priority-class.yaml` included.

## 5. The healing loops (CP6/CP7)

`platform/healing/`: the Descheduler (CronJob, every 10 min, never touches the radio room) rebalances
after a node swap; K8sGPT explains a Pending wave through the estate's own LiteLLM.

```
$ kubectl get cronjob -n healing descheduler
$ kubectl get results -n healing
```
