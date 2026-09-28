// Getting a Cloudflare credential without anyone typing one.
//
// Adopted with the tool from survival-stack (crew#838 CP1). Every test here
// graded code that survived the move to the estate's vault; the ones that graded
// the clipboard watcher, the macOS keychain, the dashboard token page and its two
// copy buttons went with the code they graded, because the estate never asks a
// person to mint and paste a credential (LAW 31, R52) and the vault is where the
// root token lives now. What is left is the part that still runs in anger: what
// counts as a credential, where one is found, and how a short-lived one is minted
// and revoked.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import * as auth from '../lib/cf-auth.mjs'

test('incident: a real token was ignored because it was not 40 characters', async () => {
  // The check was /^[A-Za-z0-9_-]{40}$/. Cloudflare started issuing a
  // `cfut_`-prefixed 53-character token, the code saw a live, active credential,
  // decided it was the wrong shape, and said nothing.
  //
  // The rule that came out of it: never assume a vendor's format is static.
  // The API is the validator. This asserts both halves — the new shape passes,
  // and no length equality is left anywhere in the source.
  assert.equal(auth.looksLikeToken('cfut_' + 'x'.repeat(48)), true, 'the cfut_ form is refused again')
  assert.equal(auth.looksLikeToken('a'.repeat(40)), true, 'the old form stopped working')
  assert.equal(auth.looksLikeToken('a'.repeat(39)), true, 'a length is being enforced again')
  assert.equal(auth.looksLikeToken('a'.repeat(41)), true, 'a length is being enforced again')
  assert.equal(auth.looksLikeToken('q'.repeat(200)), true, 'an upper bound came back')

  const src = (await readFile(new URL('../lib/cf-auth.mjs', import.meta.url), 'utf8'))
    .split('\n').filter((l) => !l.trim().startsWith('//')).join('\n')
  assert.equal(/length\s*[!=]==?\s*\d/.test(src), false, 'a length equality is back in the validator')
  assert.equal(/\{40\}/.test(src), false, 'the 40-character regex is back')
})

test('a candidate that is turned away says which thing went wrong', () => {
  // Silence was the defect. Every rejection carries the sentence that says
  // whether to fix the value or fix the token.
  for (const junk of ['', ' ', 'hunter2', 'a'.repeat(19)]) {
    const c = auth.tokenCandidate(junk)
    assert.equal(c.ok, false, `${JSON.stringify(junk)} was taken for a token`)
    assert.ok(c.why && c.why.length > 5, 'rejected with no reason given')
  }
  assert.match(auth.tokenCandidate('hunter2').why, /too short/)
  assert.match(auth.tokenCandidate('correct horse battery staple and more').why, /spaces|newlines/)
  assert.match(auth.tokenCandidate('https://example.com/quite/long/indeed/x').why, /URL/)
})

test("another vendor's key is never sent to Cloudflare to be checked", () => {
  // Checking a candidate means handing it to Cloudflare as a bearer token.
  // Several vendors issue keys of exactly this shape, so a stray value would
  // otherwise leak one secret to an unrelated company. These stop at the door.
  for (const prefix of ['sk-', 'sk_', 'pk_', 'ghp_', 'xoxb-', 'AKIA', 'AIza', 'hf_', 'glpat-', 'dop_v1_', 'SG.', 'npm_']) {
    const c = auth.tokenCandidate(prefix + 'x'.repeat(40))
    assert.equal(c.ok, false, `a ${prefix}… key would have been sent to Cloudflare`)
    assert.match(c.why, /another vendor/, 'refused, but not for the reason that matters')
  }
})

test('a multi-line value is not a token', () => {
  assert.equal(auth.looksLikeToken('a'.repeat(20) + '\n' + 'a'.repeat(19)), false)
})

test('an environment variable beats the vault', async () => {
  // The vault is where the root credential lives, and a run that is deliberately
  // pointed somewhere else — a test account, a second tenancy — must not have the
  // vault quietly win.
  const had = process.env.CF_API_TOKEN
  process.env.CF_API_TOKEN = 'e'.repeat(40)
  try {
    const r = await auth.findToken()
    assert.equal(r.token, 'e'.repeat(40))
    assert.equal(r.from, 'CF_API_TOKEN')
  } finally {
    if (had === undefined) delete process.env.CF_API_TOKEN
    else process.env.CF_API_TOKEN = had
  }
})

// --------------------------------------------------------- minting a token

