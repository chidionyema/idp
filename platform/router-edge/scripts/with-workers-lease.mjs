#!/usr/bin/env node
/**
 * P0 #8416 — one-release, least-privilege Cloudflare Workers token lease.
 * Uses the EXISTING Cloudflare root solely as a mint/revoke authority, not as
 * the deployment credential. Does not touch R2, GitHub Secrets, DNS or OCI.
 * The existing main-SHA/rollback guard and black-box probes remain in release.mjs.
 * No token, provider body or raw response is printed.
 */
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const API = 'https://api.cloudflare.com/client/v4';
const ZONE = 'meridianlabs.cloud';
const SAFE_ID = /^[a-z0-9-]{8,64}$/i;
const rawCode = obj => {
  const n = Number(obj?.errors?.[0]?.code);
  return Number.isSafeInteger(n) && n >= 0 ? String(n) : 'UNKNOWN';
};

export function requiredReleaseContext(env) {
  if (env.GITHUB_REF !== 'refs/heads/main' || !/^[a-f0-9]{40}$/.test(env.RELEASE_SHA ?? '') ||
      env.RELEASE_SHA !== env.GITHUB_SHA) throw Error('MAIN_SHA_NOT_ATTESTED');
  if (!env.CLOUDFLARE_ROOT_TOKEN) throw Error('ROOT_MINT_AUTHORITY_NOT_BOUND');
  if (!/^[a-f0-9]{32}$/.test(env.CLOUDFLARE_ACCOUNT_ID ?? '')) throw Error('CLOUDFLARE_ACCOUNT_UNVERIFIED');
  if (!env.MERIDIAN_CLIENT_KEY || !env.MERIDIAN_ADMIN_KEY) throw Error('CLIENT_OR_ADMIN_IDENTITY_UNBOUND');
  return env.RELEASE_SHA;
}

function permission(groups, name, scope, optional = false) {
  const x = groups.find(g => g?.name === name && Array.isArray(g.scopes) && g.scopes.includes(scope));
  if (!x || typeof x.id !== 'string' || !SAFE_ID.test(x.id)) {
    if (optional) return null;
    throw Error('PERMISSION_GROUP_UNAVAILABLE:' + name.replaceAll(' ', '_'));
  }
  return x.id;
}

function mintRecord(payload) {
  if (!payload || !SAFE_ID.test(payload.id ?? '') || typeof payload.value !== 'string' ||
      payload.value.length < 24 || payload.value.length > 512 || /\s/.test(payload.value)) {
    throw Error('TOKEN_MINT_RECEIPT_INVALID');
  }
  return { id: payload.id, value: payload.value };
}

