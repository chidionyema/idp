/**
 * MERIDIAN-TASK-V1 — deterministic, read-only task hydration for untrusted web agents.
 * No auth, execution, lease minting, GitHub write or outcome certification occurs here.
 * The caller supplies already-fetched, provenance-labelled public GitHub evidence.
 */
const UTF8 = new TextEncoder();
const HEX40 = /^[0-9a-f]{40}$/i;
const HEX64 = /^[0-9a-f]{64}$/i;
const IDENT = /^[A-Za-z0-9][A-Za-z0-9._:-]{1,119}$/;
const PATH = /^[A-Za-z0-9._/-]{1,180}$/;
const PROHIBITED = /(?:-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|github_pat_[A-Za-z0-9_]{12,}|\bgh[pousr]_[A-Za-z0-9]{16,}|\bsk-[A-Za-z0-9_-]{18,}|authorization\s*:\s*(?:bearer|basic)\s+[^\s]+)/i;
const DENY_SEGMENTS = new Set(['.git', '.github', '.githooks', 'node_modules', '.env', 'secrets', '.ssh']);

export class PacketError extends Error {
  constructor(code) { super(code); this.code = code; }
}

function shaValid(value, pattern = HEX40) { return typeof value === 'string' && pattern.test(value); }
function validPath(path) {
  if (typeof path !== 'string' || !PATH.test(path) || path.startsWith('/') || path.endsWith('/') || path.includes('\\')) return false;
  const parts = path.split('/');
  return parts.every((part) => part && part !== '.' && part !== '..' && !DENY_SEGMENTS.has(part.toLowerCase()) && !part.toLowerCase().startsWith('.env'));
}
const bytes = (value) => UTF8.encode(value).length;
async function digest(text) {
  const result = await crypto.subtle.digest('SHA-256', UTF8.encode(text));
  return Array.from(new Uint8Array(result), n => n.toString(16).padStart(2, '0')).join('');
}
async function gitBlobSha(text) {
  const content = UTF8.encode(text);
  const prefix = UTF8.encode('blob ' + content.length + '\0');
  const wire = new Uint8Array(prefix.length + content.length);
  wire.set(prefix);
  wire.set(content, prefix.length);
  const result = await crypto.subtle.digest('SHA-1', wire);
  return Array.from(new Uint8Array(result), n => n.toString(16).padStart(2, '0')).join('');
}
function requiredId(value, code) {
  if (typeof value !== 'string' || !IDENT.test(value)) throw new PacketError(code);
  return value;
}
function checkedSource(value) {
  if (typeof value !== 'string' || value.includes('\u0000') || PROHIBITED.test(value)) throw new PacketError('SENSITIVE_OR_INVALID_SOURCE');
  return value;
}

