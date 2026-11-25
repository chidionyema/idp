import assert from "node:assert/strict";
import { test } from "node:test";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  activeRollbackId, failureCause, requireMainSha, immutableTag, pinnedWranglerVersion, uploadArgs,
  firstBootDecision, assertScopedAuthority, probeZeroDeployments, wranglerLogTail,
} from "../scripts/release.mjs";
const SHA = "a".repeat(40);
const A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
test("only a full matching main SHA can deploy", () => {
  assert.equal(requireMainSha("refs/heads/main", SHA, SHA), SHA);
  assert.throws(() => requireMainSha("refs/heads/feature", SHA, SHA), /BLIND/);
  assert.throws(() => requireMainSha("refs/heads/main", SHA, "b".repeat(40)), /BLIND/);
  assert.throws(() => requireMainSha("refs/heads/main", "x", "x"), /BLIND/);
});
test("refuse uncertain or split rollback origins", () => {
  assert.equal(activeRollbackId(JSON.stringify({versions:[{version_id:A,percentage:100}]})), A);
  assert.equal(activeRollbackId(JSON.stringify({deployment:{versions:[{version_id:A,percentage:"100%"}]}})), A);
  for (const s of [
    "{}", "{\"versions\":[]}", "{", JSON.stringify({versions:[{version_id:A,percentage:50},{version_id:B,percentage:50}]}),
    JSON.stringify({versions:[{version_id:A,percentage:100},{version_id:B,percentage:100}]}),
  ]) assert.throws(() => activeRollbackId(s));
});
test("immutable tags use full reviewed source SHA", () => {
  assert.equal(immutableTag(SHA), "meridian-" + SHA);
  assert.throws(() => immutableTag("main"), /BLIND/);
  assert.equal(pinnedWranglerVersion(" ⛅️ wrangler 4.131.0"), true);
  assert.equal(pinnedWranglerVersion("4.131.0"), true);
  assert.equal(pinnedWranglerVersion("4.130.0"), false);
});
test("first boot never asks Wrangler to keep vars from a deployment that does not exist", () => {
  const first = uploadArgs(SHA, immutableTag(SHA), false);
  assert.ok(!first.includes("--keep-vars"), "first boot must not pass --keep-vars");
  assert.ok(first.includes("--strict"));
  assert.deepEqual(first.slice(0, 2), ["versions", "upload"]);
  assert.ok(first.includes("COMMIT_SHA:" + SHA));
  const later = uploadArgs(SHA, immutableTag(SHA), true);
  assert.ok(later.includes("--keep-vars"), "a re-deploy keeps the dashboard vars");
  assert.ok(later.includes("--strict"));
});
test("a failed child carries its own cause, never a credential", () => {
  assert.equal(failureCause("some noise\nError: Cannot use --keep-vars\n"), "Error: Cannot use --keep-vars");
  assert.equal(failureCause("Bearer abcdefghijklmnopqrstuvwxyz0123456789"), "Bearer <redacted>");
  assert.ok(!failureCause("token sk-abcdefghijklmnopqrstuvwxyz0123456789ABCDEF").includes("abcdefghijklmnopqrstuvwxyz0123456789"));
  assert.equal(failureCause(""), "");
});
// The founder's rule (2026-11-25, idp#8416): only an independently verified zero-deployment
// state is a first boot. A refusal, a timeout or a malformed body is NOT a first boot.
test("a first boot needs an independently verified zero-deployment state", () => {
  const zero = firstBootDecision({ status: 1, stdout: "", verifiedZeroDeployments: true });
  assert.deepEqual(zero, { state: "first-boot", version_id: null });
  const deployed = firstBootDecision({
    status: 0, stdout: JSON.stringify({ versions: [{ version_id: A, percentage: 100 }] }),
    verifiedZeroDeployments: false,
  });
  assert.deepEqual(deployed, { state: "deployed", version_id: A });
  for (const verified of [false, undefined, null]) {
    assert.throws(
      () => firstBootDecision({ status: 1, stdout: "", verifiedZeroDeployments: verified }),
      /BLIND/,
    );
  }
  // The old adapter caught EVERY error here, so a 401 looked like an empty account.
  assert.throws(
    () => firstBootDecision({ status: 1, stdout: "Authentication error", verifiedZeroDeployments: false }),
    /BLIND/,
  );
  assert.throws(
    () => firstBootDecision({
      status: 0,
      stdout: JSON.stringify({ versions: [{ version_id: A, percentage: 100 }, { version_id: B, percentage: 100 }] }),
      verifiedZeroDeployments: false,
    }),
    /BLIND/,
  );
});
test("the zero-deployment probe refuses what it cannot prove", async () => {
  const reply = (status, body) => async () => ({ status, ok: status >= 200 && status < 300, json: async () => body });
  const zero = await probeZeroDeployments("tok", "acct", reply(200, { result: [] }));
  assert.equal(zero.zero, true);
  const none = await probeZeroDeployments("tok", "acct", async () => ({ status: 404, ok: false, json: async () => ({}) }));
  assert.equal(none.zero, true);
  for (const status of [401, 403, 500]) {
    await assert.rejects(() => probeZeroDeployments("tok", "acct", reply(status, {})), /BLIND/);
  }
  await assert.rejects(
    () => probeZeroDeployments("tok", "acct", reply(200, { result: "not-a-list" })),
    /BLIND/,
  );
  const live = await probeZeroDeployments("tok", "acct", reply(200, { result: [{ id: A }] }));
  assert.equal(live.zero, false);
});
test("the release refuses the root token", () => {
  assert.throws(() => assertScopedAuthority("", null), /BLIND/);
  assert.throws(() => assertScopedAuthority("root-token-value", "root-token-value"), /REFUSED/);
  assert.equal(assertScopedAuthority("scoped-token-value", "root-token-value"), true);
});
test("the cause is read out of Wrangler's own log file, redacted", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "wrangler-log-"));
  const log = path.join(dir, "wrangler-2026-11-25.log");
  fs.writeFileSync(log, "noise\nHTTP 403: Workers Scripts Write is required for this account\n");
  const tail = wranglerLogTail(dir);
  assert.match(tail, /403/);
  assert.match(tail, /Workers Scripts Write/);
  fs.writeFileSync(log, "Authorization: Bearer " + "z".repeat(44) + "\n");
  assert.ok(!wranglerLogTail(dir).includes("z".repeat(44)));
  fs.rmSync(dir, { recursive: true, force: true });
  assert.equal(wranglerLogTail(path.join(dir, "absent")), "");
});
