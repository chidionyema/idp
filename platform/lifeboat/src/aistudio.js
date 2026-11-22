// I-8096-REV2: zero-click AI Studio -> fleet ingestion.
//
// The design law this file keeps: the worker is the only place the two capture channels meet,
// so a browser stream frame and a Google Drive push resolve to one commit keyed by
// (path, sha256). No Mac filesystem, no download prompt, no "Save to GitHub" click.
//
// The intake rule 59effb8f4 is enforced here rather than trusted upstream: the bytes that land
// are hashed again at the edge and a declared digest that disagrees is a partial flush, refused.

import { SUBMIT_REF, safeSourcePath, validateFiles, gitBlobSha, admittedMode, admittedBase, submissionReceipt, requirePublicSourceRelease } from "./aistudio-fence.js";

export const REPO = "chidionyema/idp";
export const LANE = SUBMIT_REF; // The producer MUST enter the trusted submit/** pre-gate.
export const INTAKE_RULE = "59effb8f4";
export const OMNIFLOW_ISSUE = 8133;
export const INTAKE_PATH = "/api/ingest/stream";
export const DRIVE_PATH = "/api/ingest/drive-webhook";

const MOCK_FIXTURES = [
  "generalPurposePersonaData.ts",
  "physicalEstateData.ts",
  "INITIAL_SPECIALIST_FLEET",
];


