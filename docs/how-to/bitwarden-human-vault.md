# Bitwarden human vault — operator setup

One-time bootstrap for the human secret door (decision 0017), written for the operator role:
today that is the founder, on a customer estate it is the platform admin — the steps are
identical. Every step is a browser step;
nothing is typed into a terminal and no value ever appears in a chat. Total: about ten minutes,
once, then never again.

## 1. Turn on Secrets Manager (Bitwarden, browser)

Vendor steps, quoted from bitwarden.com/help/sign-up-for-secrets-manager:
open the **Admin Console**, go to **Billing → Subscription**, tick
**Subscribe to Secrets Manager**, and select **Submit**. The free tier covers the estate's use:
unlimited secrets, three projects, three machine accounts.

## 2. Create the project and the machine account (Bitwarden, browser)

Quoted from bitwarden.com/help/secrets-manager-quick-start and /help/machine-accounts:
in the Secrets Manager web app select **New → Project** (name it for the estate), then
**New → Machine account**. Open the machine account, and on its **Projects** tab add the
project with **Can read**. On its **Access tokens** tab select **Create access token** —
the token is shown once.

## 3. Put the token in the cloud vault (Oracle console, browser)

Quoted from docs.oracle.com/iaas (vault secrets): open the estate's vault, select
**Secrets → Create Secret**, choose **Manual secret generation**, paste the token as the
**Secret Contents**, name it `bitwarden-machine`, and select **Create Secret**. This is the
bridge's one root credential — the one-root-then-code rule: a person hands over exactly one
value, and code mints everything after it. The register row for it is in
docs/reference/policy/root-trust.md.

## 4. Send the two public names

The organisation ID and the project ID (shown in the Bitwarden web app's address bar and
project page) are public identifiers, not secrets — send them in Telegram. They land in
`clusters/oke/estate-config.yaml` as `BITWARDEN_ORG_ID` and `BITWARDEN_PROJECT_ID`, and the
`human-vault` Flux row turns green the next time the cluster applies the declared state.

## Day 2: Storing a secret

Open the Bitwarden web vault on the phone, add a secret to the project, done — the cluster
pulls it (docs/how-to/onboarding/human-vault.md has the manifest side). The first customer is
Otto's Telegram bot token.

## If the row is red

`flux get kustomization human-vault` names the failing object. The row is isolated: red here
holds nothing else. Before the bootstrap above has run, red is the expected state.
