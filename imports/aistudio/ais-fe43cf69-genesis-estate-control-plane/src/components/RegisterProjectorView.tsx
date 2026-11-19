import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import {
  Film,
  Boxes,
  Smartphone,
  ShieldCheck,
  ShieldAlert,
  Play,
  Square,
  SkipBack,
  SkipForward,
  Plus,
  CheckCircle2,
  AlertTriangle,
  XOctagon,
  RefreshCw,
  ArrowRight,
  Terminal,
} from 'lucide-react';
import {
  PIPELINE_STAGES,
  STAGE_METADATA,
  reduceRegisterToScene,
  projectTelegram3327PinnedMessage,
  type OpsRegisterEntry,
  type OpsEvidenceFile,
  type PacketSurface,
  type ProjectorActorState,
  type FalsifierReconciliationReport,
  type RenderedActorClaim,
} from '../engine/registerProjector';
import type { FormationId } from '../engine/estateRules';
import type { EstateStateSnapshot } from '../types/estate';
import { playSovereignChime } from '../utils/sovereignAudio';
import { ArgonSyncPanel, type ArgonSyncActionResult } from './ArgonSyncPanel';

type RendererMode = 'movie' | 'isometric' | 'split3327';

interface RegisterProjectorViewProps {
  initialProjector: {
    registerPath: string;
    evidenceDir: string;
    registerEntries: OpsRegisterEntry[];
    evidenceBySeq: Record<number, OpsEvidenceFile>;
    diskSha256BySeq: Record<number, string>;
  };
  argonSync: EstateStateSnapshot['argonSync'];
  onSyncArgon: (branch?: string) => Promise<ArgonSyncActionResult>;
  onRefreshState: () => Promise<void>;
  onOpenArgonConsole: () => void;
  onPromotePacketToLegion: (
    instructionId: string,
    title: string,
    objective: string,
    repo: string
  ) => void;
}

const SURFACES: PacketSurface[] = [
  'MV3 Browser Symbiont',
  'Legion Cloud Harness',
  'Telegram 3327',
  'D1 Edge Bus',
  'Greenlane CI',
  'Optimus Verifier',
];

const FORMATIONS: FormationId[] = [
  'sniper',
  'adversarial',
  'phalanx',
  'pipeline',
  'centurion',
  'tournament',
  'sieve',
  'swarm',
];

// Fixed S-curve coordinates in normalized [0..1, 0..1] arena space for the 7 isometric buildings + Quarantine Bay
const ISOMETRIC_STAGE_ANCHORS: Array<{ x: number; y: number }> = [
  { x: 0.13, y: 0.30 }, // 0: RECEIVED (Intake Gate)
  { x: 0.35, y: 0.25 }, // 1: PLANNED (Planning Foundry)
  { x: 0.59, y: 0.25 }, // 2: DRAFTING (Drafting Loom)
  { x: 0.83, y: 0.32 }, // 3: REVIEWING (Geburah Tribunal)
  { x: 0.80, y: 0.68 }, // 4: ACTUATING (Actuation Forge)
  { x: 0.53, y: 0.73 }, // 5: QUEUED (Greenlane Queue)
  { x: 0.25, y: 0.72 }, // 6: VERIFIED_DONE (Verified Vault)
];

const QUARANTINE_ANCHOR = { x: 0.11, y: 0.80 };

interface CorruptLieOverride {
  targetInsId: string;
  forgedVerdict: 'pass';
  forgedHash: string;
  inflatedCountDelta: number;
}

