/**
 * HELM-K paired trial. Existing HELM context/validator and same model route.
 *
 * Arms: baseline-control (ordinary prompt, 10-call safety cap) and HELM
 * with a chosen k in [1,10] (one context probe, k complete proposals).
 * Each pair has the same task and oracle; oracle remains outside model input.
 *
 * This is an EVALUATION of model proposals, not authority to execute shell,
 * push commits, run Greenlane, or attest production yield. Code-producing
 * agents still use the existing estate intent executor and independent CI.
 */
import {readFileSync, mkdirSync, renameSync, writeFileSync} from "node:fs";
import {resolve,dirname} from "node:path";
import {fileURLToPath} from "node:url";
import {spawnSync} from "node:child_process";
import {messagesFor,inference,parseAction,assess} from "./helm.mjs";
import {shotPolicy, initialShotState, advanceShot, shotReport, helmDigest} from "./shot-control.mjs";

const ID=/^[A-Za-z0-9._-]{3,100}$/;

function ensureTask(task) {
  if (!task || typeof task.id!=="string" || !ID.test(task.id) ||
    typeof task.question!=="string" || !task.question.trim() ||
    !task.oracle || typeof task.oracle!=="object")
    throw Error("HELM trial requires named task, complete question and withheld oracle");
}

function profilePrompt(shots) {
  return "HELM experimental behavioural helmet. Budget: at most " + shots +
    " complete proposed actions, with only ONE context probe performed before execution. " +
    "This is not a request for a plan or preliminary answer. Emit exactly ONE complete, " +
    "self-contained, executable-intent JSON action {opcode,payload}, no preamble and no " +
    "follow-up questions. Include all necessary algorithmic content in the SINGLE payload " +
    "rather than proposing a series of partial tool calls. If a repository edit is " +
    "requested, the authorized executor (not you) handles build, tests, commit, push, " +
    "Greenlane and live readback. Never claim those steps completed without receipts. " +
    "An independent verifier, not your own narrative, grades this attempt.";
}

function armDefinition(name) {
  if (name==="control")return {arm:name,shots:10,profile:"control"};
  const m=/^helm-([1-9]|10)$/.exec(name);
  if(!m)throw Error("invalid experimental arm: "+name);
  return {arm:name,shots:Number(m[1]),profile:"helmet"};
}