// POST /user/tokens takes bearer auth, so a credential holding User → API Tokens
// → Write can mint others. That is what makes the credential actually in flight
// during a run one that expires in an hour and is deleted at the end, rather than
// the root token itself (R52).
const withFetch = async (handler, fn) => {
  const real = globalThis.fetch
  globalThis.fetch = handler
  try { return await fn() } finally { globalThis.fetch = real }
}
const reply = (body, ok = true) => new Response(JSON.stringify({ success: ok, result: body }), {
  status: ok ? 200 : 403, headers: { 'content-type': 'application/json' },
})

const GROUPS = [
  { id: 'grp-zone-write', name: 'Zone Write', scopes: ['com.cloudflare.api.account'] },
  { id: 'grp-dns-write', name: 'DNS Write', scopes: ['com.cloudflare.api.account.zone'] },
  { id: 'grp-zone-read', name: 'Zone Read', scopes: ['com.cloudflare.api.account'] },
]

test('the minted token is scoped, time-boxed, and asks for the two groups it needs', async () => {
  let sent = null
  const got = await withFetch(async (url, opts) => {
    if (String(url).includes('permission_groups')) return reply(GROUPS)
    if (String(url).endsWith('/user/tokens') && opts.method === 'POST') {
      sent = JSON.parse(opts.body)
      return reply({ id: 'tok-1', value: 'v'.repeat(40) })
    }
    throw new Error('unexpected call: ' + url)
  }, () => auth.mintEphemeral('r'.repeat(40), 'acct-123', { hours: 1 }))

  assert.equal(got.id, 'tok-1')
  assert.equal(got.token, 'v'.repeat(40))
  assert.deepEqual(sent.policies[0].permission_groups, [{ id: 'grp-zone-write' }, { id: 'grp-dns-write' }])
  assert.deepEqual(Object.keys(sent.policies[0].resources), ['com.cloudflare.api.account.acct-123'])

  // A token minted without an expiry is just a second permanent credential with
  // extra steps.
  assert.ok(sent.expires_on, 'no expiry was set')
  const secondsOut = (Date.parse(sent.expires_on) - Date.now()) / 1000
  assert.ok(secondsOut > 3000 && secondsOut < 3900, `expiry was ${secondsOut}s out`)
})

test('a credential that cannot mint returns null rather than failing the run', async () => {
  // The normal case. Most tokens do not carry API Tokens Write, and the run must
  // carry on with what it has instead of stopping.
  const denied = await withFetch(async () => reply(null, false),
    () => auth.mintEphemeral('r'.repeat(40), 'acct-123'))
  assert.equal(denied, null)

  // Present but missing a group it needs — also null, not a half-scoped token.
  const partial = await withFetch(async (url) => {
    if (String(url).includes('permission_groups')) return reply([GROUPS[2]])
    throw new Error('should not have tried to mint')
  }, () => auth.mintEphemeral('r'.repeat(40), 'acct-123'))
  assert.equal(partial, null)
})

test('revoking uses the root credential, not the token being deleted', async () => {
  let sawAuth = null
  let sawUrl = null
  const ok = await withFetch(async (url, opts) => {
    sawUrl = String(url)
    sawAuth = opts.headers.authorization
    return reply({ id: 'tok-1' })
  }, () => auth.revokeToken('r'.repeat(40), 'tok-1'))

  assert.equal(ok, true)
  assert.equal(sawUrl, 'https://api.cloudflare.com/client/v4/user/tokens/tok-1')
  assert.equal(sawAuth, 'Bearer ' + 'r'.repeat(40), 'the ephemeral token cannot delete itself')
})

test('no credential is ever asked for by hand', async () => {
  // The estate does not put a person in front of a vendor console to mint and
  // paste a secret (LAW 31, R52, founder 2026-08-28 and 2026-09-04). The adopted
  // tool did exactly that, so this pins the removal rather than trusting it.
  for (const f of ['lib/cf-auth.mjs', 'migrate-domain.mjs', 'console/checks.mjs']) {
    // Comments stripped, or this matches the paragraphs above that say the flow
    // was removed and name what it used to do.
    const src = (await readFile(new URL('../' + f, import.meta.url), 'utf8'))
      .split('\n').filter((l) => !l.trim().startsWith('//')).join('\n')
    assert.equal(/pbpaste|pbcopy|clipboard/i.test(src), false, `${f} reads the clipboard again`)
    assert.equal(/security\s+(add|find)-generic-password|keychain/i.test(src), false, `${f} uses the macOS keychain again`)
    assert.equal(/api\.telegram\.org/.test(src), false, `${f} talks to Telegram again`)
  }
})
