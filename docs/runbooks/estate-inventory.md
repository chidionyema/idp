# Runbook: The estate inventory run is red or blind

| Symptom on the run | What it means | What to do |
|---|---|---|
| `BLIND inventory oci` | the discovery search did not answer (session token, region) | rerun; if it repeats, `bin/idp-oke-rebuild --check` row `api-answers` names the door |
| `BLIND inventory kubernetes` | no cluster answered kubectl through `bin/idp-cloud cluster kubeconfig` | the cluster receipt (`state/cluster`) says whether the API is reachable |
| `BLIND inventory cloudflare: vault entry cloudflare-api-token unread` | the bootstrapper has not minted the token | an `oke-check` apply runs `bin/idp-bootstrap-cloudflare`; needs the one root (the one-root rule) |
| `BLIND inventory tailscale` | the operator OAuth client in the vault did not mint an access token | `bin/idp-bootstrap-tailscale` on the next apply re-mints it |
| `GHOST` rows on the oci plane | a state entry the search does not index (vault secrets, IAM) | list the type in `bin/idp-estate-audit lists()`; until then the row is a known false GHOST |
| `ORPHAN` rows | live, declared nowhere: adopt (`tofu import` in a pull request) or kill (founder's word) | one pull request per plane, imports proved by a clean `tofu plan` |

Every row above is read from the run log; none of them is a guess about the world.
