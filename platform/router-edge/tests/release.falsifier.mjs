import assert from "node:assert/strict";
import { test } from "node:test";
import {
  activeRollbackId, requireMainSha, immutableTag, pinnedWranglerVersion,
  zoneFromConfig, canonicalRouterUrl, routePattern, resolveZone, scrub,
  classifyPriorDeployments, secretPayload,
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
// The zone is written once. A release that cannot read that one value must refuse to deploy,
// and an environment that contradicts it must be refused rather than preferred.
test("the zone comes from one value and a contradicting environment is refused", () => {
  const config = "data:\n  ESTATE_ZONE: example-zone.test\n  ESTATE_GITHUB_REPO: chidionyema/idp\n";
  assert.equal(zoneFromConfig(config), "example-zone.test");
  assert.equal(canonicalRouterUrl("example-zone.test"), "https://llm.example-zone.test");
  assert.equal(routePattern("example-zone.test"), "llm.example-zone.test/*");
  assert.equal(resolveZone(null, config), "example-zone.test");
  assert.equal(resolveZone("example-zone.test", config), "example-zone.test");
  assert.throws(() => resolveZone("other-zone.test", config), /BLIND/);
  assert.throws(() => zoneFromConfig("data:\n  OTHER: 1\n"), /BLIND/);
  assert.throws(() => canonicalRouterUrl(""), /BLIND/);
});
// First boot is allowed and named; an unknown prior state is refused. The exit code of a CLI is
// not a classifier: the provider is asked, and only an empty deployment list is "first boot".
test("first boot is allowed, an unknown prior state is refused", () => {
  assert.deepEqual(classifyPriorDeployments({ status: 200, result: [] }, ""),
    { mode: "bootstrap", version_id: null, reason: "no_deployments" });
  assert.deepEqual(classifyPriorDeployments({ status: 404 }, ""),
    { mode: "bootstrap", version_id: null, reason: "script_absent" });
  assert.deepEqual(
    classifyPriorDeployments({ status: 200, result: [{ id: A }] }, JSON.stringify({ versions: [{ version_id: A, percentage: 100 }] })),
    { mode: "rollback", version_id: A, reason: "prior_deployment" });
  for (const bad of [
    { status: 403 }, { status: 500 }, { status: 200 }, { status: 200, result: {} }, { status: 200, result: null },
  ]) assert.throws(() => classifyPriorDeployments(bad, ""));
  // A prior deployment whose active version cannot be resolved is not a first boot.
  assert.throws(() => classifyPriorDeployments({ status: 200, result: [{ id: A }] }, JSON.stringify({ versions: [] })), /BLIND/);
  assert.throws(() => classifyPriorDeployments({ status: 200, result: [{ id: A }, { id: B }] },
    JSON.stringify({ versions: [{ version_id: A, percentage: 100 }, { version_id: B, percentage: 100 }] })), /BLIND/);
});
// The receipt is the evidence, so the reason must survive scrubbing and the credential must not.
test("the failure reason is kept and the credential is not", () => {
  const why = scrub("error: token ghp_012345678901234567890123456789012345 refused zone meridianlabs.cloud");
  assert.match(why, /refused zone/);
  assert.doesNotMatch(why, /ghp_012345678901234567890123456789012345/);
  assert.match(scrub("Authorization: Bearer abcdefghijklmnopqrstuvwxyz0123456789"), /\*\*\*/);
  assert.equal(scrub("").length, 0);
});
test("a worker secret is bound by name and type", () => {
  assert.deepEqual(secretPayload("MERIDIAN_CLIENT_KEY", "value"), {
    name: "MERIDIAN_CLIENT_KEY", text: "value", type: "secret_text",
  });
  assert.throws(() => secretPayload("MERIDIAN_CLIENT_KEY", ""), /BLIND/);
  assert.throws(() => secretPayload("", "value"), /BLIND/);
});
