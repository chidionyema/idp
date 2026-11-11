import test from "node:test";
import assert from "node:assert/strict";
import {shotPolicy,helmDigest} from "./shot-control.mjs";
import {HelmGroundGateway,FixtureShotStore} from "./shot-ground-adapter.mjs";

const SHA="c".repeat(40);
const CONTEXT="task authorised by Argon";
const plan=["BUILD","TEST","COMMIT","PUSH","GREENLANE","VERIFY"];
const make=(shots=1,changes={})=>{
  const policy=shotPolicy({
    instructionId:"INS-GROUND-01",taskDigest:helmDigest(CONTEXT),
    sourceSha:SHA,model:"agent-router-v1",shots,
    verifier:"independent-ci",...changes
  });
  const store=new FixtureShotStore();
  const calls={probes:0,dispatches:0};
  const gateway=new HelmGroundGateway({
    policy,store,permittedIntents:["repo.delivery"],
    contextProbe:async()=>{calls.probes++;return {branch:"main",sha:SHA};},
    dispatchRegisteredIntent:async request=>{
      calls.dispatches++;return {accepted:true,jobId:"job-"+calls.dispatches,request};
    }
  });
  const request={opcode:"CONTEXT_PROBE",taskDigest:helmDigest(CONTEXT),sourceSha:SHA};
  const candidate={intent:"repo.delivery",args:{repo:"idp",target:"candidate"},
    declaredPhases:plan};
  const candidateDigest=helmDigest({intent:candidate.intent,args:candidate.args,phases:plan});
  return {gateway,store,policy,calls,request,candidate,candidateDigest};
};
const fail=async(f,reason)=>assert.rejects(f,reason);

test("ground troop gets ONE real probe and one complete authorized delivery",async()=>{
  const x=make();
  const probe=await x.gateway.probeOnce(x.request);
  assert.equal(probe.sha,SHA);
  assert.equal(x.calls.probes,1);
  const receipt=await x.gateway.deliver(x.candidate);
  assert.equal(receipt.accepted,true);
  assert.equal(x.calls.dispatches,1);
  assert.equal(receipt.request.instructionId,"INS-GROUND-01");
  assert.equal(receipt.request.intent,"repo.delivery");
  assert.equal((await x.gateway.snapshot()).status,"AWAITING_GRADE");
  const outcome=await x.gateway.reconcile({
    candidateDigest:x.candidateDigest,evidenceDigest:helmDigest("ci:green"),
    passed:true,verifier:"independent-ci"
  });
  assert.equal(outcome.status,"VERIFIED");
  assert.equal(outcome.candidateSubmissions,1);
  assert.equal(outcome.liveExecutionVerified,false);
});

test("a second probe cannot call tool even when model tries",async()=>{
  const x=make(10);
  await x.gateway.probeOnce(x.request);
  await fail(()=>x.gateway.probeOnce(x.request),/probe budget spent/);
  assert.equal(x.calls.probes,1);
});

test("a failing probe consumes the one tool grant BEFORE its side effect",async()=>{
  const x=make();
  let calls=0;
  x.gateway.contextProbe=async()=>{calls++;throw Error("network down");};
  await fail(()=>x.gateway.probeOnce(x.request),/network down/);
  await fail(()=>x.gateway.probeOnce(x.request),/probe budget spent/);
  assert.equal(calls,1);
  assert.equal((await x.gateway.snapshot()).contextProbes,1);
});

test("storage outage stops both probes and mutation BEFORE effects",async()=>{
  const x=make();
  x.store.append=async()=>{throw Error("DB unavailable");};
  await fail(()=>x.gateway.probeOnce(x.request),/DB unavailable/);
  assert.equal(x.calls.probes,0);
  assert.equal(x.calls.dispatches,0);
});

test("one-shot exhausted after a negative independently evidenced grade",async()=>{
  const x=make(1);
  await x.gateway.probeOnce(x.request);
  await x.gateway.deliver(x.candidate);
  const s=await x.gateway.reconcile({
    candidateDigest:x.candidateDigest,passed:false,
    evidenceDigest:helmDigest("CI red"),verifier:"independent-ci"
  });
  assert.equal(s.status,"EXHAUSTED");
  await fail(()=>x.gateway.deliver(x.candidate),/no unconsumed delivery shot/);
  assert.equal(x.calls.dispatches,1);
});

