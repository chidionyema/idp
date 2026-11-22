/**
 * Compatibility door for the one authoritative, data-only MERIDIAN-PATCH-V1
 * validator in platform/lifeboat/src/task-packet.js.
 * The obsolete MERIDIAN-TASK-V2 schema is NOT accepted or independently judged.
 * No authenticated admission, GitHub write or independent verification occurs.
 */
import { createHash } from 'node:crypto';
import { validateProposal, PacketError } from '../../platform/lifeboat/src/task-packet.js';

// Retained small helpers for existing read-only clients; neither grants policy.
export const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
export function strictKeys(obj, keys, kind) {
  if (obj === null || typeof obj !== 'object' || Array.isArray(obj) ||
      Object.keys(obj).some(k => !keys.includes(k)) || keys.some(k => !(k in obj))) {
    throw new PacketError(`${kind}_SCHEMA_INVALID`);
  }
}
export function assertPath(path) {
  if (typeof path !== 'string' || path.length > 180 || path.startsWith('/') ||
      path.includes('\\') || path.includes('//') ||
      path.split('/').some(seg => !seg || seg === '.' || seg === '..' ||
        ['.git', '.github', '.githooks', 'node_modules', '.ssh', 'secrets', 'credentials'].includes(seg.toLowerCase()) ||
        seg.toLowerCase().startsWith('.env')) ||
      !/^[A-Za-z0-9._+@/-]+$/.test(path)) {
    throw new PacketError('PATH_NOT_ADMITTED');
  }
  return path;
}
export { validateProposal, PacketError };

export async function validatePatch(proposal, packet) {
  if (packet?.schema !== 'MERIDIAN-TASK-V1') {
    throw new PacketError('LEGACY_V2_SUPERSEDED');
  }
  // One canonical payload digest and base/issue/path/mode check, not a second
  // validator that can disagree about what counts as ready.
  return validateProposal(packet, proposal);
}
