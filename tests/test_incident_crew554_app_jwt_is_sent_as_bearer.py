"""Incident 2026-08-27/28 (crew#267, crew#503, crew#554): every oke-check apply's installation step died on
`gh: A JSON web token could not be decoded (HTTP 401)` (runs 33120447702, 33124277054). The JWT was sound:
run 33098034984 measured the same token answering 200 under `Authorization: Bearer` and 401 under gh's
`Authorization: token`. With no installation id in the vault, ExternalSecret flux-system/github-app never
rendered, Kustomization alerts-github never became Ready, Kustomization drills (the drill-dispatcher
CronJob, crew#554 CP3) never reconciled, and no App-dispatched drill ran. The fix lived in idp#441 behind
an unrelated red row; this file carries it on its own."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "bin" / "idp-github-app"


def test_an_app_jwt_is_sent_as_bearer_never_through_gh_token() -> None:
    app = APP.read_text()
    assert 'GH_TOKEN="$jwt"' not in app
    assert re.search(r'-H "Authorization: Bearer \$jwt"', app)
    for path in ("/app/installations", "/app/installations/$inst/access_tokens"):
        assert f'app_api "$jwt" {path}' in app or f'app_api "$jwt" "{path}"' in app, path


def test_a_401_body_is_never_taken_for_an_installation_id() -> None:
    """Run 33097094260: gh printed the 401 body on stdout and a non-empty check took it for an id."""
    app = APP.read_text()
    assert app.count('[[ "$inst" =~ ^[0-9]+$ ]] || app_jwt_diag') == 2, "installation and token both grade the id by shape"
    assert 'jq -r \'if type=="array" then (.[0].id // empty) else empty end\'' in app


def test_the_script_still_parses() -> None:
    r = subprocess.run(["bash", "-n", str(APP)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
