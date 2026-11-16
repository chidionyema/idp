import assert from 'node:assert/strict';
import test from 'node:test';
import { assessTransfer } from './evaluate.mjs';
import { getAssessment, getLesson, LESSON_ID } from './lesson.mjs';

test('T01: canonical teaching artifact has two structurally different domains', () => {
  const l = getLesson();
  assert.equal(l.id, LESSON_ID);
  assert.equal(l.analogies.length, 2);
  assert.notEqual(l.analogies[0].domain, l.analogies[1].domain);
  assert.ok(l.analogies.every(x => x.breaksAt && x.correspondences.length >= 3));
  assert.ok(l.target.boundary.includes('missing information'));
});
test('T02: answers are hidden from learner-facing assessment and lesson', () => {
  const a = getAssessment();
  assert.equal(a.items.length, 3);
  assert.ok(a.items.every(x => x.options.A && x.options.B && x.options.C && x.options.D && !Object.hasOwn(x, 'correct')));
  assert.ok(!JSON.stringify(getLesson()).includes('KEY ='));
});
test('T03: correct responses yield objective local score, not certified mastery', () => {
  const r = assessTransfer({ t1: 'B', t2: 'C', t3: 'D' });
  assert.equal(r.result.correct, 3);
  assert.equal(r.result.rawPercent, 100);
  assert.equal(r.mastery, 'UNKNOWN');
  assert.equal(r.independentOutcomeWitness, false);
  assert.equal(r.verifiedOperationalYield, false);
  assert.equal(r.causalLift, 'UNKNOWN');
});
test('T04: wrong answers are actually marked wrong', () => {
  const r = assessTransfer({ t1: 'A', t2: 'A', t3: 'A' });
  assert.equal(r.result.correct, 0);
  assert.equal(r.result.rawPercent, 0);
  assert.equal(r.items.filter(x => x.correct).length, 0);
});
test('T05: partial response refused, no fabricated percentage', () => {
  assert.throws(() => assessTransfer({ t1: 'B' }), /Missing or invalid choice for t2/);
});
test('T06: unknown and forged success properties are refused', () => {
  assert.throws(() => assessTransfer({ t1: 'B', t2: 'C', t3: 'D', mastery: 'CERTIFIED' }), /Unknown response field/);
});
test('T07: malformed types and missing input refused', () => {
  for (const value of [null, [], 't1:B', 7]) assert.throws(() => assessTransfer(value), TypeError);
});
test('T08: choice type cannot be coerced to correctness', () => {
  assert.throws(() => assessTransfer({ t1: ['B'], t2: 'C', t3: 'D' }), /Missing or invalid choice/);
  assert.throws(() => assessTransfer({ t1: 'b', t2: 'C', t3: 'D' }), /Missing or invalid choice/);
});
test('T09: input mutation does not alter subsequent grades', () => {
  const a = { t1: 'A', t2: 'C', t3: 'D' };
  assessTransfer(a);a.t1 = 'B';
  assert.equal(assessTransfer(a).result.correct, 3);
});
test('T10: output never promises independent mastery or missing costs', () => {
  for(const a of [{ t1: 'A', t2: 'C', t3: 'D' }, { t1: 'B', t2: 'C', t3: 'D' }]) {
    const r=assessTransfer(a);
    assert.equal(r.delayedRetention, 'UNKNOWN');
    assert.equal(r.learningCost, 'UNKNOWN');
    assert.equal(r.independentOutcomeWitness, false);
  }
});
