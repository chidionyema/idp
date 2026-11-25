import assert from "node:assert/strict";
import { test } from "node:test";
import { activeRollbackId, failureCause, firstBootDeployArgs, requireMainSha, immutableTag, pinnedWranglerVersion, uploadArgs, workerSecrets } from "../scripts/release.mjs";
import { MIN_OUTPUT_FLOOR, rolePool, seedRolePool, vendorSecrets } from "../scripts/role-pool.mjs";
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
test("a first boot deploys, because only deploy may create a Durable Object class", () => {
  const args = firstBootDeployArgs(SHA, immutableTag(SHA));
  assert.equal(args[0], "deploy", "first boot must use `wrangler deploy`");
  assert.ok(!args.includes("--keep-vars"));
  assert.ok(args.includes("--strict"));
  assert.ok(args.includes("COMMIT_SHA:" + SHA));
  assert.ok(args.includes(immutableTag(SHA)));
  assert.ok(!args.includes("--secrets-file"), "no secret file, no flag");
  const withSecrets = firstBootDeployArgs(SHA, immutableTag(SHA), "/tmp/w.json");
  assert.deepEqual(withSecrets.slice(-2), ["--secrets-file", "/tmp/w.json"]);
});
test("the Worker is given its own keys, because a deploy never carries them", () => {
  assert.deepEqual(
    workerSecrets({ MERIDIAN_CLIENT_KEY: "c", MERIDIAN_ADMIN_KEY: "a", PATH: "/bin" }),
    { MERIDIAN_CLIENT_KEY: "c", MERIDIAN_ADMIN_KEY: "a" },
  );
  assert.deepEqual(workerSecrets({ MERIDIAN_CLIENT_KEY: "c" }), { MERIDIAN_CLIENT_KEY: "c" });
  assert.deepEqual(workerSecrets({}), {});
  const args = uploadArgs(SHA, immutableTag(SHA), true, "/tmp/w.json");
  assert.deepEqual(args.slice(-3), ["--secrets-file", "/tmp/w.json", "--strict"]);
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

test("a role is never offered for a vendor the Worker holds no key for", () => {
  const both = rolePool({ SEED_MINIMAX_API_KEY: "m", SEED_DEEPSEEK_API_KEY: "d" });
  assert.deepEqual(Object.keys(both.roles), ["role:coder"]);
  assert.deepEqual(both.roles["role:coder"].candidates.map((c) => c.id), ["minimax-m3", "deepseek-chat"]);
  const only = rolePool({ SEED_MINIMAX_API_KEY: "m" });
  assert.deepEqual(only.roles["role:coder"].candidates.map((c) => c.id), ["minimax-m3"]);
  // No key at all is an empty pool, never a pool of guarantees: the refusal the edge gives
  // (`unknown_role`) is honest, a 502 from a lane with no credential is not.
  assert.deepEqual(rolePool({}), { roles: {} });
  assert.deepEqual(vendorSecrets({ SEED_DEEPSEEK_API_KEY: "d" }), { DEEPSEEK_API_KEY: "d" });
  // The Worker's own binding names, never the estate's SEED_* names, reach the deploy.
  assert.deepEqual(
    workerSecrets({ MERIDIAN_CLIENT_KEY: "c", SEED_MINIMAX_API_KEY: "m" }),
    { MERIDIAN_CLIENT_KEY: "c", MINIMAX_API_KEY: "m" },
  );
});

test("the pool carries the lane truth this repo records, not a copy of it", () => {
  const { roles } = rolePool({ SEED_MINIMAX_API_KEY: "m", SEED_DEEPSEEK_API_KEY: "d" });
  const [minimax, deepseek] = roles["role:coder"].candidates;
  assert.equal(roles["role:coder"].minOutputFloor, MIN_OUTPUT_FLOOR);
  assert.ok(roles["role:coder"].minOutputFloor >= 2048, "wrangler.toml DEFAULT_OUTPUT_FLOOR");
  assert.equal(minimax.baseUrl, "https://api.minimax.io/v1/chat/completions");
  assert.equal(minimax.upstreamModel, "MiniMax-M3");
  assert.equal(minimax.maxContextTokens, 512000);
  assert.equal(minimax.costPer1kInputUsd, 0.0003);
  assert.equal(minimax.costPer1kOutputUsd, 0.0012);
  assert.equal(deepseek.baseUrl, "https://api.deepseek.com/chat/completions");
  assert.equal(deepseek.upstreamModel, "deepseek-chat");
  assert.equal(deepseek.maxContextTokens, 65536);
  assert.equal(deepseek.costPer1kInputUsd, 0.00014);
  assert.equal(deepseek.costPer1kOutputUsd, 0.00028);
  for (const c of [minimax, deepseek]) {
    assert.equal(c.apiKeySecretName, c.apiKeySecretName.toUpperCase(), "binding name, not a key");
    assert.ok(!/sk-|Bearer /.test(JSON.stringify(c)), "a candidate never carries a secret value");
    assert.equal(c.maxOutputTokens, 8192);
    assert.equal(c.supportsTools, false, "tool support is a measurement, not an edit");
    assert.equal(c.lane, "edge-direct");
    assert.equal(c.enabled, true);
  }
});

test("seeding the pool is an idempotent PUT that names a refusal", async () => {
  const payload = rolePool({ SEED_MINIMAX_API_KEY: "m" });
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
  // Nothing to seed is not a call.
  let touched = false;
  const empty = await seedRolePool("https://llm.meridianlabs.cloud", "k", rolePool({}), async () => {
    touched = true;
    return new Response("{}", { status: 200 });
  });
  assert.deepEqual(empty, { configured: 0, status: 0, skipped: "no vendor key held" });
  assert.equal(touched, false);
});
