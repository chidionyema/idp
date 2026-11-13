"""platform/founder-passkey/worker.js: the relay holds no authority and refuses what it should.

The Worker runs here under Node with an in-memory KV in place of Cloudflare's, so the routes are
exercised on the real module: registration is write-once per nonce, approvals are kept per
challenge and capped, malformed input is refused, and the page's own script parses.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WORKER = REPO / "platform/founder-passkey/worker.js"

HARNESS = r"""
import worker from %s;
const store = new Map();
const env = { APPROVALS: { get: async k => store.get(k) ?? null, put: async (k, v) => { store.set(k, v); } } };
const call = async (method, path, body) => {
  const r = await worker.fetch(new Request('https://passkey.example.com' + path,
    { method, body: body === undefined ? undefined : (typeof body === 'string' ? body : JSON.stringify(body)) }), env);
  return { status: r.status, ct: r.headers.get('content-type') || '', csp: r.headers.get('content-security-policy') || '', text: await r.text() };
};
const N = 'n'.repeat(24), C = 'c'.repeat(43);
const out = {};
out.page = await call('GET', '/');
out.health = await call('GET', '/healthz');
out.regMissing = await call('GET', '/registration/' + N);
out.regBad = await call('POST', '/registration/' + N, { credentialId: 'x y', publicKeySpki: 'abc' });
out.reg = await call('POST', '/registration/' + N, { credentialId: 'cred_1', publicKeySpki: 'MFkwEwYH' });
out.regAgain = await call('POST', '/registration/' + N, { credentialId: 'evil', publicKeySpki: 'EVIL' });
out.regRead = await call('GET', '/registration/' + N);
out.badPath = await call('GET', '/registration/short');
out.apMissing = await call('GET', '/approve/' + C);
for (let i = 0; i < 5; i++) out['ap' + i] = await call('POST', '/approve/' + C, { authenticatorData: 'AA' + i, clientDataJSON: 'BB', signature: 'CC' });
out.apFull = await call('POST', '/approve/' + C, { authenticatorData: 'AA', clientDataJSON: 'BB', signature: 'CC' });
out.apRead = await call('GET', '/approve/' + C);
out.apJunk = await call('POST', '/approve/' + 'd'.repeat(43), 'not json');
const m = out.page.text.match(/<script>([\s\S]*)<\/script>/);
out.script = m ? m[1] : '';
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def results(tmp_path_factory) -> dict:
    node = shutil.which("node")
    if not node:
        pytest.fail("node is required to exercise the Worker")
    d = tmp_path_factory.mktemp("w")
    h = d / "harness.mjs"
    h.write_text(HARNESS % json.dumps(WORKER.as_uri()))
    r = subprocess.run([node, str(h)], capture_output=True, text=True, timeout=60)  # noqa: S603
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    script = d / "page.js"
    script.write_text(out["script"])
    chk = subprocess.run([node, "--check", str(script)], capture_output=True, text=True)  # noqa: S603
    out["script_ok"] = chk.returncode == 0
    out["script_err"] = chk.stderr
    return out


def test_page_is_served_locked_down(results: dict) -> None:
    p = results["page"]
    assert p["status"] == 200 and p["ct"].startswith("text/html")
    assert "default-src 'none'" in p["csp"]
    assert results["script_ok"], results["script_err"]


def test_health(results: dict) -> None:
    assert results["health"]["status"] == 200


def test_registration_is_write_once_per_nonce(results: dict) -> None:
    assert results["regMissing"]["status"] == 404
    assert results["regBad"]["status"] == 400
    assert results["reg"]["status"] == 200
    assert results["regAgain"]["status"] == 409
    got = json.loads(results["regRead"]["text"])
    assert got["credentialId"] == "cred_1" and got["publicKeySpki"] == "MFkwEwYH"
    assert (
        got["rp_id"] == "passkey.example.com"
        and got["origin"] == "https://passkey.example.com"
    )


def test_unknown_or_short_paths_are_refused(results: dict) -> None:
    assert results["badPath"]["status"] == 404


def test_approvals_are_kept_capped_and_validated(results: dict) -> None:
    assert results["apMissing"]["status"] == 404
    assert all(results[f"ap{i}"]["status"] == 200 for i in range(5))
    assert results["apFull"]["status"] == 429
    assert len(json.loads(results["apRead"]["text"])) == 5
    assert results["apJunk"]["status"] == 400
