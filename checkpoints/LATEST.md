# RESUME HERE

## Live, being fixed right now
`nodesoftware-operator` Flux Kustomization has never applied (namespace empty, 156m old,
`post build failed ... envsubst error: '.dockerconfigjson' var name is invalid`), and
`gvisor-runtime` has been blocked behind it its whole life. Found because #2387/#2391 removed
the drift noise that was hiding it. Three stacked causes, all measured:
- `clusters/oke/platform.yaml:1544` substituteFrom a `kubernetes.io/dockerconfigjson` Secret;
  its one key `.dockerconfigjson` is an invalid envsubst variable name, so post-build aborts.
- `platform/nodesoftware-operator/deployment.yaml` pins bare `IMAGE_TAG`, no `$`, which envsubst
  never touches; the comment claiming it is "the same mechanism as cyrus, hermes-agent" is false
  (those use `$imagepolicy` markers written into git by Flux image automation).
- `ghcr.io/chidionyema/nodesoftware-operator` is a 404; no workflow builds it; no ImagePolicy.
Fix in worktree `$SCRATCH/wt-nso`, branch `fix/nodesoftware-operator-never-applied`.

## Merged this session
#2384 kyverno policy-fetch retries -> BLIND. #2387 Flux alert multi-line anchor (D3 layer 1).
#2391 four NetworkPolicies had two Flux owners (D3 layer 2). Fence watch after #2391: 4/4
present at every 20s poll for 30 min, owner flipped cleanly to ns-fences, no gap.

## Open PRs of mine
#2415 pipeverdict header names 3 paths that are 0/0/0 tracked files; stacked on
`rules/pipeverdict-row` (#2390, idp-96). Comment only, both cases still grade.

## Not mine, do not touch
observability/signoz HelmRelease Failed + ClickHouse -- idp-96 is on it (#2388, #2413).
`.github/workflows/estate-bootstrap-preflight.yml`, a backstage template skeleton and
`bin/idp-vault-put` are staged in the primary checkout by a third session.

## RESUME HERE (2026-09-08, WJ.1 device-agnostic identity)

PR #2456 open (branch wj1/the-agent-identity-is-minted-by-the-broker-not-the-founder,
worktree $SCRATCH/wt-id): the broker's POST /identity door. Glass-break, needs founder review.

Now building the client half in $SCRATCH/wt-kube, branched off that branch:
bin/idp-kube asks the door for a token AND for the API server URL + CA, so a device with only
JIT_AGENT_KEY needs no `oci` CLI and no founder principal. Measured 2026-09-08: the in-cluster
ServiceAccount CA and the kubeconfig's certificate-authority-data are the same certificate
(sha256 53:DA:73:45:...:79:2C), so the broker can hand out its own mount.
