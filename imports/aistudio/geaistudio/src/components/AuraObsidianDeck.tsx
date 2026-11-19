import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Binary,
  Cpu,
  GitFork,
  History,
  Layers,
  Sparkles,
  Terminal,
} from 'lucide-react';
import {
  AuraEntityDescriptor,
  AuraManifoldSnapshot,
  AuraStratum,
  decodeGenesisAtomicFrame,
  DecodedGenesisAtomicFrame,
  FRAME_BYTE_LENGTH,
  lawI11Zone,
  VERDICT_FLAG_DIGEST_BOUND,
  VERDICT_FLAG_FAULT,
  VERDICT_FLAG_SEALED,
  VERDICT_FLAG_ZERO_POLL_OK,
} from '../engine/auraBinaryCodec';

const STRATUM_PRESETS: Array<{ stratum: AuraStratum; label: string; altitude: string; zoomVal: number }> = [
  { stratum: 0, label: 'Z0: Orbital', altitude: '1.00x', zoomVal: 1.0 },
  { stratum: 1, label: 'Z-1: Swarm', altitude: '0.50x', zoomVal: 0.5 },
  { stratum: 2, label: 'Z-2: Forensic', altitude: '0.15x', zoomVal: 0.15 },
  { stratum: 3, label: 'Z-3: Silicon', altitude: '0.02x', zoomVal: 0.02 },
];

function decodeBinaryRingFromBase64(b64: string): DecodedGenesisAtomicFrame[] {
  try {
    const raw = atob(b64);
    const bytes = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) {
      bytes[i] = raw.charCodeAt(i);
    }
    const count = Math.floor(bytes.byteLength / FRAME_BYTE_LENGTH);
    const out: DecodedGenesisAtomicFrame[] = [];
    for (let i = 0; i < count; i++) {
      out.push(decodeGenesisAtomicFrame(bytes.buffer, i * FRAME_BYTE_LENGTH));
    }
    return out;
  } catch {
    return [];
  }
}

function formatVerdictFlags(flags: number): string {
  const parts: string[] = [];
  if (flags & VERDICT_FLAG_SEALED) parts.push('SEALED');
  if (flags & VERDICT_FLAG_ZERO_POLL_OK) parts.push('ZERO_POLL_OK');
  if (flags & VERDICT_FLAG_DIGEST_BOUND) parts.push('DIGEST_BOUND');
  if (flags & VERDICT_FLAG_FAULT) parts.push('FAULT');
  return parts.join(' | ') || 'NONE';
}

