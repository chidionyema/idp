/**
 * TRIAD v1 — guided analogy, misconception correction and novel transfer.
 * Pure, private-by-default research engine. No storage, network, identity,
 * external LLM judge, inferred mastery or authority to write production state.
 */
import { getLesson } from './lesson.mjs';

export const ARMS = Object.freeze(['canonical', 'single', 'triad']);
export const PILOT_VERSION = 'triad-adaptive-1.0.0';

const ITEMS = Object.freeze({
  diagnostic: [
    { id: 'd-key', skill: 'dependency', prompt: 'A signed photo archive has every file and its metadata, but its only decryption key is lost. Can the images be recovered exactly?', choices: ['Yes, signatures generate missing secrets.', 'Only if an authorised key or equivalent trusted plaintext is recovered.', 'Yes, because the storage was complete.', 'Yes, because a restoration script runs.'], correct: 1, explanation: 'Cryptographic signatures verify origin, not decryption capability.' },
    { id: 'd-api', skill: 'external-input', prompt: 'A simulation recorded its commands but not the historical weather readings it consumed. Can the original state always be replayed?', choices: ['Yes, commands capture all inputs.', 'Yes, if the model can invent typical weather.', 'No; the original readings or equivalent authenticated inputs are required.', 'Yes, if the latest reading is available.'], correct: 2, explanation: 'Mutable external facts must be captured to reproduce their historical effects.' },
  ],
  transfer: [
    { id: 't-ledger', skill: 'history', prompt: 'A cooperative bank has software, keys, and a checkpoint from Monday. It lost Tuesday’s transaction events but has Wednesday’s. Can it guarantee Wednesday’s exact balances?', choices: ['Yes, Wednesday events fill missing Tuesday events.', 'No; missing changes prevent guaranteed exact reconstruction.', 'Yes, when the program builds cleanly.', 'Yes, because an old checkpoint is signed.'], correct: 1, explanation: 'A complete ordered history after the checkpoint is required; newer events cannot reconstruct arbitrary earlier changes.' },
    { id: 't-rate', skill: 'external-input', prompt: 'An international payment engine retained all transaction events but did not store historical exchange-rate API responses. Can it guarantee original totals?', choices: ['Yes, transaction events imply exchange rates.', 'Yes, the current API is equivalent.', 'No; historical external values or equivalent authenticated inputs are missing.', 'Yes, if two replicas agree on a number.'], correct: 2, explanation: 'An external changing API contributes information absent from the event log.' },
    { id: 't-split', skill: 'reconciliation', prompt: 'Two authorised warehouse replicas restart from the same checkpoint, then each accepts different stock updates while disconnected. What is needed before claiming a single correct state?', choices: ['Only a matching original checkpoint.', 'Only a green recovery dashboard.', 'Nothing; both updates can be discarded.', 'Reconcile both histories under agreed authority and verify resulting effects independently.'], correct: 3, explanation: 'Common ancestry does not eliminate divergent writes, conflicts or side effects.' },
  ],
  retest: {
    history: { id: 'r-history', skill: 'history', prompt: 'A digital museum restorer has a verified painting scan from June and every edit after August, but July edits disappeared. What is the honest restoration claim?', choices: ['The exact August state is always regenerable.', 'A complete historical reconstruction is unproven unless the missing edits or a later trusted state are recovered.', 'Two artists agreeing proves exactness.', 'The oldest scan always supersedes missing changes.'], correct: 1, explanation: 'An unknown historical segment blocks exact reconstruction without a later trusted checkpoint.' },
    'external-input': { id: 'r-external', skill: 'external-input', prompt: 'A navigation system logged decisions, but not the changing traffic feed used to make them. What would enable a reproducible historical replay?', choices: ['Any new traffic feed.', 'A sufficiently expressive metaphor.', 'The original authenticated feed observations or equivalent captured inputs.', 'A copy of the code alone.'], correct: 2, explanation: 'Historical inputs must be captured rather than guessed from later outcomes.' },
    reconciliation: { id: 'r-reconcile', skill: 'reconciliation', prompt: 'Two rescue drones process different authorised commands while offline. They reconnect with the same initial software. What is necessary before claiming one reliable combined mission log?', choices: ['Correctly ordered conflict resolution, authority checks and independent readback of real effects.', 'Only the drones sharing model weights.', 'One drone reporting mission complete.', 'Discarding one log without checking effects.'], correct: 0, explanation: 'Multiple authorised histories and physical side effects require reconciliation, not merely shared software.' },
    dependency: { id: 'r-dependency', skill: 'dependency', prompt: 'A restored service contains all encrypted database bytes and versioned software but lacks the sole authorised decrypting secret. What can be proven?', choices: ['The service necessarily holds all readable records.', 'Readable records remain unproven without the secret or equivalent trusted plaintext.', 'A previous health check restores access.', 'Software replay recreates arbitrary passwords.'], correct: 1, explanation: 'Missing keys or authority are not generated by source code or storage.' },
  },
});

