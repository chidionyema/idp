// The migration as six named phases, each one runnable on its own.
//
// It was one long script. That was fine to write and impossible to test: the
// only way to exercise "what happens when record 4 is refused" was to have
// record 4 refused on a live domain. Phases give every failure mode an entry
// point, and the state file gives a failed run something to undo.
//
// The gates are the point. Each phase refuses to start unless the one before
// it finished, and the state file - not an agent's memory, not a chat message
// - is what says whether it did.
import { mkdir, readFile, writeFile, rm } from 'node:fs/promises'
import { join } from 'node:path'
import { promises as dnsp } from 'node:dns'
import * as z from './zone.mjs'

export const PHASES = ['discover', 'validate', 'prepare', 'verify', 'cutover', 'lockdown']

// Five minutes. A verify older than that describes a zone that may have been
// edited since, and cutover is the one step that cannot be undone quickly.
export const VERIFY_TTL_MS = 5 * 60 * 1000

const STATE_DIR = process.env.MIGRATION_STATE_DIR || '.migration'

export function statePath(domain, dir = STATE_DIR) {
  return join(dir, `${domain}.json`)
}

export async function loadState(domain, dir = STATE_DIR) {
  try { return JSON.parse(await readFile(statePath(domain, dir), 'utf8')) } catch { return null }
}

export async function saveState(domain, patch, dir = STATE_DIR) {
  const now = { ...(await loadState(domain, dir)), domain, ...patch }
  await mkdir(dir, { recursive: true })
  await writeFile(statePath(domain, dir), JSON.stringify(now, null, 2) + '\n')
  return now
}

export async function clearState(domain, dir = STATE_DIR) {
  await rm(statePath(domain, dir), { force: true })
}

// A phase returns this shape and never throws for an expected failure. `stop`
// is a sentence a person can act on; `need` names the permission when that is
// what is missing, because "403 Forbidden" sends people to the wrong page.
const done = (extra = {}) => ({ ok: true, ...extra })
const stop = (why, extra = {}) => ({ ok: false, stop: why, ...extra })

// ------------------------------------------------------------- 1. DISCOVER

// Reads the zone off the nameservers actually answering for it. Touches
// nothing, needs no credential, and is the baseline every later phase is
// compared against.
export async function discover(domain, { dir = STATE_DIR, dns = z } = {}) {
  const ns = await dns.authoritativeServers(domain).catch((e) => ({ error: e.message }))
  if (ns.error) return stop(`cannot read ${domain} from its nameservers: ${ns.error}`)

  const all = await dns.readZone(domain, ns.ips)
  const records = all.filter((r) => !(r.type === 'NS' && r.name === domain))
  if (!records.length) return stop(`no records found for ${domain} - check the spelling`)

  const lock = await dns.registrarLock(domain)
  const state = await saveState(domain, {
    discoveredAt: new Date().toISOString(),
    oldNameServers: ns.names,
    oldIps: ns.ips,
    records,
    registrar: lock,
    hasMx: records.some((r) => r.type === 'MX'),
  }, dir)
  return done({ records, nameServers: ns.names, registrar: lock, state })
}

// ------------------------------------------------------------- 2. VALIDATE

// Prove the credential can do every part of the job before any of it happens.
//
// Whether a token can write DNS is a question about a zone, so there has to be
// a zone to ask about. Three cases, and only the third one changes anything:
//
//   this zone exists     ask there, change nothing on failure
//   another zone exists  ask there, change nothing on failure
//   nothing exists       create this one, ask, delete it again on failure
export async function validate(domain, token, { dir = STATE_DIR } = {}) {
  const state = await loadState(domain, dir)
  if (!state?.records) return stop('run discover first - there is nothing to validate against')

  // Zone read comes first because every other check is phrased in terms of a
  // zone, and a token that cannot list zones fails all of them for one reason.
  // It is also the only check that runs before anything could be created, so
  // getting it wrong is the difference between a clear sentence and a zone
  // created by a credential that could never have finished the job.
  if (!(await z.zoneReadable(token))) {
    return stop('this credential cannot list zones', { need: 'Zone → Zone → Read' })
  }

  const got = await z.ensureZone(token, domain, {})
    .catch((e) => ({ error: 'create-refused', message: e.message }))

  if (got.error === 'create-refused') {
    return stop('this credential cannot create a zone', { need: 'Zone → Zone → Edit', detail: got.message })
  }
  if (got.error === 'no-dns') {
    return stop('this credential cannot write DNS records', {
      need: 'Zone → DNS → Edit',
      rolledBack: got.rolledBack,
    })
  }

  const next = await saveState(domain, {
    validatedAt: new Date().toISOString(),
    zoneId: got.zone.id,
    zoneStatus: got.zone.status,
    newNameServers: (got.zone.name_servers || []).map((s) => s.toLowerCase()).sort(),
    // The single most important field in the file. Rollback reads it to decide
    // whether deleting the zone is undoing our own work or destroying someone
    // else's.
    zoneCreatedByUs: Boolean(got.fresh),
  }, dir)
  return done({ zone: got.zone, fresh: Boolean(got.fresh), state: next })
}

