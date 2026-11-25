import {createHash} from "node:crypto";
import {TextDecoder} from "node:util";
// Research candidate: pure common-spec contract predicate; no deployment or authority grant.
function validateSpec(s) {
  const errors=[];
  const obj=x=>x!==null&&typeof x==="object"&&!Array.isArray(x);
  const str=x=>typeof x==="string"&&x.trim().length>=8&&!/^(todo|tbd|n\/a|none|unknown|placeholder|lorem ipsum)$/i.test(x.trim());
  const hash=x=>typeof x==="string"&&/^[a-f0-9]{64}$/.test(x);
  const list=(x,p,fn,min=1)=>{if(!Array.isArray(x)||x.length<min||x.length>200){errors.push(p);return;}x.forEach((v,i)=>{if(!fn(v))errors.push(`${p}[${i}]`);});};
  const keys=(x,required,p)=>{if(!obj(x)){errors.push(p);return false;}for(const k of required)if(!Object.hasOwn(x,k))errors.push(`${p}.${k}`);for(const k of Object.keys(x))if(!required.includes(k))errors.push(`${p}.${k}:unexpected`);return true;};
  if(!keys(s,["schema","id","instruction","class","founder","scope","outcomes","topology","resources","delivery","assurance","recovery","annex"],"spec"))return errors;
  if(s.schema!=="meridian.spec/1")errors.push("schema");
  if(typeof s.id!=="string"||!/^[A-Z][A-Z0-9-]{2,63}$/.test(s.id))errors.push("id");
  if(!str(s.instruction))errors.push("instruction");
  if(!["research","engineering","product","operations","governance"].includes(s.class))errors.push("class");
  if(keys(s.founder,["why","proposal","value","alternatives","risks","decision","recommendation"],"founder")){
    for(const k of ["why","proposal","value","decision","recommendation"])if(!str(s.founder[k]))errors.push(`founder.${k}`);
    list(s.founder.alternatives,"founder.alternatives",v=>obj(v)&&str(v.option)&&str(v.tradeoff),2);
    list(s.founder.risks,"founder.risks",v=>obj(v)&&str(v.risk)&&str(v.control));
  }
  if(keys(s.scope,["owner","affected","excluded","base"],"scope")){
    if(!str(s.scope.owner))errors.push("scope.owner");
    list(s.scope.affected,"scope.affected",str);list(s.scope.excluded,"scope.excluded",str);
    if(typeof s.scope.base!=="string"||!/^[a-f0-9]{40,64}$/.test(s.scope.base))errors.push("scope.base");
  }
  list(s.outcomes,"outcomes",v=>obj(v)&&str(v.id)&&str(v.effect)&&str(v.acceptance)&&str(v.falsifier)&&str(v.independent_verifier));
  if(Array.isArray(s.outcomes)&&new Set(s.outcomes.map(x=>x?.id)).size!==s.outcomes.length)errors.push("outcomes:duplicate");
  if(keys(s.topology,["snapshot","dependencies","unknowns","blast_radius","fault_model"],"topology")){
    if(!hash(s.topology.snapshot))errors.push("topology.snapshot");
    list(s.topology.dependencies,"topology.dependencies",v=>obj(v)&&str(v.id)&&["required","optional","alternative","conditional"].includes(v.kind)&&str(v.evidence)&&str(v.failure_domain));
    list(s.topology.unknowns,"topology.unknowns",v=>obj(v)&&str(v.question)&&str(v.resolution)&&str(v.owner),0);
    if(!str(s.topology.blast_radius)||!str(s.topology.fault_model))errors.push("topology.impact");
  }
  if(keys(s.resources,["max_incremental_pence","max_duration_seconds","basis","uncertainties"],"resources")){
    for(const k of ["max_incremental_pence","max_duration_seconds"])if(!Number.isSafeInteger(s.resources[k])||s.resources[k]<0||(k==="max_duration_seconds"&&s.resources[k]===0))errors.push(`resources.${k}`);
    if(!str(s.resources.basis))errors.push("resources.basis");
    list(s.resources.uncertainties,"resources.uncertainties",str,0);
  }
  list(s.delivery,"delivery",v=>obj(v)&&str(v.id)&&str(v.owner)&&str(v.action)&&str(v.exit_evidence)&&Array.isArray(v.requires)&&v.requires.every(str));
  if(Array.isArray(s.delivery)){
    const done=new Set();
    for(const v of s.delivery){if(!obj(v))continue;if(done.has(v.id)||!Array.isArray(v.requires)||v.requires.some(x=>!done.has(x)))errors.push("delivery:duplicate-or-unordered-dependency");done.add(v.id);}
  }
  if(keys(s.assurance,["authority_boundary","proof_plan","negative_tests","settlement"],"assurance")){
    for(const k of ["authority_boundary","proof_plan","settlement"])if(!str(s.assurance[k]))errors.push(`assurance.${k}`);
    list(s.assurance.negative_tests,"assurance.negative_tests",str);
  }
  if(keys(s.recovery,["rollback","independent_path","custody","deadline"],"recovery"))for(const k of ["rollback","independent_path","custody","deadline"])if(!str(s.recovery[k]))errors.push(`recovery.${k}`);
  if(keys(s.annex,["ref","sha256"],"annex")){if(!str(s.annex.ref))errors.push("annex.ref");if(!hash(s.annex.sha256))errors.push("annex.sha256");}
  return errors;
}
function founderView(s) {
  const errors=validateSpec(s);
  if(errors.length)throw Error("INVALID_SPEC");
  return {id:s.id,instruction:s.instruction,...s.founder,resource_cap_pence:s.resources.max_incremental_pence,time_cap_seconds:s.resources.max_duration_seconds,uncertainties:s.resources.uncertainties,unknown_dependencies:s.topology.unknowns,outcomes:s.outcomes.map(x=>({effect:x.effect,acceptance:x.acceptance})),disposition:"PROPOSAL_ONLY"};
}
// Canonical JSON is recursively key-sorted ECMAScript JSON, without whitespace.
function canonicalSpec(value) {
  if (Array.isArray(value)) return "[" + value.map(canonicalSpec).join(",") + "]";
  if (value !== null && typeof value === "object") {
    return "{" + Object.keys(value).sort().map(k => JSON.stringify(k) + ":" + canonicalSpec(value[k])).join(",") + "}";
  }
  return JSON.stringify(value);
}
function prestart(raw, annexBytes, trusted) {
  const deny = (...errors) => ({decision:"DENY",errors});
  if (!Buffer.isBuffer(raw) || raw.length === 0 || raw.length > 262144 ||
      !Buffer.isBuffer(annexBytes) || annexBytes.length === 0 || annexBytes.length > 8388608)
    return deny("INVALID_INPUT_BYTES");
  let s;
  try {
    s = JSON.parse(new TextDecoder("utf-8",{fatal:true}).decode(raw));
    if (!raw.equals(Buffer.from(canonicalSpec(s),"utf8"))) return deny("NON_CANONICAL_SPEC");
  } catch { return deny("INVALID_SPEC_JSON"); }
  const errors = validateSpec(s);
  if (errors.length) return deny(...errors);
  const digest = createHash("sha256").update(raw).digest("hex");
  const annexDigest = createHash("sha256").update(annexBytes).digest("hex");
  // Trusted context comes ONLY from the existing authenticated admission
  // boundary. This predicate does not authenticate callers or grant authority.
  if (!trusted || trusted.verified !== true || trusted.specDigest !== digest ||
      trusted.instruction !== s.instruction || trusted.base !== s.scope.base ||
      trusted.topology !== s.topology.snapshot || trusted.annexDigest !== annexDigest ||
      s.annex.sha256 !== annexDigest || trusted.decision !== "SCOPE_AUTHORIZED" ||
      trusted.policyCurrent !== true || trusted.materialDependenciesVerified !== true ||
      !Number.isSafeInteger(trusted.now) || !Number.isSafeInteger(trusted.expires) ||
      trusted.expires <= trusted.now || !Number.isSafeInteger(trusted.reservedPence) ||
      trusted.reservedPence < s.resources.max_incremental_pence ||
      !Number.isSafeInteger(trusted.reservedSeconds) ||
      trusted.reservedSeconds < s.resources.max_duration_seconds)
    return deny("TRUSTED_ADMISSION_BINDING_REQUIRED");
  return {decision:"ELIGIBLE_FOR_EXISTING_AUTHORITY_GATE",errors:[],specDigest:digest,annexDigest};
}
export {validateSpec,founderView,canonicalSpec,prestart};
