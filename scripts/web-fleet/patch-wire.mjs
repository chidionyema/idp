/** MERIDIAN-PATCH-V1: untrusted model output, schema validation only. */
import { createHash } from 'node:crypto';
const SHA40 = /^[0-9a-f]{40}$/;
const SHA64 = /^[0-9a-f]{64}$/;
const ID = /^[a-zA-Z0-9][a-zA-Z0-9._:-]{1,127}$/;
const ALLOWED = /^(?:platform|tests|scripts|web|bin|catalog)\/[A-Za-z0-9_+./-]+$/;
const DENIED = /(^|\/)(?:\.git|\.github|\.env[^/]*|node_modules|secrets?|private|credentials?)(?:\/|$)|\.(?:pem|key|p12|pfx|age)$/i;
export const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
export function assertPath(path) {
  if (typeof path !== 'string' || path.length > 180 || !ALLOWED.test(path) ||
      path.startsWith('/') || path.includes('\\') || path.includes('//') ||
      path.split('/').includes('..') || path.split('/').includes('.') || DENIED.test(path)) {
    throw new Error('PATH_NOT_ADMITTED');
  }
  return path;
}
export function strictKeys(obj, keys, kind) {
  if (obj === null || typeof obj !== 'object' || Array.isArray(obj) ||
      Object.keys(obj).some(k => !keys.includes(k)) || keys.some(k => !(k in obj))) {
    throw new Error(`${kind}_SCHEMA_INVALID`);
  }
}
export function validatePatch(patch, packet) {
  strictKeys(patch, ['schema','instruction_id','repo','issue','base_sha','agent_label','summary','edits'], 'PATCH');
  if (patch.schema !== 'MERIDIAN-PATCH-V1' || patch.repo !== 'chidionyema/idp' ||
      !Number.isSafeInteger(patch.issue) || patch.issue < 1 || !SHA40.test(patch.base_sha) ||
      !ID.test(patch.instruction_id) || typeof patch.agent_label !== 'string' ||
      patch.agent_label.length > 96 || typeof patch.summary !== 'string' ||
      patch.summary.length > 1000 || !Array.isArray(patch.edits) ||
      patch.edits.length < 1 || patch.edits.length > 2) throw new Error('PATCH_FIELDS_INVALID');
  if (!packet || packet.schema !== 'MERIDIAN-TASK-V2' || packet.state !== 'READY_UNTRUSTED' ||
      patch.issue !== packet.issue.number || patch.base_sha !== packet.source_sha ||
      patch.instruction_id !== packet.instruction_id) throw new Error('STALE_OR_UNBOUND_PACKET');
  const seen = new Set();
  for (const edit of patch.edits) {
    strictKeys(edit, ['path','action','expected_sha256','content','mode'], 'EDIT');
    assertPath(edit.path);
    if (seen.has(edit.path)) throw new Error('DUPLICATE_EDIT_PATH');
    seen.add(edit.path);
    const file = packet.target_files.find(f => f.path === edit.path);
    if (!file || edit.action !== 'update' || edit.mode !== '100644' ||
        !SHA64.test(edit.expected_sha256) || edit.expected_sha256 !== file.sha256 ||
        typeof edit.content !== 'string' || Buffer.byteLength(edit.content) > 20_000) {
      throw new Error('EDIT_SCOPE_OR_BASE_INVALID');
    }
  }
  const digest = sha256(Buffer.from(JSON.stringify(patch)));
  return { verdict:'SCHEMA_VALID_ONLY', authenticated:false, authorised:false,
    applied:false, verified_yield:false, sha256:digest, paths:[...seen] };
}
