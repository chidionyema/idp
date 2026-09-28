# 2026-09-01. Every estate name lives in one place, and a literal anywhere else is refused

Founder, 2026-09-01, in order: "where are the domains mumchimp-, we need to plan change of domain,
should be seamless and cause least disruption ... let's look at the surface area of changes required
and find ways to shrink"; "this pattern needs to be platform wide, we need to reduce surface area
needed for any migration so the changes are constrained to one or 2 places"; then, on hearing the
store still carried 61 live lines of the zone name: "THAT SHOULD NEVER HAPPEN, P0" / "AND CAN'T EVER
HAPPEN AGAIN." His order: monitoring for any drift, and rejection on the pull request itself.
Recorded as [the one-place ruling](https://github.com/chidionyema/crew/issues/796). Nothing in this record touches the cluster; every change is a branch he merges.

## Where the domain is today (read from the registrar, the DNS plane and the tree, not memory)

- `mumchimp.com` is registered at 123-Reg, expires 2027-06-16; its nameservers are Cloudflare
  (tony/danica). Records are created by external-dns on the cluster from the `HTTPRoute` hostnames
  (Cloudflare token in the vault); certificates by cert-manager from the manifests.
- `deploy/dns/mumchimp.com.zone` in the store is a copy of the live zone kept by
  `dns-drift-drill.yml`, renamed `deploy/dns/estate.zone` so the file name carries no zone.
- The platform already had the one place since [the original one-place decision](https://github.com/chidionyema/crew/issues/269): `clusters/oke/estate-config.yaml`
  `ESTATE_ZONE`, substituted by Flux into 27 idp files (72 uses) and into the store's Flux
  `Kustomization` (`clusters/oke/edge.yaml`, `prospector`). CI reads `vars.ESTATE_ZONE`; compose and
  shell read `${ESTATE_ZONE:?}`; Python reads `os.environ["ESTATE_ZONE"]` behind an explicit override.

## The surface, before and after (bin/estate-zone-gate --root, live lines only)

| repository | before | after |
|---|---|---|
| prospector (the store) | 158 | 0 |
| hermes-v2 | 8 | 0, with `config.yaml` under a marked exemption (three `base_url` lines) |
| crew | 2 | 0 |
| idp | 3 | 0 |

A domain change is now one value (`ESTATE_ZONE`), one repository variable (`vars.ESTATE_ZONE`) and
one environment value on the machines that run compose or the Mac gateway.

## Why it drifted, and the class

The gate existed ([the original decision](https://github.com/chidionyema/crew/issues/269)) but graded only idp `platform/`. A rule that grades one
repository is a wish for the other six — a rule nobody can be stopped by is a wish. The class on the ledger is `gate-landed-after-branch` seen sideways:
the gate landed after the store was written and never widened. So the fix is the existing gate,
widened, reused by every plane that can refuse (the never-twice and guard-every-instance laws),
never a second script.

## What now refuses (all one file, `bin/estate-zone-gate`, one exemption list)

1. **Pull-request rejection.** `bin/pr-report` saves the pull-request diff, runs the gate in `--diff` mode
   over the added lines, and `policy/operating_model.rego` `rule=no_zone_literal_added` refuses
   any hit. The shared operating-model gate runs for idp, crew, hermes-v2 and the store, so one
   rule covers the estate. A repository still carrying old literals is not refused for someone
   else's debt: only what the pull request adds is graded.
2. **Drift monitoring.** `.github/workflows/name-drift.yml` (cron every six hours, plus the estate
   clock on `workflow_dispatch`) mints the App token, lists every repository the App can see,
   clones each at depth 1 and runs the gate `--root`. A red run is a `delivery.failed_runs` row in
   the estate state document, the first thing every session reads.
3. **Local rung.** `bin/idp-ci` proves the gate both ways on tree fixtures and on diff fixtures
   (`tests/fixtures/estate-zone/added-{literal,substituted}.diff`), then grades the repository.
4. **Exemptions are loud.** A file may opt out with `estate-zone-gate: exempt (<why>)` in its
   first three lines; adding that marker is itself a hit, accepted only with the founder's
   `APPROVE: zone-exempt` on the pull request (`input.pr.approvals`).

## The seamless cutover, when he names the new zone

Every step here is reversible until the last one, and none needs a person on the cluster.

1. Add the new zone to Cloudflare (nameservers at the registrar), leave the old one serving.
2. Lower the old zone's TTLs to 60 s a day ahead (Cloudflare proxied records already are).
3. Register the new redirect URIs on every OAuth client (GitHub App, Google, Tailscale) beside the
   old ones, so both hosts sign in during the overlap.
4. Flip `ESTATE_ZONE` in `clusters/oke/estate-config.yaml` on a branch, set `vars.ESTATE_ZONE`, he
   merges: Flux rewrites every `HTTPRoute`, external-dns creates the new records, cert-manager
   issues the new certificates. The store's overlay follows in the same apply.
5. A single `HTTPRoute` on the old hosts answers 301 to the new ones for the overlap.
6. Retire the old zone once the 301 traffic reads zero on the collector.

Rollback at any step before 6 is flipping the one value back.

## What he decides

- `APPROVE: zone-exempt` on the hermes-v2 branch (`config.yaml`), or the follow-up that plumbs
  `ESTATE_ZONE` into the Mac gateway's launchd environment and the hermes-agent pod lands first.
- Set the repository variable `ESTATE_ZONE` once (`gh variable set ESTATE_ZONE --body <zone>` on
  each repository, or organisation-wide after [the organisation-name move](https://github.com/chidionyema/crew/issues/785)); until then the store's
  workflows that read `vars.ESTATE_ZONE` refuse with a plain message rather than guessing.
- The registry (`ghcr.io/chidionyema`) and organisation names follow the same shape in [the naming follow-up](https://github.com/chidionyema/crew/issues/785);
  this record does not widen into them.

## Evidence

- Gate: `bin/estate-zone-gate` (tree, diff and zone modes); BDD `features/gates/estate-zone.feature`,
  five scenarios green; `conftest` refuses `zone_literals` without the approval and passes with it.
- Sweeps: prospector `fix/names-one-place`, hermes-v2 `fix/names-one-place`, crew `fix/names-one-place`,
  each graded `ok zone 0` by the gate before push.
- Board: [this decision's issue](https://github.com/chidionyema/crew/issues/796), [organisation and registry names](https://github.com/chidionyema/crew/issues/785), [the original ruling](https://github.com/chidionyema/crew/issues/269).
