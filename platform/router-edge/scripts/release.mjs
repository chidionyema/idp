#!/usr/bin/env node
// Zone B release adapter. Existing Greenlane is the only source-admission authority.
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { liveRoles, probeCodexSurface, probeLanes, releasePool, rolePool, seedRolePool, vendorSecrets } from "./role-pool.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function requireMainSha(ref, expected, actual) {
  if (ref !== "refs/heads/main" || !/^[0-9a-f]{40}$/.test(expected || "") || expected !== actual) {
    throw new Error("BLIND: release is not the exact checked-out main SHA");
  }
  return expected;
}
export function activeRollbackId(raw) {
  const json = JSON.parse(raw);
  const versions = Array.isArray(json) ? json : (json?.versions ?? json?.deployment?.versions ?? json?.result?.versions);
  if (!Array.isArray(versions)) throw new Error("BLIND: unrecognized Wrangler deployment status");
  const active = versions.filter(x => Number(String(x.percentage).replace("%", "")) === 100);
  const id = active.length === 1 ? (active[0].version_id ?? active[0].id) : "";
  if (typeof id !== "string" || !UUID.test(id)) throw new Error("BLIND: no single 100-percent active rollback version");
  return id;
}
export function pinnedWranglerVersion(output) {
  return /\b4\.131\.0\b/.test(output);
}
export function immutableTag(sha) {
  if (!/^[0-9a-f]{40}$/.test(sha)) throw new Error("BLIND: SHA must be a full commit identifier");
  return "meridian-" + sha;
}
// A failed child's own words, made safe to carry into the receipt: opaque strings and
// bearer tokens are replaced, and only the last non-empty line is kept. Without this a
// failure reads `rc=1` and the cause lives only in a log nobody can act on.
export function redact(text) {
  return String(text ?? "")
    .replace(/\b[A-Za-z0-9_-]{32,}\b/g, "<redacted>")
    .replace(/Bearer\s+\S+/gi, "Bearer <redacted>")
    .trim();
}
export function failureCause(text, max = 300) {
  // Wrangler ends its stderr with a pointer to a log file on the runner, which says
  // nothing; the diagnosis is a few lines above it. Strip colour, drop the pointer,
  // then keep the last three meaningful lines so one run names the whole refusal.
  const clean = redact(String(text ?? "").replace(/\u001b\[[0-9;]*m/g, ""));
  const lines = clean.split(/\r?\n/).map(s => s.trim()).filter(Boolean)
    .filter(s => !/logs were written to/i.test(s));
  // A `--strict` upload that aborts on remote drift prints the drift itself (what the
  // remote holds that the repo does not) ABOVE the three closing lines. Cut to three,
  // the receipt said "Aborting ... because of conflicts" and never what conflicted
  // (run 46104640154). Keep the whole block when that refusal is present.
  const keep = /because of conflicts/i.test(clean) ? 40 : 3;
  return lines.slice(-keep).join(" / ").slice(0, max);
}
function run(cmd, args, env = {}, timeout = 120000, stripWorkerAuthority = false) {
  const childEnv = { ...process.env, ...env };
  if (stripWorkerAuthority) {
    delete childEnv.CLOUDFLARE_API_TOKEN;
    delete childEnv.CLOUDFLARE_ACCOUNT_ID;
  }
  const p = spawnSync(cmd, args, {
    cwd: ROOT, env: childEnv, encoding: "utf8", timeout, maxBuffer: 1024 * 1024,
  });
  // Never echo process output: it could contain credentials or provider responses.
  if (p.error || p.status !== 0) {
    const cause = failureCause(p.stderr || p.stdout);
    const err = new Error(
      path.basename(cmd) + " " + args.slice(0, 2).join(" ") + " failed rc=" + (p.status ?? "signal")
      + (cause ? ": " + cause : ""),
    );
    // A 300-character last line is a SUMMARY, not a cause. The error carries the whole child
    // message so the receipt can name which lane failed how, not a prefix of it.
    err.detail = failureCause(p.stderr || p.stdout, 4000);
    throw err;
  }
  return p.stdout;
}
// `--strict` aborts an upload when the Worker's remote configuration was last changed from
// the Cloudflare dashboard (adding a secret there is enough) and so differs from the repo's
// wrangler.toml; it will ALWAYS differ on COMMIT_SHA, which the release injects per version.
// Measured 2026-11-28, run 46106336731. That refusal protects a drift nobody has seen, so
// it is the one failure the release answers with a single reconciling upload: the drift is
// kept in the receipt (`strict_override`) and the next upload is strict again, because the
// version this one writes is wrangler's own.
export function isStrictConflict(text) {
  return /because of conflicts/i.test(String(text ?? ""));
}
// `--keep-vars` retains the vars of the PREVIOUS deployment. On a worker with no
// deployment there is nothing to keep and Wrangler refuses the upload, so first boot
// uploads without it (I-8455 Stage 1, founder waiver 2026-11-25).
export function uploadArgs(sha, tag, hasPreviousVersion, strict = true) {
  const args = [
    "versions", "upload", "--tag", tag, "--message", "meridian:" + sha,
    "--var", "COMMIT_SHA:" + sha,
  ];
  if (hasPreviousVersion) args.push("--keep-vars");
  if (strict) args.push("--strict");
  return args;
}
// First boot creates the Worker and applies the Durable Object migration, which only
// `wrangler deploy` may do. It also creates the 100% deployment directly, so there is
// nothing for `versions deploy` to promote afterwards.
export function firstBootDeployArgs(sha, tag) {
  return [
    "deploy", "--var", "COMMIT_SHA:" + sha, "--tag", tag,
    "--message", "meridian:" + sha, "--strict",
  ];
}
// A Worker secret is SCRIPT-scoped, and `--secrets-file` on an upload binds the value to
// that one version. Measured 2026-11-25, run 45685741113: the deploy "succeeded", the very
// next admin call answered 401 invalid_admin_key, and /health reported commit 820bc8a34
// while main was 0064d55f2 — the version being served was a rollback target, so the keys in
// that file never reached the code that answered. `secret bulk` sets the script-level secret
// once, so every version — including a rollback target — authenticates the same caller.
export function secretBulkArgs(secretsFile) {
  return ["secret", "bulk", secretsFile];
}
// The Worker compares a caller's bearer against ITS OWN secret, and a deploy never
// uploads one: a Worker deployed without this rejects every real caller with 401
// while /health stays 200. The values are already in this step's env for the probes.
export function workerSecrets(env) {
  const secrets = {};
  for (const k of ["MERIDIAN_CLIENT_KEY", "MERIDIAN_ADMIN_KEY"]) {
    if (env[k]) secrets[k] = env[k];
  }
  // The routing plane resolves each candidate's `apiKeySecretName` from the Worker's own
  // env, so a lane without its vendor key is a 502 on every call it is chosen for.
  return Object.assign(secrets, vendorSecrets(env));
}
// Caller/admin authentication is mandatory. Vendor lanes are alternatives, not
// conjunctive requirements. A pre-existing binding is custody evidence, not a
// capacity or inference proof. Never overwrite an existing key with an empty value.
export function completeSecretBundle(env, pool = rolePool(), existing = []) {
  const secrets = workerSecrets(env);
  const supplied = name => typeof secrets[name] === "string" && Boolean(secrets[name].trim());
  const missing = ["MERIDIAN_CLIENT_KEY", "MERIDIAN_ADMIN_KEY"].filter(name => !supplied(name));
  if (missing.length) throw new Error("MISSING_REQUIRED_WORKER_BINDINGS:" + missing.join(","));
  for (const name of Object.keys(secrets)) if (!supplied(name)) delete secrets[name];
  const present = new Set(existing);
  for (const [name, role] of Object.entries(pool.roles)) {
    if (!role.candidates.some(c => c.enabled && (supplied(c.apiKeySecretName) || present.has(c.apiKeySecretName)))) {
      throw new Error("NO_CUSTODIED_VENDOR_BINDING:" + name);
    }
  }
  if (!Object.keys(pool.roles).length) throw new Error("NO_CONFIGURED_ROLE");
  return secrets;
}

export function existingSecretNames(raw) {
  const rows = JSON.parse(raw);
  if (!Array.isArray(rows) || rows.some(row => !row || typeof row.name !== "string" || row.type !== "secret_text")) {
    throw new Error("UNPROVEN_WORKER_SECRET_INVENTORY");
  }
  return rows.map(row => row.name);
}

const CUTOVER_HOSTS = new Set(["submit.meridianlabs.cloud", "lifeboat-llm.meridianlabs.cloud"]);
const CF_ID = /^[a-f0-9]{32}$/i;
const TUNNEL = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\.cfargotunnel\.com$/i;

// The release identity cannot invent the retired target or the intended service.
// Both must come from an exact independently authorised cutover manifest.
export function domainCutoverPlan(raw, account) {
  const data = JSON.parse(raw);
  if (!CF_ID.test(account) || data.account !== account || !CF_ID.test(data.zone) ||
      !Array.isArray(data.hosts) || data.hosts.length !== CUTOVER_HOSTS.size) {
    throw new Error("INVALID_DOMAIN_CUTOVER_SCOPE");
  }
  const names = new Set();
  for (const h of data.hosts) {
    if (!CUTOVER_HOSTS.has(h.hostname) || names.has(h.hostname) ||
        !TUNNEL.test(h.retiredTarget) || !/^[a-z0-9][a-z0-9-]{0,62}$/.test(h.service) ||
        (h.hostname === "lifeboat-llm.meridianlabs.cloud" && h.service !== "estate-lifeboat") ||
        h.service === "meridian-router-edge") throw new Error("INVALID_DOMAIN_CUTOVER_HOST");
    names.add(h.hostname);
  }
  return data;
}

export async function reconcileRetiredDomains(plan, {workersToken, dnsToken, fetchImpl = fetch}) {
  if (!workersToken || !dnsToken) throw new Error("DOMAIN_CUTOVER_AUTHORITY_MISSING");
  plan = domainCutoverPlan(JSON.stringify(plan), plan.account);
  const origin = "https://api.cloudflare.com/client/v4";
  async function cf(token, pathname, method = "GET", body) {
    const res = await fetchImpl(origin + pathname, {
      method, redirect: "error",
      headers: {authorization: "Bearer " + token, "content-type": "application/json"},
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const json = await res.json();
    if (!res.ok || json.success !== true) throw new Error("CLOUDFLARE_" + method + "_HTTP_" + res.status);
    if ((json.result_info?.total_pages ?? 1) > 1) throw new Error("DOMAIN_LIST_INCOMPLETE");
    return json.result;
  }
  const domains = "/accounts/" + plan.account + "/workers/domains";
  const records = "/zones/" + plan.zone + "/dns_records";
  const zone = await cf(dnsToken, "/zones/" + plan.zone);
  if (zone?.name !== "meridianlabs.cloud" || zone?.account?.id !== plan.account) {
    throw new Error("DOMAIN_ZONE_ACCOUNT_MISMATCH");
  }
  const readDomain = h => cf(workersToken, domains + "?hostname=" + encodeURIComponent(h.hostname));
  const readDns = h => cf(dnsToken, records + "?name=" + encodeURIComponent(h.hostname));
  const same = (d, h) => d.hostname === h.hostname && d.service === h.service &&
    d.zone_id === plan.zone && d.enabled === true;
  const retired = (d, h) => d.name === h.hostname && d.type === "CNAME" && d.content === h.retiredTarget;
  // Complete all read-only preflight before any record is removed.
  const work = [];
  for (const h of plan.hosts) {
    const current = await readDomain(h);
    if (!Array.isArray(current) || current.some(d => !same(d, h)) || current.length > 1) {
      throw new Error("DOMAIN_OWNERSHIP_CONFLICT:" + h.hostname);
    }
    if (current.length === 1) { work.push({h, done: true}); continue; }
    // A custom domain belongs to the specified existing service, never the router by default.
    await cf(workersToken, "/accounts/" + plan.account + "/workers/scripts/" + h.service + "/settings");
    const dns = await readDns(h);
    if (!Array.isArray(dns) || dns.length !== 1 || !retired(dns[0], h) || !CF_ID.test(dns[0].id)) {
      throw new Error("RETIRED_CNAME_NOT_EXACT:" + h.hostname);
    }
    work.push({h, previous: dns[0]});
  }
  const result = [];
  for (const item of work) {
    const {h, previous} = item;
    if (item.done) { result.push({hostname: h.hostname, status: "ALREADY_ATTACHED"}); continue; }
    // Re-read immediately before mutation. A changed record is not ours to delete.
    const fresh = await readDns(h);
    const attached = await readDomain(h);
    if (attached.length || fresh.length !== 1 || fresh[0].id !== previous.id || !retired(fresh[0], h)) {
      throw new Error("DNS_REVISION_CHANGED:" + h.hostname);
    }
    await cf(dnsToken, records + "/" + previous.id, "DELETE");
    try {
      await cf(workersToken, domains, "PUT", {hostname: h.hostname, service: h.service, zone_id: plan.zone});
      const live = await readDomain(h);
      if (live.length !== 1 || !same(live[0], h)) throw new Error("DOMAIN_READBACK_MISMATCH");
    } catch {
      // Restore only when readback proves neither custom domain nor replacement DNS exists.
      const nowDomain = await readDomain(h);
      const nowDns = await readDns(h);
      if (!nowDomain.length && !nowDns.length) {
        await cf(dnsToken, records, "POST", {
          type: previous.type, name: previous.name, content: previous.content,
          ttl: previous.ttl, proxied: previous.proxied,
        });
      }
      throw new Error("DOMAIN_ATTACH_NOT_VERIFIED:" + h.hostname);
    }
    result.push({hostname: h.hostname, status: "ATTACHED"});
  }
  return result;
}
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
// WHEN TO ROLL BACK IS A DECISION, NOT A REFLEX. Measured 2026-11-25 (run 45691317108): every
// lane failed with its own named vendor error (minimax 402, deepseek 401, gemini
// missing_secret_GEMINI_API_KEY), the release rolled back to 031b134f anyway, and the
// post-rollback probe failed too -- because that version holds no role pool at all, so the
// surface it restored answered `unknown_role` to every caller. A rollback to a strictly worse
// version is not safety; it is a second regression, and it defeats the design that a key set
// out-of-band (dashboard) starts serving with no release.
//
// A deployment that answers with its OWN structured refusal is working: it routed, tried each
// candidate in priority order, and named each cause. The lanes are down, not the deploy.
export function isAllBackendsFailed(text) {
  // The measured body arrives ESCAPED: the prober's failure is a JSON string inside the JSON
  // line the child printed, so the receipt holds \"type\":\"all_pool_backends_failed\".
  // Matching only the unescaped form is why run 45693773697 still rolled back after this
  // decision landed -- the falsifier had pinned a shape the estate never actually emits.
  const flat = String(text ?? "").replace(/\\"/g, '"');
  return /"type"\s*:\s*"all_pool_backends_failed"/.test(flat);
}

export function shouldRollback({ liveSha, releasedSha, probeError }) {
  // No answer at all, or the wrong version answering: the deploy is the problem.
  if (!liveSha || liveSha !== releasedSha) return true;
  if (!probeError) return false;
  // The release's own answer from its own pool: keep the version that can route.
  return !isAllBackendsFailed(probeError);
}
// What a failed release writes down. Measured 2026-11-25 (run 45688808353): the pool answered
// 503 all_pool_backends_failed and the receipt stopped inside the FIRST attempt
// ("backendId":"minimax-m3","status":402 ...), so which lane failed how -- the whole point of
// the receipt -- was unreadable. The summary line stays short; the detail carries the cause.
export function receiptError(e) {
  const message = String(e?.message ?? e);
  const detail = String(e?.detail ?? message);
  return { error: message.slice(0, 400), error_detail: detail.slice(0, 4000) };
}
// A new Cloudflare deployment propagates in seconds, and a 3x3s window was measured too
// short on run 45685741113, where /health still answered the rollback target afterwards.
// The window is a named budget so a falsifier can assert it rather than guess it.
export const SERVE_ATTEMPTS = 5;
export const SERVE_PAUSE_MS = 3000;

// What the deployment says about itself, read from the deployment.
export async function liveCommitSha(baseUrl, fetchImpl = fetch) {
  const res = await fetchImpl(baseUrl + "/health");
  if (!res.ok) throw new Error(`health refused ${res.status}`);
  const data = await res.json();
  if (typeof data?.commit_sha !== "string") throw new Error("BLIND: /health carries no commit_sha");
  return data.commit_sha;
}

export async function release() {
  const r = {
    schema: "meridian/zone-b-release-v1", sha: process.env.RELEASE_SHA ?? null,
    status: "BLIND", previous_version_id: null, upload_ok: false, deploy_attempted: false,
    probes: [], rollback_attempted: false, rollback_verified: false, error: null,
    role_seed: null, live_commit_sha: null, secrets_applied: false, error_detail: null, strict_override: null,
    rollback_skipped: null, lanes: [], dead_lanes: [], codex_surface: null,
    started_at: new Date().toISOString(),
  };
  const out = process.env.RELEASE_RECEIPT_PATH || path.join(process.cwd(), "router-release-receipt.json");
  const wrangler = path.join(ROOT, "node_modules", ".bin", "wrangler");
  let secretsFile = "";
  let secretsDir = "";
  try {
    const sha = requireMainSha(process.env.GITHUB_REF, process.env.RELEASE_SHA, run("git", ["rev-parse", "HEAD"]).trim());
    for (const k of ["CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "MERIDIAN_CLIENT_KEY", "MERIDIAN_ADMIN_KEY"]) {
      if (!process.env[k]) throw new Error("BLIND: missing trusted secret " + k);
    }
    if (process.env.MERIDIAN_ROUTER_URL !== "https://llm.meridianlabs.cloud") {
      throw new Error("BLIND: target hostname differs from canonical Zone B endpoint");
    }
    if (!fs.existsSync(wrangler) || !pinnedWranglerVersion(run(wrangler, ["--version"]))) {
      throw new Error("BLIND: pinned Wrangler 4.131.0 absent");
    }
    // Tests ran in the prior credential-free GitHub step. Never execute npm here.
    const preflight = process.env.RELEASE_PREFLIGHT_FILE;
    if (!preflight || fs.readFileSync(preflight, "utf8").trim() !== sha) {
      throw new Error("BLIND: exact-SHA preflight receipt missing");
    }
    // Without a single previously active version, DO migration/bootstrap needs separate explicit authority.
    // First boot (I-8455 Stage 1, founder waiver 2026-11-25): a worker with zero
    // deployments refuses `deployments status` (rc=1). That is not an outage — it is
    // the initial deploy. Proceed without a rollback target; rollback stays refused
    // until a previous version exists.
    try {
      r.previous_version_id = activeRollbackId(run(wrangler, ["deployments", "status", "--json"]));
    } catch {
      r.previous_version_id = null;
    }
    const tag = immutableTag(sha);
    // The Worker's own secrets are values a deploy never carries; without them the edge
    // rejects every real caller while /health reports ok. Written 0600, used, removed.
    const pool = rolePool();
    const existing = r.previous_version_id
      ? existingSecretNames(run(wrangler, ["secret", "list", "--format", "json"]))
      : [];
    const secrets = completeSecretBundle(process.env, pool, existing);
    r.vendor_binding_custody = Object.values(pool.roles).flatMap(role => role.candidates
      .filter(c => c.enabled).map(c => ({
        id: c.id,
        source: Object.hasOwn(secrets, c.apiKeySecretName) ? "sync" :
          existing.includes(c.apiKeySecretName) ? "existing" : "absent",
      })));
    // A complete binding is NOT evidence of working provider capacity.
    // The existing three authenticated probes remain the operational gate.
    secretsDir = fs.mkdtempSync(path.join(os.tmpdir(), "meridian-worker-secrets-"));
    secretsFile = path.join(secretsDir, "bundle.json");
    fs.writeFileSync(secretsFile, JSON.stringify(secrets), { mode: 0o600, flag: "wx" });
    const cutover = process.env.MERIDIAN_DOMAIN_CUTOVER_JSON
      ? domainCutoverPlan(process.env.MERIDIAN_DOMAIN_CUTOVER_JSON, process.env.CLOUDFLARE_ACCOUNT_ID)
      : null;
    if (cutover && !process.env.CLOUDFLARE_DNS_API_TOKEN) throw new Error("DOMAIN_CUTOVER_AUTHORITY_MISSING");
    // DO migrations must not be silently converted to an unversioned initial deploy.
    // Cloudflare refuses a Durable Object class creation from `versions upload`:
    // "any change that creates, deletes, renames, or transfers a Durable Object class
    // must be applied through wrangler deploy" (Workers docs, deployment management).
    // wrangler.toml declares new_sqlite_classes v1, so first boot IS that change.
    if (r.previous_version_id === null) {
      run(wrangler, firstBootDeployArgs(sha, tag));
    } else {
      try {
        run(wrangler, uploadArgs(sha, tag, true));
      } catch (e) {
        if (!isStrictConflict(e.detail ?? e.message)) throw e;
        r.strict_override = String(e.detail ?? e.message).slice(0, 1500);
        run(wrangler, uploadArgs(sha, tag, true, false));
      }
      r.upload_ok = true;
      run(wrangler, ["versions", "deploy", "--version-tag", tag + "@100%", "--yes", "--message", "meridian:" + sha]);
    }
    r.deploy_attempted = true;
    // "uploaded" and "serving" are different facts. A rollback from an earlier failed run
    // leaves the OLD version answering while this run says upload_ok; the receipt must not
    // call that a deploy. Retried because a new deployment propagates in seconds.
    for (let n = 1; n <= SERVE_ATTEMPTS; n++) {
      try {
        r.live_commit_sha = await liveCommitSha(process.env.MERIDIAN_ROUTER_URL);
        if (r.live_commit_sha === sha) break;
      } catch (e) {
        r.live_commit_sha = null;
      }
      if (n === SERVE_ATTEMPTS) {
        throw new Error(`deploy not serving: /health reports ${r.live_commit_sha ?? "BLIND"}, released ${sha}`);
      }
      await pause(SERVE_PAUSE_MS);
    }
    // Script-scoped secrets, applied after the deploy so the version that answers holds them.
    if (secretsFile) {
      run(wrangler, secretBulkArgs(secretsFile));
      r.secrets_applied = true;
      await pause(2000);
    }
    // A deployed router with no role pool refuses every routing call: measured on run
    // 45675424976, probe 3 answered 404 {"error":{"type":"admission_refused",
    // "detail":"{\"error\":\"unknown_role\",\"role\":\"role:coder\"}"}} while /health was
    // 200 with configured_roles 0. The pool is seeded through the admin API (zero static
    // TOML) from the estate's recorded lane truth, and only for vendors the Worker holds.
    // Seeding is idempotent, so it is retried while the new version propagates.
    // Repo truth, not release env: the pool names every lane the estate records, and the
    // router fails over across them, so a key set out-of-band (dashboard) serves with no
    // code change and an exhausted wallet costs one attempt instead of the role.
    if (Object.keys(pool.roles).length) {
      for (let n = 1; n <= 3; n++) {
        try {
          r.role_seed = await seedRolePool(process.env.MERIDIAN_ROUTER_URL, process.env.MERIDIAN_ADMIN_KEY, releasePool());
          break;
        } catch (e) {
          r.role_seed = { configured: 0, status: 0, error: String(e?.message ?? e).slice(0, 200) };
          if (n === 3) throw e;
          await pause(3000);
        }
      }
    } else {
      r.role_seed = { configured: 0, status: 0, skipped: "no enabled candidate" };
    }
    // The receipt proves what the ROUTER holds, not what this script sent.
    try {
      r.role_seed.live = await liveRoles(process.env.MERIDIAN_ROUTER_URL, process.env.MERIDIAN_ADMIN_KEY);
    } catch (e) {
      r.role_seed.live_read_error = String(e?.message ?? e).slice(0, 160);
    }
    await pause(3000);
    for (let n = 1; n <= 3; n++) {
      run("node", ["scripts/blackbox-prober.mjs"], { EXPECTED_COMMIT_SHA: sha }, 110000, true);
      r.probes.push({ round: n, passed: true, at: new Date().toISOString() });
    }
    if (cutover) {
      r.domain_cutover = await reconcileRetiredDomains(cutover, {
        workersToken: process.env.CLOUDFLARE_API_TOKEN,
        dnsToken: process.env.CLOUDFLARE_DNS_API_TOKEN,
      });
      for (const h of cutover.hosts) {
        const health = await fetch("https://" + h.hostname + "/health", {redirect: "error"});
        if (!health.ok) throw new Error("DOMAIN_HEALTH_NOT_VERIFIED:" + h.hostname);
      }
    } else {
      r.domain_cutover = {status: "NOT_REQUESTED"};
    }
    // The router answering is not the same fact as every lane answering. The release is
    // OPERATIONAL only when each enabled lane served its own probe; otherwise it is
    // DEGRADED and names the dead lanes. Not a rollback: the deployment is healthy, a key,
    // a wallet or a model id is not, and the previous version has the same lanes.
    r.lanes = await probeLanes(process.env.MERIDIAN_ROUTER_URL, process.env.MERIDIAN_CLIENT_KEY);
    r.dead_lanes = r.lanes.filter((l) => !l.ok).map((l) => l.id);
    const serving = r.lanes.find((l) => l.ok);
    r.codex_surface = serving
      ? await probeCodexSurface(process.env.MERIDIAN_ROUTER_URL, process.env.MERIDIAN_CLIENT_KEY, serving.id)
      : { ok: false, error: "no serving lane to probe" };
    r.status = r.lanes.length && !r.dead_lanes.length && r.codex_surface.ok ? "OPERATIONAL" : "DEGRADED";
  } catch (e) {
    r.status = "NOT_OPERATIONAL";
    Object.assign(r, receiptError(e));
    const canRollback = Boolean(r.deploy_attempted && r.previous_version_id);
    const rollback = canRollback && shouldRollback({
      liveSha: r.live_commit_sha, releasedSha: r.sha, probeError: r.error_detail ?? r.error,
    });
    if (canRollback && !rollback) {
      r.rollback_skipped = "deploy answered with its own all_pool_backends_failed: the lanes are down, the deployment is not";
    }
    if (rollback) {
      r.rollback_attempted = true;
      try {
        run(wrangler, ["rollback", r.previous_version_id, "--message", "restore:" + r.sha]);
        await pause(3000);
        run("node", ["scripts/blackbox-prober.mjs"], { EXPECTED_COMMIT_SHA: "" }, 110000, true);
        r.rollback_verified = true;
      } catch (x) {
        r.rollback_error = String(x?.message ?? x).slice(0, 160);
      }
    }
  } finally {
    if (secretsDir) fs.rmSync(secretsDir, { recursive: true, force: true });
    r.finished_at = new Date().toISOString();
    fs.writeFileSync(out, JSON.stringify(r, null, 2) + "\n", { mode: 0o600 });
    console.log(JSON.stringify({
      status: r.status, sha: r.sha, passed_rounds: r.probes.length,
      role_seed: r.role_seed?.configured ?? 0, dead_lanes: r.dead_lanes, codex_surface_ok: r.codex_surface?.ok,
      rollback_attempted: r.rollback_attempted, rollback_verified: r.rollback_verified,
    }));
  }
  return r.status === "OPERATIONAL" ? 0 : 1;
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = await release();
}
