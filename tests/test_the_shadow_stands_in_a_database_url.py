"""The shadow stands in a DATABASE_URL in the shape psycopg parses, not prose.

Incident (2026-10-25, runs 40241468896, base and head alike): every shadow run went red on

    pod unified-memory/unified-memory-server-... container server is CrashLoopBackOff
    (restarts 3)
      psycopg.ProgrammingError: missing "=" after "shadow-vault-stand-in"
      in connection info string
      ERROR: Application startup failed. Exiting.
    FAIL shadow flux could not reconcile platform/unified-memory-server

platform/unified-memory-server's ExternalSecret templates DATABASE_URL as a conninfo
(`postgresql://memory:{{ .password }}@estate-rw.estate-db.svc.cluster.local:5432/memory?...`).
The vault stand-in wrote `shadow-vault-stand-in` into it -- the right move for a credential read
as a string, the wrong shape for one a consumer parses -- so the app died on its first byte and
the row could never converge. Because the row is in scope for every image update and every PR
that touches the memory plane, it blocked the merge behind it, base included.

The fix is the same rule the JSON stand-in already follows: the value's shape follows the key's
own consumer. A templated conninfo keeps the row's own template -- host, role, database and its
TLS policy -- with every `{{ ... }}` replaced by the stand-in's placeholder, which the stand-in
postgres accepts because it seeds that same password from the head's databases.yaml and serves
TLS (`ssl=on`). Nothing is forged and nothing is relaxed: a row that needs the real credential
still fails where it belongs, and a `sslmode=require` that would break in production still
breaks here.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

REPO = Path(__file__).resolve().parents[1]
MEMORY_ROW = REPO / "platform" / "unified-memory-server" / "oke-unified-memory.yaml"


def load_shadow():
    loader = importlib.machinery.SourceFileLoader(
        "idp_shadow_dsn", str(REPO / "bin" / "idp-shadow")
    )
    spec = importlib.util.spec_from_loader("idp_shadow_dsn", loader)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def the_head_template():
    """The DATABASE_URL template platform/unified-memory-server actually ships.

    Read from the head, not typed here: if the manifest's own template changes shape, this
    test grades the new one instead of a copy of the old.
    """
    text = MEMORY_ROW.read_text()
    m = re.search(r'DATABASE_URL:\s*"([^"]+)"', text)
    assert m, "platform/unified-memory-server no longer templates DATABASE_URL"
    return m.group(1)


def test_a_templated_conninfo_is_stood_in_as_a_parsable_dsn():
    shadow = load_shadow()
    template = the_head_template()
    value = shadow.placeholder("DATABASE_URL", template)
    assert value != shadow.VAULT_PLACEHOLDER, "prose where psycopg parses a DSN"
    parsed = urlparse(value)
    assert parsed.scheme in ("postgresql", "postgres"), value
    assert parsed.username == "memory"
    assert parsed.hostname == "estate-rw.estate-db.svc.cluster.local"
    assert parsed.port == 5432
    assert parsed.path == "/memory"
    # The password is the stand-in's, never a credential.
    assert parsed.password == shadow.VAULT_PLACEHOLDER
    # And no template braces survive, or the DSN would not parse in the pod either.
    assert "{{" not in value and "}}" not in value
    # Everything else the template carried is preserved, query string included.
    assert parse_qs(parsed.query) == parse_qs(urlparse(template).query)


def test_the_stand_in_keeps_the_rows_own_tls_policy_because_it_can_serve_it():
    """`sslmode` is the PR's to set. The stand-in runs postgres with ssl=on, so it is served.

    A stand-in that relaxed `require` to `disable` would connect here and fail in production --
    it would hide the exact misconfiguration `require` exists to surface.
    """
    shadow = load_shadow()
    qs = parse_qs(
        urlparse(shadow.placeholder("DATABASE_URL", the_head_template())).query
    )
    assert qs.get("sslmode") == parse_qs(urlparse(the_head_template()).query).get(
        "sslmode"
    )
    # ...and the stand-in it connects to actually speaks TLS.
    postgres = [
        c
        for o in shadow.db_standin_objects()
        if o["kind"] == "Deployment"
        for c in o["spec"]["template"]["spec"]["containers"]
    ]
    assert postgres, "the database stand-in has no container"
    assert "ssl=on" in " ".join(postgres[0]["args"]), "a require would be refused"


def test_a_conninfo_without_sslmode_is_left_without_one():
    shadow = load_shadow()
    value = shadow.placeholder(
        "DATABASE_URL", "postgresql://u:{{ .password }}@h:5432/d"
    )
    assert value == f"postgresql://u:{shadow.VAULT_PLACEHOLDER}@h:5432/d"


def test_prose_keys_are_unchanged():
    shadow = load_shadow()
    assert shadow.placeholder("API_KEY") == shadow.VAULT_PLACEHOLDER
    assert shadow.placeholder("API_KEY", "not a uri") == shadow.VAULT_PLACEHOLDER


def test_a_json_key_wins_over_a_template():
    """'.dockerconfigjson' is parsed as JSON whatever its template says."""
    shadow = load_shadow()
    assert (
        shadow.placeholder(".dockerconfigjson", '{"auths":{{ .creds }}}')
        == shadow.JSON_STAND_IN
    )


def test_the_externalsecret_gets_the_dsn_not_the_prose():
    """End to end through the function the shadow actually calls: template -> Secret."""
    shadow = load_shadow()
    items = [
        {
            "metadata": {"name": "unified-memory-db", "namespace": "unified-memory"},
            "spec": {
                "target": {
                    "name": "unified-memory-db",
                    "template": {
                        "data": {
                            "DATABASE_URL": the_head_template(),
                            "MEMORY_SURFACE_TOKEN": "{{ .token }}",
                        }
                    },
                },
                "data": [],
            },
        }
    ]
    secrets = shadow.vault_stand_ins(items)
    assert len(secrets) == 1
    data = secrets[0]["stringData"]
    assert urlparse(data["DATABASE_URL"]).scheme == "postgresql"
    assert urlparse(data["DATABASE_URL"]).password == shadow.VAULT_PLACEHOLDER
    # The prose key beside it is still prose: only the consumer's shape changed.
    assert data["MEMORY_SURFACE_TOKEN"] == shadow.VAULT_PLACEHOLDER
