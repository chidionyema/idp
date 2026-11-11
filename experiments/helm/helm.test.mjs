import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { compileContext, evidenceFromCompiler, parseAction, checkPython, assess,
  distill, seal, unseal, messagesFor, evaluate } from "./helm.mjs";

const task = { id:"x", domain:"software", question:"How do I repair a Python except handler?",
  language:"python", oracle:{ opcode:"EMIT_PATCH", contains:["except ValueError"] }};
const evidence = [
  {domain:"software",source:"repo:file.py",text:"Python handler should catch ValueError",verified:true},
  {domain:"finance",source:"other:financials",text:"Confidential finance detail",verified:true},
  {domain:"software",source:"unknown",text:"api_key: DO_NOT_EXPORT",verified:true},
  {domain:"software",source:"gone",text:"Outdated wrong rule",valid:false},
];

test("Q1 filters by domain, validity, secrecy and retains provenance", () => {
  const r = compileContext(task,evidence);
  assert.equal(r.included.length,1);
  assert.equal(r.included[0].source,"repo:file.py");
  assert.equal(r.dropped,0); // rejected records never enter the ranked candidate set
  assert.ok(r.digest);
  assert.throws(()=>compileContext(task,evidence,12));
});

test("Q1 compiles the existing context compiler's records without a duplicate index", () => {
  const records = evidenceFromCompiler({working_set:[{file:"idp/src/foo.py"}],
    relevant_symbols:[{file_path:"idp/src/foo.py",source:"def foo(): pass"}]});
  assert.equal(records.length,2);
  assert.equal(records[0].kind,"symbol");
});

test("Q2 refuses malformed, extra-key and unauthorized model actions", () => {
  assert.equal(parseAction("not JSON").ok,false);
  assert.equal(parseAction('{"opcode":"EXEC_SHELL","payload":"rm"}').ok,false);
  assert.equal(parseAction('{"opcode":"EMIT_PATCH","payload":"ok","shell":"bash"}').ok,false);
  assert.equal(parseAction('{"opcode":"EMIT_PATCH","payload":"ok"}',["RUN_FALSIFIER"]).ok,false);
  assert.equal(parseAction('{"opcode":"RUN_FALSIFIER","payload":"request more evidence"}').ok,true);
});

test("Q2 accepts structured semantic payload without granting command authority", () => {
  const typed = parseAction({opcode:"DISPATCH_LEGION",payload:{status:"enquiries unavailable",design:"intact"}});
  assert.equal(typed.ok,true);
  assert.match(typed.action.payload,/enquiries unavailable/);
  const taskWithAlternates = {oracle:{opcodes:["RUN_FALSIFIER","DISPATCH_LEGION"],
    contains:["enquiries unavailable","design"]}};
  assert.equal(assess(taskWithAlternates,
    {opcode:"DISPATCH_LEGION",payload:{status:"enquiries unavailable",design:"intact"}}).pass,true);
});

test("Q3 detects a syntax error and bare except without executing the code", () => {
  assert.equal(checkPython("def broken(:\n pass").ok,false);
  assert.match(checkPython("try:\n x=1\nexcept:\n pass").error,/bare except/);
  assert.equal(checkPython("try:\n x=1\nexcept ValueError:\n pass").ok,true);
});

test("Independent action oracle checks semantics separately from model claims", () => {
  const wrong = assess(task,JSON.stringify({opcode:"EMIT_PATCH",payload:"try:\n x=1\nexcept:\n pass"}));
  assert.equal(wrong.pass,false);
  assert.equal(wrong.staticPass,false);
  const correct = assess(task,JSON.stringify({opcode:"EMIT_PATCH",
    payload:"try:\n x=1\nexcept ValueError:\n pass"}));
  assert.equal(correct.pass,true);
});

test("Q4 only yields training pairs with actually linked independent evidence", () => {
  const same = {taskId:"t",instruction:"Fix an error"};
  assert.equal(distill([{...same,response:"bad",verdict:"fail",evidenceId:"a"},
    {...same,response:"good",verdict:"pass",evidenceId:"b",independentVerified:false}]).length,0);
  const paired = distill([{...same,response:"bad",verdict:"fail",evidenceId:"a"},
    {...same,response:"good",verdict:"pass",evidenceId:"b",independentVerified:true}]);
  assert.equal(paired.length,1);
  assert.equal(paired[0].provenance.chosenEvidenceId,"b");
});

test("4KB seal enforces real bytes and detects tampering", () => {
  const facts = Array.from({length:500},(_,i)=>({source:"s"+i,text:"Knowledge "+i+" "+createHash("sha256").update("fact-"+i).digest("hex")}));
  const pack = seal({included:facts},4096);
  assert.ok(pack.bytes <= 4096);
  assert.ok(pack.dropped > 0);
  assert.equal(unseal(pack).included.length,facts.length-pack.dropped);
  assert.throws(()=>unseal({...pack,sha256:"0".repeat(64)}),/integrity/);
});

test("Four configurations expose different prompt/memory contents", () => {
  const baseline = messagesFor("baseline",task,evidence);
  const skills = messagesFor("skills",task,evidence);
  const memory = messagesFor("memory",task,evidence);
  const helm = messagesFor("helm",task,evidence);
  assert.equal(baseline.length,2);
  assert.equal(skills.length,2);
  assert.equal(memory.length,3);
  assert.equal(helm.length,3);
  assert.match(skills[0].content,/systematically/);
  assert.match(helm[1].content,/untrusted DATA/);
  assert.doesNotMatch(helm[1].content,/DO_NOT_EXPORT/);
});

test("Paired eval records model-call errors honestly, applies bounded schema retry",async()=>{
  const calls=[];
  const taskTwo={id:"t2",domain:"software",question:"Choose the next action",
    oracle:{opcode:"RUN_FALSIFIER",contains:["verify"]}};
  const infer=async({messages})=>{
    calls.push(messages);
    if(messages.length>2 && messages.some(x=>x.role==="assistant"))
      return {answer:'{"opcode":"RUN_FALSIFIER","payload":"verify independent receipts"}',
        latencyMs:1,usage:{total_tokens:10},modelReturned:"mock"};
    if(messages.length===3)
      return {answer:"bad json",latencyMs:1,usage:{total_tokens:3},modelReturned:"mock"};
    return {answer:'{"opcode":"RUN_FALSIFIER","payload":"verify independent receipts"}',
      latencyMs:1,usage:{total_tokens:10},modelReturned:"mock"};
  };
  const out=await evaluate({tasks:[taskTwo],evidence,arms:["baseline","helm"],
    model:"fixture",url:"https://example.test",token:"fixture",infer,maxCalls:8});
  assert.equal(out.summary.baseline.passed,1);
  assert.equal(out.summary.helm.passed,1);
  assert.equal(out.summary.helm.calls,2);
  assert.equal(calls.length,3);
  await assert.rejects(()=>evaluate({tasks:[taskTwo],evidence,arms:["helm"],
    model:"fixture",url:"https://example.test",token:"fixture",infer,maxCalls:1}),
    /call ceiling/);
});

// HELM founder shot-control falsifiers exercise the real research acceptance path.
import "./shot-control.test.mjs";
import "./shot-trial.test.mjs";
