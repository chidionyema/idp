import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generateKeyPairSync } from 'node:crypto';
import { execFileSync, spawnSync } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { signSeal, sealPayload } from '../src/seal.js';
const verifier = fileURLToPath(new URL('../../../bin/idp-auth-verify', import.meta.url));

test('seal bytes match the independent shell verifier', () => {
  assert.equal(sealPayload({ts:'t',head:'h',reason:'r',paths:['a','b']}), 't\nh\nr\na\nb');
});

test('actual CLI verifies a Worker-signed Git commit, rejects tampering', async () => {
  const dir = mkdtempSync(join(tmpdir(), 'seal-cli-'));
  try {
    const git = (...args) => execFileSync('git', ['-C', dir, ...args], { encoding: 'utf8', stdio:['ignore','pipe','pipe'] }).trim();
    git('init','-q'); git('config','user.name','Synthetic test'); git('config','user.email','test@invalid'); git('commit','--allow-empty','-qm','base');
    const parent = git('rev-parse','HEAD');
    const {privateKey,publicKey} = generateKeyPairSync('ed25519');
    const pub = join(dir,'test.pub'); writeFileSync(pub,publicKey.export({type:'spki',format:'pem'}));
    const r = await signSeal({FOUNDER_SEAL_KEY_PEM:privateKey.export({type:'pkcs8',format:'pem'})},{head:parent,reason:'synthetic compatibility test',paths:['.github/workflows/incident-loop.yml','bin/idp-auth']});
    assert.equal(r.ok,true); git('commit','--allow-empty','-qm','test\n\n'+r.trailer);
    const check = () => spawnSync('bash',[verifier,'HEAD'],{cwd:dir,env:{...process.env,IDP_FOUNDER_PUBKEY:pub},encoding:'utf8'});
    const valid=check(); assert.equal(valid.status,0,valid.stderr);
    git('commit','--amend','--allow-empty','-qm','test\n\n'+r.trailer.replace('synthetic compatibility test','tampered'));
    assert.equal(check().status,1);
  } finally {rmSync(dir,{recursive:true,force:true});}
});
