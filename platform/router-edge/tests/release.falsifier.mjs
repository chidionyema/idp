import assert from "node:assert/strict";
import { test } from "node:test";
import { activeRollbackId, failureCause, firstBootDeployArgs, requireMainSha, immutableTag, pinnedWranglerVersion, uploadArgs, workerSecrets } from "../scripts/release.mjs";
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
