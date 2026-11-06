import assert from 'node:assert/strict';
import { generateKeyPairSync, sign, createHmac, randomBytes } from 'node:crypto';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { verifyExternalVerdict } from './external-verdict-gate.mjs';

const {publicKey,privateKey}=generateKeyPairSync('ed25519');
const pem=publicKey.export({type:'spki',format:'pem'});
const other=generateKeyPairSync('ed25519');
const data={schema:'estate.external-verdict.v1',repository:'chidionyema/idp',
  commit:'1'.repeat(40),artifact_sha256:'2'.repeat(64),
  evidence_sha256:'3'.repeat(64),issuer:'external-certifier-app',
  result:'PASS',issued_at_unix:1799000000,expires_at_unix:1799000600,
  nonce:'4'.repeat(32)};
const prefix=Buffer.from('estate.external-verdict.v1\0');
function signed(p=data,key=privateKey) {
  const raw=Buffer.from(JSON.stringify(p),'utf8');
  return {schema:'estate.external-verdict.v1',payload_b64:raw.toString('base64'),
    signature_b64:sign(null,Buffer.concat([prefix,raw]),key).toString('base64')};
}
const expected={trustedPublicKeyPem:pem,expectedRepository:data.repository,
  expectedCommit:data.commit,expectedArtifactSha256:data.artifact_sha256,
  expectedEvidenceSha256:data.evidence_sha256,expectedIssuer:data.issuer,
  expectedNonce:data.nonce,nowSeconds:data.issued_at_unix+10};
const check=(e,opt=expected)=>verifyExternalVerdict(e,opt);

test('authentic Ed25519 subject binding passes',()=>{
  const x=check(signed());
  assert.equal(x.verdict,'PASS');
  assert.equal(x.subject.commit,data.commit);
});
test('absent externally pinned public key fails closed even if candidate submits its own',()=>{
  assert.equal(check({...signed(),public_key:pem},{...expected,trustedPublicKeyPem:null}).verdict,'UNVERIFIED');
  assert.equal(check(signed(),{...expected,trustedPublicKeyPem:null}).verdict,'UNVERIFIED');
});
test('distinct key pair cannot impersonate certifier',()=>{
  assert.equal(check(signed(data,other.privateKey)).reason,'signature-invalid');
});
test('post-signature modifications are rejected',()=>{
  const e=signed();const p=JSON.parse(Buffer.from(e.payload_b64,'base64').toString());
  p.commit='5'.repeat(40); e.payload_b64=Buffer.from(JSON.stringify(p)).toString('base64');
  assert.equal(check(e).reason,'signature-invalid');
});
test('wrong repository, commit, artifact, evidence or issuer fails despite a valid signature',()=>{
  for(const k of ['repository','commit','artifact_sha256','evidence_sha256','issuer']){
    const v=k==='repository'?'chidionyema/argon':
      k==='issuer'?'agent-proposer':'a'.repeat(k==='commit'?40:64);
    assert.equal(check(signed({...data,[k]:v})).reason,'subject-or-issuer-mismatch',k);
  }
});
test('replayed nonce is refused against a fresh verifier challenge',()=>{
  assert.equal(check(signed(),{...expected,expectedNonce:'5'.repeat(32)}).reason,
    'subject-or-issuer-mismatch');
});
test('signed payload with reordered keys is not canonical across runtimes',()=>{
  const reordered={commit:data.commit,schema:data.schema,
    repository:data.repository,...data};
  const e=signed(reordered);
  assert.equal(check(e).reason,'noncanonical-signed-payload');
});
test('signed expiry, future issuance and TTL over 15m are rejected',()=>{
  const cases=[
    [{...data,expires_at_unix:data.issued_at_unix+1},data.issued_at_unix+10],
    [{...data,issued_at_unix:data.issued_at_unix+100,
      expires_at_unix:data.issued_at_unix+700},expected.nowSeconds],
    [{...data,expires_at_unix:data.issued_at_unix+901},expected.nowSeconds],
  ];
  for(const [payload,clock] of cases)
    assert.equal(check(signed(payload),{...expected,nowSeconds:clock}).reason,
      'verdict-expired-or-invalid-time-window');
});
test('signed FAIL and UNKNOWN can never authorize promotion',()=>{
  for(const result of ['FAIL','UNKNOWN'])
    assert.equal(check(signed({...data,result})).reason,'signed-result-'+result);
});
test('HMAC cannot masquerade as an Ed25519 signature',()=>{
  const e=signed(); e.signature_b64=createHmac('sha256',randomBytes(32))
    .update(Buffer.from(e.payload_b64,'base64')).digest('base64');
  assert.equal(check(e).reason,'bad-signature-length');
});
test('unexpected envelope fields and bad base64 are refused',()=>{
  assert.equal(check({...signed(),override:'PASS'}).reason,'invalid-envelope-schema');
  assert.match(check({...signed(),signature_b64:'!!'}).reason,/noncanonical-base64/);
});
test('RSA PEM is not a substitute for the pinned Ed25519 key',()=>{
  const rsa=generateKeyPairSync('rsa',{modulusLength:2048}).publicKey
    .export({type:'spki',format:'pem'});
  assert.equal(check(signed(),{...expected,trustedPublicKeyPem:rsa}).reason,
    'expected-ed25519-public-key');
});
test('CLI exits 2 on absent external trust pin; never silently passes',()=>{
  const folder=mkdtempSync(join(tmpdir(),'estate-certifier-'));
  const filename=join(folder,'verdict.json');
  writeFileSync(filename,JSON.stringify(signed()));
  const script=fileURLToPath(new URL('./external-verdict-gate.mjs',import.meta.url));
  const processResult=spawnSync(process.execPath,[script,filename,
    data.repository,data.commit,data.artifact_sha256,
    data.evidence_sha256,data.issuer,data.nonce],
    {env:{...process.env,EXTERNAL_CERTIFIER_PUBLIC_KEY_FILE:'/nonexistent/key.pem'},encoding:'utf8'});
  assert.equal(processResult.status,2);
  assert.equal(JSON.parse(processResult.stdout).verdict,'UNVERIFIED');
});
test('even correctly signed duplicate JSON keys are not accepted',()=>{
  const raw=Buffer.from(JSON.stringify(data).replace('"result":"PASS"',
    '"result":"FAIL","result":"PASS"'));
  const e={schema:'estate.external-verdict.v1',payload_b64:raw.toString('base64'),
    signature_b64:sign(null,Buffer.concat([prefix,raw]),privateKey).toString('base64')};
  assert.equal(check(e).reason,'noncanonical-signed-payload');
});
