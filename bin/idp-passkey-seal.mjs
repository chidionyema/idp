// idp-passkey-seal -- the founder's passkey seals a commit, and any host can check it offline.
//
// Two modes, one payload, one implementation:
//
//   --request   build the payload, print the one link the founder taps, poll the relay for the
//               assertion, verify it, and write it to docs/keys/approvals/<challenge>.json.
//               The private key never leaves the founder's device; this only stores a signature.
//   (default)   decide whether a commit carries that seal: the trailers name the parent, the
//               nonce, the time and the sealed paths; the assertion is read from the commit
//               itself, never the worktree.
//
// The seal used to be an Ed25519 file on one MacBook (~/.idp/founder.key). A WebAuthn passkey
// signs authenticatorData||sha256(clientDataJSON), never the payload, so the raw-signature check
// this file used to make could not accept a real Face ID tap at all (measured 2026-11-21). The
// checks now live in one place, bin/idp-passkey-verify.mjs, shared with the approval manifest.
//
//   usage: node bin/idp-passkey-seal.mjs --repo R --commit SHA [--files a,b] [--keyring P]
//          node bin/idp-passkey-seal.mjs --request --host passkey.example --files a,b
//   exit:  0 sealed · 1 refused · 2 unusable input

import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join, dirname } from 'node:path';
import { homedir } from 'node:os';
import { verifyAssertionOverPayload } from './idp-passkey-verify.mjs';

const VERSION = 'idp-founder-seal-v1';
const MAX_AGE_MS = 24 * 3600 * 1000;
const args = process.argv.slice(2);
const get = n => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : undefined; };
const has = n => args.includes(n);
const repo = get('--repo') || '.';
const keyringPath = get('--keyring') || join(repo, 'docs/keys/founder-passkey.json');
const list = v => (v || '').split(',').map(s => s.trim()).filter(Boolean);

const refuse = (why, code = 1) => { process.stderr.write('REFUSE passkey-seal: ' + why + '\n'); return code; };

function git(...a) {
  try { return execFileSync('git', ['-C', repo, ...a], { encoding: 'utf8' }).trim(); }
  catch { return ''; }
}

function trailer(msg, key) {
  const line = msg.split('\n').find(l => l.startsWith(key + ': '));
  return line ? line.slice(key.length + 2).trim() : '';
}

function keyring() {
  if (!existsSync(keyringPath)) return null;
  const ring = JSON.parse(readFileSync(keyringPath, 'utf8'));
  for (const k of ['credentialId', 'publicKeySpki', 'rpId', 'origin', 'enrollmentCommit']) {
    if (!ring[k]) throw new Error('keyring is missing ' + k);
  }
  return ring;
}

const payloadFor = (parent, nonce, at, paths) =>
  Buffer.from([VERSION, parent, nonce, at, ...paths].join('\n'), 'utf8');
const challengeOf = payload => createHash('sha256').update(payload).digest();
const b64u = b => Buffer.from(b).toString('base64url');

const assertionPath = (root, challenge) =>
  join(root, 'docs/keys/approvals', challenge.toString('hex') + '.json');