function clone(x) { return structuredClone(x); }
function assertSession(s) {
  if (!s || s.version !== PILOT_VERSION || !ARMS.includes(s.arm) ||
      !['diagnostic', 'teach', 'transfer', 'remediation', 'retest', 'complete'].includes(s.phase) ||
      !Array.isArray(s.answers) || s.answers.length > 6) {
    throw new TypeError('Invalid TRIAD research session');
  }
  let expectedRetest = null;
  for (let i = 0; i < s.answers.length; i++) {
    const a = s.answers[i];
    const expectedPhase = i < 2 ? 'diagnostic' : i < 5 ? 'transfer' : 'retest';
    if (!a || a.phase !== expectedPhase) throw new TypeError('Invalid assessment ordering');
    if (i === 5) {
      expectedRetest = s.answers.slice(2, 5).find(v => !v.correct)?.skill;
      if (!expectedRetest || s.retestSkill !== expectedRetest) throw new TypeError('Forged or unneeded retest');
    }
    const item = i < 2 ? ITEMS.diagnostic[i] : i < 5 ? ITEMS.transfer[i - 2] : ITEMS.retest[expectedRetest];
    if (!item || a.itemId !== item.id || a.skill !== item.skill ||
        !Number.isInteger(a.choice) || a.choice < 0 || a.choice >= item.choices.length ||
        a.correct !== (a.choice === item.correct) ||
        typeof a.confidence !== 'number' || !Number.isFinite(a.confidence) ||
        a.confidence < 0 || a.confidence > 1) {
      throw new TypeError('Tampered, duplicated or invalid assessment record');
    }
  }
  const n = s.answers.length;
  if ((n < 2 && s.phase !== 'diagnostic') ||
      (n === 2 && !['teach', 'transfer'].includes(s.phase)) ||
      (n > 2 && n < 5 && s.phase !== 'transfer') ||
      (n === 5 && s.answers.slice(2,5).every(a=>a.correct) && s.phase !== 'complete') ||
      (n === 5 && s.answers.slice(2,5).some(a=>!a.correct) && !['remediation','retest'].includes(s.phase)) ||
      (n === 6 && s.phase !== 'complete')) {
    throw new TypeError('Forged or inconsistent assessment lifecycle');
  }
  if (n >= 5) {
    const shouldRetest = s.answers.slice(2,5).find(a => !a.correct)?.skill || null;
    if (s.retestSkill !== shouldRetest) throw new TypeError('Incorrect remediation target');
  } else if (s.retestSkill !== null) throw new TypeError('Premature remediation target');
}
function safeQuestion(q) {
  const { id, skill, prompt, choices } = q;
  return { id, skill, prompt, choices: [...choices] };
}
function questionFor(s) {
  if (s.phase === 'diagnostic' || s.phase === 'transfer') {
    const attempts = s.answers.filter(a => a.phase === s.phase).length;
    return ITEMS[s.phase][attempts] || null;
  }
  if (s.phase === 'retest') return ITEMS.retest[s.retestSkill] || null;
  return null;
}
function wrongSkills(s) {
  return s.answers.filter(a => a.phase === 'transfer' && !a.correct).map(a => a.skill);
}
function personalisedCorrection(skill) {
  const text = {
    history: {
      analogy: 'Film editing',
      explanation: 'A film project with the opening scene and the final scene still cannot reproduce missing middle edits. You need the edits or a trusted later export.',
      limit: 'The film metaphor does not account for digital signatures or live external dependencies.',
    },
    'external-input': {
      analogy: 'Cooking',
      explanation: 'A recipe and a log of the cook’s actions cannot recreate the exact meal if ingredient quantities and temperatures were never recorded.',
      limit: 'Real cooking is not deterministic and cannot guarantee bit-identical outcomes.',
    },
    reconciliation: {
      analogy: 'Two authors',
      explanation: 'Two authors start from the same manuscript and make different edits. Combining their work requires identifying conflicts and agreeing which changes survive.',
      limit: 'Software conflicts can include irreversible real-world side effects, unlike a document edit.',
    },
    dependency: {
      analogy: 'Locked vault',
      explanation: 'A complete map of a vault and an inventory of its contents do not reveal a lost combination. The instructions never contained that secret.',
      limit: 'Some lawful recovery methods may exist, but they require new authenticated evidence or access.',
    },
  };
  return clone(text[skill] || text.history);
}

