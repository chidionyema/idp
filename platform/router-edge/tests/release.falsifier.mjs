import assert from "node:assert/strict";
import fs from "node:fs";
import { test } from "node:test";
import { SERVE_ATTEMPTS, SERVE_PAUSE_MS, activeRollbackId, failureCause, firstBootDeployArgs, isAllBackendsFailed, liveCommitSha, receiptError, requireMainSha, immutableTag, pinnedWranglerVersion, secretBulkArgs, shouldRollback, uploadArgs, workerSecrets } from "../scripts/release.mjs";
import { MIN_OUTPUT_FLOOR, liveRoles, rolePool, seedRolePool, vendorSecrets } from "../scripts/role-pool.mjs";
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
  assert.ok(!first.includes("--secrets-file"), "a version upload never carries a secret");
  assert.ok(!first.includes("--keep-vars"), "first boot must not pass --keep-vars");
  assert.ok(first.includes("--strict"));
  assert.deepEqual(first.slice(0, 2), ["versions", "upload"]);
  assert.ok(first.includes("COMMIT_SHA:" + SHA));
  const later = uploadArgs(SHA, immutableTag(SHA), true);
  assert.ok(!first.includes("--secrets-file"));
  assert.ok(later.includes("--keep-vars"), "a re-deploy keeps the dashboard vars");
  assert.ok(later.includes("--strict"));
});
test("a first boot deploys, because only deploy may create a Durable Object class", () => {
  const args = firstBootDeployArgs(SHA, immutableTag(SHA));
  assert.equal(args[0], "deploy", "first boot must use `wrangler deploy`");
  assert.ok(!args.includes("--keep-vars"));
  assert.ok(args.includes("--strict"));
  assert.ok(args.includes("COMMIT_SHA:" + SHA));
  assert.ok(args.includes(immutableTag(SHA)));
  assert.ok(!args.includes("--secrets-file"), "no secret file, no flag");
});

test("a Worker secret is set at script scope, so a rollback target authenticates too", () => {
  // Measured 2026-11-25 (run 45685741113): `--secrets-file` on an upload bound the admin key
  // to one version, the run reported upload_ok, the next admin call answered
  // 401 invalid_admin_key, and /health served commit 820bc8a34 while main was 0064d55f2.
  assert.deepEqual(secretBulkArgs("/tmp/w.json"), ["secret", "bulk", "/tmp/w.json"]);
  for (const args of [uploadArgs(SHA, immutableTag(SHA), true), firstBootDeployArgs(SHA, immutableTag(SHA))]) {
    assert.ok(!args.includes("--secrets-file"), "secrets are never bound to a single version");
  }
});

test("a deploy is proved by the version that answers, not by an upload that said ok", async () => {
  assert.equal(await liveCommitSha("https://llm.meridianlabs.cloud", async () =>
    new Response(JSON.stringify({ status: "ok", commit_sha: SHA }), { status: 200 })), SHA);
  await assert.rejects(
    liveCommitSha("https://llm.meridianlabs.cloud", async () => new Response("{}", { status: 503 })),
    /health refused 503/,
  );
  await assert.rejects(
    liveCommitSha("https://llm.meridianlabs.cloud", async () => new Response("{}", { status: 200 })),
    /BLIND: \/health carries no commit_sha/,
  );
});
test("the Worker is given its own keys, because a deploy never carries them", () => {
  assert.deepEqual(
    workerSecrets({ MERIDIAN_CLIENT_KEY: "c", MERIDIAN_ADMIN_KEY: "a", PATH: "/bin" }),
    { MERIDIAN_CLIENT_KEY: "c", MERIDIAN_ADMIN_KEY: "a" },
  );
  assert.deepEqual(workerSecrets({ MERIDIAN_CLIENT_KEY: "c" }), { MERIDIAN_CLIENT_KEY: "c" });
  assert.deepEqual(workerSecrets({}), {});
  const args = uploadArgs(SHA, immutableTag(SHA), true);
  assert.deepEqual(args.slice(-2), ["--keep-vars", "--strict"]);
  assert.ok(!args.includes("--secrets-file"), "secrets go through `secret bulk`, at script scope");
});
test("a failed child carries its own cause, never a credential", () => {
  assert.equal(failureCause("some noise\nError: Cannot use --keep-vars\n"), "some noise / Error: Cannot use --keep-vars");
  assert.equal(failureCause("Bearer abcdefghijklmnopqrstuvwxyz0123456789"), "Bearer <redacted>");
  assert.ok(!failureCause("token sk-abcdefghijklmnopqrstuvwxyz0123456789ABCDEF").includes("abcdefghijklmnopqrstuvwxyz0123456789"));
  assert.equal(failureCause(""), "");
  const wrangler = "\u001b[31m✘ [ERROR] A request to the Cloudflare API failed.\u001b[0m\n"
    + "  Authentication error [code: 10000]\n"
    + "🪵  Logs were written to \"/home/runner/.config/.wrangler/logs/x.log\"\n";
  assert.equal(
    failureCause(wrangler),
    "✘ [ERROR] A request to the Cloudflare API failed. / Authentication error [code: 10000]",
  );
});