test("two-shot only permits repair after independent grade",async()=>{
  const x=make(2);
  await x.gateway.probeOnce(x.request);
  await x.gateway.deliver(x.candidate);
  await fail(()=>x.gateway.deliver(x.candidate),/no unconsumed delivery shot/);
  await x.gateway.reconcile({
    candidateDigest:x.candidateDigest,passed:false,
    evidenceDigest:helmDigest("CI red"),verifier:"independent-ci"
  });
  const retry={...x.candidate,args:{...x.candidate.args,target:"patched"}};
  await x.gateway.deliver(retry);
  assert.equal(x.calls.dispatches,2);
  const digest=helmDigest({intent:retry.intent,args:retry.args,phases:plan});
  const ok=await x.gateway.reconcile({
    candidateDigest:digest,passed:true,
    evidenceDigest:helmDigest("CI green"),verifier:"independent-ci"
  });
  assert.equal(ok.status,"VERIFIED");
});

test("crash after external command returned unknown NEVER permits duplicate dispatch",async()=>{
  const x=make(10);
  await x.gateway.probeOnce(x.request);
  x.gateway.dispatchRegisteredIntent=async()=>{x.calls.dispatches++;throw Error("lost HTTP ACK");};
  await fail(()=>x.gateway.deliver(x.candidate),/lost HTTP ACK/);
  const recovered=new HelmGroundGateway({
    policy:x.policy,store:x.store,
    permittedIntents:["repo.delivery"],
    contextProbe:async()=>{x.calls.probes++;},
    dispatchRegisteredIntent:async()=>{x.calls.dispatches++;}
  });
  await fail(()=>recovered.deliver(x.candidate),/no unconsumed delivery shot/);
  assert.equal(x.calls.dispatches,1);
  assert.equal((await recovered.snapshot()).status,"AWAITING_GRADE");
  const r=await recovered.reconcile({
    candidateDigest:x.candidateDigest,passed:false,
    evidenceDigest:helmDigest("later independent readback"),
    verifier:"independent-ci"
  });
  assert.equal(r.status,"READY");
  assert.equal(r.candidateSubmissions,1);
});

test("invalid data and unregistered intent never call the executor",async()=>{
  const x=make(4);
  await x.gateway.probeOnce(x.request);
  for(const cand of [
    {...x.candidate,intent:"shell.exec"},
    {...x.candidate,declaredPhases:["BUILD","COMMIT"]},
    {...x.candidate,args:"rm -rf /"},
    {...x.candidate,declaredPhases:[...plan,"SKIP_GATE"]},
    null
  ])await fail(()=>x.gateway.deliver(cand),/complete registered delivery intent/);
  assert.equal(x.calls.dispatches,0);
});

test("missing independent receipt cannot satisfy a real code change",async()=>{
  const x=make(1);
  await x.gateway.probeOnce(x.request);
  await x.gateway.deliver(x.candidate);
  await fail(()=>x.gateway.reconcile({
    candidateDigest:x.candidateDigest,passed:true,
    verifier:"independent-ci",evidenceDigest:""
  }),/external evidence digest/);
  await fail(()=>x.gateway.reconcile({
    candidateDigest:x.candidateDigest,passed:true,
    verifier:"agent-router-v1",evidenceDigest:helmDigest("agent claimed green")
  }),/verifier identity mismatch/);
});

test("old model cannot replace founder policy after receiving a task",async()=>{
  const x=make(1);
  await x.gateway.probeOnce(x.request);
  const other=shotPolicy({...x.policy,shots:10});
  const competing=new HelmGroundGateway({
    policy:other,store:x.store,permittedIntents:["repo.delivery"],
    contextProbe:async()=>{},dispatchRegisteredIntent:async()=>{}
  });
  await fail(()=>competing.snapshot(),/journal integrity mismatch|policy mutation/);
});

test("replaying a failed storage CAS never invokes the mutable external command",async()=>{
  const x=make();
  await x.gateway.probeOnce(x.request);
  x.store.append=async()=>{throw Error("concurrent CAS conflict");};
  await fail(()=>x.gateway.deliver(x.candidate),/CAS conflict/);
  assert.equal(x.calls.dispatches,0);
});

test("new gateway refuses a nontransactional store or missing real tool capability",()=>{
  const p=make().policy;
  assert.throws(()=>new HelmGroundGateway({
    policy:p,store:{read:()=>[]},contextProbe:async()=>{},
    dispatchRegisteredIntent:async()=>{},permittedIntents:["repo.delivery"]
  }),/transactional ledger/);
  assert.throws(()=>new HelmGroundGateway({
    policy:p,store:new FixtureShotStore(),
    contextProbe:async()=>{},permittedIntents:["repo.delivery"]
  }),/registered probe and intent door/);
});

test("context request cannot fetch stale or unrelated source",async()=>{
  const x=make();
  await fail(()=>x.gateway.probeOnce({
    ...x.request,sourceSha:"d".repeat(40)
  }),/stale context request/);
  assert.equal(x.calls.probes,0);
});
