// Migration status notifications via webhook.
//
// This module sends migration events to an ops portal webhook. Telegram support
// is handled by the platform's alert system, not directly here.
import { createHmac, timingSafeEqual } from 'node:crypto'

export const EVENTS = [
  'migration.phase_start',
  'migration.phase_complete',
  'migration.phase_failed',
  'migration.cutover_ready',
  'migration.cutover_done',
  'migration.lockdown_done',
  'migration.rollback',
]

const ICON = {
  'migration.phase_start': '▶️',
  'migration.phase_complete': '✅',
  'migration.phase_failed': '❌',
  'migration.cutover_ready': '🔓',
  'migration.cutover_done': '🚀',
  'migration.lockdown_done': '🔒',
  'migration.rollback': '↩️',
}

const cfg = (env) => ({
  webhookUrl: env.OPS_WEBHOOK_URL || null,
  webhookSecret: env.OPS_WEBHOOK_SECRET || null,
})

export function redact(text, env = process.env) {
  let s = String(text ?? '')
  const secrets = [
    env.OPS_WEBHOOK_SECRET, env.OPS_WEBHOOK_URL,
    env.CF_API_TOKEN,
  ].filter((v) => typeof v === 'string' && v.length >= 8)
  for (const v of secrets) s = s.split(v).join('[redacted]')
  return s
}

export function formatEvent(p) {
  const icon = ICON[p.event] || 'ℹ️'
  const lines = [`${icon} ${p.domain} — ${p.phase || p.event}`]
  if (p.status) lines.push(`Status: ${p.status}`)
  if (p.records !== undefined) lines.push(`Records: ${p.records}`)
  if (p.seconds !== undefined) lines.push(`Took: ${p.seconds}s`)
  if (p.error) lines.push(`Error: ${redact(p.error)}`)
  return lines.join('\n')
}

export function sign(body, secret, timestamp) {
  return createHmac('sha256', secret).update(`${timestamp}.${body}`).digest('hex')
}

export function verify(body, secret, timestamp, signature, { now = Date.now(), toleranceMs = 300_000 } = {}) {
  if (!body || !secret || !timestamp || !signature) return false
  if (Math.abs(now - Number(timestamp) * 1000) > toleranceMs) return false
  const want = Buffer.from(sign(body, secret, timestamp), 'utf8')
  const got = Buffer.from(String(signature), 'utf8')
  if (want.length !== got.length) return false
  return timingSafeEqual(want, got)
}

async function postWebhook(payload, c, { env, fetchImpl, timeoutMs }) {
  const body = JSON.stringify({
    ...payload,
    timestamp: new Date().toISOString(),
    source: 'idp/migrate-domain',
  })
  const headers = { 'content-type': 'application/json' }
  if (c.webhookSecret) {
    const ts = Math.floor(Date.now() / 1000).toString()
    headers['x-migration-timestamp'] = ts
    headers['x-migration-signature'] = `sha256=${sign(body, c.webhookSecret, ts)}`
  }
  const res = await fetchImpl(c.webhookUrl, {
    method: 'POST', headers, body, signal: AbortSignal.timeout(timeoutMs),
  })
  if (!res.ok) {
    return { ok: false, why: `ops webhook answered ${res.status}` }
  }
  return { ok: true }
}

export async function notify(payload, {
  env = process.env,
  fetchImpl = globalThis.fetch,
  timeoutMs = 5000,
  log = (m) => process.stderr.write(m + '\n'),
} = {}) {
  const c = cfg(env)
  const out = { webhook: 'not configured' }

  if (c.webhookUrl) {
    try {
      const r = await postWebhook(payload, c, { env, fetchImpl, timeoutMs })
      out.webhook = r.ok ? 'sent' : 'failed'
      if (!r.ok) log(redact('  ' + r.why, env))
    } catch (err) {
      out.webhook = 'failed'
      const why = err?.name === 'TimeoutError' ? `no answer in ${timeoutMs}ms` : (err?.message || String(err))
      log(redact(`  ops webhook notify failed: ${why}`, env))
    }
  }

  return out
}
