/**
 * Exact-public-source GitHub evidence adapter for the ONE canonical Lifeboat
 * MERIDIAN-TASK-V1 hydrator. Source data only; never authorises an action.
 * No duplicated model-facing wire schema, store, scheduler or GitHub writer.
 */
import { createHash } from 'node:crypto';
const REPO = 'chidionyema/idp';
const API = `https://api.github.com/repos/${REPO}`;
const SHA40 = /^[a-f0-9]{40}$/i;
const SEGMENT = /^[a-zA-Z0-9_.+@-]{1,120}$/;
const DENIED = new Set(['.git', '.github', '.githooks', 'node_modules', '.ssh', 'secrets', 'credentials']);
const PRIVATE = /(?:-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|github_pat_[\w]{12,}|\bgh[pousr]_[\w]{16,}|\bsk-[\w-]{18,}|authorization\s*:\s*(?:bearer|basic)\s+\S+)/i;
const sha256 = raw => createHash('sha256').update(raw).digest('hex');
const gitBlob = raw => createHash('sha1').update(Buffer.from(`blob ${raw.length}\0`)).update(raw).digest('hex');
export class EvidenceBlind extends Error { constructor(code) { super(code); this.code=code; } }
const deny = code => { throw new EvidenceBlind(code); };
export function safePath(path) {
  if (typeof path !== 'string' || path.length>180 || path.startsWith('/') || path.includes('\\') ||
      path.includes('//') || path.split('/').length>8 || !path.split('/').every(x=>SEGMENT.test(x) && x!=='.' && x!=='..' && !DENIED.has(x.toLowerCase()) && !x.toLowerCase().startsWith('.env')))
    deny('SOURCE_PATH_REFUSED');
  return path;
}
function id(value) { if(!Number.isSafeInteger(value)||value<1) deny('INVALID_GITHUB_ID'); return value; }
export async function githubJson(path,{requester=fetch,token=process.env.GH_TOKEN||process.env.GITHUB_TOKEN}={}) {
  if (!/^\/(?:branches\/main|git\/commits\/[a-f0-9]{40}|git\/trees\/[a-f0-9]{40}|issues\/[0-9]+|actions\/runs\/[0-9]+(?:\/jobs\?per_page=100)?|contents\/[A-Za-z0-9._+@\/-]+\?ref=[a-f0-9]{40})$/.test(path)) deny('UNEXPECTED_GITHUB_READ');
  let response;
  try { response=await requester(API+path,{redirect:'manual',headers:{'accept':'application/vnd.github+json','user-agent':'meridian-readonly-evidence/1',...(token?{authorization:`Bearer ${token}`}:{})},signal:AbortSignal.timeout(15000)}); }
  catch { deny('GITHUB_READ_UNAVAILABLE'); }
  if(response.status!==200) deny(`GITHUB_READ_HTTP_${response.status}`);
  if(!(response.headers.get('content-type')||'').includes('json')) deny('NON_JSON_GITHUB_RESPONSE');
  try { return await response.json(); } catch { deny('INVALID_GITHUB_JSON'); }
}
export function diagnosticLines(log) {
  if(typeof log!=='string'||log.length>500_000) deny('CI_LOG_UNAVAILABLE_OR_OVERSIZED');
  const matched=log.split('\n').map(x=>x.replace(/\x1b\[[0-9;]*m/g,''))
    .filter(x=>/\b(?:FAIL|ERROR|Error|Traceback|Would reformat|failed|refused)\b/.test(x)).slice(-12)
    .map(x=>x.slice(0,240));
  if(!matched.length||matched.some(x=>PRIVATE.test(x))) deny('CI_DIAGNOSTICS_MISSING_OR_SENSITIVE');
  return matched;
}
export async function sourceEvidence({issue,paths,runId=null,taskId,instructionId,owner,acceptance,checkpoint=null,read=githubJson,readJobLog=null}) {
  id(issue);
  if(typeof taskId!=='string'||typeof instructionId!=='string'||!taskId||!instructionId||
    typeof owner!=='string'||!owner||typeof acceptance!=='string'||!acceptance||PRIVATE.test(acceptance) ||
    !Array.isArray(paths)||paths.length<1||paths.length>2||new Set(paths).size!==paths.length) deny('EVIDENCE_REQUEST_INVALID');
  paths.forEach(safePath);
  const [b,issueRow]=await Promise.all([read('/branches/main'),read(`/issues/${issue}`)]);
  const head=b?.commit?.sha;
  if(!SHA40.test(head)||issueRow?.number!==issue||issueRow?.state!=='open'||issueRow.pull_request) deny('MAIN_OR_ISSUE_NOT_CONFIRMED');
  const sourceSha=head.toLowerCase();
  const commit=await read(`/git/commits/${sourceSha}`);
  let tree=commit?.tree?.sha;
  if(!SHA40.test(tree)) deny('COMMIT_TREE_MISSING');
  const treeCache=new Map(),files=[];
  async function entries(sha){
    if(!treeCache.has(sha)){
      const t=await read(`/git/trees/${sha}`);
      if(t.truncated===true||!Array.isArray(t.tree))deny('TREE_TRUNCATED_OR_INVALID');
      treeCache.set(sha,t.tree);
    }
    return treeCache.get(sha);
  }
  for(const path of paths){
    let cursor=tree,chosen;
    const parts=path.split('/');
    for(let i=0;i<parts.length;i++){
      chosen=(await entries(cursor)).find(e=>e.path===parts[i]);
      if(!chosen||!SHA40.test(chosen.sha))deny('PATH_NOT_IN_PINNED_TREE');
      if(i<parts.length-1){if(chosen.type!=='tree')deny('NON_DIRECTORY_ON_PATH');cursor=chosen.sha;}
    }
    if(chosen.type!=='blob'||!['100644','100755'].includes(chosen.mode))deny('SOURCE_MODE_REFUSED');
    const record=await read(`/contents/${path}?ref=${sourceSha}`);
    if(record?.type!=='file'||record.encoding!=='base64'||record.sha!==chosen.sha||typeof record.content!=='string'||!Number.isSafeInteger(record.size)||record.size>8500)deny('CONTENT_OR_BLOB_REFUSED');
    const encoded=record.content.replace(/\s/g,'');
    if(!/^[A-Za-z0-9+/]*={0,2}$/.test(encoded))deny('BASE64_INVALID');
    const raw=Buffer.from(encoded,'base64');
    if(raw.toString('base64')!==encoded||raw.length!==record.size||gitBlob(raw)!==chosen.sha)deny('CONTENT_HASH_MISMATCH');
    let content;
    try{content=new TextDecoder('utf-8',{fatal:true}).decode(raw);}catch{deny('NON_UTF8_SOURCE');}
    if(content.includes('\0')||PRIVATE.test(content))deny('PRIVATE_SOURCE_REFUSED');
    files.push({path,blobSha:chosen.sha,mode:chosen.mode,content,sha256:sha256(raw)});
  }
  let ci=null;
  if(runId!==null){
    id(runId);
    const [run,jobs]=await Promise.all([read(`/actions/runs/${runId}`),read(`/actions/runs/${runId}/jobs?per_page=100`)]);
    if(run.id!==runId||run.head_sha!==sourceSha||!Array.isArray(jobs.jobs))deny('CI_SHA_OR_RUN_MISMATCH');
    const failed=jobs.jobs.find(j=>j.conclusion==='failure'&&Number.isSafeInteger(j.id));
    if(!failed||typeof readJobLog!=='function')deny('NO_VERIFIABLE_FAILED_CI_LOG');
    const lines=diagnosticLines(await readJobLog(failed.id,runId));
    ci={runId,sourceSha,lines};
  }
  const fresh=await read('/branches/main');
  if(fresh?.commit?.sha!==sourceSha)deny('MAIN_MOVED_DURING_SNAPSHOT');
  return {taskId,instructionId,issue,sourceSha,files,ci,acceptance,owner,checkpoint};
}
export async function hydrateFromGitHub(options,{hydrate=null,...deps}={}){
  const evidence=await sourceEvidence({...options,...deps});
  let impl=hydrate;
  if(!impl){
    try { ({hydrateTask:impl}=await import('../../platform/lifeboat/src/task-packet.js')); }
    catch {deny('CANONICAL_LIFEBOAT_HYDRATOR_NOT_LANDED');}
  }
  if(typeof impl!=='function')deny('CANONICAL_LIFEBOAT_HYDRATOR_MISSING');
  return impl(evidence); // canonical V1 only. No other model-facing schema.
}
