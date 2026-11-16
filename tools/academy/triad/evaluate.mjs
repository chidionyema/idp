import { LESSON_ID, getAssessment } from './lesson.mjs';

// Answer key is intentionally separate from the learner-facing content.
// This is deterministic grading of three items, NOT an independent causal
// evaluation of TRIAD, and does not certify human mastery or operational yield.
const KEY = Object.freeze({ t1: 'B', t2: 'C', t3: 'D' });
const FEEDBACK = Object.freeze({
  t1: 'Encryption cannot be undone by a checkpoint; recover the authorised key or trusted plaintext.',
  t2: 'Mutable external API results are part of the necessary replay inputs.',
  t3: 'Concurrent branches must reconcile changes and prove causal continuity and side effects.',
});

export function assessTransfer(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    throw new TypeError('Answers must be an object mapping item IDs to A/B/C/D.');
  }
  if (Object.getPrototypeOf(raw) !== Object.prototype && Object.getPrototypeOf(raw) !== null) {
    throw new TypeError('Answers must be a plain object.');
  }
  const allowed = Object.keys(KEY);
  const submitted = Object.keys(raw);
  for (const id of submitted) if (!allowed.includes(id)) throw new TypeError('Unknown response field: ' + id);
  const items = [];
  for (const id of allowed) {
    const selection = raw[id];
    const presented = getAssessment().items.find(item => item.id === id);
    if (typeof selection !== 'string' || !Object.hasOwn(presented.options, selection)) {
      throw new TypeError('Missing or invalid choice for ' + id);
    }
    items.push({ id, correct: selection === KEY[id], selected: selection, feedback: FEEDBACK[id] });
  }
  const correct = items.filter(item => item.correct).length;
  return {
    lessonId: LESSON_ID,
    evidenceClass: 'UNBLINDED_LOCAL_TRANSFER_PILOT',
    items,
    result: { correct, total: items.length, rawPercent: Math.round(correct / items.length * 100) },
    independentOutcomeWitness: false,
    mastery: 'UNKNOWN',
    delayedRetention: 'UNKNOWN',
    causalLift: 'UNKNOWN',
    learningCost: 'UNKNOWN',
    verifiedOperationalYield: false,
  };
}
