// Finding a Cloudflare credential that can actually do the job.
//
// The root credential comes out of the estate's vault, and nothing here ever asks
// a person for one. The tool this was adopted from watched the pasteboard and
// stored the token in the macOS keychain; that whole flow is gone, because the
// estate does not put anybody in front of a vendor console to mint and paste a
// secret (LAW 31, R52). What the root token is for is minting a scoped one that
// expires in an hour, which is the credential the run actually carries.
import { execFile } from 'node:child_process'
import { promisify } from 'node:util'
import { fileURLToPath } from 'node:url'

const run = promisify(execFile)

// -------------------------------------------------------------- vault credential

const VAULT_KEY = 'cloudflare-api-token'

// Get token from vault via idp-cloud
// Resolved against this file, never against the working directory: `bin/idp-cloud`
// as a relative string only works when the tool is launched from the top of the
// checkout, and nothing makes that true (LAW 46).
const IDP_CLOUD = fileURLToPath(new URL('../../../idp-cloud', import.meta.url))

export async function getVaultToken() {
  try {
    const { stdout } = await run(IDP_CLOUD, ['secret', 'get', VAULT_KEY])
    const token = stdout.trim()
    if (token && token.length >= 20) return token
    return null
  } catch {
    return null
  }
}

// -------------------------------------------------------------- credential validation

export const MIN_TOKEN_LENGTH = 20

const NOT_OURS = [
  'sk-', 'sk_', 'pk_', 'rk_', 'whsec_',
  'ghp_', 'gho_', 'ghs_', 'ghu_', 'ghr_', 'github_pat_',
  'xoxb-', 'xoxp-', 'xapp-', 'xoxa-', 'xoxr-',
  'AKIA', 'ASIA', 'ABIA', 'ACCA',
  'AIza', 'ya29.',
  'hf_', 'glpat-', 'gldt-', 'dop_v1_', 'doo_v1_', 'dor_v1_',
  'shpat_', 'shpss_', 'SG.', 'npm_', 'pypi-', 'atlasv1.',
  'fly_', 'FlyV1', 'lin_api_', 'sntrys_', 'sq0atp-', 'sq0csp-',
  'EAAC', 'EAAG', 'r8_', 'tvly-', 'nvapi-', 'ntn_', 'secret_',
]

export function tokenCandidate(s) {
  const v = String(s || '').trim()
  if (!v) return { ok: false, why: 'nothing to check' }
  if (v.length < MIN_TOKEN_LENGTH) {
    return { ok: false, why: `${v.length} characters is too short to be a credential` }
  }
  if (/\s/.test(v)) return { ok: false, why: 'it contains spaces or newlines, so it is text' }
  if (v.includes('://')) return { ok: false, why: 'it is a URL' }
  const vendor = NOT_OURS.find((pfx) => v.startsWith(pfx))
  if (vendor) {
    return { ok: false, why: `it starts with "${vendor}" - that is another vendor's key` }
  }
  return { ok: true }
}

export function looksLikeToken(s) {
  return tokenCandidate(s).ok
}

// -------------------------------------------------------------- discovery

// In order: env var, then vault
export async function findToken() {
  if (process.env.CF_API_TOKEN) return { token: process.env.CF_API_TOKEN, from: 'CF_API_TOKEN' }
  if (process.env.CLOUDFLARE_API_TOKEN) return { token: process.env.CLOUDFLARE_API_TOKEN, from: 'CLOUDFLARE_API_TOKEN' }

  const vaultToken = await getVaultToken()
  if (vaultToken) return { token: vaultToken, from: 'vault' }

  return { token: null, from: null }
}

// -------------------------------------------------------------- tokens minting tokens

const API_BASE = () => (process.env.CF_API_BASE || 'https://api.cloudflare.com') + '/client/v4'

async function api(token, path, opts = {}) {
  try {
    const r = await fetch(API_BASE() + path, {
      ...opts,
      signal: AbortSignal.timeout(25000),
      headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json', ...(opts.headers || {}) },
    })
    const body = await r.json().catch(() => ({}))
    return { ok: r.ok && body.success !== false, body }
  } catch (e) {
    return { ok: false, body: {}, offline: true, error: String(e.message || e) }
  }
}

export async function permissionGroups(token) {
  const r = await api(token, '/user/tokens/permission_groups?per_page=200')
  if (!r.ok) return null
  return r.body.result || []
}

const findGroup = (groups, name, scope) =>
  groups.find((g) => g.name === name && (g.scopes || []).includes(scope))

export async function mintEphemeral(token, accountId, { hours = 1 } = {}) {
  const groups = await permissionGroups(token)
  if (!groups) return null

  const zoneWrite = findGroup(groups, 'Zone Write', 'com.cloudflare.api.account')
  const dnsWrite = findGroup(groups, 'DNS Write', 'com.cloudflare.api.account.zone')
  if (!zoneWrite || !dnsWrite) return null

  const expires = new Date(Date.now() + hours * 3600_000).toISOString().replace(/\.\d{3}/, '')
  const r = await api(token, '/user/tokens', {
    method: 'POST',
    body: JSON.stringify({
      name: `idp ephemeral ${expires.slice(0, 16)}`,
      status: 'active',
      expires_on: expires,
      policies: [{
        effect: 'allow',
        resources: { [`com.cloudflare.api.account.${accountId}`]: '*' },
        permission_groups: [{ id: zoneWrite.id }, { id: dnsWrite.id }],
      }],
    }),
  })
  if (!r.ok || !r.body.result?.value) return null
  return { token: r.body.result.value, id: r.body.result.id, expires }
}

export async function revokeToken(rootToken, tokenId) {
  const r = await api(rootToken, `/user/tokens/${tokenId}`, { method: 'DELETE' })
  return r.ok
}

// --------------------------------------------------------------- what it can do

export async function capability(token) {
  const v = await api(token, '/user/tokens/verify')
  if (!v.ok) return { valid: false, canMint: false, canWriteDns: null, accountId: null, zones: null, offline: !!v.offline }

  const acc = await api(token, '/accounts?per_page=1')
  const accountId = acc.ok ? acc.body.result?.[0]?.id || null : null

  const zr = await api(token, '/zones?per_page=50')
  const zoneList = zr.ok ? zr.body.result || [] : null
  const zones = zoneList ? zoneList.map((z) => z.name) : null

  let canWriteDns = null
  if (zoneList && zoneList.length) {
    const r = await api(token, `/zones/${zoneList[0].id}/dns_records?per_page=1`)
    canWriteDns = r.offline ? null : r.ok
  }

  let canMint = false
  if (accountId) {
    const probe = await mintEphemeral(token, accountId, { hours: 1 })
    if (probe) {
      canMint = true
      await revokeToken(token, probe.id)
    }
  }
  return { valid: true, canMint, canWriteDns, accountId, zones }
}
