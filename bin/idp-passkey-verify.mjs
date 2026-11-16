#!/usr/bin/env node
/**
 * Read-only WebAuthn founder assertion cryptographic verifier.
 *
 * This is NOT the production admission gate. It deliberately returns an
 * admissionPermitted=false receipt until trusted key enrollment, atomic
 * challenge consumption and gate wiring are exercised end to end.
 *
 * Canonical protocol is exactly the source Worker at
 * platform/founder-passkey/worker.js: challenge = SHA256(UTF8(payload)).
 *
 * CLI: node bin/idp-passkey-verify.mjs --keyring trusted.json
 *        --manifest trusted-approval-manifest.json --assertions worker.json
 */
import {
  createHash, createPublicKey, timingSafeEqual, verify as verifySignature,
} from 'node:crypto';
import { readFileSync } from 'node:fs';

const HEX40 = /^[0-9a-f]{40}$/;
const HEX64 = /^[0-9a-f]{64}$/;
const B64 = /^[A-Za-z0-9_-]+$/;
const VERSION = 'idp-founder-approval-v1';

function reject(message) { throw new Error('REFUSE_PASSKEY: ' + message); }

export function decodeB64url(x, max = 8192) {
  if (typeof x !== 'string' || !x || x.length > max || !B64.test(x) || x.length % 4 === 1) {
    reject('malformed base64url');
  }
  const bytes = Buffer.from(x, 'base64url');
  if (bytes.toString('base64url') !== x) reject('noncanonical base64url');
  return bytes;
}
export function sha256(b) { return createHash('sha256').update(b).digest(); }
function same(a, b) { return a.length === b.length && timingSafeEqual(a,b); }
function strictObject(x, name) {
  if (x === null || typeof x !== 'object' || Array.isArray(x)) reject(name + ' must be an object');
}
function strictKeys(obj, allowed, name) {
  for (const key of Object.keys(obj)) if (!allowed.includes(key)) reject(name + ' contains unexpected field ' + key);
}
function validRpId(host) {
  if (typeof host !== 'string' || host.length > 253 ||
    !/^(?:[a-z0-9]+(?:-[a-z0-9]+)*\.)+[a-z]{2,}$/.test(host)) reject('invalid RP ID');
}
function validateManifest(m) {
  strictObject(m, 'manifest');
  strictKeys(m,['version','requestedAt','baseSha','contentSha256','change','targets'],'manifest');
  if (m.version !== VERSION) reject('unsupported approval protocol');
  const date = typeof m.requestedAt === 'string' ? Date.parse(m.requestedAt) : NaN;
  if (!Number.isFinite(date) || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{3})?Z$/.test(m.requestedAt)) {
    reject('invalid requestedAt UTC timestamp');
  }
  if (!HEX40.test(m.baseSha) || !HEX64.test(m.contentSha256)) reject('invalid base or content SHA');
  if (typeof m.change !== 'string' || !m.change || m.change.length > 250 || /[\r\n\x00-\x1f]/.test(m.change)) {
    reject('invalid human-readable change');
  }
  if (!Array.isArray(m.targets) || m.targets.length < 1 || m.targets.length > 5) reject('target count outside 1..5');
  const found = new Set();
  for (const t of m.targets) {
    strictObject(t,'target'); strictKeys(t,['pr','head'],'target');
    if (!Number.isInteger(t.pr) || t.pr <= 0 || !HEX40.test(t.head) || found.has(t.pr)) {
      reject('invalid, duplicate or unpinned PR head');
    }
    found.add(t.pr);
  }
  if (![...m.targets].sort((a,b) => a.pr-b.pr).every((t,i)=>t.pr===m.targets[i].pr)) {
    reject('targets must be in canonical PR-number order');
  }
  return date;
}
export function approvalPayload(m) {
  validateManifest(m);
  return Buffer.from([
    VERSION,m.requestedAt,m.baseSha,m.contentSha256,m.change,
    ...m.targets.map(t=>\`PR #\${t.pr} @ \${t.head}\`),
  ].join('\n'),'utf8');
}

export function verifyAssertion({ keyring, manifest, assertion, nowMs = Date.now() }) {
  strictObject(keyring,'keyring');
  strictKeys(keyring,['credentialId','publicKeySpki','rpId','origin','enrollmentCommit'],'keyring');
  validRpId(keyring.rpId);
  if (keyring.origin !== 'https://' + keyring.rpId) reject('origin mismatch with pinned RP ID');
  if (!HEX40.test(keyring.enrollmentCommit)) reject('missing founder-authorized enrollment commit');
  const expectedId = decodeB64url(keyring.credentialId, 512);
  const keyDER = decodeB64url(keyring.publicKeySpki, 4096);
  if (!expectedId.length || keyDER.length < 64) reject('invalid credential key material');
  let key;
  try { key=createPublicKey({key:keyDER,format:'der',type:'spki'}); }
  catch { reject('invalid SPKI public key'); }
  if (key.asymmetricKeyType!=='ec' || key.asymmetricKeyDetails?.namedCurve!=='prime256v1') {
    reject('passkey algorithm must be ES256 P-256');
  }
  const created = validateManifest(manifest);
  if (!Number.isFinite(nowMs) || created > nowMs + 60_000 || nowMs-created > 15 * 60_000) {
    reject('approval expired or created in future');
  }
  strictObject(assertion,'assertion');
  strictKeys(assertion,
    ['credentialId','authenticatorData','clientDataJSON','signature'],'assertion');
  if (!same(decodeB64url(assertion.credentialId,512),expectedId)) reject('credential not enrolled');
  const auth = decodeB64url(assertion.authenticatorData,4096);
  const clientBytes = decodeB64url(assertion.clientDataJSON,8192);
  const sig = decodeB64url(assertion.signature,2048);
  if (auth.length < 37 || sig.length < 16) reject('short authenticator assertion');
  if (!same(auth.subarray(0,32),sha256(Buffer.from(keyring.rpId,'utf8')))) {
    reject('RP ID hash does not match pinned passkey host');
  }
  const flags = auth[32];
  if (!(flags & 0x01) || !(flags & 0x04)) reject('user presence AND user verification required');
  if (flags & 0x40) reject('unexpected attested credential data in assertion');
  let client;
  try { client=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(clientBytes)); }
  catch { reject('unreadable clientDataJSON'); }
  strictObject(client,'clientData');
  if (client.type!=='webauthn.get' || client.origin!==keyring.origin ||
    client.crossOrigin === true || client.topOrigin) reject('invalid WebAuthn ceremony or origin');
  const challenge=sha256(approvalPayload(manifest));
  if (!same(decodeB64url(client.challenge,512),challenge)) reject('challenge not bound to exact manifesto');
  const signBytes=Buffer.concat([auth,sha256(clientBytes)]);
  let valid=false;
  try { valid=verifySignature('sha256',signBytes,key,sig); } catch { valid=false; }
  if (!valid) reject('P-256 assertion signature invalid');
  return Object.freeze({
    verdict:'CRYPTO_ASSERTION_VERIFIED_ONLY',
    admissionPermitted:false,
    rpId:keyring.rpId,
    targetHeads:manifest.targets.map(t=>({pr:t.pr,head:t.head})),
    challenge:challenge.toString('base64url'),
    signedPayloadSha256:sha256(approvalPayload(manifest)).toString('hex'),
    signatureVerified:true,
    enrolledKeyProvenance:'DECLARED_NOT_ADJUDICATED',
    challengeConsumed:false,
    independentGitHubHeadsChecked:false,
    note:'Caller must authenticate trusted-main enrollment commit, check live PR heads, consume challenge once atomically and run the actual signed guard. This receipt cannot release production.',
  });
}
export function checkFromFiles({keyring,manifest,assertions}) {
  if (!Array.isArray(assertions) || assertions.length > 5) reject('invalid assertion list');
  let receipts=[];
  for (const assertion of assertions) {
    try { receipts.push(verifyAssertion({keyring,manifest,assertion})); }
    catch { /* Ignore untrusted malformed candidates, but do NOT admit anything. */ }
  }
  if (!receipts.length) reject('no cryptographically valid assertion for requested target heads');
  return receipts[0];
}
const cliArgs = process.argv.slice(2);
if (process.argv[1] && /idp-passkey-verify\.mjs$/.test(process.argv[1])) {
  const get = name => {
    const at=cliArgs.indexOf(name);
    if (at<0 || at===cliArgs.length-1 || cliArgs.indexOf(name,at+1)!==-1) reject('required unique argument '+name);
    return cliArgs[at+1];
  };
  try {
    const keyring=JSON.parse(readFileSync(get('--keyring'),'utf8'));
    const manifest=JSON.parse(readFileSync(get('--manifest'),'utf8'));
    const assertions=JSON.parse(readFileSync(get('--assertions'),'utf8'));
    const result=checkFromFiles({keyring,manifest,assertions});
    process.stdout.write(JSON.stringify(result)+'\n');
    // Intentionally nonzero until an independently reviewed trusted admission
    // ceremony exists. A cryptographic-only receipt NEVER acts as approval.
    process.exitCode=3;
  } catch (e) {
    process.stderr.write('REFUSED: '+e.message+'\n');
    process.exitCode=2;
  }
}
