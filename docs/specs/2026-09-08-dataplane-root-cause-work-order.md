# Dataplane root cause and work order (2026-09-08)

Measured from the founder Mac between 11:50Z and 12:40Z with the admin kubeconfig. Every fact
carries the command that produced it. Nothing here was applied; this is the map for the agent
that repairs it. Freeze crew#739 and the dump in R0 both bind before any step in the second half.

## 1. What is true right now

| # | Fact | Command |
|---|------|---------|
| F1 | Every new pod gets a Calico address: `/etc/cni/net.d` on both nodes holds only `10-calico.conflist`. The flannel DaemonSet is gone from kube-system. | `kubectl exec -n kube-system <calico-node> -- ls /host/etc/cni/net.d`; `kubectl get ds -n kube-system` |
| F2 | 92 pods still hold flannel addresses (`10.244.1.128/25` on 10.0.159.197, `10.244.2.0/25` on 10.0.148.221); 84 hold Calico addresses (`10.244.3.0/24`, `10.244.117.0/24`). A flannel-addressed pod keeps its address until it restarts. | `kubectl get pods -A -o jsonpath='{range .items[*]}{.status.podIP}{"\n"}{end}'` |
| F3 | Flannel leftovers on both nodes with no daemon maintaining them: `flannel.1` (UP), `cni0` (DOWN, `linkdown` route), 6 `FLANNEL-*` iptables rules, `flannel.alpha.coreos.com/*` node annotations, and the cross-node route `10.244.2.0/25 via 10.244.2.0 dev flannel.1 onlink`. | `ip -br link; ip route; iptables-save \| grep FLANNEL` inside calico-node |
| F4 | Cilium leftovers on both nodes from the 2026-08-28 chained install that was reverted the same day (commits b7067005, cde04bed): `cilium_host`/`cilium_net` veths carrying `10.0.0.153/32` and `10.0.1.218/32` (addresses inside the VCN range), 34 `CILIUM_*` nft rules including `CILIUM_PRE_raw ... -j CT --notrack`, 10 `cilium.io` CRDs. | `ip -br addr; iptables-save \| grep -ci cilium; kubectl get crd \| grep cilium` |
| F5 | kube-proxy is iptables mode and healthy on paper: 411 `KUBE-SVC` and 506 `KUBE-SEP` rules per node, DNAT rules for the source-controller service present, legacy tables empty, `FORWARD` policy ACCEPT. | `iptables-save \| grep -c KUBE-SVC; iptables-legacy-save \| grep -c '^-A'` |
| F6 | Calico runs iptables mode (`bpfEnabled=false`), VXLAN, block size /24 with a `blackhole` route per own block, 3,632 and 4,272 `cali-*` rules. Installed by the raw operatorless manifest (commit 905c653e, 2026-09-06). | `kubectl get felixconfiguration default -o yaml; ip route \| grep blackhole` |
| F7 | OKE's own record says the migration failed: both nodes carry `last-migration-failure=get_kubesvc_failure` and `oci.oraclecloud.com/vcn-native-ip-cni=false`. OKE still believes this is a flannel cluster. | `kubectl get nodes -o json` (labels and annotations) |
| F8 | Empirical, from the LiteLLM pod (Calico address, node 10.0.159.197): apiserver ClusterIP `10.96.0.1:443` OK in 0.0s; source-controller ClusterIP `10.96.202.29:80` timeout; source-controller pod address `10.244.117.185:9090` (other node) timeout; kube-dns `10.96.0.10:53` TCP timeout. The `llm` namespace carries a default-deny fence, so this proves the fence drops, not yet the overlay. | python socket probe via `kubectl exec -n llm litellm-... -- python3 -c ...` |
| F9 | The fences: 293 NetworkPolicies, 47 default-deny. Flannel enforced none of them for 276 hours; Calico enforces all of them. The cutover made every fence live at once with allow-lists that had never dropped a packet. The apiserver reaches webhooks from three source addresses (10.0.0.11, the node address, the peer node's VXLAN tunnel address); PR #2549 fixed the generator for that. | `kubectl get netpol -A --no-headers \| wc -l` |
| F10 | Kyverno: every pod-security policy is `Enforce` with zero namespace exclusions, so `kubectl debug node/...` is refused. The only shells on a node are the already-privileged `calico-node` and `kube-proxy` pods; `kubectl exec` into them works. The calico-node image has `grep`, `ip`, `iptables-save`, `iptables-legacy-save`; it has no `awk`, `cut`, `tr`, `wc`, `head`. | `kubectl get cpol -o json`; `kubectl debug node/<n>` (refused) |
| F11 | Cluster Postgres has no backup (crew#713); `prospector/store-db-backup` is suspended. Data that is not in git: 21 PVCs of 50Gi each (estate-db x2, temporal, backstage, dagster, litellm, hindsight, guacamole, healthchecks, signoz, langfuse, prometheus, nats, jit ledger, workforce, hermes). | `kubectl get pvc -A; kubectl get cronjobs -A` |
| F12 | Consequence chain: Flux 26 True / 50 False / 4 Unknown of 80, 48 pods not ready, `oauth2-proxy` in CrashLoopBackOff (14 restarts) so no surface can be signed into, external-secrets cannot sync, and the cost fix #2534 and the fence fix #2549 are on main and cannot reach the cluster. | `kubectl get kustomizations -A; kubectl get pods -n identity` |

## 2. The root cause, as a class

Three CNIs were applied to one two-node production cluster in twelve days, and none was rehearsed
on a throwaway cluster first:

1. 2026-08-28: Cilium chained over flannel (crew#539 CP12), took the pod network down, reverted
   the same day in git only. The nodes were never cleaned (F4).
2. 2026-09-06: Calico installed as a full overlay beside flannel by raw manifest (F6), on a
   managed service whose own record still says flannel (F7).
3. 2026-09-08: a descheduler profile (#2501) evicted 78 pods onto the Calico dataplane because
   "every new pod has a Calico address" was taken as proof that the path worked (F2, F8). It was
   stopped by #2543.

Each step declared a state before the path that proves it had been measured. The ephemeral cluster
stream (`platform/k3d`, `platform/staging`, `platform/sandbox`) is the capability built to rehearse
exactly this and it was not used for any of the three. It is therefore the first stream to bring
up after the fire, not one to park.

## 3. What is still unknown, and the one command that settles each

Run these from an unfenced namespace. `guacamole` has `bash` and no NetworkPolicy.

- U1, does the Calico VXLAN carry packets between the nodes? Read `ip -s link show vxlan.calico`
  inside calico-node on both nodes, probe `10.244.117.185:9090` from a guacamole pod on
  10.0.159.197 with `timeout 4 bash -c 'exec 3<>/dev/tcp/10.244.117.185/9090'`, read again.
  TX rises on the sender and RX does not rise on the receiver: UDP 4789 is blocked between the
  workers in the VCN security list (OKE opens flannel's 8472 by default, not Calico's 4789).
  RX rises and the connect still fails: node-side, go to U2.
- U2, does a same-node ClusterIP work from an unfenced pod? Pick a service whose one endpoint
  is on the pod's own node and connect to its ClusterIP. Failure with F5 true points at the
  `CILIUM_PRE_raw` NOTRACK rules (a NOTRACKed packet can never be DNATed) or at Calico's
  `cali-rpf-skip`; removing the Cilium chains (R1) is the test.
- U3, does the fence DNS exception allow TCP 53 as well as UDP 53? `grep -n 53 bin/idp-ns-fence-gen`.
  F8 shows TCP 53 timing out from a fenced pod.

## 4. The work order, in order, each with its done command

- R0 safety, before anything changes: `kubectl exec -n estate-db estate-1 -- pg_dumpall` and the
  same for `temporal-db-0`, `backstage/postgres-0`, `dagster/postgresql-0`, `llm/litellm-db-0`,
  `hindsight/hindsight-db-0`, `guacamole/guacamole-db-0`, `healthchecks/healthchecks-db-0`, to a
  location off the cluster. Done: eight dump files with a byte size above zero, listed.
- R1 eradicate Cilium from both nodes: delete the 10 CRDs; inside each node flush and delete every
  `CILIUM_*` chain in raw, mangle, nat and filter; `ip link del cilium_host`. Done:
  `iptables-save | grep -ci cilium` is 0 on both nodes and `ip -br link | grep -c cilium` is 0.
- R2 settle U1. If 4789 is blocked, add one worker-to-worker UDP 4789 ingress rule to the worker
  security list in `platform/oci` and apply it through the road that owns it (decision 0026).
  Done: the probe in U1 connects and RX rises on the receiver.
- R3 eradicate flannel from both nodes: `ip link del flannel.1; ip link del cni0`, delete the
  `FLANNEL-FWD` and `FLANNEL-POSTRTG` chains, remove the `flannel.alpha.coreos.com/*` node
  annotations. Then restart every flannel-addressed pod, stateless first, StatefulSets last, one
  namespace at a time. Done: `kubectl get pods -A -o jsonpath=...podIP` shows zero addresses in
  `10.244.1.0/24` or `10.244.2.0/24`.
- R4 fences to log-only until the cluster is green: suspend the `ns-fences` Kustomization and
  delete the 47 default-deny policies from the cluster (the files stay in git). Done:
  `kubectl get kustomizations -A` shows 80 True. Then re-enable one namespace at a time with an
  allow-list written from Calico's denied-packet log, and only after the fix in U3.
- R5 the decision the founder owns: OKE documents Calico as a policy engine on top of flannel,
  not as a replacement overlay; F7 shows OKE still expects flannel, so a node replacement or an
  OKE upgrade would reinstall it and repeat this outage. The one answer is Calico policy-only
  over OKE's flannel, which is the documented pattern and removes the second dataplane for good.
  Risk: the migration back is one more dataplane change, so it is rehearsed on the ephemeral
  cluster first (section 2). Done: `kubectl get nodes` shows no `last-migration-failure` label
  and one CNI conflist per node.
- R6 the guard so it is the last time: a rule row that refuses any change under `platform/calico`,
  `platform/cni` or `platform/ns-fences` whose pull request does not carry a green run of the
  same change on the ephemeral cluster.

## 5. Where every other stream stands

Nothing in flight is lost. All 1,735 real commits of the last fourteen days are on main or on a
branch; the cluster cannot run them until R0 to R4 are done. The measured state per stream is in
the founder's reply of 2026-09-08 12:15Z (session e5728c64), and the parking there was a sequence,
not a value judgement: every stream resumes the moment Flux reads 80 True.

---

## Session progress log (2026-09-08, post-12:40Z) — appended by the repair session

### R0 - safety dumps: DONE
Two data homes, off-cluster, verified headers/tails:
- `estate-1` pg_dumpall (all 15 app DBs): /Users/chidionyema/backups/estate-20260908-125420/estate-cluster-1.pg_dumpall.sql (623,231,683 bytes)
- `temporal-db-0` pg_dumpall: same dir temporal-db-0.pg_dumpall.sql (527,470 bytes)
NOTE: the work order's original "8 separate per-namespace postgres pods" list was a misreading; the real homes are the estate CloudNativePG cluster (15 DBs incl. dagster/litellm/backstage/hindsight/guacamole/hc) + the temporal StatefulSet. No per-namespace postgres pods exist.

### R1 - eradicate Cilium: DONE (both nodes)
- 4 tables (raw/mangle/filter/nat): removed 11 `cilium-feeder` base-chain jumps + flushed/deleted all CILIUM_* chains, both nodes.
- Deleted cilium_host veths (cilium_net auto-gone). Cluster-wide 10 Cilium CRDs deleted.
- VERIFIED: `iptables-save | grep -ci cilium` = 0 both nodes; `ip -br link | grep cilium` = 0.
- Measured effect: Flux reconciles recovered from 26 True (baseline) toward green; cross-node pod TCP + apiserver ClusterIP reachable from an unfenced pod (K=OK). U1/U2 dataplane blockers RESOLVED by R1: the Cilium NOTRACK/raw interference was the cross-node/ClusterIP killer, NOT a VCN 4789 block. **R2 (open 4789) is therefore NOT needed** vs work-order hypothesis.

### R3/R4/R5/R6 - NOT started (parked, tracked): 
R3 (flannel eradication) shows no measured payoff now cluster works; R4 (delete 47 fences) would lower security mid-recovery - advise against doing blind. R5 founder decision: corrected against Oracle docs - "Calico policy-only over flannel" is NOT Oracle-supported (causes network issues); live cluster is Calico-overlay which Oracle DOES allow. VCN-native (npn) is cluster-creation-only, requires rebuild - too big for this fire. R6 guard standing.
DECISION OWNER: founder chose Option 1 (stabilize live Calico overlay), Option 2 (VCN-native) tracked as later follow-on.

### BONUS FIX - oauth2-proxy sign-in blocker (F12 "no surface can be signed into")
Root cause: estate-seed `put_raw` stores `gen urlsafe32` output (python print = trailing \n) verbatim -> vault cookie_secret held "...Mo\n" -> ESO rendered `cookie_secret = "...Mo\n"` = invalid TOML "basic strings cannot have new lines" -> oauth2-proxy CrashLoop -> no sign-in on any surface.
- Immediate: re-stored vault oauth2-proxy-cookie-secret trimmed (43 bytes, no \n); forced ESO resync; rollout-restarted oauth2-proxy.
- VERIFIED: rendered cfg byte-clean (closing quote straight after value); oauth2-proxy 1/1 Running, serving /ready /ping 200.
- Durable (git, branch fix/oauth2-cookie-secret-newline, NOT yet committed/merged): bin/idp-estate-seed `put_raw` now `gen "$g" | tr -d '\n' > "$f"`; syntax-verified. Open the PR to merge.

## Appended 2026-09-08 ~17:40Z — hindsight residual (post router/config fixes)

The estate-platform causes of the hindsight crash are FIXED and merged+applied:
- #2586 in-cluster router URL + router key mounted as a file (no env; kyverno-clean).
- #2605 verify against the minimax lane (gemini lane was RateLimitError).
- #2607 spec.upgrade.force: true (a Failed deployment otherwise stalls the helm upgrade).
Empirically: `model=minimax base_url=http://litellm.llm.svc.cluster.local:4000/v1`,
`Verifying connection: openai/minimax` -> `Connection verified: openai/minimax` (SUCCEEDS now).

REMAINING (hindsight application-internal, NOT estate-platform): after LLM-connection-verify the
FastAPI lifespan blocks before "Application startup complete" and the pod is killed (exit 137,
reason Error = liveness/probe on a start that never binds 8888; logs end at Connection verified).
The startup now reaches: DB ok, MCP lifespans ok, bge-small-en embed init, cross-encoder
ms-marco-MiniLM-L-6-v2 reranker, minimax verified — then hangs. Suspect: a pgvector/first-boot
step or the model-cache warm after the deployment was deleted, OR the known crew#573 slow-start /
2Gi memory headroom. Needs hindsight-application or model-cache warming, not more router fixes.
Owner: hindsight app thread / operator. gateway (otto) stays red until hindsight is 1/1 Ready
because the memory-store backfill pages hindsight's /memories API.

## Appended ~18:00Z — cyrus (crew#834) restart-loop + webhook leads RESOLVED

Root cause (verified live + git): cyrus-github is an ESO GithubAccessToken external-secret on a
10m refresh; ESO mints a new GitHub App token and rewrites the mounted secret every 10 minutes.
cyrus reads the token DYNAMICALLY via GIT_ASKPASS (entrypoint.sh cats the file per git call), so a
rotation needs no restart. But reloader.stakater.com/auto was drifted true on the deployment, so
every mint rolled the pod (643 revisions / 11 ReplicaSets / 90 min), wiping the /repo and
/worktrees emptyDir and killing any run longer than ~10 min. => "cyrus never does anything".
The Linear-webhook public-door timeout is the same cause downstream (route/service/port 3456 are
correct end-to-end); a mid-roll pod isn't Ready so Traefik refuses the delivery.
Fix: pin reloader.stakater.com/auto: "false" on the cyrus pod template; PR #2614 merged+applied.
Applied state: template annotation false; revision stable at 645 (no roll on the token mint);
single active ReplicaSet; pod 1/1 Ready through the observation window.

## Appended ~20:00Z — VERIFIED recovery convergence (empirical, not claimed)

- hindsight: kustomization True; pod 1/1 Ready, restarts=0, started=true. After #2586 (in-cluster
  router + file secret), #2605 (minimax lane), #2607 (force helm upgrade), #2616 (boot offline —
  the fence never answered huggingface.co). The offline-boot fix (#2616) was the last piece.
- otto-gateway: kustomization True. Its health gate was red on the Failed otto-memory-store-6
  one-shot backfill, which pages hindsight's /memories API. hindsight was down all session so the
  backfill could never complete. Now hindsight is Ready: deleted the stale Failed job, Flux
  recreated it, and it COMPLETED (status.succeeded=1 of 1). Empirical proof hindsight serves its
  memory API and otto-gateway is green.
- Flux: 76 True of ~80 (up from 64 during the trans-regress image-roll storm, and from the
  session's hard-down start).
- Remaining reds (known, independent): nodesoftware-operator (+gvisor dependency, pre-existing
  image bug), temporal (stale edge dep), commerce/prospector (reconciling/cert tail).