export function AuraObsidianDeck() {
  const [snapshot, setSnapshot] = useState<AuraManifoldSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [stratum, setStratum] = useState<AuraStratum>(1);
  const [selectedEntityId, setSelectedEntityId] = useState<number | null>(null);
  const [omniInput, setOmniInput] = useState(':fork --upstream kimi --override-intent latency_check');
  const [commandStatus, setCommandStatus] = useState<string | null>(null);
  const [runningCmd, setRunningCmd] = useState(false);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const tickRef = useRef(0);

  const loadManifold = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/aura/manifold');
      if (res.ok) {
        const data = (await res.json()) as AuraManifoldSnapshot;
        setSnapshot(data);
        setSelectedEntityId((prev) => prev ?? data.entities[1]?.entityId ?? null);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadManifold();
  }, [loadManifold]);

  async function runOmniCommand(cmdText: string) {
    setRunningCmd(true);
    try {
      const res = await fetch('/api/aura/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmdText }),
      });
      const json = (await res.json()) as {
        outcome: { ok: boolean; message: string; focusSlug?: string };
        manifold: AuraManifoldSnapshot;
      };
      setSnapshot(json.manifold);
      setCommandStatus(json.outcome.message);
      if (json.outcome.focusSlug) {
        const match = json.manifold.entities.find((e) => e.slug === json.outcome.focusSlug);
        if (match) {
          setSelectedEntityId(match.entityId);
          setStratum(match.stratum);
        }
      }
    } finally {
      setRunningCmd(false);
    }
  }

  // Real 64-byte ArrayBuffer decoding in client memory (matches #[repr(C, align(64))])
  const clientDecodedFrames = useMemo(() => {
    if (!snapshot) return [];
    return decodeBinaryRingFromBase64(snapshot.framesBase64);
  }, [snapshot]);

  const selectedEntity: AuraEntityDescriptor | null = useMemo(() => {
    if (!snapshot) return null;
    return (
      snapshot.entities.find((e) => e.entityId === selectedEntityId) ??
      snapshot.entities[1] ??
      snapshot.entities[0] ??
      null
    );
  }, [snapshot, selectedEntityId]);

  const ancestryIds = useMemo(() => {
    if (!snapshot || !selectedEntity) return new Set<number>();
    const ids = new Set<number>([selectedEntity.entityId]);
    let curr: AuraEntityDescriptor | undefined = selectedEntity;
    for (let i = 0; i < 6 && curr; i++) {
      ids.add(curr.causalParentId);
      const pid: number = curr.causalParentId;
      if (pid === curr.entityId) break;
      curr = snapshot.entities.find((e) => e.entityId === pid);
    }
    snapshot.entities.forEach((e) => {
      if (e.causalParentId === selectedEntity.entityId) ids.add(e.entityId);
    });
    return ids;
  }, [snapshot, selectedEntity]);

  // Obsidian Manifold Physics Canvas Renderer (zero DOM churn during frame pulse)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !snapshot) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let rafId = 0;
    let frameIndex = 0;

    const drawFrame = () => {
      frameIndex++;
      tickRef.current = frameIndex * 0.04;
      const t = tickRef.current;

      const dpr = Math.min(2, window.devicePixelRatio || 1);
      const rect = canvas.getBoundingClientRect();
      const width = Math.max(320, rect.width || 900);
      const height = Math.max(280, rect.height || 460);

      if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) {
        canvas.width = Math.round(width * dpr);
        canvas.height = Math.round(height * dpr);
      }

      ctx.save();
      ctx.scale(dpr, dpr);

      // 1. Absolute Obsidian Void (#04060B)
      ctx.fillStyle = '#04060B';
      ctx.fillRect(0, 0, width, height);

      // 2. I-8090 Zero-Poll Perimeter Interference Field
      ctx.strokeStyle = snapshot.zeroPollShieldIntact
        ? 'rgba(0, 240, 255, 0.14)'
        : 'rgba(255, 0, 85, 0.55)';
      ctx.lineWidth = snapshot.zeroPollShieldIntact ? 1 : 2;
      ctx.strokeRect(8, 8, width - 16, height - 16);

      // Subtle Hairline Spacetime Grid (gravity-bent near hot nodes)
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.06)';
      ctx.lineWidth = 1;
      for (let gx = 40; gx < width; gx += 52) {
        ctx.beginPath();
        ctx.moveTo(gx, 12);
        ctx.lineTo(gx, height - 12);
        ctx.stroke();
      }
      for (let gy = 40; gy < height; gy += 52) {
        ctx.beginPath();
        ctx.moveTo(12, gy);
        ctx.lineTo(width - 12, gy);
        ctx.stroke();
      }

      const cx = width * 0.5;
      const cy = height * 0.52;
      const sx = width * 0.42;
      const sy = height * 0.39;

      const mapPos = (e: AuraEntityDescriptor) => ({
        px: cx + e.x * sx,
        py: cy + e.y * sy,
      });

      const visibleEntities = snapshot.entities.filter((e) => e.stratum <= Math.max(1, stratum));
      const frameMap = new Map(clientDecodedFrames.map((f) => [f.entityId, f]));

      // 3. Proxy :4001 Orbital Upstream Rings (MiniMax, Z.ai, Kimi Code)
      const proxy = snapshot.entities.find((e) => e.slug === 'argon::proxy-4001');
      if (proxy) {
        const pp = mapPos(proxy);
        const pools = [
          { r: 44, key: 'minimax' as const, label: 'MiniMax' },
          { r: 62, key: 'zai' as const, label: 'Z.ai' },
          { r: 80, key: 'kimi' as const, label: 'Kimi' },
        ];
        pools.forEach((pl) => {
          const is429 = snapshot.upstreamPoolPressure[pl.key].status429;
          ctx.beginPath();
          ctx.arc(pp.px, pp.py, pl.r, 0, Math.PI * 2);
          ctx.strokeStyle = is429 ? 'rgba(255, 0, 85, 0.55)' : 'rgba(0, 240, 255, 0.20)';
          ctx.setLineDash(is429 ? [6, 4] : [3, 6]);
          ctx.lineWidth = is429 ? 1.8 : 1;
          ctx.stroke();
          ctx.setLineDash([]);
        });
      }

      // 4. Causal Merkle-WAL Edges & Binary Packet Pulses
      visibleEntities.forEach((entity) => {
        if (entity.entityId === entity.causalParentId) return;
        const parent = snapshot.entities.find((p) => p.entityId === entity.causalParentId);
        if (!parent) return;

        const a = mapPos(parent);
        const b = mapPos(entity);
        const isIsolatedMode = Boolean(snapshot.isolatedLane) || Boolean(selectedEntityId);
        const inAncestry = ancestryIds.has(entity.entityId) && ancestryIds.has(parent.entityId);
        const alpha = isIsolatedMode && !inAncestry ? 0.1 : 0.72;

        ctx.beginPath();
        ctx.moveTo(a.px, a.py);
        ctx.lineTo(b.px, b.py);
        ctx.strokeStyle =
          entity.opcode === 429 || entity.zeroPollViolation || entity.digestShortCopyFault
            ? `rgba(255, 0, 85, ${alpha})`
            : `rgba(0, 240, 255, ${alpha * 0.45})`;
        ctx.lineWidth = inAncestry ? 1.8 : 1;
        ctx.stroke();

        // Moving binary frame pulse along edge (reversed direction when rewinding)
        const dir = snapshot.activeRewindSec > 0 ? -1 : 1;
        const rawProgress = ((t * 0.45 * dir + (entity.entityId % 10) * 0.13) % 1 + 1) % 1;
        const qx = a.px + (b.px - a.px) * rawProgress;
        const qy = a.py + (b.py - a.py) * rawProgress;

        if (entity.digestShortCopyFault) {
          // Shattered crimson fragments for PR #8164 short-copy mismatch
          ctx.fillStyle = '#FF0055';
          ctx.fillRect(qx - 5, qy - 5, 4, 4);
          ctx.fillRect(qx + 3, qy + 2, 4, 4);
        } else if (entity.opcode === 429) {
          // HTTP 429 refractive deflection pulse
          ctx.beginPath();
          ctx.arc(qx, qy, 4, 0, Math.PI * 2);
          ctx.fillStyle = '#FF0055';
          ctx.fill();
        } else {
          // Solid crystalline diamond once SHA-256 digest bound
          ctx.save();
          ctx.translate(qx, qy);
          ctx.rotate(Math.PI / 4);
          ctx.fillStyle = '#00F0FF';
          ctx.fillRect(-3, -3, 6, 6);
          ctx.restore();
        }
      });

      // 5. Counterfactual Gold Ghost-Topology Branches (:fork)
      if (snapshot.activeForks.length > 0 && proxy) {
        snapshot.activeForks.slice(0, 2).forEach((fork) => {
          const target = snapshot.entities.find(
            (e) => e.upstreamPool === fork.upstreamOverride
          );
          if (!target) return;
          const pp = mapPos(proxy);
          const tp = mapPos(target);
          ctx.beginPath();
          ctx.moveTo(pp.px, pp.py);
          ctx.quadraticCurveTo(
            (pp.px + tp.px) / 2,
            (pp.py + tp.py) / 2 - 42,
            tp.px,
            tp.py
          );
          ctx.strokeStyle = 'rgba(250, 204, 21, 0.9)';
          ctx.setLineDash([5, 4]);
          ctx.lineWidth = 2.2;
          ctx.stroke();
          ctx.setLineDash([]);
        });
      }

      // 6. Render Nodes with Law I11 Temporal Gravity Rings
      visibleEntities.forEach((entity) => {
        const { px, py } = mapPos(entity);
        const frame = frameMap.get(entity.entityId);
        const inAncestry = ancestryIds.has(entity.entityId);
        const dim = selectedEntityId && !inAncestry;

        ctx.globalAlpha = dim ? 0.25 : 1;

        const zone = lawI11Zone(entity.lawI11ElapsedSec);
        const ringColor =
          entity.zeroPollViolation || entity.digestShortCopyFault || entity.opcode === 429
            ? '#FF0055'
            : zone === 'EVENT_HORIZON' || zone === 'SEVERED'
              ? '#FF0055'
              : zone === 'COMPRESSION'
                ? '#FFB000'
                : '#00F0FF';

        const pulseRadius = 11 + (entity.cpuSaturationPct / 100) * 10 + Math.sin(t * 2 + entity.entityId) * 1.4;

        // Law I11 temporal ring
        ctx.beginPath();
        ctx.arc(px, py, pulseRadius + 6, 0, Math.PI * 2 * (1 - entity.lawI11ElapsedSec / 120));
        ctx.strokeStyle = ringColor;
        ctx.lineWidth = entity.entityId === selectedEntityId ? 2.6 : 1.5;
        ctx.stroke();

        // Core Obsidian Node Disc
        ctx.beginPath();
        ctx.arc(px, py, pulseRadius, 0, Math.PI * 2);
        ctx.fillStyle = '#070C18';
        ctx.fill();
        ctx.strokeStyle = ringColor;
        ctx.lineWidth = 1.6;
        ctx.stroke();

        // Selected halo
        if (entity.entityId === selectedEntityId) {
          ctx.beginPath();
          ctx.arc(px, py, pulseRadius + 11, 0, Math.PI * 2);
          ctx.strokeStyle = '#FACC15';
          ctx.lineWidth = 1.2;
          ctx.stroke();
        }

        // Crisp Monospace Labels directly embedded in manifold
        ctx.font = '600 10.5px "JetBrains Mono", monospace';
        ctx.textAlign = 'center';
        ctx.fillStyle = '#E2E8F0';
        ctx.fillText(entity.label, px, py + pulseRadius + 16);

        const metricStr = `${entity.latencyUs}us · op:${frame?.syscallOrOpcode ?? entity.opcode}`;
        ctx.font = '500 9px "JetBrains Mono", monospace';
        ctx.fillStyle = ringColor;
        ctx.fillText(metricStr, px, py + pulseRadius + 27);

        ctx.globalAlpha = 1;
      });

      ctx.restore();
    };

    // Initial synchronous draw so headless screenshots always capture rich live physics immediately
    drawFrame();

    const interval = window.setInterval(() => {
      rafId = window.requestAnimationFrame(drawFrame);
    }, 80);

    return () => {
      window.clearInterval(interval);
      if (rafId) window.cancelAnimationFrame(rafId);
    };
  }, [snapshot, stratum, selectedEntityId, ancestryIds, clientDecodedFrames]);

  function handleCanvasClick(evt: React.MouseEvent<HTMLCanvasElement>) {
    if (!canvasRef.current || !snapshot) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const clickX = evt.clientX - rect.left;
    const clickY = evt.clientY - rect.top;
    const cx = rect.width * 0.5;
    const cy = rect.height * 0.52;
    const sx = rect.width * 0.42;
    const sy = rect.height * 0.39;

    let best: AuraEntityDescriptor | null = null;
    let bestDist = 42;
    snapshot.entities
      .filter((e) => e.stratum <= Math.max(1, stratum))
      .forEach((e) => {
        const px = cx + e.x * sx;
        const py = cy + e.y * sy;
        const d = Math.hypot(clickX - px, clickY - py);
        if (d < bestDist) {
          bestDist = d;
          best = e;
        }
      });

    if (best) {
      setSelectedEntityId((best as AuraEntityDescriptor).entityId);
    }
  }

  if (loading && !snapshot) {
    return <div className="h-[620px] rounded-lg bg-[#04060B] border border-slate-800 animate-pulse" />;
  }

  if (!snapshot) return null;

  return (
    <div className="space-y-5">
      {/* AURA-2100 Obsidian Glass Primary Manifold Frame */}
      <section className="rounded-lg border border-slate-800 bg-[#04060B] text-slate-100 overflow-hidden">
        {/* Top Semantic Zoom & Protocol Telemetry Strip */}
        <div className="px-4 py-3 border-b border-slate-800/90 bg-[#070B14] flex flex-col xl:flex-row xl:items-center xl:justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono">
              <span className="text-cyan-400 font-semibold">AURA-2100 OBSIDIAN GLASS</span>
              <span className="text-slate-600">&middot;</span>
              <span className="text-slate-300">
                {snapshot.frameByteSize}B Binary Ring ({snapshot.frameCount} frames)
              </span>
              <span className="text-slate-600">&middot;</span>
              <span className="text-amber-300">
                IN_PROCESS_BINARY_RING (eBPF/QUIC: EXTERNAL_KERNEL_TARGET)
              </span>
            </div>
          </div>

          {/* Continuous Semantic Zoom Stratum Selector */}
          <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Semantic zoom stratum">
            {STRATUM_PRESETS.map((p) => (
              <button
                key={p.stratum}
                type="button"
                onClick={() => setStratum(p.stratum)}
                className={`rounded px-2.5 py-1 font-mono text-[11px] whitespace-nowrap border ${
                  stratum === p.stratum
                    ? 'border-cyan-400/70 bg-cyan-500/15 text-cyan-300'
                    : 'border-slate-800 bg-[#04060B] text-slate-400 hover:text-slate-200'
                }`}
              >
                {p.label} ({p.altitude})
              </button>
            ))}
          </div>
        </div>

        {/* Fault & Topology Stimulus Bar */}
        <div className="px-4 py-2 border-b border-slate-800/80 bg-[#050811] flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono">
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => void runOmniCommand('/inject-429 zai')}
              className={`rounded border px-2 py-1 ${
                snapshot.upstreamPoolPressure.zai.status429
                  ? 'border-pink-500/70 bg-pink-500/15 text-pink-300'
                  : 'border-slate-700 bg-[#070B14] text-slate-300 hover:border-slate-500'
              }`}
            >
              Z.ai 429 Shield: {snapshot.upstreamPoolPressure.zai.status429 ? 'RICOCHET ON' : 'OFF'}
            </button>
            <button
              type="button"
              onClick={() => void runOmniCommand('/toggle-short-copy')}
              className={`rounded border px-2 py-1 ${
                snapshot.entities.find((e) => e.slug === 'idp::gemini-intake-8164')?.digestShortCopyFault
                  ? 'border-pink-500/70 bg-pink-500/15 text-pink-300'
                  : 'border-slate-700 bg-[#070B14] text-slate-300 hover:border-slate-500'
              }`}
            >
              #8164 Digest Glyph:{' '}
              {snapshot.entities.find((e) => e.slug === 'idp::gemini-intake-8164')?.digestShortCopyFault
                ? 'SHATTERED'
                : 'SEALED CRYSTAL'}
            </button>
            <button
              type="button"
              onClick={() => void runOmniCommand('/toggle-poll-spike')}
              className={`rounded border px-2 py-1 ${
                !snapshot.zeroPollShieldIntact
                  ? 'border-pink-500/70 bg-pink-500/15 text-pink-300'
                  : 'border-slate-700 bg-[#070B14] text-slate-300 hover:border-slate-500'
              }`}
            >
              I-8090 Perimeter: {snapshot.zeroPollShieldIntact ? 'ZERO-POLL PURE' : 'SPIKE ALERT (78)'}
            </button>
            <button
              type="button"
              onClick={() => void runOmniCommand('/reset')}
              className="rounded border border-slate-700 bg-[#070B14] px-2 py-1 text-slate-300 hover:border-slate-500"
            >
              Reset Manifold
            </button>
          </div>

          <a
            href="/api/aura/frames.bin"
            download="genesis-atomic-frames.bin"
            className="inline-flex items-center gap-1 text-cyan-300 hover:underline"
          >
            <Binary className="h-3.5 w-3.5" aria-hidden="true" />
            Download 64B Raw Binary (.bin)
          </a>
        </div>

        {/* Main Topological Force-Mesh Canvas + Atomic Sidebar */}
        <div className="grid grid-cols-1 xl:grid-cols-12">
          <div className="xl:col-span-8 relative border-b xl:border-b-0 xl:border-r border-slate-800">
            <canvas
              ref={canvasRef}
              data-testid="aura-manifold-canvas"
              data-stratum={stratum}
              data-rewind={snapshot.activeRewindSec}
              data-forks={snapshot.activeForks.length}
              onClick={handleCanvasClick}
              onWheel={(e) => {
                if (Math.abs(e.deltaY) < 4) return;
                setStratum((s) =>
                  e.deltaY > 0 ? (Math.min(3, s + 1) as AuraStratum) : (Math.max(0, s - 1) as AuraStratum)
                );
              }}
              className="block w-full h-[340px] sm:h-[460px] cursor-crosshair"
            />

            {/* Floating Translucent Omni-Command Bar */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void runOmniCommand(omniInput);
              }}
              className="border-t border-slate-800/90 bg-[#060A13]/95 px-3 py-2.5 flex flex-col sm:flex-row sm:items-center gap-2"
            >
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <Terminal className="h-3.5 w-3.5 text-cyan-400 shrink-0" aria-hidden="true" />
                <input
                  type="text"
                  value={omniInput}
                  onChange={(e) => setOmniInput(e.target.value)}
                  aria-label="AURA Omni-Command Bar"
                  placeholder=":fork --upstream kimi | /rewind 42.8 | /inspect 4001 | /mesh-isolate lane-2"
                  className="w-full bg-transparent font-mono text-xs text-cyan-100 placeholder:text-slate-600 focus:outline-none"
                />
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  type="submit"
                  disabled={runningCmd}
                  className="rounded border border-cyan-500/50 bg-cyan-500/15 px-3 py-1 font-mono text-[11px] text-cyan-200 hover:bg-cyan-500/25 disabled:opacity-50"
                >
                  {runningCmd ? 'EXEC...' : 'EXECUTE'}
                </button>
              </div>
            </form>

            {commandStatus && (
              <div
                role="status"
                className="border-t border-slate-800 bg-[#07111C] px-3 py-1.5 font-mono text-[11px] text-cyan-300"
              >
                &gt; {commandStatus}
              </div>
            )}
          </div>

          {/* Right 4 Cols: Selected Node Atomic Telemetry + Law I11 + Z-3 DNA Matrix */}
          <aside className="xl:col-span-4 p-4 space-y-4 bg-[#060911]">
            {selectedEntity && (
              <>
                <div className="border-b border-slate-800 pb-3">
                  <div className="flex items-center justify-between gap-2 font-mono text-[10px] text-slate-400">
                    <span>
                      0x{selectedEntity.entityId.toString(16).padStart(8, '0')} &middot; Stratum Z-
                      {selectedEntity.stratum}
                    </span>
                    <span
                      className={
                        selectedEntity.opcode === 429 || selectedEntity.zeroPollViolation
                          ? 'text-pink-400 font-semibold'
                          : 'text-cyan-400 font-semibold'
                      }
                    >
                      {lawI11Zone(selectedEntity.lawI11ElapsedSec)}
                    </span>
                  </div>
                  <div className="mt-1 text-sm font-semibold text-white">{selectedEntity.label}</div>
                  <div className="font-mono text-[11px] text-slate-400">{selectedEntity.slug}</div>
                </div>

                <div className="grid grid-cols-2 gap-2 font-mono text-xs">
                  <div className="rounded border border-slate-800 bg-[#04060B] p-2.5">
                    <div className="text-[10px] text-slate-500">Wire Latency</div>
                    <div className="mt-0.5 text-cyan-300 font-semibold">{selectedEntity.latencyUs} us</div>
                  </div>
                  <div className="rounded border border-slate-800 bg-[#04060B] p-2.5">
                    <div className="text-[10px] text-slate-500">Law I11 Horizon</div>
                    <div className="mt-0.5 text-amber-300 font-semibold">
                      {selectedEntity.lawI11ElapsedSec}s / 100.0s
                    </div>
                  </div>
                  <div className="rounded border border-slate-800 bg-[#04060B] p-2.5">
                    <div className="text-[10px] text-slate-500">CPU / RAM Sat</div>
                    <div className="mt-0.5 text-slate-200 font-semibold">
                      {selectedEntity.cpuSaturationPct}% · {selectedEntity.ramMb} MB
                    </div>
                  </div>
                  <div className="rounded border border-slate-800 bg-[#04060B] p-2.5">
                    <div className="text-[10px] text-slate-500">Velocity / Op</div>
                    <div className="mt-0.5 text-emerald-300 font-semibold">
                      {selectedEntity.tokPerSec} t/s · {selectedEntity.opcode}
                    </div>
                  </div>
                </div>
              </>
            )}

            {/* Z-3 Silicon DNA Sequencer / Flame Matrix */}
            <div className="border-t border-slate-800 pt-3 space-y-2">
              <div className="flex items-center justify-between text-[11px] font-mono text-slate-300">
                <span className="inline-flex items-center gap-1.5">
                  <Cpu className="h-3.5 w-3.5 text-cyan-400" aria-hidden="true" />
                  Z-3 Silicon DNA Allocation Matrix
                </span>
                <span className="text-slate-500">Tokio :4001</span>
              </div>
              <div className="space-y-1.5 font-mono text-[10.5px]">
                {snapshot.siliconMatrix.map((row) => (
                  <div key={row.frameLabel} className="rounded border border-slate-800/80 bg-[#04060B] p-2">
                    <div className="flex items-center justify-between text-slate-300">
                      <span className="truncate">{row.frameLabel}</span>
                      <span className="text-cyan-300 shrink-0">{row.epollWaitUs}us</span>
                    </div>
                    <div className="mt-1 h-1.5 w-full rounded bg-slate-900 overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-cyan-400 to-amber-400"
                        style={{ width: `${row.hotPct}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </aside>
        </div>

        {/* Bottom 24px Nanosecond Chrono-Forking Phase Scrubber */}
        <div className="border-t border-slate-800 bg-[#060B15] px-4 py-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-[11px] font-mono text-amber-300 shrink-0">
            <History className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Chrono-Forking Scrubber: T-{snapshot.activeRewindSec.toFixed(1)}s</span>
          </div>
          <input
            type="range"
            min={0}
            max={120}
            step={0.2}
            value={snapshot.activeRewindSec}
            aria-label="Nanosecond chrono phase scrubber"
            onChange={(e) => void runOmniCommand(`/rewind ${e.target.value}`)}
            className="flex-1 accent-amber-400"
          />
          <button
            type="button"
            onClick={() => void runOmniCommand(':fork --upstream kimi --override-intent canary_shadow')}
            className="inline-flex items-center gap-1 rounded border border-amber-400/50 bg-amber-400/10 px-2.5 py-1 font-mono text-[11px] text-amber-300 hover:bg-amber-400/20 shrink-0"
          >
            <GitFork className="h-3 w-3" aria-hidden="true" />
            Fork Counterfactual (:4001 Kimi)
          </button>
        </div>
      </section>

      {/* Bottom 2-Col Deck: Counterfactual Shadow Forks & Z0 Verdict Cards + 64-Byte Decoded Wire Frames */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Z0 Sovereign Verdict Cards & Counterfactual Gold Forks */}
        <section className="rounded-lg border border-slate-200 bg-white p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">
                Z0 Sovereign Verdict Cards &amp; Shadow Counterfactuals
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Structured routing verdicts and gold shadow forks spawned at historical rewind timestamps.
              </p>
            </div>
            <Sparkles className="h-4 w-4 text-amber-600 shrink-0" aria-hidden="true" />
          </div>

          {snapshot.activeForks.length > 0 && (
            <div className="space-y-2">
              {snapshot.activeForks.map((f) => (
                <div
                  key={f.forkId}
                  className="rounded-md border border-amber-300 bg-amber-50 p-3 text-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2"
                >
                  <div>
                    <div className="font-mono font-semibold text-amber-900">
                      {f.forkId} &middot; Shadow Upstream: {f.upstreamOverride.toUpperCase()} (at T-
                      {f.parentRewindSec.toFixed(1)}s)
                    </div>
                    <div className="text-amber-800 mt-0.5">{f.overrideIntent}</div>
                  </div>
                  <div className="font-mono text-[11px] text-right shrink-0 text-amber-900">
                    <div>
                      {f.historicalLatencyMs}ms &rarr; <strong>{f.forkLatencyMs}ms</strong>
                    </div>
                    <div>
                      ${f.historicalCostUsd.toFixed(5)} &rarr; <strong>${f.forkCostUsd.toFixed(5)}</strong>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="space-y-2.5">
            {snapshot.verdictCards.map((vc) => (
              <div key={vc.id} className="rounded-md border border-slate-200 p-3 text-xs space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono font-semibold text-slate-900">{vc.id}</span>
                  <span
                    className={`font-mono text-[10px] font-semibold ${
                      vc.verdict === 'ALLOW_SEALED'
                        ? 'text-emerald-700'
                        : vc.verdict === 'DEFLECT_429_FAILOVER'
                          ? 'text-amber-700'
                          : 'text-red-700'
                    }`}
                  >
                    {vc.verdict}
                  </span>
                </div>
                <div className="text-slate-700">{vc.intentParsed}</div>
                <div className="font-mono text-[11px] text-slate-500 flex flex-wrap justify-between gap-2 pt-1 border-t border-slate-100">
                  <span>Lane: {vc.chosenLane}</span>
                  <span>Conf: {(vc.confidenceScore * 100).toFixed(1)}% &middot; Merkle: {vc.traceMerkleRoot}</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Zero-Copy 64-Byte Decoded Frame Ring Table */}
        <section className="rounded-lg border border-slate-200 bg-white overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">
                Decoded 64-Byte GenesisAtomicFrame Wire Buffer
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Live client-side DataView decode over ArrayBuffer matching #[repr(C, align(64))].
              </p>
            </div>
            <Layers className="h-4 w-4 text-slate-400 shrink-0" aria-hidden="true" />
          </div>

          <div className="overflow-x-auto max-h-[360px]">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-mono text-[11px]">
                  <th className="py-2 px-3">Entity Hex</th>
                  <th className="py-2 px-3">Op</th>
                  <th className="py-2 px-3">Bitmask Flags</th>
                  <th className="py-2 px-3">28B Preview</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 font-mono text-[11px]">
                {clientDecodedFrames.map((f) => (
                  <tr key={f.entityId} className="hover:bg-slate-50">
                    <td className="py-2 px-3 text-slate-900">
                      0x{f.entityId.toString(16).padStart(8, '0')}
                    </td>
                    <td
                      className={`py-2 px-3 font-semibold ${
                        f.syscallOrOpcode >= 400 || f.syscallOrOpcode === 78
                          ? 'text-red-700'
                          : 'text-emerald-700'
                      }`}
                    >
                      {f.syscallOrOpcode}
                    </td>
                    <td className="py-2 px-3 text-slate-600">{formatVerdictFlags(f.verdictFlags)}</td>
                    <td className="py-2 px-3 text-slate-800">{f.payloadPreview}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
