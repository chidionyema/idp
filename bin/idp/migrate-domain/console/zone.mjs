// Moving a domain to Cloudflare, without a dashboard.
//
// The manual version is: log in, add a site, wait for a scan, check every
// record it guessed, add the ones it missed, then compare by eye. The eye is
// the part that fails, and mail records are what it fails on — an SPF or DKIM
// record that did not come across breaks nothing visible and quietly costs you
// deliverability for a week.
//
// So this reads the zone from the nameservers actually answering for it, writes
// every record into Cloudflare through the API, and then asks both sides the
// same questions and refuses to say ready unless the answers match.
import { Resolver, promises as dnsp } from 'node:dns'
import { execFile } from 'node:child_process'

// CF_API_BASE points the whole tool at the mock server in test/helpers, which
// is how the failure matrix exercises the real HTTP path - headers, JSON,
// status codes - instead of a stubbed fetch that agrees with itself.
// Read per call, not at import. A test points this at the mock server after
// the module graph is already loaded, and a constant captured at import time
// would send every one of those calls to the live API instead.
const CF = () => (process.env.CF_API_BASE || 'https://api.cloudflare.com') + '/client/v4'

// Everything a small business is likely to have, plus every DKIM selector the
// common mail providers use. A name nobody ever asks about costs one UDP packet.
const NAMES = ['@', 'www', 'mail', 'smtp', 'imap', 'pop', 'webmail', 'autodiscover',
  'autoconfig', 'ftp', 'blog', 'shop', 'app', 'api', 'dev', 'staging', 'm', 'cdn',
  'static', 'assets', 'calendar', 'docs', 'drive', 'sites', 'status', 'support',
  'help', 'admin', 'portal', 'vpn', 'git', 'ns1', 'ns2',
  '_dmarc', 'google._domainkey', 'mailjet._domainkey', 'default._domainkey',
  'selector1._domainkey', 'selector2._domainkey', 'k1._domainkey', 'k2._domainkey',
  's1._domainkey', 's2._domainkey', 'mandrill._domainkey', 'sendgrid._domainkey',
  'em._domainkey', 'dkim._domainkey', 'smtp._domainkey', 'pm._domainkey',
  'zoho._domainkey', 'mail._domainkey', 'fm1._domainkey', 'fm2._domainkey', 'fm3._domainkey']

const TYPES = ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'CAA', 'SRV', 'NS']

async function cf(token, path, opts = {}) {
  const r = await fetch(CF() + path, {
    ...opts,
    signal: AbortSignal.timeout(25000),
    headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json', ...(opts.headers || {}) },
  })
  const body = await r.json().catch(() => ({}))
  return { status: r.status, ok: r.ok && body.success !== false, body }
}

const firstError = (b) => b?.errors?.[0]?.message || b?.messages?.[0]?.message || 'Cloudflare said no'

// -------------------------------------------------------------- reading a zone

// Ask the servers that hold the zone, not a resolver. A resolver hands back
// whatever it has cached, which during a migration is exactly the wrong answer.
export async function authoritativeServers(domain) {
  const names = await dnsp.resolveNs(domain)
  const ips = []
  for (const n of names) {
    for (const ip of await dnsp.resolve4(n).catch(() => [])) ips.push(ip)
  }
  if (!ips.length) throw new Error(`no reachable nameserver for ${domain}`)
  return { names: names.sort(), ips }
}

function resolverOn(ips) {
  const r = new Resolver({ timeout: 3000, tries: 2 })
  r.setServers(ips)
  return r
}

const ask = (res, name, type) => new Promise((resolve) => {
  res.resolve(name, type, (err, out) => resolve(err ? [] : out))
})

// One flat list of strings, so two zones can be compared by set difference.
export async function readZone(domain, ips, { names = NAMES } = {}) {
  const res = resolverOn(ips)
  const out = []
  const jobs = []
  for (const n of names) {
    const fqdn = n === '@' ? domain : `${n}.${domain}`
    for (const type of TYPES) {
      jobs.push(ask(res, fqdn, type).then((rows) => {
        for (const row of rows) out.push({ name: fqdn, type, ...normalise(type, row) })
      }))
    }
  }
  await Promise.all(jobs)
  return out.sort((a, b) => key(a).localeCompare(key(b)))
}

function normalise(type, row) {
  if (type === 'MX') return { content: row.exchange.replace(/\.$/, ''), priority: row.priority }
  if (type === 'TXT') return { content: (Array.isArray(row) ? row.join('') : row) }
  if (type === 'SRV') return { content: `${row.weight} ${row.port} ${row.name}`, priority: row.priority }
  if (type === 'CAA') return { content: `${row.critical} ${row.issue ? 'issue' : 'iodef'} "${row.issue || row.iodef}"` }
  return { content: String(row).replace(/\.$/, '') }
}

