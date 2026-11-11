import {readFileSync,writeFileSync,mkdirSync} from "node:fs";
import {resolve,dirname} from "node:path";
import {fileURLToPath} from "node:url";

/** HELM research-grade matched evaluation; no causal claim from incomplete pairs. */
const errorIsProvider=(row)=>typeof row.error==="string"&&row.error.startsWith("provider:");
const choose=(n,k)=>{
  if(k<0||k>n)return 0;
  k=Math.min(k,n-k);let v=1;
  for(let i=1;i<=k;i++)v=v*(n-k+i)/i;
  return v;
};
function exactMcNemar(better,worse){
  const n=better+worse;
  if(n===0)return null;
  let tail=0;
  for(let i=0;i<=Math.min(better,worse);i++)tail+=choose(n,i)/Math.pow(2,n);
  return Math.min(1,2*tail);
}
const ratio=(a,b)=>b===0?null:a/b;
const round=v=>v===null?null:Math.round(v*10000)/10000;

export function analyseTrial(trial,{baseline="baseline",treatment="verified-experience"}={}){
  if(!trial||!Array.isArray(trial.records)||!trial.targetCorpusSha256||!trial.model)
    throw Error("missing real experiment, corpus hash or model identity");
  if(baseline===treatment)throw Error("arms must differ");
  const byTask=new Map(),seen=new Set();
  for(const r of trial.records){
    if(!r||typeof r.taskId!=="string"||typeof r.arm!=="string"||typeof r.passed!=="boolean")
      throw Error("malformed trial record");
    if(![baseline,treatment].includes(r.arm))continue;
    const key=r.taskId+"::"+r.arm;
    if(seen.has(key))throw Error("duplicate arm-task pair: "+key);
    seen.add(key);
    if(!byTask.has(r.taskId))byTask.set(r.taskId,{});
    byTask.get(r.taskId)[r.arm]=r;
  }
  const tasks=[],rows={};
  for(const arm of [baseline,treatment])rows[arm]=[];
  for(const [taskId,pair] of [...byTask].sort((a,b)=>a[0].localeCompare(b[0]))){
    const b=pair[baseline],t=pair[treatment];
    if(!b||!t)throw Error("incomplete paired task: "+taskId);
    const bErr=errorIsProvider(b),tErr=errorIsProvider(t);
    const modelConsistent=[b,t].every(x=>!x.modelReturned||x.modelReturned===trial.model);
    rows[baseline].push(b);rows[treatment].push(t);
    tasks.push({taskId,usable:!bErr&&!tErr&&modelConsistent,
      baselinePass:b.passed,treatmentPass:t.passed,
      baselineProviderError:bErr,treatmentProviderError:tErr,
      sameModel:modelConsistent});
  }
  if(!tasks.length)throw Error("no paired observations");
  const provider={};
  for(const arm of [baseline,treatment]){
    const all=rows[arm],healthy=all.filter(x=>!errorIsProvider(x));
    provider[arm]={calls:all.length,providerErrors:all.length-healthy.length,
      healthyCalls:healthy.length,passes:all.filter(x=>x.passed).length,
      failureCountedRate:round(ratio(all.filter(x=>x.passed).length,all.length)),
      providerHealthyRate:round(ratio(healthy.filter(x=>x.passed).length,healthy.length)),
      totalLatencyMs:all.reduce((n,x)=>n+(Number(x.latencyMs)||0),0)};
  }
  const eligible=tasks.filter(x=>x.usable);
  let treatmentOnly=0,baselineOnly=0,both=0,neither=0;
  for(const x of eligible){
    if(x.treatmentPass&&x.baselinePass)both++;
    else if(x.treatmentPass)treatmentOnly++;
    else if(x.baselinePass)baselineOnly++;
    else neither++;
  }
  const delta=round(ratio(treatmentOnly-baselineOnly,eligible.length));
  return {
    schema:"helm.matched-analysis.v1",model:trial.model,
    trialSha:trial.trialSha||null,
    corpusSha256:trial.targetCorpusSha256,
    sourceMemorySha256:trial.sourceMemorySha256||null,
    sourceProgramSha256:trial.sourceProgramSha256||null,
    question:"Does verified experience increase independently executed success on NEW tasks?",
    raw:provider,
    pairs:{
      total:tasks.length,eligible:eligible.length,censored:tasks.length-eligible.length,
      baselineOnly,treatmentOnly,both,neither,
      observedPairedDelta:delta,
      exactMcNemarP:eligible.length>=10?round(exactMcNemar(treatmentOnly,baselineOnly)):null,
      inferencePermitted:eligible.length>=30&&trial.registrationFrozen===true&&
        tasks.every(x=>x.sameModel)
    },
    decision:eligible.length<10?"INCONCLUSIVE_NO_RELIABLE_SAMPLE":
      eligible.length<30?"EXPLORATORY_NOT_CONFIRMATORY":
      trial.registrationFrozen!==true?"NOT_PREREGISTERED":"REQUIRES_REPLICATION",
    notes:[
      "Failure-counted rates include provider errors; provider-healthy rates do not.",
      "Pairs with an error from either provider or a model identity mismatch are excluded from paired quality inference.",
      "An unconfirmed or unavailable source can never be promoted to a cognitive win.",
      "No p-value is reported for fewer than ten usable pairs, nor does one trial establish a commercial claim.",
      "Exact-task persisted reuse is a separate measured capability, not this treatment effect."
    ],
    perTask:tasks
  };
}

export function analyseAndWrite(input,output){
  const trial=JSON.parse(readFileSync(resolve(input),"utf8"));
  const result=analyseTrial(trial);
  const p=resolve(output);mkdirSync(dirname(p),{recursive:true});
  writeFileSync(p,JSON.stringify(result,null,2)+"\n",{mode:0o600});
  return result;
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  try{
    const input=process.argv[2],output=process.argv[3]||"experiments/helm/out/matched-analysis.json";
    if(!input)throw Error("usage: node research-eval.mjs TRIAL.json [OUTPUT.json]");
    const r=analyseAndWrite(input,output);
    console.log(JSON.stringify({status:r.decision,model:r.model,pairs:r.pairs,
      raw:r.raw,trialSha:r.trialSha,artifact:output}));
  }catch(e){console.error("HELM_EVAL_ERROR:",String(e.message||e));process.exitCode=1;}
}
