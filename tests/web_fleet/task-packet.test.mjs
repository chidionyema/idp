import test from 'node:test';
import assert from 'node:assert/strict';
import { makePacket, Blind } from '../../scripts/web-fleet/task-packet.mjs';
import { validatePatch, assertPath, sha256 } from '../../scripts/web-fleet/patch-wire.mjs';
const sha='a'.repeat(40), runSha='b'.repeat(40);
const file={type:'file',encoding:'base64',size:10,content:Buffer.from('const x=1;').toString('base64')};
const get=async path=>{
  if(path.includes('/branches/main'))return {commit:{sha}};
  if(path.includes('/issues/42'))return {number:42,title:'Build source safely',body:'Only target file. Claims untrusted.',state:'open'};
  if(path.includes('/contents/'))return file;
  if(path.includes('/actions/runs/99/jobs'))return {jobs:[{id:123,name:'fast-gate',conclusion:'failure'}]};
  if(path.includes('/actions/runs/99'))return {id:99,head_sha:runSha,status:'completed',conclusion:'failure'};
  throw new Error('unexpected '+path);
};
const opts={issue:42,paths:['platform/router-edge/src/index.ts'],get,now:()=> '2026-11-22T00:00:00Z'};
const patchFor=p=>({schema:'MERIDIAN-PATCH-V1',instruction_id:p.instruction_id,repo:'chidionyema/idp',issue:42,base_sha:sha,agent_label:'gemini-web-unverified',summary:'safe edit',edits:[{path:p.target_files[0].path,action:'update',expected_sha256:p.target_files[0].sha256,content:'const x=2;',mode:'100644'}]});
test('precise public task packet, no authority, no imaginary live yield', async()=>{
 const p=await makePacket(opts);
 assert.equal(p.state,'READY_UNTRUSTED');assert.equal(p.source_sha,sha);
 assert.equal(p.target_files[0].sha256,sha256('const x=1;'));
 assert.equal(p.authority,'UNTRUSTED_PROPOSAL_ONLY');
 assert.ok(Buffer.byteLength(JSON.stringify(p))<=12288);
 assert.equal(validatePatch(patchFor(p),p).verdict,'SCHEMA_VALID_ONLY');
});
test('run from different SHA cannot be used as current main failure proof', async()=>{
 const p=await makePacket({...opts,runId:99});
 assert.equal(p.state,'BLIND');
 assert.ok(p.missing.some(x=>x.reason==='CI_RUN_HEAD_DIFFERS_FROM_CURRENT_MAIN'));
});
test('body truncation is visible, not silent', async()=>{
 const p=await makePacket({...opts,get:async path=>path.includes('/issues/')?{number:42,title:'T',body:'x'.repeat(2000),state:'open'}:get(path)});
 assert.equal(p.state,'BLIND');assert.ok(p.missing.some(x=>x.reason==='ISSUE_BODY_TRUNCATED'));
});
test('large exact file stays BLIND rather than truncated source', async()=>{
 const huge='a'.repeat(4000);
 const p=await makePacket({...opts,get:async path=>path.includes('/contents/')?{type:'file',encoding:'base64',size:4000,content:Buffer.from(huge).toString('base64')}:get(path)});
 assert.equal(p.state,'BLIND');assert.equal(p.target_files.length,0);
});
test('untrusted issue cannot become an authority', async()=>{
 const p=await makePacket(opts);assert.throws(()=>validatePatch({...patchFor(p),authorised:true},p),/PATCH_SCHEMA_INVALID/);
});
test('forbidden paths and traversal blocked before any network', async()=>{
 for(const path of ['../.env','platform/../../.github/workflows/a.yml','secrets/token','platform/.env.production','platform\\x','/etc/passwd','platform/foo//bar']){
  assert.throws(()=>assertPath(path),/PATH_NOT_ADMITTED/);
 }
 await assert.rejects(makePacket({...opts,paths:['platform/../../.github/workflows/a.yml']}),/PATH_NOT_ADMITTED/);
});
test('replay against stale main and modified base digest blocked', async()=>{
 const p=await makePacket(opts);const q=patchFor(p);
 assert.throws(()=>validatePatch({...q,base_sha:'b'.repeat(40)},p),/STALE_OR_UNBOUND_PACKET/);
 assert.throws(()=>validatePatch({...q,edits:[{...q.edits[0],expected_sha256:'b'.repeat(64)}]},p),/EDIT_SCOPE_OR_BASE_INVALID/);
});
test('duplicate, executable and out-of-scope modifications blocked', async()=>{
 const p=await makePacket(opts),q=patchFor(p);
 assert.throws(()=>validatePatch({...q,edits:[q.edits[0],q.edits[0]]},p),/DUPLICATE_EDIT_PATH/);
 assert.throws(()=>validatePatch({...q,edits:[{...q.edits[0],mode:'100755'}]},p),/EDIT_SCOPE_OR_BASE_INVALID/);
 assert.throws(()=>validatePatch({...q,edits:[{...q.edits[0],path:'platform/evil.ts'}]},p),/EDIT_SCOPE_OR_BASE_INVALID/);
});
test('incorrect API evidence and missing source refuse', async()=>{
 await assert.rejects(makePacket({...opts,get:async path=>path.includes('/branches/main')?{commit:{sha:'bad'}}:get(path)}),/MAIN_SHA_NOT_VERIFIED/);
 await assert.rejects(makePacket({...opts,get:async path=>path.includes('/contents/')?{...file,size:15}:get(path)}),/SOURCE_SIZE_MISMATCH/);
});
