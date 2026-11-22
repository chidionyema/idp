import { test } from 'node:test';
import assert from 'node:assert/strict';
import { hydrateTask, validateProposal, PacketError, policy } from '../src/task-packet.js';
const SHA = 'a'.repeat(40);
const make = (over = {}) => ({ taskId: 'WEB-001', instructionId: 'FIR-06', issue: 8133, sourceSha: SHA,
  owner: 'gemini-web', acceptance: 'Produce a source patch proposal, not a commit',
  files: [{path: 'src/example.ts', blobSha: 'ad1d380d6cc4dfe69119852d461b7ccd89a19228', mode: '100755', content: 'export const x = 1;\n', sha256: 'b40dedde60828bf61d1fadbfc3bb7ea2e0421e9511d22f1b5fb44ae5ba07dbb3'}], ...over });
const ready = async(over={}) => hydrateTask(make(over));
const fails = async(code, action) => assert.rejects(action, (e) => e instanceof PacketError && e.code === code);

test('bounded deterministic canonical task', async () => {
 const a = await ready(), b=await ready();
 assert.equal(a.payload_sha256,b.payload_sha256); assert.equal(a.source_sha,SHA); assert.equal(a.checkpoint.lease,'UNOBSERVED');
 assert.ok(new TextEncoder().encode(JSON.stringify(a)).length < 12288);
});
test('wrong sha refuses', async()=>{await fails('SOURCE_SHA_UNKNOWN',()=>ready({sourceSha:'short'}));});
test('traversal and protected paths refuse', async()=>{
 for(const path of ['../evil.ts','/tmp/x','foo/../evil.js','.github/workflows/x.yml','.env','src/.ssh/key','src//x.js'])
  await fails('UNSAFE_SOURCE_PATH',()=>ready({files:[{...make().files[0],path}]}));
});
test('duplicate paths refuse', async()=>{const f=make().files[0];await fails('DUPLICATE_SOURCE_PATH',()=>ready({files:[f,f]}));});
test('digest mismatch refuses', async()=>{await fails('SOURCE_CONTENT_DIGEST_MISMATCH',()=>ready({files:[{...make().files[0],sha256:'0'.repeat(64)}]}));});
test('mode missing refuses', async()=>{await fails('SOURCE_PROVENANCE_OR_MODE_UNKNOWN',()=>ready({files:[{...make().files[0],mode:null}]}));});
test('private secret refuses', async()=>{await fails('SENSITIVE_OR_INVALID_SOURCE',()=>ready({files:[{...make().files[0],content:'github_pat_abcdefghijklmno'}]}));});
test('over budget refuses', async()=>{await fails('SOURCE_FILE_TOO_LARGE',()=>ready({files:[{...make().files[0],content:'x'.repeat(8501)}]}));});
test('fabricated CI provenance refuses', async()=>{await fails('CI_PROVENANCE_UNKNOWN',()=>ready({ci:{runId:1,sourceSha:'f'.repeat(40),lines:[]}}));});
test('CI timestamps cannot be assumed to carry milliseconds', async()=>{const p=await ready({ci:{runId:45034502220,sourceSha:SHA,lines:['error: compile failed']}}); assert.equal(p.failure.time_precision,'SOURCE_UNVERIFIED_OR_SECONDS_ONLY');});
test('valid proposal remains untrusted pending real preseal',async()=>{const p=await ready(); const o=await validateProposal(p,{schema:'MERIDIAN-PATCH-V1',task_id:p.task_id,base_sha:p.source_sha,files:[{path:p.source_files[0].path,mode:'100755',content:p.source_files[0].content,sha256:p.source_files[0].content_sha256}]});assert.equal(o.status,'PROPOSED_UNTRUSTED');assert.ok(o.needs.includes('TRUSTED_PRESEAL_CANONICALISATION'));});
test('forged mode or stale commit refuses',async()=>{const p=await ready();let draft={schema:'MERIDIAN-PATCH-V1',task_id:p.task_id,base_sha:p.source_sha,files:[{path:p.source_files[0].path,mode:'100644',content:p.source_files[0].content,sha256:p.source_files[0].content_sha256}]};await fails('EXECUTABLE_MODE_CHANGED',()=>validateProposal(p,draft));await fails('STALE_OR_UNBOUND_PROPOSAL',()=>validateProposal(p,{...draft,base_sha:'f'.repeat(40)}));});
test('forged Git blob cannot pass as source provenance',async()=>{await fails('SOURCE_BLOB_DIGEST_MISMATCH',()=>ready({files:[{...make().files[0],blobSha:'b'.repeat(40)}]}));});
test('unsigned altered task is refused before patch check',async()=>{const p=await ready();p.source_sha='f'.repeat(40);await fails('PACKET_TAMPERED',()=>validateProposal(p,{}));});
test('checkpoint cannot hide bearer credentials',async()=>{await fails('UNTRUSTED_CHECKPOINT',()=>ready({checkpoint:{state:'READY',lease:'Authorization: Bearer xxxxxxxxx'}}));});

test('checkpoint is an allowlisted projection, never a raw secret channel',async()=>{const p=await ready({checkpoint:{state:'READY',lease:'lease-01',raw_private_key:'secrets-must-not-leak'}});assert.equal(p.checkpoint.lease,'lease-01');assert.equal('raw_private_key' in p.checkpoint,false);assert.equal(JSON.stringify(p).includes('secrets-must-not-leak'),false);});