export class IngestError extends Error {
  constructor(status, code, detail = {}) {
    super(code);
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function bearer(request) {
  const h = request.headers.get("authorization") || "";
  return h.startsWith("Bearer ") ? h.slice(7) : "";
}

function bytesToB64(bytes) {
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}

export function b64ToBytes(b64) {
  if (typeof b64 !== "string" || b64.length === 0) throw new Error("empty");
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i += 1) out[i] = bin.charCodeAt(i);
  return out;
}

export async function sha256Hex(bytes) {
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export function unsafePath(path) {
  return !safeSourcePath(path);
}

export function isMockFixture(path) {
  return MOCK_FIXTURES.some((needle) => path.includes(needle));
}

export async function prepare(files) {
  const accepted = [];
  const sanitized = [];
  const rejected = [];
  const seen = new Set();

  for (const file of files) {
    const path = file?.path;
    if (unsafePath(path)) {
      rejected.push({ path: path ?? null, reason: "UNSAFE_PATH" });
      continue;
    }
    if (isMockFixture(path)) {
      sanitized.push({ path, reason: "MOCK_FIXTURE" });
      continue;
    }

    let bytes;
    try {
      bytes = b64ToBytes(file.content_b64);
    } catch {
      rejected.push({ path, reason: "BAD_BASE64" });
      continue;
    }

    const sha = await sha256Hex(bytes);
    if (typeof file.sha256 !== "string" || file.sha256 !== sha) {
      rejected.push({ path, reason: "PARTIAL_FLUSH_DIGEST" });
      continue;
    }
    if (!Number.isSafeInteger(file.bytes) || file.bytes !== bytes.length) {
      rejected.push({ path, reason: "PARTIAL_FLUSH_LENGTH" });
      continue;
    }

    const key = `${path}:${sha}`;
    if (seen.has(key)) {
      sanitized.push({ path, reason: "DUPLICATE_IN_PAYLOAD" });
      continue;
    }
    seen.add(key);
    accepted.push({ path, sha, bytes: bytes.length, content_b64: bytesToB64(bytes), git_blob_sha: await gitBlobSha(bytes) });
  }

  return { accepted, sanitized, rejected };
}

function token(env) {
  return env.OMNIFLOW_GH_TOKEN || env.GITHUB_TOKEN || "";
}

async function gh(fetchImpl, env, path, init = {}) {
  const ghToken = token(env);
  if (!ghToken) throw new IngestError(503, "GH_TOKEN_ABSENT");
  const res = await fetchImpl(`https://api.github.com${path}`, {
    ...init,
    headers: {
      authorization: `Bearer ${ghToken}`,
      accept: "application/vnd.github+json",
      "content-type": "application/json",
      "user-agent": "genesis-aistudio-ingest",
      ...(init.headers || {}),
    },
  });
  const text = await res.text();
  let body = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }
  if (!res.ok) {
    if (res.status === 404 && init.allow404) return null;
    throw new IngestError(502, "GITHUB_API", { path, status: res.status, body });
  }
  return body;
}

async function laneHead(fetchImpl, env) {
  const ref = await gh(fetchImpl, env, `/repos/${REPO}/git/ref/heads/${LANE}`, {
    allow404: true,
  });
  return ref?.object?.sha || null;
}

async function trustedMainHead(fetchImpl, env) {
  const ref = await gh(fetchImpl, env, `/repos/${REPO}/git/ref/heads/main`);
  return ref?.object?.sha || null;
}

async function laneTree(fetchImpl, env, head) {
  const commit = await gh(fetchImpl, env, `/repos/${REPO}/git/commits/${head}`);
  const tree = await gh(fetchImpl, env, `/repos/${REPO}/git/trees/${commit.tree.sha}?recursive=1`);
  if (tree.truncated) throw new IngestError(409, "TRUNCATED_SOURCE_TREE");
  const files = new Map();
  for (const entry of tree.tree || []) {
    files.set(entry.path, { sha: entry.sha, mode: entry.mode, type: entry.type });
  }
  return { sha: commit.tree.sha, files };
}

async function commitFiles(fetchImpl, env, accepted, base) {
  // Guard ALL modes before a single write-capable GitHub POST.
  const staged = accepted.map((file) => ({
    ...file,
    mode: admittedMode(base.files.get(file.path)),
  }));
  const blobs = [];
  for (const file of staged) {
    const blob = await gh(fetchImpl, env, `/repos/${REPO}/git/blobs`, {
      method: "POST",
      body: JSON.stringify({ content: file.content_b64, encoding: "base64" }),
    });
    if (blob?.sha !== file.git_blob_sha) throw new IngestError(409, "GITHUB_BLOB_SHA_MISMATCH");
    blobs.push({ path: file.path, mode: file.mode, type: "blob", sha: blob.sha });
  }

  const tree = await gh(fetchImpl, env, `/repos/${REPO}/git/trees`, {
    method: "POST",
    body: JSON.stringify(base.sha ? { base_tree: base.sha, tree: blobs } : { tree: blobs }),
  });

  const commit = await gh(fetchImpl, env, `/repos/${REPO}/git/commits`, {
    method: "POST",
    body: JSON.stringify({
      message: `feat(aistudio): untrusted source through submit gate (${INTAKE_RULE})\n\nClaim: chidionyema/idp#7760\nAgent: aistudio-browser-untrusted\n\nNo source is self-certified by this commit.`,
      tree: tree.sha,
      parents: base.head ? [base.head] : [],
    }),
  });

  if (base.submitHead) {
    await gh(fetchImpl, env, `/repos/${REPO}/git/refs/heads/${LANE}`, {
      method: "PATCH",
      body: JSON.stringify({ sha: commit.sha, force: false }),
    });
  } else {
    await gh(fetchImpl, env, `/repos/${REPO}/git/refs`, {
      method: "POST",
      body: JSON.stringify({ ref: `refs/heads/${LANE}`, sha: commit.sha }),
    });
  }
  return { commit: commit.sha, tree: tree.sha };
}

async function announce(_fetchImpl, _env, _packet) {
  // Submit branch push wakes the existing trusted submit-gate automatically.
  // Neither an untrusted browser nor an optional OMNIFLOW URL may promote
  // source or dispatch Greenlane before the fast-gate signs the exact SHA.
  return { submit_gate_on_push: true, promotion: "NOT_OBSERVED" };
}

async function broadcast(fetchImpl, env, packet) {
  const url = env.GENESIS_REALTIME_URL || "";
  if (!url) return { skipped: "GENESIS_REALTIME_URL absent" };
  const res = await fetchImpl(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ type: "chronicle.aistudio_ready", ...packet }),
  });
  if (!res.ok) throw new IngestError(502, "REALTIME_BROADCAST", { status: res.status });
  return { posted: true };
}

async function commentAssignment(fetchImpl, env, packet) {
  await gh(fetchImpl, env, `/repos/${REPO}/issues/${OMNIFLOW_ISSUE}/comments`, {
    method: "POST",
    body: JSON.stringify({
      body: `OMNIFLOW-EVENT/v1\n\`\`\`json\n${JSON.stringify(packet)}\n\`\`\``,
    }),
  });
}

