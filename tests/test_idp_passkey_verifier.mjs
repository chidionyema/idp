import test from 'node:test';
import assert from 'node:assert/strict';
import { generateKeyPairSync, createHash, randomBytes, sign } from 'node:crypto';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { approvalPayload, verifyAssertion, checkFromFiles, decodeB64url } from '../bin/idp-passkey-verify.mjs';

const sha = x => createHash('sha256').update(x).digest();
const enc = x => Buffer.from(x).toString('base64url');
const head = x => x.repeat(40);
const content = x => x.repeat(64);
const { privateKey, publicKey } = generateKeyPairSync('ec',{namedCurve:'P-256'});
const cred = randomBytes(32);
const now = Date.parse('2026-11-16T20:30:00.000Z');
const baseManifest = {
  version:'idp-founder-approval-v1',
  requestedAt:'2026-11-16T20:29:00.000Z',
  baseSha:head('a'),
  contentSha256:content('b'),
  change:'Authorise reviewed changes to #8175 and #8182',
  targets:[
    {pr:8175,head:head('c')},
    {pr:8182,head:head('d')},
  ],
};
const baseKeyring = {
  credentialId:enc(cred),
  publicKeySpki:enc(publicKey.export({format:'der',type:'spki'})),
  rpId:'passkey.mumchimp.com',
  origin:'https://passkey.mumchimp.com',
  enrollmentCommit:head('e'),
};
function sample({
  keyring=baseKeyring, manifest=baseManifest, signer=privateKey,
  rpId=keyring.rpId, flags=0x05, origin=keyring.origin,
  challenge=enc(sha(approvalPayload(manifest))), type='webauthn.get',
  clientCrossOrigin=false, credentialId=keyring.credentialId,
}={}) {
  const clientDataJSON=Buffer.from(JSON.stringify({type,origin,challenge,crossOrigin:clientCrossOrigin}));
  const authData=Buffer.concat([sha(Buffer.from(rpId,'utf8')),Buffer.from([flags]),Buffer.alloc(4)]);
  const signed=Buffer.concat([authData,sha(clientDataJSON)]);
  return {
    credentialId,authenticatorData:enc(authData),clientDataJSON:enc(clientDataJSON),
    signature:enc(sign('sha256',signed,signer)),
  };
}
function check(overrides={}) {
  const m=structuredClone(overrides.manifest||baseManifest);
  const k=structuredClone(overrides.keyring||baseKeyring);
  const assertion=overrides.assertion||sample({manifest:m,keyring:k});
  return verifyAssertion({manifest:m,keyring:k,assertion,nowMs:overrides.nowMs??now});
}
test('P01 valid authentic ES256 UV assertion binds exactly two heads but NEVER grants authority',()=>{
  const r=check();
  assert.equal(r.signatureVerified,true);
  assert.equal(r.verdict,'CRYPTO_ASSERTION_VERIFIED_ONLY');
  assert.equal(r.admissionPermitted,false);
  assert.equal(r.challengeConsumed,false);
  assert.equal(r.independentGitHubHeadsChecked,false);
  assert.deepEqual(r.targetHeads.map(x=>x.pr),[8175,8182]);
});
test('P02 deterministic canonical payload is exactly SHA-256 WebAuthn challenge bytes',()=>{
  const raw=approvalPayload(baseManifest);
  assert.match(raw.toString(),/^idp-founder-approval-v1\n/);
  assert.match(raw.toString(),/PR #8175 @ c{40}\nPR #8182 @ d{40}$/);
  assert.equal(check().challenge,enc(sha(raw)));
});
test('P03 forged trailer or empty assertion cannot be authorisation',()=>{
  assert.throws(()=>checkFromFiles({keyring:baseKeyring,manifest:baseManifest,assertions:[],nowMs:now}),/no cryptographically valid assertion/);
  assert.throws(()=>checkFromFiles({keyring:baseKeyring,manifest:baseManifest,assertions:[{trailer:'X-Founder-Passkey-Seal: forged'}],nowMs:now}),/no cryptographically valid assertion/);
});
test('P04 invalid signature from different signer is refused',()=>{
  const evil=generateKeyPairSync('ec',{namedCurve:'P-256'});
  assert.throws(()=>check({assertion:sample({signer:evil.privateKey})}),/signature invalid/);
});
test('P05 same signed assertion cannot be reused for different target head',()=>{
  const old=sample();
  const mutated=structuredClone(baseManifest);mutated.targets[1].head=head('f');
  assert.throws(()=>check({manifest:mutated,assertion:old}),/challenge not bound/);
});
test('P06 changing the trusted base or content digest breaks challenge binding',()=>{
  const orig=sample();
  for (const key of ['baseSha','contentSha256']) {
    const m=structuredClone(baseManifest);
    m[key]=key==='baseSha'?head('f'):content('f');
    assert.throws(()=>check({manifest:m,assertion:orig}),/challenge not bound/);
  }
});
test('P07 cross-origin passkey assertion is refused',()=>{
  assert.throws(()=>check({assertion:sample({origin:'https://evil.example.com'})}),/origin/);
  assert.throws(()=>check({assertion:sample({clientCrossOrigin:true})}),/origin/);
});
test('P08 wrong RP ID hash is refused',()=>{
  assert.throws(()=>check({assertion:sample({rpId:'evil.example.com'})}),/RP ID/);
});
test('P09 both physical presence and actual user verification required',()=>{
  assert.throws(()=>check({assertion:sample({flags:0})}),/presence/);
  assert.throws(()=>check({assertion:sample({flags:0x01})}),/verification/);
});
test('P10 unregistered credential ID is refused',()=>{
  assert.throws(()=>check({assertion:sample({credentialId:enc(randomBytes(32))})}),/credential not enrolled/);
});
test('P11 expires and rejects future timestamps',()=>{
  assert.throws(()=>check({nowMs:now+20*60_000}),/expired/);
  assert.throws(()=>check({nowMs:now-3*60_000}),/created in future/);
});
test('P12 rejects malformed and noncanonical base64url',()=>{
  for (const s of ['','A','__==','a b','!!']) assert.throws(()=>decodeB64url(s));
});
test('P13 wrong algorithm, corrupted key and missing enrollment provenance fail closed',()=>{
  const x=structuredClone(baseKeyring);x.enrollmentCommit='';
  assert.throws(()=>check({keyring:x}),/enrollment/);
  const y=structuredClone(baseKeyring);y.publicKeySpki=enc(Buffer.from('not-a-key'));
  assert.throws(()=>check({keyring:y}),/key material/);
  const z=structuredClone(baseKeyring);z.origin='https://alternate.example.com';
  assert.throws(()=>check({keyring:z}),/origin/);
});
test('P14 invalid or duplicate PR targets cannot be signed',()=>{
  const m=structuredClone(baseManifest);m.targets.push({...m.targets[0]});
  assert.throws(()=>approvalPayload(m),/duplicate/);
  const m2=structuredClone(baseManifest);m2.targets.reverse();
  assert.throws(()=>approvalPayload(m2),/canonical/);
});
test('P15 untrusted report fields are refused before verifying',()=>{
  const m=structuredClone(baseManifest);m.productionVerified=true;
  assert.throws(()=>approvalPayload(m),/unexpected field/);
  const assertion=sample();assertion.authorized=true;
  assert.throws(()=>check({assertion}),/unexpected field/);
});
test('P16 cap on posted assertions; one genuine after junk returns crypto-only evidence',()=>{
  assert.throws(()=>checkFromFiles({keyring:baseKeyring,manifest:baseManifest,assertions:Array(6).fill(sample()),nowMs:now}),/assertion list/);
  const r=checkFromFiles({keyring:baseKeyring,manifest:baseManifest,assertions:[{junk:true},sample()],nowMs:now});
  assert.equal(r.admissionPermitted,false);
  assert.equal(r.signatureVerified,true);
});
test('P17 CLI always exits nonzero even with authentic assertion because anti-replay gate not integrated',()=>{
  const folder=mkdtempSync(path.join(tmpdir(),'idp-passkey-'));
  try{
    for(const [p,x] of [['keyring.json',baseKeyring],['manifest.json',baseManifest],['assertions.json',[sample()]]]){
      writeFileSync(path.join(folder,p),JSON.stringify(x));
    }
    // CLI uses wall clock and intentionally refuses an older ceremony.
    const result=spawnSync(process.execPath,[
      new URL('../bin/idp-passkey-verify.mjs',import.meta.url).pathname,
      '--keyring',path.join(folder,'keyring.json'),
      '--manifest',path.join(folder,'manifest.json'),
      '--assertions',path.join(folder,'assertions.json')
    ],{encoding:'utf8',timeout:15000});
    assert.notEqual(result.status,0);
  } finally{rmSync(folder,{recursive:true,force:true});}
});
