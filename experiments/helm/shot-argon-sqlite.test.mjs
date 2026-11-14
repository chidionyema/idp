import test from "node:test";
import assert from "node:assert/strict";
import {mkdtempSync,existsSync,rmSync} from "node:fs";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {DatabaseSync} from "node:sqlite";
import {shotPolicy,helmDigest,initialShotState,advanceShot} from "./shot-control.mjs";
import {ArgonHelmSqliteStore} from "./shot-argon-sqlite.mjs";
import {HelmGroundGateway} from "./shot-ground-adapter.mjs";

const SHA="d".repeat(40);
const TASK="founder instructs HELM execution";
function fixture(){
  const root=mkdtempSync(join(tmpdir(),"helm-argon-"));
  const dbPath=join(root,"estate.db");
  const db=new DatabaseSync(dbPath);
  db.exec(
    "CREATE TABLE instruction_ledger ("+
    "instruction_id TEXT PRIMARY KEY,ticket_id TEXT NOT NULL,"+
    "origin_surface TEXT NOT NULL,connectivity_tier TEXT NOT NULL,"+
    "prompt_sha256 TEXT NOT NULL,expected_outcomes_json TEXT NOT NULL,"+
    "stage TEXT NOT NULL,fencing_token INTEGER NOT NULL,"+
    "yield_bps INTEGER NOT NULL DEFAULT 0,fabrication_deltas INTEGER NOT NULL DEFAULT 0,"+
    "reconciled INTEGER NOT NULL DEFAULT 0,initiated_at_ms INTEGER NOT NULL,"+
    "updated_at_ms INTEGER NOT NULL,ledger_hmac TEXT NOT NULL)"
  );
  db.prepare(
    "INSERT INTO instruction_ledger "+
    "(instruction_id,ticket_id,origin_surface,connectivity_tier,"+
    "prompt_sha256,expected_outcomes_json,stage,fencing_token,"+
    "initiated_at_ms,updated_at_ms,ledger_hmac) VALUES "+
    "(?,?,?,?,?,?,?,?,?,?,?)"
  ).run("INS-HELM-SQL-1","IDP-7908","genesis","CONNECTED_TIER1",
    helmDigest(TASK),"[]","INITIATED",1,1,1,"signed-by-argon-fixture");
  db.close();
  const policy=shotPolicy({
    instructionId:"INS-HELM-SQL-1",taskDigest:helmDigest(TASK),
    sourceSha:SHA,model:"ground-agent-model",
    shots:1,verifier:"oracle-runner"
  });
  const store=new ArgonHelmSqliteStore(dbPath);
  function cleanup(){
    store.close();
    rmSync(root,{recursive:true,force:true});
  }
  return {root,dbPath,policy,store,cleanup};
}
const probe=p=>({
  kind:"PROBE",eventId:"PROBE-001",instructionId:p.instructionId,
  probeDigest:helmDigest("single probe"),sourceSha:p.sourceSha
});
const dispatch=p=>({
  kind:"SHOT",eventId:"SHOT-1",instructionId:p.instructionId,
  candidateDigest:helmDigest("single complete delivery"),
  opcode:"DISPATCH_LEGION",model:p.model
});

test("never creates a competing DB when canonical Argon file is missing",()=>{
  const dir=mkdtempSync(join(tmpdir(),"helm-missing-"));
  const missing=join(dir,"not-an-authoritative-database.db");
  assert.throws(()=>new ArgonHelmSqliteStore(missing),/existing shared absolute/);
  assert.equal(existsSync(missing),false);
  rmSync(dir,{recursive:true,force:true});
});

test("an existing SQLite file without instruction_ledger is not the authority",()=>{
  const dir=mkdtempSync(join(tmpdir(),"helm-wrong-"));
  const dbPath=join(dir,"wrong.db");
  new DatabaseSync(dbPath).close();
  assert.throws(()=>new ArgonHelmSqliteStore(dbPath),/Argon instruction_ledger not found/);
  rmSync(dir,{recursive:true,force:true});
});

test("a founder helmet cannot be created before its canonical instruction exists",()=>{
  const x=fixture();
  try{
    assert.throws(()=>x.store.admitFounderPolicy(
      shotPolicy({...x.policy,instructionId:"INS-MISSING"})
    ),/unknown canonical Argon instruction/);
    assert.throws(()=>x.store.policyFor("INS-HELM-SQL-1"),
      /founder helmet not admitted/);
  }finally{x.cleanup();}
});

test("policy is stored in original Argon DB and cannot silently increase to 10 shots",()=>{
  const x=fixture();
  try{
    const admitted=x.store.admitFounderPolicy(x.policy);
    assert.equal(admitted.existing,false);
    assert.equal(x.store.admitFounderPolicy(x.policy).existing,true);
    assert.throws(()=>x.store.admitFounderPolicy(
      shotPolicy({...x.policy,shots:10})
    ),/founder policy immutable/);
    const raw=new DatabaseSync(x.dbPath);
    const tables=raw.prepare("SELECT name FROM sqlite_master WHERE type='table'").all().map(x=>x.name);
    assert.ok(tables.includes("instruction_ledger"));
    assert.ok(tables.includes("helm_instruction_policy"));
    assert.ok(tables.includes("helm_instruction_events"));
    const n=raw.prepare("SELECT COUNT(*) n FROM helm_instruction_policy").get().n;
    assert.equal(n,1);
    raw.close();
  }finally{x.cleanup();}
});

