/**
 * HELM opt-in research adapter for estate agents. Existing compiler, model router,
 * and authorized intent executor remain authoritative. This adapter proposes an
 * action and emits a receipt; it never commits, runs commands, or grants permissions.
 */
import {readFileSync,mkdirSync,writeFileSync,renameSync} from "node:fs";
import {resolve,dirname} from "node:path";
import {createHash} from "node:crypto";
import {messagesFor,evidenceFromCompiler,parseAction,checkPython,inference} from "./helm.mjs";

const hash = s => createHash("sha256").update(s).digest("hex");
const PUBLIC_URL="https://ai-gateway.kilo.ai/api/v1/chat/completions";

export async function propose({task,contextPlan=null,evidence=[],model,url,token=null,
  infer=inference,maxAttempts=2}={}) {
  if(!task||typeof task.question!=="string"||!task.question.trim()||!task.id)
    throw Error("task must contain id and nonempty question");
  if(!model||!url?.startsWith("https://"))throw Error("HTTPS model route is required");
  if(!Number.isInteger(maxAttempts)||maxAttempts<1||maxAttempts>3)
    throw Error("maxAttempts must be 1..3");
  // The unauthenticated third-party model route may see public synthetic fixtures only.
  // A caller cannot attach a real repository compiler plan to that route.
  if(url===PUBLIC_URL && !token && (contextPlan||task.classification!=="public-synthetic"))
    throw Error("anonymous free provider may receive public-synthetic tasks only, never private ContextPlans");
  const authoritativeEvidence=contextPlan?evidenceFromCompiler(contextPlan):evidence;
  const messages=messagesFor("helm",task,authoritativeEvidence);
  const decisions=[];
  for(let i=0;i<maxAttempts;i++){
    let result;
    try{
      result=await infer({url,token,model,messages,timeoutMs:45000});
    }catch(error){
      decisions.push({state:"provider-error",error:String(error.message||error).slice(0,300)});
      break;
    }
    const parsed=parseAction(result.answer);
    let verdict=parsed.ok?"CANDIDATE":"SCHEMA_REFUSED";
    let staticCheck=null;
    if(parsed.ok && parsed.action.opcode==="EMIT_PATCH"){
      if(!task.patchTarget)verdict="PATCH_TARGET_REFUSED";
      else if(task.language==="python"){
        staticCheck=checkPython(parsed.action.payload);
        if(!staticCheck.ok)verdict="STATIC_REFUSED";
      }
    }
    if(parsed.ok && parsed.action.opcode==="SUBMIT_YIELD" &&
       task.requiresOperationalProof===true && task.verifiedReceipt!==true)
      verdict="UNVERIFIED_YIELD_REFUSED";
    decisions.push({state:verdict,replySha256:hash(result.answer),
      action:verdict==="CANDIDATE"?parsed.action:null,
      error:parsed.error||staticCheck?.error||null,
      latencyMs:result.latencyMs||null,usage:result.usage||null});
    if(verdict==="CANDIDATE")break;
    if(i+1<maxAttempts){
      messages.push({role:"assistant",content:result.answer});
      messages.push({role:"user",content:"HELM verifier refused your last proposed action ("+
        verdict+"). Return a correct JSON action. No self-certified verification."});
    }
  }
  const final=decisions.at(-1);
  return {
    schema:"helm.agent-proposal.v1",taskId:task.id,model,
    classification:task.classification||"unspecified",
    contextPlanHash:contextPlan?.plan_hash||null,
    contextPlanCommit:contextPlan?.provenance?.commit||null,
    taskSha256:hash(task.question),
    state:final?.state||"NO_ATTEMPT",action:final?.state==="CANDIDATE"?final.action:null,
    independentlyVerified:false,
    note:"Proposed action only. Existing estate intent executor and independent real-caller proof remain mandatory.",
    attempts:decisions,
  };
}

function writeAtomic(path,value){
  const target=resolve(path);
  mkdirSync(dirname(target),{recursive:true});
  const tmp=target+".tmp-"+process.pid;
  writeFileSync(tmp,JSON.stringify(value,null,2)+"\n",{mode:0o600});
  renameSync(tmp,target);
}

if(process.argv[1] && import.meta.url===new URL("file://"+resolve(process.argv[1])).href){
  try{
    const taskFile=process.argv[2],outFile=process.argv[3];
    if(!taskFile||!outFile)throw Error("usage: node agent-adapter.mjs TASK.json RECEIPT.json [CONTEXT_PLAN.json]");
    const task=JSON.parse(readFileSync(resolve(taskFile),"utf8"));
    const contextPlan=process.argv[4]?
      JSON.parse(readFileSync(resolve(process.argv[4]),"utf8")):null;
    const result=await propose({task,contextPlan,
      model:process.env.HELM_MODEL,url:process.env.HELM_INFERENCE_URL,
      token:process.env.HELM_TOKEN||null});
    writeAtomic(outFile,result);
    console.log(JSON.stringify({receipt:outFile,state:result.state,verified:false}));
    if(result.state!=="CANDIDATE")process.exitCode=2;
  }catch(error){
    console.error("HELM_AGENT_ERROR:",String(error.message||error).slice(0,400));
    process.exitCode=1;
  }
}
