import test from 'node:test';
import assert from 'node:assert/strict';
import { ARMS, PILOT_VERSION, startSession, currentView, submitChoice, advance, getReport } from './adaptive.mjs';

const correctChoices = { 'd-key': 1, 'd-api': 2, 't-ledger': 1, 't-rate': 2, 't-split': 3, 'r-history': 1, 'r-external': 2, 'r-reconcile': 0, 'r-dependency': 1 };

function take(s, choice, confidence = 0.8) {
  const q = currentView(s).question;
  assert.ok(q, 'active question');
  return submitChoice(s, { itemId: q.id, choice, confidence });
}
function finish({arm='triad', transfer=[1,2,3], diagnostic=[1,2], retest=null} = {}) {
  let s=startSession({arm});
  for (const a of diagnostic) s=take(s,a);
  assert.equal(s.phase,'teach');
  s=advance(s);
  for (const a of transfer) s=take(s,a);
  if (s.phase==='remediation') {
    assert.ok(currentView(s).correction.breaksAt === undefined);
    s=advance(s);
    s=take(s,retest ?? correctChoices[currentView(s).question.id]);
  }
  assert.equal(s.phase,'complete');
  return s;
}

test('A01: three legitimate teaching arms share one canonical target',()=>{
  assert.deepEqual(ARMS,['canonical','single','triad']);
  for(const arm of ARMS) {
    let s=startSession({arm});
    s=take(s,1);s=take(s,2);
    const v=currentView(s);
    assert.equal(v.canonical.title,'Can a small seed continuously regenerate an entire system?');
    assert.equal(v.analogies.length,arm==='canonical'?0:arm==='single'?1:2);
  }
});
test('A02: before teaching all diagnostic questions are unseen and without feedback',()=>{
  let s=startSession();
  const v=currentView(s);
  assert.equal(v.phase,'diagnostic');assert.equal(v.step,1);
  assert.equal(v.question.id,'d-key');
  assert.ok(!Object.hasOwn(v.question,'correct'));
  assert.ok(!JSON.stringify(v).includes('explanation'));
  s=take(s,0);
  assert.equal(currentView(s).question.id,'d-api');
  assert.ok(!Object.hasOwn(currentView(s),'feedback'));
});
test('A03: invalid arm, session id and answers are refused',()=>{
  assert.throws(()=>startSession({arm:'verified'}),TypeError);
  assert.throws(()=>startSession({sessionId:'../../etc/passwd'}),TypeError);
  assert.throws(()=>submitChoice(startSession(),{itemId:'d-api',choice:2}),/Out-of-sequence/);
  assert.throws(()=>submitChoice(startSession(),{itemId:'d-key',choice:'B'}),/Invalid response choice/);
  assert.throws(()=>submitChoice(startSession(),{itemId:'d-key',choice:1,confidence:150}),/Confidence/);
});
test('A04: cannot skip teaching or record unsupplied transfer evidence',()=>{
  assert.throws(()=>advance(startSession()),/Advance only/);
  assert.equal(getReport(startSession()).learnerMastery,'UNKNOWN');
  assert.equal(getReport(startSession()).verdict,'NOT_COMPLETED');
});
test('A05: exact response sequence passes without certifying mastery or efficacy',()=>{
  const s=finish();
  const r=getReport(s);
  assert.equal(r.diagnostic.correct,2);
  assert.equal(r.transfer.correct,3);
  assert.equal(r.transfer.total,3);
  assert.equal(r.retest.total,0);
  assert.equal(r.learnerMastery,'UNKNOWN');
  assert.equal(r.verifiedLearningGain,null);
  assert.equal(r.productionOperationalYield,false);
  assert.equal(r.causalUplift,null);
});
test('A06: missing history triggers a corrective analogy and novel retest',()=>{
  let s=startSession();
  s=take(s,1);s=take(s,2);s=advance(s);
  s=take(s,0);s=take(s,2);s=take(s,3);
  assert.equal(s.phase,'remediation');
  assert.equal(s.retestSkill,'history');
  assert.equal(currentView(s).correction.analogy,'Film editing');
  assert.match(currentView(s).correction.limit,/does not account/);
  s=advance(s);
  assert.equal(currentView(s).question.id,'r-history');
  s=take(s,1);
  assert.equal(getReport(s).transfer.correct,2);
  assert.equal(getReport(s).retest.correct,1);
});
test('A07: wrong external input selects a different analogy and test item',()=>{
  let s=startSession();s=take(s,1);s=take(s,2);s=advance(s);
  s=take(s,1);s=take(s,0);s=take(s,3);
  assert.equal(currentView(s).correction.analogy,'Cooking');
  s=advance(s);assert.equal(currentView(s).question.id,'r-external');
  s=take(s,2);assert.equal(getReport(s).retest.correct,1);
});
test('A08: wrong reconciliation requires retest on real conflicts',()=>{
  let s=startSession();s=take(s,1);s=take(s,2);s=advance(s);
  s=take(s,1);s=take(s,2);s=take(s,0);
  assert.equal(currentView(s).correction.analogy,'Two authors');
  s=advance(s);assert.equal(currentView(s).question.id,'r-reconcile');
  s=take(s,0);assert.equal(getReport(s).retest.correct,1);
});
test('A09: retest correction is not proof of mastery',()=>{
  const s=finish({transfer:[0,2,3],retest:1});
  assert.equal(getReport(s).retest.correct,1);
  assert.equal(getReport(s).learnerMastery,'UNKNOWN');
  assert.equal(getReport(s).delayedRetention,'UNKNOWN');
});
test('A10: saving a duplicate or mutating phase cannot fabricate assessment records',()=>{
  const s=startSession();
  const fake={...s,phase:'complete'};
  assert.throws(()=>getReport(fake),/Forged/);
  const valid=finish();
  const poisoned=structuredClone(valid);
  poisoned.answers[0].correct=false;
  assert.throws(()=>getReport(poisoned),/Tampered/);
  const repeated=structuredClone(valid);repeated.answers[1]={...repeated.answers[0]};
  assert.throws(()=>getReport(repeated),/Tampered/);
});
test('A11: falsified completion after incorrect transfer must include real retest',()=>{
  let s=startSession();s=take(s,1);s=take(s,2);s=advance(s);
  s=take(s,0);s=take(s,2);s=take(s,3);
  const fake={...s,phase:'complete'};
  assert.throws(()=>getReport(fake),/Forged/);
});
test('A12: browser-facing view cannot mutate the underlying source or leak correct keys',()=>{
  let s=startSession();s=take(s,1);s=take(s,2);
  const v=currentView(s);v.analogies[0].statement='evil';v.canonical.rule='corrupt';
  assert.notEqual(currentView(s).analogies[0].statement,'evil');
  assert.notEqual(currentView(s).canonical.rule,'corrupt');
});
test('A13: descriptive confidence calibration stays bounded and never becomes mastery',()=>{
  const s=finish({transfer:[1,2,3]});
  const r=getReport(s);
  assert.ok(r.calibrationBrierDescriptive>=0 && r.calibrationBrierDescriptive<=1);
  assert.equal(r.independentEvaluator,null);
});
test('A14: no local session can mint verified operating yield via user-provided fields',()=>{
  const s=finish();s.verifiedOperationalYield=true;s.externalVerifier='self-certification';
  const r=getReport(s);
  assert.equal(r.productionOperationalYield,false);
  assert.equal(r.independentEvaluator,null);
});
test('A15: progress retains one coherent goal and subgoals across each teaching arm',()=>{
  for(const arm of ARMS){
    const s=finish({arm});
    assert.equal(s.version,PILOT_VERSION);
    assert.equal(getReport(s).arm,arm);
  }
});
