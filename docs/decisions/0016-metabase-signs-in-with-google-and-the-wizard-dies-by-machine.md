# 0016 — Metabase signs in with Google, and the setup wizard dies by machine

Date: 2026-09-02. Status: accepted (founder word, 2026-09-02, session 54539261). Fires on: the founder was asked by Metabase to create a password (2026-09-01).

## The defect

`platform/observability/metabase-deployment.yaml` claims Metabase reads the signed-in user's
email from the gateway header (`METABASE_USER_LOGIN_EMAIL_HEADER`) and that "no password exists
anywhere for Metabase". Neither variable exists in Metabase: the vendor's
[environment-variable reference](https://www.metabase.com/docs/latest/configuring-metabase/environment-variables)
has no header-auth setting at all, and Metabase settings are `MB_`-prefixed, so both
`METABASE_*` lines are inert. The pod boots to the first-run setup wizard, which asked the
founder to invent a password — exactly what decisions 0003 and 0007 forbid. This is a claim the
file does not support, on a founder surface.

## What the vendor edition can and cannot do

Verified against the vendor's live documentation on 2026-09-02:

- Open source Metabase has two federated doors: Google Sign-In and LDAP. Header/proxy auth does
  not exist in any edition; JWT, SAML and OIDC are Pro/Enterprise only.
- The first-run wizard is killable by machine: `POST /api/setup` with the instance's setup
  token creates the first admin without a person in the loop.

## The decision

1. **A Job seeds the first admin by machine.** One-shot Job in `observability`: reads the setup
   token, `POST /api/setup` with the founder's email (the vault's `langfuse-init-user-email`)
   and a random password minted into the vault (`metabase-admin-password`) that no person is
   ever shown or types. The wizard is gone before anyone visits.
2. **Google Sign-In is the interactive door**, pinned so only the founder's account enrols.
   Federated login, no password ever held for a person (decision 0007). Google exposes no API for
   standard OAuth clients (verified 2026-09-02: only IAP-internal clients are API-creatable),
   so the client is born once in the Google console by the founder -- the exact steps are
   quoted in `docs/runbooks/metabase-google-signin.md`. The client id is public and lives in
   `clusters/oke/estate-config.yaml` (one place for every name, R70); Metabase Google Sign-In
   needs no client secret.
3. **The deployment stops lying.** The two inert `METABASE_*` env lines and the header-auth
   comment go; the manifest says what is true.

## The risk, in a sentence

The founder passes two prompts (gateway SSO, then Google) instead of one; accepted because the
open-source edition cannot consume the gateway identity and the Pro edition's JWT door costs
more per month than the whole estate's $0–150 cost contract allows. Revisit if Pro is ever
bought.

## Rejected

- **Metabase Pro JWT/OIDC** — the only true single-login path; breaks the cost contract.
- **LDAP** — the estate runs no directory; standing one up to sign in one person is stitching.
- **Vault password typed by the founder** — decision 0007 forbids a person holding a password.