function assertProviderForTask(url, token, task) {
  if(typeof url!=="string" || !/^https:\/\//.test(url))
    throw Error("HELM requires an explicit HTTPS model route");
  const publicFree=url==="https://ai-gateway.kilo.ai/api/v1/chat/completions";
  if (publicFree && !token && task.classification!=="public-synthetic")
    throw Error("anonymous provider cannot receive non-public task");
}

const expectedTokenCount = usage => (
  usage && Number.isFinite(Number(usage.total_tokens)) ? Number(usage.total_tokens) : null
);

export async function runOneArm({task,arm,evidence=[],model,url,token,
  sourceSha, infer=inference, grade=assess, timeoutMs=45000}={}) {
  ensureTask(task);
  assertProviderForTask(url,token,task);
  const a=armDefinition(arm);
  const instructionId="HELM-"+task.id+"-"+arm;
  if (!ID.test(instructionId))
    throw Error("instructionId too long: "+instructionId);
  const policy=shotPolicy({
    instructionId,
    taskDigest:helmDigest(task.question), sourceSha, model,
    shots:a.shots, profile:a.profile, verifier:"independent-oracle"
  });
  let state=initialShotState(policy);
  const initialMessages=messagesFor(a.profile==="helmet"?"helm":"baseline",task,evidence);
  const messages=structuredClone(initialMessages);
  if(a.profile==="helmet")
    messages.splice(1,0,{role:"system",content:profilePrompt(a.shots)});
  // The canonical context compiler owns Q1. This is ONE prepared context
  // snapshot per arm, not a tool-probe loop or a second memory index.
  const contextDigest=helmDigest(JSON.stringify(initialMessages));
  state=advanceShot(policy,state,{
    kind:"PROBE",eventId:"PROBE-001",instructionId,
    probeDigest:contextDigest,sourceSha
  });
  const calls=[];
  for(let i=1;i<=a.shots;i++){
    const started=performance.now();
    let raw=null,providerError=null,usage=null,returnedModel=null;
    try{
      const reply=await infer({url,token,model,messages,timeoutMs});
      raw=reply?.answer;
      usage=reply?.usage||null;
      returnedModel=reply?.modelReturned||null;
      if(typeof raw!=="string" || !raw.trim())
        providerError="empty model completion";
      if(returnedModel && returnedModel!==model)
        providerError="provider model mismatch";
    }catch(error){
      providerError=String(error.message||error).slice(0,260);
    }
    const parsing=raw ? parseAction(raw) : {ok:false};
    const result=providerError ? {pass:false,reason:"provider-failure"} :
      grade(task,raw,a.profile==="helmet");
    // Invalid action consumes a shot but NEVER becomes an executable opcode.
    const candidateDigest=helmDigest(raw||"provider-error:"+providerError+":"+i);
    state=advanceShot(policy,state,{
      kind:"SHOT",eventId:"SHOT-"+i,instructionId,candidateDigest,
      opcode:parsing.ok?parsing.action.opcode:"INVALID_PROPOSAL",model
    });
    const verdict={
      passed: !providerError && result?.pass===true,
      reason: providerError ? "provider-failure" : String(result?.reason||"unknown"),
      shapeValid:parsing.ok===true
    };
    // The full gold oracle and test source were never in the model messages.
    const evidenceDigest=helmDigest({
      candidateDigest, taskId:task.id, verdict,
      grader:"independent-oracle", sourceSha
    });
    state=advanceShot(policy,state,{
      kind:"GRADE",eventId:"GRADE-"+i,instructionId,candidateDigest,
      passed:verdict.passed,verifier:"independent-oracle",evidenceDigest
    });
    calls.push({
      attempt:i,candidateDigest,
      syntaxAndSchema:parsing.ok, fixtureOraclePass:verdict.passed,
      verdict:verdict.reason, providerError,
      latencyMs:Math.round(performance.now()-started),
      totalTokens:expectedTokenCount(usage), returnedModel,
      evidenceDigest
    });
    if(verdict.passed || providerError)break;
    if(i<a.shots){
      messages.push({role:"assistant",content:raw||""});
      messages.push({role:"user",content:
        "The independently administered trial did not verify that proposal. " +
        "Use one remaining complete shot. Respond with a revised, self-contained " +
        "JSON action only. No oracle, solutions or privileged operations are provided."});
    }
  }
  const report=shotReport(policy,state);
  const latencyMs=calls.reduce((total,c)=>total+c.latencyMs,0);
  const knownTokens=calls.every(c=>c.totalTokens!==null);
  return {
    schema:"helm.shot-arm-result.v1",taskId:task.id,
    taskDigest:helmDigest(task.question),instructionId,
    arm,profile:a.profile,model,sourceSha,
    status:calls.at(-1)?.providerError?"PROVIDER_BLOCKED_RETRYABLE":report.status,
    passedFixtureOracle:report.passedFixtureOracle,
    liveExecutionVerified:false,
    independentRuntimeEvidence:false,
    calls:calls.length,contextProbes:report.contextProbes,
    maximumShots:a.shots,remainingShots:report.remaining,
    totalTokens:knownTokens?calls.reduce((s,c)=>s+c.totalTokens,0):null,
    latencyMs, chainHead:report.chainHead,
    attempts:calls, journal:state.events
  };
}

function aggregate(rows) {
  const passed=rows.filter(x=>x.passedFixtureOracle).length;
  const healthy=rows.filter(x=>!x.attempts.some(a=>a.providerError)).length;
  return {
    total:rows.length,passed,failures:rows.length-passed,
    providerFailed:rows.length-healthy,
    failureCountedSuccessRate:rows.length?passed/rows.length:null,
    totalCalls:rows.reduce((s,r)=>s+r.calls,0),
    totalLatencyMs:rows.reduce((s,r)=>s+r.latencyMs,0),
    totalTokens:rows.every(r=>r.totalTokens!==null) ?
      rows.reduce((s,r)=>s+r.totalTokens,0):null
  };
}

export async function runShotMatrix({tasks,evidence=[],model,url,token,
  sourceSha,limits=[1,2,3,4,5,6,7,8,9,10],includeControl=true,
  controlCeiling=10,maxCalls=120,infer=inference,grade=assess,
  onCheckpoint=()=>{}}={}) {
  if(!Array.isArray(tasks)||tasks.length<1)throw Error("nonempty task corpus required");
  for(const task of tasks)ensureTask(task);
  if(!Array.isArray(limits)||!limits.length||
    limits.some(k=>!Number.isInteger(k)||k<1||k>10)||
    new Set(limits).size!==limits.length)
    throw Error("shot limits must be distinct integers 1..10");
  if(controlCeiling!==10)
    throw Error("control safety ceiling remains exactly 10");
  if(!model || !/^[0-9a-f]{7,64}$/.test(String(sourceSha)))
    throw Error("pinned model and source revision required");
  if(typeof maxCalls!=="number"||!Number.isInteger(maxCalls)||maxCalls<1)
    throw Error("finite call ceiling required");
  const names=[
    ...(includeControl?["control"]:[]),
    ...limits.map(k=>"helm-"+k)
  ];
  const worstCase=tasks.length*(names.reduce((sum,name)=>sum+armDefinition(name).shots,0));
  // IMPORTANT: refuse before any external call if the researcher configured
  // a matrix whose worst-case resource bill exceeds the founder's ceiling.
  if(worstCase>maxCalls)
    throw Error("HELM research model-call ceiling exceeded before execution: "+
      worstCase+" > "+maxCalls);
  const unique=new Set(tasks.map(t=>t.id));
  if(unique.size!==tasks.length)throw Error("duplicate task identities");
  const results=[];
  const out={
    schema:"helm.shot-matrix.v1",evaluation:"fixture-oracle-only",
    realModelCalls:infer===inference,
    independentlyVerifiedProductionYield:false,
    model,sourceSha,taskCorpusDigest:helmDigest(tasks.map(t=>[t.id,t.question])),
    arms:names,shotLimits:limits,
    configuredMaximumCalls:maxCalls,worstCaseCalls:worstCase,
    taskCount:tasks.length,results,summary:{},pairs:[]
  };
  for(let t=0;t<tasks.length;t++){
    const task=tasks[t];
    const ordered=t%2===0?names:[...names].reverse();
    for(const arm of ordered){
      const result=await runOneArm({
        task,
        arm,evidence,model,url,token,sourceSha,infer,grade
      });
      results.push(result);
      // Exact per-arm snapshots are sent to existing artifact storage by caller.
      // The runner never writes an additional authority database.
      onCheckpoint(out);
    }
  }
  for(const name of names)
    out.summary[name]=aggregate(results.filter(r=>r.arm===name));
  if(includeControl)for(const k of limits){
    const treatment="helm-"+k;
    const pairs=tasks.map(task=>{
      const base=results.find(r=>r.taskId===task.id&&r.arm==="control");
      const helm=results.find(r=>r.taskId===task.id&&r.arm===treatment);
      if(!base||!helm)throw Error("incomplete paired task");
      const usable=![...base.attempts,...helm.attempts].some(a=>a.providerError||a.returnedModel&&a.returnedModel!==model);
      return {
        taskId:task.id,usable,baselinePass:base.passedFixtureOracle,
        helmPass:helm.passedFixtureOracle,
        baselineCalls:base.calls,helmCalls:helm.calls
      };
    });
    out.pairs.push({
      arm:treatment,comparison:"control",
      tasks:pairs,usable:pairs.filter(p=>p.usable).length,
      treatmentOnly:pairs.filter(p=>p.usable&&p.helmPass&&!p.baselinePass).length,
      baselineOnly:pairs.filter(p=>p.usable&&!p.helmPass&&p.baselinePass).length,
      inferencePermitted:false,
      reason:"Exploratory paired synthetic fixtures; no production or causal superiority claim"
    });
  }
  return out;
}

export function atomicTrialReceipt(file,body) {
  const target=resolve(file);
  mkdirSync(dirname(target),{recursive:true});
  const tmp=target+".tmp-"+process.pid;
  writeFileSync(tmp,JSON.stringify(body,null,2)+"\n",{mode:0o600});
  renameSync(tmp,target);
}

function parseLimits(raw) {
  const nums=raw.split(",").map(x=>Number(x.trim()));
  if(!nums.length||nums.some(x=>!Number.isInteger(x)||x<1||x>10)||new Set(nums).size!==nums.length)
    throw Error("HELM_SHOT_LIMITS must contain unique integers 1..10");
  return nums;
}

export async function shotTrialMain({env=process.env}={}){
  const corpus=JSON.parse(readFileSync(new URL("./fixtures/tasks.json",import.meta.url),"utf8"));
  const limits=parseLimits(env.HELM_SHOT_LIMITS||"1,2,3,5");
  // Only this hardcoded repository-owned public corpus may be explicitly classified
  // synthetic. Never relabel arbitrary user or private tasks in runShotMatrix.
  const tasks=corpus.tasks.slice(0,Number(env.HELM_SHOT_TASKS||1)).map(
    t=>({...t,classification:"public-synthetic"})
  );
  const sourceSha=env.GITHUB_SHA||
    spawnSync("git",["rev-parse","HEAD"],{encoding:"utf8",timeout:3000}).stdout?.trim();
  const path=env.HELM_SHOT_RECEIPT||"experiments/helm/out/shot-matrix.json";
  const out=await runShotMatrix({
    tasks,evidence:corpus.evidence,model:env.HELM_MODEL,
    url:env.HELM_INFERENCE_URL,token:env.HELM_TOKEN,
    sourceSha,limits,maxCalls:Number(env.HELM_MAX_MODEL_CALLS||80),
    onCheckpoint:partial=>atomicTrialReceipt(path,partial)
  });
  atomicTrialReceipt(path,out);
  console.log(JSON.stringify({
    grade:"SHOT_MATRIX_RECORDED_NOT_PRODUCTION_YIELD",
    sourceSha:out.sourceSha,model:out.model,summary:out.summary,
    pairs:out.pairs.map(p=>({arm:p.arm,usable:p.usable,
      baselineOnly:p.baselineOnly,treatmentOnly:p.treatmentOnly})),
    artifact:path
  }));
  const providerErrors=out.results.some(r=>r.attempts.some(x=>x.providerError));
  return providerErrors?2:0;
}

if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  try{
    process.exitCode=await shotTrialMain();
  }catch(error){
    console.error("HELM_SHOT_ERROR:",String(error.message||error).slice(0,800));
    process.exitCode=1;
  }
}