// ------------------------------------------------------------- 3. PREPARE

// Write every discovered record into the zone. Live traffic is still on the
// old nameservers throughout, so this phase is invisible from outside.
//
// A partial write is the failure this phase is shaped around. Four records in
// and a refusal on the fifth used to leave four records and a zone behind, and
// the next run then could not tell them from configuration somebody meant.
// Now the run undoes exactly what it wrote, and nothing else.
export async function prepare(domain, token, { dir = STATE_DIR, onEach = () => {} } = {}) {
  const state = await loadState(domain, dir)
  if (!state?.zoneId) return stop('run validate first - there is no zone to write into')
  if (!state.records?.length) return stop('run discover first - there is nothing to write')

  const res = await z.writeRecords(token, state.zoneId, state.records, onEach)
  await saveState(domain, { addedRecordIds: res.addedIds }, dir)

  if (res.failed.length) {
    const undone = await undo(domain, token, { dir })
    return stop(`${res.failed.length} of ${state.records.length} records were refused`, {
      failed: res.failed,
      rolledBack: undone,
    })
  }

  const next = await saveState(domain, { preparedAt: new Date().toISOString(), written: res.added }, dir)
  return done({ added: res.added, already: res.already, state: next })
}

// -------------------------------------------------------------- 4. VERIFY

// Ask both nameserver sets the same questions and refuse to say ready unless
// the answers match. This is the gate that stands between a half-written zone
// and a shop that stops answering.
// A record written a second ago is not yet a record the edge answers with.
// Measured on mumchimp.com: prepare wrote all 8, verify ran immediately after
// and reported all 8 missing; the same command 40 seconds later said Identical.
// A gate that cries wolf on its own writes teaches people to re-run it until it
// agrees, which is the one habit this gate exists to prevent. So it waits.
export async function verify(domain, {
  dir = STATE_DIR, dns = z, resolve4 = dnsp.resolve4,
  attempts = 6, waitMs = 8000, sleep = (ms) => new Promise((r) => setTimeout(r, ms)),
  onWait = () => {},
} = {}) {
  const state = await loadState(domain, dir)
  if (!state?.preparedAt) return stop('run prepare first - the zone has not been written yet')

  const newIps = []
  for (const n of state.newNameServers || []) {
    for (const ip of await resolve4(n).catch(() => [])) newIps.push(ip)
  }
  if (!newIps.length) return stop('the new nameservers do not resolve yet - wait and run verify again')

  let d = await dns.compare(domain, state.oldIps, newIps)
  for (let i = 1; i < attempts && !d.ready; i++) {
    onWait(d.missing.length, i, attempts)
    await sleep(waitMs)
    d = await dns.compare(domain, state.oldIps, newIps)
  }
  if (!d.ready) {
    await saveState(domain, { verifiedAt: null }, dir)
    return stop(`${d.missing.length} records are missing on the new side`, { diff: d })
  }
  const next = await saveState(domain, { verifiedAt: new Date().toISOString(), newIps, diff: d }, dir)
  return done({ diff: d, state: next })
}

// ------------------------------------------------------------- 5. CUTOVER

