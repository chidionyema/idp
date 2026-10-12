"""The vault stand-in must give a key the shape that key's consumer parses.

Incident: 2026-10-12. Every image-update PR sat at shadow-verify and no built image ever moved
the overlays. platform/mcp's `fetch-estate-db` init container runs `flux pull artifact` with
DOCKER_CONFIG=/creds, which parses /creds/config.json -- the stood-in ghcr-pull
`.dockerconfigjson` -- and the stand-in wrote its prose placeholder into every key, so flux died
on the first byte, before the network:

    parsing config file (/creds/config.json): invalid character 's' looking for beginning of value

which is the `s` of "shadow-vault-stand-in". A row whose ExternalSecret feeds a JSON-parsing
consumer was therefore unconvergeable in every shadow run, which reads as a broken change.

The stand-in still forges no credential: what it writes for such a key is an empty auths block,
which is anonymous. A row that needs a real credential to go Ready still fails, at the registry
rather than at the parser.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def load_shadow():
    loader = importlib.machinery.SourceFileLoader(
        "idp_shadow", str(REPO / "bin" / "idp-shadow")
    )
    spec = importlib.util.spec_from_loader("idp_shadow", loader)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def an_external_secret(
    namespace="mcp", name="ghcr-pull", secret_key=".dockerconfigjson"
):
    """The shape the API server hands the stand-in for platform/mcp's ghcr-pull row."""
    return {
        "metadata": {"name": name, "namespace": namespace},
        "spec": {
            "target": {"name": name},
            "data": [{"secretKey": secret_key, "remoteRef": {"key": "ghcr-pull"}}],
        },
    }


def test_a_docker_config_key_is_stood_in_with_json_a_parser_accepts():
    shadow = load_shadow()
    (secret,) = shadow.vault_stand_ins([an_external_secret()])
    value = secret["stringData"][".dockerconfigjson"]
    # the exact call flux makes on the file this key becomes
    assert json.loads(value) == {"auths": {}}, value
    assert value != shadow.VAULT_PLACEHOLDER, "prose is what broke the row"


def test_a_json_suffixed_key_gets_json_too_and_a_credential_still_gets_prose():
    shadow = load_shadow()
    (json_key, credential) = shadow.vault_stand_ins(
        [
            an_external_secret(secret_key="service-account.json"),
            an_external_secret(name="temporal-db", secret_key="password"),
        ]
    )
    assert json.loads(json_key["stringData"]["service-account.json"]) == {"auths": {}}
    # unchanged, and deliberately so: the stand-in is not a credential, it is a placeholder
    assert credential["stringData"]["password"] == shadow.VAULT_PLACEHOLDER


def test_the_key_this_stands_in_for_is_the_file_the_mcp_init_container_parses():
    """Ties the test to the real consumer, so it cannot pass on a mount nobody uses."""
    text = (REPO / "platform/mcp/estate-mcp.yaml").read_text()
    assert "secretName: ghcr-pull" in text
    assert "key: .dockerconfigjson" in text
    assert "path: config.json" in text
    assert "DOCKER_CONFIG" in text
