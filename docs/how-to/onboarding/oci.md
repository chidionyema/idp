# Onboarding: Oracle identity (ADR 0004 step 1)

## What it is

`bin/idp-oci-bootstrap` builds the least-privilege identity OpenTofu uses for `platform/oci`:
compartment `estate`, group `estate-operators`, user `estate-tofu`, one policy scoped to that
compartment. The API key pair is generated on this machine; only the public half is registered
with Oracle, the private half goes into the sops vault (`secrets/<env>/OCI_API_PRIVATE_KEY.yaml`)
through `scripts/secret-add` on stdin. No key is downloaded from the console and none is kept on
the founder's admin user.

`bin/idp-oci-login` is the read side: it renders `~/.oci/config` (mode 600) and
`platform/oci/terraform.tfvars` from the vault and proves the identity with
`oci iam region-subscription list`. `bin/idp-verify` calls it as the `oci` drill row.

## Vault entries

| key | written by | secret |
|---|---|---|
| `OCI_REGION`, `OCI_TENANCY_OCID`, `OCI_TENANCY_NAME` | hand, once | no |
| `OCI_COMPARTMENT_OCID`, `OCI_USER_OCID`, `OCI_FINGERPRINT` | bootstrap | no |
| `OCI_API_PRIVATE_KEY` | bootstrap | yes, never printed |

## Why not `oci setup config`

It is interactive, writes the private key unvaulted under `~/.oci`, and registers it on whichever
user is logged in, which is the tenancy owner. A buyer's engineer would flag all three.

## Rotation

`bin/idp-oci-bootstrap --rotate` registers a new key and replaces the vault entry; delete the old
fingerprint in the console afterwards. Oracle allows three keys per user.

## Runbook, as run on 2026-08-25

What the founder does: sign in once in the browser tab that opens. Nothing else.

What the script does, in order, and what each line looks like:

```
login   browser opens once; sign in as the tenancy owner (token lives 1 hour)
iam     compartment estate
iam     group estate-operators
iam     user estate-tofu
iam     policy estate-operators-manage-estate
vault   OCI_API_PRIVATE_KEY written
vault   OCI_FINGERPRINT written
key     registered on estate-tofu, fingerprint 9b:1d:3a...
vault   OCI_USER_OCID written
vault   OCI_COMPARTMENT_OCID written
vault   committed and pushed
done    next: bin/idp-oci-login
```

Then `bin/idp-oci-login` renders `~/.oci/config` and proves the key. A key uploaded seconds
ago answers 401 for several minutes; login retries every 30 s for up to 8 minutes and prints
`wait oci 401 after a fresh key upload` while it does.

Two things broke on the first run and are now guarded:

1. Oracle identity domains refuse a user without a primary email
   (`error.identity.user.primaryEmailNotSpecified`). The vault now carries
   `OCI_SERVICE_USER_EMAIL`; the script refuses to start without it.
2. The script printed `iam user estate-tofu` with an empty OCID and went on to upload the key
   to user "". `ensure` now fails on an empty OCID and the run stops there.

If the token expires mid-run, re-run the script: it reuses a live session, otherwise opens
the browser again, and every IAM step is idempotent.

## Cluster, as run on 2026-08-25

Four things broke on the first `platform/oci` apply and are now in the config:

