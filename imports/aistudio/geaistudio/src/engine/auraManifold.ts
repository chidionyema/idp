import {
  AuraEntityDescriptor,
  AuraManifoldSnapshot,
  AuraStratum,
  CounterfactualForkBranch,
  decodeGenesisAtomicFrame,
  DecodedGenesisAtomicFrame,
  deterministicEntityHash,
  encodeGenesisAtomicFrame,
  FRAME_BYTE_LENGTH,
  lawI11Zone,
  packFramesToBinaryBuffer,
  SerializedAtomicFrame,
  SovereignVerdictCard,
  VERDICT_FLAG_DIGEST_BOUND,
  VERDICT_FLAG_FAULT,
  VERDICT_FLAG_SEALED,
  VERDICT_FLAG_ZERO_POLL_OK,
} from './auraBinaryCodec';
import { DagsterOrchestrator } from './dagsterOrchestrator';
import { buildI8095LockdownSnapshot } from './i8095Lockdown';
import { ModelSupplyRegistry } from './modelSupply';
import { RouterEngine } from './routerCore';

export * from './auraBinaryCodec';

export interface AuraManifoldMutableState {
  activeRewindSec: number;
  isolatedLane: string | null;
  pool429Override: { minimax: boolean; zai: boolean; kimi: boolean };
  simulateShortCopy8164: boolean;
  simulateZeroPollSpike: boolean;
  activeForks: CounterfactualForkBranch[];
}

export function createDefaultAuraState(): AuraManifoldMutableState {
  return {
    activeRewindSec: 0,
    isolatedLane: null,
    pool429Override: { minimax: false, zai: true, kimi: false },
    simulateShortCopy8164: false,
    simulateZeroPollSpike: false,
    activeForks: [],
  };
}

