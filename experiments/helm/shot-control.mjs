/**
 * HELM / founder-configured LOCAL degrees of freedom, not a second executor.
 *
 * This pure deterministic controller is an admission barrier around a model's
 * *proposed* actions. The authorised IDP intent executor remains the only path
 * allowed to mutate code or call git. One action is one complete candidate.
 *
 * Protocol:
 *   ADMIT -> PROBE (once) -> [SHOT -> GRADE] x [1..10] -> terminal.
 *   Additional probes, speculative writes, overruns and model self-grading
 *   are hard refused. No implicit restart after exhaustion.
 *
 * Persistent owner: caller stores the event sequence against the existing
 * Argon instruction_id in its authoritative database. A snapshot alone is not
 * an ACID ledger; no claim of cross-process atomicity or production adoption.
 */
import { createHash } from "node:crypto";

const ID = /^[A-Za-z0-9._-]{3,100}$/; // Argon ProvenanceLedger identity contract
const HEX = /^[0-9a-f]{64}$/;
const KINDS = new Set(["PROBE", "SHOT", "GRADE"]);
const digest = value => createHash("sha256").update(
  typeof value === "string" ? value : JSON.stringify(value)
).digest("hex");

function refuse(reason) {
  const error = new Error("HELM_REFUSED: " + reason);
  error.code = "HELM_REFUSED";
  throw error;
}

export function shotPolicy({ instructionId, taskDigest, sourceSha, model,
  shots = 1, profile = "helmet", verifier = "independent-oracle" } = {}) {
  if (typeof instructionId !== "string" || !ID.test(instructionId))
    refuse("invalid canonical instruction_id");
  if (typeof taskDigest !== "string" || !HEX.test(taskDigest))
    refuse("task digest missing or malformed");
  if (typeof sourceSha !== "string" || !/^[0-9a-f]{7,64}$/.test(sourceSha))
    refuse("pinned source SHA required");
  if (typeof model !== "string" || !model.trim())
    refuse("model identity required");
  if (!Number.isInteger(shots) || shots < 1 || shots > 10)
    refuse("founder shot budget must be integer 1..10");
  if (!["helmet", "control"].includes(profile))
    refuse("unknown experimental arm");
  if (!ID.test(verifier) || verifier === model)
    refuse("distinct verifier identity required");
  return Object.freeze({
    schema: "helm.shot-policy.v1", instructionId, taskDigest,
    sourceSha, model, shots, profile, verifier,
    maxContextProbes: 1,
    maxCompleteCandidateSubmissions: shots,
    grantsExecutionAuthority: false
  });
}

export function initialShotState(policy) {
  if (policy?.schema !== "helm.shot-policy.v1")
    refuse("HELM policy missing");
  return {
    schema: "helm.shot-state.v1", instructionId: policy.instructionId,
    policyDigest: digest(policy), phase: "NEEDS_PROBE",
    probes: 0, shots: 0, grades: 0, pass: false,
    currentShot: null, events: [], head: "0".repeat(64)
  };
}

function validateEventBase(policy, state, event) {
  if (!event || typeof event !== "object" || Array.isArray(event))
    refuse("typed action event required");
  if (event.instructionId !== policy.instructionId)
    refuse("wrong instruction_id");
  if (!KINDS.has(event.kind)) refuse("invalid opcode; no raw shell execution");
  if (typeof event.eventId !== "string" || !ID.test(event.eventId))
    refuse("eventId required for deterministic retry");
  const allowed = {
    PROBE: ["kind","eventId","instructionId","probeDigest","sourceSha"],
    SHOT: ["kind","eventId","instructionId","candidateDigest","opcode","model"],
    GRADE: ["kind","eventId","instructionId","candidateDigest","passed","verifier","evidenceDigest"]
  }[event.kind];
  if (Object.keys(event).some(key => !allowed.includes(key)))
    refuse("undeclared action attribute");
  if (state.policyDigest !== digest(policy))
    refuse("policy mutation or wrong instance");
  if (state.instructionId !== policy.instructionId)
    refuse("ledger identity mismatch");
}

