# 0018. Superset is the dashboard, because it takes the gateway's word

- Status: PROPOSED. Only the founder moves this to accepted (his standing ruling of 2026-08-24).
- Date: 2026-09-02
- Deciders: founder — his word, verbatim: "SWAP. We are pulling Metabase out by the roots."
- Affects: the boardroom dashboards, the observability area of the cluster, the shared edge Gateway, the vault

## The problem, measured on 2026-09-02

The estate has one login (decisions 0003 and 0007): single sign-on at the gateway, no password held for a
person, no login page inside an app. Metabase's free edition cannot take part. It has no
trusted-header door (the community request has been open unbuilt since 2020,
https://discourse.metabase.com/t/11475) and sells single sign-on in its paid tiers. The
workaround built on the abandoned branch was Google sign-in inside Metabase: a second identity
provider, a cloud-console step for the founder, and a login living in an app — each one a thing
the estate's identity policy forbids. The founder, verbatim: "I traded a 5-second password
prompt for a 15-minute nightmare navigating the Google Cloud Console."

## The decision

Metabase is evicted. Apache Superset (Helm chart 0.22.4, app 6.1.0) replaces it behind the same
gateway. Superset's account layer, Flask-AppBuilder, ships remote-user trust for free: a
twelve-line middleware copies the gateway's X-Auth-Request-Email header — a value the gateway
overwrites with the login proxy's verdict on every request — into REMOTE_USER, and
Superset creates the account from it on first sight. No login page, no second provider, no
console step, no licence fee.

The word also set a standard that now applies estate-wide: a surface that cannot accept the
gateway's word for who is signed in, at no cost, is replaced — never the identity model.
Founder, verbatim: "if a tool cannot support it for free, the tool gets evicted."

## Consequences

- platform/observability runs the Superset chart install plus its own
Postgres; every metabase
  manifest, the Terraform that minted its password, and its demo and onboarding pages are
  deleted in the same change.
- The shared edge listener https-metabase becomes https-superset with hostname
  superset.${ESTATE_ZONE} (`prospector/deploy/k8s/base/edge.yaml`, branch feat/superset-listener).
- The vault gains superset-db-password and superset-secret-key, both Terraform-minted
  (platform/oci/superset.tf); metabase-db-password leaves the vault when Terraform next applies.
- One piece of cleanup outlives the merge: the PersistentVolumeClaim pgdata-metabase-db-0 in
  observability still holds the dead Metabase database (prune is off in that directory). The
  founder deletes it when he applies the change; the Superset runbook names it.
- Decision 0016 (Google sign-in inside Metabase) is superseded before acceptance; its branch is
  deleted unmerged and its Google-console runbook dies with it.