// The registrar step, and the one this tool does not perform.
//
// 123-reg has no public API for a retail account, so the nameserver change is
// two strings pasted into one form by a person. What the tool can do is refuse
// to print those strings until it is safe, which is the part that goes wrong.
export async function cutover(domain, { dir = STATE_DIR, dns = z, now = Date.now() } = {}) {
  const state = await loadState(domain, dir)
  if (!state?.verifiedAt) return stop('verify has not passed - the new nameservers do not answer identically yet')

  const age = now - Date.parse(state.verifiedAt)
  if (age > VERIFY_TTL_MS) {
    return stop(`the last verify was ${Math.round(age / 60000)} minutes ago - run verify again before switching`)
  }

  const lock = await dns.registrarLock(domain)
  if (lock.locked) {
    return stop('the domain is locked at the registrar, so the form will reject the change', {
      need: 'turn Domain Lock off at 123-reg, then run this again',
      statuses: lock.statuses,
    })
  }

  return done({
    from: state.oldNameServers,
    to: state.newNameServers,
    manual: true,
    where: `https://www.123-reg.co.uk/secure/cpanel/domain/${domain}/manage-nameservers`,
    rollback: `put ${(state.oldNameServers || []).join(' and ')} back`,
  })
}

// ------------------------------------------------------------ 6. LOCKDOWN

// Did the change actually land everywhere, and is the door shut again.
const RESOLVERS = { '1.1.1.1': '1.1.1.1', '8.8.8.8': '8.8.8.8', '9.9.9.9': '9.9.9.9' }

export async function lockdown(domain, { dir = STATE_DIR, dns = z, resolvers = RESOLVERS, ask = askNs } = {}) {
  const state = await loadState(domain, dir)
  if (!state?.newNameServers?.length) return stop('there is no target nameserver set to check against')

  const want = state.newNameServers.join(',')
  const seen = {}
  for (const [label, ip] of Object.entries(resolvers)) {
    seen[label] = (await ask(domain, ip)).join(',')
  }
  const behind = Object.entries(seen).filter(([, got]) => got !== want).map(([l]) => l)

  const lock = await dns.registrarLock(domain)
  if (behind.length) {
    return stop(`${behind.join(', ')} still answer with the old nameservers`, { seen, want, lock })
  }
  if (!lock.locked) {
    return stop('propagated, but the registrar lock is still off', {
      need: 'turn Domain Lock back on at 123-reg',
      seen, want,
    })
  }
  const next = await saveState(domain, { lockedDownAt: new Date().toISOString() }, dir)
  return done({ seen, want, lock, state: next })
}

async function askNs(domain, serverIp) {
  const { Resolver } = await import('node:dns')
  const r = new Resolver({ timeout: 3000, tries: 2 })
  r.setServers([serverIp])
  return new Promise((res) => r.resolveNs(domain, (e, out) => res(e ? [] : out.map((s) => s.toLowerCase()).sort())))
}

// ------------------------------------------------------------- rollback

// Undo exactly what this run did, and refuse anything else.
//
// The refusal is the important half. A zone that was already there when the
// run started belongs to a decision somebody made, and deleting it because a
// permission was wrong turns a bad first run into a lost configuration.
export async function undo(domain, token, { dir = STATE_DIR, log = () => {} } = {}) {
  const state = await loadState(domain, dir)
  if (!state) return { ok: false, stop: 'nothing recorded for this domain - there is nothing to undo' }

  const removed = []
  for (const rid of state.addedRecordIds || []) {
    if (await z.deleteRecord(token, state.zoneId, rid)) removed.push(rid)
  }
  log('records', removed.length)

  // Deleting the zone is the irreversible half, so it gets a second question
  // that does not depend on the state file being right. If anything is left in
  // the zone after our own records have gone, somebody put it there and the
  // zone stays. That makes a state file written from a guess safe: the worst a
  // wrong `zoneCreatedByUs` can do is delete something already empty.
  let zoneDeleted = false
  let notEmpty = 0
  if (state.zoneCreatedByUs && state.zoneId) {
    notEmpty = (await z.allRecords(token, state.zoneId))
      .filter((r) => !(r.type === 'NS' && r.name === domain)).length
    if (notEmpty === 0) {
      zoneDeleted = await z.deleteZone(token, state.zoneId)
      log('zone', zoneDeleted)
    }
  }

  await saveState(domain, {
    addedRecordIds: [],
    preparedAt: null,
    verifiedAt: null,
    ...(zoneDeleted ? { zoneId: null, zoneCreatedByUs: false, validatedAt: null } : {}),
    rolledBackAt: new Date().toISOString(),
  }, dir)

  return {
    ok: true,
    recordsRemoved: removed.length,
    zoneDeleted,
    zoneKept: Boolean(state.zoneId) && !zoneDeleted,
    keptBecause: !state.zoneId ? null
      : !state.zoneCreatedByUs ? 'the zone was already there before this run started'
        : notEmpty ? `${notEmpty} record(s) in it were not written by this run`
          : null,
  }
}
