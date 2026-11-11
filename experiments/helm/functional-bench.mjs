/**
 * HELM-FUNC: independent executable agent benchmark.
 * Generated Python is executed only inside an isolated Docker container with no
 * network, secrets, elevated privileges or host filesystem beyond readonly fixtures.
 * Model input never includes independent grader source.
 */
import {spawnSync} from "node:child_process";
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,rmSync,chmodSync,renameSync} from "node:fs";
import {tmpdir} from "node:os";
import {join,resolve} from "node:path";
import {fileURLToPath} from "node:url";
import {createHash} from "node:crypto";
import {messagesFor,inference,parseAction,checkPython} from "./helm.mjs";

const sha = s => createHash("sha256").update(s).digest("hex");
const image = "python:3.12-alpine";
const sample = JSON.parse(readFileSync(new URL("./fixtures/functional.json",import.meta.url),"utf8"));
const references=JSON.parse(readFileSync(new URL("./fixtures/functional-references.json",import.meta.url),"utf8"));
const arms = ["baseline","skills","memory","memory_repair","helm"];

function programFromAction(raw) {
  const envelope=parseAction(raw,["EMIT_PATCH"]);
  if(!envelope.ok) return {ok:false,reason:"schema: "+envelope.error};
  let code=envelope.action.payload;
  if(typeof code!=="string")return {ok:false,reason:"payload is not a string"};
  try {
    const obj=JSON.parse(code);
    if(obj && typeof obj==="object" && typeof obj.code==="string") code=obj.code;
  }catch{}
  const check=checkPython(code);
  if(!check.ok)return {ok:false,reason:"static: "+check.error};
  return {ok:true,code};
}

export function runIndependentTests(testCase,code,{timeoutMs=25000,runner=spawnSync}={}) {
  const check=checkPython(code);
  if(!check.ok)return {passed:false,kind:"static",detail:check.error,tests:0};
  const dir=mkdtempSync(join(tmpdir(),"helm-functional-"));
  // The image runs as the unprivileged nobody user: only the temporary fixture dir is mounted.
  chmodSync(dir,0o755);
  const launcher = [
    "import unittest,sys",
    'sys.path.insert(0,"/work")',
    "import oracle",
    "suite=unittest.TestLoader().loadTestsFromModule(oracle)",
    "result=unittest.TextTestRunner(stream=sys.stderr,verbosity=0).run(suite)",
    'print("HELM_FUNCTIONAL_RESULT tests="+str(result.testsRun)+" ok="+str(int(result.wasSuccessful())),flush=True)',
    "sys.exit(0 if result.wasSuccessful() and result.testsRun>0 else 1)",
  ].join("\n")+"\n";
  try {
    writeFileSync(join(dir,"candidate.py"),code,{mode:0o644,flag:"wx"});
    writeFileSync(join(dir,"oracle.py"),testCase.oracle,{mode:0o644,flag:"wx"});
    writeFileSync(join(dir,"run_oracle.py"),launcher,{mode:0o644,flag:"wx"});
    const args=["run","--rm","--network=none","--read-only","--cap-drop=ALL",
      "--security-opt=no-new-privileges","--pids-limit=64","--memory=192m",
      "--cpus=0.75","--user=65534:65534",
      "--tmpfs=/tmp:rw,nosuid,nodev,size=8m",
      "--mount","type=bind,source="+dir+",target=/work,readonly",
      "--workdir=/work",image,"python","-B","/work/run_oracle.py"];
    const res=runner("docker",args,{encoding:"utf8",timeout:timeoutMs,maxBuffer:65536,
      shell:false,env:{PATH:process.env.PATH||"/usr/bin:/bin",HOME:"/tmp"}});
    const stdout=String(res.stdout||"");
    const match=stdout.match(/HELM_FUNCTIONAL_RESULT tests=(\d+) ok=([01])\s*$/);
    const tests=match?Number(match[1]):0;
    const passed=res.status===0 && match && tests===testCase.expectedTests && match[2]==="1";
    const detail=passed?"all independent tests passed":
      res.error?.code||res.signal||String(res.stderr||res.stdout||"missing verifier receipt").slice(-2200);
    return {passed:Boolean(passed),kind:res.error?"sandbox":tests?"functional":"sandbox",
      tests,expectedTests:testCase.expectedTests,detail:String(detail).slice(-2200)};
  }finally{rmSync(dir,{recursive:true,force:true});}
}

function atomicWrite(result,path) {
  mkdirSync(resolve("experiments/helm/out"),{recursive:true});
  const file=resolve("experiments/helm/out",path);
  const temp=file+".tmp-"+process.pid;
  writeFileSync(temp,JSON.stringify(result,null,2)+"\n",{mode:0o600});
  renameSync(temp,file);
}

