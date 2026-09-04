#!/usr/bin/env node
// Move a domain onto Cloudflare without opening a dashboard.
//
//   node bin/idp/migrate-domain/migrate-domain.mjs mumchimp.com                 all four safe phases
//   node bin/idp/migrate-domain/migrate-domain.mjs mumchimp.com --watch         then wait for the registrar
//   node bin/idp/migrate-domain/migrate-domain.mjs mumchimp.com --phase=verify  one phase on its own
//   node bin/idp/migrate-domain/migrate-domain.mjs mumchimp.com --rollback      undo what a run did
//   node bin/idp/migrate-domain/migrate-domain.mjs mumchimp.com --dry-run       read, print, change nothing
//
// It reads the zone off the nameservers currently answering for it, proves the
// credential can do the whole job before it does any of it, writes every record
// in, and refuses to print the go-ahead unless both sides answer identically.
//
// The only step it cannot do is the registrar. 123-reg has no public API for a
// retail account, so the last move is two strings pasted into one form. It
// prints them, gates them, and with --watch tells you when the change lands.
import * as z from './console/zone.mjs'
import * as ph from './console/phases.mjs'
import * as auth from './lib/cf-auth.mjs'
import { checkCfToken } from './console/checks.mjs'
import { notify } from './lib/notify.mjs'

const b = (s) => `\x1b[1m${s}\x1b[0m`
const dim = (s) => `\x1b[2m${s}\x1b[0m`
const red = (s) => `\x1b[31m${s}\x1b[0m`
const grn = (s) => `\x1b[32m${s}\x1b[0m`
const say = (s = '') => process.stdout.write(s + '\n')

const argv = process.argv.slice(2)
const domain = argv[0]
const flag = (n) => argv.find((a) => a === `--${n}` || a.startsWith(`--${n}=`))
const value = (n) => (flag(n) || '').split('=')[1] || null

const watch = Boolean(flag('watch'))
const dryRun = Boolean(flag('dry-run'))
const rollback = Boolean(flag('rollback'))
const phase = value('phase')
// Notifications are on when they are configured, off when they are not. There
// is no flag to remember. --no-notify is for the run you do not want on the
// record, and for tests.
const quiet = Boolean(flag('no-notify'))

// What phase we are in, so a failure can say so without being handed it.
let current = null
const note = async (event, extra = {}) => {
  if (quiet) return
  await notify({ event, domain, phase: current, ...extra })
}

if (!domain || domain.startsWith('-') || (phase && !ph.PHASES.includes(phase))) {
  say('usage: node bin/idp/migrate-domain/migrate-domain.mjs <domain> [--watch] [--dry-run]')
  say('                                       [--phase=' + ph.PHASES.join('|') + ']')
  say('                                       [--rollback] [--no-notify]')
  process.exit(2)
}

// A phase that fails says one sentence, names the permission when that is the
// problem, and exits. Every failure path goes through here so none of them can
// end in a stack trace with a status code in it.
async function halt(r) {
  say('')
  say(red('  ' + r.stop))
  if (r.need) say(dim('  what is missing: ' + r.need))
  if (r.rolledBack === true) say(dim('  the zone this run created has been removed - nothing was left behind'))
  if (r.rolledBack && typeof r.rolledBack === 'object') {
    say(dim(`  rolled back: ${r.rolledBack.recordsRemoved} record(s)`
      + (r.rolledBack.zoneDeleted ? ' and the zone this run created' : '')))
    if (r.rolledBack.keptBecause) say(dim(`  the zone was kept - ${r.rolledBack.keptBecause}`))
  }
  if (r.need && /DNS|Zone/.test(r.need)) { say(''); say('  Token needs Zone:Edit and DNS:Edit permissions') }
  await note('migration.phase_failed', { status: 'blocked', error: r.stop, need: r.need || null })
  await cleanUp()
  process.exit(1)
}

// ------------------------------------------------------------- the credential

async function getToken() {
  const { token: T, from } = await auth.findToken()
  if (T) { say(dim(`  credential from ${from}`)); return T }
  if (dryRun) return null

  say('')
  say(red('  No Cloudflare token found'))
  say(dim('  Set CF_API_TOKEN env var or add cloudflare-api-token to vault:'))
  say(dim('    bin/idp-cloud secret set cloudflare-api-token <token>'))
  process.exit(1)
}

const needsToken = !dryRun && phase !== 'discover' && phase !== 'lockdown' && phase !== 'cutover'
const ROOT = needsToken || rollback ? await getToken() : null