/** Precondition: caller has independently fetched file bytes from public IDP at sourceSha. */
export async function hydrateTask({ taskId, instructionId, issue, sourceSha, files, ci = null, acceptance, owner, checkpoint = null }) {
  const tid = requiredId(taskId, 'INVALID_TASK_ID');
  const iid = requiredId(instructionId, 'INVALID_INSTRUCTION_ID');
  const actor = requiredId(owner, 'UNATTRIBUTED_OWNER');
  if (!Number.isInteger(issue) || issue <= 0) throw new PacketError('INVALID_ISSUE');
  if (!shaValid(sourceSha)) throw new PacketError('SOURCE_SHA_UNKNOWN');
  if (!Array.isArray(files) || files.length === 0 || files.length > 3) throw new PacketError('INVALID_SOURCE_FILE_COUNT');
  if (typeof acceptance !== 'string' || !acceptance.trim() || bytes(acceptance) > 1200) throw new PacketError('ACCEPTANCE_MISSING_OR_OVERSIZE');
  if (PROHIBITED.test(acceptance)) throw new PacketError('SENSITIVE_ACCEPTANCE');
  const seen = new Set(), sources = [];
  for (const file of files) {
    const path = file?.path;
    if (!validPath(path)) throw new PacketError('UNSAFE_SOURCE_PATH');
    if (seen.has(path)) throw new PacketError('DUPLICATE_SOURCE_PATH');
    seen.add(path);
    if (!shaValid(file.blobSha) || !['100644', '100755'].includes(file.mode)) throw new PacketError('SOURCE_PROVENANCE_OR_MODE_UNKNOWN');
    const content = checkedSource(file.content);
    if (bytes(content) > 8500) throw new PacketError('SOURCE_FILE_TOO_LARGE');
    const contentSha256 = await digest(content);
    if (file.blobSha.toLowerCase() !== await gitBlobSha(content)) throw new PacketError('SOURCE_BLOB_DIGEST_MISMATCH');
    if (!shaValid(file.sha256, HEX64) || file.sha256.toLowerCase() !== contentSha256) throw new PacketError('SOURCE_CONTENT_DIGEST_MISMATCH');
    sources.push({ path, git_blob_sha: file.blobSha.toLowerCase(), content_sha256: contentSha256, source_mode: file.mode, bytes: bytes(content), content });
  }
  let failure = null;
  if (ci !== null) {
    if (!Number.isInteger(ci.runId) || ci.runId <= 0 || ci.sourceSha !== sourceSha || !Array.isArray(ci.lines)) throw new PacketError('CI_PROVENANCE_UNKNOWN');
    const lines = ci.lines.filter(x => typeof x === 'string').slice(0, 12).map(x => x.replace(/\x1b\[[0-9;]*m/g, '').slice(0, 240));
    if (lines.some(line => PROHIBITED.test(line))) throw new PacketError('SENSITIVE_CI_OUTPUT');
    failure = { run_id: ci.runId, source_sha: ci.sourceSha, failed_lines: lines, time_precision: 'SOURCE_UNVERIFIED_OR_SECONDS_ONLY', source_url: 'https://github.com/chidionyema/idp/actions/runs/' + ci.runId };
  }
  if (checkpoint !== null && (
    !checkpoint || typeof checkpoint !== 'object' ||
    typeof checkpoint.state !== 'string' ||
    !['READY', 'LEASED', 'BLOCKED', 'UNKNOWN'].includes(checkpoint.state) ||
    typeof checkpoint.lease !== 'string' || bytes(checkpoint.lease) > 100 ||
    PROHIBITED.test(JSON.stringify(checkpoint))
  )) throw new PacketError('UNTRUSTED_CHECKPOINT');
  const payload = {
    schema: 'MERIDIAN-TASK-V1', task_id: tid, root_instruction_id: iid, issue,
    source_repo: 'chidionyema/idp', source_sha: sourceSha.toLowerCase(),
    source_files: sources, acceptance, owner: actor,
    checkpoint: checkpoint === null ? { state: 'UNKNOWN', lease: 'UNOBSERVED' } : checkpoint,
    failure, requested_result: { schema: 'MERIDIAN-PATCH-V1', authority: 'DATA_ONLY_UNTRUSTED', preseal: 'PINNED_RUFF_REGISTRY_TESTS_REQUIRED' },
    clock: { wall_clock_accuracy: 'UNVERIFIED', causal_edges: 'NOT_INFERRED_FROM_TIMESTAMPS' },
  };
  const canonical = JSON.stringify(payload);
  if (bytes(canonical) > 12288) throw new PacketError('PACKET_TOO_LARGE');
  const envelope = { ...payload, payload_sha256: await digest(canonical) };
  if (bytes(JSON.stringify(envelope)) > 12288) throw new PacketError('PACKET_TOO_LARGE');
  return envelope;
}

/** Untrusted patch suggestions are never READY, even if hashes and syntax are valid. */
export async function validateProposal(packet, proposal) {
  if (!packet || packet.schema !== 'MERIDIAN-TASK-V1' || !shaValid(packet.payload_sha256, HEX64)) throw new PacketError('INVALID_PACKET');
  const { payload_sha256: expected, ...unsigned } = packet;
  if (await digest(JSON.stringify(unsigned)) !== expected) throw new PacketError('PACKET_TAMPERED');
  if (!proposal || proposal.schema !== 'MERIDIAN-PATCH-V1' || proposal.task_id !== packet.task_id || proposal.base_sha !== packet.source_sha) throw new PacketError('STALE_OR_UNBOUND_PROPOSAL');
  if (!Array.isArray(proposal.files) || !proposal.files.length || proposal.files.length > 3) throw new PacketError('INVALID_PATCH_FILES');
  const permitted = new Map(packet.source_files.map(f => [f.path, f]));
  const unique = new Set();
  for (const file of proposal.files) {
    if (!validPath(file?.path) || !permitted.has(file.path)) throw new PacketError('UNAUTHORISED_PATCH_PATH');
    if (unique.has(file.path)) throw new PacketError('DUPLICATE_PATCH_PATH');
    unique.add(file.path);
    const original = permitted.get(file.path);
    if (file.mode !== original.source_mode) throw new PacketError('EXECUTABLE_MODE_CHANGED');
    const content = checkedSource(file.content);
    if (bytes(content) > 8500 || !shaValid(file.sha256, HEX64) || file.sha256.toLowerCase() !== await digest(content)) throw new PacketError('PATCH_CONTENT_INVALID');
  }
  return { status: 'PROPOSED_UNTRUSTED', needs: ['TRUSTED_PRESEAL_CANONICALISATION', 'SCOPE_AND_IDENTITY_CHECK', 'EXACT_SHA_BUILD', 'INDEPENDENT_EFFECT_READBACK'], files: unique.size, task_id: packet.task_id };
}

export const policy = Object.freeze({ validPath, digest, maxBytes: 12288 });
