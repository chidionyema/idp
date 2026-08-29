"""crew#618, founder 2026-08-29: "oauth is not in settings ... why guess when you can verify".

bin/idp-set-root sent him to /admin/settings/oauth with a "Generate OAuth client" button. Tailscale's
own page (kb/1215/oauth-clients, read 2026-08-29) says: Trust credentials page, press Credential, then
OAuth, then Generate credential. The estate already held that fact (root-trust.md, "Trust credentials
page") and the script was written from memory instead. This pins the script and the policy to the
vendor's words so the next rewrite cannot drift back.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTED = "https://console.tailscale.com/admin/settings/trust-credentials"


def test_tailscale_step_opens_the_trust_credentials_page():
    s = (ROOT / "bin/idp-set-root").read_text()
    assert DOCUMENTED in s
    assert "settings/oauth" not in s
    assert "Generate OAuth client" not in s
    assert 'Press "Credential", then "OAuth"' in s


def test_policy_names_the_same_page():
    for f in ("docs/reference/policy/credential-lifecycle.md",):
        t = (ROOT / f).read_text()
        assert "Trust credentials" in t, f
        assert "Settings, OAuth clients" not in t, f