if (ROOT) {
  const v = await checkCfToken(ROOT)
  if (!v.ok) {
    say(red(`Cloudflare will not accept this credential: ${v.note}`))
    say(dim('  To update the vault token: bin/idp-cloud secret set cloudflare-api-token <token>'))
    process.exit(1)
  }
  say(dim(`  ${v.note}`))
}

// A credential that can mint others is not used for the work. Mint one that
// dies in an hour, use that, delete it on the way out — including on Ctrl-C,
// which is the exit path that actually happens.
let T = ROOT
let ephemeral = null
if (ROOT && !dryRun) {
  const id = await z.accountId(ROOT)
  if (id) {
    ephemeral = await auth.mintEphemeral(ROOT, id, { hours: 1 })
    if (ephemeral) {
      T = ephemeral.token
      say(dim(`  minted a token that expires ${ephemeral.expires} and is deleted when this finishes`))
    }
  }
}

async function cleanUp() {
  if (!ephemeral) return
  const gone = await auth.revokeToken(ROOT, ephemeral.id)
  ephemeral = null
  say(dim(gone ? '  ephemeral token deleted' : '  could not delete the ephemeral token — it expires within the hour'))
}
process.on('exit', () => { if (ephemeral) process.stderr.write('\n  ephemeral token left to expire\n') })
for (const sig of ['SIGINT', 'SIGTERM']) {
  process.on(sig, async () => { await cleanUp(); process.exit(130) })
}
const finish = async (code) => { await cleanUp(); process.exit(code) }

// ----------------------------------------------------------------- rollback

if (rollback) {
  say('')
  say(b(`Undoing what the last run did to ${domain}`))
  const r = await ph.undo(domain, T)
  if (!r.ok) { say(red('  ' + r.stop)); await finish(1) }
  say(`  ${r.recordsRemoved} record(s) removed`)
  say(r.zoneDeleted
    ? '  the zone this run created has been deleted'
    : dim(`  the zone was kept — ${r.keptBecause || 'it was not created by a run'}`))
  say('')
  say(dim('  Live traffic was never on Cloudflare, so nothing outside changed.'))
  await note('migration.rollback', {
    status: 'done', records: r.recordsRemoved, zoneDeleted: Boolean(r.zoneDeleted),
  })
  await finish(0)
}

// -------------------------------------------------------------- the phases

const only = phase ? [phase] : ['discover', 'validate', 'prepare', 'verify']

for (const step of only) {
  current = step
  const startedAt = Date.now()
  const completed = (extra = {}) => note('migration.phase_complete', {
    status: 'ok', seconds: Math.round((Date.now() - startedAt) / 1000), ...extra,
  })
  await note('migration.phase_start', { status: 'running' })

  if (step === 'discover') {
    say('')
    say(b(`Reading ${domain} from the nameservers answering for it now`))
    const r = await ph.discover(domain)
    if (!r.ok) await halt(r)
    say(`  ${r.nameServers.join(', ')}`)
    for (const rec of r.records) say('  ' + dim(z.key(rec).slice(0, 110)))
    say(`  ${r.records.length} records`)
    if (!r.records.some((x) => x.type === 'MX')) {
      say(red('  no MX — if this domain takes mail, the sweep missed it. Stop.'))
    }
    if (dryRun) { say(''); say('--dry-run: nothing was created.'); await finish(0) }
    await completed({ records: r.records.length })
  }

  if (step === 'validate') {
    say('')
    say(b('Proving the credential can do the whole job before it does any of it'))
    const r = await ph.validate(domain, T)
    if (!r.ok) await halt(r)
    say(r.fresh ? `  zone created (${r.zone.status})` : `  zone already exists (${r.zone.status})`)
    if (r.fresh) {
      say(dim('  waiting for its own scan, as a second opinion on the record list'))
      await new Promise((res) => setTimeout(res, 20000))
    }
    await completed({ zoneCreated: Boolean(r.fresh), zoneStatus: r.zone.status })
  }

  if (step === 'prepare') {
    say('')
    say(b('Writing the records in, all grey-clouded'))
    const r = await ph.prepare(domain, T, {
      onEach: (rec) => {
        const mark = rec.state === 'added' ? grn('+') : rec.state === 'already there' ? dim('=') : red('!')
        say(`  ${mark} ${rec.type.padEnd(5)} ${rec.name.padEnd(38)} `
          + (rec.state === 'added' || rec.state === 'already there' ? '' : rec.state))
      },
    })
    if (!r.ok) await halt(r)
    say(dim(`  ${r.added} written, ${r.already} already there`))
    await completed({ records: r.added + r.already, written: r.added })
  }

  if (step === 'verify') {
    say('')
    say(b('Asking both sets of nameservers the same questions'))
    const r = await ph.verify(domain, {
      onWait: (missing, i, of) =>
        say(dim(`  ${missing} not answered by Cloudflare yet - waiting (${i}/${of - 1})`)),
    })
    if (!r.ok) {
      if (r.diff) for (const k of r.diff.missing) say(red('  missing on Cloudflare: ') + k.slice(0, 100))
      say('')
      say(red(b('NOT READY. Do not touch the registrar.')))
      await halt(r)
    }
    say(`  ${r.diff.total} records asked for on the old side`)
    for (const k of r.diff.extra) say(dim('  extra on Cloudflare:   ') + k.slice(0, 100))
    say('')
    say(grn(b('Identical. Cloudflare answers exactly as the old nameservers do.')))
    await completed({ status: 'identical', records: r.diff.total })
    // The one worth waking up for: everything is staged and the registrar is
    // the only thing left.
    await note('migration.cutover_ready', { status: 'ready', records: r.diff.total })
  }

  if (step === 'cutover') {
    const r = await ph.cutover(domain)
    if (!r.ok) await halt(r)
    printRegistrarStep(r.from, r.to)
    await note('migration.cutover_ready', { status: 'unlocked, waiting for the paste', to: r.to })
    await finish(0)
  }

  if (step === 'lockdown') {
    say('')
    say(b('Checking the change landed everywhere and the door is shut again'))
    const r = await ph.lockdown(domain)
    if (!r.ok) {
      say(red('  ' + r.stop))
      for (const [who, got] of Object.entries(r.seen || {})) say(dim(`  ${who}: ${got || 'no answer'}`))
      await finish(1)
    }
    say(grn('  every resolver answers with the new nameservers, and the lock is back on'))
    await completed({ status: 'complete' })
    await note('migration.lockdown_done', { status: 'complete' })
    await finish(0)
  }
}