export function buildAuraManifoldSnapshot(params: {
  router: RouterEngine;
  dagster: DagsterOrchestrator;
  supply: ModelSupplyRegistry;
  auraState: AuraManifoldMutableState;
}): AuraManifoldSnapshot {
  const { router, dagster, supply, auraState } = params;
  const lanes = router.getLanes();
  const packets = router.forensics.getPackets(12);
  const models = supply.getModels();
  const i8095 = buildI8095LockdownSnapshot({ router, dagster });

  const idEstate = deterministicEntityHash('estate-graph::root');
  const idProxy = deterministicEntityHash('argon::proxy-4001');
  const idIdp = deterministicEntityHash('idp::delivery-8169');
  const idCrew = deterministicEntityHash('crew::legion-swarm');
  const idIntake = deterministicEntityHash('idp::gemini-intake-8164');
  const idSymbiont = deterministicEntityHash('estate::i8090-symbiont');
  const idMiniMax = deterministicEntityHash('proxy-4001::pool-minimax');
  const idZai = deterministicEntityHash('proxy-4001::pool-zai');
  const idKimi = deterministicEntityHash('proxy-4001::pool-kimi');
  const idMsr = deterministicEntityHash('crew::magentic-fara');
  const idWal = deterministicEntityHash('argon::merkle-wal');
  const idSilicon = deterministicEntityHash('argon::rust-tokio-epoll');

  const latestPkt = packets[0];
  const any429 =
    auraState.pool429Override.minimax ||
    auraState.pool429Override.zai ||
    auraState.pool429Override.kimi ||
    lanes.some((l) => l.faultMode === '429_rate_limit');

  const rewindFactor = Math.max(0.25, 1 - auraState.activeRewindSec / 120);

  const entities: AuraEntityDescriptor[] = [
    {
      entityId: idEstate,
      slug: 'estate-graph::root',
      label: 'estate-graph',
      repo: 'estate-graph',
      stratum: 0,
      causalParentId: idEstate,
      x: 0,
      y: -0.05,
      cpuSaturationPct: Math.round(38 * rewindFactor),
      ramMb: 1420,
      lawI11ElapsedSec: 18,
      opcode: 200,
      digestBound: true,
      digestShortCopyFault: false,
      zeroPollViolation: false,
      sealed: true,
      latencyUs: 240,
      tokPerSec: Math.round(latestPkt?.timings.tokensPerSec ?? 185),
    },
    {
      entityId: idProxy,
      slug: 'argon::proxy-4001',
      label: 'genesis-kernel :4001',
      repo: 'proxy-4001',
      stratum: 0,
      causalParentId: idEstate,
      x: 0.48,
      y: -0.14,
      cpuSaturationPct: any429 ? 76 : 44,
      ramMb: 640,
      lawI11ElapsedSec: any429 ? 64 : 24,
      opcode: any429 ? 429 : 200,
      digestBound: true,
      digestShortCopyFault: false,
      zeroPollViolation: false,
      sealed: true,
      latencyUs: 112,
      tokPerSec: 340,
    },
    {
      entityId: idIdp,
      slug: 'idp::delivery-8169',
      label: 'idp (#8169)',
      repo: 'idp',
      stratum: 0,
      causalParentId: idEstate,
      x: -0.52,
      y: -0.22,
      cpuSaturationPct: 31,
      ramMb: 510,
      lawI11ElapsedSec: 42,
      opcode: 200,
      digestBound: true,
      digestShortCopyFault: false,
      zeroPollViolation: false,
      sealed: true,
      latencyUs: 195,
      tokPerSec: 110,
    },
    {
      entityId: idCrew,
      slug: 'crew::legion-swarm',
      label: 'crew / legion',
      repo: 'crew',
      stratum: 0,
      causalParentId: idEstate,
      x: -0.38,
      y: 0.44,
      cpuSaturationPct: 52,
      ramMb: 890,
      lawI11ElapsedSec: 56, // Compression zone amber
      opcode: 200,
      digestBound: true,
      digestShortCopyFault: false,
      zeroPollViolation: auraState.simulateZeroPollSpike,
      sealed: !auraState.simulateZeroPollSpike,
      latencyUs: 148,
      tokPerSec: 270,
    },
    {
      entityId: idMiniMax,
      slug: 'proxy-4001::pool-minimax',
      label: 'MiniMax M3.1 Pool',
      repo: 'proxy-4001',
      stratum: 1,
      causalParentId: idProxy,
      x: 0.72,
      y: -0.45,
      cpuSaturationPct: auraState.pool429Override.minimax ? 94 : 36,
      ramMb: 310,
      lawI11ElapsedSec: auraState.pool429Override.minimax ? 91 : 19,
      opcode: auraState.pool429Override.minimax ? 429 : 200,
      digestBound: true,
      digestShortCopyFault: false,
      zeroPollViolation: false,
      sealed: true,
      latencyUs: 165,
      tokPerSec: 220,
      upstreamPool: 'minimax',
    },
    {
      entityId: idZai,
      slug: 'proxy-4001::pool-zai',
      label: 'Z.ai GLM-5.3 Pool',
      repo: 'proxy-4001',
      stratum: 1,
      causalParentId: idProxy,
      x: 0.80,
      y: -0.02,
      cpuSaturationPct: auraState.pool429Override.zai ? 92 : 41,
      ramMb: 280,
      lawI11ElapsedSec: auraState.pool429Override.zai ? 88 : 29,
      opcode: auraState.pool429Override.zai ? 429 : 200,
      digestBound: true,
      digestShortCopyFault: false,
      zeroPollViolation: false,
      sealed: true,
      latencyUs: auraState.pool429Override.zai ? 490 : 178,
      tokPerSec: 195,
      upstreamPool: 'zai',
    },
    {
      entityId: idKimi,
      slug: 'proxy-4001::pool-kimi',
      label: 'Kimi Code K2 Pool',
      repo: 'proxy-4001',
      stratum: 1,
      causalParentId: idProxy,
      x: 0.68,
      y: 0.36,
      cpuSaturationPct: auraState.pool429Override.kimi ? 95 : 28,
      ramMb: 320,
      lawI11ElapsedSec: auraState.pool429Override.kimi ? 94 : 15,
      opcode: auraState.pool429Override.kimi ? 429 : 200,
      digestBound: true,
      digestShortCopyFault: false,
      zeroPollViolation: false,
      sealed: true,
      latencyUs: 132,
      tokPerSec: 260,
      upstreamPool: 'kimi',
    },
    {
      entityId: idMsr,
      slug: 'crew::magentic-fara',
      label: 'MagenticBrain + Fara1.5',
      repo: 'crew',
      stratum: 1,
      causalParentId: idCrew,
      x: -0.68,
      y: 0.25,
      cpuSaturationPct: 48,
      ramMb: 440,
      lawI11ElapsedSec: 21,
      opcode: 200,
      digestBound: true,
      digestShortCopyFault: false,
      zeroPollViolation: false,
      sealed: true,
      latencyUs: 96,
      tokPerSec: 410,
    },
    {
      entityId: idIntake,
      slug: 'idp::gemini-intake-8164',
      label: 'gemini-intake #8164',
      repo: 'idp',
      stratum: 2,
      causalParentId: idIdp,
      x: -0.26,
      y: -0.52,
      cpuSaturationPct: auraState.simulateShortCopy8164 ? 89 : 22,
      ramMb: 190,
      lawI11ElapsedSec: auraState.simulateShortCopy8164 ? 95 : 14,
      opcode: auraState.simulateShortCopy8164 ? 422 : 200,
      digestBound: !auraState.simulateShortCopy8164,
      digestShortCopyFault: auraState.simulateShortCopy8164,
      zeroPollViolation: false,
      sealed: !auraState.simulateShortCopy8164,
      latencyUs: 88,
      tokPerSec: 95,
    },
    {
      entityId: idSymbiont,
      slug: 'estate::i8090-symbiont',
      label: 'I-8090 Zero-Poll Bus',
      repo: 'estate-graph',
      stratum: 2,
      causalParentId: idEstate,
      x: 0.08,
      y: 0.56,
      cpuSaturationPct: auraState.simulateZeroPollSpike ? 97 : 19,
      ramMb: 160,
      lawI11ElapsedSec: auraState.simulateZeroPollSpike ? 98 : 11,
      opcode: auraState.simulateZeroPollSpike ? 78 : 200,
      digestBound: true,
      digestShortCopyFault: false,
      zeroPollViolation: auraState.simulateZeroPollSpike,
      sealed: !auraState.simulateZeroPollSpike,
      latencyUs: 64,
      tokPerSec: 320,
    },
    {
      entityId: idWal,
      slug: 'argon::merkle-wal',
      label: 'Merkle WAL Ring',
      repo: 'argon',
      stratum: 2,
      causalParentId: idProxy,
      x: 0.25,
      y: -0.50,
      cpuSaturationPct: 33,
      ramMb: 240,
      lawI11ElapsedSec: 17,
      opcode: 200,
      digestBound: true,
      digestShortCopyFault: false,
      zeroPollViolation: false,
      sealed: true,
      latencyUs: 42,
      tokPerSec: 510,
    },
    {
      entityId: idSilicon,
      slug: 'argon::rust-tokio-epoll',
      label: 'Tokio epoll_wait Heap',
      repo: 'argon',
      stratum: 3,
      causalParentId: idProxy,
      x: 0.35,
      y: 0.28,
      cpuSaturationPct: 39,
      ramMb: 128,
      lawI11ElapsedSec: 8,
      opcode: 200,
      digestBound: true,
      digestShortCopyFault: false,
      zeroPollViolation: false,
      sealed: true,
      latencyUs: 18,
      tokPerSec: 690,
    },
  ];

  const baseNs = BigInt(Date.now()) * 1_000_000n - BigInt(Math.round(auraState.activeRewindSec * 1e9));
  const rawFrames: DecodedGenesisAtomicFrame[] = entities.map((e, idx) => {
    let flags = 0;
    if (e.sealed) flags |= VERDICT_FLAG_SEALED;
    if (!e.zeroPollViolation) flags |= VERDICT_FLAG_ZERO_POLL_OK;
    if (e.digestBound) flags |= VERDICT_FLAG_DIGEST_BOUND;
    if (e.opcode >= 400 || e.opcode === 78 || e.digestShortCopyFault || e.zeroPollViolation) {
      flags |= VERDICT_FLAG_FAULT;
    }
    const rootHex = ((0x9e3779b97f4a7c15n ^ BigInt(e.entityId + idx * 97)) & 0xffffffffffffffffn)
      .toString(16)
      .padStart(16, '0');
    return {
      timestampNs: baseNs + BigInt(idx * 140_000),
      traceMerkleRoot: rootHex,
      entityId: e.entityId,
      causalParentId: e.causalParentId,
      metricPrimary: e.latencyUs,
      metricSecondary: Number((e.lawI11ElapsedSec / 100).toFixed(3)),
      syscallOrOpcode: e.opcode,
      stratum: e.stratum,
      verdictFlags: flags,
      payloadPreview: `${e.slug.slice(0, 20)}:${e.opcode}`,
    };
  });

  const packed = packFramesToBinaryBuffer(rawFrames);
  const framesBase64 = Buffer.from(packed).toString('base64');

  const decodedSample: SerializedAtomicFrame[] = rawFrames.map((_, idx) => {
    const f = decodeGenesisAtomicFrame(
      packed.buffer,
      packed.byteOffset + idx * FRAME_BYTE_LENGTH
    );
    return { ...f, timestampNs: f.timestampNs.toString() };
  });

  const verdictCards: SovereignVerdictCard[] = [
    {
      id: 'VC-8169-01',
      timestampIso: new Date(Number(baseNs / 1_000_000n)).toISOString(),
      intentParsed: 'Whisper-Vector: /route cognitive=orchestration zero_retention=true',
      confidenceScore: 0.984,
      chosenLane:
        models.find((m) => m.id === 'msr-magentic-brain')?.name ?? 'MagenticBrain Orchestrator',
      verdict: 'ALLOW_SEALED',
      traceMerkleRoot: rawFrames[7].traceMerkleRoot,
    },
    {
      id: 'VC-4001-02',
      timestampIso: new Date(Number(baseNs / 1_000_000n) - 1200).toISOString(),
      intentParsed: auraState.pool429Override.zai
        ? 'Proxy :4001 HTTP 429 deflection on Z.ai -> sub-ms ricochet to Kimi Code'
        : 'Proxy :4001 balanced multi-pool dispatch across MiniMax / Z.ai / Kimi',
      confidenceScore: 0.992,
      chosenLane: auraState.pool429Override.zai ? 'kimi-code-k2' : 'zai-glm-5.3',
      verdict: auraState.pool429Override.zai ? 'DEFLECT_429_FAILOVER' : 'ALLOW_SEALED',
      traceMerkleRoot: rawFrames[5].traceMerkleRoot,
    },
    {
      id: 'VC-8164-03',
      timestampIso: new Date(Number(baseNs / 1_000_000n) - 3400).toISOString(),
      intentParsed: auraState.simulateShortCopy8164
        ? 'gemini-intake #8164 dst copy SHA-256 mismatch -> shatter & freeze vector'
        : 'gemini-intake #8164 dst SHA-256 copy re-hash bound to source digest',
      confidenceScore: 1.0,
      chosenLane: 'bin/gemini-intake',
      verdict: auraState.simulateShortCopy8164 ? 'SHATTER_SHORT_COPY' : 'ALLOW_SEALED',
      traceMerkleRoot: rawFrames[8].traceMerkleRoot,
    },
  ];

  return {
    generatedAt: new Date().toISOString(),
    provenanceNotice:
      'IN_PROCESS_BINARY_RING (64B GenesisAtomicFrame ArrayBuffer verified) — Hardware eBPF uprobes & external WebTransport QUIC sockets are EXTERNAL_KERNEL_TARGET.',
    frameByteSize: 64,
    frameCount: rawFrames.length,
    framesBase64,
    entities,
    verdictCards,
    activeForks: auraState.activeForks,
    isolatedLane: auraState.isolatedLane,
    activeRewindSec: auraState.activeRewindSec,
    zeroPollShieldIntact: !auraState.simulateZeroPollSpike && i8095.counts.bddPassed === 4,
    upstreamPoolPressure: {
      minimax: {
        pressure: auraState.pool429Override.minimax ? 0.94 : 0.36,
        status429: auraState.pool429Override.minimax,
      },
      zai: {
        pressure: auraState.pool429Override.zai ? 0.92 : 0.41,
        status429: auraState.pool429Override.zai,
      },
      kimi: {
        pressure: auraState.pool429Override.kimi ? 0.95 : 0.28,
        status429: auraState.pool429Override.kimi,
      },
    },
    siliconMatrix: [
      { frameLabel: 'tokio::net::tcp::stream', syscall: 'epoll_wait', heapDeltaKb: 14, epollWaitUs: 18, hotPct: 34 },
      { frameLabel: 'certifier::verify_raw_sha256', syscall: 'sha256_ni', heapDeltaKb: 4, epollWaitUs: 7, hotPct: 26 },
      { frameLabel: 'wal::merkle_ring_append', syscall: 'pwrite64', heapDeltaKb: 8, epollWaitUs: 11, hotPct: 19 },
      { frameLabel: 'proxy::sse_zero_copy_mux', syscall: 'splice', heapDeltaKb: 2, epollWaitUs: 5, hotPct: 13 },
      { frameLabel: 'symbiont::after_insert_notify', syscall: 'futex_wake', heapDeltaKb: 1, epollWaitUs: 3, hotPct: 8 },
    ],
    decodedSample,
  };
}

