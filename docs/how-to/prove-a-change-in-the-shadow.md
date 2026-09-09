# Prove a change in the shadow before it touches production

**Who this is for:** anyone changing a workload's config, limits, image or manifest that Flux
will later apply on the estate — i.e. almost every `platform/`, `clusters/` or image change.
**What it saves:** proving a change in the *real* cluster by mistake. A pull request that breaks
a pod's readiness, replica count or probes is caught here, in an environment that is destroyed
afterwards, before it ever reaches a file Flux reconciles.

## The idea

The zero-trust framework (`docs/decisions/0025-*.md`, the W2 part of
`docs/policy/agent-infra-safety-spec.md`) stops an agent from holding write on production by
confining it to a *shadow dimension*: an **ephemeral vcluster** that carries a workload as it
would run, where the change is applied and asserted to still converge. Only then may the change
meet the merge gate. The shadow never is production, never persists, and holds no live secret.

The estate's shadow is the sandbox vcluster (`platform/sandbox/vcluster`, the one app the vcluster
seeds plus anything a proof applies on top), driven by `bin/idp-shadow`. The industry pattern this
implements is the **ephemeral preview/vcluster-per-PR** one: spin up, prove, destroy. Shared
staging drifts within days and costs a fortune; an ephemeral vcluster is destroyed after the run,
so nothing accumulates:

- vCluster CI/CD pattern: environments are created when a PR starts and **destroyed when it
  merges/closes** (vcluster.com production guide, GitHub Actions preview-environments docs).
- Cost studies: 200 on-demand clusters cost ~$11 each/month against $16k/month always-on staging
  (Zop.dev); Deloitte reported ~89% faster provisioning and ~500 QA hours/yr saved by many
  vcluster instances on one host.

The spec (W2.1) makes the ephemerality load-bearing: `bin/idp-shadow down` *"destroys it; the
existing sweeper covers a leak."* A **leak** is named as the failure — the sandbox runs on a
1-hour hold (`platform/sandbox/vcluster/helmrelease.yaml`: *"persistence off: a one-hour sandbox
keeps no state; a pod restart resets it, by design"*), and `bin/idp-sandbox-sweep` force-pushes
the launch branch back to idle when the hold expires.

## Once (only when you run proofs by hand)

The sandbox vcluster lives on the estate cluster under a 1-hour hold. It is started by the
`demo-sandbox` workflow and torn down by the same mechanism on a schedule:

```
gh workflow run demo-sandbox.yml --ref main -f action=launch -f hold=1h   # or hold=4h
# ... prove ...
gh workflow run demo-sandbox.yml --ref main -f action=end                # tear it down
```

The vcluster API is reached by port-forwarding its Service to `127.0.0.1:8443` and extracting its
kubeconfig (`bin/idp-shadow` does this for you):

```
kubectl -n demo-sandbox port-forward svc/demo-sandbox 8443:443 --address 127.0.0.1 &
idp-shadow up <workload> platform/.../deployment.yaml
idp-shadow verify <workload>
idp-shadow down <workload>
```

## Every proof — the three commands

`bin/idp-shadow` (`up`/`verify`/`down`) drives the sandbox vcluster:

```
# apply the workload's manifests into the shadow; secrets are reshaped to shells by
# bin/idp-shadow-sync so no live value reaches the shadow (W2.1, LAW 21)
idp-shadow up <workload> /path/to/deployment.yaml /path/to/configmap.yaml

# apply the branch and assert the workload still converges from the vcluster's LIVE state:
#   Ready, available == required replicas, probes green (W2.2)
idp-shadow verify <workload>                # exit 0 = converged (ok ... converged)
                                            # exit 1 = the change broke it (FAIL ... names why)
                                            # exit 2 = BLIND, no sandbox to prove against

# remove the workload from the shadow so nothing leaks (W2.1)
idp-shadow down <workload>
```

The graders it drives are merged gates with their own fixture proofs:
`bin/idp-shadow-sync` (`shadow-sync` rule), `bin/idp-shadow-verify` (`shadow-verify`),
`bin/idp-convergence-proof` (`convergence-proof` rule).

## The fence — what the shadow will and will not run

Understanding this saves the whole class of "why is my applied pod Pending?":

1. **The shadow syncs only host-legal pods.** A synced pod is admitted on the host like any other
   deployment (first real launch, 2026-09-06): it must carry `runAsNonRoot`, a
   `seccompProfile: RuntimeDefault`, a read-only root (`securityContext.readOnlyRootFilesystem` /
   `capabilities.drop: [ALL]`) and real probes. A bare nginx pod is refused once synced; a
   host-legal one reaches Ready 1/1. `bin/idp-shadow-sync` reshapes *Secrets* only — it does not
   add security context — so proofs pass a host-admissible manifest (the estate's rendered
   deployments already are).

2. **Namespace sync is fixed at the vcluster's first deploy.** What a vcluster mirrors onto which
   host namespace is decided when it is created; vCluster documents that advanced/namespace sync
   *cannot be changed after deploy* (vcluster.com, sync/to-host/namespaces). That is why a
   workload applied into a *provisioned* shadow namespace runs, and one placed where the vcluster
   was never told to sync stays Pending. `bin/idp-shadow` applies into the synced `demo`
   namespace, which is why proofs converge (and why the earlier "the demo cannot run applied
   workloads" read was wrong — the pod's spec, not the sync, was the cause).

3. **It is ephemeral and never holds a secret.** A pod restart resets it (`persistence off`);
   the sweeper ends it after the hold; `idp-shadow down` removes the workload. If a proof's
   virtual cluster implodes, the corrective action is to delete it and try again — the host
   cluster's etcd and admission pipeline are never touched (decision 0025, Engine 1).

## Done means a quoted run

A claim that a change "passed the shadow" is only true with the verifier's own output quoted:

```
ok      shadow-verify  demo/<workload> converged: ready, at replicas, probes + tests green   (exit 0)
FAIL    shadow-verify  demo/<workload>   # a change that breaks it, naming why           (exit 1)
```

That green + red quoted output is the spec's W2.2 "Done when" — the shadow run IS the proof, not a
synthetic fixture. Anything else is an unproven change waiting for the merge gate.
