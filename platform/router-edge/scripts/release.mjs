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
  return lines.slice(-3).join(" / ").slice(0, max);
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
    throw new Error(
      path.basename(cmd) + " " + args.slice(0, 2).join(" ") + " failed rc=" + (p.status ?? "signal")
      + (cause ? ": " + cause : ""),
    );
  }
  return p.stdout;
}
// `--keep-vars` retains the vars of the PREVIOUS deployment. On a worker with no
// deployment there is nothing to keep and Wrangler refuses the upload, so first boot
// uploads without it (I-8455 Stage 1, founder waiver 2026-11-25).
export function uploadArgs(sha, tag, hasPreviousVersion) {
  const args = [
    "versions", "upload", "--tag", tag, "--message", "meridian:" + sha,
    "--var", "COMMIT_SHA:" + sha,
  ];
  if (hasPreviousVersion) args.push("--keep-vars");
  args.push("--strict");
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
    // DO migrations must not be silently converted to an unversioned initial deploy.
    // Cloudflare refuses a Durable Object class creation from `versions upload`:
    // "any change that creates, deletes, renames, or transfers a Durable Object class
    // must be applied through wrangler deploy" (Workers docs, deployment management).
    // wrangler.toml declares new_sqlite_classes v1, so first boot IS that change.
    if (r.previous_version_id === null) {
      run(wrangler, firstBootDeployArgs(sha, tag));
    } else {
      run(wrangler, uploadArgs(sha, tag, true));
      r.upload_ok = true;
      run(wrangler, ["versions", "deploy", "--version-tag", tag + "@100%", "--yes", "--message", "meridian:" + sha]);
    }
    r.deploy_attempted = true;
    await pause(3000);
    for (let n = 1; n <= 3; n++) {
      run("node", ["scripts/blackbox-prober.mjs"], { EXPECTED_COMMIT_SHA: sha }, 110000, true);
      r.probes.push({ round: n, passed: true, at: new Date().toISOString() });
    }
    r.status = "OPERATIONAL";
  } catch (e) {
    r.status = "NOT_OPERATIONAL";
    r.error = String(e?.message ?? e).slice(0, 400);
    if (r.deploy_attempted && r.previous_version_id) {
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
