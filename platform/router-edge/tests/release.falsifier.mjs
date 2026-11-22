import assert from "node:assert/strict";
import { test } from "node:test";
import { activeRollbackId, requireMainSha, immutableTag } from "../scripts/release.mjs";
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
});
