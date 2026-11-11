import test from "node:test";
import assert from "node:assert/strict";
import {runOneArm,runShotMatrix} from "./shot-trial.mjs";
import {helmDigest} from "./shot-control.mjs";

const SHA="b".repeat(40);
const task={id:"PY-ERR-001",domain:"software",language:"python",
  question:"Return a valid EMIT_PATCH action for a safe Python parser.",
  patchTarget:"parser.py",
  classification:"public-synthetic",
  oracle:{opcode:"EMIT_PATCH",contains:["except ValueError"]}};
const url="https://local.fixture.invalid/v1/chat/completions";
const good={opcode:"EMIT_PATCH",payload:"try:\n x=1\nexcept ValueError:\n pass\n"};
const bad={opcode:"EMIT_PATCH",payload:"try:\n x=1\nexcept:\n pass\n"};
const answer=value=>({
  answer:JSON.stringify(value),usage:{total_tokens:23},
  modelReturned:"fixture-model",latencyMs:5
});
const opts={task,sourceSha:SHA,url,model:"fixture-model",evidence:[]};

test("one-shot receives exactly one model call and one data probe",async()=>{
  let calls=0;
  const r=await runOneArm({...opts,arm:"helm-1",
    infer:async()=>{calls++;return answer(good);}});
  assert.equal(calls,1);
  assert.equal(r.maximumShots,1);
  assert.equal(r.contextProbes,1);
  assert.equal(r.status,"VERIFIED");
  assert.equal(r.passedFixtureOracle,true);
  assert.equal(r.calls,1);
  assert.equal(r.totalTokens,23);
  assert.equal(r.liveExecutionVerified,false);
  assert.equal(r.journal.length,3);
});

test("one-shot failure cannot quietly create a second attempt",async()=>{
  let calls=0;
  const r=await runOneArm({...opts,arm:"helm-1",
    infer:async()=>{calls++;return answer(bad);}});
  assert.equal(calls,1);
  assert.equal(r.status,"EXHAUSTED");
  assert.equal(r.passedFixtureOracle,false);
  assert.equal(r.attempts[0].fixtureOraclePass,false);
});

test("two-shot repair gets exactly one corrected second complete output",async()=>{
  const prompts=[];
  const r=await runOneArm({...opts,arm:"helm-2",
    infer:async({messages})=>{
      prompts.push(structuredClone(messages));
      return answer(prompts.length===1?bad:good);
    }});
  assert.equal(prompts.length,2);
  assert.ok(prompts[1].some(m=>/one remaining complete shot/.test(m.content)));
  assert.ok(!prompts[1].some(m=>/oracle.*except ValueError/.test(m.content)));
  assert.equal(r.status,"VERIFIED");
  assert.equal(r.calls,2);
  assert.equal(r.totalTokens,46);
  assert.equal(r.contextProbes,1);
});

test("ten-shot bound is enforced on ten failed model outputs",async()=>{
  let calls=0;
  const r=await runOneArm({...opts,arm:"helm-10",
    infer:async()=>{calls++;return answer(bad);}});
  assert.equal(calls,10);
  assert.equal(r.calls,10);
  assert.equal(r.status,"EXHAUSTED");
  assert.equal(r.journal.length,21); // one probe + 10 (shot,grade)
});

test("a malformed response consumes exactly one shot but is never executed",async()=>{
  let calls=0;
  const r=await runOneArm({...opts,arm:"helm-2",
    infer:async()=>{calls++;return {answer:"NOT JSON",modelReturned:"fixture-model"};}});
  assert.equal(calls,2);
  assert.equal(r.status,"EXHAUSTED");
  assert.equal(r.journal[1].opcode,"INVALID_PROPOSAL");
  assert.equal(r.attempts[0].syntaxAndSchema,false);
});

test("the same task with unmodified control prompt has no HELM text",async()=>{
  let count=0;let prompt;
  const r=await runOneArm({...opts,arm:"control",
    infer:async({messages})=>{
      count++;
      prompt=messages;
      return answer(good);
    }});
  assert.equal(count,1);
  assert.equal(r.profile,"control");
  assert.equal(r.maximumShots,10);
  assert.ok(prompt.every(m=>!m.content.includes("behavioural helmet")));
  assert.equal(r.passedFixtureOracle,true);
});

test("HELM does not turn failures into success by using an internal grader",async()=>{
  const r=await runOneArm({...opts,arm:"helm-3",
    infer:async()=>answer({opcode:"SUBMIT_YIELD",payload:"done"})});
  assert.equal(r.status,"EXHAUSTED");
  assert.equal(r.passedFixtureOracle,false);
});

test("provider failures are visible, not graded as negative model intelligence",async()=>{
  let calls=0;
  const r=await runOneArm({...opts,arm:"helm-10",infer:async()=>{
    calls++;throw Error("HTTP 429 provider quota");
  }});
  assert.equal(calls,1);
  assert.equal(r.status,"PROVIDER_BLOCKED_RETRYABLE");
  assert.equal(r.attempts[0].providerError,"HTTP 429 provider quota");
  assert.equal(r.passedFixtureOracle,false);
  assert.equal(r.calls,1);
});