1. `Node shape is unavailable in subnet availability domain(s)` -- A1 exists only in AD-1 and
   AD-2 of uk-london-1, so the worker pool carries `placement_ads = [1, 2]` (#64).
2. No aarch64 OKE image for the default Kubernetes version; `kubernetes_version` is v1.35.2.
3. `control_plane_is_public = true` alone gives a private endpoint. The module also needs
   `assign_public_ip_to_control_plane = true` (#66). Flipping it on an existing cluster is an
   in-place change, but the module's kube-config data source asks for the public endpoint
   before it exists, so the plan errors. Apply the cluster first, then everything:
   `tofu apply -target=module.oke.module.cluster`, then a normal plan and apply.
4. The public endpoint admitted nobody: the module's `control_plane_allowed_cidrs` defaults
   to `[]`, and `idp-flux-bootstrap` timed out on port 6443 (#67). `idp-oci-login` now measures
   this machine's egress IP and writes it as a /32 into `terraform.tfvars`; on a new network,
   re-run login and apply.

Each apply is behind the spend guard; Always Free sizes are the founder's sign-off (R14).

## The storefront (mumchimp.com), as wired on 2026-08-25

What runs: `prospector-store-api` (.NET, SQLite on a 10 GiB block volume) and `prospector-store-web`
(Next.js). The engine is not on the cluster: its core is rewritten next sprint.

Where each piece lives:

| Piece | File | Owner |
|---|---|---|
| Edge charts (Traefik, cert-manager, external-dns, Kyverno) | `platform/edge/` | idp |
| Flux chain: CRDs -> edge -> prospector-platform -> prospector | `clusters/oke/edge.yaml` | idp |
| Namespace, `ghcr-pull`, API secret files (OCI Vault via ExternalSecret) | `platform/prospector/`, `bin/idp-flux-bootstrap` | idp |
| Deployments, Gateway, HTTPRoutes, ClusterIssuer, policies | `prospector/deploy/k8s/overlays/oke` | prospector |

The API reads its secrets as files under `/var/run/secrets/prospector`, one file per key, from
Secret `prospector-store-api-env`, which External Secrets writes from the OCI Vault secret
`prospector-store-api-env` (one JSON object, one key per file). To change one: update that vault
secret (`oci vault secret update-base64`); the ExternalSecret refreshes it within an hour, or
`kubectl -n prospector annotate externalsecret prospector-store-api-env force-sync=$(date +%s)` now.

DNS. The zone is on Cloudflare (123-reg holds only the registration). external-dns writes A
records for the HTTPRoute hostnames from the Traefik load balancer address, with a TXT registry and
`upsert-only`. It never edits a record it did not create, so the cutover from Fly is one manual
step: delete the `www` and `api` CNAMEs and the apex A record in the Cloudflare dashboard, and
external-dns creates the three within a minute. The token it needs is Secret `cloudflare-api-token`
in namespace `edge`, key `CF_API_TOKEN`, scope Edit zone DNS on mumchimp.com; until it exists the
external-dns pod stays Pending and `flux get hr -n edge` says so.

Data. The last Fly volume is `~/backups/fly-teardown-2026-08-25/prospector-store-api.data.tgz`
(not in git). Restore with the API scaled to 0 (`kubectl -n prospector scale deploy prospector-store-api --replicas=0`), with a pod that mounts
the claim. The pod spec is the Kyverno-compliant one (seccomp, probes, non-root, read-only root); a bare busybox is refused.
The `rm -f` matters: if the API ever started against an empty claim it left a `store.db-wal`, and SQLite replays a
stale WAL over a restored `store.db`, which reads as an empty catalogue (2026-08-25: `/catalog` returned `[]` with 78
listed packs on disk). The md5 must match `md5 -q` of `store.db` inside the tarball.

```
kubectl -n prospector run restore --image=docker.io/library/busybox:1.37 --restart=Never \
  --overrides='{"spec":{"securityContext":{"runAsNonRoot":true,"runAsUser":10001,"runAsGroup":10001,"fsGroup":10001,"seccompProfile":{"type":"RuntimeDefault"}},"containers":[{"name":"r","image":"docker.io/library/busybox:1.37","command":["sleep","900"],"securityContext":{"allowPrivilegeEscalation":false,"readOnlyRootFilesystem":true,"capabilities":{"drop":["ALL"]},"seccompProfile":{"type":"RuntimeDefault"}},"resources":{"requests":{"cpu":"10m","memory":"32Mi"},"limits":{"cpu":"200m","memory":"128Mi"}},"volumeMounts":[{"name":"d","mountPath":"/data"},{"name":"t","mountPath":"/tmp"}],"livenessProbe":{"exec":{"command":["true"]},"periodSeconds":10},"readinessProbe":{"exec":{"command":["true"]},"periodSeconds":10}}],"volumes":[{"name":"d","persistentVolumeClaim":{"claimName":"prospector-store-api-data"}},{"name":"t","emptyDir":{}}]}}'
kubectl -n prospector wait --for=condition=Ready pod/restore --timeout=120s
kubectl -n prospector cp ~/backups/fly-teardown-2026-08-25/prospector-store-api.data.tgz restore:/tmp/d.tgz
kubectl -n prospector exec restore -- sh -c 'rm -f /data/store.db /data/store.db-wal /data/store.db-shm && mkdir -p /tmp/x && tar xzf /tmp/d.tgz -C /tmp/x && cp -a /tmp/x/data/. /data/ && ls -la /data && md5sum /data/store.db'
kubectl -n prospector delete pod restore
```

Not held anywhere after the Fly teardown, so off until re-issued: the Mailjet key pair (mail from
the store) and the Google OAuth client (sign in with Google). The JWT signing key was minted fresh
on 2026-08-25, so every session issued on Fly is invalid; users sign in again.
