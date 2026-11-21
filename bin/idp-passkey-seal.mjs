// idp-passkey-seal -- decide whether a commit carries the founder's seal, from a passkey.
//
// The seal used to be an Ed25519 file on one MacBook (`bin/idp-auth`, ~/.idp/founder.key).
// This is the second, device-independent proof: a P-256 signature from the founder's passkey,
// over a payload that names the exact commit, a one-time nonce and the guarded paths. The
// public key is the keyring committed at docs/keys/founder-passkey.json by the enrolment
// ceremony (bin/idp-passkey-enroll).
//
// A signature alone is still not an approval: the nonce must be one this host has never
// consumed, so a captured trailer cannot be replayed onto another commit. Refusal is the
// default for every missing, stale or mismatched input.
//
//   usage: node bin/idp-passkey-seal.mjs --repo <root> --commit <sha> [--keyring <path>]
//   exit:  0 sealed · 1 refused · 2 unusable input

import { createHash, createPublicKey, verify } from 'node:crypto';
import { appendFileSync, existsSync, readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join } from 'node:path';
import { homedir } from 'node:os';

const VERSION = 'idp-founder-seal-v1';
const MAX_AGE_MS = 24 * 3600 * 1000;
const args = process.argv.slice(2);
const get = n => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : undefined; };
const repo = get('--repo') || '.';
const commit = get('--commit') || 'HEAD';
const files = (get('--files') || '').split(',').map(s => s.trim()).filter(Boolean);
const keyringPath = get('--keyring') || join(repo, 'docs/keys/founder-passkey.json');
const ledger = process.env.IDP_SEAL_LEDGER || join(homedir(), '.estate/state/passkey-seal-nonces.jsonl');

const refuse = (why, code = 1) => { process.stderr.write('REFUSE passkey-seal: ' + why + '\n'); return code; };

function git(...a) {
  try { return execFileSync('git', ['-C', repo, ...a], { encoding: 'utf8' }).trim(); }
  catch { return ''; }
}

function trailer(msg, key) {
  const line = msg.split('\n').find(l => l.startsWith(key + ': '));
  return line ? line.slice(key.length + 2).trim() : '';
}

function main() {
  if (!existsSync(keyringPath)) return refuse('no keyring at ' + keyringPath + ' (enrol first)', 2);
  const ring = JSON.parse(readFileSync(keyringPath, 'utf8'));
  for (const k of ['credentialId', 'publicKeySpki', 'rpId', 'origin', 'enrollmentCommit']) {
    if (!ring[k]) return refuse('keyring is missing ' + k, 2);
  }

  const sha = git('rev-parse', commit);
  if (!/^[0-9a-f]{40}$/.test(sha)) return refuse('cannot resolve ' + commit, 2);
  const parent = git('rev-parse', sha + '^');
  if (!/^[0-9a-f]{40}$/.test(parent)) return refuse('commit ' + sha + ' has no parent', 2);

  const msg = git('log', '-1', '--format=%B', sha);
  const sig = trailer(msg, 'X-Idp-Seal');
  const nonce = trailer(msg, 'X-Idp-Seal-Nonce');
  const at = trailer(msg, 'X-Idp-Seal-At');
  const target = trailer(msg, 'X-Idp-Seal-Target');
  const paths = trailer(msg, 'X-Idp-Seal-Paths');
  if (!sig || !nonce || !at || !target || !paths) return refuse('commit carries no seal trailers');

  // What the founder actually sealed. A signature over "bin/x" must not lift the file ceiling
  // and the guarded-path rule for a commit that also rewrites .github/workflows, so every file
  // the commit touches has to be inside the sealed list. Exact path, a trailing '/' prefix, or
  // a '/**' subtree.
  const sealed = paths.split(',').map(s => s.trim()).filter(Boolean);
  const covers = (pattern, file) => {
    if (pattern === file) return true;
    if (pattern.endsWith('/**')) return file.startsWith(pattern.slice(0, -2));
    if (pattern.endsWith('/')) return file.startsWith(pattern);
    return false;
  };
  const unsealed = files.filter(f => !sealed.some(p => covers(p, f)));
  if (unsealed.length) {
    return refuse(`seal does not cover ${unsealed.slice(0, 3).join(', ')}${unsealed.length > 3 ? ` (+${unsealed.length - 3})` : ''}`);
  }

  // The founder signs the commit her seal applies to, which is the parent of the commit that
  // carries the trailers -- the same rule bin/idp-auth-verify uses for the file key.
  if (target !== parent) return refuse(`seal targets ${target.slice(0, 12)}, parent is ${parent.slice(0, 12)}`);
  const ts = Date.parse(at);
  if (!Number.isFinite(ts)) return refuse('X-Idp-Seal-At is not a timestamp');
  const age = Date.now() - ts;
  if (age > MAX_AGE_MS || age < -300000) return refuse('seal is stale or from the future');

  const payload = Buffer.from(
    [VERSION, parent, nonce, at, ...paths.split(',')].join('\n'), 'utf8');
  let key;
  try {
    key = createPublicKey({ key: Buffer.from(ring.publicKeySpki, 'base64url'), format: 'der', type: 'spki' });
  } catch { return refuse('keyring public key is not valid SPKI', 2); }
  if (key.asymmetricKeyType !== 'ec') return refuse('keyring key is not EC', 2);

  let ok = false;
  try {
    ok = verify('sha256', payload, { key, dsaEncoding: 'der' }, Buffer.from(sig, 'base64url'));
  } catch { ok = false; }
  if (!ok) return refuse('signature does not verify against the enrolled key');

  // One-time nonce, with the identity of what it sealed. The same nonce over the same commit is
  // the same seal read again -- pre-commit, pre-push and CI all ask, and a gate that answered
  // differently the second time would block the commit it just approved. A nonce over a
  // different commit is a replay and is refused, which is the actual attack: two commits off one
  // parent share the payload, so only the recorded sha tells them apart.
  const payloadSha256 = createHash('sha256').update(payload).digest('hex');
  if (existsSync(ledger)) {
    for (const line of readFileSync(ledger, 'utf8').split('\n')) {
      if (!line.trim()) continue;
      let seen;
      try { seen = JSON.parse(line); } catch { continue; }
      if (seen.nonce !== nonce) continue;
      if (seen.sha === sha && seen.payloadSha256 === payloadSha256) {
        process.stdout.write(`ok passkey-seal: ${sha.slice(0, 12)} already sealed by ${ring.rpId} nonce ${nonce}\n`);
        return 0;
      }
      return refuse(`nonce already consumed by ${String(seen.sha).slice(0, 12)}`);
    }
  }
  appendFileSync(ledger, JSON.stringify({ nonce, sha, at, payloadSha256 }) + '\n');

  process.stdout.write(`ok passkey-seal: ${sha.slice(0, 12)} sealed by ${ring.rpId} nonce ${nonce}\n`);
  return 0;
}

process.exit(main());
