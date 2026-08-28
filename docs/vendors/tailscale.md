# Tailscale — capability sheet (crew#590)

Measured 2026-08-28 from the admin console's New credential wizard (console.tailscale.com/admin/settings/trust-credentials/add) and tailscale.com/docs/reference/trust-credentials. Founder, same night: "you have to first know, learn, research everything, the full capabilities". One row per capability the vendor documents; USED / NOT USED with the why / CANDIDATE with a ticket. Re-measure when older than 30 days.

## Trust credentials

| Kind | What it is | Status |
|---|---|---|
| OAuth client | long-lived client id + secret, scoped; created in the console OR by `POST /api/v2/tailnet/-/keys` with `keyType: client` (vendor SDK `KeysResource.CreateOAuthClient`, measured 2026-08-28 — an earlier line here said console-only; that was measured from the console, not the API) | USED: `tailscale-operator`, minted through the API by `bin/idp-bootstrap-tailscale` from the one-scope seed `tailscale-seed` |
| Federated identity | trust an OIDC issuer; a short-lived token is exchanged for a Tailscale access token, no stored secret; created by the same endpoint with `keyType: federated` | CANDIDATE crew#589 (GitHub Actions and the cluster both issue OIDC) |
| API access token | personal, 90-day max | NOT USED: a person's credential, never a machine's |

## Scopes, as the console lists them

| Tab | Scope | Grants | Status |
|---|---|---|---|
| General | dns | MagicDNS, nameservers, split DNS | NOT USED: DNS is Cloudflare from git |
| General | policy_file | read/write the tailnet ACL | USED write: `bin/idp-tailscale-policy` |
| General | users | roles, approval, suspension, deletion | NOT USED: never a machine's |
| General | tailnets | create tailnets | NOT USED |
| General | services | Tailscale Services (VIP services) | CANDIDATE: internal doors (signoz, langfuse) off the public edge |
| General | oauth_apps | third-party OAuth applications | NOT USED |
| Devices | devices:core | list/authorise/remove machines, tags | USED write: the Kubernetes operator |
| Devices | devices:posture_attributes | posture values for ACL conditions | NOT USED |
| Devices | devices:routes | subnet routes, exit nodes | CANDIDATE: cluster CIDR as a subnet route (crew#66) |
| Devices | device_invites | invite external devices | NOT USED |
| Keys | auth_keys | mint tagged auth keys | USED write, tag:k8s: the operator joins pods |
| Keys | api_access_tokens | mint API tokens | NOT USED |
| Keys | oauth_keys | create, read, modify, delete OAuth credentials | USED write, by the seed only: `tailscale-seed` carries this scope and nothing else, and mints `tailscale-operator` |
| Keys | federated_keys | federated identities | CANDIDATE crew#589 |
| Keys | webhooks | event webhooks | CANDIDATE: device events into the collector (LAW 50) |
| Logging | log_streaming | configuration + network flow logs to a SIEM | CANDIDATE: stream to SigNoz (LAW 50) |
| Settings | feature settings | tailnet feature toggles | NOT USED |

Rule: a scope with no consumer is attack surface; three writes and one tag is the whole operator client, and one scope is the whole seed.

## Product capabilities not scoped above

| Capability | Status |
|---|---|
| Kubernetes operator (ingress, egress, proxy groups, connector) | USED: `clusters/oke` HelmRelease `tailscale` |
| Tailscale SSH | NOT USED: no human shells into nodes (LAW 31) |
| Serve / Funnel | NOT USED: the public edge is Traefik + Cloudflare |
| Taildrop, Mullvad exit nodes | NOT USED |
| tsnet (embed a node in a Go program) | NOT USED |
| Auth keys via API `POST /api/v2/tailnet/-/keys` | USED by the operator |
