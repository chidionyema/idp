import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {messagesFor} from "./helm.mjs";
import {runFunctional,summarise} from "./functional-bench.mjs";

const fixture=JSON.parse(readFileSync(new URL("./fixtures/functional.json",import.meta.url),"utf8"));

test("All three functional oracles are independent of the model-input projection",()=>{
  assert.equal(fixture.cases.length,3);
  assert.deepEqual(fixture.cases.map(c=>c.expectedTests),[7,8,9]);
  for(const c of fixture.cases){
    assert.ok(c.oracle.includes("class Tests(unittest.TestCase)"));
    const inputs=messagesFor("helm",c,fixture.evidence).map(m=>m.content).join("\n");
    assert.equal(inputs.includes(c.oracle),false);
    assert.equal(inputs.includes("def test_good_open"),false);
    assert.ok(inputs.includes(c.question));
  }
});

test("Memory-repair control receives the same evidence without HELM's executive instruction",()=>{
  const c=fixture.cases[1];
  const mem=messagesFor("memory_repair",c,fixture.evidence);
  const helm=messagesFor("helm",c,fixture.evidence);
  assert.equal(mem.length,3);
  assert.equal(helm.length,3);
  assert.ok(mem[1].content.includes("exact registered"));
  assert.ok(helm[0].content.includes("Executive-control semantics"));
  assert.ok(!mem[0].content.includes("Executive-control semantics"));
});

test("Functional multi-arm harness captures failures and bounded repair without real inference",async()=>{
  const c=fixture.cases[0];
  let count=0,grading=0;
  const valid='def classify_surface(homepage,sections,contact_api):\n return "ENQUIRIES_DISABLED"\n';
  const fake=async({messages})=>{
    count++;
    const failed=messages.some(m=>m.content?.startsWith("Independent verifier rejected"));
    return {answer:failed?JSON.stringify({opcode:"EMIT_PATCH",payload:valid}):"not JSON",
      latencyMs:2,usage:{total_tokens:4},modelReturned:"mock"};
  };
  const result=await runFunctional({tasks:[c],evidence:fixture.evidence,model:"mock",url:"https://mock.example/v1",
    fn:fake,testFn:(task,code)=>{grading++;return {passed:true,kind:"functional",tests:7,expectedTests:7,detail:"test"}}});
  assert.equal(result.kind,"fixture-model");
  assert.equal(result.summary.baseline.passed,0);
  assert.equal(result.summary.skills.passed,0);
  assert.equal(result.summary.memory.passed,0);
  assert.equal(result.summary.memory_repair.passed,1);
  assert.equal(result.summary.helm.passed,1);
  assert.equal(result.summary.helm.attempts,2);
  assert.equal(result.summary.memory_repair.attempts,2);
  assert.equal(count,7);
  assert.equal(grading,2);
});

test("Summary does not transform provider failures into successful outputs",()=>{
  const rows=[{arm:"baseline",passed:false,attempts:[{kind:"provider-error"}]},
    {arm:"helm",passed:true,attempts:[{kind:"functional",latencyMs:100}]}];
  const s=summarise(rows,["baseline","helm"]);
  assert.equal(s.baseline.providerErrors,1);
  assert.equal(s.baseline.passed,0);
  assert.equal(s.helm.passed,1);
  assert.equal(s.helm.aggregateLatencyMs,100);
});