export function startSession({ arm = 'triad', sessionId = 'anonymous-local' } = {}) {
  if (!ARMS.includes(arm)) throw new TypeError('Unknown experimental arm');
  if (typeof sessionId !== 'string' || !/^[a-zA-Z0-9._-]{1,64}$/.test(sessionId)) throw new TypeError('Invalid local session identifier');
  return { version: PILOT_VERSION, sessionId, arm, phase: 'diagnostic', answers: [], retestSkill: null, startedAt: null, externalVerifier: null };
}

export function currentView(session) {
  assertSession(session);
  const base = { phase: session.phase, arm: session.arm, version: PILOT_VERSION, lessonId: getLesson().id, verifiedLearningGain: null };
  const q = questionFor(session);
  if (q) return { ...base, question: safeQuestion(q), step: session.answers.filter(a => a.phase === session.phase).length + 1, total: session.phase === 'diagnostic' ? ITEMS.diagnostic.length : session.phase === 'transfer' ? ITEMS.transfer.length : 1 };
  if (session.phase === 'teach') {
    const lesson = getLesson();
    const count = session.arm === 'canonical' ? 0 : session.arm === 'single' ? 1 : 2;
    return { ...base, canonical: clone(lesson.target), analogies: clone(lesson.analogies.slice(0, count)), sharedCore: lesson.sharedCore, action: 'advance' };
  }
  if (session.phase === 'remediation') return { ...base, missedSkills: wrongSkills(session), correction: personalisedCorrection(session.retestSkill), action: 'advance' };
  return { ...base, action: 'review', summary: getReport(session) };
}

export function submitChoice(session, { itemId, choice, confidence = 0.5 } = {}) {
  assertSession(session);
  if (!['diagnostic', 'transfer', 'retest'].includes(session.phase)) throw new Error('No active assessment question');
  const q = questionFor(session);
  if (!q || itemId !== q.id) throw new Error('Out-of-sequence, unknown or reused question');
  if (!Number.isInteger(choice) || choice < 0 || choice >= q.choices.length) throw new TypeError('Invalid response choice');
  if (typeof confidence !== 'number' || !Number.isFinite(confidence) || confidence < 0 || confidence > 1) throw new TypeError('Confidence must be between 0 and 1');
  const s = clone(session);
  const phase = s.phase;
  s.answers.push({ phase, itemId, skill: q.skill, choice, correct: choice === q.correct, confidence });
  if (phase === 'diagnostic' && s.answers.filter(a => a.phase === 'diagnostic').length >= ITEMS.diagnostic.length) s.phase = 'teach';
  if (phase === 'transfer' && s.answers.filter(a => a.phase === 'transfer').length >= ITEMS.transfer.length) {
    const missed = wrongSkills(s);
    s.retestSkill = missed[0] || null;
    s.phase = missed.length ? 'remediation' : 'complete';
  }
  if (phase === 'retest') s.phase = 'complete';
  // Never reveal feedback mid-assessment: leakage would contaminate later items.
  return s;
}
export function advance(session) {
  assertSession(session);
  if (!['teach', 'remediation'].includes(session.phase)) throw new Error('Advance only after teaching or remediation');
  const s = clone(session);
  s.phase = s.phase === 'teach' ? 'transfer' : 'retest';
  return s;
}
function aggregate(s, phase) {
  const a = s.answers.filter(x => x.phase === phase);
  return { correct: a.filter(x => x.correct).length, total: a.length, wrongSkills: [...new Set(a.filter(x => !x.correct).map(x => x.skill))] };
}
export function getReport(session) {
  assertSession(session);
  if (session.phase !== 'complete') return { verdict: 'NOT_COMPLETED', verifiedLearningGain: null, learnerMastery: 'UNKNOWN' };
  const d = aggregate(session, 'diagnostic'), t = aggregate(session, 'transfer'), r = aggregate(session, 'retest');
  const brier = session.answers.reduce((sum, a) => sum + (a.confidence - (a.correct ? 1 : 0)) ** 2, 0) / session.answers.length;
  return {
    verdict: 'LOCAL_RESEARCH_OBSERVATION_ONLY',
    arm: session.arm,
    version: session.version,
    diagnostic: d,
    transfer: t,
    retest: r,
    calibrationBrierDescriptive: Number(brier.toFixed(4)),
    learnerMastery: 'UNKNOWN',
    delayedRetention: 'UNKNOWN',
    verifiedLearningGain: null,
    causalUplift: null,
    independentEvaluator: null,
    productionOperationalYield: false,
    caveat: 'Unlike matched randomised blinded cohort results, an individual local score cannot show causal learning improvement or certify mastery.',
  };
}
