import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdtempSync, readFileSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { parseArgs, createPacket } from '../../scripts/web-fleet/task-packet.mjs';
import { EvidenceBlind } from '../../scripts/web-fleet/github-evidence.mjs';

const argv = ['--issue', '8430', '--file', 'platform/lifeboat/src/task-packet.js', '--instruction', 'FIR-07'];
const parsed = () => parseArgs(argv);
const blind = (code, f) => assert.throws(f, (e) => e instanceof EvidenceBlind && e.code === code);

const raw=Buffer.from('export const x=1;\n');
const blob=createHash('sha1').update(Buffer.from(`blob ${raw.length}\0`)).update(raw).digest('hex');
const commit='a'.repeat(40), tree='b'.repeat(40), subtree='c'.repeat(40);
const gitRead=async (p) => {
  if(p==='/branches/main') return {commit:{sha:commit}};
  if(p==='/issues/8430')return {number:8430,state:'open'};
  if(p===`/git/commits/${commit}`)return {tree:{sha:tree}};
  if(p===`/git/trees/${tree}`)return {tree:[{path:'platform',type:'tree',sha:subtree}]};
  if(p===`/git/trees/${subtree}`)return {tree:[{path:'lifeboat',type:'tree',sha:'d'.repeat(40)}]};
  if(p==='/git/trees/'+'d'.repeat(40))return {tree:[{path:'src',type:'tree',sha:'e'.repeat(40)}]};
  if(p==='/git/trees/'+'e'.repeat(40))return {tree:[{path:'task-packet.js',type:'blob',sha:blob,mode:'100644'}]};
  if(p===`/contents/platform/lifeboat/src/task-packet.js?ref=${commit}`)
    return {type:'file',encoding:'base64',sha:blob,size:raw.length,content:raw.toString('base64')};
  if(p==='/actions/runs/45039629748')return {id:45039629748,head_sha:commit};
  if(p==='/actions/runs/45039629748/jobs?per_page=100')
    return {jobs:[{id:1001,conclusion:'failure'}]};
  throw new Error(`Unexpected GitHub fixture path ${p}`);
};


// All cases are offline. The real GitHub API and actual V1 module are proved
// separately by github-evidence.test.mjs and the independent cloud run.
test('deterministic real-world CLI request with untrusted owner and explicit accepted source', () => {
  const p = parsed();
  assert.equal(p.issue, 8430);
  assert.equal(p.instructionId, 'FIR-07');
  assert.equal(p.taskId, 'IDP-8430-SOURCE');
  assert.equal(p.owner, 'web-fleet-unverified');
  assert.equal(p.paths.length, 1);
  assert.ok(p.acceptance.includes('data-only'));
});
test('help is immediate and does not perform a GitHub read', () => {
  const child = spawnSync(process.execPath, ['scripts/web-fleet/task-packet.mjs', '--help'], {encoding:'utf8'});
  assert.equal(child.status, 0);
  assert.match(child.stdout, /MERIDIAN-TASK-V1/);
});
test('missing issue refuses before network', () => blind('MISSING_OR_INVALID_ISSUE', () => parseArgs(['--file','a.js'])));
test('unknown option, missing value and flags used as values refuse', () => {
  for (const args of [['--magic','1'],['--issue','4','--file'],['--issue','--file','--file','a.js']]) {
    blind('INVALID_CLI_ARGUMENTS', () => parseArgs(args));
  }
});
test('duplicate scalar flag and duplicate file refuse', () => {
  blind('DUPLICATE_CLI_FLAG', () => parseArgs([...argv,'--issue','8431']));
  blind('INVALID_SOURCE_PATH_COUNT', () => parseArgs([...argv,'--file',parsed().paths[0]]));
});
test('bad numeric run and oversized acceptance refuse', () => {
  blind('INVALID_RUN_ID', () => parseArgs([...argv,'--run','-1']));
  blind('ACCEPTANCE_OVERSIZE', () => parseArgs([...argv,'--acceptance','x'.repeat(1201)]));
});
test('canonical V1 only: reject fabricated V2 even when shape plausible', async () => {
  await assert.rejects(createPacket(parsed(), { read:gitRead, hydrate: async () => ({schema:'MERIDIAN-TASK-V2'}) }),
    (e) => e instanceof EvidenceBlind && e.code === 'NON_CANONICAL_PACKET');
});
test('canonical V1 packet output cannot grant execution authority', async () => {
  const dir=mkdtempSync(join(tmpdir(),'meridian-v1-packet-'));
  const out=join(dir,'packet.json');
  const packet={schema:'MERIDIAN-TASK-V1',requested_result:{authority:'DATA_ONLY_UNTRUSTED'},payload_sha256:'a'.repeat(64)};
  const built=await createPacket({...parsed(),outFile:out},{read:gitRead,hydrate:async()=>packet});
  assert.equal(built,packet);
  assert.equal(JSON.parse(readFileSync(out,'utf8')).schema,'MERIDIAN-TASK-V1');
  assert.equal(statSync(out).mode & 0o777,0o600);
  await assert.rejects(createPacket({...parsed(),outFile:out},{read:gitRead,hydrate:async()=>packet}),/EEXIST/);
});
test('wire >12 KiB is rejected, not truncated',async()=>{
  const big={schema:'MERIDIAN-TASK-V1',requested_result:{authority:'DATA_ONLY_UNTRUSTED'},payload_sha256:'x'.repeat(12500)};
  await assert.rejects(createPacket(parsed(),{read:gitRead,hydrate:async()=>big}),(e)=>e instanceof EvidenceBlind&&e.code==='WIRE_EXCEEDS_12K');
});
test('unverified CI run without a real log reader stays BLIND',async()=>{
  const p=parseArgs([...argv,'--run','45039629748']);
  const noSource=async()=>{throw new EvidenceBlind('NO_VERIFIABLE_FAILED_CI_LOG');};
  await assert.rejects(createPacket(p,{read:gitRead,hydrate:noSource}),(e)=>e instanceof EvidenceBlind&&e.code==='NO_VERIFIABLE_FAILED_CI_LOG');
});

