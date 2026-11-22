import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {sourceEvidence,hydrateFromGitHub,diagnosticLines,EvidenceBlind} from '../../scripts/web-fleet/github-evidence.mjs';
const root='a'.repeat(40), sha='b'.repeat(40), issue=7760;
const raw=Buffer.from('export const x=1;\n');
const blob=createHash('sha1').update(Buffer.from(`blob ${raw.length}\0`)).update(raw).digest('hex');
const sha256=createHash('sha256').update(raw).digest('hex');
const trees={
 [root]:[{path:'platform',type:'tree',mode:'040000',sha:'c'.repeat(40)}],
 ['c'.repeat(40)]:[{path:'tiny.js',type:'blob',mode:'100755',sha:blob}],
};
const path='platform/tiny.js';
const read=async p=>{
 if(p==='/branches/main')return {commit:{sha}};
 if(p===`/issues/${issue}`)return {number:issue,state:'open',title:'Review',body:'Data only'};
 if(p===`/git/commits/${sha}`)return {tree:{sha:root}};
 if(p.startsWith('/git/trees/'))return {tree:trees[p.slice('/git/trees/'.length)]};
 if(p===`/contents/${path}?ref=${sha}`)return {type:'file',sha:blob,encoding:'base64',content:raw.toString('base64'),size:raw.length};
 if(p==='/actions/runs/99')return {id:99,head_sha:sha};
 if(p==='/actions/runs/99/jobs?per_page=100')return {jobs:[{id:7,name:'fast-gate',conclusion:'failure'}]};
 throw new Error('UNEXPECTED:'+p);
};
const options={issue,paths:[path],taskId:'FIR-07-A',instructionId:'FIR-07',owner:'gemini-web',acceptance:'Return a bounded proposal only',read};
const fails=async (code,fn)=>assert.rejects(fn,(e)=>e instanceof EvidenceBlind&&e.code===code);
test('real Git tree mode SHA1 blob SHA256 source evidence',async()=>{
 const out=await sourceEvidence(options);assert.equal(out.sourceSha,sha);assert.equal(out.files[0].mode,'100755');
 assert.equal(out.files[0].blobSha,blob);assert.equal(out.files[0].sha256,sha256);assert.equal(out.files[0].content,raw.toString());
});
test('uses existing canonical hydrator, not a second wire protocol',async()=>{
 let observed;const out=await hydrateFromGitHub(options,{hydrate:async x=>{observed=x;return {schema:'MERIDIAN-TASK-V1'};}});
 assert.equal(out.schema,'MERIDIAN-TASK-V1');assert.equal(observed.files[0].mode,'100755');
});
test('rejects path traversal and protected directory before GitHub read',async()=>{
 for(const x of ['../foo','platform/../../.github/x','/tmp/credentials','platform/.env','platform/x//z','platform\\foo']){
 await fails('SOURCE_PATH_REFUSED',()=>sourceEvidence({...options,paths:[x]}));}
});
test('rejects forged or stale source Git object',async()=>{
 await fails('CONTENT_OR_BLOB_REFUSED',()=>sourceEvidence({...options,read:async p=>p.startsWith('/contents/')?{type:'file',sha:'0'.repeat(40),encoding:'base64',content:raw.toString('base64'),size:raw.length}:read(p)}));
});
test('source must be checked with mode 100755; no silent mode rewrite',async()=>{
 await fails('SOURCE_MODE_REFUSED',()=>sourceEvidence({...options,read:async p=>p==='/git/trees/'+'c'.repeat(40)?{tree:[{path:'tiny.js',type:'blob',mode:'160000',sha:blob}]}:read(p)}));
});
test('fails closed if main advances while fetching',async()=>{
 let calls=0;await fails('MAIN_MOVED_DURING_SNAPSHOT',()=>sourceEvidence({...options,read:async p=>p==='/branches/main'&&++calls===2?{commit:{sha:'0'.repeat(40)}}:read(p)}));
});
test('CI failure tied to identical SHA and exact redacted lines',async()=>{
 const out=await sourceEvidence({...options,runId:99,readJobLog:async()=>`info\nFAIL ruff-fmt would reformat file\nError: command exit 1`});
 assert.equal(out.ci.sourceSha,sha);assert.equal(out.ci.lines.length,2);
});
test('CI with wrong SHA cannot be attributed',async()=>{
 await fails('CI_SHA_OR_RUN_MISMATCH',()=>sourceEvidence({...options,runId:99,read:async p=>p==='/actions/runs/99'?{id:99,head_sha:'0'.repeat(40)}:read(p),readJobLog:async()=> 'FAIL test'}));
});
test('sensitive CI output refused rather than sent to consumer model',async()=>{
 await fails('CI_DIAGNOSTICS_MISSING_OR_SENSITIVE',()=>sourceEvidence({...options,runId:99,readJobLog:async()=> 'FAIL authorization: bearer secret123'}));
});
test('cannot invent failure lines absent a real job log',async()=>{
 await fails('NO_VERIFIABLE_FAILED_CI_LOG',()=>sourceEvidence({...options,runId:99}));
});
test('duplicate, oversized, private source refused',async()=>{
 await fails('EVIDENCE_REQUEST_INVALID',()=>sourceEvidence({...options,paths:[path,path]}));
 await fails('CONTENT_OR_BLOB_REFUSED',()=>sourceEvidence({...options,read:async p=>p.startsWith('/contents/')?{type:'file',sha:blob,encoding:'base64',size:8501,content:raw.toString('base64')}:read(p)}));
});
test('no malicious diagnostics concealed by ANSI stripping',()=>{
 assert.deepEqual(diagnosticLines('progress\n\x1b[31mFAIL build\x1b[0m'),['FAIL build']);
 assert.throws(()=>diagnosticLines('no errors'),e=>e instanceof EvidenceBlind);
});
test('real canonical V1 hydrator compiles exact verified source evidence', async()=>{
 const out=await hydrateFromGitHub(options);
 assert.equal(out.schema,'MERIDIAN-TASK-V1');
 assert.equal(out.source_files[0].source_mode,'100755');
 assert.equal(out.source_files[0].git_blob_sha,blob);
 assert.equal(out.checkpoint.state,'UNKNOWN');
 assert.equal(out.requested_result.authority,'DATA_ONLY_UNTRUSTED');
 assert.match(out.payload_sha256,/^[a-f0-9]{64}$/);
});
