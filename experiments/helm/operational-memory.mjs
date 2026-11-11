/**
 * HELM verified-experience memory (internal research).
 *
 * A program only enters the store after its generating trial reports success AND
 * an independent test runner re-executes it against the exact pinned oracle.
 * Reuse is only allowed for an identical task+oracle fingerprint and reruns
 * independent tests each time. No model call, no generalisation claim.
 *
 * The SHA-256 fingerprints provide integrity checks, NOT signer authentication.
 * Production trust must come from the existing estate provenance/audit system.
 */
import {createHash} from "node:crypto";
import {readFileSync,writeFileSync,mkdirSync,renameSync} from "node:fs";
import {resolve,dirname} from "node:path";
import {fileURLToPath} from "node:url";
import {runIndependentTests} from "./functional-bench.mjs";

const sha=s=>createHash("sha256").update(s).digest("hex");
const fixture=JSON.parse(readFileSync(new URL("./fixtures/functional.json",import.meta.url),"utf8"));

export function fingerprint(task){
  if(!task || typeof task.question!=="string" || typeof task.oracle!=="string")throw Error("task and oracle required");
  return {taskSha256:sha(task.question),oracleSha256:sha(task.oracle)};
}

export function harvestVerified({trial,tasks=fixture.cases,verify=runIndependentTests,allowFixture=false}={}){
  if(!trial || (trial.kind!=="real-model" && !(allowFixture && trial.kind==="fixture-model")))
    throw Error("refuse ungrounded or mock-generated trajectory");
  const byId=new Map(tasks.map(t=>[t.id,t]));
  const entries=[]; const rejected=[];
  for(const row of trial.records||[]){
    const t=byId.get(row.taskId);
    const evidence=row.verifiedProgram;
    if(!row.passed || !evidence)continue;
    const fp=t?fingerprint(t):null;
    if(!t || row.taskSha!==fp.taskSha256 || row.oracleSha!==fp.oracleSha256){
      rejected.push({taskId:row.taskId,arm:row.arm,reason:"task-or-oracle-mismatch"});continue;
    }
    const code=evidence.source;
    if(typeof code!=="string" || code.length>12000 || sha(code)!==evidence.sha256){
      rejected.push({taskId:row.taskId,arm:row.arm,reason:"program-integrity-mismatch"});continue;
    }
    const attestation=verify(t,code);
    if(!attestation.passed || attestation.tests!==t.expectedTests){
      rejected.push({taskId:row.taskId,arm:row.arm,reason:"independent-reverification-failed",
        detail:String(attestation.detail||"").slice(0,250)});continue;
    }
    entries.push({schema:"helm.verified-program.v1",taskId:t.id,...fp,
      code,codeSha256:sha(code),expectedTests:t.expectedTests,
      origin:{arm:row.arm,model:evidence.modelReturned||trial.model,
        generatingRun:trial.codeSha,attemptDigest:row.attempts?.at(-1)?.answerSha256||null},
      verification:{kind:"independent-execution-recheck",
        testsPassed:t.expectedTests,verifier:"docker-python-unittest",
        sourceCorpus:trial.corpusSha256}});
  }
  return {schema:"helm.verified-memory.v1",algorithm:"exact-task+oracle-only",
    requiresIndependentReverification:true,sourceTrialSha:trial.codeSha,
    accepted:entries.length,rejected,entries};
}

export function replayVerified({memory,tasks=fixture.cases,verify=runIndependentTests}={}){
  if(memory?.schema!=="helm.verified-memory.v1")throw Error("invalid HELM memory format");
  const byId=new Map(tasks.map(t=>[t.id,t]));
  const results=[];
  for(const e of memory.entries||[]){
    const t=byId.get(e.taskId);
    const fp=t?fingerprint(t):null;
    if(!t || e.taskSha256!==fp.taskSha256 || e.oracleSha256!==fp.oracleSha256){
      results.push({taskId:e.taskId,passed:false,reason:"task-or-oracle-changed",modelCalls:0});continue;
    }
    if(sha(e.code)!==e.codeSha256 || e.expectedTests!==t.expectedTests){
      results.push({taskId:e.taskId,passed:false,reason:"program-integrity-mismatch",modelCalls:0});continue;
    }
    const verdict=verify(t,e.code);
    results.push({taskId:e.taskId,originArm:e.origin?.arm,originModel:e.origin?.model,
      passed:verdict.passed===true && verdict.tests===t.expectedTests,
      tests:verdict.tests||0,expected:t.expectedTests,modelCalls:0,
      reason:verdict.passed?"fresh-independent-execution":"execution-failed",
      codeSha256:e.codeSha256});
  }
  return {schema:"helm.memory-replay.v1",
    claimedScope:"exact-task verified-experience reuse; no generalisation or fine-tuning",
    passed:results.filter(r=>r.passed).length,
    total:results.length,
    independentTestsPassed:results.filter(r=>r.passed).reduce((n,r)=>n+r.tests,0),
    modelCalls:0,results};
}

function save(path,value){
  const p=resolve(path),tmp=p+".tmp-"+process.pid;
  mkdirSync(dirname(p),{recursive:true});
  writeFileSync(tmp,JSON.stringify(value,null,2)+"\n",{mode:0o600});
  renameSync(tmp,p);
}

if(process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  try{
    const command=process.argv[2],path=process.argv[3];
    if(command==="harvest"){
      if(!path)throw Error("provide trial receipt JSON");
      const trial=JSON.parse(readFileSync(resolve(path),"utf8"));
      const memory=harvestVerified({trial});
      save("experiments/helm/out/verified-program-memory.json",memory);
      const replay=replayVerified({memory});
      save("experiments/helm/out/verified-program-replay.json",replay);
      console.log(JSON.stringify({status:"HARVEST_AND_REPLAY",accepted:memory.accepted,
        rejected:memory.rejected.length,modelCallsDuringReplay:replay.modelCalls,
        passed:replay.passed,total:replay.total,independentTestsPassed:replay.independentTestsPassed}));
      if(replay.passed!==memory.accepted || memory.rejected.length)process.exitCode=2;
    }else if(command==="replay"){
      if(!path)throw Error("provide verified memory JSON");
      const memory=JSON.parse(readFileSync(resolve(path),"utf8"));
      const result=replayVerified({memory});
      save("experiments/helm/out/verified-program-replay.json",result);
      console.log(JSON.stringify({status:"INDEPENDENT_REPLAY",passed:result.passed,total:result.total,
        modelCalls:result.modelCalls,independentTestsPassed:result.independentTestsPassed}));
      if(result.passed!==result.total)process.exitCode=2;
    }else throw Error("usage: node operational-memory.mjs [harvest TRIAL.json|replay MEMORY.json]");
  }catch(error){
    console.error("HELM_MEMORY_ERROR:",String(error.message||error).slice(0,300));
    process.exitCode=1;
  }
}