export const key = (r) => `${r.name} ${r.type} ${r.priority ?? ''} ${r.content}`.trim()

// ------------------------------------------------------------- writing a zone

export async function accountId(token) {
  const r = await cf(token, '/accounts?per_page=5')
  if (!r.ok) return null
  return r.body.result?.[0]?.id || null
}

export async function findZone(token, domain) {
  const r = await cf(token, `/zones?name=${encodeURIComponent(domain)}`)
  if (!r.ok) return null
  return r.body.result?.[0] || null
}

// jump_start is left on deliberately. Cloudflare's scanner looks for records the
// same way this file does and gets different answers, because neither can list a
// zone it cannot transfer — both are guessing names. Two guessers that agree is
// the closest thing to a listing available without the registrar's own API, and
// where they disagree is the only part worth a human's attention.
// `account` is optional, and a null one is the normal case rather than an
// error. A token scoped to zones and not to the account reads GET /accounts as
// 200 with an empty list - not a 403 - so there is no account id to send, and
// the old code stopped there saying the token needed Account:Read. It does not.
// POST /zones with no account attaches the zone to the only account the
// credential belongs to. Measured: 200, zone created, nameservers returned.
export async function createZone(token, account, domain, jumpStart = true) {
  const body = { name: domain, type: 'full', jump_start: jumpStart }
  if (account) body.account = { id: account }
  const r = await cf(token, '/zones', { method: 'POST', body: JSON.stringify(body) })
  if (!r.ok) throw new Error(firstError(r.body))
  return r.body.result
}

// Whether this credential can actually touch DNS on this zone, asked of the
// API rather than inferred from the token being "valid".
//
// The incident: a token with Zone:Edit and no DNS permission created the zone,
// reported "valid, 1 zone in scope", and then refused all eight record writes
// with eight identical lines reading "Authentication error". Nothing in that
// output named the missing permission. One call up front does.
export async function dnsReachable(token, zoneId) {
  const r = await cf(token, `/zones/${zoneId}/dns_records?per_page=1`)
  return r.ok
}

// Everything goes in grey-clouded. Today nothing is proxied, so proxying on the
// way in would change how traffic reaches the origin and how TLS terminates, on
// the same day as the move, with two changes to untangle if anything breaks.
export async function writeRecords(token, zoneId, records, onEach = () => {}) {
  const existing = await allRecords(token, zoneId)
  const have = new Set(existing.map((r) => key(fromCf(r))))
  // addedIds is what makes a failed prepare undoable: the ids of the records
  // this run put there, and nothing else. Without it a rollback would have to
  // guess which records were already somebody's configuration.
  const results = { added: 0, already: 0, skipped: [], failed: [], addedIds: [] }

  for (const rec of records) {
    if (rec.type === 'NS' && rec.name === records.domain) continue
    if (have.has(key(rec))) { results.already++; onEach({ ...rec, state: 'already there' }); continue }
    const body = {
      type: rec.type,
      name: rec.name,
      content: rec.content,
      ttl: 300,
      proxied: false,
      ...(rec.priority !== undefined ? { priority: rec.priority } : {}),
    }
    const r = await cf(token, `/zones/${zoneId}/dns_records`, { method: 'POST', body: JSON.stringify(body) })
    if (r.ok) { results.added++; results.addedIds.push(r.body.result.id); onEach({ ...rec, state: 'added' }) }
    else { results.failed.push({ ...rec, why: firstError(r.body) }); onEach({ ...rec, state: `refused: ${firstError(r.body)}` }) }
  }
  return results
}

// Undo one record this run wrote. The rollback path only ever passes ids from
// writeRecords' own addedIds, so it can never remove a record that was already
// there before the run started.
export async function deleteRecord(token, zoneId, recordId) {
  const r = await cf(token, `/zones/${zoneId}/dns_records/${recordId}`, { method: 'DELETE' })
  return r.ok
}

export async function allRecords(token, zoneId) {
  const out = []
  for (let page = 1; page <= 10; page++) {
    const r = await cf(token, `/zones/${zoneId}/dns_records?per_page=100&page=${page}`)
    if (!r.ok) break
    out.push(...r.body.result)
    if (r.body.result.length < 100) break
  }
  return out
}

const fromCf = (r) => ({
  name: r.name, type: r.type, content: String(r.content).replace(/\.$/, ''),
  ...(r.priority !== undefined && r.priority !== null ? { priority: r.priority } : {}),
})

// ------------------------------------------------------------------- the check