export async function runWithLease({ env = process.env, fetchImpl = fetch, execute = defaultExecute, clock = () => Date.now() } = {}) {
  let root, temporaryReader, temporaryWorker, failure = null, exitCode = 1, cleanupFailed = false;
  // The root is never passed to Wrangler, child env, logs or release receipt.
  async function cf(token, method, apiPath, body) {
    let response, json;
    try {
      response = await fetchImpl(API + apiPath, {
        method, redirect: 'error', cache: 'no-store', signal: AbortSignal.timeout(15000),
        headers: { authorization: 'Bearer ' + token, accept: 'application/json',
          ...(body === undefined ? {} : { 'content-type': 'application/json' }) },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      });
      json = await response.json();
    } catch {
      throw Error('CLOUDFLARE_NETWORK_OR_INVALID_JSON:' + method);
    }
    if (!response.ok || json?.success !== true) {
      throw Error('CLOUDFLARE_REJECTED:' + method + ':http_' + response.status + ':code_' + rawCode(json));
    }
    return json.result;
  }
  const mint = (name, policies) => cf(root, 'POST', '/user/tokens', {
    name, policies,
    expires_on: new Date(clock() + 40 * 60_000).toISOString(),
  }).then(mintRecord);
  const deleteToken = id => cf(root, 'DELETE', '/user/tokens/' + id);
  try {
    const sha = requiredReleaseContext(env);
    root = env.CLOUDFLARE_ROOT_TOKEN;
    const verifyRoot = await cf(root, 'GET', '/user/tokens/verify');
    if (verifyRoot?.status !== 'active') throw Error('ROOT_MINT_AUTHORITY_INACTIVE');
    const groups = await cf(root, 'GET', '/user/tokens/permission_groups');
    if (!Array.isArray(groups)) throw Error('PERMISSION_GROUPS_INVALID');
    const zoneRead = permission(groups, 'Zone Read', 'com.cloudflare.api.account.zone.read');
    const scriptsWrite = permission(groups, 'Workers Scripts Write', 'com.cloudflare.api.account');
    const routesWrite = permission(groups, 'Workers Routes Write', 'com.cloudflare.api.account.zone');
    const aiWrite = permission(groups, 'Workers AI Write', 'com.cloudflare.api.account', true);

    let zones = await cf(root, 'GET', '/zones?name=' + ZONE);
    if (!Array.isArray(zones)) throw Error('ZONE_LOOKUP_INVALID');
    if (zones.length !== 1) {
      // Same bounded zone-read child method used by the existing estate bootstrap.
      temporaryReader = await mint('meridian-zone-read-' + sha.slice(0, 12), [
        {effect:'allow', resources: {'com.cloudflare.api.account.zone.*':'*'},
         permission_groups:[{id:zoneRead}]}
      ]);
      zones = await cf(temporaryReader.value, 'GET', '/zones?name=' + ZONE);
    }
    if (!Array.isArray(zones) || zones.length !== 1 || zones[0]?.name !== ZONE ||
        zones[0]?.account?.id !== env.CLOUDFLARE_ACCOUNT_ID || !SAFE_ID.test(zones[0]?.id ?? '')) {
      throw Error('ZONE_OR_ACCOUNT_IDENTITY_MISMATCH');
    }
    const zoneId = zones[0].id;
    const accountId = env.CLOUDFLARE_ACCOUNT_ID;
    const policies = [
      {effect:'allow', resources: {['com.cloudflare.api.account.' + accountId]:'*'},
       permission_groups:[{id:scriptsWrite}, ...(aiWrite ? [{id:aiWrite}] : [])]},
      {effect:'allow', resources: {['com.cloudflare.api.account.zone.' + zoneId]:'*'},
       permission_groups:[{id:routesWrite}]}
    ];
    temporaryWorker = await mint('meridian-router-release-' + sha.slice(0, 12), policies);
    const verifyWorker = await cf(temporaryWorker.value, 'GET', '/user/tokens/verify');
    if (verifyWorker?.status !== 'active') throw Error('WORKERS_RELEASE_TOKEN_INACTIVE');
    await cf(temporaryWorker.value, 'GET', '/accounts/' + accountId + '/workers/scripts');

    const childEnv = { ...env, CLOUDFLARE_API_TOKEN: temporaryWorker.value };
    delete childEnv.CLOUDFLARE_ROOT_TOKEN;
    delete childEnv.CF_ROOT;
    exitCode = await execute(childEnv);
    if (exitCode !== 0) failure = 'EXISTING_RELEASE_FAILED';
  } catch (err) {
    // Never echo a provider response; all errors are controlled class/code strings.
    failure = String(err?.message ?? err).slice(0, 160);
  } finally {
    // A successful deployment must not leave a reusable Workers deployment token.
    if (root) for (const token of [temporaryWorker, temporaryReader]) {
      if (!token) continue;
      try { await deleteToken(token.id); }
      catch { cleanupFailed = true; }
    }
    root = undefined;
  }
  if (cleanupFailed) failure = 'EPHEMERAL_LEASE_REVOKE_UNVERIFIED';
  console.log(JSON.stringify({ schema:'meridian/router-workers-lease-v1',
    status: failure ? 'NOT_CERTIFIED' : 'RELEASE_EXECUTED',
    failure: failure || null, child_exit_code: exitCode,
    workers_token_revoke_verified: !!temporaryWorker && !cleanupFailed,
    zone_read_child_used: !!temporaryReader,
    r2_used: false,
  }));
  return failure ? 1 : 0;
}

function defaultExecute(env) {
  const cwd = resolve(dirname(fileURLToPath(import.meta.url)), '..');
  const child = spawnSync(process.execPath, ['scripts/release.mjs'], {
    cwd, env, stdio: 'inherit', timeout: 17 * 60_000,
  });
  return child.error ? 1 : (child.status ?? 1);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  process.exitCode = await runWithLease();
}