test("atomic admission commits before registered tool callback; restart retains cap",async()=>{
  const x=fixture();
  let calls=0;
  try{
    x.store.admitFounderPolicy(x.policy);
    function gateway(store){
      return new HelmGroundGateway({
        policy:x.policy,store,permittedIntents:["repo.ship"],
        contextProbe:async()=>({facts:"single snapshot"}),
        dispatchRegisteredIntent:async()=>{calls++;throw Error("lost ACK");}
      });
    }
    const g=gateway(x.store);
    await g.probeOnce({opcode:"CONTEXT_PROBE",taskDigest:x.policy.taskDigest,sourceSha:SHA});
    const phases=["BUILD","TEST","COMMIT","PUSH","GREENLANE","VERIFY"];
    await assert.rejects(()=>g.deliver({intent:"repo.ship",args:{ticket:"x"},declaredPhases:phases}),/lost ACK/);
    assert.equal(calls,1);
    const reopened=new ArgonHelmSqliteStore(x.dbPath);
    try{
      const g2=gateway(reopened);
      assert.equal((await g2.snapshot()).status,"AWAITING_GRADE");
      await assert.rejects(()=>g2.deliver({
        intent:"repo.ship",args:{ticket:"x"},declaredPhases:phases
      }),/no unconsumed delivery shot/);
      assert.equal(calls,1);
    }finally{reopened.close();}
  }finally{x.cleanup();}
});

test("optimistic lock conflict prevents concurrent second agent from taking same shot",async()=>{
  const x=fixture();
  try{
    x.store.admitFounderPolicy(x.policy);
    const first=initialShotState(x.policy);
    const e=probe(x.policy);
    const head=advanceShot(x.policy,first,e).head;
    assert.equal(await x.store.append({
      policy:x.policy,instructionId:x.policy.instructionId,
      previousHead:first.head,event:e,expectedNextHead:head
    }),head);
    const second=new ArgonHelmSqliteStore(x.dbPath);
    try{
      const other={...e,eventId:"PROBE-OTHER"};
      await assert.rejects(()=>second.append({
        policy:x.policy,instructionId:x.policy.instructionId,
        previousHead:first.head,event:other,
        expectedNextHead:head
      }),/CAS conflict/);
      assert.equal((await second.read(x.policy.instructionId)).length,1);
    }finally{second.close();}
  }finally{x.cleanup();}
});

test("modified policy or event bytes are independently detectable after restart",async()=>{
  const x=fixture();
  try{
    x.store.admitFounderPolicy(x.policy);
    let s=initialShotState(x.policy);
    const e=probe(x.policy);
    const next=advanceShot(x.policy,s,e);
    await x.store.append({policy:x.policy,instructionId:x.policy.instructionId,
      previousHead:s.head,event:e,expectedNextHead:next.head});
    const external=new DatabaseSync(x.dbPath);
    external.prepare("UPDATE helm_instruction_events SET event_json=? WHERE instruction_id=?")
      .run(JSON.stringify({...next.events[0],probeDigest:helmDigest("TAMPERED")}),x.policy.instructionId);
    await assert.rejects(()=>x.store.append({
      policy:x.policy,instructionId:x.policy.instructionId,
      previousHead:next.head,event:dispatch(x.policy),
      expectedNextHead:helmDigest("fake")
    }),/journal integrity mismatch/);
    external.prepare("UPDATE helm_instruction_events SET event_json=? WHERE instruction_id=?")
      .run(JSON.stringify(next.events[0]),x.policy.instructionId);
    external.prepare("UPDATE helm_instruction_policy SET policy_json=? WHERE instruction_id=?")
      .run(JSON.stringify({...x.policy,shots:10}),x.policy.instructionId);
    assert.throws(()=>x.store.policyFor(x.policy.instructionId),/integrity mismatch/);
    external.close();
  }finally{x.cleanup();}
});

test("refuses an unadmitted policy before the ground tool can perform any IO",async()=>{
  const x=fixture();
  let touches=0;
  try{
    const g=new HelmGroundGateway({
      policy:x.policy,store:x.store,
      permittedIntents:["repo.ship"],
      contextProbe:async()=>{touches++;},
      dispatchRegisteredIntent:async()=>{touches++;}
    });
    await assert.rejects(()=>g.probeOnce({
      opcode:"CONTEXT_PROBE",taskDigest:x.policy.taskDigest,sourceSha:SHA
    }),/founder helmet not admitted/);
    assert.equal(touches,0);
  }finally{x.cleanup();}
});