test("model mismatch invalidates apparent passing output",async()=>{
  const r=await runOneArm({...opts,arm:"helm-1",
    infer:async()=>({...answer(good),modelReturned:"different-model"})});
  assert.equal(r.passedFixtureOracle,false);
  assert.equal(r.attempts[0].providerError,"provider model mismatch");
});

test("private task cannot go to anonymous public inference route",async()=>{
  const publicUrl="https://ai-gateway.kilo.ai/api/v1/chat/completions";
  let called=false;
  await assert.rejects(()=>runOneArm({...opts,url:publicUrl,
    task:{...task,classification:"internal"},arm:"helm-1",
    infer:async()=>{called=true;return answer(good);}}),
    /anonymous provider/);
  assert.equal(called,false);
});

test("matrix cannot relabel private tasks as public synthetic",async()=>{
  let called=false;
  await assert.rejects(()=>runShotMatrix({...opts,
    tasks:[{...task,classification:"private"}],limits:[1],
    infer:async()=>{called=true;return answer(good);},
    url:"https://ai-gateway.kilo.ai/api/v1/chat/completions"}),
    /anonymous provider/);
  assert.equal(called,false);
});

test("matrix preflight cost ceiling refuses before first model call",async()=>{
  let called=false;
  await assert.rejects(()=>runShotMatrix({...opts,
    tasks:[task],limits:[1,2,3,4,5,6,7,8,9,10],maxCalls:64,
    infer:async()=>{called=true;return answer(good);}}),/model-call ceiling/);
  assert.equal(called,false);
});

test("paired matrix records complete comparable denominators",async()=>{
  let calls=0;
  const out=await runShotMatrix({
    tasks:[task],evidence:[],model:"fixture-model",
    url,sourceSha:SHA,limits:[1,2,10],maxCalls:23,
    infer:async()=>{calls++;return answer(good);}
  });
  assert.equal(out.schema,"helm.shot-matrix.v1");
  assert.equal(out.independentlyVerifiedProductionYield,false);
  assert.equal(calls,4); // early stop in every arm
  assert.equal(out.results.length,4);
  assert.equal(out.summary.control.passed,1);
  assert.equal(out.summary["helm-1"].totalCalls,1);
  assert.equal(out.summary["helm-10"].totalCalls,1);
  assert.equal(out.pairs.length,3);
  assert.equal(out.pairs[0].usable,1);
  assert.equal(out.pairs[0].inferencePermitted,false);
});

test("separate tasks reverse arm order to reduce sequential provider confounding",async()=>{
  const checkpoints=[];
  const task2={...task,id:"PY-ERR-002",question:task.question+" Again."};
  const out=await runShotMatrix({
    tasks:[task,task2],evidence:[],model:"fixture-model",
    url,sourceSha:SHA,limits:[1],maxCalls:22,
    infer:async()=>answer(good),
    onCheckpoint:x=>checkpoints.push(x.results.at(-1).arm)
  });
  assert.deepEqual(checkpoints,["control","helm-1","helm-1","control"]);
  assert.equal(out.results.length,4);
});

test("shot results preserve exactly one canonical instruction ID per arm",async()=>{
  const r=await runOneArm({...opts,arm:"helm-1",infer:async()=>answer(good)});
  assert.equal(r.instructionId,"HELM-PY-ERR-001-helm-1");
  assert.equal(r.taskDigest,helmDigest(task.question));
  assert.match(r.chainHead,/^[a-f0-9]{64}$/);
});

test("invalid task, omitted source sha and unpinned model are rejected before inference",async()=>{
  let called=false;
  const fn=async()=>{called=true;return answer(good);};
  await assert.rejects(()=>runOneArm({...opts,task:{...task,id:"!"},arm:"helm-1",infer:fn}),/named task/);
  await assert.rejects(()=>runOneArm({...opts,sourceSha:"local",arm:"helm-1",infer:fn}),/pinned source/);
  await assert.rejects(()=>runShotMatrix({
    tasks:[task],limits:[1],sourceSha:SHA,model:"",
    infer:fn
  }),/pinned model/);
  assert.equal(called,false);
});

test("a negative non-model-availability result does not become zero tokens",async()=>{
  const r=await runOneArm({...opts,arm:"helm-1",infer:async()=>({
    answer:JSON.stringify(good),modelReturned:"fixture-model",usage:null
  })});
  assert.equal(r.totalTokens,null);
  assert.equal(r.passedFixtureOracle,true);
});

test("independent grader source cannot be substituted into model prompt",async()=>{
  let got;
  const taskPrivateOracle={...task,oracle:{opcode:"EMIT_PATCH",contains:["SECRET_ORACLE_NO_LEAK"]}};
  await runOneArm({...opts,task:taskPrivateOracle,arm:"helm-1",
    infer:async({messages})=>{got=messages;return answer(good);}});
  assert.ok(got.every(x=>!x.content.includes("SECRET_ORACLE_NO_LEAK")));
});
