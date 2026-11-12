/**
 * Read-only scientific projection over existing HELM trial receipts.
 * No memory store, model training, authority grant or runtime action.
 * A model alias is never an immutable provider revision without independent provenance.
 */
const ARMS = ["baseline", "skills", "memory", "helm"];
const VALID_REVISION = "provider-attested";
const isHash = value => typeof value === "string" && /^[0-9a-f]{40,64}$/i.test(value);
const mean = xs => xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null;

function validateTrial(trial, label) {
  if (trial?.schema !== "helm.trial.v1" || !Array.isArray(trial.results)) {
    throw new Error(label + ": expected existing HELM trial receipts");
  }
}
function identity(input) {
  return {
    provider: input.provider || "UNKNOWN",
    alias: input.modelAlias || "UNKNOWN",
    resolvedRevision: input.resolvedRevision || "UNKNOWN",
    revisionEvidence: input.revisionEvidence || "UNKNOWN",
    fingerprint: input.modelFingerprint || "UNKNOWN",
    methodSha: input.methodSha || "UNKNOWN",
    evaluatorSha: input.evaluatorSha || "UNKNOWN",
    oracleSha: input.oracleSha || "UNKNOWN",
    environmentSha: input.environmentSha || "UNKNOWN",
    observedAt: input.observedAt || null,
    recordedAt: input.recordedAt || null,
    agentGeneration: input.agentGeneration || "UNKNOWN",
  };
}
function indexed(trial, side, gaps) {
  const map = new Map();
  for (const row of trial.results) {
    const key = String(row.taskId || "") + "::" + String(row.arm || "");
    if (!row.taskId || !ARMS.includes(row.arm)) {
      gaps.push({ code: "INVALID_TRIAL_ROW", side, key });
      continue;
    }
    if (map.has(key)) {
      gaps.push({ code: "DUPLICATE_OBSERVATION", side, key });
      map.set(key, null);
      continue;
    }
    const attempts = Array.isArray(row.attempts) ? row.attempts : [];
    const last = attempts.at(-1);
    let outcome = "UNKNOWN";
    if (last && !last.error && typeof last.result?.pass === "boolean" &&
        typeof row.pass === "boolean" && last.result.pass === row.pass) {
      outcome = row.pass ? "PASS" : "FAIL";
    } else {
      gaps.push({ code: last?.error ? "PROVIDER_OR_EXECUTION_ERROR" :
        "MISSING_OR_CONFLICTING_ORACLE", side, key });
    }
    map.set(key, {
      taskId: row.taskId,
      arm: row.arm,
      taskHash: row.questionSha256 || "UNKNOWN",
      outcome,
      source: row.source || "UNKNOWN",
      returnedModels: [...new Set(attempts.map(a => a.returnedModel).filter(Boolean))],
      attempts: attempts.length,
      tokens: attempts.reduce((n, a) => n + (Number.isFinite(a.usage?.total_tokens) ?
        a.usage.total_tokens : 0), 0),
      usageComplete: attempts.every(a => Number.isFinite(a.usage?.total_tokens)),
    });
  }
  return map;
}
function pairedCI(values) {
  // Deterministic nonparametric paired bootstrap; descriptive, not a permission to reward.
  if (values.length < 10) return null;
  let state = 0x9e3779b9;
  const next = () => { state ^= state << 13; state ^= state >>> 17;
    state ^= state << 5; return (state >>> 0) / 4294967296; };
  const samples = [];
  for (let b = 0; b < 1000; b++) {
    let total = 0;
    for (let j = 0; j < values.length; j++) {
      total += values[Math.floor(next() * values.length)];
    }
    samples.push(total / values.length);
  }
  samples.sort((a, b) => a - b);
  return { low: samples[24], high: samples[974], method: "paired-bootstrap-1000" };
}
function effect(xs) {
  return { delta: mean(xs), taskPairs: xs.length, ci95: pairedCI(xs) };
}

