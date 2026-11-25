#!/usr/bin/env node
// Zone B release adapter. Existing Greenlane is the only source-admission authority.
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const CF_API = "https://api.cloudflare.com/client/v4";
const SCRIPT_NAME = "meridian-router-edge";
const CONFIG_REL = path.join("clusters", "oke", "estate-config.yaml");

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

// THE ZONE IS WRITTEN ONCE (clusters/<cluster>/estate-config.yaml). No literal zone name may
// live in this file: the estate writes it in one place so a zone migration is one value and one
// reconcile (bin/estate-zone-gate). Everything below derives from that one value.
export function zoneFromConfig(text) {
  const m = /^\s*ESTATE_ZONE:\s*([A-Za-z0-9.-]+)\s*$/m.exec(String(text || ""));
  if (!m) throw new Error("BLIND: ESTATE_ZONE is absent from " + CONFIG_REL);
  return m[1];
}
export function canonicalRouterUrl(zone) {
  if (!/^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$/i.test(String(zone || "")) || !String(zone).includes(".")) {
    throw new Error("BLIND: ESTATE_ZONE is not a hostname");
  }
  return `https://llm.${zone}`;
}
export function routePattern(zone) {
  return `llm.${zone}/*`;
}
export function resolveZone(envZone, configText) {
  const fromConfig = zoneFromConfig(configText);
  if (envZone && envZone !== fromConfig) {
    throw new Error("BLIND: ESTATE_ZONE (" + envZone + ") disagrees with " + CONFIG_REL + " (" + fromConfig + ")");
  }
  return fromConfig;
}

// The receipt is the evidence. A failure without the provider's reason is not a diagnosis, it
// is a shrug: the 2026-11-25 release run said only "rc=1" and cost the estate the reason.
// Provider output can carry credentials, so it is scrubbed and bounded before it is written.
export function scrub(text) {
  return String(text || "")
    .replace(/Bearer\s+[A-Za-z0-9._~+/=-]+/gi, "Bearer ***")
    .replace(/[A-Za-z0-9_-]{32,}/g, "***")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 600);
}

// First boot is not an outage; an unknown prior state is. The provider is asked directly
// (the API answers in JSON) instead of inferring "no deployments" from an exit code:
//   {mode:"bootstrap"}  -> the script has no deployment at all: deploy, no rollback target
//   {mode:"rollback", version_id} -> exactly one active version: deploy, keep the rollback
//   anything else -> refuse. Unknown is never "first boot".
export function classifyPriorDeployments(api, wranglerStatus) {
  if (api && api.status === 404) return { mode: "bootstrap", version_id: null, reason: "script_absent" };
  if (!api || api.status !== 200 || !Array.isArray(api.result)) {
    throw new Error("BLIND: cloudflare did not answer the prior-deployment question");
  }
  if (api.result.length === 0) return { mode: "bootstrap", version_id: null, reason: "no_deployments" };
  const id = activeRollbackId(wranglerStatus);
  return { mode: "rollback", version_id: id, reason: "prior_deployment" };
}
export function secretPayload(name, text) {
  if (!name || !text) throw new Error("BLIND: a worker secret is missing");
  return { name, text, type: "secret_text" };
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
  // Never echo process output: it could contain credentials or provider responses. The failure
  // reason is scrubbed and bounded so the receipt can name it (see scrub).
  if (p.error || p.status !== 0) {
    const why = scrub(p.stderr) || scrub(p.stdout);
    throw new Error(
      path.basename(cmd) + " " + args.slice(0, 2).join(" ") + " failed rc=" + (p.status ?? "signal") +
      (why ? ": " + why : ""),
    );
  }
  return p.stdout;
}
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

async function cf(pathname, { method = "GET", body = null } = {}) {
  const res = await fetch(CF_API + pathname, {
    method,
    headers: {
      authorization: "Bearer " + process.env.CLOUDFLARE_API_TOKEN,
      "content-type": "application/json",
    },
    body: body === null ? undefined : JSON.stringify(body),
  });
  const text = await res.text();
  let json = null;
  try { json = JSON.parse(text); } catch { json = null; }
  return { status: res.status, ok: res.ok, json, result: json && json.result };
}

