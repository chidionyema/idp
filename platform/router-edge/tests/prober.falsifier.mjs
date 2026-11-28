// Falsifier for scripts/blackbox-prober.mjs. The release workflow's only proof of "operating" is this
// prober; a prober that crashes on a healthy router makes every release NOT_OPERATIONAL and every
// rollback unverifiable (run 45837152441: "Body is unusable: Body has already been read").
//
// known-good: a healthy stub router  -> exit 0, five PASS lines
// known-bad:  chat answers 502       -> exit 1, probe 3 FAIL carrying the response body
import assert from "node:assert/strict";
import http from "node:http";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const PROBER = fileURLToPath(new URL("../scripts/blackbox-prober.mjs", import.meta.url));
const SHA = "abc1234";

function stub(chatStatus) {
  return http.createServer((req, res) => {
    const send = (code, obj, headers = {}) => {
      res.writeHead(code, { "content-type": "application/json", ...headers });
      res.end(typeof obj === "string" ? obj : JSON.stringify(obj));
    };
    req.resume();
    if (req.url === "/health") {
      return send(200, { status: "ok", ledger_ok: true, zone: "zone-b-cloudflare-edge", commit_sha: SHA });
    }
    if (req.url === "/v1/chat/completions") {
      if (req.headers.authorization !== "Bearer client-key") return send(401, { error: "unauthorized" });
      if (chatStatus !== 200) return send(chatStatus, "upstream exploded: lane pool empty");
      return send(200, { choices: [{ message: { content: "PROBE_OK" } }] }, { "x-meridian-commit-sha": SHA });
    }
    if (req.url === "/admin/v1/roles") return send(200, { roles: { coder: {} } });
    if (req.url === "/admin/v1/budget") return send(200, { ok: true, remainingUsd: 1 });
    return send(404, { error: "not found" });
  });
}

async function runProber(chatStatus) {
  const server = stub(chatStatus);
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const env = {
    PATH: process.env.PATH,
    MERIDIAN_ROUTER_URL: `http://127.0.0.1:${server.address().port}`,
    MERIDIAN_CLIENT_KEY: "client-key",
    MERIDIAN_ADMIN_KEY: "admin-key",
    EXPECTED_COMMIT_SHA: SHA,
  };
  const child = spawn(process.execPath, [PROBER], { env });
  let out = "";
  let err = "";
  child.stdout.on("data", (d) => (out += d));
  child.stderr.on("data", (d) => (err += d));
  const code = await new Promise((r) => child.on("close", r));
  server.close();
  return { code, out, err };
}

const good = await runProber(200);
assert.equal(good.code, 0, `healthy router must probe clean, got rc=${good.code}\n${good.out}\n${good.err}`);
assert.equal((good.out.match(/"status":"PASS"/g) || []).length, 5, `expected five PASS lines:\n${good.out}`);

const bad = await runProber(502);
assert.equal(bad.code, 1, "a 502 on the authenticated chat must fail the prober closed");
assert.match(bad.err, /3_authenticated_large_payload_200/, "probe 3 must be the failing probe");
assert.match(bad.err, /upstream exploded: lane pool empty/, "the failure must carry the response body");
assert.doesNotMatch(bad.err, /Body is unusable/, "the prober must read the body once");

console.log("prober.falsifier: ok (healthy stub passes 5/5; 502 fails closed with its body)");
