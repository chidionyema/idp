"""Offline GitHub clock/JWT regression, using synthetic headers and no real key."""
import base64
import json
import os
from pathlib import Path
import subprocess

import pytest

NOW = 1794966590
DATE = "Wed, 18 Nov 2026 01:49:50 GMT"
ROOT = Path(__file__).resolve().parents[1]


def response(headers, status=200):
    return f"HTTP/2 {status}\r\n{headers}\r\n\r\n"


@pytest.mark.parametrize("headers,local,curl_rc,ok", [
    (response("Date: " + DATE), NOW + 93, 0, True),
    ("HTTP/1.1 200 Connection established\r\nDate: Wed, 18 Nov 2026 00:00:00 GMT\r\n\r\n" + response("dAtE: " + DATE), NOW, 0, True),
    ("HTTP/1.1 200 Connection established\r\nDate: " + DATE + "\r\n\r\n" + response("Server: GitHub"), NOW, 0, False),
    (response("Server: GitHub"), NOW, 0, False),
    (response("Date: Wed,"), NOW, 0, False),
    (response("Date: " + DATE + "\r\nDate: " + DATE), NOW, 0, False),
    (response("Date: " + DATE + "\r\nAge: 7200"), NOW, 0, False),
    (response("Date: " + DATE + "\r\nAge: 0"), NOW, 0, True),
    (response("Date: " + DATE), NOW + 121, 0, False),
    (response("Date: " + DATE), NOW - 121, 0, False),
    (response("Date: Thu, 18 Nov 2026 01:49:50 GMT"), NOW, 0, False),
    (response("Date: Wed, 18 Nov 2026 25:49:50 GMT"), NOW, 0, False),
    (response("Date: " + DATE, 401), NOW, 0, False),
    (response("Date: " + DATE), NOW, 1, False),
])
def test_clock_at_signing_boundary(tmp_path, headers, local, curl_rc, ok):
    source = (ROOT / "bin/idp-github-app").read_text()
    start = source.index("github_now() {")
    end = source.index("\n# app_api", start)
    functions = tmp_path / "functions.sh"
    functions.write_text(source[start:end])
    spy = tmp_path / "signed"
    script = r'''
set -euo pipefail
source "$FUNCTIONS"
curl(){ printf '%s' "$HEADERS"; return "$CURL_RC"; }
date(){ if [[ "$*" == '-u +%s' ]]; then printf '%s\n' "$LOCAL_NOW"; else command date "$@"; fi; }
openssl(){ if [[ "$1" == dgst ]]; then touch "$SPY"; cat >/dev/null; printf 'fake-signature'; else command openssl "$@"; fi; }
b64url(){ openssl base64 -A | tr '+/' '-_' | tr -d '='; }
jwt=$(app_jwt 4740261 ZmFrZQ==) || exit 2
printf '%s' "$jwt"
'''
    result = subprocess.run(["bash", "-c", script], env={
        **os.environ, "FUNCTIONS": str(functions), "HEADERS": headers,
        "LOCAL_NOW": str(local), "CURL_RC": str(curl_rc), "SPY": str(spy),
    }, capture_output=True, text=True, timeout=15)
    assert result.returncode == (0 if ok else 2), result.stderr
    assert spy.exists() == ok
    if ok:
        payload = result.stdout.split(".")[1]
        decoded = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        assert decoded == {"iat": NOW - 60, "exp": NOW + 420, "iss": "4740261"}
    else:
        assert not result.stdout
