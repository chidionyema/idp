"""platform/brain-hub/worker.js: the One-Brain off the Mac.

The Worker and its Durable Object run here under Node, with node:sqlite standing in for the
Durable Object's SQLite storage (same exec(query, ...params).toArray() surface) and a Map for R2.
Every route is exercised on the real module: reads open, writes fail closed without the key,
ledgers are null (not zero) before the first import, import is idempotent, the stream replays
by cursor, reports gaps, pushes live events, and the hourly snapshot reaches R2.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WORKER = REPO / "platform/brain-hub/worker.js"

HARNESS = r"""
import { DatabaseSync } from 'node:sqlite';
import worker, { BrainHub } from %s;
const db = new DatabaseSync(':memory:');
const sql = { exec: (q, ...p) => { const s = db.prepare(q); const isRead = /^\s*select/i.test(q);
  const rows = isRead ? s.all(...p) : (s.run(...p), []); return { toArray: () => rows }; } };
const r2 = new Map();
const KEY = 'k'.repeat(32);
let hubObj;
const mk = (envExtra) => {
  const env = { BRAIN_ADMIN_KEY: KEY, HUB_BUILD: 'abc123', SNAPSHOTS: { put: async (k, v) => r2.set(k, v) }, ...envExtra };
  hubObj = hubObj || new BrainHub({ storage: { sql } }, env);
  hubObj.env = env;
  env.HUB = { idFromName: () => 'estate', get: () => hubObj };
  return env;
};
const env = mk({});
const call = async (method, path, body, headers = {}, e = env) => {
  const r = await worker.fetch(new Request('https://brain.example.com' + path, { method, headers,
    body: body === undefined ? undefined : (typeof body === 'string' ? body : JSON.stringify(body)) }), e);
  return { status: r.status, ct: r.headers.get('content-type') || '', text: r.body && !path.includes('/stream') ? await r.text() : '', body: r.body };
};
const auth = { authorization: 'Bearer ' + KEY };
async function readStream(r, ms) {
  const reader = r.body.getReader(); const dec = new TextDecoder(); let out = '';
  const end = Date.now() + ms;
  let pending = reader.read();
  while (Date.now() < end) {
    const res = await Promise.race([pending, new Promise(z => setTimeout(() => z({ timeout: true }), 50))]);
    if (res.timeout) continue; if (res.done) break; out += dec.decode(res.value); pending = reader.read();
  }
  reader.cancel().catch(() => {}); return out;
}
const out = {};
out.health = await call('GET', '/healthz');
out.other = await call('GET', '/nope');
out.state0 = JSON.parse((await call('GET', '/api/brain/state')).text);
out.noKeyEnv = await call('POST', '/api/brain/steer', { directive: 'x' }, auth, mk({ BRAIN_ADMIN_KEY: '' }));
mk({});
out.wrongKey = await call('POST', '/api/brain/steer', { directive: 'x' }, { authorization: 'Bearer ' + 'z'.repeat(32) });
out.badJson = await call('POST', '/api/brain/heartbeat', '{', {});
const data = { source: 'mac', instructions: [{ instructionId: 'I-1', initiatedAtMs: 1 }, { instructionId: 'I-2', initiatedAtMs: 2 }],
  yieldReceipts: [{ receiptId: 'Y-1', recordedAtMs: 3 }], policyDecisions: [], sessions: [{ sessionId: 'S-1', updatedAt: '2026-11-14T00:00:00Z' }],
  arrTickets: [{ ticketId: 'A-1', createdAt: '2026-11-14T00:00:00Z' }, { nope: true }], labFlags: { x: true } };
out.imp1 = JSON.parse((await call('POST', '/api/brain/import', data, auth)).text);
out.imp2 = JSON.parse((await call('POST', '/api/brain/import', data, auth)).text);
out.rec = await call('POST', '/api/brain/record/instruction', { instructionId: 'I-3', initiatedAtMs: 9 }, auth);
out.recBad = await call('POST', '/api/brain/record/yield', { noid: 1 }, auth);
out.hb = await call('POST', '/api/brain/heartbeat', { name: 'cockpit', kind: 'surface' });
out.hbBad = await call('POST', '/api/brain/heartbeat', { name: '<script>' });
out.steer = JSON.parse((await call('POST', '/api/brain/steer', { directive: 'ship it' }, auth)).text);
out.state1 = JSON.parse((await call('GET', '/api/brain/state')).text);
const s0 = await call('GET', '/api/brain/stream');
out.streamFresh = await readStream(s0, 300);
const s1 = await call('GET', '/api/brain/stream?since=1');
out.streamReplay = await readStream(s1, 300);
const s2 = await call('GET', '/api/brain/stream', undefined, { 'last-event-id': '999' });
out.streamGap = await readStream(s2, 300);
const live = await call('GET', '/api/brain/stream?since=' + out.state1.streamSequence);
const pending = readStream(live, 600);
await new Promise(z => setTimeout(z, 100));
await call('POST', '/api/brain/steer', { directive: 'live one' }, auth);
out.streamLive = await pending;
await worker.scheduled({}, env);
out.r2 = [...r2.keys()];
out.r2latest = JSON.parse(r2.get('brain/latest.json'));
const cors = async (o, m = 'GET') => { const r = await worker.fetch(new Request('https://brain.example.com/api/brain/state', { method: m, headers: o ? { origin: o } : {} }), env);
  return { status: r.status, acao: r.headers.get('access-control-allow-origin') }; };