async function request() {
  const host = (get('--host') || '').replace(/^https?:\/\//, '').replace(/\/+$/, '');
  if (!/^(?:[a-z0-9]+(?:-[a-z0-9]+)*\.)+[a-z]{2,}$/.test(host)) return refuse('--host must be a bare hostname', 2);
  const paths = list(get('--files'));
  if (!paths.length) return refuse('--files is required: what exactly is being sealed', 2);

  let ring;
  try { ring = keyring(); } catch (e) { return refuse(e.message, 2); }
  if (!ring) return refuse('no keyring at ' + keyringPath + ' (enrol first)', 2);
  if (ring.rpId !== host) return refuse(`keyring was enrolled for ${ring.rpId}, not ${host}`, 2);

  const parent = git('rev-parse', 'HEAD');
  if (!/^[0-9a-f]{40}$/.test(parent)) return refuse('cannot resolve HEAD', 2);
  const nonce = get('--nonce') || b64u(createHash('sha256').update(String(Date.now()) + String(Math.random())).digest()).slice(0, 24);
  const at = get('--at') || new Date().toISOString().replace(/\.\d+Z$/, 'Z');
  const payload = payloadFor(parent, nonce, at, paths);
  const challenge = challengeOf(payload);

  process.stdout.write(`open    https://${host}/#p=${b64u(payload)}\n`);
  process.stdout.write(`waiting up to ${get('--timeout') || 900}s for the founder's tap ...\n`);

  const deadline = Date.now() + Number(get('--timeout') || 900) * 1000;
  const poll = Math.max(1, Number(get('--poll') || 5)) * 1000;
  let assertion = null;
  while (Date.now() < deadline && !assertion) {
    try {
      const r = await fetch(`https://${host}/approve/${b64u(challenge)}`, { cache: 'no-store' });
      if (r.ok) {
        for (const candidate of await r.json()) {
          try {
            verifyAssertionOverPayload({
              keyring: ring, payload, assertion: candidate, nowMs: Date.now(),
              maxAgeMs: MAX_AGE_MS, signedAtMs: Date.parse(at),
            });
            assertion = candidate;
            break;
          } catch { /* not this one */ }
        }
      }
    } catch { /* relay unreachable; keep waiting until the deadline */ }
    if (!assertion) await new Promise(r => setTimeout(r, poll));
  }
  if (!assertion) return refuse('no valid assertion was posted for this payload', 1);

  const dest = assertionPath(repo, challenge);
  mkdirSync(dirname(dest), { recursive: true, mode: 0o755 });
  writeFileSync(dest, JSON.stringify(assertion, null, 2) + '\n', { mode: 0o644 });
  process.stdout.write(`sealed  ${dest}\n`);
  process.stdout.write('trailers for the sealed commit:\n');
  for (const [k, v] of [['X-Idp-Seal-Nonce', nonce], ['X-Idp-Seal-At', at],
    ['X-Idp-Seal-Target', parent], ['X-Idp-Seal-Paths', paths.join(',')]]) {
    process.stdout.write(`${k}: ${v}\n`);
  }
  return 0;
}

function verify() {
  let ring;
  try { ring = keyring(); } catch (e) { return refuse(e.message, 2); }
  if (!ring) return refuse('no keyring at ' + keyringPath + ' (enrol first)', 2);

  const commit = get('--commit') || 'HEAD';
  const sha = git('rev-parse', commit);
  if (!/^[0-9a-f]{40}$/.test(sha)) return refuse('cannot resolve ' + commit, 2);
  const parent = git('rev-parse', sha + '^');
  if (!/^[0-9a-f]{40}$/.test(parent)) return refuse('commit ' + sha + ' has no parent', 2);

  const msg = git('log', '-1', '--format=%B', sha);
  const nonce = trailer(msg, 'X-Idp-Seal-Nonce');
  const at = trailer(msg, 'X-Idp-Seal-At');
  const target = trailer(msg, 'X-Idp-Seal-Target');
  const paths = trailer(msg, 'X-Idp-Seal-Paths');
  if (!nonce || !at || !target || !paths) return refuse('commit carries no seal trailers');

  // The founder signs the commit her seal applies to, which is the parent of the commit that
  // carries the trailers -- the same rule bin/idp-auth-verify uses for the file key.
  if (target !== parent) return refuse(`seal targets ${target.slice(0, 12)}, parent is ${parent.slice(0, 12)}`);

  // What the founder actually sealed. A signature over "bin/x" must not lift the file ceiling
  // and the guarded-path rule for a commit that also rewrites .github/workflows, so every file
  // the commit touches has to be inside the sealed list: exact path, trailing '/', or '/**'.
  const sealed = list(paths);
  const covers = (pattern, file) => {
    if (pattern === file) return true;
    if (pattern.endsWith('/**')) return file.startsWith(pattern.slice(0, -2));
    if (pattern.endsWith('/')) return file.startsWith(pattern);
    return false;
  };
  const files = list(get('--files'));
  const unsealed = files.filter(f => !sealed.some(p => covers(p, f)));
  if (unsealed.length) {
    return refuse(`seal does not cover ${unsealed.slice(0, 3).join(', ')}${unsealed.length > 3 ? ` (+${unsealed.length - 3})` : ''}`);
  }

  const payload = payloadFor(parent, nonce, at, sealed);
  const challenge = challengeOf(payload);
  const file = assertionPath(repo, challenge);
  // Read the assertion out of the commit, not the worktree: an uncommitted file must never seal.
  let raw = '';
  try { raw = execFileSync('git', ['-C', repo, 'show', `${sha}:docs/keys/approvals/${challenge.toString('hex')}.json`], { encoding: 'utf8' }); }
  catch { raw = ''; }
  if (!raw) return refuse(`no assertion committed for this payload (${file})`);

  let assertion;
  try { assertion = JSON.parse(raw); } catch { return refuse('committed assertion is not JSON', 2); }
  try {
    verifyAssertionOverPayload({
      keyring: ring, payload, assertion, nowMs: Date.now(),
      maxAgeMs: MAX_AGE_MS, signedAtMs: Date.parse(at),
    });
  } catch (e) {
    return refuse(String(e.message || e).replace(/^REFUSE_PASSKEY: /, ''));
  }

  // One-time nonce, with the identity of what it sealed. The same nonce over the same commit is
  // the same seal read again -- pre-commit, pre-push and CI all ask, and a gate that answered
  // differently the second time would block the commit it just approved. A nonce over a
  // different commit is a replay and is refused, which is the actual attack: two commits off one
  // parent share the payload, so only the recorded sha tells them apart.
  const ledger = process.env.IDP_SEAL_LEDGER || join(homedir(), '.estate/state/passkey-seal-nonces.jsonl');
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
  mkdirSync(dirname(ledger), { recursive: true });
  writeFileSync(ledger, JSON.stringify({ nonce, sha, at, payloadSha256 }) + '\n', { flag: 'a' });

  process.stdout.write(`ok passkey-seal: ${sha.slice(0, 12)} sealed by ${ring.rpId} nonce ${nonce}\n`);
  return 0;
}

const run = has('--request') ? request : async () => verify();
run().then(code => process.exit(code)).catch(e => {
  process.stderr.write('REFUSE passkey-seal: ' + (e && e.message ? e.message : String(e)) + '\n');
  process.exit(1);
});
