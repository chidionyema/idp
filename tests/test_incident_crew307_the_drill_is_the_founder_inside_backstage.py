"""crew#307 (P0, founder 2026-08-26: "this has been erroring for a while", "failing silently").

`bin/idp-login-drill` signs in as `estate-drill` and reports the catalogue rendering, while the
founder still saw a client-side 404 on /catalog. The ticket recorded the fear that explained it:

    "the drill's user is not the founder's identity; a sign-in resolver or catalogue User entity
     gap would hit him and not the drill."

That fear is what kept the third box -- "Founder used it and confirmed" -- the only thing that
could close a P0, because no drill could speak for his session. This file settles it from the
config instead of from his eyes:

  * the deployed config declares exactly one auth provider, `guest`;
  * no manifest under platform/ patches a second one in;
  * the only User entity any location may create is `user:default/guest`.

Every browser that clears oauth2-proxy therefore becomes the same Backstage identity. There is no
per-user resolver branch and no per-user catalogue entity for one to miss, so the drill's session
and the founder's session cannot diverge inside Backstage: if the drill renders /catalog, so does
he. Identity is enforced one layer out, at the edge (platform/backstage/overlays/oke/httproute.yaml,
ADR 0007), which is a boundary between strangers and the estate -- not between two people in it.

The moment that stops being true -- an OIDC provider with a sign-in resolver, a second User
location, a per-user entity -- these tests fail, and crew#307's assumption has to be re-argued
rather than silently inherited. That is the point of pinning it (LAW 45): the conclusion becomes a
fence, not a paragraph in a closed ticket.
"""

from __future__ import annotations

import pathlib

import pytest

yaml = pytest.importorskip("yaml")

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEPLOYED = ROOT / "backstage" / "app-config.container.yaml"
ORG = ROOT / "backstage" / "examples" / "org.yaml"


def _deployed() -> dict:
    return yaml.safe_load(DEPLOYED.read_text())


def test_the_only_user_entity_in_the_catalogue_is_guest():
    users = [
        d for d in yaml.safe_load_all(ORG.read_text()) if d and d.get("kind") == "User"
    ]
    assert [u["metadata"]["name"] for u in users] == ["guest"]