test("the pool is repo truth, so a key set out-of-band can serve without a release", () => {
  // Seeding must not depend on the release step's env: the Cloudflare dashboard (or a
  // sealed workflow later) can put a vendor key on the Worker, and this pool must already
  // name that lane. A pool gated on SEED_* could only ever serve keys CI happened to hold.
  assert.deepEqual(rolePool(), rolePool({}));
  const { roles } = rolePool();
  assert.deepEqual(Object.keys(roles), ["role:coder"]);
  assert.deepEqual(
    roles["role:coder"].candidates.map((c) => c.id),
    ["minimax-m3", "deepseek-chat", "gemini-3.5-flash"],
  );
  const bindings = new Set(Object.keys(vendorSecrets({
    SEED_MINIMAX_API_KEY: "m", SEED_DEEPSEEK_API_KEY: "d", SEED_GEMINI_API_KEY: "g",
  })));
  for (const c of roles["role:coder"].candidates) {
    assert.ok(bindings.has(c.apiKeySecretName), `unknown binding ${c.apiKeySecretName}`);
    assert.ok(!/sk-|Bearer /.test(JSON.stringify(c)), "a candidate never carries a secret value");
  }
  // The Worker's own binding names reach the deploy, never the estate's SEED_* names.
  assert.deepEqual(
    workerSecrets({ MERIDIAN_CLIENT_KEY: "c", SEED_GEMINI_API_KEY: "g" }),
    { MERIDIAN_CLIENT_KEY: "c", GEMINI_API_KEY: "g" },
  );
});

test("the pool carries the lane truth this repo records, not a copy of it", () => {
  const { roles } = rolePool();
  const [minimax, deepseek, gemini] = roles["role:coder"].candidates;
  assert.equal(roles["role:coder"].minOutputFloor, MIN_OUTPUT_FLOOR);
  assert.ok(roles["role:coder"].minOutputFloor >= 2048, "wrangler.toml DEFAULT_OUTPUT_FLOOR");
  assert.equal(minimax.baseUrl, "https://api.minimax.io/v1/chat/completions");
  assert.equal(minimax.upstreamModel, "MiniMax-M3");
  assert.equal(minimax.maxContextTokens, 512000);
  assert.equal(minimax.costPer1kInputUsd, 0.0003);
  assert.equal(minimax.costPer1kOutputUsd, 0.0012);
  assert.equal(deepseek.baseUrl, "https://api.deepseek.com/chat/completions");
  assert.equal(deepseek.upstreamModel, "deepseek-chat");
  assert.equal(deepseek.costPer1kInputUsd, 0.00014);
  assert.equal(deepseek.costPer1kOutputUsd, 0.00028);
  assert.equal(gemini.baseUrl, "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions");
  assert.equal(gemini.upstreamModel, "gemini-3.5-flash");
  // "Gemini goes last everywhere and heads nothing" (llm/config.yaml).
  assert.ok(gemini.priority > minimax.priority && gemini.priority > deepseek.priority);
  for (const c of [minimax, deepseek, gemini]) {
    assert.equal(c.maxOutputTokens, 8192);
    assert.equal(c.supportsTools, false, "tool support is a measurement, not an edit");
    assert.equal(c.lane, "edge-direct");
    assert.equal(c.enabled, true);
  }
});

test("seeding the pool is an idempotent PUT that names a refusal and is proved by a read", async () => {
  const payload = rolePool();
  const calls = [];
  const ok = await seedRolePool("https://llm.meridianlabs.cloud", "admin-key", payload, async (url, init) => {
    calls.push({ url, init });
    return new Response(JSON.stringify({ ok: true }), { status: 200 });
  });
  assert.deepEqual(ok, { configured: 1, status: 200 });
  assert.equal(calls[0].url, "https://llm.meridianlabs.cloud/admin/v1/roles");
  assert.equal(calls[0].init.method, "PUT");
  assert.equal(calls[0].init.headers.authorization, "Bearer admin-key");
  assert.deepEqual(Object.keys(JSON.parse(calls[0].init.body).roles), ["role:coder"]);
  // A refused seed is a named failure, not a silent pass: this is how `unknown_role`
  // reached the receipt on run 45675424976.
  await assert.rejects(
    seedRolePool("https://llm.meridianlabs.cloud", "admin-key", payload, async () =>
      new Response('{"error":"unknown_role"}', { status: 404 })),
    /role seed refused 404: \{"error":"unknown_role"\}/,
  );
  // What the router holds is read back, not assumed from a 200 on the PUT.
  const live = await liveRoles("https://llm.meridianlabs.cloud", "admin-key", async (url, init) => {
    assert.equal(init.method, undefined, "a read is a GET");
    assert.equal(init.headers.authorization, "Bearer admin-key");
    return new Response(JSON.stringify({ roles: { "role:coder": { candidates: [] } } }), { status: 200 });
  });
  assert.deepEqual(live, ["role:coder"]);
  await assert.rejects(
    liveRoles("https://llm.meridianlabs.cloud", "k", async () => new Response("{}", { status: 401 })),
    /role read refused 401/,
  );
});

