# Demo: idp-login-drill

## What it is

A drill that signs in to the front door the way a person does, in a headless browser, and fails
loudly when anything in the chain is broken. The existing login row of `bin/idp-verify` follows a
redirect and stops there, so it proves the door points at the identity domain and nothing more. It
cannot tell a working sign-in from a domain that has quietly put every account into a
password-reset loop, an app grant that was removed, an expired session cookie, or a catalogue that
answers 200 with an empty shell. This drill walks the whole path: Traefik, oauth2-proxy, the OCI
identity domain, the app grant, the session cookie and the Backstage render.

## Run it

    bin/idp-login-drill

It prints one line and exits 0 only on a rendered catalogue:

    ok      login-drill  signed in as estate-drill, catalogue rendered as user:default/estate-drill in 4.1s

A failure names the layer that broke, so nobody has to guess where to look:

    FAIL    login-drill  redirect https://catalogue.mumchimp.com/ landed on catalogue.mumchimp.com, expected the identity domain ...
    FAIL    login-drill  password-change the domain is demanding a new password for estate-drill ...
    FAIL    login-drill  catalogue answered 200 but no Backstage shell rendered
    FAIL    login-drill  identity https://catalogue.mumchimp.com/ rendered Backstage's guest sign-in page; the door's identity never reached the auth provider

Stages are `config`, `python`, `vault`, `browser`, `redirect`, `credentials`, `password-change`,
`session`, `catalogue` and `identity`.

## Where the credential comes from

Nowhere a person can reach. `platform/oci/identity` creates the domain user `estate-drill`, grants
it the front-door application beside the founder, generates its password with `random_password`
and writes that password into the same OCI vault the oauth2-proxy client secrets already live in,
under the name `front-door-drill-password`. The drill reads it back by name, hands it to the
browser driver through an environment variable, and never writes it to a log, an argument list or
a file. Rotating it is one `bin/idp-identity-apply apply` away.

## Where it runs on its own

The `login-drill` job of `.github/workflows/oke-check.yml`, daily at 06:17 and on every pull
request that touches the front door. It authenticates with the same GitHub OIDC to OCI token
exchange the platform check uses, so there is no key on any laptop for this path either.
