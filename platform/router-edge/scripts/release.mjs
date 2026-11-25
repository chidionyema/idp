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
  const lines = redact(text).split(/\r?\n/).map(s => s.trim()).filter(Boolean);
  return (lines.pop() ?? "").slice(0, max);
}
// THE CAUSE IS IN WRANGLER'S OWN LOG FILE (measured 2026-11-25, run 45664064642).
// On a failed upload Wrangler prints one line -- "Logs were written to
// /home/runner/.config/.wrangler/logs/<name>.log" -- and keeps the actual error in that file.
// A receipt that carries only that line names a PATH, not a CAUSE, so the next agent has
// nothing to act on. This reads the newest log file and carries its tail, redacted.
export function wranglerLogDir(env = process.env) {
  return env.WRANGLER_LOG_PATH
    || path.join(env.HOME || "/root", ".config", ".wrangler", "logs");
}
export function wranglerLogTail(dir = wranglerLogDir(), max = 12) {
  let names = [];
  try {
    names = fs.readdirSync(dir);
  } catch {
    return "";
  }
  const files = names
    .filter((n) => n.endsWith(".log"))
    .map((n) => {
      const f = path.join(dir, n);
      let m = 0;
      try { m = fs.statSync(f).mtimeMs; } catch { m = 0; }
      return { f, m };
    })
    .sort((a, b) => b.m - a.m);
  if (!files.length) return "";
  let text = "";
  try {
    text = fs.readFileSync(files[0].f, "utf8");
  } catch {
    return "";
  }
  return redact(text.split(/\r?\n/).map((s) => s.trim()).filter(Boolean).slice(-max).join(" | ")).slice(0, 700);
}
// THE FIRST-BOOT DECISION (founder, 2026-11-25, idp#8416).
// The first release of a worker has no previous version, so `wrangler deployments status` exits
// non-zero. The adapter used to catch EVERY error from that call and call it a first boot: a
// 401, a 403, a timeout, a malformed body and a split deployment all entered the same catch, so
// an authority refusal was indistinguishable from an empty account. Only an INDEPENDENTLY
// VERIFIED zero-deployment state may proceed; everything else is refused by name.
export function firstBootDecision({ status, stdout, verifiedZeroDeployments }) {
  if (status === 0) return { state: "deployed", version_id: activeRollbackId(stdout) };
  if (verifiedZeroDeployments === true) return { state: "first-boot", version_id: null };
  throw new Error(
    "BLIND: no active version and the zero-deployment state is not independently verified; refusing to deploy",
  );
}
// The release must run on a SCOPED token. The root token can see (and mint) everything, so a
// release that runs on it holds no narrow-waist proof at all.
export function assertScopedAuthority(token, rootToken) {
  if (!token) throw new Error("BLIND: release has no Cloudflare token");
  if (rootToken && token === rootToken) {
    throw new Error("REFUSED: the release is holding the Cloudflare root token, not a scoped one");
  }
  return true;
}
// The independent zero-deployment probe. It asks Cloudflare, not the tool that just refused,
// and it distinguishes "this worker was never uploaded" from "this token may not look".
export async function probeZeroDeployments(token, accountId, fetchImpl = fetch, worker = "meridian-router-edge") {
  const head = { Authorization: `Bearer ${token}` };
  const base = `https://api.cloudflare.com/client/v4/accounts/${encodeURIComponent(accountId)}/workers/scripts/${worker}`;
  const res = await fetchImpl(`${base}/deployments`, { headers: head });
  if (res.status === 401 || res.status === 403) {
    throw new Error(`BLIND: the deployments probe was refused (HTTP ${res.status}); first boot is not proven`);
  }
  if (res.status === 404) {
    const script = await fetchImpl(base, { headers: head });
    if (script.status === 404) return { zero: true, evidence: "no worker script exists" };
    if (script.status === 401 || script.status === 403) {
      throw new Error(`BLIND: the script probe was refused (HTTP ${script.status}); first boot is not proven`);
    }
    if (!script.ok) throw new Error(`BLIND: the script probe failed (HTTP ${script.status})`);
    return { zero: true, evidence: "the worker script exists and has no deployments" };
  }
  if (!res.ok) throw new Error(`BLIND: the deployments probe failed (HTTP ${res.status})`);
  const body = await res.json();
  const list = Array.isArray(body?.result) ? body.result : (body?.result?.deployments ?? body?.result?.versions);
  if (!Array.isArray(list)) throw new Error("BLIND: the deployments probe returned no machine-readable list");
  return { zero: list.length === 0, evidence: `deployments=${list.length}` };
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
    const log = path.basename(cmd).startsWith("wrangler") ? wranglerLogTail() : "";
    throw new Error(
      path.basename(cmd) + " " + args.slice(0, 2).join(" ") + " failed rc=" + (p.status ?? "signal")
      + (cause ? ": " + cause : "")
      + (log ? " | wrangler log: " + log : ""),
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
    assertScopedAuthority(process.env.CLOUDFLARE_API_TOKEN, process.env.SEED_CLOUDFLARE_ROOT_TOKEN);
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
    // The deployment state, read TWO ways: the tool's own status, and Cloudflare's answer.
    // A tool that refuses is not evidence of an empty account -- a 401, a 403, a timeout and a
    // malformed body all look the same from the outside -- so the zero-deployment state must be
    // proven independently before the first boot is allowed (founder, 2026-11-25, idp#8416).
    const status = spawnSync(wrangler, ["deployments", "status", "--json"], {
      cwd: ROOT, env: process.env, encoding: "utf8", timeout: 120000, maxBuffer: 1024 * 1024,
    });
    let zero = { zero: false, evidence: "not probed" };
    if (status.status !== 0) {
      zero = await probeZeroDeployments(
        process.env.CLOUDFLARE_API_TOKEN, process.env.CLOUDFLARE_ACCOUNT_ID,
      );
      r.zero_deployment_evidence = zero.evidence;
    }
    const decision = firstBootDecision({
      status: status.status, stdout: status.stdout, verifiedZeroDeployments: zero.zero,
    });
    r.previous_version_id = decision.version_id;
    r.first_boot = decision.state === "first-boot";
    const tag = immutableTag(sha);
    // DO migrations must not be silently converted to an unversioned initial deploy.
    run(wrangler, uploadArgs(sha, tag, Boolean(r.previous_version_id)));
    r.upload_ok = true;
    r.deploy_attempted = true;
    run(wrangler, ["versions", "deploy", "--version-tag", tag + "@100%", "--yes", "--message", "meridian:" + sha]);
    await pause(3000);
    for (let n = 1; n <= 3; n++) {
      run("node", ["scripts/blackbox-prober.mjs"], { EXPECTED_COMMIT_SHA: sha }, 110000, true);
      r.probes.push({ round: n, passed: true, at: new Date().toISOString() });
    }
    r.status = "OPERATIONAL";
  } catch (e) {
    r.status = "NOT_OPERATIONAL";
    r.error = String(e?.message ?? e).slice(0, 900);
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
    } else if (r.deploy_attempted && !r.previous_version_id) {
      // A first boot has nothing to roll back TO. Compensation is the other direction: un-deploy
      // the version that was just put live, so a failed probe does not leave the route serving a
      // build that was proven bad. Deleting is safe (that version serves nothing else) and it is
      // the honest end state: NOT_OPERATIONAL with no live version.
      r.compensation = "delete-unproven-version";
      try {
        const active = spawnSync(wrangler, ["deployments", "status", "--json"], {
          cwd: ROOT, env: process.env, encoding: "utf8", timeout: 120000, maxBuffer: 1024 * 1024,
        });
        if (active.status === 0) {
          const version = activeRollbackId(active.stdout);
          run(wrangler, ["versions", "delete", version, "--force"]);
          r.compensated_version_id = version;
        }
      } catch (x) {
        r.compensation_error = String(x?.message ?? x).slice(0, 400);
      }
    }
  } finally {
    r.finished_at = new Date().toISOString();
    fs.writeFileSync(out, JSON.stringify(r, null, 2) + "\n", { mode: 0o600 });
    console.log(JSON.stringify({
      status: r.status, sha: r.sha, passed_rounds: r.probes.length,
      rollback_attempted: r.rollback_attempted, rollback_verified: r.rollback_verified,
      compensation: r.compensation ?? null, error: r.error ?? null,
    }));
  }
  return r.status === "OPERATIONAL" ? 0 : 1;
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = await release();
}
