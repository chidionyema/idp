/**
 * Read-only verifier for externally issued Ed25519 attestations.
 * The public key must be pinned outside the candidate's write scope.
 * This does not sign anything, set GitHub status or assert a test was run.
 */
import { readFileSync } from 'node:fs';
import { createPublicKey, verify as ed25519Verify } from 'node:crypto';

const PREFIX = Buffer.from('estate.external-verdict.v1\0', 'utf8');
const SHA256 = /^[a-f0-9]{64}$/;
const GIT_SHA = /^[a-f0-9]{40}$/;
const REPO = /^[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+$/;
const ISSUER = /^[a-zA-Z0-9_.\/-]{3,128}$/;
function exactKeys(o, keys) {
  return !!o && typeof o === 'object' && !Array.isArray(o) &&
    Object.keys(o).length === keys.length && keys.every(k => Object.hasOwn(o, k));
}
function b64(text, limit) {
  if (typeof text !== 'string' || !text ||
      !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(text) ||
      text.length > Math.ceil(limit / 3) * 4 + 4) throw Error('noncanonical-base64');
  const raw = Buffer.from(text, 'base64');
  if (raw.length > limit || raw.toString('base64') !== text)
    throw Error('noncanonical-base64');
  return raw;
}
/**
 * PASS proves Ed25519 signed-byte and expected-subject correspondence only.
 * Actual trial validity, issuer isolation, authorization, nonce replay control
 * and GitHub rule enforcement are distinct external acceptance obligations.
 */
export function verifyExternalVerdict(envelope, {
  trustedPublicKeyPem, expectedRepository, expectedCommit,
  expectedArtifactSha256, expectedEvidenceSha256, expectedIssuer,
  expectedNonce, nowSeconds = Math.floor(Date.now()/1000),
} = {}) {
  if (!trustedPublicKeyPem || !expectedRepository || !expectedCommit ||
      !expectedArtifactSha256 || !expectedEvidenceSha256 || !expectedIssuer ||
      !expectedNonce)
    return { verdict: 'UNVERIFIED', reason: 'external-trust-input-missing' };
  try {
    if (!exactKeys(envelope, ['schema','payload_b64','signature_b64']) ||
        envelope.schema !== 'estate.external-verdict.v1')
      return { verdict:'FAIL', reason:'invalid-envelope-schema' };
    const raw = b64(envelope.payload_b64, 16384);
    const sig = b64(envelope.signature_b64, 64);
    if (sig.length !== 64) return { verdict:'FAIL', reason:'bad-signature-length' };
    const key = createPublicKey(trustedPublicKeyPem);
    if (key.asymmetricKeyType !== 'ed25519')
      return { verdict:'FAIL', reason:'expected-ed25519-public-key' };
    if (!ed25519Verify(null, Buffer.concat([PREFIX,raw]), key, sig))
      return { verdict:'FAIL', reason:'signature-invalid' };
    const p = JSON.parse(raw.toString('utf8'));
    // The protocol's exact UTF-8 object field order is normative across Rust/JS.
    // Re-serialize only those ordered fields: reject duplicate, reordered and extra
    // keys even when the candidate signs a structurally ambiguous JSON document.
    const fields=['schema','repository','commit','artifact_sha256',
      'evidence_sha256','issuer','result','issued_at_unix','expires_at_unix','nonce'];
    if (!exactKeys(p, fields)) return { verdict:'FAIL', reason:'invalid-signed-payload' };
    const canonical = Object.fromEntries(fields.map(f => [f,p[f]]));
    if (!Buffer.from(JSON.stringify(canonical), 'utf8').equals(raw))
      return { verdict:'FAIL', reason:'noncanonical-signed-payload' };
    if (!exactKeys(p, fields) || p.schema !== 'estate.external-verdict.v1' ||
        !REPO.test(p.repository) || !GIT_SHA.test(p.commit) ||
        !SHA256.test(p.artifact_sha256) || !SHA256.test(p.evidence_sha256) ||
        !ISSUER.test(p.issuer) || !['PASS','FAIL','UNKNOWN'].includes(p.result) ||
        !Number.isSafeInteger(p.issued_at_unix) ||
        !Number.isSafeInteger(p.expires_at_unix) ||
        typeof p.nonce !== 'string' || !/^[a-f0-9]{32,64}$/.test(p.nonce))
      return { verdict:'FAIL', reason:'invalid-signed-payload' };
    if (p.repository !== expectedRepository || p.commit !== expectedCommit ||
        p.artifact_sha256 !== expectedArtifactSha256 ||
        p.evidence_sha256 !== expectedEvidenceSha256 || p.issuer !== expectedIssuer ||
        p.nonce !== expectedNonce)
      return { verdict:'FAIL', reason:'subject-or-issuer-mismatch' };
    if (!Number.isSafeInteger(nowSeconds) ||
        p.issued_at_unix > nowSeconds + 30 ||
        p.expires_at_unix <= nowSeconds ||
        p.expires_at_unix <= p.issued_at_unix ||
        p.expires_at_unix - p.issued_at_unix > 900)
      return { verdict:'FAIL', reason:'verdict-expired-or-invalid-time-window' };
    if (p.result !== 'PASS')
      return { verdict:'FAIL', reason:'signed-result-'+p.result };
    return { verdict:'PASS', reason:'ed25519-signed-subject-binding-valid',
      subject:{repository:p.repository,commit:p.commit,
        artifact_sha256:p.artifact_sha256,evidence_sha256:p.evidence_sha256},
      issuer:p.issuer, expires_at_unix:p.expires_at_unix };
  } catch(e) {
    return {verdict:'FAIL', reason:'malformed-or-invalid:'+e.message};
  }
}
// Read-only CLI. Never signs, writes status or loads a key from candidate data.
if (process.argv[1] &&
    import.meta.url === new URL('file://' + process.argv[1]).href) {
  const [file,repo,commit,artifact,evidence,issuer,nonce]=process.argv.slice(2);
  let envelope=null,publicKey;
  try {envelope=JSON.parse(readFileSync(file,'utf8'));}catch{}
  try {publicKey=readFileSync(process.env.EXTERNAL_CERTIFIER_PUBLIC_KEY_FILE,'utf8');}catch{}
  const result=verifyExternalVerdict(envelope,{
    trustedPublicKeyPem:publicKey,expectedRepository:repo,expectedCommit:commit,
    expectedArtifactSha256:artifact,expectedEvidenceSha256:evidence,
    expectedIssuer:issuer,expectedNonce:nonce});
  process.stdout.write(JSON.stringify(result)+'\n');
  process.exitCode=result.verdict==='PASS'?0:result.verdict==='UNVERIFIED'?2:1;
}
