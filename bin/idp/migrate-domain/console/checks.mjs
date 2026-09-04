// Every field is checked against the service that owns it, not against a regex.
// A token that looks right and does not work is the failure this whole file
// exists to stop: it passes setup, and then the first cold start at 2am is the
// thing that discovers it.
//
// A check returns { ok, note }. The note is what the service said about itself
// — an account name, a bot username, a key count — never the credential.
import { createHmac, createHash } from 'node:crypto'

const CF = () => (process.env.CF_API_BASE || 'https://api.cloudflare.com') + '/client/v4'

const UA = { 'user-agent': 'survival-stack-setup' }

// `wrangler whoami` prints "You are not authenticated" and exits 0. Its exit code
// is not a login test, and treating it as one sent one setup run all the way to a
// failed KV create before anything said the word login.
export function isLoggedIn(whoamiOutput) {
  return /Account ID|associated with the email/.test(String(whoamiOutput || ''))
}

async function json(url, opts = {}) {
  const ctl = AbortSignal.timeout(15000)
  const r = await fetch(url, { ...opts, signal: ctl, headers: { ...UA, ...(opts.headers || {}) } })
  let body = null
  try { body = await r.json() } catch { /* some errors are not json */ }
  return { status: r.status, ok: r.ok, body }
}

const fail = (note) => ({ ok: false, note })
const pass = (note, extra = {}) => ({ ok: true, note, ...extra })

// ---------------------------------------------------------------- Cloudflare

export async function checkCfToken(token) {
  if (!token) return fail('nothing pasted')
  const v = await json(CF() + '/user/tokens/verify', {
    headers: { authorization: `Bearer ${token}` },
  })
  // Cloudflare answers a malformed token with 400 "Invalid request headers", which
  // reads as a bug in this tool rather than a bad paste. Say what it means.
  if (!v.body?.success) return fail('Cloudflare rejected this token')
  const z = await json(CF() + '/zones?per_page=50', {
    headers: { authorization: `Bearer ${token}` },
  })
  if (!z.body?.success) return fail('the token works but cannot read zones — add Zone:Read')
  const zones = (z.body.result || []).map((r) => ({ id: r.id, name: r.name }))
  // No zones used to be a failure. It is now a starting state: the console can
  // create the zone itself, so a fresh account with nothing in it is fine.
  if (zones.length === 0) return pass('valid, no domains on this account yet', { zones })
  return pass(`valid, ${zones.length} zone(s) in scope`, { zones })
}

// The apex A record is what failover rewrites. Asking a person to copy its id out
// of the dashboard is two clicks and a chance to paste the wrong one, so find it.
// If the domain has no A record yet, make one pointing at TEST-NET-1, which is
// reserved and routes nowhere. The first cold start overwrites it.
export async function findOrCreateApex(token, zoneId, domain) {
  const h = { authorization: `Bearer ${token}`, 'content-type': 'application/json' }
  const base = `${CF()}/zones/${zoneId}/dns_records`
  const list = await json(`${base}?type=A&name=${encodeURIComponent(domain)}`, { headers: h })
  if (!list.body?.success) return fail(list.body?.errors?.[0]?.message || 'could not read DNS records')
  const found = list.body.result?.[0]
  if (found) return pass(`apex A record found (${found.content})`, { recordId: found.id, created: false })
  const made = await json(base, {
    method: 'POST',
    headers: h,
    body: JSON.stringify({ type: 'A', name: domain, content: '192.0.2.1', proxied: true, ttl: 1 }),
  })
  if (!made.body?.success) {
    return fail(made.body?.errors?.[0]?.message || 'could not create the apex A record — add Zone:DNS:Edit')
  }
  return pass('apex A record created, parked until the first box comes up',
    { recordId: made.body.result.id, created: true })
}

// ------------------------------------------------------------------ Telegram

export async function checkTelegramBot(token) {
  if (!token) return fail('nothing pasted')
  const r = await json(`https://api.telegram.org/bot${token}/getMe`)
  if (!r.body?.ok) return fail(r.body?.description || 'Telegram rejected this token')
  return pass(`@${r.body.result.username}`, { username: r.body.result.username })
}

// Nobody should have to go and find @userinfobot. Message the bot and it tells us.
export async function findChatId(token) {
  const r = await json(`https://api.telegram.org/bot${token}/getUpdates?limit=10&timeout=0`)
  if (!r.body?.ok) return fail(r.body?.description || 'Telegram would not hand over updates')
  const msgs = (r.body.result || []).map((u) => u.message || u.edited_message).filter(Boolean)
  const last = msgs[msgs.length - 1]
  if (!last) return fail('no message yet — send your bot anything from your phone')
  const who = last.from?.first_name || last.chat?.title || 'you'
  return pass(`heard from ${who}`, { chatId: String(last.chat.id) })
}

export async function sendTelegram(token, chatId, text) {
  return json(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ chat_id: chatId, text, parse_mode: 'Markdown' }),
  })
}

export async function setWebhook(token, url, secret) {
  return json(`https://api.telegram.org/bot${token}/setWebhook`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ url, secret_token: secret, allowed_updates: ['message'] }),
  })
}

// ------------------------------------------------------------------ Providers
// Each one is asked for its SSH keys as well as its identity, because the next
// question setup would otherwise ask is "what is your SSH key called".