export const RegisterProjectorView: React.FC<RegisterProjectorViewProps> = ({
  initialProjector,
  argonSync,
  onSyncArgon,
  onRefreshState,
  onOpenArgonConsole,
  onPromotePacketToLegion,
}) => {
  const [registerEntries, setRegisterEntries] = useState<OpsRegisterEntry[]>(
    initialProjector.registerEntries
  );
  const [evidenceBySeq, setEvidenceBySeq] = useState<Record<number, OpsEvidenceFile>>(
    initialProjector.evidenceBySeq
  );

  const [rendererMode, setRendererMode] = useState<RendererMode>('movie');
  const [scrubSeq, setScrubSeq] = useState<number | null>(null);
  const [isReplaying, setIsReplaying] = useState(false);
  const [showUnverifiedNarration, setShowUnverifiedNarration] = useState(true);
  const [sseConnected, setSseConnected] = useState(false);

  const [selectedInsId, setSelectedInsId] = useState<string>('INS-TEST-001');
  const [isActuating, setIsActuating] = useState(false);
  const [isReconciling, setIsReconciling] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Adversarial Renderer Lie Injection state (proves R1/R2/R3 Falsifier catches pixel lies!)
  const [lieOverride, setLieOverride] = useState<CorruptLieOverride | null>(null);
  const [reconciliation, setReconciliation] = useState<FalsifierReconciliationReport | null>(null);

  // Mint New Packet controls
  const [showMintForm, setShowMintForm] = useState(false);
  const [mintInsId, setMintInsId] = useState('');
  const [mintTitle, setMintTitle] = useState('');
  const [mintSurface, setMintSurface] = useState<PacketSurface>('MV3 Browser Symbiont');
  const [mintFormation, setMintFormation] = useState<FormationId>('sniper');

  // Sync when parent snapshot refreshes and re-verify R1-R3 when new register entries land (e.g. INS-ARGON-SYNC)
  useEffect(() => {
    setRegisterEntries(initialProjector.registerEntries);
    setEvidenceBySeq(initialProjector.evidenceBySeq);
  }, [initialProjector]);

  // Subscribe to real-time `/api/brain/stream` SSE `register-delta` events (15ms WAL stream)
  useEffect(() => {
    const es = new EventSource('/api/brain/stream');
    es.addEventListener('connected', () => {
      setSseConnected(true);
    });
    es.addEventListener('register-delta', (ev) => {
      try {
        const parsed = JSON.parse((ev as MessageEvent).data) as {
          entry: OpsRegisterEntry;
          evidence: OpsEvidenceFile;
        };
        if (parsed?.entry && typeof parsed.entry.seq === 'number') {
          setRegisterEntries((prev) => {
            if (prev.some((e) => e.seq === parsed.entry.seq)) return prev;
            return [...prev, parsed.entry];
          });
          if (parsed.evidence) {
            setEvidenceBySeq((prev) => ({
              ...prev,
              [parsed.entry.seq]: parsed.evidence,
            }));
          }
        }
      } catch {
        // Ignore malformed frame
      }
    });
    es.onerror = () => {
      setSseConnected(false);
    };
    return () => {
      es.close();
    };
  }, []);

  // Pure deterministic Actor Model reduction
  const truthScene = useMemo(
    () => reduceRegisterToScene(registerEntries, evidenceBySeq, { scrubSeq }),
    [registerEntries, evidenceBySeq, scrubSeq]
  );

  // Apply optional adversarial client pixel lie ONLY when testing the R1-R3 falsifier
  const displayedActors: ProjectorActorState[] = useMemo(() => {
    if (!lieOverride) return truthScene.actors;
    return truthScene.actors.map((actor) => {
      if (actor.insId !== lieOverride.targetInsId) return actor;
      return {
        ...actor,
        verdict: lieOverride.forgedVerdict,
        mood: 'celebrating',
        latestEvidenceSha256: lieOverride.forgedHash,
        speechBubble: `[UNVERIFIED PIXEL CLAIM] Rendered PASS despite register verdict=${actor.verdict}`,
      };
    });
  }, [truthScene.actors, lieOverride]);

  const displayedInFlightCount =
    truthScene.inFlightCount + (lieOverride ? lieOverride.inflatedCountDelta : 0);

  const selectedActor = useMemo(
    () =>
      displayedActors.find((a) => a.insId === selectedInsId) ??
      displayedActors[0] ??
      null,
    [displayedActors, selectedInsId]
  );

  // Movie Replay timer over historical register `seq` frames
  useEffect(() => {
    if (!isReplaying) return;
    if (truthScene.maxSeq <= 1) {
      setIsReplaying(false);
      return;
    }
    const timer = window.setInterval(() => {
      setScrubSeq((prev) => {
        const cur = prev ?? 1;
        if (cur >= truthScene.maxSeq) {
          setIsReplaying(false);
          return null; // Lock back onto Live Head
        }
        playSovereignChime('lock', true);
        return cur + 1;
      });
    }, 620);
    return () => window.clearInterval(timer);
  }, [isReplaying, truthScene.maxSeq]);

  const runReconciliation = useCallback(
    async (
      overrideActors?: ProjectorActorState[],
      overrideInFlight?: number,
      overrideCursor?: number | null
    ) => {
      setIsReconciling(true);
      try {
        const targetActors = overrideActors ?? displayedActors;
        const targetCount = overrideInFlight ?? displayedInFlightCount;
        const claims: RenderedActorClaim[] = targetActors.map((a) => ({
          insId: a.insId,
          seq: a.latestSeq,
          stage: a.stage,
          verdict: a.verdict,
          revoked: a.revoked,
          evidenceSha256: a.latestEvidenceSha256,
        }));

        const res = await fetch('/api/projector/reconcile', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            cursorSeq: overrideCursor !== undefined ? overrideCursor : scrubSeq,
            renderedInFlightCount: targetCount,
            renderedActors: claims,
          }),
        });
        const data = await res.json();
        if (data.reconciliation) {
          const rep = data.reconciliation as FalsifierReconciliationReport;
          setReconciliation(rep);
          playSovereignChime(rep.passed ? 'execute' : 'refuse', true);
          setStatusMessage(
            rep.passed
              ? `R1–R3 Reconciliation PASSED at seq #${rep.cursorSeq}: all ${rep.r1HashAgreement.checkedFiles} .ops/evidence SHA-256 digests, verdicts, and in-flight counts match disk.`
              : `D.1 FALSIFIER REFUSED RENDERER: ${rep.discrepancies.length} pixel claim mismatch(es) detected against .ops/register.jsonl!`
          );
        }
      } finally {
        setIsReconciling(false);
      }
    },
    [displayedActors, displayedInFlightCount, scrubSeq]
  );

  // Run initial R1-R3 check on mount so the Captain immediately sees verified reconciliation
  const didInitialReconcileRef = useRef(false);
  useEffect(() => {
    if (!didInitialReconcileRef.current && truthScene.actors.length > 0) {
      didInitialReconcileRef.current = true;
      runReconciliation(truthScene.actors, truthScene.inFlightCount, null);
    }
  }, [truthScene.actors, truthScene.inFlightCount, runReconciliation]);

  const handleInjectRendererLie = async () => {
    const target =
      truthScene.actors.find((a) => a.verdict === 'fail') ?? truthScene.actors[0];
    if (!target) return;

    const forged: CorruptLieOverride = {
      targetInsId: target.insId,
      forgedVerdict: 'pass',
      forgedHash: 'deadbeefcafebabe000000000000000000000000000000000000000000000000',
      inflatedCountDelta: 2,
    };
    setLieOverride(forged);
    setSelectedInsId(target.insId);

    const corruptedActors = truthScene.actors.map((a) =>
      a.insId === target.insId
        ? {
            ...a,
            verdict: 'pass' as const,
            latestEvidenceSha256: forged.forgedHash,
          }
        : a
    );
    await runReconciliation(
      corruptedActors,
      truthScene.inFlightCount + forged.inflatedCountDelta,
      scrubSeq
    );
  };

  const handleRestoreTruth = async () => {
    setLieOverride(null);
    await runReconciliation(truthScene.actors, truthScene.inFlightCount, scrubSeq);
  };

  const handleActuate = async (
    mode: 'ADVANCE_STAGE' | 'EXIT_ZERO_TRAP' | 'CLASS_REPAIR_GREEN' | 'REVOKE_LEASE' | 'MINT_PACKET',
    customParams?: {
      insId?: string;
      title?: string;
      surface?: PacketSurface;
      formation?: FormationId;
    }
  ) => {
    setIsActuating(true);
    setScrubSeq(null); // Follow live head on new actuation
    setLieOverride(null);
    try {
      const targetIns = customParams?.insId ?? selectedActor?.insId ?? 'INS-TEST-001';
      const res = await fetch('/api/projector/actuate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode,
          insId: targetIns,
          title: customParams?.title,
          surface: customParams?.surface ?? selectedActor?.surface ?? 'MV3 Browser Symbiont',
          formation: customParams?.formation ?? selectedActor?.formation ?? 'sniper',
          repo: selectedActor?.repo ?? 'chidionyema/idp',
        }),
      });
      const data = await res.json();
      if (data.projector) {
        setRegisterEntries(data.projector.registerEntries);
        setEvidenceBySeq(data.projector.evidenceBySeq);
        if (data.entry?.insId) {
          setSelectedInsId(data.entry.insId);
        }
        const nextScene = reduceRegisterToScene(
          data.projector.registerEntries,
          data.projector.evidenceBySeq
        );
        await runReconciliation(nextScene.actors, nextScene.inFlightCount, null);
        setStatusMessage(
          `Wrote ${data.entry.evidenceFile} (sha256:${data.entry.evidenceSha256.slice(0, 12)}…) → ${data.entry.insId} @ ${data.entry.stage} [${data.entry.verdict.toUpperCase()}]`
        );
      }
    } finally {
      setIsActuating(false);
    }
  };

  const handleMintSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mintTitle.trim()) {
      setStatusMessage('Provide a concise packet objective before minting.');
      return;
    }
    await handleActuate('MINT_PACKET', {
      insId: mintInsId.trim() || undefined,
      title: mintTitle.trim(),
      surface: mintSurface,
      formation: mintFormation,
    });
    setMintInsId('');
    setMintTitle('');
    setShowMintForm(false);
  };

  // ==========================================================================
  // ISOMETRIC 2.5D VIRTUAL WORLD CANVAS RENDERER (Factorio / Face & Fleet)
  // Mounts loop cleanly; reads latest actors via useRef (zero setState in rAF!)
  // ==========================================================================
  const isoCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const actorsRef = useRef<ProjectorActorState[]>(displayedActors);
  const selectedInsRef = useRef<string | null>(selectedActor?.insId ?? null);
  const avatarPosCacheRef = useRef<Map<string, { x: number; y: number }>>(new Map());
  const avatarHitBoxesRef = useRef<Array<{ insId: string; cx: number; cy: number; r: number }>>([]);

  useEffect(() => {
    actorsRef.current = displayedActors;
    selectedInsRef.current = selectedActor?.insId ?? null;
  }, [displayedActors, selectedActor]);

  useEffect(() => {
    if (rendererMode !== 'isometric' && rendererMode !== 'split3327') return;
    const canvas = isoCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let timerId = 0;
    let tick = 0;

    const drawIsometricBox = (
      cx: number,
      cy: number,
      halfW: number,
      halfH: number,
      extrudeH: number,
      topColor: string,
      leftColor: string,
      rightColor: string,
      strokeColor: string
    ) => {
      // Top diamond
      ctx.beginPath();
      ctx.moveTo(cx, cy - extrudeH - halfH);
      ctx.lineTo(cx + halfW, cy - extrudeH);
      ctx.lineTo(cx, cy - extrudeH + halfH);
      ctx.lineTo(cx - halfW, cy - extrudeH);
      ctx.closePath();
      ctx.fillStyle = topColor;
      ctx.fill();
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = 1.2;
      ctx.stroke();

      // Left face
      ctx.beginPath();
      ctx.moveTo(cx - halfW, cy - extrudeH);
      ctx.lineTo(cx, cy - extrudeH + halfH);
      ctx.lineTo(cx, cy + halfH);
      ctx.lineTo(cx - halfW, cy);
      ctx.closePath();
      ctx.fillStyle = leftColor;
      ctx.fill();
      ctx.stroke();

      // Right face
      ctx.beginPath();
      ctx.moveTo(cx + halfW, cy - extrudeH);
      ctx.lineTo(cx, cy - extrudeH + halfH);
      ctx.lineTo(cx, cy + halfH);
      ctx.lineTo(cx + halfW, cy);
      ctx.closePath();
      ctx.fillStyle = rightColor;
      ctx.fill();
      ctx.stroke();
    };

    const renderWorldFrame = () => {
      tick += 1;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const rect = canvas.getBoundingClientRect();
      const width = Math.max(640, Math.floor(rect.width || 920));
      const height = Math.max(380, Math.floor(rect.height || 430));
      if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
        canvas.width = width * dpr;
        canvas.height = height * dpr;
      }

      ctx.save();
      ctx.scale(dpr, dpr);

      // 1. Deep Sovereign Arena Floor
      ctx.fillStyle = '#060B16';
      ctx.fillRect(0, 0, width, height);

      // Subtle isometric floor lattice
      ctx.strokeStyle = 'rgba(51, 65, 85, 0.28)';
      ctx.lineWidth = 1;
      const step = 48;
      for (let gx = -height; gx < width + height; gx += step) {
        ctx.beginPath();
        ctx.moveTo(gx, 0);
        ctx.lineTo(gx + height * 1.4, height);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(gx, 0);
        ctx.lineTo(gx - height * 1.4, height);
        ctx.stroke();
      }

      const actors = actorsRef.current;
      const selectedId = selectedInsRef.current;

      // 2. Conveyor Bus Circuit Paths connecting Stages 0 -> 6
      ctx.save();
      ctx.strokeStyle = 'rgba(14, 165, 233, 0.35)';
      ctx.lineWidth = 4;
      ctx.beginPath();
      ISOMETRIC_STAGE_ANCHORS.forEach((pt, idx) => {
        const px = pt.x * width;
        const py = pt.y * height;
        if (idx === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      });
      ctx.stroke();

      // Animated WAL data pulse beads moving along circuit
      ctx.strokeStyle = 'rgba(245, 158, 11, 0.65)';
      ctx.lineWidth = 2;
      ctx.setLineDash([8, 18]);
      ctx.lineDashOffset = -(tick * 3);
      ctx.stroke();
      ctx.restore();

      // 3. Render 7 Architectural Stage Buildings + Quarantine Bay
      PIPELINE_STAGES.forEach((stage, idx) => {
        const anchor = ISOMETRIC_STAGE_ANCHORS[idx];
        const bx = anchor.x * width;
        const by = anchor.y * height;
        const meta = STAGE_METADATA[stage];

        const stageActors = actors.filter((a) => a.revoked === 0 && a.stageIndex === idx);
        const hasFail = stageActors.some((a) => a.verdict === 'fail');
        const isVault = stage === 'VERIFIED_DONE';

        // Building perimeter glow if failing or vault active
        if (hasFail) {
          ctx.beginPath();
          ctx.ellipse(bx, by + 4, 58, 30, 0, 0, Math.PI * 2);
          ctx.fillStyle = 'rgba(244, 63, 94, 0.18)';
          ctx.fill();
          ctx.strokeStyle = 'rgba(244, 63, 94, 0.75)';
          ctx.lineWidth = 1.5;
          ctx.stroke();
        } else if (isVault && stageActors.length > 0) {
          ctx.beginPath();
          ctx.ellipse(bx, by + 4, 56, 28, 0, 0, Math.PI * 2);
          ctx.fillStyle = 'rgba(16, 185, 129, 0.14)';
          ctx.fill();
        }

        drawIsometricBox(
          bx,
          by,
          44,
          22,
          24,
          hasFail ? '#4C1D24' : isVault ? '#0F2E26' : '#162238',
          hasFail ? '#321017' : '#0D1526',
          hasFail ? '#3F151D' : '#111C30',
          hasFail ? '#F43F5E' : isVault ? '#10B981' : '#334155'
        );

        // Stack Building Name + Stage Count cleanly below the isometric base (leaves airspace above free for avatar speech bubbles!)
        ctx.fillStyle = hasFail ? '#FDA4AF' : isVault ? '#6EE7B7' : '#E2E8F0';
        ctx.font = '600 11px "Plus Jakarta Sans", system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(`0${idx + 1} · ${meta.buildingName}`, bx, by + 33);

        ctx.fillStyle = '#94A3B8';
        ctx.font = '500 10px "JetBrains Mono", monospace';
        ctx.fillText(`${stage} (${stageActors.length})`, bx, by + 47);
      });

      // Quarantine Bay for `revoked=1` actors
      const qx = QUARANTINE_ANCHOR.x * width;
      const qy = QUARANTINE_ANCHOR.y * height;
      drawIsometricBox(qx, qy, 34, 17, 14, '#1E1B2E', '#12101C', '#171424', '#64748B');
      ctx.fillStyle = '#94A3B8';
      ctx.font = '500 10px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText('REVOKED BAY', qx, qy + 28);

      // 4. Render Articulated Agent Avatars (Interpolated smoothly across stages)
      const hitBoxes: Array<{ insId: string; cx: number; cy: number; r: number }> = [];
      const slotCounters = new Map<string, number>();

      actors.forEach((actor) => {
        const slotKey = actor.revoked === 1 ? 'REVOKED' : `STAGE_${actor.stageIndex}`;
        const slotIdx = slotCounters.get(slotKey) ?? 0;
        slotCounters.set(slotKey, slotIdx + 1);

        const baseAnchor =
          actor.revoked === 1
            ? QUARANTINE_ANCHOR
            : ISOMETRIC_STAGE_ANCHORS[Math.max(0, Math.min(6, actor.stageIndex))];

        // Offset multiple avatars around the same building cleanly so they never overlap
        const angle = slotIdx * 2.1 + 0.6;
        const spreadR = slotIdx === 0 ? 0 : 28 + slotIdx * 8;
        const targetX = baseAnchor.x * width + Math.cos(angle) * spreadR;
        const targetY = baseAnchor.y * height - 18 + Math.sin(angle) * (spreadR * 0.55);

        const prev = avatarPosCacheRef.current.get(actor.insId) ?? { x: targetX, y: targetY };
        const curX = prev.x + (targetX - prev.x) * 0.26;
        const curY = prev.y + (targetY - prev.y) * 0.26;
        avatarPosCacheRef.current.set(actor.insId, { x: curX, y: curY });

        const isMoving = Math.hypot(targetX - curX, targetY - curY) > 1.5;
        const isSelected = actor.insId === selectedId;

        const ringColor =
          actor.revoked === 1
            ? '#64748B'
            : actor.verdict === 'fail'
              ? '#F43F5E'
              : actor.verdict === 'pass'
                ? '#10B981'
                : '#F59E0B';

        const jitterX =
          actor.mood === 'failing' ? Math.sin(tick * 1.9) * 2.2 : 0;
        const bounceY =
          actor.mood === 'celebrating'
            ? Math.abs(Math.sin(tick * 0.35)) * -4
            : isMoving
              ? Math.abs(Math.sin(tick * 0.8)) * -3
              : 0;

        const ax = curX + jitterX;
        const ay = curY + bounceY;

        hitBoxes.push({ insId: actor.insId, cx: ax, cy: ay - 10, r: 22 });

        // Status Halo Ring under avatar's feet
        ctx.beginPath();
        ctx.ellipse(ax, ay + 6, isSelected ? 19 : 14, isSelected ? 9.5 : 7, 0, 0, Math.PI * 2);
        ctx.fillStyle = isSelected ? 'rgba(245, 158, 11, 0.28)' : 'rgba(15, 23, 42, 0.75)';
        ctx.fill();
        ctx.strokeStyle = isSelected ? '#FBBF24' : ringColor;
        ctx.lineWidth = isSelected ? 2.2 : 1.6;
        ctx.stroke();

        // Articulated Legs
        const stride = isMoving ? Math.sin(tick * 0.9) * 4 : 0;
        ctx.strokeStyle = actor.revoked === 1 ? '#475569' : '#CBD5E1';
        ctx.lineWidth = 2.2;
        ctx.beginPath();
        ctx.moveTo(ax - 3, ay - 2);
        ctx.lineTo(ax - 4 - stride, ay + 5);
        ctx.moveTo(ax + 3, ay - 2);
        ctx.lineTo(ax + 4 + stride, ay + 5);
        ctx.stroke();

        // Armored Sovereign Torso
        ctx.fillStyle =
          actor.revoked === 1
            ? '#334155'
            : actor.verdict === 'fail'
              ? '#E11D48'
              : actor.verdict === 'pass'
                ? '#059669'
                : '#D97706';
        ctx.beginPath();
        ctx.roundRect(ax - 7, ay - 16, 14, 14, 4);
        ctx.fill();
        ctx.strokeStyle = '#F8FAFC';
        ctx.lineWidth = 1;
        ctx.stroke();

        // Helmet & Visor
        ctx.fillStyle = '#0F172A';
        ctx.beginPath();
        ctx.arc(ax, ay - 22, 6.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = ringColor;
        ctx.lineWidth = 1.4;
        ctx.stroke();

        // Glowing Visor Slit
        ctx.fillStyle = actor.revoked === 1 ? '#64748B' : '#38BDF8';
        ctx.fillRect(ax - 4, ay - 23.5, 8, 2.5);

        // Actor Callsign Tag
        ctx.fillStyle = isSelected ? '#FDE68A' : '#F1F5F9';
        ctx.font = '600 10px "JetBrains Mono", monospace';
        ctx.textAlign = 'center';
        ctx.fillText(actor.insId, ax, ay + 18);

        // Compact Speech Bubble for selected or failing actors (auto-sized to exact text width)
        if (isSelected || actor.verdict === 'fail') {
          const snippet =
            actor.speechBubble.length > 34
              ? `${actor.speechBubble.slice(0, 34)}…`
              : actor.speechBubble;
          ctx.font = '500 10px "JetBrains Mono", monospace';
          const tw = Math.ceil(ctx.measureText(snippet).width) + 20;
          const bx = Math.max(tw / 2 + 8, Math.min(width - tw / 2 - 8, ax));
          const by = Math.max(20, ay - 44);

          ctx.fillStyle =
            actor.verdict === 'fail'
              ? 'rgba(69, 10, 18, 0.95)'
              : 'rgba(15, 23, 42, 0.95)';
          ctx.strokeStyle = actor.verdict === 'fail' ? '#F43F5E' : '#38BDF8';
          ctx.lineWidth = 1.2;
          ctx.beginPath();
          ctx.roundRect(bx - tw / 2, by - 11, tw, 20, 5);
          ctx.fill();
          ctx.stroke();

          ctx.fillStyle = actor.verdict === 'fail' ? '#FECDD3' : '#E0F2FE';
          ctx.textAlign = 'center';
          ctx.fillText(snippet, bx, by + 3);
        }
      });

      avatarHitBoxesRef.current = hitBoxes;
      ctx.restore();
    };

    // Initial immediate paint + bounded 12fps loop (100ms budget per architecture spec!)
    renderWorldFrame();
    timerId = window.setInterval(renderWorldFrame, 90);

    return () => {
      window.clearInterval(timerId);
    };
  }, [rendererMode]);

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = isoCanvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    for (const box of avatarHitBoxesRef.current) {
      if (Math.hypot(x - box.cx, y - box.cy) <= box.r + 8) {
        setSelectedInsId(box.insId);
        playSovereignChime('lock', true);
        return;
      }
    }
  };

  const telegram3327Pin = useMemo(
    () => projectTelegram3327PinnedMessage(truthScene, reconciliation),
    [truthScene, reconciliation]
  );

  const falsifierFailed = reconciliation !== null && !reconciliation.passed;

  return (
    <div
      className={`space-y-6 transition-colors ${
        falsifierFailed
          ? 'p-4 rounded-2xl border-2 border-rose-500 bg-rose-950/10'
          : ''
      }`}
    >
      {/* Argon Continuity & Governed lane/* Sync Strip */}
      <ArgonSyncPanel
        argonSync={argonSync}
        onTriggerSync={async (branch) => {
          setScrubSeq(null);
          setLieOverride(null);
          const out = await onSyncArgon(branch);
          if (out.ok) {
            setSelectedInsId('INS-ARGON-SYNC');
            // Fetch fresh projector state and reconcile R1-R3 immediately so INS-ARGON-SYNC is verified green
            try {
              const projRes = await fetch('/api/projector/state');
              if (projRes.ok) {
                const projData = await projRes.json();
                setRegisterEntries(projData.registerEntries);
                setEvidenceBySeq(projData.evidenceBySeq);
                const nextScene = reduceRegisterToScene(
                  projData.registerEntries,
                  projData.evidenceBySeq
                );
                await runReconciliation(nextScene.actors, nextScene.inFlightCount, null);
              }
            } catch {
              // Parent refresh handles fallback
            }
          }
          return out;
        }}
        onRefreshState={onRefreshState}
        variant="compact"
        onOpenFullConsole={onOpenArgonConsole}
      />

      {/* Top Architecture Header & Swappable Renderer Selector */}
      <section className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 dark:text-slate-400 font-mono tabular-nums">
              <span>.ops/register.jsonl</span>
              <span aria-hidden="true">·</span>
              <span>seq #{truthScene.cursorSeq}/{truthScene.maxSeq}</span>
              <span aria-hidden="true">·</span>
              <span>{sseConnected ? 'SSE WAL Connected (15ms)' : 'Disk Snapshot Active'}</span>
              <span aria-hidden="true">·</span>
              <span>{displayedInFlightCount} packets in flight</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
              Face &amp; Fleet — Register Projector
            </h1>
            <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 max-w-3xl">
              Render the register, not the narrative. Every actor, mood, subtitle line, and building alarm is a pure projection of signed <code className="font-mono text-amber-600 dark:text-amber-400">.ops/evidence/*.json</code> records—continuously falsified by R1–R3 reconciliation.
            </p>
          </div>

          {/* Swappable Projection Mode Selector (Single Row) */}
          <div
            role="group"
            aria-label="Select Register Renderer Projection"
            className="flex flex-wrap sm:flex-nowrap items-center gap-1 p-1 bg-slate-100 dark:bg-[#050811] border border-slate-200 dark:border-slate-800 rounded-xl self-start shrink-0"
          >
            <button
              type="button"
              onClick={() => setRendererMode('movie')}
              className={`inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg transition-colors whitespace-nowrap shrink-0 ${
                rendererMode === 'movie'
                  ? 'bg-slate-900 text-white dark:bg-amber-400 dark:text-slate-950 font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              <Film className="w-3.5 h-3.5" aria-hidden="true" />
              01. Movie
            </button>
            <button
              type="button"
              onClick={() => setRendererMode('isometric')}
              className={`inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg transition-colors whitespace-nowrap shrink-0 ${
                rendererMode === 'isometric'
                  ? 'bg-slate-900 text-white dark:bg-amber-400 dark:text-slate-950 font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              <Boxes className="w-3.5 h-3.5" aria-hidden="true" />
              02. Isometric World
            </button>
            <button
              type="button"
              onClick={() => setRendererMode('split3327')}
              className={`inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg transition-colors whitespace-nowrap shrink-0 ${
                rendererMode === 'split3327'
                  ? 'bg-slate-900 text-white dark:bg-amber-400 dark:text-slate-950 font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              <Smartphone className="w-3.5 h-3.5" aria-hidden="true" />
              03. World + 3327 Pin
            </button>
          </div>
        </div>

        {/* Time Scrubber Row + Live Packet Actuation Row */}
        <div className="pt-3 border-t border-slate-200 dark:border-slate-800 space-y-3">
          {/* Row 1: Replayable Sequence Scrubber */}
          <div className="flex flex-wrap items-center gap-2.5">
            <button
              type="button"
              onClick={() => {
                setIsReplaying(false);
                setScrubSeq((prev) => Math.max(1, (prev ?? truthScene.maxSeq) - 1));
              }}
              aria-label="Step back one register sequence"
              className="p-2 text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 rounded-lg"
            >
              <SkipBack className="w-3.5 h-3.5" />
            </button>

            <div className="flex items-center gap-2 min-w-[210px] sm:min-w-[260px] flex-1 max-w-md">
              <label
                htmlFor="register-seq-scrubber"
                className="text-xs font-mono text-slate-600 dark:text-slate-300 whitespace-nowrap tabular-nums"
              >
                Seq {truthScene.cursorSeq}/{truthScene.maxSeq}
              </label>
              <input
                id="register-seq-scrubber"
                type="range"
                min={1}
                max={Math.max(1, truthScene.maxSeq)}
                value={truthScene.cursorSeq}
                onChange={(e) => {
                  setIsReplaying(false);
                  const val = Number(e.target.value);
                  setScrubSeq(val >= truthScene.maxSeq ? null : val);
                }}
                className="w-full accent-amber-400 cursor-pointer"
              />
            </div>

            <button
              type="button"
              onClick={() => {
                setIsReplaying(false);
                setScrubSeq((prev) => {
                  const next = (prev ?? truthScene.maxSeq) + 1;
                  return next >= truthScene.maxSeq ? null : next;
                });
              }}
              aria-label="Step forward one register sequence"
              className="p-2 text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 rounded-lg"
            >
              <SkipForward className="w-3.5 h-3.5" />
            </button>

            {!isReplaying ? (
              <button
                type="button"
                onClick={() => {
                  setScrubSeq(1);
                  setIsReplaying(true);
                }}
                className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 rounded-lg whitespace-nowrap shrink-0"
              >
                <Play className="w-3.5 h-3.5 text-amber-500" aria-hidden="true" />
                Replay Movie
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setIsReplaying(false)}
                className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-500 rounded-lg whitespace-nowrap shrink-0"
              >
                <Square className="w-3.5 h-3.5" aria-hidden="true" />
                Stop Replay
              </button>
            )}

            <button
              type="button"
              onClick={() => {
                setIsReplaying(false);
                setScrubSeq(null);
              }}
              className={`px-3 py-2 text-xs font-mono rounded-lg border transition-colors whitespace-nowrap shrink-0 ${
                scrubSeq === null
                  ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/40 font-semibold'
                  : 'bg-slate-100 dark:bg-slate-900 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-800'
              }`}
            >
              {scrubSeq === null ? 'LIVE HEAD' : 'Jump to Live Head'}
            </button>
          </div>

          {/* Live Packet Actuators (Writes Real .ops/evidence/*.json + .ops/register.jsonl) */}
          <div className="flex flex-wrap items-center gap-2">
            <label htmlFor="target-packet-select" className="sr-only">
              Active Packet Target
            </label>
            <select
              id="target-packet-select"
              value={selectedActor?.insId ?? ''}
              onChange={(e) => setSelectedInsId(e.target.value)}
              className="px-2.5 py-2 text-xs font-mono bg-slate-50 dark:bg-[#050811] border border-slate-200 dark:border-slate-800 rounded-lg text-slate-900 dark:text-slate-100"
            >
              {displayedActors.map((a) => (
                <option key={a.insId} value={a.insId}>
                  {a.insId} ({a.stage})
                </option>
              ))}
            </select>

            <button
              type="button"
              disabled={isActuating}
              onClick={() => handleActuate('ADVANCE_STAGE')}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 disabled:opacity-50 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
              Advance Stage
            </button>

            <button
              type="button"
              disabled={isActuating}
              onClick={() => handleActuate('EXIT_ZERO_TRAP')}
              className="px-3 py-2 text-xs font-medium text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-950/40 hover:bg-rose-100 dark:hover:bg-rose-900/50 border border-rose-200 dark:border-rose-800/70 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              Inject Exit-0 / 0-Collected Trap
            </button>

            <button
              type="button"
              disabled={isActuating}
              onClick={() => handleActuate('CLASS_REPAIR_GREEN')}
              className="px-3 py-2 text-xs font-medium text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/40 hover:bg-emerald-100 dark:hover:bg-emerald-900/50 border border-emerald-200 dark:border-emerald-800/70 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              Run Green Tests (31)
            </button>

            <button
              type="button"
              disabled={isActuating}
              onClick={() => handleActuate('REVOKE_LEASE')}
              className="px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              Revoke Lease
            </button>

            <button
              type="button"
              onClick={() => setShowMintForm((v) => !v)}
              className="inline-flex items-center gap-1 px-3 py-2 text-xs font-medium text-cyan-700 dark:text-cyan-300 bg-cyan-50 dark:bg-cyan-950/30 border border-cyan-200 dark:border-cyan-800/70 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Plus className="w-3.5 h-3.5" aria-hidden="true" />
              Mint Packet
            </button>
          </div>
        </div>

        {/* Optional Mint New INS-XXXXX Packet Form */}
        {showMintForm && (
          <form
            onSubmit={handleMintSubmit}
            className="p-4 bg-slate-50 dark:bg-[#050811] border border-slate-200 dark:border-slate-800 rounded-xl grid grid-cols-1 sm:grid-cols-5 gap-3 items-end"
          >
            <div>
              <label htmlFor="mint-ins-id" className="block text-[11px] font-medium text-slate-600 dark:text-slate-400 mb-1">
                Packet ID (optional)
              </label>
              <input
                id="mint-ins-id"
                type="text"
                value={mintInsId}
                onChange={(e) => setMintInsId(e.target.value)}
                placeholder="INS-LIVE-009"
                className="w-full px-3 py-2 text-xs font-mono bg-white dark:bg-[#0B101D] border border-slate-300 dark:border-slate-700 rounded-lg"
              />
            </div>
            <div className="sm:col-span-2">
              <label htmlFor="mint-title" className="block text-[11px] font-medium text-slate-600 dark:text-slate-400 mb-1">
                Packet Objective (Required)
              </label>
              <input
                id="mint-title"
                type="text"
                required
                value={mintTitle}
                onChange={(e) => setMintTitle(e.target.value)}
                placeholder="Verify Mailjet fail-closed enquiry receipt on Meridian"
                className="w-full px-3 py-2 text-xs bg-white dark:bg-[#0B101D] border border-slate-300 dark:border-slate-700 rounded-lg"
              />
            </div>
            <div>
              <label htmlFor="mint-surface" className="block text-[11px] font-medium text-slate-600 dark:text-slate-400 mb-1">
                Router Surface
              </label>
              <select
                id="mint-surface"
                value={mintSurface}
                onChange={(e) => setMintSurface(e.target.value as PacketSurface)}
                className="w-full px-2.5 py-2 text-xs bg-white dark:bg-[#0B101D] border border-slate-300 dark:border-slate-700 rounded-lg"
              >
                {SURFACES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1">
                <label htmlFor="mint-formation" className="block text-[11px] font-medium text-slate-600 dark:text-slate-400 mb-1">
                  Formation
                </label>
                <select
                  id="mint-formation"
                  value={mintFormation}
                  onChange={(e) => setMintFormation(e.target.value as FormationId)}
                  className="w-full px-2.5 py-2 text-xs bg-white dark:bg-[#0B101D] border border-slate-300 dark:border-slate-700 rounded-lg"
                >
                  {FORMATIONS.map((f) => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="submit"
                disabled={isActuating}
                className="px-3.5 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg whitespace-nowrap shrink-0"
              >
                Mint in D1
              </button>
            </div>
          </form>
        )}

        {statusMessage && (
          <div
            role="status"
            className={`px-3.5 py-2.5 rounded-lg text-xs font-mono border ${
              falsifierFailed
                ? 'bg-rose-50 dark:bg-rose-950/40 text-rose-800 dark:text-rose-200 border-rose-300 dark:border-rose-800'
                : 'bg-slate-50 dark:bg-[#050811] text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-800'
            }`}
          >
            {statusMessage}
          </div>
        )}
      </section>

      {/* ==================================================================== */}
      {/* RENDERER 01: CINEMATIC TIMELINE ("THE MOVIE")                        */}
      {/* ==================================================================== */}
      {rendererMode === 'movie' && (
        <section
          aria-label="Cinematic Register Pipeline"
          className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-5"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                01. Cinematic Pipeline — Seven-Stage Evidence Movie
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Actors glide across stages strictly as <code className="font-mono">.ops/register.jsonl</code> records append. Click any actor track to inspect its full SHA-256 evidence chain.
              </p>
            </div>

            <button
              type="button"
              onClick={() => setShowUnverifiedNarration((v) => !v)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors whitespace-nowrap ${
                showUnverifiedNarration
                  ? 'bg-amber-400/15 text-amber-700 dark:text-amber-300 border-amber-500/40'
                  : 'bg-slate-100 dark:bg-slate-900 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-800'
              }`}
            >
              {showUnverifiedNarration
                ? 'Agent Narration Track: Visible (Labeled Unverified)'
                : 'Agent Narration Track: Hidden'}
            </button>
          </div>

          {/* 7-Stage Pipeline Column Header */}
          <div className="hidden lg:grid lg:grid-cols-7 gap-2 pb-2 border-b border-slate-200 dark:border-slate-800">
            {PIPELINE_STAGES.map((stage, idx) => {
              const meta = STAGE_METADATA[stage];
              const count = displayedActors.filter(
                (a) => a.revoked === 0 && a.stageIndex === idx
              ).length;
              return (
                <div
                  key={stage}
                  className="px-2.5 py-2 rounded-lg bg-slate-50 dark:bg-[#050811] border border-slate-200/80 dark:border-slate-800/80"
                >
                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 dark:text-slate-400 tabular-nums">
                    <span>0{idx + 1}</span>
                    <span>{count} active</span>
                  </div>
                  <div className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate">
                    {meta.buildingName}
                  </div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                    {stage}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Horizontal Actor Lanes + Subtitle Script */}
          <div className="space-y-3">
            {displayedActors.map((actor) => {
              const lastScript = actor.scriptLines[actor.scriptLines.length - 1];
              const isSelected = selectedActor?.insId === actor.insId;

              return (
                <div
                  key={actor.insId}
                  onClick={() => setSelectedInsId(actor.insId)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      setSelectedInsId(actor.insId);
                    }
                  }}
                  className={`p-4 rounded-xl border transition-colors cursor-pointer space-y-3 ${
                    actor.verdict === 'fail'
                      ? 'bg-rose-50/50 dark:bg-rose-950/20 border-rose-300 dark:border-rose-800/80'
                      : isSelected
                        ? 'bg-amber-50/40 dark:bg-[#10182B] border-amber-400 dark:border-amber-500/60'
                        : 'bg-slate-50/70 dark:bg-[#070C18] border-slate-200 dark:border-slate-800/90 hover:border-slate-300 dark:hover:border-slate-700'
                  }`}
                >
                  {/* Top Actor Identity & Verdict Row (Zero-Pill clean metadata) */}
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      <span className="font-mono font-semibold text-slate-900 dark:text-slate-100">
                        {actor.insId}
                      </span>
                      <span aria-hidden="true" className="text-slate-400">·</span>
                      <span className="font-medium text-slate-800 dark:text-slate-200">
                        {actor.title}
                      </span>
                      <span aria-hidden="true" className="text-slate-400">·</span>
                      <span className="font-mono text-slate-500 dark:text-slate-400">
                        {actor.surface} / {actor.formation}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-xs font-mono tabular-nums">
                      {actor.revoked === 1 ? (
                        <span className="inline-flex items-center gap-1 text-slate-500 dark:text-slate-400 font-semibold">
                          <XOctagon className="w-3.5 h-3.5" aria-hidden="true" />
                          REVOKED (epoch {actor.leaseEpoch})
                        </span>
                      ) : actor.verdict === 'fail' ? (
                        <span className="inline-flex items-center gap-1 text-rose-600 dark:text-rose-400 font-semibold">
                          <AlertTriangle className="w-3.5 h-3.5" aria-hidden="true" />
                          VERDICT: FAIL
                        </span>
                      ) : actor.verdict === 'pass' ? (
                        <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-semibold">
                          <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />
                          VERDICT: PASS
                        </span>
                      ) : (
                        <span className="text-amber-600 dark:text-amber-400 font-semibold">
                          AWAITING SEAL
                        </span>
                      )}
                      <span aria-hidden="true" className="text-slate-500">·</span>
                      <span className="text-slate-500 dark:text-slate-400">
                        sha256:{actor.latestEvidenceSha256.slice(0, 10)}…
                      </span>
                    </div>
                  </div>

                  {/* 7-Stage Visual Motion Track (Exact 1/7th Column Compositor Transform) */}
                  <div className="relative h-9 bg-slate-200/70 dark:bg-[#050811] border border-slate-300/70 dark:border-slate-800 rounded-lg px-3 flex items-center overflow-hidden">
                    <div className="w-full grid grid-cols-7 text-[10px] font-mono text-slate-400 dark:text-slate-600 pointer-events-none select-none text-center">
                      {PIPELINE_STAGES.map((st) => (
                        <span key={st} className="truncate px-1">
                          {st}
                        </span>
                      ))}
                    </div>

                    {/* Compositor-animated Actor Puck: width = 1/7th track, translateX(stageIndex * 100%) lands dead-center in column */}
                    <div
                      style={{
                        width: 'calc((100% - 1.5rem) / 7)',
                        transform: `translateX(${actor.stageIndex * 100}%)`,
                      }}
                      className={`absolute left-3 top-1.5 bottom-1.5 transition-transform duration-200 ease-out flex items-center justify-center px-2 rounded-md font-mono text-[11px] font-semibold shadow-sm truncate ${
                        actor.verdict === 'fail'
                          ? 'bg-rose-600 text-white'
                          : actor.revoked === 1
                            ? 'bg-slate-700 text-slate-200'
                            : 'bg-amber-400 text-slate-950'
                      }`}
                    >
                      <span className="truncate">{actor.stage}</span>
                    </div>
                  </div>

                  {/* Truthful Evidence Script Subtitle Line */}
                  {lastScript && (
                    <div className="space-y-1 font-mono text-xs">
                      <div
                        className={
                          actor.verdict === 'fail'
                            ? 'text-rose-700 dark:text-rose-300'
                            : 'text-cyan-800 dark:text-cyan-300'
                        }
                      >
                        &gt; {lastScript.formattedLine}
                      </div>
                      {showUnverifiedNarration && lastScript.agentNarrationUnverified && (
                        <div className="text-[11px] text-slate-500 dark:text-slate-400">
                          [agent narration · UNVERIFIED]: &ldquo;{lastScript.agentNarrationUnverified}&rdquo;
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* ==================================================================== */}
      {/* RENDERER 02 & 03: ISOMETRIC 2.5D VIRTUAL WORLD (+ 3327 POCKET PIN)   */}
      {/* ==================================================================== */}
      {(rendererMode === 'isometric' || rendererMode === 'split3327') && (
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
          <div
            className={`${
              rendererMode === 'split3327' ? 'lg:col-span-8' : 'lg:col-span-12'
            } bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-4 space-y-3 flex flex-col`}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                  02. Isometric Stage World — Live Formation Avatars
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Buildings represent packet stages (01 Intake Gate → 07 Verified Vault). Click any walking avatar to inspect its signed evidence script.
                </p>
              </div>
              <div className="text-xs font-mono text-slate-500 dark:text-slate-400 tabular-nums">
                Selected: <span className="text-amber-500 font-semibold">{selectedActor?.insId}</span>
              </div>
            </div>

            <div className="relative w-full h-[430px] rounded-xl overflow-hidden border border-slate-800 bg-[#060B16]">
              <canvas
                ref={isoCanvasRef}
                data-testid="isometric-world-canvas"
                onClick={handleCanvasClick}
                aria-label="Isometric virtual world showing INS packet avatars moving between seven pipeline stage buildings"
                className="w-full h-full block cursor-pointer"
              />
            </div>
          </div>

          {rendererMode === 'split3327' && (
            <div className="lg:col-span-4 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 flex flex-col justify-between space-y-4">
              <div className="space-y-2">
                <div className="text-xs font-mono text-amber-600 dark:text-amber-400">
                  TELEGRAM 3327 · POCKET PROJECTION
                </div>
                <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                  Pinned Mobile Cockpit Mirror
                </h3>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  Emitted by the exact same <code className="font-mono">reduceRegisterToScene()</code> reducer. Phone and desktop never diverge.
                </p>
              </div>

              <pre
                data-testid="telegram-3327-pin"
                className="flex-1 p-4 rounded-xl bg-slate-950 text-emerald-300 font-mono text-[11px] leading-relaxed overflow-x-auto border border-slate-800 whitespace-pre-wrap"
              >
                {telegram3327Pin}
              </pre>

              <div className="text-[11px] text-slate-500 dark:text-slate-400 font-mono">
                Source: .ops/register.jsonl @ seq #{truthScene.cursorSeq}
              </div>
            </div>
          )}
        </section>
      )}

      {/* ==================================================================== */}
      {/* D.1 FALSIFIER RECONCILIATION GATE (R1 · R2 · R3) & EVIDENCE SCRIPT   */}
      {/* ==================================================================== */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Left: R1-R3 Continuous Falsifier Gate */}
        <div className="lg:col-span-5 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                03. D.1 Falsifier Reconciliation (R1–R3)
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                The visual is a claim; <code className="font-mono">.ops/register.jsonl</code> is the truth. Reconcile re-reads disk SHA-256 digests and refuses pixel drift.
              </p>
            </div>
            {reconciliation?.passed ? (
              <ShieldCheck className="w-5 h-5 text-emerald-500 shrink-0" aria-hidden="true" />
            ) : (
              <ShieldAlert className="w-5 h-5 text-rose-500 shrink-0" aria-hidden="true" />
            )}
          </div>

          {reconciliation && (
            <div className="space-y-2.5 text-xs font-mono tabular-nums">
              <div className="p-3 rounded-lg bg-slate-50 dark:bg-[#050811] border border-slate-200 dark:border-slate-800 flex items-center justify-between">
                <span>R1 · Evidence SHA-256</span>
                <span
                  className={
                    reconciliation.r1HashAgreement.passed
                      ? 'text-emerald-600 dark:text-emerald-400 font-semibold'
                      : 'text-rose-600 dark:text-rose-400 font-semibold'
                  }
                >
                  {reconciliation.r1HashAgreement.passed
                    ? `PASS (${reconciliation.r1HashAgreement.checkedFiles}/${reconciliation.r1HashAgreement.checkedFiles} files)`
                    : `FAIL (${reconciliation.r1HashAgreement.mismatches} hash mismatch)`}
                </span>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 dark:bg-[#050811] border border-slate-200 dark:border-slate-800 flex items-center justify-between">
                <span>R2 · Verdict Agreement</span>
                <span
                  className={
                    reconciliation.r2VerdictAgreement.passed
                      ? 'text-emerald-600 dark:text-emerald-400 font-semibold'
                      : 'text-rose-600 dark:text-rose-400 font-semibold'
                  }
                >
                  {reconciliation.r2VerdictAgreement.passed
                    ? `PASS (${reconciliation.r2VerdictAgreement.checkedActors} actors)`
                    : `FAIL (${reconciliation.r2VerdictAgreement.mismatches} verdict lie)`}
                </span>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 dark:bg-[#050811] border border-slate-200 dark:border-slate-800 flex items-center justify-between">
                <span>R3 · In-Flight Count</span>
                <span
                  className={
                    reconciliation.r3CountAgreement.passed
                      ? 'text-emerald-600 dark:text-emerald-400 font-semibold'
                      : 'text-rose-600 dark:text-rose-400 font-semibold'
                  }
                >
                  {reconciliation.r3CountAgreement.passed
                    ? `PASS (${reconciliation.r3CountAgreement.registerInFlight} active)`
                    : `FAIL (UI ${reconciliation.r3CountAgreement.renderedInFlight} vs Disk ${reconciliation.r3CountAgreement.registerInFlight})`}
                </span>
              </div>
            </div>
          )}

          {reconciliation && reconciliation.discrepancies.length > 0 && (
            <div
              role="alert"
              className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-300 dark:border-rose-800 space-y-2"
            >
              <div className="text-xs font-semibold text-rose-800 dark:text-rose-200">
                Falsifier Refusal Log ({reconciliation.discrepancies.length} Discrepancies Caught):
              </div>
              <ul className="space-y-1.5 text-[11px] font-mono text-rose-700 dark:text-rose-300">
                {reconciliation.discrepancies.map((d, idx) => (
                  <li key={`${d.rule}-${idx}`}>
                    [{d.rule}] {d.subject}: expected {d.expectedTruth}, got {d.renderedClaim}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-200 dark:border-slate-800">
            <button
              type="button"
              disabled={isReconciling}
              onClick={() => runReconciliation()}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <RefreshCw
                className={`w-3.5 h-3.5 ${isReconciling ? 'animate-spin' : ''}`}
                aria-hidden="true"
              />
              Reconcile R1–R3
            </button>

            {!lieOverride ? (
              <button
                type="button"
                disabled={isReconciling}
                onClick={handleInjectRendererLie}
                className="px-3 py-2 text-xs font-medium text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-950/40 hover:bg-rose-100 dark:hover:bg-rose-900/50 border border-rose-200 dark:border-rose-800/70 rounded-lg transition-colors whitespace-nowrap shrink-0"
              >
                Test Falsifier (Inject Renderer Lie)
              </button>
            ) : (
              <button
                type="button"
                disabled={isReconciling}
                onClick={handleRestoreTruth}
                className="px-3.5 py-2 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition-colors whitespace-nowrap shrink-0"
              >
                Restore Register Truth
              </button>
            )}
          </div>
        </div>

        {/* Right: Selected Actor Complete Ordered Evidence Script */}
        <div className="lg:col-span-7 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4">
          {selectedActor ? (
            <>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-slate-500 dark:text-slate-400">
                    <span>{selectedActor.insId}</span>
                    <span aria-hidden="true">·</span>
                    <span>{selectedActor.repo}</span>
                    <span aria-hidden="true">·</span>
                    <span>Grants: {selectedActor.capabilityGrants.join(', ')}</span>
                  </div>
                  <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                    04. Evidence Chain Transcript — {selectedActor.title}
                  </h2>
                </div>

                <button
                  type="button"
                  onClick={() =>
                    onPromotePacketToLegion(
                      selectedActor.insId,
                      selectedActor.title,
                      `Execute cloud Legion ${selectedActor.formation} harness for ${selectedActor.insId}: ${selectedActor.title}`,
                      selectedActor.repo
                    )
                  }
                  className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
                >
                  <Terminal className="w-3.5 h-3.5 text-amber-500" aria-hidden="true" />
                  Dispatch in Cloud Legion
                </button>
              </div>

              <div className="space-y-2.5 max-h-[320px] overflow-y-auto pr-1">
                {selectedActor.scriptLines.map((line) => (
                  <div
                    key={line.seq}
                    className="p-3 rounded-lg bg-slate-50 dark:bg-[#050811] border border-slate-200 dark:border-slate-800 space-y-1.5 font-mono text-xs"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-500 dark:text-slate-400 tabular-nums">
                      <span>
                        seq #{line.seq} · {line.timeShort} UTC · {line.stage}
                      </span>
                      <span>sha256:{line.evidenceSha256.slice(0, 14)}…</span>
                    </div>
                    <div
                      className={
                        line.verdict === 'fail'
                          ? 'text-rose-700 dark:text-rose-300 font-medium'
                          : line.revoked === 1
                            ? 'text-slate-500 line-through'
                            : 'text-slate-900 dark:text-slate-100'
                      }
                    >
                      {line.formattedLine}
                    </div>
                    <div className="text-[11px] text-slate-600 dark:text-slate-400">
                      stdoutTail: {line.stdoutTail}
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="text-xs text-slate-500">
              No packet selected. Mint or select a packet above to inspect its evidence script.
            </div>
          )}
        </div>
      </section>
    </div>
  );
};
