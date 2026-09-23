# Onboarding: idp-login-drill

## What it is

The command you run when someone says the portal will not let them in, and the job that tells you
first when that becomes true overnight. It signs in to `https://catalogue.<zone>/` as a dedicated
drill account and confirms the catalogue actually renders. Everything it needs is already in the
repository and the vault, so there is nothing to configure and nothing to paste.

## Before the first run

Two things must exist, and both are Terraform's job rather than yours:

    bin/idp-identity-apply plan          # read what it will create
    bin/idp-identity-apply apply -auto-approve

That creates the domain user `estate-drill`, grants it the front-door application, and stores its
generated password in the OCI vault as `front-door-drill-password`. You never see the password and
you never need it.

Locally the drill needs a Python with Playwright and a Chromium:

    pip install playwright && playwright install chromium

If your default `python3` is not the one holding Playwright, point at the right interpreter with
`DRILL_PYTHON=/path/to/python bin/idp-login-drill`. In CI the job installs both itself.

## Reading a failure

The word after `FAIL    login-drill` is the stage, and the stage is the layer to look at.

- `config` — `clusters/oke/estate-config.yaml` is missing `ESTATE_ZONE` or `ESTATE_OIDC_DOMAIN_URL`.
- `vault` — the secret is absent or this identity cannot read it. Run the apply above.
- `redirect` — the door served something instead of handing the visitor to the identity domain.
  Look at the Traefik middleware and the oauth2-proxy pods.
- `credentials` — the sign-in form did not accept the drill account. The grant or the password has
  drifted from what Terraform wrote.
- `password-change` — the identity domain wants a new password for the drill user. The drill will
  not set one, on purpose: a script that can change its own credential is a script that can lock
  the account out of Terraform's hands. Re-apply, or clear the must-change flag on the user.
- `session` — sign-in worked but the browser did not come back to the catalogue host.
- `catalogue` — the session is good and Backstage is not rendering. That is a Backstage problem.
- `identity` — the catalogue rendered but Backstage did not take the door's identity: it showed a guest sign-in page, or its `oauth2Proxy` provider did not return a `user:` ref. Look at the ForwardAuth middleware headers and `packages/backend/src/auth`.

## What it never does

It never bypasses a password prompt, never stores a credential outside the vault, and never prints
one. A drill that works around a broken door proves nothing about the door.
