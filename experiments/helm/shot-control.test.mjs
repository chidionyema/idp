import test from "node:test";
import assert from "node:assert/strict";
import { shotPolicy, initialShotState, advanceShot, replayShots, shotReport, helmDigest } from "./shot-control.mjs";

const SHA = "a".repeat(40);
const makePolicy = (shots = 1, overrides = {}) => shotPolicy({
  instructionId: "INS-HELM-11", sourceSha: SHA, taskDigest: helmDigest("task"),
  model: "fixture-model", shots, ...overrides
});
const probe = () => ({
  kind:"PROBE", eventId:"PROBE-001", instructionId:"INS-HELM-11",
  probeDigest:helmDigest("one complete discovery"), sourceSha:SHA
});
const candidate = (i=1) => ({
  kind:"SHOT", eventId:"SHOT-"+i, instructionId:"INS-HELM-11",
  candidateDigest:helmDigest("complete script "+i), opcode:"EMIT_PATCH", model:"fixture-model"
});
const grade = (i=1, passed=false) => ({
  kind:"GRADE",eventId:"GRADE-"+i,instructionId:"INS-HELM-11",
  candidateDigest:helmDigest("complete script "+i),
  passed, verifier:"independent-oracle", evidenceDigest:helmDigest("oracle:"+i+":"+passed)
});
const accept = (p, events) => events.reduce((state,e)=>advanceShot(p,state,e),initialShotState(p));
const fail = (f,why=/HELM_REFUSED/) => assert.throws(f,why);

test("all ten Kabala-associated budgets are valid; 0, 11 and fractions are not",()=>{
  for(let n=1;n<=10;n++) assert.equal(makePolicy(n).shots,n);
  for(const n of [0,-1,11,100,1.1,"2",null,NaN,Infinity])
    fail(()=>makePolicy(n),/shot budget/);
});

test("the exact Argon instruction primary-key grammar is enforced",()=>{
  for(const id of ["a", "bad/slash","BAD SPACE","x".repeat(101),"abc:001",""])
    fail(()=>makePolicy(1,{instructionId:id}),/instruction_id/);
  assert.equal(makePolicy(1,{instructionId:"I-0045"}).instructionId,"I-0045");
});

test("a one-shot helmet allows exactly one probe, one proposal and one independent grade",()=>{
  const p=makePolicy();
  const s=accept(p,[probe(),candidate(1),grade(1,true)]);
  const receipt=shotReport(p,s);
  assert.equal(s.phase,"VERIFIED");
  assert.equal(receipt.contextProbes,1);
  assert.equal(receipt.candidateSubmissions,1);
  assert.equal(receipt.independentlyGraded,1);
  assert.equal(receipt.remaining,0);
  assert.equal(receipt.passedFixtureOracle,true);
  assert.equal(receipt.liveExecutionVerified,false);
  fail(()=>advanceShot(p,s,candidate(2)),/terminal/);
  fail(()=>advanceShot(p,s,{...probe(),eventId:"PROBE-002"}),/terminal/);
});

test("one-shot failure is terminal and may not silently retry",()=>{
  const p=makePolicy();
  const s=accept(p,[probe(),candidate(1),grade(1,false)]);
  assert.equal(s.phase,"EXHAUSTED");
  fail(()=>advanceShot(p,s,candidate(2)),/terminal/);
});

test("two-shot allows second complete candidate only after independent negative grade",()=>{
  const p=makePolicy(2);
  let s=accept(p,[probe(),candidate(1)]);
  fail(()=>advanceShot(p,s,candidate(2)),/needs one prior|graded predecessor/);
  s=advanceShot(p,s,grade(1,false));
  assert.equal(s.phase,"READY");
  s=advanceShot(p,s,candidate(2));
  s=advanceShot(p,s,grade(2,true));
  assert.equal(s.phase,"VERIFIED");
  assert.equal(shotReport(p,s).candidateSubmissions,2);
});

test("ten-shot agent cannot submit an eleventh candidate",()=>{
  const p=makePolicy(10);
  const events=[probe()];
  for(let i=1;i<=10;i++)events.push(candidate(i),grade(i,false));
  const s=accept(p,events);
  assert.equal(s.phase,"EXHAUSTED");
  assert.equal(s.shots,10);
  assert.equal(s.grades,10);
  fail(()=>advanceShot(p,s,candidate(11)),/terminal/);
});

test("no free investigation: extra discovery is refused for all k",()=>{
  for(const k of [1,2,10]){
    const p=makePolicy(k);
    const s=accept(p,[probe()]);
    fail(()=>advanceShot(p,s,{...probe(),eventId:"PROBE-NEW"}),/one context probe/);
  }
});

test("a model cannot propose before the first context probe",()=>{
  fail(()=>advanceShot(makePolicy(),initialShotState(makePolicy()),candidate()),/one prior context probe/);
});

test("an agent cannot grade its own proposal or impersonate the independent grader",()=>{
  const p=makePolicy();
  const s=accept(p,[probe(),candidate()]);
  fail(()=>advanceShot(p,s,{...grade(),verifier:"fixture-model"}),/self-certify/);
  fail(()=>advanceShot(p,s,{...grade(),verifier:"anonymous"}),/self-certify/);
});