/** One before/after contrast on the same independently graded task identities. */
export function compareEvolution({ before, after, beforeIdentity, afterIdentity,
  minTaskPairs = 20 }) {
  validateTrial(before, "before");
  validateTrial(after, "after");
  if (!Number.isSafeInteger(minTaskPairs) || minTaskPairs < 10) {
    throw new Error("minimum scientific cohort must contain at least 10 matched tasks");
  }
  const older = identity(beforeIdentity || {});
  const newer = identity(afterIdentity || {});
  const gaps = [];
  const controls = ["provider", "alias", "evaluatorSha", "oracleSha", "environmentSha"];
  for (const field of controls) {
    if (older[field] === "UNKNOWN" || newer[field] === "UNKNOWN" ||
        older[field] !== newer[field]) {
      gaps.push({ code: "CONTROL_UNRESOLVED_OR_CHANGED", field });
    }
  }
  if (older.methodSha === "UNKNOWN" || newer.methodSha === "UNKNOWN" ||
      older.methodSha !== newer.methodSha) {
    gaps.push({ code: "METHOD_DRIFT_CONFOUNDS_INTERACTION" });
  }
  const revisionComparable = older.revisionEvidence === VALID_REVISION &&
    newer.revisionEvidence === VALID_REVISION &&
    older.resolvedRevision !== "UNKNOWN" && newer.resolvedRevision !== "UNKNOWN" &&
    older.resolvedRevision !== newer.resolvedRevision &&
    older.fingerprint !== "UNKNOWN" && newer.fingerprint !== "UNKNOWN";
  if (!revisionComparable) gaps.push({ code: "PROVIDER_REVISION_NOT_COMPARABLE" });
  const b = indexed(before, "before", gaps);
  const a = indexed(after, "after", gaps);
  const taskIds = new Set([...b.keys(), ...a.keys()].map(x => x.split("::")[0]));
  const deltas = { providerWithoutMethods: [], methodOld: [], methodNew: [],
    interaction: [], combined: [], skillsOld: [], memoryOld: [] };
  let complete = 0, missing = 0, tokenComplete = true, observedTokens = 0;
  for (const taskId of [...taskIds].sort()) {
    const keys = ["baseline", "helm"];
    const br = keys.map(arm => b.get(taskId + "::" + arm));
    const ar = keys.map(arm => a.get(taskId + "::" + arm));
    const four = [...br, ...ar];
    // Collect every independently observable defect, even when a separate
    // duplicate makes another cell unavailable for the factorial comparison.
    if (br[0]?.taskHash && ar[0]?.taskHash &&
        (br[0].taskHash !== ar[0].taskHash || br[0].taskHash === "UNKNOWN")) {
      gaps.push({ code: "TASK_HASH_CHANGED_OR_UNKNOWN", taskId });
    }
    if (four.some(row => !row || row.outcome === "UNKNOWN")) {
      missing++;
      gaps.push({ code: "MISSING_MATCHED_TASK_OR_VERDICT", taskId });
      continue;
    }
    if (new Set(four.map(x => x.taskHash)).size !== 1 ||
        four[0].taskHash === "UNKNOWN") {
      missing++;
      gaps.push({ code: "TASK_HASH_CHANGED_OR_UNKNOWN", taskId });
      continue;
    }
    complete++;
    const [bo, bh, ao, ah] = four.map(x => x.outcome === "PASS" ? 1 : 0);
    deltas.providerWithoutMethods.push(ao - bo);
    deltas.methodOld.push(bh - bo);
    deltas.methodNew.push(ah - ao);
    deltas.interaction.push((ah - ao) - (bh - bo));
    deltas.combined.push(ah - bo);
    for (const row of four) {
      observedTokens += row.tokens;
      tokenComplete &&= row.usageComplete;
    }
    for (const [arm, key] of [["skills", "skillsOld"], ["memory", "memoryOld"]]) {
      const candidate = b.get(taskId + "::" + arm);
      if (candidate?.outcome !== "UNKNOWN" &&
          candidate?.taskHash === four[0].taskHash) {
        deltas[key].push(Number(candidate.outcome === "PASS") - bo);
      }
    }
  }
  const completeCoverage = taskIds.size > 0 && complete === taskIds.size &&
    !gaps.some(x => ["DUPLICATE_OBSERVATION", "INVALID_TRIAL_ROW",
      "PROVIDER_OR_EXECUTION_ERROR", "MISSING_OR_CONFLICTING_ORACLE"].includes(x.code));
  const comparableEnvironment = !gaps.some(x =>
    ["CONTROL_UNRESOLVED_OR_CHANGED", "METHOD_DRIFT_CONFOUNDS_INTERACTION"].includes(x.code));
  const sampleAdequate = complete >= minTaskPairs;
  // This scientific projection does NOT verify the provider attestor or
  // QUAD evidence signatures; a supplied string must never mint credit.
  // Comparability is only a research candidate, not verified causality.
  const candidateForProviderAttribution = revisionComparable && completeCoverage &&
    comparableEnvironment && sampleAdequate;
  const eligibleForProviderAttribution = false;
  const effects = Object.fromEntries(Object.entries(deltas).map(([k, v]) => [k, effect(v)]));
  effects.providerWithoutMethods = { ...effects.providerWithoutMethods,
    attributable: false, researchComparable: candidateForProviderAttribution };
  effects.interaction = { ...effects.interaction,
    attributable: false, researchComparable: candidateForProviderAttribution };
  return {
    schema: "estate.science.model-evolution.v1",
    status: "RESEARCH_DESCRIPTIVE_ONLY",
    authorizedToRewardOrDelegate: false,
    before: older, after: newer,
    coverage: { expectedTasks: taskIds.size, matchedTasks: complete, missingTasks: missing,
      complete: completeCoverage, sampledAdequately: sampleAdequate },
    controlsComparable: comparableEnvironment,
    providerRevisionComparable: revisionComparable,
    candidateForProviderAttribution,
    eligibleForProviderAttribution,
    effects,
    usage: { tokens: tokenComplete && complete > 0 ? observedTokens : null,
      status: tokenComplete && complete > 0 ? "MEASURED" : "UNKNOWN",
      billedCost: null, costStatus: "UNKNOWN_NOT_ZERO" },
    gaps,
    scientificNextStep: "Independent signed source/evaluator receipts, held-out replicated trials and live outcomes are required for causal or reward claims.",
  };
}