export async function release() {
  const r = {
    schema: "meridian/zone-b-release-v1", sha: process.env.RELEASE_SHA ?? null,
    status: "BLIND", previous_version_id: null, upload_ok: false, deploy_attempted: false,
    probes: [], rollback_attempted: false, rollback_verified: false, error: null,
    started_at: new Date().toISOString(),
  };
  const out = process.env.RELEASE_RECEIPT_PATH || path.join(process.cwd(), "router-release-receipt.json");
  const wrangler = path.join(ROOT, "node_modules", ".bin", "wrangler");
  let target = "";
  try {
    const sha = requireMainSha(process.env.GITHUB_REF, process.env.RELEASE_SHA, run("git", ["rev-parse", "HEAD"]).trim());
    for (const k of ["CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "MERIDIAN_CLIENT_KEY", "MERIDIAN_ADMIN_KEY"]) {
      if (!process.env[k]) throw new Error("BLIND: missing trusted secret " + k);
    }
    // One zone value, written once. The environment may repeat it; it may never contradict it.
    const configPath = path.join(ROOT, "..", "..", CONFIG_REL);
    const zone = resolveZone(process.env.ESTATE_ZONE || null, fs.readFileSync(configPath, "utf8"));
    target = canonicalRouterUrl(zone);
    r.zone = zone;
    r.target = target;
    if (process.env.MERIDIAN_ROUTER_URL && process.env.MERIDIAN_ROUTER_URL !== target) {
      throw new Error("BLIND: target hostname differs from the canonical Zone B endpoint");
    }
    if (!fs.existsSync(wrangler) || !pinnedWranglerVersion(run(wrangler, ["--version"]))) {
      throw new Error("BLIND: pinned Wrangler 4.131.0 absent");
    }
    // Tests ran in the prior credential-free GitHub step. Never execute npm here.
    const preflight = process.env.RELEASE_PREFLIGHT_FILE;
    if (!preflight || fs.readFileSync(preflight, "utf8").trim() !== sha) {
      throw new Error("BLIND: exact-SHA preflight receipt missing");
    }
    // The prior state is ASKED, not inferred from an exit code. First boot (no deployment at
    // all) is allowed and recorded as bootstrap; an unknown prior state is refused.
    const account = process.env.CLOUDFLARE_ACCOUNT_ID;
    const prior = await cf("/accounts/" + account + "/workers/scripts/" + SCRIPT_NAME + "/deployments");
    let wranglerStatus = "";
    if (prior.status === 200 && Array.isArray(prior.result) && prior.result.length > 0) {
      wranglerStatus = run(wrangler, ["deployments", "status", "--json"]);
    }
    const classified = classifyPriorDeployments(
      { status: prior.status, result: prior.result },
      wranglerStatus,
    );
    r.previous_version_id = classified.version_id;
    r.bootstrap = classified.mode === "bootstrap";
    r.prior_state = classified.reason;
    const tag = immutableTag(sha);
    // DO migrations must not be silently converted to an unversioned initial deploy.
    run(wrangler, ["versions", "upload", "--tag", tag, "--message", "meridian:" + sha,
      "--var", "COMMIT_SHA:" + sha, "--keep-vars", "--strict"]);
    r.upload_ok = true;
    // The Worker authenticates with secrets, not with nothing. They are bound here, once, by
    // name, so the probes can prove a real bearer instead of a 401.
    const secrets = [
      secretPayload("MERIDIAN_CLIENT_KEY", process.env.MERIDIAN_CLIENT_KEY),
      secretPayload("MERIDIAN_ADMIN_KEY", process.env.MERIDIAN_ADMIN_KEY),
    ];
    for (const s of secrets) {
      const put = await cf("/accounts/" + account + "/workers/scripts/" + SCRIPT_NAME + "/secrets", {
        method: "PUT", body: s,
      });
      if (!put.ok || !put.json || put.json.success !== true) {
        throw new Error("BLIND: cloudflare refused the worker secret " + s.name + ": " +
          scrub(put.json && put.json.errors ? put.json.errors[0] && put.json.errors[0].message : put.json));
      }
    }
    r.secrets_bound = secrets.map(s => s.name);
    r.deploy_attempted = true;
    run(wrangler, ["versions", "deploy", "--version-tag", tag + "@100%", "--yes", "--message", "meridian:" + sha]);
    await pause(3000);
    // The hostname is served by the Worker, not by an origin: a Worker route on the zone's
    // hostname is what turns a dead origin (Cloudflare 525) into an answer the estate owns.
    const zoneList = await cf("/zones?name=" + encodeURIComponent(zone));
    const zoneId = zoneList.ok && zoneList.json && zoneList.json.success && Array.isArray(zoneList.result)
      ? (zoneList.result[0] && zoneList.result[0].id) || null
      : null;
    if (!zoneId) throw new Error("BLIND: the zone is not visible to this token: " + scrub(zoneList.json));
    const routes = await cf("/zones/" + zoneId + "/workers/routes");
    const pattern = routePattern(zone);
    const attached = routes.ok && routes.json && routes.json.success && Array.isArray(routes.result)
      ? routes.result.find(x => x && x.pattern === pattern)
      : null;
    r.route_pattern = pattern;
    r.route_script = attached ? attached.script : null;
    if (attached && attached.script !== SCRIPT_NAME) {
      // Ambiguous ownership is refused, never taken over silently.
      throw new Error("BLIND: " + pattern + " is owned by another Worker (" + attached.script + ")");
    }
    if (!attached) {
      // The zone's hostname is served by this Worker and by nothing else: that is what turns a
      // dead origin (Cloudflare 525) into an answer the estate owns, off-host.
      const created = await cf("/zones/" + zoneId + "/workers/routes", {
        method: "POST", body: { pattern, script: SCRIPT_NAME },
      });
      if (!created.ok || !created.json || created.json.success !== true) {
        throw new Error("BLIND: the Worker route " + pattern + " could not be created: " +
          scrub(created.json && created.json.errors ? created.json.errors[0] && created.json.errors[0].message : created.json));
      }
      r.route_created = true;
      await pause(2000);
    }
    r.route_script = SCRIPT_NAME;
    for (let n = 1; n <= 3; n++) {
      run("node", ["scripts/blackbox-prober.mjs"],
        { EXPECTED_COMMIT_SHA: sha, MERIDIAN_ROUTER_URL: target }, 110000, true);
      r.probes.push({ round: n, passed: true, at: new Date().toISOString() });
    }
    r.status = "OPERATIONAL";
  } catch (e) {
    r.status = "NOT_OPERATIONAL";
    r.error = scrub(String(e?.message ?? e));
    if (r.deploy_attempted && r.previous_version_id) {
      r.rollback_attempted = true;
      try {
        run(wrangler, ["rollback", r.previous_version_id, "--message", "restore:" + r.sha]);
        await pause(3000);
        run("node", ["scripts/blackbox-prober.mjs"],
          { EXPECTED_COMMIT_SHA: "", MERIDIAN_ROUTER_URL: target }, 110000, true);
        r.rollback_verified = true;
      } catch (x) {
        r.rollback_error = scrub(String(x?.message ?? x)).slice(0, 160);
      }
    }
  } finally {
    r.finished_at = new Date().toISOString();
    fs.writeFileSync(out, JSON.stringify(r, null, 2) + "\n", { mode: 0o600 });
    console.log(JSON.stringify({
      status: r.status, sha: r.sha, passed_rounds: r.probes.length,
      bootstrap: r.bootstrap ?? null, route: r.route_script ?? null,
      rollback_attempted: r.rollback_attempted, rollback_verified: r.rollback_verified,
    }));
  }
  return r.status === "OPERATIONAL" ? 0 : 1;
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = await release();
}
