# Signing in to SigNoz

SigNoz is the one tool in the estate that asks for a second credential. Everything else on the
zone opens on the estate login alone, and the hourly login-drill proves it door by door.

## Why it is different

SigNoz 0.138.0 is the community edition. Its vendor page
(`signoz.io/docs/userguide/sso-authentication`, read 2026-08-30) puts OIDC and SAML 2.0 in the
enterprise edition and leaves the community edition with Google Workspace only. Our identity
provider is an Oracle identity domain, not Google Workspace, so there is no configuration that
makes SigNoz join the one login. This is a property of the edition we run, not a gap in our
setup, and it is carried as a named exception on crew#718 CP2 rather than hidden.

The estate login still does real work here: `oauth2-proxy` stands in front of `signoz.<zone>`, so
nobody reaches the SigNoz sign-in page without first passing the front door. The second credential
is the second lock on the same door, not a way around the first.

## Signing in

The account is the root administrator SigNoz provisions at startup from the vault
(`SIGNOZ_USER_ROOT_*`, `platform/observability/values.yaml`). Its email and password are two vault
entries, `signoz-root-email` and `signoz-root-password`.

Read them with the estate's own vault primitive, which prints the value to your clipboard and never
to the terminal, a log or a shell history entry:

From your idp checkout:

```bash
bin/idp-cloud secret get signoz-root-email      # the address to type
bin/idp-cloud secret get signoz-root-password | pbcopy   # the password, straight to the clipboard
```

Then open `https://signoz.<zone>`, pass the front door on your estate login as usual, and paste.

Put both into your password manager the first time you do this. After that the browser fills them
and SigNoz is one click like everything else.

## What not to do

Do not paste either value into a chat, an issue, a pull request or a commit message. Founder
ruling R49, 2026-08-28: "we dont send password here". Name the vault entry instead; that is what
this page does.

## If it stops working

`bin/idp-cloud secret get` exits 1 with `NotFound` when the entry is absent and 4 when it cannot be
decoded. If the entry is gone, the SigNoz pod's own `ExternalSecret` (`signoz-root`,
`platform/observability/signoz.yaml`) is reading the same two names, so the pod would be failing
too — check that before assuming the vault is at fault.