export function executeAuraOmniCommand(
  commandRaw: string,
  state: AuraManifoldMutableState
): { ok: boolean; message: string; focusSlug?: string } {
  const cmd = commandRaw.trim();
  if (!cmd) {
    return { ok: false, message: 'Empty command. Try :fork --upstream kimi, /rewind 42.8, or /mesh-isolate lane-2.' };
  }

  if (cmd.startsWith(':fork')) {
    const upMatch = /--upstream\s+(minimax|zai|kimi)/i.exec(cmd);
    const upstream = (upMatch?.[1]?.toLowerCase() ?? 'kimi') as 'minimax' | 'zai' | 'kimi';
    const intentMatch = /--override-intent\s+(.+)$/i.exec(cmd);
    const intent = intentMatch?.[1]?.trim() || 'Counterfactual shadow execution branch';
    const forkId = `FORK-${String(state.activeForks.length + 1).padStart(2, '0')}`;
    const forkCost = upstream === 'kimi' ? 0.00042 : upstream === 'minimax' ? 0.00019 : 0.00028;
    state.activeForks.unshift({
      forkId,
      parentRewindSec: state.activeRewindSec,
      upstreamOverride: upstream,
      overrideIntent: intent,
      historicalLatencyMs: 245,
      forkLatencyMs: upstream === 'kimi' ? 92 : 118,
      historicalCostUsd: 0.0031,
      forkCostUsd: forkCost,
      gateVerdict: state.pool429Override[upstream] ? 'DEFLECTED' : 'PASS_SHADOW_GATE',
      createdAt: new Date().toISOString(),
    });
    return {
      ok: true,
      message: `Spawned shadow counterfactual ${forkId} on ${upstream.toUpperCase()} at T-${state.activeRewindSec.toFixed(1)}s`,
      focusSlug: `proxy-4001::pool-${upstream}`,
    };
  }

  if (cmd.startsWith('/rewind')) {
    const num = Number(cmd.replace('/rewind', '').trim());
    const sec = Number.isFinite(num) ? Math.max(0, Math.min(120, num)) : 42.8;
    state.activeRewindSec = Number(sec.toFixed(1));
    return {
      ok: true,
      message: `Chrono-scrubber rewound to T-${state.activeRewindSec.toFixed(1)}s across 64-byte Merkle ring`,
    };
  }

  if (cmd.startsWith('/mesh-isolate')) {
    const lane = cmd.replace('/mesh-isolate', '').trim() || 'lane-2';
    state.isolatedLane = lane === 'clear' || lane === 'none' ? null : lane;
    return {
      ok: true,
      message: state.isolatedLane
        ? `Causal isolation engaged for ${state.isolatedLane} (non-ancestry faded to 5%)`
        : 'Cleared causal lane isolation',
    };
  }

  if (cmd.startsWith('/inspect')) {
    const target = cmd.replace('/inspect', '').trim().toLowerCase();
    if (target.includes('4001') || target.includes('rust')) {
      return { ok: true, message: 'Semantic zoom locked on genesis-kernel :4001', focusSlug: 'argon::proxy-4001' };
    }
    if (target.includes('8164') || target.includes('intake')) {
      return { ok: true, message: 'Semantic zoom locked on gemini-intake #8164', focusSlug: 'idp::gemini-intake-8164' };
    }
    if (target.includes('tokio') || target.includes('silicon')) {
      return { ok: true, message: 'Semantic zoom locked on Tokio epoll_wait Silicon Matrix', focusSlug: 'argon::rust-tokio-epoll' };
    }
    return { ok: true, message: `Inspecting estate entity matching "${target}"`, focusSlug: 'estate-graph::root' };
  }

  if (cmd.startsWith('/inject-429')) {
    const pool = (cmd.replace('/inject-429', '').trim().toLowerCase() || 'zai') as 'minimax' | 'zai' | 'kimi';
    if (pool in state.pool429Override) {
      state.pool429Override[pool] = !state.pool429Override[pool];
      return {
        ok: true,
        message: `${pool.toUpperCase()} HTTP 429 deflection shield ${
          state.pool429Override[pool] ? 'ACTIVE (ricochet engaged)' : 'CLEARED'
        }`,
        focusSlug: `proxy-4001::pool-${pool}`,
      };
    }
  }

  if (cmd === '/toggle-short-copy') {
    state.simulateShortCopy8164 = !state.simulateShortCopy8164;
    return {
      ok: true,
      message: state.simulateShortCopy8164
        ? 'gemini-intake #8164 short-copy SHA-256 mismatch injected (glyph shattered)'
        : 'gemini-intake #8164 SHA-256 digest binding restored (crystalline seal)',
      focusSlug: 'idp::gemini-intake-8164',
    };
  }

  if (cmd === '/toggle-poll-spike') {
    state.simulateZeroPollSpike = !state.simulateZeroPollSpike;
    return {
      ok: true,
      message: state.simulateZeroPollSpike
        ? 'Injected synchronous polling spike at I-8090 perimeter (exit 78 alert)'
        : 'Restored I-8090 Zero-Poll interference perimeter',
      focusSlug: 'estate::i8090-symbiont',
    };
  }

  if (cmd === '/reset') {
    state.activeRewindSec = 0;
    state.isolatedLane = null;
    state.simulateShortCopy8164 = false;
    state.simulateZeroPollSpike = false;
    state.pool429Override = { minimax: false, zai: true, kimi: false };
    state.activeForks = [];
    return { ok: true, message: 'Reset AURA-2100 manifold to live T-0.0s laminar baseline' };
  }

  return {
    ok: false,
    message: `Unknown command "${cmd}". Supported: /inspect, /rewind <sec>, /mesh-isolate <lane>, :fork --upstream <minimax|zai|kimi>, /inject-429 <pool>, /toggle-short-copy, /toggle-poll-spike, /reset`,
  };
}