import { validatePatch, assertPath } from '../../scripts/web-fleet/patch-wire.mjs';
import { hydrateTask } from '../../platform/lifeboat/src/task-packet.js';

test('legacy V2 compatibility door refuses duplicate authority', async () => {
  await assert.rejects(validatePatch({ schema: 'MERIDIAN-PATCH-V1' }, {schema:'MERIDIAN-TASK-V2'}),
    (e) => e.code === 'LEGACY_V2_SUPERSEDED');
});
test('compatibility door invokes exact V1 validator; never marks yield complete', async () => {
  const raw = Buffer.from('export const x=1;\n');
  const realBlob = createHash('sha1').update(Buffer.from(`blob ${raw.length}\0`)).update(raw).digest('hex');
  const valueSha = createHash('sha256').update(raw).digest('hex');
  const packet = await hydrateTask({taskId:'WEB-001',instructionId:'FIR-07',issue:8430,
    sourceSha:'a'.repeat(40),owner:'gemini-web-unverified',
    acceptance:'Data-only proposal; never an instruction to write main',
    files:[{path:'src/a.ts',blobSha:realBlob,mode:'100755',content:raw.toString(),sha256:valueSha}]});
  const proposal = {schema:'MERIDIAN-PATCH-V1',task_id:packet.task_id,base_sha:packet.source_sha,
    files:[{path:'src/a.ts',mode:'100755',content:raw.toString(),sha256:valueSha}]};
  const result = await validatePatch(proposal, packet);
  assert.equal(result.status, 'PROPOSED_UNTRUSTED');
  assert.equal(result.files, 1);
  assert.ok(result.needs.includes('TRUSTED_PRESEAL_CANONICALISATION'));
  await assert.rejects(validatePatch({...proposal, base_sha:'b'.repeat(40)},packet),e=>e.code==='STALE_OR_UNBOUND_PROPOSAL');
});


test('legacy compatibility path helper preserves all original denial boundaries', () => {
  assert.equal(assertPath('platform/estate/code.py'), 'platform/estate/code.py');
  for (const path of [
    'other/subdir/a.py', 'src/file.ts', '.github/workflows/evil.yml',
    'platform/../../.github/workflows/x.yml', 'platform/.env.prod',
    'platform/private/a.txt', 'platform/credentials/pass.pem',
    'platform/secret.key', 'platform/bundle.age', 'platform\\evil.js',
    'platform/a//x.js', '/tmp/a.ts',
  ]) assert.throws(() => assertPath(path), e => e.code === 'PATH_NOT_ADMITTED');
});