export async function ingest(payload, env = {}, fetchImpl = fetch) {
  const source = payload?.source === "drive" ? "drive" : "stream";
  const files = Array.isArray(payload?.files) ? payload.files : [];
  if (files.length === 0) throw new IngestError(422, "NO_FILES");

  const prepared = await prepare(files);
  if (prepared.rejected.length > 0) {
    throw new IngestError(409, "PARTIAL_FLUSH_REJECTED", prepared.rejected);
  }
  if (prepared.accepted.length === 0) {
    throw new IngestError(422, "NO_SOURCE_AFTER_SANITIZE", prepared.sanitized);
  }

  try {
    validateFiles(prepared.accepted.map((file) => ({
      path: file.path,
      bytes: b64ToBytes(file.content_b64),
    })));
  } catch (error) {
    throw new IngestError(409, "UNTRUSTED_SOURCE_REFUSED", { reason: String(error.message) });
  }

  // Read-only verification first; no browser source reaches public Git objects
  // without a matching server-held, task-bound public-release manifest.
  const mainHead = await trustedMainHead(fetchImpl, env);
  let release;
  try { release = requirePublicSourceRelease(prepared.accepted, env, mainHead); }
  catch (error) {
    throw new IngestError(409, "PUBLIC_SOURCE_RELEASE_HELD", { reason: String(error.message) });
  }
  const submitHead = await laneHead(fetchImpl, env);
  const parentHead = admittedBase(submitHead, mainHead);
  const base = await laneTree(fetchImpl, env, parentHead);
  const unchanged =
    submitHead !== null &&
    prepared.accepted.every((file) => base.files.get(file.path)?.sha === file.git_blob_sha);

  let commit = parentHead;
  let tree = base.sha;
  if (!unchanged) {
    const landed = await commitFiles(fetchImpl, env, prepared.accepted, { ...base, head: parentHead, submitHead });
    commit = landed.commit;
    tree = landed.tree;
  }

  const manifest = prepared.accepted.map((file) => ({
    path: file.path,
    sha256: file.sha,
    git_blob_sha: file.git_blob_sha,
    mode: admittedMode(base.files.get(file.path)),
    bytes: file.bytes,
  }));
  const packet = {
    kind: "SOURCE_PROPOSED",
    mission: "aistudio-preseal",
    source,
    repo: REPO,
    lane: LANE,
    commit,
    deduped: unchanged,
    intake_rule: INTAKE_RULE,
    release: { issue: release.issue, instruction_id: release.instruction_id },
    files: manifest,
  };

  await commentAssignment(fetchImpl, env, packet);
  const broadcastResult = await broadcast(fetchImpl, env, packet);
  const dispatch = await announce(fetchImpl, env, packet);

  return {
    ok: true,
    source,
    repo: REPO,
    lane: LANE,
    deduped: unchanged,
    commit,
    tree,
    intake_rule: INTAKE_RULE,
    release: { issue: release.issue, instruction_id: release.instruction_id },
    files: manifest,
    sanitized: prepared.sanitized,
    omniflow: { issue: OMNIFLOW_ISSUE, event: "OMNIFLOW-EVENT/v1", kind: "ASSIGN" },
    broadcast: broadcastResult,
    dispatch,
    custody: submissionReceipt({ commit, deduped: unchanged }),
  };
}

export async function handleIngest(request, env = {}, fetchImpl = fetch) {
  if (request.method !== "POST") return json({ ok: false, error: "METHOD_NOT_ALLOWED" }, 405);

  const secret = env.AI_STUDIO_INGEST_SECRET || "";
  if (!secret) return json({ ok: false, error: "INGEST_SECRET_ABSENT" }, 503);

  const presented = request.headers.get("x-genesis-ingest-token") || bearer(request);
  if (presented !== secret) return json({ ok: false, error: "UNAUTHORIZED" }, 401);

  const path = new URL(request.url).pathname;
  if (path === DRIVE_PATH) {
    const state = request.headers.get("x-goog-resource-state") || "";
    if (state === "sync") return json({ ok: true, sync: true });
    if ((request.headers.get("x-goog-channel-token") || "") !== secret) {
      return json({ ok: false, error: "UNAUTHORIZED" }, 401);
    }
  }

  let payload;
  try {
    payload = await request.json();
  } catch {
    return json({ ok: false, error: "BAD_JSON" }, 400);
  }

  try {
    return json(await ingest(payload, env, fetchImpl));
  } catch (error) {
    if (error instanceof IngestError) {
      return json({ ok: false, error: error.code, detail: error.detail }, error.status);
    }
    return json({ ok: false, error: "INTERNAL", detail: String(error?.message || error) }, 500);
  }
}