test("the serve window is a budget, not a single look", () => {
  // Run 45685741113 measured the old 3x3s window too short: /health still reported the
  // rollback target after an upload that said ok. The wait is bounded so a stuck deploy
  // fails the release instead of hanging it.
  assert.ok(SERVE_ATTEMPTS >= 5, "at least five looks at /health");
  assert.ok(SERVE_ATTEMPTS * SERVE_PAUSE_MS <= 30_000, "the whole window stays under 30s");
});

test("secrets are set before the pool is seeded, because a version without them refuses the seed", () => {
  // Measured 2026-11-25 (run 45685741113): role seed refused 401 invalid_admin_key because
  // the version answering held no admin key. The script-scoped secret must land first.
  const src = fs.readFileSync(new URL("../scripts/release.mjs", import.meta.url), "utf8");
  const bulkAt = src.indexOf("secretBulkArgs(secretsFile)");
  const seedAt = src.indexOf("seedRolePool(process.env");
  assert.ok(bulkAt > 0, "the release applies script-scoped secrets");
  assert.ok(seedAt > 0, "the release seeds the pool");
  assert.ok(bulkAt < seedAt, "secrets before seed");
});

test("a failed release carries the whole cause, not the first 400 characters of it", () => {
  // The measured receipt of run 45688808353 cut the 503 body mid-JSON, inside the FIRST
  // attempt: the estate could see all_pool_backends_failed and could not see which lane
  // answered 402 and which answered 401. A cause you cannot read is not a receipt.
  const body = 'failed rc=1: {"error":{"type":"all_pool_backends_failed","role":"role:coder","attempts":['
    + '{"backendId":"minimax-m3","status":402,"detail":"insufficient_balance_error"},'
    + '{"backendId":"deepseek-chat","status":401,"detail":"authentication_error"},'
    + '{"backendId":"gemini-3.5-flash","status":500,"detail":"missing_secret_GEMINI_API_KEY"}]}}';
  const e = Object.assign(new Error(body), { detail: body });
  const r = receiptError(e);
  assert.equal(r.error.length, Math.min(400, body.length), "the summary line stays bounded");
  assert.equal(r.error_detail, body);
  for (const lane of ["minimax-m3", "deepseek-chat", "gemini-3.5-flash", "missing_secret_GEMINI_API_KEY"]) {
    assert.ok(r.error_detail.includes(lane), `receipt names ${lane}`);
  }
  // A bounded detail, so a pathological child cannot fill the artifact.
  assert.equal(receiptError(Object.assign(new Error("x"), { detail: "y".repeat(9000) })).error_detail.length, 4000);
  // An error with no detail of its own degrades to its own message.
  assert.equal(receiptError(new Error("plain")).error_detail, "plain");
});

test("a deployment whose own pool failed is kept, not rolled back onto a version that cannot route", () => {
  // Measured 2026-11-25 (run 45691317108): minimax 402, deepseek 401, gemini
  // missing_secret_GEMINI_API_KEY, and the release rolled back to 031b134f, whose post-rollback
  // probe ALSO failed because that version holds no role pool. The surface it restored answers
  // `unknown_role` to every caller, and it defeats the design that a key set out-of-band starts
  // serving with no release.
  const poolFailed = '{"error":{"type":"all_pool_backends_failed","role":"role:coder","attempts":[]}}';
  assert.ok(isAllBackendsFailed(poolFailed));
  assert.equal(shouldRollback({ liveSha: SHA, releasedSha: SHA, probeError: poolFailed }), false);
  assert.equal(shouldRollback({ liveSha: SHA, releasedSha: SHA, probeError: "x " + poolFailed + " y" }), false);
  // The shape the estate ACTUALLY emits: the prober's failure is a JSON string nested inside
  // the line the child printed, so every quote is escaped. Run 45693773697 rolled back because
  // the first version of this matcher only understood the unescaped form.
  const escaped = 'AssertionError: expected 200, got 503: {\"error\":{\"type\":\"all_pool_backends_failed\",'
    + '\"role\":\"role:coder\",\"attempts\":[{\"backendId\":\"minimax-m3\",\"status\":402}]}}\n\n503 !== 200';
  assert.ok(isAllBackendsFailed(escaped), "the escaped body is the measured one");
  assert.equal(shouldRollback({ liveSha: SHA, releasedSha: SHA, probeError: escaped }), false);
  // The deploy being wrong IS a rollback: no answer, or the wrong version answering.
  assert.equal(shouldRollback({ liveSha: null, releasedSha: SHA, probeError: "anything" }), true);
  assert.equal(shouldRollback({ liveSha: "b".repeat(40), releasedSha: SHA, probeError: poolFailed }), true);
  // Any other probe failure with the right version live still rolls back: that is our own
  // defect (auth, payload, 5xx), not a vendor wallet.
  assert.equal(shouldRollback({ liveSha: SHA, releasedSha: SHA, probeError: '{"probe":"auth","status":"FAIL"}' }), true);
  assert.equal(shouldRollback({ liveSha: SHA, releasedSha: SHA, probeError: "" }), false);
});
