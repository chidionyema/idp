/**
 * AI Studio origin is untrusted. Only source proposals enter the existing
 * submit-gate; no public/private source or protected file may escape this fence.
 * Pure Cloudflare-compatible logic: no GitHub/token/network access.
 */
export const SUBMIT_REF = "submit/aistudio-auto-intake";
export const MAX_FILES = 8;
export const MAX_FILE_BYTES = 32 * 1024;
export const MAX_TOTAL_BYTES = 96 * 1024;

const ROOTS = new Set(["src", "tests", "packages", "platform", "docs", "bin", "scripts"]);
const DENIED = new Set([
  ".git", ".github", ".githooks", ".ssh", ".env", "node_modules",
  "secrets", "secret", "credentials", "credential", "private", ".vault",
]);
const SECRET_SUFFIX = /\.(?:pem|key|p12|pfx|age|kdbx|sqlite|db|env)(?:\.[^/]*)?$/i;
const PRIVATE_TOKEN = /(?:-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|github_pat_[A-Za-z0-9_]{12,}|\bgh[pousr]_[A-Za-z0-9]{16,}|\bsk-[A-Za-z0-9_-]{18,}|authorization\s*:\s*(?:bearer|basic)\s+\S+)/i;
const HEX40 = /^[a-f0-9]{40}$/i;

export function safeSourcePath(path) {
  if (typeof path !== "string" || path.length > 180 || path.startsWith("/") ||
      path.includes("\\") || !/^[a-zA-Z0-9._/-]+$/.test(path) || SECRET_SUFFIX.test(path)) {
    return false;
  }
  const parts = path.split("/");
  if (!ROOTS.has(parts[0]) || parts.length < 2) return false;
  return parts.every((p) => p !== "" && p !== "." && p !== ".." &&
    !DENIED.has(p.toLowerCase()) && !p.toLowerCase().startsWith(".env"));
}

export function validateFiles(files) {
  if (!Array.isArray(files) || files.length === 0 || files.length > MAX_FILES) {
    throw new Error("FILE_COUNT_NOT_ADMITTED");
  }
  let total = 0;
  const paths = new Set();
  for (const file of files) {
    if (!safeSourcePath(file?.path)) throw new Error("UNTRUSTED_PATH_REFUSED");
    if (paths.has(file.path)) throw new Error("DUPLICATE_PATH_REFUSED");
    paths.add(file.path);
    if (!(file.bytes instanceof Uint8Array) || file.bytes.length > MAX_FILE_BYTES) {
      throw new Error("UNTRUSTED_BYTES_REFUSED");
    }
    total += file.bytes.length;
    if (total > MAX_TOTAL_BYTES) throw new Error("TOTAL_BYTES_REFUSED");
    let text;
    try { text = new TextDecoder("utf-8", { fatal: true }).decode(file.bytes); }
    catch { throw new Error("BINARY_SOURCE_REFUSED"); }
    if (text.includes("\0") || PRIVATE_TOKEN.test(text)) throw new Error("SENSITIVE_SOURCE_REFUSED");
  }
  return true;
}

/** GitHub tree uses Git blob SHA-1, NOT the source's SHA-256 digest. */
export async function gitBlobSha(bytes) {
  if (!(bytes instanceof Uint8Array)) throw new Error("INVALID_BYTES");
  const header = new TextEncoder().encode("blob " + bytes.length + "\0");
  const blob = new Uint8Array(header.length + bytes.length);
  blob.set(header);
  blob.set(bytes, header.length);
  const digest = await crypto.subtle.digest("SHA-1", blob);
  return [...new Uint8Array(digest)].map((v) => v.toString(16).padStart(2, "0")).join("");
}

/** Existing files never lose their executable mode; symlink/submodule refused. */
export function admittedMode(treeEntry) {
  if (!treeEntry) return "100644";
  if (treeEntry.type !== "blob" || !["100644", "100755"].includes(treeEntry.mode)) {
    throw new Error("EXISTING_FILE_MODE_REFUSED");
  }
  return treeEntry.mode;
}

export function admittedBase(submitHead, mainHead) {
  if (submitHead !== null && !HEX40.test(submitHead)) throw new Error("INVALID_SUBMIT_HEAD");
  if (!HEX40.test(mainHead)) throw new Error("MAIN_SHA_UNVERIFIED");
  return submitHead || mainHead;
}

export function submissionReceipt({ commit, deduped = false }) {
  if (!HEX40.test(commit)) throw new Error("MISSING_COMMIT_RECEIPT");
  return {
    phase: "SUBMIT_SOURCE_ONLY",
    commit,
    submit_ref: SUBMIT_REF,
    gate_verified: false,
    greenlane_landed: false,
    operational_yield: false,
    deduped,
  };
}


/**
 * A browser-provided public label is never permission to publish. The only
 * authority this projection consumes is a server-held, already-reviewed release
 * manifest installed by the trusted estate. The manifest cannot be injected via
 * JSON request, userscript, model or Drive payload. Absent/mismatched manifest
 * means HOLD; private source must use private quarantine instead.
 * This release predicate is a protective interlock, not a replacement for QUAD.
 */
export function requirePublicSourceRelease(accepted, env, mainHead) {
  const raw = env?.AI_STUDIO_PUBLIC_RELEASE_MANIFEST_JSON;
  if (typeof raw !== "string" || !raw || raw.length > 8192) {
    throw new Error("PUBLIC_SOURCE_RELEASE_NOT_CONFIGURED");
  }
  let release;
  try { release = JSON.parse(raw); }
  catch { throw new Error("PUBLIC_SOURCE_RELEASE_INVALID"); }
  if (!release || release.schema !== "MERIDIAN-PUBLIC-RELEASE-V1" ||
      release.repo !== "chidionyema/idp" ||
      release.source_sha !== mainHead ||
      !HEX40.test(mainHead) ||
      !Number.isSafeInteger(release.issue) || release.issue <= 0 ||
      typeof release.instruction_id !== "string" ||
      !/^[A-Za-z0-9][A-Za-z0-9._:-]{1,119}$/.test(release.instruction_id) ||
      !Array.isArray(release.files) || release.files.length !== accepted.length ||
      release.files.length === 0 || release.files.length > MAX_FILES) {
    throw new Error("PUBLIC_SOURCE_RELEASE_INVALID");
  }
  const seen = new Set();
  const permitted = new Map();
  for (const entry of release.files) {
    if (!safeSourcePath(entry?.path) || seen.has(entry.path) ||
        typeof entry.sha256 !== "string" || !/^[a-f0-9]{64}$/i.test(entry.sha256) ||
        !Number.isSafeInteger(entry.bytes) || entry.bytes < 0) {
      throw new Error("PUBLIC_SOURCE_RELEASE_INVALID");
    }
    seen.add(entry.path);
    permitted.set(entry.path, entry);
  }
  for (const file of accepted) {
    const entry = permitted.get(file.path);
    if (!entry || entry.sha256 !== file.sha || entry.bytes !== file.bytes) {
      throw new Error("UNREVIEWED_PUBLIC_SOURCE_REFUSED");
    }
  }
  return { public_release_source: "TRUSTED_SERVER_CONFIGURATION", issue: release.issue,
    instruction_id: release.instruction_id, source_sha: release.source_sha };
}
