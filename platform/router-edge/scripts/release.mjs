#!/usr/bin/env node
// Zone B release adapter. Existing Greenlane is the only source-admission authority.
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

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
export function immutableTag(sha) {
  if (!/^[0-9a-f]{40}$/.test(sha)) throw new Error("BLIND: SHA must be a full commit identifier");
  return "meridian-" + sha;
}
function run(cmd, args, env = {}, timeout = 120000) {
  const p = spawnSync(cmd, args, {
    cwd: ROOT, env: { ...process.env, ...env }, encoding: "utf8", timeout, maxBuffer: 1024 * 1024,
  });
  // Never echo process output: it could contain credentials or provider responses.
  if (p.error || p.status !== 0) throw new Error(path.basename(cmd) + " " + args.slice(0, 2).join(" ") + " failed rc=" + (p.status ?? "signal"));
  return p.stdout;
}
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

export async function release() {
  const r = {
    schema: "meridian/zone-b-release-v1", sha: process.env.RELEASE_SHA ?? null,
    status: "BLIND", previous_version_id: null, upload_ok: false, deploy_attempted: false,
    probes: [], rollback_attempted: false, rollback_verified: false, error: null,
    started_at: new Date().toISOString(),
  };
  const out = process.env.RELEASE_RECEIPT_PATH || path.join(process.cwd(), "router-release-receipt.json");
  const wrangler = path.join(ROOT, "node_modules", ".bin", "wrangler");
  try {
    const sha = requireMainSha(process.env.GITHUB_REF, process.env.RELEASE_SHA, run("git", ["rev-parse", "HEAD"]).trim());
    for (const k of ["CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "MERIDIAN_CLIENT_KEY", "MERIDIAN_ADMIN_KEY"]) {
      if (!process.env[k]) throw new Error("BLIND: missing trusted secret " + k);
    }
    if (process.env.MERIDIAN_ROUTER_URL !== "https://llm.meridianlabs.cloud") {
      throw new Error("BLIND: target hostname differs from canonical Zone B endpoint");
    }
    if (!fs.existsSync(wrangler) || !/^4\.131\.0\b/.test(run(wrangler, ["--version"]).trim())) {
      throw new Error("BLIND: pinned Wrangler 4.131.0 absent");
    }
    // Source + zero-spend falsifiers first; no network mutation until all pass.
    run("npm", ["test"]);
    run("node", ["--test", "tests/release.falsifier.mjs"]);
    // Without a single previously active version, DO migration/bootstrap needs separate explicit authority.
    r.previous_version_id = activeRollbackId(run(wrangler, ["deployments", "status", "--json"]));
    const tag = immutableTag(sha);
    // DO migrations must not be silently converted to an unversioned initial deploy.
    run(wrangler, ["versions", "upload", "--tag", tag, "--message", "meridian:" + sha,
      "--var", "COMMIT_SHA:" + sha, "--keep-vars", "--strict"]);
    r.upload_ok = true;
    r.deploy_attempted = true;
    run(wrangler, ["versions", "deploy", "--version-tag", tag + "@100%", "--yes", "--message", "meridian:" + sha]);
    await pause(3000);
    for (let n = 1; n <= 3; n++) {
      run("node", ["scripts/blackbox-prober.mjs"], { EXPECTED_COMMIT_SHA: sha }, 110000);
      r.probes.push({ round: n, passed: true, at: new Date().toISOString() });
    }
    r.status = "OPERATIONAL";
  } catch (e) {
    r.status = "NOT_OPERATIONAL";
    r.error = String(e?.message ?? e).slice(0, 240);
    if (r.deploy_attempted && r.previous_version_id) {
      r.rollback_attempted = true;
      try {
        run(wrangler, ["rollback", r.previous_version_id, "--message", "restore:" + r.sha]);
        await pause(3000);
        run("node", ["scripts/blackbox-prober.mjs"], { EXPECTED_COMMIT_SHA: "" }, 110000);
        r.rollback_verified = true;
      } catch (x) {
        r.rollback_error = String(x?.message ?? x).slice(0, 160);
      }
    }
  } finally {
    r.finished_at = new Date().toISOString();
    fs.writeFileSync(out, JSON.stringify(r, null, 2) + "\n", { mode: 0o600 });
    console.log(JSON.stringify({
      status: r.status, sha: r.sha, passed_rounds: r.probes.length,
      rollback_attempted: r.rollback_attempted, rollback_verified: r.rollback_verified,
    }));
  }
  return r.status === "OPERATIONAL" ? 0 : 1;
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = await release();
}
