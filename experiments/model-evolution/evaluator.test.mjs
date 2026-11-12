import test from "node:test";
import assert from "node:assert/strict";
import { compareEvolution, auditObservationCoverage } from "./evaluator.mjs";

const hash = "a".repeat(64), alt = "b".repeat(64);
const rows = (pass, taskIds = ["t1", "t2"], arm = "baseline") => taskIds.map((id, i) => ({
  taskId: id, questionSha256: i ? alt : hash, arm, pass,
  attempts: [{ result: { pass }, usage: { total_tokens: 10 }, returnedModel: "model-x" }],
}));
const trial = (basePass, helmPass, ids) => ({
  schema: "helm.trial.v1", model: "model-x",
  results: [...rows(basePass, ids), ...rows(helmPass, ids, "helm")],
});
const old = { provider: "vendor", modelAlias: "model-x", resolvedRevision: "rev-1",
  revisionEvidence: "provider-attested", modelFingerprint: "fingerprint-1",
  methodSha: hash, evaluatorSha: alt, oracleSha: hash, environmentSha: alt,
  agentGeneration: "G1" };
const newer = { ...old, resolvedRevision: "rev-2", modelFingerprint: "fingerprint-2",
  agentGeneration: "G2" };
const compare = (a, b, prev = old, next = newer) => compareEvolution({
  before: a, after: b, beforeIdentity: prev, afterIdentity: next, minTaskPairs: 10,
});

test("provider contribution and our intervention differ in 2-by-2 matched evaluation", () => {
  const before = trial(false, true), after = trial(true, true);
  const report = compare(before, after);
  assert.equal(report.coverage.matchedTasks, 2);
  assert.equal(report.effects.providerWithoutMethods.delta, 1);
  assert.equal(report.effects.methodOld.delta, 1);
  assert.equal(report.effects.methodNew.delta, 0);
  assert.equal(report.effects.interaction.delta, -1);
  assert.equal(report.status, "RESEARCH_DESCRIPTIVE_ONLY");
  assert.equal(report.authorizedToRewardOrDelegate, false);
  assert.equal(report.eligibleForProviderAttribution, false); // N=2, not evidence for promotion
});
test("opaque model alias makes provider-version attribution UNKNOWN", () => {
  const report = compare(trial(false, true), trial(true, true), old,
    { ...newer, revisionEvidence: "self-declared", resolvedRevision: "UNKNOWN" });
  assert.equal(report.providerRevisionComparable, false);
  assert.equal(report.effects.providerWithoutMethods.attributable, false);
  assert.ok(report.gaps.some(x => x.code === "PROVIDER_REVISION_NOT_COMPARABLE"));
});
test("change to HELM method alongside model revision blocks clean attribution", () => {
  const report = compare(trial(false, true), trial(true, true), old,
    { ...newer, methodSha: "d".repeat(64) });
  assert.equal(report.controlsComparable, false);
  assert.ok(report.gaps.some(x => x.code === "METHOD_DRIFT_CONFOUNDS_INTERACTION"));
});
test("missing observations are in the denominator, never counted as zero", () => {
  const before = trial(false, true, ["t1", "t2"]);
  const after = trial(true, true, ["t1"]);
  const r = compare(before, after);
  assert.equal(r.coverage.expectedTasks, 2);
  assert.equal(r.coverage.missingTasks, 1);
  assert.equal(r.coverage.complete, false);
});
test("provider failure or oracle disagreement is not converted to a failed task", () => {
  const before = trial(false, true), after = trial(true, true);
  after.results[0].attempts = [{ error: "rate limited" }];
  const r = compare(before, after);
  assert.equal(r.coverage.missingTasks, 1);
  assert.ok(r.gaps.some(x => x.code === "PROVIDER_OR_EXECUTION_ERROR"));
});
test("different task hashes and duplicate observations cannot contaminate uplift", () => {
  const before = trial(false, true), after = trial(true, true);
  after.results[0].questionSha256 = "0".repeat(64);
  after.results.push({ ...after.results[2] });
  const r = compare(before, after);
  assert.equal(r.coverage.complete, false);
  assert.ok(r.gaps.some(x => x.code === "TASK_HASH_CHANGED_OR_UNKNOWN"));
  assert.ok(r.gaps.some(x => x.code === "DUPLICATE_OBSERVATION"));
});
test("reported token usage is not falsely converted to known billed cost", () => {
  const r = compare(trial(false, true), trial(true, true));
  assert.equal(r.usage.costStatus, "UNKNOWN_NOT_ZERO");
  assert.equal(r.usage.billedCost, null);
});
test("no model can self-certify a missing observation", () => {
  const required = [{ id: "signature", owner: "QUAD" }, { id: "browser", owner: "Genesis" }];
  const seen = [{ id: "signature", verified: true, actor: "agent-a", verifier: "agent-a",
    evidenceSha: hash }];
  const r = auditObservationCoverage(required, seen);
  assert.equal(r.expected, 2);
  assert.equal(r.unobserved, 1);
  assert.equal(r.details[0].status, "OBSERVED_UNVERIFIED");
  assert.equal(r.details[1].status, "MISSING");
});
test("even a distinct-attestor receipt is not misrepresented as cryptographically verified", () => {
  const r = auditObservationCoverage([{ id: "quadevent" }], [{ id: "quadevent",
    verified: true, actor: "agent-a", verifier: "independent", evidenceSha: hash }]);
  assert.equal(r.details[0].status, "ATTESTATION_PRESENT_NOT_CRYPTOGRAPHICALLY_VERIFIED");
});
test("identical provider rev or missing controls precludes provider attribution", () => {
  const r = compare(trial(false, true), trial(true, true), old,
    { ...newer, resolvedRevision: old.resolvedRevision, evaluatorSha: "UNKNOWN" });
  assert.equal(r.providerRevisionComparable, false);
  assert.equal(r.controlsComparable, false);
});
