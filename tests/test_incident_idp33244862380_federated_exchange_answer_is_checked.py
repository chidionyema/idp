"""Incident, oke-check run 33244862380 (2026-08-29): bin/idp-bootstrap-tailscale printed
`ok federated OIDC token exchanged` before reading Tailscale's answer, then blamed the seed
(`vault entry tailscale-seed does not exchange`). The exchange had been refused and the reason was
never shown. Silent green is the defect class: the answer is checked before the word ok."""

import re
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "idp-bootstrap-tailscale"


def _federated_block() -> str:
    text = SCRIPT.read_text()
    start = text.index('"$API/api/v2/oauth/token-exchange"')
    end = text.index('cat "$P/xchg"\n}', start)
    return text[start:end]


def test_the_exchange_answer_is_checked_before_ok():
    block = _federated_block()
    assert "jq -e '.access_token'" in block, (
        "the token-exchange answer must be checked before `ok federated`"
    )
    assert "FAIL federated" in block


def test_the_refusal_prints_the_full_answer_and_the_expected_subject():
    text = SCRIPT.read_text()
    assert 'Full answer:" >&2' in text, (
        "the full refusal body is printed, to stderr so a $(...) capture cannot swallow it"
    )
    assert "The runner presented: $claims" in text, (
        "the claims come from the token itself, never guessed (run 33248046751)"
    )


def test_the_token_is_never_printed():
    text = SCRIPT.read_text()
    for line in text.splitlines():
        for m in re.finditer(r'(?:say|fail) +\S+ +"([^"]*)"', line):
            assert not re.search(r"\$seed_tok|\$new_sec|\$tok\b", m.group(1)), line


def test_the_seed_failure_names_the_reason_too():
    text = SCRIPT.read_text()
    assert re.search(
        r'fail seed "the seed does not exchange for a token: \$\(jq -r', text
    )


# --- the exchange against a fake API, both answers (founder 2026-08-29: mock success and failure) ---
import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class _FakeApi(BaseHTTPRequestHandler):
    status = 200
    body = {"access_token": "tskey-api-NEVER-PRINTED", "scope": "oauth_keys"}
    seen = []

    def log_message(self, *_):
        pass

    def do_GET(self):  # the GitHub OIDC endpoint
        self._send(
            200,
            {
                "value": "header.eyJpc3MiOiAiaHR0cHM6Ly90b2tlbi5hY3Rpb25zLmdpdGh1YnVzZXJjb250ZW50LmNvbSIsICJzdWIiOiAicmVwbzpjaGlkaW9ueWVtYUAzNzczOTYvaWRwQDEzNDQzNjA2NTQ6cmVmOnJlZnMvaGVhZHMvbWFpbiIsICJhdWQiOiAiYXBpLnRhaWxzY2FsZS5jb20vZmVkaWQtdGVzdCJ9.signature"
            },
        )

    def do_POST(self):  # /api/v2/oauth/token-exchange
        n = int(self.headers.get("Content-Length", 0))
        _FakeApi.seen.append((self.path, self.rfile.read(n).decode()))
        self._send(self.status, self.body)

    def _send(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def _run_check(status, body):
    _FakeApi.status, _FakeApi.body, _FakeApi.seen = status, body, []
    srv = HTTPServer(("127.0.0.1", 0), _FakeApi)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    env = dict(
        os.environ,
        TAILSCALE_API_URL=base,
        TAILSCALE_FEDERATED_CLIENT_ID="fedid-test",
        ACTIONS_ID_TOKEN_REQUEST_URL=f"{base}/oidc?x=1",
        ACTIONS_ID_TOKEN_REQUEST_TOKEN="rt",
        GITHUB_REPOSITORY="chidionyema/idp",
        GITHUB_REF="refs/heads/main",
    )
    try:
        return subprocess.run(
            [str(SCRIPT), "--federated-check"],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
    finally:
        srv.shutdown()


def test_a_200_with_a_token_is_ok_and_the_token_is_not_printed():
    r = _run_check(
        200, {"access_token": "tskey-api-NEVER-PRINTED", "scope": "oauth_keys"}
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ok      federated" in r.stdout and "no secret held" in r.stdout
    assert "NEVER-PRINTED" not in r.stdout + r.stderr
    assert _FakeApi.seen and _FakeApi.seen[0][0] == "/api/v2/oauth/token-exchange"
    assert (
        "client_id=fedid-test" in _FakeApi.seen[0][1] and "jwt=" in _FakeApi.seen[0][1]
    )


def test_a_refusal_prints_the_full_body_and_exits_non_zero():
    r = _run_check(
        403,
        {
            "message": "subject claim does not match: repo:chidionyema/idp:ref:refs/heads/main"
        },
    )
    assert r.returncode == 1, r.stdout + r.stderr
    out = r.stdout + r.stderr
    assert "FAIL    federated" in out and "HTTP 403" in out
    assert "subject claim does not match" in out, (
        "the full refusal body is what the operator reads"
    )
    assert "sub=repo:chidionyema@377396/idp@1344360654:ref:refs/heads/main" in out, (
        "the exact sub the runner sent is printed, decoded from the token"
    )
    assert "iss=https://token.actions.githubusercontent.com" in out


def test_a_200_without_a_token_is_a_failure_not_a_green():
    r = _run_check(200, {"message": "nothing"})
    assert r.returncode == 1 and "no access_token" in r.stdout + r.stderr


def test_the_seed_never_mints_the_operator_on_the_runner():
    """founder 2026-08-29: the one bootstrap credential manages identities; the operator is minted
    only with the federated token. On the runner a refused identity is re-registered, then exchanged."""
    text = SCRIPT.read_text()
    block = text[
        text.index(
            'if [ -n "$fed_id" ] && seed_json=$(federated_exchange'
        ) : text.index("seed_tok=$(jq")
    ]
    assert "using the seed" not in text
    assert block.index("federated_exchange") < block.index("else"), (
        "federated is tried first, always"
    )
    runner = block[block.index('if [ -n "${ACTIONS_ID_TOKEN_REQUEST_URL:-}" ]; then') :]
    assert (
        'keyType:"federated"' in runner
        and 'seed_json=$(federated_exchange "$new_fid")' in runner
    )
