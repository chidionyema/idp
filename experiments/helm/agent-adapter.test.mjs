import test from "node:test";
import assert from "node:assert/strict";
import {propose} from "./agent-adapter.mjs";
const endpoint="https://private-model.example/v1/chat/completions";
const plan={plan_hash:"known-plan",provenance:{commit:"a1",index_commit:"a1"},
  items:[{rank:1,source:"lib/handler.py",excerpt:"def handle(): pass",sha256:"source-digest"}]};

test("Model proposal uses canonical ContextPlan, never claims execution",async()=>{
  let sent=[];
  const infer=async({messages})=>{
    sent=messages;
    return {answer:JSON.stringify({opcode:"EMIT_PATCH",payload:"def handle():\n return 1\n"}),
      latencyMs:8,usage:{total_tokens:25}};
  };
  const result=await propose({model:"fixture",url:endpoint,token:"fixture",
    contextPlan:plan,task:{id:"T",question:"Correct handler",patchTarget:"lib/handler.py",language:"python"},
    infer});
  assert.equal(result.state,"CANDIDATE");
  assert.equal(result.contextPlanHash,"known-plan");
  assert.equal(result.independentlyVerified,false);
  assert.equal(result.action.opcode,"EMIT_PATCH");
  assert.equal(sent[1].role,"user");
  assert.ok(sent[1].content.includes("lib/handler.py"));
});

test("Unverified claims are refused and not laundered into an action",async()=>{
  const infer=async()=>({answer:JSON.stringify({opcode:"SUBMIT_YIELD",payload:"all done"})});
  const result=await propose({model:"fixture",url:endpoint,token:"fixture",
    task:{id:"T",question:"Verify work",requiresOperationalProof:true},
    infer,maxAttempts:1});
  assert.equal(result.state,"UNVERIFIED_YIELD_REFUSED");
  assert.equal(result.action,null);
  assert.equal(result.independentlyVerified,false);
});

test("Anonymous free provider cannot ingest internal compiler source",async()=>{
  await assert.rejects(()=>propose({model:"cohere/north-mini-code:free",
    url:"https://ai-gateway.kilo.ai/api/v1/chat/completions",
    contextPlan:plan,task:{id:"T",question:"Fix it",classification:"public-synthetic"}}),
    /public-synthetic tasks only/);
});

test("Stale ContextPlan fails before inference, with no fabrications",async()=>{
  let called=false;
  const infer=async()=>{called=true;return {answer:"{}"}};
  await assert.rejects(()=>propose({model:"fixture",url:endpoint,token:"fixture",
    contextPlan:{...plan,provenance:{commit:"a1",index_commit:"a0"}},
    task:{id:"T",question:"Fix it"},infer}),/stale context index/);
  assert.equal(called,false);
});
