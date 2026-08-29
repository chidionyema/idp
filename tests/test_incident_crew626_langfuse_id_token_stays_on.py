"""crew#626 CP15: AUTH_CUSTOM_ID_TOKEN=false made every Langfuse SSO click fail with
error=OAuthCallback (drill run 33256502843). The vendor page says false switches to the plain
OAuth2 callback, which fails whenever the token response carries an id_token. Pinned on.
"""

from pathlib import Path

LANGFUSE = (
    Path(__file__).resolve().parents[1] / "platform" / "observability" / "langfuse.yaml"
)


def test_langfuse_reads_the_id_token():
    src = LANGFUSE.read_text()
    assert 'AUTH_CUSTOM_ID_TOKEN: "true"' in src
    assert 'AUTH_CUSTOM_ID_TOKEN: "false"' not in src