// Nothing past here calls Cloudflare — the watch loop only asks nameservers.
await cleanUp()

if (phase) {
  // --watch lives past this line, so a run that asked for both got neither the
  // wait nor a word about it. Say so rather than exit quietly: a command that
  // silently ignores half of what you typed teaches you to distrust the rest.
  if (watch) say(dim('  --watch does nothing with --phase. Run without --phase to wait for the registrar.'))
  process.exit(0)
}

// --------------------------------------------------------- the one manual step

const state = await ph.loadState(domain)
printRegistrarStep(state.oldNameServers, state.newNameServers)

function printRegistrarStep(from, to) {
  say('')
  say(b('Your one step, at 123-reg — nowhere else'))
  const lock = state?.registrar
  if (lock?.locked) {
    say('')
    say(red('  First, turn the domain lock off. It is on right now.'))
    say(dim(`  The registry has ${lock.statuses.join(', ')} set, which blocks a nameserver`))
    say(dim('  change. The form does not say that — it says "Invalid nameservers".'))
    say(dim('  123-reg: Manage Domain → Domain Lock → off. Turn it back on afterwards.'))
    say('')
  }
  say('  https://www.123-reg.co.uk/secure/cpanel/domain/' + domain + '/manage-nameservers')
  say('  Replace the two nameservers with:')
  say('')
  for (const n of to || []) say('    ' + b(n))
  say('')
  say(dim('  Nothing else changes. Every record above already answers identically,'))
  say(dim('  so the shop and the mail carry on through the switch. To undo: put'))
  say(dim(`  ${(from || []).join(' and ')} back.`))
}

if (!watch) {
  say('')
  say(dim('  Run again with --watch and it will tell you when the change lands.'))
  process.exit(0)
}

// ------------------------------------------------------------- wait for it

say('')
say(b('Watching for the registrar change. Ctrl-C to stop.'))
const want = (state.newNameServers || []).join(',')
for (let i = 0; i < 720; i++) {
  const now = await z.nameserversNowServing(domain)
  if (now.join(',') === want) {
    say('')
    say(grn(b('Live on Cloudflare.')) + ` ${domain} is answered by ${state.newNameServers.join(' and ')}.`)
    say(dim('  Next: node scripts/migrate-domain.mjs ' + domain + ' --phase=lockdown'))
    current = 'cutover'
    await note('migration.cutover_done', { status: 'live on cloudflare', to: state.newNameServers })
    process.exit(0)
  }
  process.stdout.write(`\r  ${new Date().toISOString().slice(11, 19)}  still ${now.join(', ') || 'unresolved'}   `)
  await new Promise((r) => setTimeout(r, 60000))
}
