import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {createHash} from "node:crypto";
import {runFunctional} from "./functional-bench.mjs";
import {harvestVerified,replayVerified,fingerprint} from "./operational-memory.mjs";

const cases=JSON.parse(readFileSync(new URL("./fixtures/functional.json",import.meta.url),"utf8")).cases;
const refs=JSON.parse(readFileSync(new URL("./fixtures/functional-references.json",import.meta.url),"utf8"));
const sha=s=>createHash("sha256").update(s).digest("hex");

test("A generated, verified program becomes independently replayable without a model call",async()=>{
  const t=cases[1];
  let modelCalls=0,verifierCalls=0;
  const result=await runFunctional({tasks:[t],evidence:[],model:"fixture-model",
    url:"https://fixture.example/v1",fn:async()=>{
      modelCalls++;
      return {answer:JSON.stringify({opcode:"EMIT_PATCH",payload:refs[t.id]}),
        modelReturned:"fixture-model",latencyMs:1};
    },testFn:()=>({passed:true,kind:"functional",tests:t.expectedTests})});
  assert.equal(result.summary.helm.passed,1);
  assert.equal(modelCalls,5);
  assert.ok(result.records.find(r=>r.arm==="helm").verifiedProgram);
  const independent=(task,code)=>{
    verifierCalls++;
    return {passed:task.id===t.id&&code===refs[t.id],
      kind:"functional",tests:t.expectedTests};
  };
  const memory=harvestVerified({trial:result,tasks:[t],verify:independent,allowFixture:true});
  assert.ok(memory.accepted>=1);
  assert.equal(memory.rejected.length,0);
  const before=modelCalls;
  const replay=replayVerified({memory,tasks:[t],verify:independent});
  assert.equal(modelCalls,before);
  assert.equal(replay.modelCalls,0);
  assert.equal(replay.passed,replay.total);
  assert.ok(replay.independentTestsPassed>=t.expectedTests);
  assert.equal(verifierCalls,memory.accepted+memory.accepted);
});

test("Mock/ungrounded trajectories cannot enter real evidence memory",()=>{
  assert.throws(()=>harvestVerified({trial:{kind:"fixture-model",records:[]},tasks:cases}),
    /refuse ungrounded/);
  assert.throws(()=>harvestVerified({trial:{kind:"unverified",records:[]},tasks:cases}),
    /refuse ungrounded/);
});

test("Do not store a fabricated success when independent verifier rejects it",()=>{
  const t=cases[0],code=refs[t.id];
  const memory=harvestVerified({trial:{kind:"real-model",codeSha:"test",model:"model",
    records:[{taskId:t.id,arm:"helm",passed:true,
      taskSha:sha(t.question),oracleSha:sha(t.oracle),
      verifiedProgram:{source:code,sha256:sha(code),testCount:t.expectedTests}}]},
    tasks:[t],verify:()=>({passed:false,tests:0,detail:"failure"})});
  assert.equal(memory.accepted,0);
  assert.equal(memory.rejected.length,1);
});

test("Changed oracle or program makes replay fail closed even with a passed receipt",()=>{
  const t=cases[2],code=refs[t.id];
  const memory=harvestVerified({trial:{kind:"real-model",codeSha:"source-sha",model:"model",
    records:[{taskId:t.id,arm:"helm",passed:true,
      taskSha:sha(t.question),oracleSha:sha(t.oracle),
      verifiedProgram:{source:code,sha256:sha(code),testCount:t.expectedTests}}]},
    tasks:[t],verify:()=>({passed:true,tests:t.expectedTests})});
  assert.equal(memory.accepted,1);
  const alteredOracle={...t,oracle:t.oracle+"\n# patch changes the oracle"};
  const stale=replayVerified({memory,tasks:[alteredOracle],
    verify:()=>{throw Error("must not execute stale code");}});
  assert.equal(stale.passed,0);
  assert.equal(stale.results[0].reason,"task-or-oracle-changed");
  const tampered=structuredClone(memory);
  tampered.entries[0].code+="\n# tampered";
  const bad=replayVerified({memory:tampered,tasks:[t],
    verify:()=>{throw Error("must not execute corrupt code");}});
  assert.equal(bad.passed,0);
  assert.equal(bad.results[0].reason,"program-integrity-mismatch");
  assert.deepEqual(fingerprint(t),{taskSha256:sha(t.question),oracleSha256:sha(t.oracle)});
});