export async function runFunctional({tasks=sample.cases,evidence=sample.evidence,model,url,token,
  maxAttempts=2,armSet=arms,fn=inference,testFn=runIndependentTests,sourceSha="local",write=()=>{}}={}) {
  if(!model||!url)throw Error("model and HTTPS inference URL required");
  const records=[];
  const out={schema:"helm.functional.receipt.v1",kind:fn===inference?"real-model":"fixture-model",
    codeSha:sourceSha,model,createdAt:new Date().toISOString(),
    corpusSha256:sha(JSON.stringify(tasks)),oracleMode:"independent Python unittest in isolated Docker",
    arms:armSet,records,summary:null};
  for(let t=0;t<tasks.length;t++){
    const task=tasks[t];
    const order=t%2===0?armSet:[...armSet].reverse();
    for(const arm of order){
      const messages=messagesFor(arm,task,evidence);
      const attempts=[];
      let verifiedProgram=null;
      const repairEnabled=arm==="helm"||arm==="memory_repair";
      for(let n=0;n<(repairEnabled?maxAttempts:1);n++){
        const calledAt=performance.now();
        try{
          const reply=await fn({url,token,model,messages,timeoutMs:45000});
          const payload=programFromAction(reply.answer);
          const outcome=payload.ok?testFn(task,payload.code):
            {passed:false,kind:"schema-or-static",tests:0,detail:payload.reason};
          attempts.push({n:n+1,answerSha256:sha(reply.answer),latencyMs:reply.latencyMs,
            usage:reply.usage||null,modelReturned:reply.modelReturned||null,
            outputShape:payload.ok?"python-action":payload.reason,
            ...outcome});
          if(outcome.passed){
            // Preserve only program bytes that actually passed independent execution.
            // Source is public/synthetic fixture data; do not collect estate-private code here.
            verifiedProgram={source:payload.code,sha256:sha(payload.code),
              testCount:outcome.tests,modelReturned:reply.modelReturned||model};
            break;
          }
          if(!repairEnabled||n+1>=maxAttempts)break;
          messages.push({role:"assistant",content:reply.answer});
          // Independent test feedback, never the hidden oracle source or gold implementation.
          messages.push({role:"user",content:"Independent verifier rejected this proposed Python code: "+
            String(outcome.detail).slice(0,900)+". Return a revised valid JSON EMIT_PATCH action, payload complete corrected Python source."});
        }catch(error){
          attempts.push({n:n+1,passed:false,kind:"provider-error",tests:0,
            latencyMs:Math.round(performance.now()-calledAt),
            detail:String(error.message||error).slice(0,250)});
          break;
        }
      }
      const final=attempts.at(-1);
      records.push({taskId:task.id,arm,passed:final?.passed===true,attempts,
        sourceSha,taskSha:sha(task.question),oracleSha:sha(task.oracle),
        ...(final?.passed===true && verifiedProgram ? {verifiedProgram} : {})});
      out.summary=summarise(records,armSet);
      write(out);
    }
  }
  return out;
}

export function summarise(records,armNames=arms) {
  const result={};
  for(const arm of armNames){
    const rows=records.filter(x=>x.arm===arm);
    result[arm]={passed:rows.filter(x=>x.passed).length,total:rows.length,
      providerErrors:rows.filter(x=>x.attempts.some(a=>a.kind==="provider-error")).length,
      attempts:rows.reduce((n,x)=>n+x.attempts.length,0),
      aggregateLatencyMs:rows.reduce((n,x)=>n+x.attempts.reduce((a,b)=>a+(b.latencyMs||0),0),0)};
  }
  return result;
}

if(process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const mode=process.argv[2]||"test";
  if(mode==="test"){
    // Two-sided oracle contract: every test must accept a known-good implementation
    // and reject an empty patch. This catches broken or vacuous benchmarks.
    const evidence=[];
    for(const c of sample.cases){
      const empty=runIndependentTests(c,"# intentionally empty patch\n");
      if(empty.passed)throw Error("vacuous oracle accepted empty patch: "+c.id);
      const correct=runIndependentTests(c,references[c.id]);
      if(!correct.passed)throw Error("invalid oracle/reference for "+c.id+": "+correct.detail);
      evidence.push({id:c.id,negativeRejected:true,referencePassed:true,tests:correct.tests});
    }
    console.log(JSON.stringify({grade:"TWO_SIDED_ORACLES_PASS",evidence}));
  }else if(mode==="live" || mode==="yield"){
    const model=process.env.HELM_MODEL;
    const url=process.env.HELM_INFERENCE_URL;
    const singleTask=sample.cases.find(t=>t.id===(process.env.HELM_YIELD_TASK_ID||"FUNC-INTENT-AUTHORITY"));
    if(mode==="yield" && !singleTask)throw Error("unknown HELM_YIELD_TASK_ID");
    const trialName=mode==="yield"?"yield-trial.json":"functional-trial.json";
    const result=await runFunctional({model,url,token:process.env.HELM_TOKEN,
      tasks:mode==="yield"?[singleTask]:sample.cases,
      armSet:mode==="yield"?["helm"]:arms,
      sourceSha:process.env.GITHUB_SHA||"local",
      write:x=>atomicWrite(x,trialName)});
    console.log(JSON.stringify({grade:"FUNCTIONAL_TRIAL_RECORDED",mode,model,summary:result.summary,
      corpusSha256:result.corpusSha256,sourceSha:result.codeSha}));
    if(mode==="yield"){
      const {harvestVerified,replayVerified}=await import("./operational-memory.mjs");
      const memory=harvestVerified({trial:result,tasks:[singleTask]});
      atomicWrite(memory,"verified-program-memory.json");
      const replay=replayVerified({memory,tasks:[singleTask]});
      atomicWrite(replay,"verified-program-replay.json");
      console.log(JSON.stringify({status:"END_TO_END_EXPERIENCE_YIELD",
        accepted:memory.accepted,
        replayed:replay.passed,independentTestsPassed:replay.independentTestsPassed,
        replayModelCalls:replay.modelCalls,
        modelCalls:result.summary.helm.attempts,
        errors:result.summary.helm.providerErrors}));
      if(replay.passed<1 || replay.passed!==memory.accepted)process.exitCode=2;
    }else if(Object.values(result.summary).some(x=>x.providerErrors>0))process.exitCode=2;
  }else throw Error("usage: node functional-bench.mjs [test|live]");
}
