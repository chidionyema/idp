import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {createHash} from "node:crypto";
import {messagesForTransfer,evaluateTransfer} from "./transfer-bench.mjs";

const transfer=JSON.parse(readFileSync(new URL("./fixtures/transfer.json",import.meta.url),"utf8"));
const original=JSON.parse(readFileSync(new URL("./fixtures/functional.json",import.meta.url),"utf8")).cases[1];
const reference=JSON.parse(readFileSync(new URL("./fixtures/functional-references.json",import.meta.url),"utf8"))[original.id];
const sha=s=>createHash("sha256").update(s).digest("hex");
const memory={schema:"helm.verified-memory.v1",accepted:1,
  entries:[{taskId:original.id,taskSha256:sha(original.question),
    oracleSha256:sha(original.oracle),expectedTests:original.expectedTests,
    code:reference,codeSha256:sha(reference),origin:{model:"fixture"}}]};

test("Cross-task oracles never enter either model arm",()=>{
  for(const t of transfer.cases){
    const base=messagesForTransfer(t,"baseline",reference);
    const experienced=messagesForTransfer(t,"verified-experience",reference);
    assert.equal(base.length,2);
    assert.equal(experienced.length,3);
    assert.ok(experienced[1].content.includes("def choose_intent"));
    for(const messages of [base,experienced]){
      const text=messages.map(m=>m.content).join("\n");
      assert.ok(!text.includes(t.oracle));
      assert.ok(!text.includes("class Tests(unittest.TestCase)"));
      assert.ok(text.includes(t.question));
    }
  }
});

test("Independent source replay is required before transfer inference",async()=>{
  let called=false;
  await assert.rejects(()=>evaluateTransfer({memory,
    model:"mock",url:"https://fixture.test",tasks:transfer.cases,
    infer:async()=>{called=true;return {answer:"{}"}},
    verify:()=>({passed:false,tests:0})}),/source experience/);
  assert.equal(called,false);
});

test("Model responses are graded by executable-test adapter, both arms get matching tasks",async()=>{
  const prompts=[];
  const result=await evaluateTransfer({memory,model:"fixture",url:"https://fixture.test",
    tasks:transfer.cases,verify:(t)=>({passed:true,tests:t.expectedTests}),
    infer:async({messages})=>{
      prompts.push(messages);
      return {answer:JSON.stringify({opcode:"EMIT_PATCH",payload:"def dummy():\n return True\n"}),
        modelReturned:"fixture",usage:{completion_tokens:100}};
    }});
  assert.equal(prompts.length,4);
  assert.equal(result.summary.baseline.passed,2);
  assert.equal(result.summary["verified-experience"].passed,2);
  assert.equal(result.sourceReplayTestsPassed,8);
  assert.equal(result.records.length,4);
});
