# Metabase Google sign-in

Decision 0016 (accepted 2026-09-02): nobody ever types a password into Metabase. A one-shot
Job creates the first admin by machine with a vault password no person is shown, and the
interactive door is Google Sign-In, limited to the founder's account because account
automatic account creation is off and the seeded admin is the only user that exists.

## The one human step: Mint the Google client id

Google has no API for creating a standard OAuth client (only IAP-internal ones), so this is
done once, in the Google console. Steps per the vendor pages (Metabase "Google Sign-In" doc
and Google's "Setting up OAuth 2.0" help page, read 2026-09-02):

1. Open https://console.cloud.google.com/apis/credentials (any project; create one if none).
2. Click **Create credentials** → **OAuth client ID**. If asked, configure the consent screen
   first (External, app name anything, your email).
3. Application type: **Web application**.
4. **Authorized JavaScript origins**: add `https://metabase.<your zone>` — the zone is the
   `ESTATE_ZONE` value in `clusters/oke/estate-config.yaml`.
5. Leave **Authorized redirect URIs** empty (the vendor doc says exactly this).
6. Copy the client ID (it ends in `.apps.googleusercontent.com`). It is public, not a secret.
7. Paste it as the `METABASE_GOOGLE_CLIENT_ID` value in `clusters/oke/estate-config.yaml`
   (tell any agent "the Metabase client id is <value>" and it lands there for your review).

Until step 7 lands, the Google button simply doesn't appear; Metabase stays fenced behind the
gateway login and nothing is broken.

## What the machines do (no hands)

- Terraform mints `metabase-admin-password` into the vault (`platform/oci/metabase.tf`);
  External Secrets mounts it as a file.
- The `metabase-setup` Job (`platform/observability/metabase-setup.yaml`) waits for Metabase,
  reads the setup token from `/api/session/properties`, and POSTs `/api/setup` with your email
  and that password. The "create a password" wizard never appears again. Already set up = the
  Job prints so and exits green.
- The deployment enables `MB_GOOGLE_AUTH_ENABLED` only when the client id is non-empty.

## How you sign in, after

Open `https://metabase.<zone>`, pass the gateway login as always, then click **Sign in with
Google** and pick your account. Two prompts, zero passwords — the free edition cannot reuse
the gateway identity (that is Pro-only and over the cost contract; decision 0016 records it).

## If it misbehaves

- Google button missing: `METABASE_GOOGLE_CLIENT_ID` is still empty, or the pod predates the
  config change (Reloader rolls it on the ConfigMap update).
- "This account isn't allowed": expected for any account that isn't the seeded founder email —
  that is the pinning working.
- Wizard visible again: someone emptied the database; Flux re-runs the Job when it next applies the declared state.