// The guard. Two nameserver sets, the same questions, and a refusal unless the
// answers match. NS records are excluded because they differ by definition
// while a migration is in progress.
export async function compare(domain, oldIps, newIps) {
  const [before, after] = await Promise.all([readZone(domain, oldIps), readZone(domain, newIps)])
  const real = (rs) => rs.filter((r) => !(r.type === 'NS' && r.name === domain))
  const a = new Set(real(before).map(key))
  const b = new Set(real(after).map(key))
  return {
    total: a.size,
    missing: [...a].filter((k) => !b.has(k)).sort(),
    extra: [...b].filter((k) => !a.has(k)).sort(),
    ready: [...a].every((k) => b.has(k)),
  }
}

// Can this credential list zones at all - as distinct from listing them and
// finding none. findZone and listZones both flatten a 403 into an empty
// answer, which reads as "no such zone" and sends you to create one. This is
// the only call that tells the two apart, so it runs first.
export async function zoneReadable(token) {
  const r = await cf(token, '/zones?per_page=1')
  return r.ok
}

export async function listZones(token, limit = 5) {
  const r = await cf(token, `/zones?per_page=${limit}`)
  return r.ok ? r.body.result || [] : []
}

// Undo a zone this run created. Only ever called on a zone this run created:
// a pre-existing zone belongs to somebody else's decision, and deleting one on
// a permission failure would turn a bad first run into a lost configuration.
export async function deleteZone(token, zoneId) {
  const r = await cf(token, `/zones/${zoneId}`, { method: 'DELETE' })
  return r.ok
}

// Get a zone to work in, or fail having changed nothing.
//
// The incident: a token with Zone:Edit and no DNS permission created the zone,
// then failed on record 1 of 8 with "Authentication error". The founder was
// left holding a half-created zone and a message naming no permission.
// Founder: "This is not nice debugging."
//
// The rule that came out of it: the probe runs before the mutation, and a
// failed run leaves zero side effects. Whether a credential can write DNS is a
// question about a zone, so there has to be a zone to ask about, and there are
// three cases:
//
//   the zone exists      ask there, change nothing on failure
//   another zone exists  ask there, change nothing on failure
//   nothing exists       create this one, ask, delete it again on failure
//
// Returns { zone } or { error: 'no-dns', rolledBack }. It never returns a zone
// it has not proved it can write DNS in.
export async function ensureZone(token, domain, { log = () => {} } = {}) {
  const existing = await findZone(token, domain)
  if (existing) {
    log('exists', existing)
    if (!(await dnsReachable(token, existing.id))) return { error: 'no-dns', rolledBack: false }
    return { zone: existing }
  }

  // Any zone answers "can this token touch DNS at all", and using one that is
  // already there means a bad credential costs nothing.
  const [other] = await listZones(token, 1)
  if (other && !(await dnsReachable(token, other.id))) return { error: 'no-dns', rolledBack: false }

  const account = await accountId(token)
  const zone = await createZone(token, account, domain)
  log('created', zone)

  // Nothing was in scope to ask first, so the new zone is the question, and it
  // is withdrawn if the answer is no. Only ever this one: a zone somebody else
  // created is their decision, and deleting it over a permission would turn a
  // bad first run into a lost configuration.
  if (!other && !(await dnsReachable(token, zone.id))) {
    return { error: 'no-dns', rolledBack: await deleteZone(token, zone.id) }
  }
  return { zone, fresh: true }
}

// Whether the registry will accept a nameserver change at all.
//
// The incident: the founder was given the two Cloudflare nameservers, pasted
// them into 123-reg, and got "Invalid nameservers". Nothing was wrong with the
// nameservers - both resolve, both already answer authoritatively for the
// zone. The domain carried clientUpdateProhibited, which is the registrar lock,
// and it blocks updates to the domain object including its nameserver set. The
// form reports that as a problem with what was typed.
//
// One whois call before the registrar step turns a mystifying rejection into a
// sentence naming the toggle to turn off. It degrades quietly: no whois binary,
// or a registry that does not answer, means no claim either way.
export async function registrarLock(domain) {
  const out = await new Promise((resolve) => {
    execFile('whois', [domain], { timeout: 15000 }, (err, stdout) => resolve(err && !stdout ? null : String(stdout || '')))
  })
  if (out === null) return { known: false, locked: false, statuses: [] }
  const statuses = [...new Set(
    [...out.matchAll(/^\s*Domain Status:\s*(client\w+)/gim)].map((m) => m[1]),
  )]
  return { known: true, locked: statuses.includes('clientUpdateProhibited'), statuses }
}

export async function nameserversNowServing(domain) {
  return (await dnsp.resolveNs(domain).catch(() => [])).map((n) => n.toLowerCase()).sort()
}

export { NAMES }
