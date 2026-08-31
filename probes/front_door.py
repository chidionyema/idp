"""crew#631 CP9, the L3 layer for every surface behind the one login: what bin/idp-login-drill saw
after the front-door session walked to a surface. Two assertions per surface, all from the drill's
own measurements (the host and path the browser came to rest on, the status, the count of password
inputs), so a verdict about a surface grades the person's road and never a screenshot.

reached_host  the browser came to rest on the surface's own host with the front-door session: not
              on the identity domain (no grant), not elsewhere, not on an error status.
signed_in     the resting page is neither a sign-in path nor a page with a password input, so the
              one login was one. A surface that needs a second credential (the drill's
              SECOND_LOGIN_EXPECTED, SigNoz community: crew#718 CP2) fails this honestly and its
              prover marks the verdict BLOCKED with the reason, never PASS over a login screen."""

from probes.verdict import assertion

# a surface that comes to rest on one of these did not sign anybody in, whatever its DOM says
SIGN_IN_PATHS = ("/login", "/signin", "/sign-in", "/signup", "/sign-up", "/auth/")


def assertions(
    name,
    want_host,
    landed_host,
    landed_path,
    password_fields,
    status=200,
    domain_host="",
):
    on_domain = bool(domain_host) and landed_host == domain_host
    reached = (
        landed_host == want_host and not on_domain and not (status and status >= 400)
    )
    at_sign_in = any(landed_path.startswith(p) for p in SIGN_IN_PATHS)
    return [
        assertion(
            f"l3.front_door.{name}.reached_host",
            want_host,
            f"{landed_host}{landed_path} ({status})",
            reached,
        ),
        assertion(
            f"l3.front_door.{name}.signed_in",
            "no sign-in path, 0 password fields",
            f"{landed_path}, {password_fields} password field(s)",
            reached and not at_sign_in and password_fields == 0,
        ),
    ]