export function advanceShot(policy, snapshot, event) {
  // Derive state from stored events. No process-local counter is authoritative.
  const state = replayShots(policy, snapshot?.events || []);
  validateEventBase(policy, state, event);
  const prior = state.events.find(e => e.eventId === event.eventId);
  if (prior) {
    const { chain, sequence, ...original } = prior;
    if (JSON.stringify(original) !== JSON.stringify(event))
      refuse("idempotency key reused with different payload");
    return state; // byte-identical retry consumes no budget
  }
  if (state.phase === "VERIFIED" || state.phase === "EXHAUSTED")
    refuse("terminal instruction is not restartable");
  const next = apply(policy, state, event);
  const row = {
    ...event, sequence: state.events.length + 1,
    chain: digest(state.head + "|" + JSON.stringify(event))
  };
  return {
    ...next, events: [...state.events, row], head: row.chain
  };
}

function apply(policy, state, event) {
  if (event.kind === "PROBE") {
    if (state.phase !== "NEEDS_PROBE" || state.probes >= 1)
      refuse("one context probe only; no repeated discovery");
    if (!HEX.test(event.probeDigest) || event.sourceSha !== policy.sourceSha)
      refuse("probe must be bound to exact source and hash");
    return { ...state, probes: 1, phase: "READY" };
  }
  if (event.kind === "SHOT") {
    if (state.phase !== "READY")
      refuse("a complete shot needs one prior context probe and graded predecessor");
    if (state.shots >= policy.shots)
      refuse("founder shot ceiling reached");
    if (!HEX.test(event.candidateDigest))
      refuse("complete candidate digest required");
    if (event.model !== policy.model)
      refuse("unregistered model substituted");
    if (!["EMIT_PATCH","RUN_FALSIFIER","DISPATCH_LEGION","SUBMIT_YIELD"].includes(event.opcode))
      refuse("model asked for unregistered executor operation");
    return {
      ...state, phase: "AWAITING_GRADE", shots: state.shots + 1,
      currentShot: { digest: event.candidateDigest, opcode: event.opcode }
    };
  }
  if (state.phase !== "AWAITING_GRADE")
    refuse("cannot grade without one pending candidate");
  if (event.candidateDigest !== state.currentShot?.digest)
    refuse("independent grade must reference exact candidate bytes");
  if (event.verifier !== policy.verifier || event.verifier === policy.model)
    refuse("agent cannot self-certify yield");
  if (typeof event.passed !== "boolean" || !HEX.test(event.evidenceDigest))
    refuse("independent verifier needs explicit verdict and evidence digest");
  const grades = state.grades + 1;
  const phase = event.passed ? "VERIFIED" :
    state.shots === policy.shots ? "EXHAUSTED" : "READY";
  return {
    ...state, grades, phase, pass: event.passed,
    currentShot: null
  };
}

/** Replay is the source of truth; reject modified, reordered, or missing events. */
export function replayShots(policy, events) {
  let state = initialShotState(policy);
  if (!Array.isArray(events)) refuse("event journal is missing");
  const seen = new Set();
  for (const entry of events) {
    const { chain, sequence, ...event } = entry || {};
    validateEventBase(policy, state, event);
    if (seen.has(event.eventId)) refuse("duplicate stored event ID");
    if (sequence !== state.events.length + 1)
      refuse("journal sequence gap");
    if (chain !== digest(state.head + "|" + JSON.stringify(event)))
      refuse("journal integrity mismatch");
    const next = apply(policy, state, event);
    seen.add(event.eventId);
    state = {
      ...next, events: [...state.events, entry], head: chain
    };
  }
  return state;
}

export function shotReport(policy, state) {
  const s = replayShots(policy, state.events);
  return {
    schema: "helm.shot-receipt.v1",
    instructionId: s.instructionId,
    policyDigest: s.policyDigest,
    chainHead: s.head,
    profile: policy.profile,
    shotCeiling: policy.shots,
    contextProbes: s.probes,
    candidateSubmissions: s.shots,
    independentlyGraded: s.grades,
    remaining: policy.shots - s.shots,
    status: s.phase,
    passedFixtureOracle: s.pass,
    liveExecutionVerified: false,
    claimsProductionDeployment: false
  };
}

export { digest as helmDigest };
