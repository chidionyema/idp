import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { PROVIDER_PILOTS, pilotRequest, prepareProviderPilot, parsePilotCLI } from '../../scripts/web-fleet/provider-pilots.mjs';

const SHA40 = 'a'.repeat(40), SHA64 = 'b'.repeat(64);
function canonical(opts) {
  const unsigned = {
    schema: 'MERIDIAN-TASK-V1', task_id: opts.taskId,
    root_instruction_id: opts.instructionId, issue: opts.issue,
    owner: opts.owner,
    source_repo: 'chidionyema/idp', source_sha: SHA40,
    source_files: opts.paths.map(path=>({path, content: 'readback'})),
    checkpoint: {state: 'UNKNOWN', lease: 'UNOBSERVED'},
    requested_result: {schema: 'MERIDIAN-PATCH-V1', authority: 'DATA_ONLY_UNTRUSTED'},
  };
  return {...unsigned,payload_sha256: createHash('sha256').update(JSON.stringify(unsigned)).digest('hex')};
}

for (const [provider, label] of [['zai','BR-ZAI-01'],['deepseek','BR-DSH-01'],['kimi','BR-KIMI-01']]) {
  test(`${provider}: one canonical V1 task, no new authority`, async () => {
    let observed;
    const packet = await prepareProviderPilot(provider, {hydrate: async request => {
      observed = request; return canonical(request);
    }});
    assert.equal(packet.schema, 'MERIDIAN-TASK-V1');
    assert.equal(packet.task_id, `${label}-SOURCE-PILOT`);
    assert.equal(observed.issue, 7794);
    assert.equal(observed.instructionId, 'FIR-07');
    assert.deepEqual(observed.checkpoint, {state:'UNKNOWN', lease:'UNOBSERVED'});
    assert.equal(observed.paths.length, 2);
    assert.match(observed.acceptance, /NO_CHANGE/);
    assert.match(observed.acceptance, /never assume current production health/);
  });
}
test('all provider identities and source scopes are distinct', () => {
  const all = Object.values(PROVIDER_PILOTS);
  assert.equal(new Set(all.map(p => p.id)).size, 3);
  assert.equal(new Set(all.map(p => p.owner)).size, 3);
  assert.equal(new Set(all.flatMap(p => p.paths)).size, 6);
  assert.ok(all.every(p => p.site.startsWith('https://')));
});
test('unknown provider cannot turn into an arbitrary website or credential', () => {
  for(const provider of ['gemini','https://evil.example','zai/../../','__proto__','constructor','']) {
    assert.throws(() => pilotRequest(provider), /UNKNOWN_PROVIDER_PILOT/);
  }
});
test('no paid API, token, login automation or browser wallet permissions in pilot spec', () => {
  for (const p of Object.values(PROVIDER_PILOTS)) {
    assert.deepEqual(Object.keys(p).sort(), ['focus','id','owner','paths','site']);
    assert.doesNotMatch(p.site, /\/api\/|\/console\/|[?]key=/i);
  }
  assert.ok(Object.values(PROVIDER_PILOTS).every(p=> !p.paths.some(x=>x.includes('.github/') || x.includes('.env'))));
});
test('non V1 result is rejected even when provider label matches', async () => {
  await assert.rejects(prepareProviderPilot('zai',{hydrate:async request=>({...canonical(request),schema:'MERIDIAN-TASK-V2'})}),/NONCANONICAL/);
});
test('forged ready lease and execution authority rejected', async () => {
  for(const patch of [{checkpoint:{state:'READY',lease:'fake'}},{requested_result:{schema:'MERIDIAN-PATCH-V1',authority:'EXECUTE'}}]){
    await assert.rejects(prepareProviderPilot('kimi',{hydrate:async request=>({...canonical(request),...patch})}),/NONCANONICAL/);
  }
});
test('no packet without pinned source SHA and digest', async()=>{
  for(const patch of [{source_sha:'unknown'},{payload_sha256:'bad'}]) {
    await assert.rejects(prepareProviderPilot('deepseek',{hydrate:async request=>({...canonical(request),...patch})}),/NONCANONICAL/);
  }
});
test('no packet with wrong task binding', async()=>{
  await assert.rejects(prepareProviderPilot('zai',{hydrate:async request=>({...canonical(request),task_id:'BR-DSH-01-SOURCE-PILOT'})}),/NONCANONICAL/);
});
test('source hydration errors fail closed, never fabricate', async()=>{
  await assert.rejects(prepareProviderPilot('deepseek',{hydrate:async()=>{throw Error('GITHUB_READ_UNAVAILABLE')}}),/GITHUB_READ_UNAVAILABLE/);
});
test('CLI flags require allowlisted provider and prevent overwrite arguments',()=>{
  assert.deepEqual(parsePilotCLI(['--provider','kimi']),{provider:'kimi',out:null});
  assert.deepEqual(parsePilotCLI(['--provider','zai','--out','/tmp/new.json']),{provider:'zai',out:'/tmp/new.json'});
  for(const args of [['--provider','evil'],['--provider','zai','--out','--help'],['--out','/tmp/new.json'],['--provider','zai','--api-key','abc']]){
    assert.throws(()=>parsePilotCLI(args),/INVALID_PILOT/);
  }
});
