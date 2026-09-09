# Disaster recovery register

**Purpose.** The single honest list of everything that stands between a founder-only cold boot —
or a move off Oracle — and a working estate. The founder/CEO should be selling, not debugging
infrastructure. Each row is PROVEN (a repo file, test or drill shows it) or OPEN (needs a live
drill to know). Nothing here claims a live result that was not measured.

**Why this file exists.** crew#673 (DR lane, "recover when only the founder is left") names this
file as its CP1. The portability drill (crew#488) already proves most of the *code* moves; this
register is the honest account of what is NOT code and would stop a reboot.

**The one-line recovery story that is already PROVEN:** the estate's Flux manifests hydrate onto a
vanilla, non-Oracle k3s cluster, weekly (`bin/idp-portability-drill`, `drills/portability-floor.txt`
at 10/43, only `secret-store` and `estate-catalog` are OCI-red). So the "code survives Oracle"
half is largely real. The register below is the half that is NOT yet proven: the identities,
secrets, cloud resources, data and non-git objects a reboot depends on.

---

## Phase 0 — the very first identity (highest risk)

| Dependency | Status | Recovery truth |
|---|---|---|
| Founder's OCI identity (browser login) | **PROVEN root, no second door written** | `bin/idp-oci-bootstrap` (bin/idp-oci-bootstrap:44) requires a founder browser login and is the root that creates the IAM user (`estate-tofu`), its API key, the dynamic groups, and the GitHub WIF. If the tenancy is gone or this identity is lost, recovery needs Oracle account recovery, not this repo. **There is no documented second door.** |
| OCI tenancy OCID / region / home region | PROVEN sourced | From the sops vault by `bin/idp-oci-bootstrap:33`. Needed before any OCI action. Not in git (correctly). |
| `estate-tofu` user + API key | PROVEN | Machine-created and vaulted (bin/idp-oci-bootstrap:83,151-160). Recoverable only after the founder identity above exists. |

**Rule:** nothing in this estate works from cold until the founder's OCI identity exists. This is
the one place a "jungle boot" stops unless a second door (escrow, or a recovery identity Oracle can
restore) is created and tested. See crew#673 CP1.

## Phase 1 — cluster + Kubernetes identity

| Dependency | Status | Recovery truth |
|---|---|---|
| Kube auth / how anyone reaches the cluster | PROVEN | `bin/idp-kube:7,70` uses an OCI-generated kubeconfig + short-lived tokens from `bin/idp-cloud`/`bin/idp-jit`. Depends on Phase 0 identity. |
| Cluster recreation | PROVEN tool, OPEN end-to-end | `bin/idp-oke-rebuild` rebuilds the cluster from git (crew#78). **OPEN:** no drill has proven rebuild from an EMPTY tenancy with only founder login. |
| Cluster identity inside (instance principal pods, SPIRE) | PROVEN exists / OPEN recover | The portability drill proves pods hydrate on a non-OCI cluster, but instance-principal pods (OCI-calling) need the OCI dynamic group (`workers`/`bridge`). |

## Phase 2 — secrets and their doors

Live ground truth (run of `bin/idp-root-trust --check`): **63 register rows; 53 MEETS, 10 MISS.**
A MISS row is a human-door gap — no bootstrapper exists, so it needs a person.

| Secret home / item | Status | Recovery truth |
|---|---|---|
| OCI vault (estate-vault, machine-minted) | PROVEN | Code mints into it via ESO/generators. Recoverable with Phase 0 OCI access. |
| Bitwarden human-vault (human-born) | PROVEN, single point | Root = founder's Bitwarden master password (docs/decisions/0017). Machine token in `platform/human-vault/store.yaml:18`. **A founder who loses the master password loses this door.** |
| GitHub repo secrets (SEED_*, R52 roots) | PROVEN human-dependent | Set once by founder via `bin/idp-set-root`. If the GitHub org is gone, these are gone and must be re-created at each vendor (see crew#832). |
| JIT broker signing + agent key | PROVEN recoverable | Machine-minted into vault (`bin/idp-vault-put jit-broker ...`, docs/reference/policy/root-trust.md, platform/jit/deployment.yaml). Not a DR blocker (repo-agnostic, vault-held). |

**The 10 MISS rows (human-born, no bootstrapper)** — each needs the founder or a human door:
`ghcr-pull` (crew#577), `commerce-payment-provider` (crew#623), `bitwarden-machine` (crew#809),
`otto-staging-telegram` (crew#832), `cyrus-linear` + `cyrus-linear-api-token` (crew#834),
the vendor keys `DEEPSEEK_API_KEY MINIMAX_API_KEY MOONSHOT_API_KEY OPENROUTER_API_KEY
GEMINI_API_KEY EXA_API_KEY CURSOR_API_KEY` (crew#832), `GOOGLE_OAUTH_CLIENT_*` (crew#809),
`TELEGRAM_ALERTS_*`/`TELEGRAM_HERMES_*` (crew#832), `STRIPE_SECRET_KEY` (crew#809).

**Rule:** every one of these is lost to automated recovery because the vendor has no create-key
API — a human made it once in a console. The named fix (crew#832/809 decision 0020): a one-shot
ingest through the portal so even a rotation needs no Bitwarden web form. Until that lands, these
are the enforcement of "the founder must be present".

## Phase 3 — external vendors and non-git objects

| Dependency | Status | Recovery truth |
|---|---|---|
| External vendor keys | mostly PROVEN human-born | DeepSeek, Stripe root, Telegram/BotFather, Google OAuth, Linear, Minimax, OpenRouter, Kimi, Exa, Cursor, Kaggle: no programmatic create-key API, so a human is in the loop (platform/vendors/consoles.yaml, crew#832). |
| Domain / DNS registrar | **OPEN** | Cloudflare DNS bootstrapped (`bin/idp-bootstrap-cloudflare`), but the root registrar/domain ownership recovery is NOT documented as recoverable by code. |
| Telegram bot + registered webhook | PROVEN | BotFather token human-born; only one webhook per bot; recovery depends on the founder reaching BotFather. |
| Payment method / cloud account ownership | PROVEN | OCI root is machine after founder SSO; Stripe root is human-born. |
| GitHub org ownership | PROVEN human | The platform is a GitHub App (`bin/idp-github-app`); the org is owned by the founder, not recoverable by code. |
| Cert issuer (external CA) | OPEN | cert-manager handles in-cluster; external CA root trust not documented as recoverable. |

## Phase 4 — data and state

| Dependency | Status | Recovery truth |
|---|---|---|
| Service catalog / inventory | PROVEN regenerable | `catalog-gen` from the LAW 39 inventory in git. Not a loss. |
| Postgres (estate-db, langfuse, backstage, Temporal, commerce, hindsight, Dagster, Guacamole, Healthchecks, LiteLLM) | **mostly OPEN** | restic adopted (docs/reports/2026-09-08-founder-requests-ledger.md); the `shop-backup` drill proves SQLite restore (drills/catalogue.yaml), but **no Postgres restore is proven-by-restore** (crew#715; docs/runbooks/dagster.md "not yet implemented"). Live Postgres is the estate's single biggest data-loss risk. |
| Scheduled drills / health | PROVEN exist, OPEN founder-only | 30+ drills in `drills/catalogue.yaml` (oke-check, login-drill, verdict-*, estate-*). Trust re-establishment on a rebuilt estate with no agents is not proven. |

---

## Top blockers to a zero-friction cold boot / provider move (plain order)

1. **Founder's OCI identity is the one true root, with no second door.** Nothing boots until it
   exists, and no repo file recreates it. If Oracle (or the founder's own recoverability) is the
   fear, this is the apex.
2. **Live Postgres data is not proven recoverable.** restic is adopted; no restore drill proves a
   single database. A "move to AWS" that loses the data is not a recovery.
3. **10 human-door secrets have no bootstrapper.** They are the concrete enforcement of "the
   founder must be present," because vendors have no create-key API. The portal one-shot ingest
   (decision 0020) is the named path to shrink this.
4. **The GitHub org and vendor consoles are outside git and owned by the founder.** If the org is
   lost, `SEED_*` roots die with it; re-establishment is manual at each vendor.
5. **Rebuild-from-empty-tenancy is unproven.** `bin/idp-oke-rebuild` + the portability drill
   prove the mechanics exist; nobody has run the full founder-only chain into an empty tenancy
   (crew#673 CP3's exact ask).

## Evidence discipline

Every PROVEN row cites a repo file/line or a drill in `drills/catalogue.yaml`. Every OPEN row is
exactly that: needs a live drill. This register does not claim a single measured-to-work recovery
step that has not been run. This register is the content of crew#673 CP1.

_Generated 2026-09-09 from three read-only surface audits (cloud+identity, data+state+boot,
secrets+vendors) plus a live `bin/idp-root-trust --check` run._