/** Required observations are an explicit denominator; missing is never zero. */
export function auditObservationCoverage(expected, observed) {
  if (!Array.isArray(expected) || !Array.isArray(observed)) throw new Error("invalid observations");
  const emitted = new Map();
  for (const row of observed) {
    if (!row?.id) continue;
    const bucket = emitted.get(row.id) || [];
    bucket.push(row);
    emitted.set(row.id, bucket);
  }
  const details = expected.map(item => {
    const records = emitted.get(item.id) || [];
    let status = "MISSING";
    if (records.length > 1) status = "DUPLICATE_REQUIRES_RECONCILIATION";
    else if (records.length === 1 && records[0].verified === true &&
             records[0].verifier && records[0].verifier !== records[0].actor &&
             isHash(records[0].evidenceSha)) status = "ATTESTATION_PRESENT_NOT_CRYPTOGRAPHICALLY_VERIFIED";
    else if (records.length === 1) status = "OBSERVED_UNVERIFIED";
    return { id: item.id, status, owner: item.owner || "UNKNOWN" };
  });
  return { expected: expected.length, observed: details.filter(x => x.status !== "MISSING").length,
    unobserved: details.filter(x => x.status === "MISSING").length, details,
    guarantees: "Read-only observation assessment; QUAD authenticates external receipts." };
}