export async function checkHetzner(token) {
  if (!token) return fail('nothing pasted')
  const r = await json('https://api.hetzner.cloud/v1/ssh_keys', {
    headers: { authorization: `Bearer ${token}` },
  })
  if (r.status === 401) return fail('Hetzner rejected this token')
  if (!r.ok) return fail(`Hetzner said ${r.status}`)
  const keys = (r.body.ssh_keys || []).map((k) => k.name)
  return pass(keys.length ? `${keys.length} SSH key(s): ${keys.join(', ')}` : 'valid, but no SSH key uploaded yet',
    { keys })
}

export async function checkDigitalOcean(token) {
  if (!token) return fail('nothing pasted')
  const h = { authorization: `Bearer ${token}` }
  const acct = await json('https://api.digitalocean.com/v2/account', { headers: h })
  if (acct.status === 401) return fail('DigitalOcean rejected this token')
  if (!acct.ok) return fail(`DigitalOcean said ${acct.status}`)
  const k = await json('https://api.digitalocean.com/v2/account/keys', { headers: h })
  const keys = (k.body?.ssh_keys || []).map((x) => x.name)
  return pass(`${acct.body.account.email_verified ? 'verified' : 'unverified'} account, ${keys.length} SSH key(s)`,
    { keys })
}

export async function checkVultr(token) {
  if (!token) return fail('nothing pasted')
  const h = { authorization: `Bearer ${token}` }
  const acct = await json('https://api.vultr.com/v2/account', { headers: h })
  if (acct.status === 401) return fail('Vultr rejected this key')
  if (!acct.ok) return fail(`Vultr said ${acct.status}`)
  const k = await json('https://api.vultr.com/v2/ssh-keys', { headers: h })
  const keys = (k.body?.ssh_keys || []).map((x) => x.name)
  return pass(`balance ${acct.body.account?.balance ?? '?'}, ${keys.length} SSH key(s)`, { keys })
}

// -------------------------------------------------------------------- Stripe

export async function checkStripe(key) {
  if (!key) return fail('nothing pasted')
  const r = await json('https://api.stripe.com/v1/balance', {
    headers: { authorization: `Bearer ${key}` },
  })
  if (r.status === 401) return fail('Stripe rejected this key')
  if (!r.ok) return fail(r.body?.error?.message || `Stripe said ${r.status}`)
  return pass(r.body.livemode ? 'live key, working' : 'TEST key — real orders will not charge')
}

// ------------------------------------------------------------------------ R2
// The one credential where a typo is silent. It is only used by litestream on a
// box you cannot see, so a wrong key means backups that never happened and a
// restore that finds nothing. Signed and sent, so it is checked here or never.

function sigv4Headers({ method, host, path, accessKey, secretKey, region = 'auto', service = 's3', payload = '' }) {
  const amzDate = new Date().toISOString().replace(/[:-]|\.\d{3}/g, '')
  const dateStamp = amzDate.slice(0, 8)
  const hash = (s) => createHash('sha256').update(s).digest('hex')
  const hmac = (k, s) => createHmac('sha256', k).update(s).digest()
  const payloadHash = hash(payload)
  const canonicalHeaders = `host:${host}\nx-amz-content-sha256:${payloadHash}\nx-amz-date:${amzDate}\n`
  const signedHeaders = 'host;x-amz-content-sha256;x-amz-date'
  const canonical = [method, path, '', canonicalHeaders, signedHeaders, payloadHash].join('\n')
  const scope = `${dateStamp}/${region}/${service}/aws4_request`
  const toSign = ['AWS4-HMAC-SHA256', amzDate, scope, hash(canonical)].join('\n')
  let k = hmac(`AWS4${secretKey}`, dateStamp)
  for (const part of [region, service, 'aws4_request']) k = hmac(k, part)
  const signature = createHmac('sha256', k).update(toSign).digest('hex')
  return {
    authorization: `AWS4-HMAC-SHA256 Credential=${accessKey}/${scope}, SignedHeaders=${signedHeaders}, Signature=${signature}`,
    'x-amz-content-sha256': payloadHash,
    'x-amz-date': amzDate,
  }
}

export async function checkR2(accountId, accessKey, secretKey) {
  if (!accessKey || !secretKey) return fail('both halves are needed')
  if (!accountId) return fail('log in to Cloudflare first — the endpoint is built from your account id')
  const host = `${accountId}.r2.cloudflarestorage.com`
  const headers = sigv4Headers({ method: 'GET', host, path: '/', accessKey, secretKey })
  let r
  try {
    r = await fetch(`https://${host}/`, { headers: { ...headers, ...UA }, signal: AbortSignal.timeout(15000) })
  } catch (e) {
    return fail(`could not reach R2: ${e.message}`)
  }
  if (r.status === 403) return fail('R2 rejected this key pair')
  if (!r.ok) return fail(`R2 said ${r.status}`)
  const xml = await r.text()
  const buckets = [...xml.matchAll(/<Name>([^<]+)<\/Name>/g)].map((m) => m[1])
  return pass(buckets.length ? `signed in, sees ${buckets.length} bucket(s)` : 'signed in, no buckets yet',
    { buckets })
}

export { sigv4Headers }