test("receipt spoofing with wrong candidate bytes is refused",()=>{
  const p=makePolicy();
  const s=accept(p,[probe(),candidate()]);
  fail(()=>advanceShot(p,s,{...grade(),candidateDigest:helmDigest("ghost")}),/exact candidate bytes/);
});

test("unsupported privileged opcodes never reach the executor",()=>{
  const p=makePolicy(4);
  const s=accept(p,[probe()]);
  for(const name of ["EXEC_SHELL","DEPLOY_NOW","BYPASS_GREENLANE","WRITE_FILE","git push"])
    fail(()=>advanceShot(p,s,{...candidate(),opcode:name}),/unregistered executor operation/);
});

test("same event id + same bytes is idempotent across disconnected runner sessions",()=>{
  const p=makePolicy(2);
  const s=accept(p,[probe(),candidate()]);
  const copy=JSON.parse(JSON.stringify(s));
  const again=advanceShot(p,copy,candidate());
  assert.deepEqual(again,copy);
  assert.equal(again.shots,1);
  assert.equal(again.events.length,2);
});

test("same event id + DIFFERENT bytes is a conflict, not a free retry",()=>{
  const p=makePolicy(2);
  const s=accept(p,[probe(),candidate()]);
  fail(()=>advanceShot(p,s,{...candidate(),candidateDigest:helmDigest("conflict")}),/idempotency/);
});

test("wrong instruction ID never mutates the ledger",()=>{
  const p=makePolicy();
  const s=initialShotState(p);
  fail(()=>advanceShot(p,s,{...probe(),instructionId:"INS-OTHER"}),/wrong instruction/);
  assert.equal(s.events.length,0);
});

test("changing the helmet configuration is a fork, not a silent budget upgrade",()=>{
  const p=makePolicy(1);
  const s=accept(p,[probe()]);
  fail(()=>advanceShot(makePolicy(10),s,candidate()),/journal integrity mismatch|policy mutation/);
});

test("model swapping during a shot is denied",()=>{
  const p=makePolicy(2);
  const s=accept(p,[probe()]);
  fail(()=>advanceShot(p,s,{...candidate(),model:"other-model"}),/model substituted/);
});

test("wrong source revision cannot validate the one probe",()=>{
  const p=makePolicy();
  const s=initialShotState(p);
  fail(()=>advanceShot(p,s,{...probe(),sourceSha:"b".repeat(40)}),/exact source/);
});

test("forged missing evidence is refused instead of being a passing verdict",()=>{
  const p=makePolicy();
  const s=accept(p,[probe(),candidate()]);
  fail(()=>advanceShot(p,s,{...grade(1,true),evidenceDigest:""}),/evidence digest/);
});

test("duplicate or unknown fields fail closed",()=>{
  const p=makePolicy();
  const s=initialShotState(p);
  fail(()=>advanceShot(p,s,{...probe(),executionAuthority:true}),/undeclared action attribute/);
  fail(()=>advanceShot(p,s,{...probe(),kind:"DELETE_HISTORY"}),/invalid opcode/);
});

test("replayed journal survives process restart and detects every corruption class",()=>{
  const p=makePolicy(3);
  const s=accept(p,[probe(),candidate(),grade(1,false),candidate(2),grade(2,true)]);
  const stored=JSON.parse(JSON.stringify(s.events));
  const recovered=replayShots(p,stored);
  assert.equal(recovered.phase,"VERIFIED");
  assert.equal(recovered.head,s.head);
  const changed=structuredClone(stored);
  changed[2].passed=true;
  fail(()=>replayShots(p,changed),/journal integrity mismatch/);
  fail(()=>replayShots(p,stored.slice(1)),/journal sequence gap/);
  fail(()=>replayShots(p,[...stored,stored[0]]),/duplicate stored event ID|journal sequence gap/);
  const switched=structuredClone(stored);
  [switched[1],switched[2]]=[switched[2],switched[1]];
  fail(()=>replayShots(p,switched),/journal sequence gap|journal integrity mismatch/);
});

test("the controller grants no execute, network, file, git or CI permission",()=>{
  const p=makePolicy(1,{profile:"control"});
  assert.equal(p.grantsExecutionAuthority,false);
  assert.equal(p.maxContextProbes,1);
  assert.equal(p.maxCompleteCandidateSubmissions,1);
  assert.equal(Object.isFrozen(p),true);
});

test("an ungraded candidate can recover after crash without another model call",()=>{
  const p=makePolicy(2);
  const s=accept(p,[probe(),candidate(1)]);
  const recovered=replayShots(p,JSON.parse(JSON.stringify(s.events)));
  assert.equal(recovered.phase,"AWAITING_GRADE");
  assert.equal(recovered.shots,1);
  const done=advanceShot(p,recovered,grade(1,true));
  assert.equal(done.phase,"VERIFIED");
  assert.equal(done.shots,1);
});

test("an unauthorized evidence-shape change is refused",()=>{
  const p=makePolicy(1);
  const s=accept(p,[probe(),candidate()]);
  fail(()=>advanceShot(p,s,{...grade(),passed:"true"}),/verdict/);
});
