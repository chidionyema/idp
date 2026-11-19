export const FRAME_BYTE_LENGTH = 64;

export const VERDICT_FLAG_SEALED = 1 << 0; // 0x01
export const VERDICT_FLAG_ZERO_POLL_OK = 1 << 1; // 0x02
export const VERDICT_FLAG_DIGEST_BOUND = 1 << 2; // 0x04
export const VERDICT_FLAG_FAULT = 1 << 3; // 0x08

export type AuraStratum = 0 | 1 | 2 | 3; // Z0_Orbital, Z1_Swarm, Z2_Forensic, Z3_Silicon

export interface AuraEntityDescriptor {
  entityId: number;
  slug: string;
  label: string;
  repo: 'idp' | 'argon' | 'crew' | 'estate-graph' | 'proxy-4001';
  stratum: AuraStratum;
  causalParentId: number;
  x: number;
  y: number;
  cpuSaturationPct: number;
  ramMb: number;
  lawI11ElapsedSec: number;
  opcode: number;
  digestBound: boolean;
  digestShortCopyFault: boolean;
  zeroPollViolation: boolean;
  sealed: boolean;
  latencyUs: number;
  tokPerSec: number;
  upstreamPool?: 'minimax' | 'zai' | 'kimi';
}

export interface DecodedGenesisAtomicFrame {
  timestampNs: bigint;
  traceMerkleRoot: string;
  entityId: number;
  causalParentId: number;
  metricPrimary: number;
  metricSecondary: number;
  syscallOrOpcode: number;
  stratum: AuraStratum;
  verdictFlags: number;
  payloadPreview: string;
}

export interface SerializedAtomicFrame extends Omit<DecodedGenesisAtomicFrame, 'timestampNs'> {
  timestampNs: string;
}

export interface SovereignVerdictCard {
  id: string;
  timestampIso: string;
  intentParsed: string;
  confidenceScore: number;
  chosenLane: string;
  verdict: 'ALLOW_SEALED' | 'DEFLECT_429_FAILOVER' | 'SEVER_LAW_I11' | 'SHATTER_SHORT_COPY';
  traceMerkleRoot: string;
}

export interface CounterfactualForkBranch {
  forkId: string;
  parentRewindSec: number;
  upstreamOverride: 'minimax' | 'zai' | 'kimi';
  overrideIntent: string;
  historicalLatencyMs: number;
  forkLatencyMs: number;
  historicalCostUsd: number;
  forkCostUsd: number;
  gateVerdict: 'PASS_SHADOW_GATE' | 'DEFLECTED';
  createdAt: string;
}

export interface SiliconSpectrogramRow {
  frameLabel: string;
  syscall: string;
  heapDeltaKb: number;
  epollWaitUs: number;
  hotPct: number;
}

export interface AuraManifoldSnapshot {
  generatedAt: string;
  provenanceNotice: string;
  frameByteSize: 64;
  frameCount: number;
  framesBase64: string;
  entities: AuraEntityDescriptor[];
  verdictCards: SovereignVerdictCard[];
  activeForks: CounterfactualForkBranch[];
  isolatedLane: string | null;
  activeRewindSec: number;
  zeroPollShieldIntact: boolean;
  upstreamPoolPressure: {
    minimax: { pressure: number; status429: boolean };
    zai: { pressure: number; status429: boolean };
    kimi: { pressure: number; status429: boolean };
  };
  siliconMatrix: SiliconSpectrogramRow[];
  decodedSample: SerializedAtomicFrame[];
}

export function deterministicEntityHash(slug: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < slug.length; i++) {
    h ^= slug.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

export function encodeGenesisAtomicFrame(
  frame: DecodedGenesisAtomicFrame
): ArrayBuffer {
  const buf = new ArrayBuffer(FRAME_BYTE_LENGTH);
  const view = new DataView(buf);

  view.setBigUint64(0, frame.timestampNs, true);
  const rootBig = BigInt(`0x${frame.traceMerkleRoot.replace(/[^0-9a-fA-F]/g, '').slice(0, 16) || '0'}`);
  view.setBigUint64(8, rootBig, true);
  view.setUint32(16, frame.entityId >>> 0, true);
  view.setUint32(20, frame.causalParentId >>> 0, true);
  view.setFloat32(24, frame.metricPrimary, true);
  view.setFloat32(28, frame.metricSecondary, true);
  view.setUint16(32, frame.syscallOrOpcode & 0xffff, true);
  view.setUint8(34, frame.stratum & 0x03);
  view.setUint8(35, frame.verdictFlags & 0xff);

  const enc = new TextEncoder();
  const bytes = enc.encode(frame.payloadPreview.slice(0, 28));
  const out = new Uint8Array(buf, 36, 28);
  out.set(bytes.slice(0, 28));

  return buf;
}

export function decodeGenesisAtomicFrame(
  buffer: ArrayBufferLike,
  byteOffset = 0
): DecodedGenesisAtomicFrame {
  const view = new DataView(buffer, byteOffset, FRAME_BYTE_LENGTH);
  const timestampNs = view.getBigUint64(0, true);
  const rootHex = view.getBigUint64(8, true).toString(16).padStart(16, '0');
  const entityId = view.getUint32(16, true);
  const causalParentId = view.getUint32(20, true);
  const metricPrimary = view.getFloat32(24, true);
  const metricSecondary = view.getFloat32(28, true);
  const syscallOrOpcode = view.getUint16(32, true);
  const stratum = (view.getUint8(34) & 0x03) as AuraStratum;
  const verdictFlags = view.getUint8(35);

  const previewSlice = new Uint8Array(buffer, byteOffset + 36, 28);
  let len = 28;
  while (len > 0 && previewSlice[len - 1] === 0) len--;
  const payloadPreview = new TextDecoder().decode(previewSlice.subarray(0, len));

  return {
    timestampNs,
    traceMerkleRoot: rootHex,
    entityId,
    causalParentId,
    metricPrimary,
    metricSecondary,
    syscallOrOpcode,
    stratum,
    verdictFlags,
    payloadPreview,
  };
}

export function packFramesToBinaryBuffer(frames: DecodedGenesisAtomicFrame[]): Uint8Array {
  const total = new Uint8Array(frames.length * FRAME_BYTE_LENGTH);
  frames.forEach((f, idx) => {
    const single = new Uint8Array(encodeGenesisAtomicFrame(f));
    total.set(single, idx * FRAME_BYTE_LENGTH);
  });
  return total;
}

export function lawI11Zone(
  elapsedSec: number
): 'LAMINAR' | 'COMPRESSION' | 'EVENT_HORIZON' | 'SEVERED' {
  if (elapsedSec >= 100) return 'SEVERED';
  if (elapsedSec >= 86) return 'EVENT_HORIZON';
  if (elapsedSec >= 51) return 'COMPRESSION';
  return 'LAMINAR';
}