out.corsPreview = await cors('https://otto-private-office-git-lane-deade-462d2a-chidionyemas-projects.vercel.app');
out.corsPages = await cors('https://genesis-founder-surface.pages.dev');
out.corsEvil = await cors('https://evil.example.com');
out.corsSpoof = await cors('https://otto-private-office-x-chidionyemas-projects.vercel.app.evil.com');
out.preflightOk = await cors('https://genesis-founder-surface.pages.dev', 'OPTIONS');
out.preflightEvil = await cors('https://evil.example.com', 'OPTIONS');
console.log(JSON.stringify(out));
process.exit(0);
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    d = tmp_path_factory.mktemp("hub")
    h = d / "h.mjs"
    h.write_text(HARNESS % json.dumps(WORKER.as_uri()))
    p = subprocess.run(
        [node, "--no-warnings", str(h)], capture_output=True, text=True, timeout=60
    )
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_health_and_front_door(run):
    assert run["health"]["status"] == 200 and run["health"]["text"] == "ok"
    assert run["other"]["status"] == 404


def test_ledgers_are_null_not_zero_before_first_import(run):
    s = run["state0"]
    assert (
        s["instructions"] is None
        and s["yieldReceipts"] is None
        and s["sessions"] is None
    )
    assert (
        s["ledgersSource"] == "awaiting-first-import-from-mac"
        and s["laptopMayBeRequired"] is False
    )


def test_writes_fail_closed(run):
    assert run["noKeyEnv"]["status"] == 503
    assert run["wrongKey"]["status"] == 401
    assert run["badJson"]["status"] == 400


def test_import_is_idempotent_and_counts_only_identified_records(run):
    assert run["imp1"]["imported"] == {
        "instructions": 2,
        "yieldReceipts": 1,
        "policyDecisions": 0,
        "sessions": 1,
        "arrTickets": 1,
    }
    s = run["state1"]
    assert [i["instructionId"] for i in s["instructions"]] == [
        "I-3",
        "I-2",
        "I-1",
    ]  # newest first, no duplicates
    assert (
        len(s["yieldReceipts"]) == 1
        and len(s["arrTickets"]) == 1
        and s["labFlags"] == {"x": True}
    )
    assert run["recBad"]["status"] == 400


def test_heartbeat_steer_and_state(run):
    s = run["state1"]
    assert [x["name"] for x in s["surfaces"]] == ["cockpit"] and run["hbBad"][
        "status"
    ] == 400
    assert (
        s["directive"]["directive"] == "ship it"
        and s["streamSequence"] >= 5
        and s["commit"] == "abc123"
    )


def test_stream_snapshot_replay_gap_and_live_push(run):
    assert "retry: 3000" in run["streamFresh"] and "event: state" in run["streamFresh"]
    assert (
        "event: import" in run["streamReplay"]
        and "event: state" not in run["streamReplay"]
    )
    assert "event: gap" in run["streamGap"] and "cursor-ahead" in run["streamGap"]
    assert "event: directive" in run["streamLive"] and "live one" in run["streamLive"]


def test_hourly_snapshot_reaches_r2(run):
    assert "brain/latest.json" in run["r2"] and any(
        k.startswith("brain/20") for k in run["r2"]
    )
    assert run["r2latest"]["status"] == "cloud-hub"


def test_cors_only_for_the_founder_surfaces(run):
    assert run["corsPreview"]["acao"].endswith("chidionyemas-projects.vercel.app")
    assert run["corsPages"]["acao"] == "https://genesis-founder-surface.pages.dev"
    assert run["corsEvil"]["acao"] is None and run["corsSpoof"]["acao"] is None
    assert run["preflightOk"]["status"] == 204 and run["preflightEvil"]["status"] == 403
