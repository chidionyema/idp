// Every field is checked against the service that owns it, not against a regex.
// A token that looks right and does not work is the failure this whole file
// exists to stop: it passes setup, and then the first cold start at 2am is the
// thing that discovers it.
//
// A check returns { ok, note }. The note is what the service said about itself
// — an account name, a zone count — never the credential.
//
// Cloudflare only. The file this was adopted from also checked Telegram, Hetzner,
// DigitalOcean, Vultr, Stripe and R2, and signed its own SigV4 requests to do the
// last one. None of that is this tool's job and none of it was reachable from
// migrate-domain.mjs, which imports checkCfToken and nothing else; the estate has
// one place each for alerting and for object storage. Dropped on adoption
// (crew#838 CP1) rather than carried in as a second copy of six other tools.

const CF = () => (process.env.CF_API_BASE || 'https://api.cloudflare.com') + '/client/v4'

const UA = { 'user-agent': 'idp-migrate-domain' }

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
