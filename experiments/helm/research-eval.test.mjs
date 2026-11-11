import test from "node:test";
import assert from "node:assert/strict";
import {analyseTrial} from "./research-eval.mjs";

const trial=records=>({schema:"helm.transfer.v1",model:"liquid/lfm-3-1.7b:free",
  trialSha:"observed-sha",targetCorpusSha256:"frozen-corpus-hash",
  sourceMemorySha256:"source-memory-hash",records});

test("Real provider-censored transfer trial never manufactures a treatment win",()=>{
  const sample=trial([
    {taskId:"A",arm:"baseline",passed:true,latencyMs:1200,modelReturned:"liquid/lfm-3-1.7b:free"},
    {taskId:"A",arm:"verified-experience",passed:false,error:"provider:429"},
    {taskId:"B",arm:"baseline",passed:false,error:"provider:no text answer"},
    {taskId:"B",arm:"verified-experience",passed:false,error:"provider:output exhausted"}
  ]);
  const report=analyseTrial(sample);
  assert.equal(report.pairs.total,2);
  assert.equal(report.pairs.eligible,0);
  assert.equal(report.pairs.censored,2);
  assert.equal(report.pairs.observedPairedDelta,null);
  assert.equal(report.pairs.exactMcNemarP,null);
  assert.equal(report.pairs.inferencePermitted,false);
  assert.equal(report.decision,"INCONCLUSIVE_NO_RELIABLE_SAMPLE");
  assert.equal(report.raw.baseline.providerErrors,1);
  assert.equal(report.raw["verified-experience"].providerErrors,2);
  assert.equal(report.raw.baseline.failureCountedRate,.5);
});

test("Never count provider unavailable as model-quality failure for paired comparison",()=>{
  const sample=trial([
    {taskId:"A",arm:"baseline",passed:true},
    {taskId:"A",arm:"verified-experience",passed:false,error:"provider:429"},
    {taskId:"B",arm:"baseline",passed:false,error:"tests did not pass"},
    {taskId:"B",arm:"verified-experience",passed:true}
  ]);
  const r=analyseTrial(sample);
  assert.equal(r.pairs.eligible,1);
  assert.equal(r.pairs.treatmentOnly,1);
  assert.equal(r.pairs.observedPairedDelta,1);
  assert.equal(r.raw["verified-experience"].providerHealthyRate,1);
});

test("Provider output model alias mismatch censors the pair",()=>{
  const r=analyseTrial(trial([
    {taskId:"A",arm:"baseline",passed:true,modelReturned:"switch-model"},
    {taskId:"A",arm:"verified-experience",passed:true}
  ]));
  assert.equal(r.pairs.eligible,0);
  assert.equal(r.pairs.censored,1);
});

test("Malformed, duplicate and incomplete comparisons fail explicitly",()=>{
  assert.throws(()=>analyseTrial(trial([])),/no paired observations/);
  assert.throws(()=>analyseTrial(trial([{taskId:"A",arm:"baseline",passed:true}])),/incomplete/);
  assert.throws(()=>analyseTrial(trial([
    {taskId:"A",arm:"baseline",passed:true},
    {taskId:"A",arm:"baseline",passed:true},
    {taskId:"A",arm:"verified-experience",passed:true}
  ])),/duplicate/);
  assert.throws(()=>analyseTrial({...trial([]),model:""}),/missing real experiment/);
});

test("A 10-task exploratory comparison reports an exact paired test without claiming confirmation",()=>{
  const rows=[];
  for(let i=0;i<10;i++){
    rows.push({taskId:String(i),arm:"baseline",passed:false},
      {taskId:String(i),arm:"verified-experience",passed:i<3});
  }
  const r=analyseTrial(trial(rows));
  assert.equal(r.pairs.eligible,10);
  assert.equal(r.pairs.treatmentOnly,3);
  assert.equal(r.pairs.observedPairedDelta,.3);
  assert.equal(r.pairs.exactMcNemarP,.25);
  assert.equal(r.decision,"EXPLORATORY_NOT_CONFIRMATORY");
  assert.equal(r.pairs.inferencePermitted,false);
});

test("Registration, sample size and common model are all required before inference is permitted",()=>{
  const rows=[];
  for(let i=0;i<32;i++){
    rows.push({taskId:String(i),arm:"baseline",passed:i%3===0},
      {taskId:String(i),arm:"verified-experience",passed:i%2===0});
  }
  const candidate=trial(rows);
  let r=analyseTrial(candidate);
  assert.equal(r.pairs.inferencePermitted,false);
  assert.equal(r.decision,"NOT_PREREGISTERED");
  candidate.registrationFrozen=true;
  r=analyseTrial(candidate);
  assert.equal(r.pairs.inferencePermitted,true);
  assert.equal(r.decision,"REQUIRES_REPLICATION");
  assert.equal(r.pairs.total,32);
});
