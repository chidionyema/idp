# The inventory is read from the control planes, never from git

Tracked on [the inventory ticket](https://github.com/chidionyema/crew/issues/740).

**Decision.** One job, `bin/idp-inventory`, asks every plane the estate runs on what it holds —
the cloud tenancy's discovery search, a full dump of the cluster, GitHub, Cloudflare and Tailscale
through Steampipe, the Mac's launchd and hooks — and grades every thing it finds against what git
declares. Four verdicts: MANAGED, DRIFTED, ORPHAN, GHOST. A plane that could not be read is UNKNOWN
on the table, never a green zero.

**Why.** On 2026-08-31 the sessions could not say whether LiteLLM was in the estate. The estate
already had three inventories (`bin/catalog-platform` from the Flux manifests, the Mac asset
inventory, `bin/idp-catalogue-drift` on hostnames) and all three read git or a receipt of git.
Anything made by hand, by a controller, or by a console was invisible by construction. The founder
had asked for this at the start of the cloud migration and insisted it must never be out of sync.

**Options considered.**
1. Extend `bin/catalog-platform` to more manifests — still git; rejected, it cannot see an orphan.
2. Per-plane shell loops over each vendor CLI — rejected under the never-reinvent-the-wheel rule; Steampipe already models
   every one of these APIs as SQL, and one query file per plane is what a reviewer can read.
3. Steampipe for every plane including OCI — the OCI plugin authenticates from an API-key profile,
   while the runner holds a session token; `bin/idp-estate-audit` already reads the tenancy with the
   structured search the blueprint names, so OCI rides on that and Steampipe takes the three SaaS planes.

**Consequences.** Audit mode first: the run reports and never fails on a red row until every row
is adopted (imported into Terraform) or killed. The next pull request (E1) makes the nightly run a required
check with `--strict`. The read-only cloud principal for this job is minted in Terraform in the
E2 pull request with the other agent-scope work; until then it runs on the oke-check identity, which is the
one the founder's blueprint allows for the first run.

**Architecture laws.** Inventory every asset; never reinvent a wheel a mature tool already turns (Steampipe, not a script per API); coverage is proved by querying the state store, never by scanning files; secure by default (read-only, no root in the file; credentials come from the vault under the one-root rule). The rule numbers are in the pull request body.
