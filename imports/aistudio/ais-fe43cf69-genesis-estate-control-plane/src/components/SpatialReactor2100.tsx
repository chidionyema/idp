import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import {
  Mic,
  Square,
  Volume2,
  VolumeX,
  ChevronDown,
  ChevronUp,
  Crosshair,
  Radio,
  ArrowUpRight,
  Play,
  RefreshCw,
} from 'lucide-react';
import {
  gravityOf,
  computeMotionHonesty,
  fireJetParticles3D,
  stepJetParticles3D,
  type ReactorNodeDatum,
  type ReactorActivity,
  type JetParticle3D,
  type Voice2100SpeculateResult,
  type Voice2100CandidateAction,
} from '../engine/optimusAndReactor';
import type { FormationId } from '../engine/estateRules';
import {
  createBrowserSpeechRecognizer,
  playSovereignChime,
  type BrowserSpeechRecognizerHandle,
} from '../utils/sovereignAudio';

function createAzimuthCompassTexture(maxAnisotropy: number): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = 1024;
  canvas.height = 1024;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    const cx = 512;
    const cy = 512;
    ctx.clearRect(0, 0, 1024, 1024);

    // Concentric calibrated orbital rings
    const radii = [148, 256, 368, 468, 492];
    radii.forEach((r, idx) => {
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.strokeStyle =
        idx === 3 ? 'rgba(245, 158, 11, 0.42)' : 'rgba(56, 189, 248, 0.22)';
      ctx.lineWidth = idx === 3 ? 2.5 : 1.5;
      ctx.stroke();
    });

    // 72 degree ticks (5° increments, major every 30°)
    for (let deg = 0; deg < 360; deg += 5) {
      const rad = (deg * Math.PI) / 180;
      const isMajor = deg % 30 === 0;
      const rInner = isMajor ? 444 : 458;
      const rOuter = 468;
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(rad) * rInner, cy + Math.sin(rad) * rInner);
      ctx.lineTo(cx + Math.cos(rad) * rOuter, cy + Math.sin(rad) * rOuter);
      ctx.strokeStyle = isMajor
        ? 'rgba(251, 191, 36, 0.65)'
        : 'rgba(148, 163, 184, 0.28)';
      ctx.lineWidth = isMajor ? 2.4 : 1.1;
      ctx.stroke();

      if (deg % 45 === 0) {
        ctx.save();
        ctx.translate(cx + Math.cos(rad) * 420, cy + Math.sin(rad) * 420);
        ctx.rotate(rad + Math.PI / 2);
        ctx.fillStyle = 'rgba(226, 232, 240, 0.62)';
        ctx.font = '600 18px "JetBrains Mono", monospace';
        ctx.textAlign = 'center';
        ctx.fillText(`${String(deg).padStart(3, '0')}°`, 0, 0);
        ctx.restore();
      }
    }

    // Subtle radial crosshairs
    for (let k = 0; k < 4; k++) {
      const a = (k * Math.PI) / 4;
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(a) * 150, cy + Math.sin(a) * 150);
      ctx.lineTo(cx + Math.cos(a) * 440, cy + Math.sin(a) * 440);
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.12)';
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  }

  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = Math.max(1, maxAnisotropy);
  tex.needsUpdate = true;
  return tex;
}

interface SpatialReactor2100Props {
  nodes: ReactorNodeDatum[];
  optimusEventCount: number;
  greenlaneReadyCount: number;
  idpHeadSha: string;
  onSwitchToMatrix: () => void;
  onNavigateTab: (tab: 'beast' | 'academy' | 'standards' | 'catalog' | 'omega' | 'io' | 'projector' | 'synapse' | 'reactor' | 'optimus' | 'fleet' | 'legion' | 'flow' | 'greenlane' | 'chronos') => void;
  onExecuteFormation: (payload: {
    formationId: FormationId;
    repo: string;
    instructionId?: string;
    title?: string;
    objective: string;
    helmShots: number;
  }) => Promise<unknown>;
  onIngestOptimus: (targetSurface?: string) => Promise<void>;
  onRunWatchdog: () => Promise<{ recoveredIds: string[] }>;
  onReprobe: () => Promise<void>;
  onOpenVoiceDrawer: () => void;
  onPlayBriefing: () => Promise<void>;
  onStopBriefing: () => void;
  isPlayingBriefing: boolean;
  briefingScript: string | null;
  onSyncArgon?: () => Promise<{ message: string }>;
}

const ACTIVITY_HEX: Record<ReactorActivity, number> = {
  thinking: 0x06b6d4, // Calibrated Telemetry Cyan
  waiting: 0xf59e0b,  // Sovereign Amber
  stuck: 0xf43f5e,    // Hazard Rose
  finished: 0x10b981, // Settled Emerald
};

const ACTIVITY_LABEL: Record<ReactorActivity, string> = {
  thinking: 'Thinking (Respiration)',
  waiting: 'Waiting (Orbital Drift)',
  stuck: 'Blocked / Stuck (Tremor)',
  finished: 'Settled (Verified)',
};

const MAX_JET_POINTS = 320;

export const SpatialReactor2100: React.FC<SpatialReactor2100Props> = ({
  nodes,
  optimusEventCount,
  greenlaneReadyCount,
  idpHeadSha,
  onSwitchToMatrix,
  onNavigateTab,
  onExecuteFormation,
  onIngestOptimus,
  onRunWatchdog,
  onReprobe,
  onOpenVoiceDrawer,
  onPlayBriefing,
  onStopBriefing,
  isPlayingBriefing,
  briefingScript,
  onSyncArgon,
}) => {
  const canvasMountRef = useRef<HTMLDivElement | null>(null);
  const nodesRef = useRef<ReactorNodeDatum[]>(nodes);
  nodesRef.current = nodes;

  const [selectedNodeId, setSelectedNodeId] = useState<string>('CORE-ONEBRAIN');
  const [blastActive, setBlastActive] = useState<boolean>(false);
  const [dockCollapsed, setDockCollapsed] = useState<boolean>(false);
  const [actionBusy, setActionBusy] = useState<boolean>(false);
  const [statusBanner, setStatusBanner] = useState<string | null>(null);
  const [webglLost, setWebglLost] = useState<boolean>(false);
  const [chimesEnabled, setChimesEnabled] = useState<boolean>(true);
  const [isInlineListening, setIsInlineListening] = useState<boolean>(false);

  // Voice 2100 Speculative Intent State
  const [utterance, setUtterance] = useState<string>('');
  const [speculation, setSpeculation] = useState<Voice2100SpeculateResult | null>(null);
  const [speculateError, setSpeculateError] = useState<string | null>(null);

  const inlineRecognizerRef = useRef<BrowserSpeechRecognizerHandle | null>(null);
  const orbitDeltaRef = useRef<number>(0);
  const chimesRef = useRef<boolean>(chimesEnabled);
  chimesRef.current = chimesEnabled;

  const selectedIdRef = useRef<string>(selectedNodeId);
  selectedIdRef.current = selectedNodeId;

  const blastRef = useRef<boolean>(blastActive);
  blastRef.current = blastActive;

  const jetTriggerRef = useRef<{ origin: [number, number, number]; ownerId: string; activity: ReactorActivity } | null>(
    null
  );

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) ?? nodes[0] ?? null;

  const triggerNodeJet = useCallback((node: ReactorNodeDatum | undefined) => {
    if (!node) return;
    jetTriggerRef.current = {
      origin: node.position,
      ownerId: node.id,
      activity: node.activity,
    };
  }, []);

  // Speculative Intent Compiler (`POST /api/voice/speculate`) on utterance change
  useEffect(() => {
    const trimmed = utterance.trim();
    if (trimmed.length < 2) {
      setSpeculation(null);
      setSpeculateError(null);
      return;
    }

    const ctrl = new AbortController();
    const timer = window.setTimeout(async () => {
      try {
        const res = await fetch('/api/voice/speculate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ transcript: trimmed, sessionId: 'founder-reactor-2100' }),
          signal: ctrl.signal,
        });
        const data = await res.json();
        if (!res.ok) {
          setSpeculation(null);
          setSpeculateError(data.message || 'Schema v2 armor refused input.');
          playSovereignChime('refuse', chimesRef.current);
          return;
        }
        setSpeculateError(null);
        setSpeculation(data as Voice2100SpeculateResult);
        if (data.ok && !data.clarificationNeeded && data.targetNodeId) {
          setSelectedNodeId(data.targetNodeId);
          playSovereignChime('lock', chimesRef.current);
        } else if (data.ok && data.clarificationNeeded) {
          playSovereignChime('clarify', chimesRef.current);
        }
      } catch {
        // Ignore aborted partial requests
      }
    }, 105);

    return () => {
      ctrl.abort();
      window.clearTimeout(timer);
    };
  }, [utterance]);

  const toggleInlineDictation = () => {
    if (isInlineListening) {
      inlineRecognizerRef.current?.stop();
      inlineRecognizerRef.current = null;
      setIsInlineListening(false);
      return;
    }

    const rec = createBrowserSpeechRecognizer({
      onTranscript: (text) => {
        setUtterance(text);
      },
      onError: () => {
        setIsInlineListening(false);
        onOpenVoiceDrawer();
      },
      onEnd: () => {
        setIsInlineListening(false);
      },
    });

    if (!rec.supported) {
      onOpenVoiceDrawer();
      return;
    }

    inlineRecognizerRef.current = rec;
    setIsInlineListening(true);
    setStatusBanner('Listening for Captain voice directive — speak naturally…');
    rec.start();
  };

  const executeCandidateAction = async (candidate: {
    targetNodeId: string;
    actionKind: Voice2100CandidateAction['actionKind'];
    targetTab?: 'beast' | 'academy' | 'standards' | 'catalog' | 'omega' | 'io' | 'projector' | 'synapse' | 'reactor' | 'optimus' | 'fleet' | 'legion' | 'flow' | 'greenlane' | 'chronos';
    formation?: FormationId;
    repo?: string;
    summaryText: string;
  }) => {
    setSelectedNodeId(candidate.targetNodeId);
    const targetNode = nodesRef.current.find((n) => n.id === candidate.targetNodeId);
    triggerNodeJet(targetNode);
    setActionBusy(true);
    setStatusBanner(null);
    playSovereignChime(candidate.actionKind === 'TRIGGER_BLAST' ? 'blast' : 'execute', chimesRef.current);

    try {
      if (candidate.actionKind === 'INGEST_OPTIMUS') {
        await onIngestOptimus('reactor-2100:optimus-probe');
        setStatusBanner('Optimus signed HMAC observation ingested & broadcast over SSE.');
      } else if (candidate.actionKind === 'SWEEP_WATCHDOG') {
        const out = await onRunWatchdog();
        setStatusBanner(
          out.recoveredIds.length > 0
            ? `FLOW 600s Watchdog fenced & recovered: ${out.recoveredIds.join(', ')}`
            : 'FLOW 600s Watchdog sweep complete — all active leases healthy (<600s).'
        );
      } else if (candidate.actionKind === 'REPROBE_ESTATE') {
        await onReprobe();
        setStatusBanner('Live GitHub E1 commits and production edge surfaces re-probed.');
      } else if (candidate.actionKind === 'PLAY_BRIEFING') {
        await onPlayBriefing();
        setStatusBanner('Captain executive audio sitrep synthesized and playing.');
      } else if (candidate.actionKind === 'TRIGGER_BLAST') {
        setBlastActive(true);
        setStatusBanner(`Sonar Blast Cascade active from ${candidate.targetNodeId}.`);
      } else if (candidate.actionKind === 'SYNC_ARGON') {
        if (onSyncArgon) {
          const syncRes = await onSyncArgon();
          setStatusBanner(syncRes.message);
        } else {
          onNavigateTab('flow');
          setStatusBanner('Opened Argon Continuity Sync console.');
        }
      } else if (candidate.actionKind === 'NAVIGATE_TAB' && candidate.targetTab) {
        onNavigateTab(candidate.targetTab);
        setStatusBanner(`Morphed viewport to ${candidate.targetTab.toUpperCase()}.`);
      } else if (candidate.actionKind === 'EXECUTE_LEGION') {
        const formation = candidate.formation ?? 'sniper';
        const repo = candidate.repo ?? 'chidionyema/idp';
        await onExecuteFormation({
          formationId: formation,
          repo,
          instructionId: targetNode?.instructionId ?? `INS-R${Math.floor(1000 + Math.random() * 8999)}`,
          title: candidate.summaryText.slice(0, 68),
          objective: candidate.summaryText,
          helmShots: 2,
        });
        setStatusBanner(`Dispatched Legion ${formation.toUpperCase()} on ${repo} with Geburah Claim-Gate.`);
      } else {
        setStatusBanner(`CineCam locked onto ${candidate.targetNodeId}.`);
      }
      setUtterance('');
      setSpeculation(null);
    } catch (err) {
      setStatusBanner(err instanceof Error ? err.message : 'Execution failed');
    } finally {
      setActionBusy(false);
    }
  };

  const handleSpeculativeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!speculation || !speculation.ok) return;
    if (speculation.clarificationNeeded) {
      setStatusBanner('Confidence < 0.90: select one of the clarified sovereign intents below.');
      return;
    }
    await executeCandidateAction({
      targetNodeId: speculation.targetNodeId,
      actionKind: speculation.actionKind,
      targetTab: speculation.targetTab,
      formation: speculation.formation,
      repo: speculation.repo,
      summaryText: utterance.trim() || speculation.summary,
    });
  };

  // Keyboard Flight Controls (1 Wide Orbit, 2 Optimus, 3 #2468, Space Blast, H Zen HUD, Arrows Orbit)
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.tagName === 'SELECT' ||
          target.isContentEditable)
      ) {
        return;
      }

      if (e.key === 'ArrowLeft') {
        orbitDeltaRef.current -= 0.14;
      } else if (e.key === 'ArrowRight') {
        orbitDeltaRef.current += 0.14;
      } else if (e.key === '1') {
        setSelectedNodeId('CORE-ONEBRAIN');
        setBlastActive(false);
        playSovereignChime('lock', chimesRef.current);
      } else if (e.key === '2') {
        setSelectedNodeId('CORE-OPTIMUS');
        playSovereignChime('lock', chimesRef.current);
      } else if (e.key === '3') {
        setSelectedNodeId('INC-2468');
        playSovereignChime('lock', chimesRef.current);
      } else if (e.key === 'h' || e.key === 'H') {
        setDockCollapsed((c) => !c);
      } else if (e.key === ' ') {
        e.preventDefault();
        setBlastActive((b) => !b);
        playSovereignChime('blast', chimesRef.current);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  // Mount Three.js WebGL Scene ONCE (`useEffect(..., [])`) per Three.js skill §4.1
  useEffect(() => {
    const container = canvasMountRef.current;
    if (!container) return;

    // 1. Software-WebGL Guard (`threejs` skill §2.1)
    const isSoftwareGl = (() => {
      try {
        const probeCanvas = document.createElement('canvas');
        const gl = probeCanvas.getContext('webgl2') || probeCanvas.getContext('webgl');
        if (!gl) return true;
        const ext = gl.getExtension('WEBGL_debug_renderer_info');
        const param = ext ? ext.UNMASKED_RENDERER_WEBGL : gl.RENDERER;
        const gpu = String(gl.getParameter(param));
        gl.getExtension('WEBGL_lose_context')?.loseContext();
        return /SwiftShader|llvmpipe|softpipe|Software|Basic Render/i.test(gpu);
      } catch {
        return true;
      }
    })();

    const width = Math.max(320, container.clientWidth || window.innerWidth);
    const height = Math.max(420, container.clientHeight || 680);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color('#04070f');
    scene.fog = new THREE.FogExp2('#04070f', 0.0082);

    const camera = new THREE.PerspectiveCamera(48, width / height, 0.1, 400);
    camera.position.set(Math.sin(0.35) * 48, 15, Math.cos(0.35) * 48);

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: !isSoftwareGl,
        preserveDrawingBuffer: true,
        powerPreference: 'high-performance',
      });
    } catch {
      return;
    }

    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.12;
    renderer.setPixelRatio(isSoftwareGl ? 1 : Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height);
    renderer.shadowMap.enabled = !isSoftwareGl;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);

    // 2. Mandatory Studio Environment Reflection (`RoomEnvironment`)
    const pmremGenerator = new THREE.PMREMGenerator(renderer);
    const envTexture = pmremGenerator.fromScene(new RoomEnvironment(), 0.04).texture;
    scene.environment = envTexture;
    pmremGenerator.dispose();

    // 3. Balanced Warm/Cool Studio Rig
    const hemiLight = new THREE.HemisphereLight(0x38bdf8, 0x080d1a, 0.85);
    scene.add(hemiLight);

    const keyLight = new THREE.DirectionalLight(0xfde68a, 1.65);
    keyLight.position.set(28, 42, 32);
    scene.add(keyLight);

    const rimLight = new THREE.DirectionalLight(0x06b6d4, 1.1);
    rimLight.position.set(-34, -18, -28);
    scene.add(rimLight);

    const worldGroup = new THREE.Group();
    scene.add(worldGroup);

    // 4. Central Sovereign Astrolabe Core (5-Part Composite Procedural Group)
    const centralAstrolabe = new THREE.Group();
    const coreCrystalGeo = new THREE.IcosahedronGeometry(2.35, 1);
    const coreCrystalMat = new THREE.MeshStandardMaterial({
      color: 0xf59e0b,
      emissive: 0xb45309,
      emissiveIntensity: 0.45,
      metalness: 0.92,
      roughness: 0.18,
    });
    const coreCrystal = new THREE.Mesh(coreCrystalGeo, coreCrystalMat);

    const innerGimbalGeo = new THREE.TorusGeometry(4.1, 0.075, 14, 64);
    const innerGimbalMat = new THREE.MeshStandardMaterial({
      color: 0x06b6d4,
      emissive: 0x0891b2,
      emissiveIntensity: 0.35,
      metalness: 0.82,
      roughness: 0.44,
    });
    const innerGimbal = new THREE.Mesh(innerGimbalGeo, innerGimbalMat);

    const outerGimbalGeo = new THREE.TorusGeometry(5.9, 0.055, 14, 80);
    const outerGimbalMat = new THREE.MeshStandardMaterial({
      color: 0x94a3b8,
      metalness: 0.88,
      roughness: 0.22,
    });
    const outerGimbal = new THREE.Mesh(outerGimbalGeo, outerGimbalMat);
    outerGimbal.rotation.x = Math.PI / 2.6;

    const spireGeo = new THREE.ConeGeometry(0.32, 2.2, 6);
    const spireMat = new THREE.MeshStandardMaterial({
      color: 0xe2e8f0,
      metalness: 0.7,
      roughness: 0.5,
    });
    const topSpire = new THREE.Mesh(spireGeo, spireMat);
    topSpire.position.y = 3.4;
    const bottomSpire = new THREE.Mesh(spireGeo, spireMat);
    bottomSpire.position.y = -3.4;
    bottomSpire.rotation.x = Math.PI;

    centralAstrolabe.add(coreCrystal, innerGimbal, outerGimbal, topSpire, bottomSpire);
    worldGroup.add(centralAstrolabe);

    // Subtle Equatorial Reference Plane + Procedural 1024x1024 Holographic Azimuth Compass Dial
    const horizonRingGeo = new THREE.RingGeometry(29.6, 30.0, 96);
    const horizonRingMat = new THREE.MeshBasicMaterial({
      color: 0x1e293b,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.45,
      polygonOffset: true,
      polygonOffsetFactor: -1,
      polygonOffsetUnits: -1,
    });
    const horizonRing = new THREE.Mesh(horizonRingGeo, horizonRingMat);
    horizonRing.rotation.x = Math.PI / 2;
    horizonRing.position.y = -0.04;
    worldGroup.add(horizonRing);

    const compassTex = createAzimuthCompassTexture(renderer.capabilities.getMaxAnisotropy());
    const compassDialGeo = new THREE.PlaneGeometry(58, 58);
    const compassDialMat = new THREE.MeshBasicMaterial({
      map: compassTex,
      transparent: true,
      opacity: 0.48,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      side: THREE.DoubleSide,
      polygonOffset: true,
      polygonOffsetFactor: -2,
      polygonOffsetUnits: -2,
    });
    const compassDial = new THREE.Mesh(compassDialGeo, compassDialMat);
    compassDial.rotation.x = -Math.PI / 2;
    compassDial.position.y = -3.8;
    worldGroup.add(compassDial);

    // 16 Instanced Orbital Calibration Pylons around the equatorial ring (1 draw call)
    const pylonCount = 16;
    const pylonGeo = new THREE.CylinderGeometry(0.06, 0.14, 1.9, 6);
    const pylonMat = new THREE.MeshStandardMaterial({
      color: 0x38bdf8,
      emissive: 0x0284c7,
      emissiveIntensity: 0.35,
      metalness: 0.85,
      roughness: 0.25,
    });
    const pylonInstanced = new THREE.InstancedMesh(pylonGeo, pylonMat, pylonCount);
    const _pylonDummy = new THREE.Object3D();
    for (let i = 0; i < pylonCount; i++) {
      const ang = (i / pylonCount) * Math.PI * 2;
      _pylonDummy.position.set(Math.cos(ang) * 29.8, -2.9, Math.sin(ang) * 29.8);
      _pylonDummy.rotation.set(0, -ang, 0);
      _pylonDummy.updateMatrix();
      pylonInstanced.setMatrixAt(i, _pylonDummy.matrix);
    }
    pylonInstanced.instanceMatrix.needsUpdate = true;
    pylonInstanced.computeBoundingSphere();
    worldGroup.add(pylonInstanced);

    // Dynamic 3D Sovereign Target Lock Reticle (counter-rotating telemetry brackets)
    const reticleGroup = new THREE.Group();
    const reticleOuterGeo = new THREE.RingGeometry(2.85, 3.02, 6);
    const reticleOuterMat = new THREE.MeshBasicMaterial({
      color: 0xfbbf24,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.78,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const reticleOuter = new THREE.Mesh(reticleOuterGeo, reticleOuterMat);
    const reticleInnerGeo = new THREE.RingGeometry(2.35, 2.46, 32);
    const reticleInnerMat = new THREE.MeshBasicMaterial({
      color: 0x22d3ee,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.58,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const reticleInner = new THREE.Mesh(reticleInnerGeo, reticleInnerMat);
    reticleGroup.add(reticleOuter, reticleInner);
    worldGroup.add(reticleGroup);

    // 5. Build 24 Composite 4-Part Procedural Estate Nodes
    const coreGeos = {
      CORE: new THREE.IcosahedronGeometry(1.35, 1),
      LEGION: new THREE.OctahedronGeometry(1.25, 0),
      REPO: new THREE.DodecahedronGeometry(1.2, 0),
      INCIDENT: new THREE.TetrahedronGeometry(1.45, 0),
      FLOW: new THREE.OctahedronGeometry(1.05, 1),
      SURFACE: new THREE.IcosahedronGeometry(1.05, 0),
    };
    const nodeRingGeo = new THREE.TorusGeometry(2.15, 0.055, 12, 48);
    const nodeCapGeo = new THREE.ConeGeometry(0.24, 0.85, 5);
    const nodeHaloGeo = new THREE.SphereGeometry(2.45, 18, 18);
    const hitProxyGeo = new THREE.SphereGeometry(3.1, 10, 10);
    const hitProxyMat = new THREE.MeshBasicMaterial({ visible: false });

    interface NodeSceneEntry {
      id: string;
      seed: number;
      group: THREE.Group;
      hullMat: THREE.MeshStandardMaterial;
      ringMesh: THREE.Mesh;
      ringMat: THREE.MeshStandardMaterial;
      haloMat: THREE.MeshBasicMaterial;
      basePos: THREE.Vector3;
    }

    const nodeEntries = new Map<string, NodeSceneEntry>();
    const clickableProxies: THREE.Mesh[] = [];

    const initialNodes = nodesRef.current;
    initialNodes.forEach((n, idx) => {
      const group = new THREE.Group();
      const basePos = new THREE.Vector3(n.position[0], n.position[1], n.position[2]);
      group.position.copy(basePos);

      const hex = ACTIVITY_HEX[n.activity];

      // Part 1: Primary PBR Metallic Hull (roughness 0.22)
      const hullMat = new THREE.MeshStandardMaterial({
        color: hex,
        emissive: hex,
        emissiveIntensity: 0.35,
        metalness: 0.82,
        roughness: 0.22,
      });
      const hullMesh = new THREE.Mesh(coreGeos[n.category] || coreGeos.LEGION, hullMat);

      // Part 2: Secondary Gyroscopic Containment Ring (roughness 0.54 -> delta >= 0.25)
      const ringMat = new THREE.MeshStandardMaterial({
        color: hex,
        emissive: hex,
        emissiveIntensity: 0.2,
        metalness: 0.65,
        roughness: 0.54,
      });
      const ringMesh = new THREE.Mesh(nodeRingGeo, ringMat);
      ringMesh.rotation.x = (idx * 0.7) % Math.PI;
      ringMesh.rotation.y = (idx * 1.1) % Math.PI;

      // Part 3: Polar Telemetry Spire Accent (roughness 0.48)
      const capMat = new THREE.MeshStandardMaterial({
        color: 0xf8fafc,
        metalness: 0.75,
        roughness: 0.48,
      });
      const capMesh = new THREE.Mesh(nodeCapGeo, capMat);
      capMesh.position.y = 1.65;

      // Part 4: Volumetric Additive Energy Halo
      const haloMat = new THREE.MeshBasicMaterial({
        color: hex,
        transparent: true,
        opacity: 0.13,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });
      const haloMesh = new THREE.Mesh(nodeHaloGeo, haloMat);

      // Simplified invisible proxy sphere on layer 1 for fast raycasting
      const proxy = new THREE.Mesh(hitProxyGeo, hitProxyMat);
      proxy.layers.set(1);
      proxy.userData.nodeId = n.id;
      clickableProxies.push(proxy);

      group.add(hullMesh, ringMesh, capMesh, haloMesh, proxy);
      worldGroup.add(group);

      nodeEntries.set(n.id, {
        id: n.id,
        seed: idx * 1.37 + 0.5,
        group,
        hullMat,
        ringMesh,
        ringMat,
        haloMat,
        basePos,
      });
    });

    // 6. Causal Topology Edges + Photon Packets
    interface EdgeEntry {
      fromId: string;
      toId: string;
      line: THREE.Line;
      lineMat: THREE.LineBasicMaterial;
      photon: THREE.Mesh;
      photonMat: THREE.MeshBasicMaterial;
      progress: number;
      speed: number;
    }

    const edgeEntries: EdgeEntry[] = [];
    const photonGeo = new THREE.SphereGeometry(0.32, 8, 8);
    const seenPairs = new Set<string>();

    initialNodes.forEach((n, idx) => {
      for (const targetId of n.connections) {
        const pairKey = [n.id, targetId].sort().join('::');
        if (seenPairs.has(pairKey)) continue;
        const fromEntry = nodeEntries.get(n.id);
        const toEntry = nodeEntries.get(targetId);
        if (!fromEntry || !toEntry) continue;
        seenPairs.add(pairKey);

        const lineGeo = new THREE.BufferGeometry().setFromPoints([
          fromEntry.basePos.clone(),
          toEntry.basePos.clone(),
        ]);
        const lineMat = new THREE.LineBasicMaterial({
          color: 0x334155,
          transparent: true,
          opacity: 0.28,
          blending: THREE.AdditiveBlending,
        });
        const line = new THREE.Line(lineGeo, lineMat);
        worldGroup.add(line);

        const photonMat = new THREE.MeshBasicMaterial({
          color: ACTIVITY_HEX[n.activity],
          transparent: true,
          opacity: 0.85,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
        });
        const photon = new THREE.Mesh(photonGeo, photonMat);
        worldGroup.add(photon);

        edgeEntries.push({
          fromId: n.id,
          toId: targetId,
          line,
          lineMat,
          photon,
          photonMat,
          progress: (idx * 0.19) % 1,
          speed: 0.18 + (idx % 5) * 0.05,
        });
      }
    });

    // 7. Sonar / Blast Cascade Shockwave Torus
    const sonarGeo = new THREE.TorusGeometry(1, 0.08, 12, 64);
    const sonarMat = new THREE.MeshBasicMaterial({
      color: 0xf43f5e,
      transparent: true,
      opacity: 0,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const sonarMesh = new THREE.Mesh(sonarGeo, sonarMat);
    sonarMesh.rotation.x = Math.PI / 2;
    worldGroup.add(sonarMesh);

    // 8. Pre-allocated 3D Jet Particle Cloud (`reactor.ts` jets — zero GC!)
    const activeJets: JetParticle3D[] = [];
    const jetPositions = new Float32Array(MAX_JET_POINTS * 3);
    const jetColors = new Float32Array(MAX_JET_POINTS * 3);
    const jetGeo = new THREE.BufferGeometry();
    jetGeo.setAttribute('position', new THREE.BufferAttribute(jetPositions, 3));
    jetGeo.setAttribute('color', new THREE.BufferAttribute(jetColors, 3));
    const jetMat = new THREE.PointsMaterial({
      size: 0.65,
      vertexColors: true,
      transparent: true,
      opacity: 0.9,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const jetPoints = new THREE.Points(jetGeo, jetMat);
    jetPoints.frustumCulled = false;
    worldGroup.add(jetPoints);

    // Ambient Deep-Space Starfield Instanced / Points
    const starCount = 420;
    const starPos = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount * 3; i++) {
      starPos[i] = (Math.random() - 0.5) * 220;
    }
    const starGeo = new THREE.BufferGeometry();
    starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
    const starMat = new THREE.PointsMaterial({
      color: 0x94a3b8,
      size: 0.28,
      transparent: true,
      opacity: 0.35,
    });
    const starPoints = new THREE.Points(starGeo, starMat);
    scene.add(starPoints);

    // 9. Raycasting & Drag Orbit Controls (restricted to layer 1, throttled)
    const raycaster = new THREE.Raycaster();
    raycaster.layers.set(1);
    const pointerNdc = new THREE.Vector2();
    let isDragging = false;
    let dragMoved = false;
    let prevX = 0;
    let orbitAzimuth = 0.35;

    const domEl = renderer.domElement;
    const onPointerDown = (e: PointerEvent) => {
      isDragging = true;
      dragMoved = false;
      prevX = e.clientX;
    };
    const onPointerMove = (e: PointerEvent) => {
      if (!isDragging) return;
      const dx = e.clientX - prevX;
      if (Math.abs(dx) > 3) dragMoved = true;
      orbitAzimuth -= dx * 0.0055;
      prevX = e.clientX;
    };
    const onPointerUp = (e: PointerEvent) => {
      if (!isDragging) return;
      isDragging = false;
      if (dragMoved) return;

      const rect = domEl.getBoundingClientRect();
      pointerNdc.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      pointerNdc.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointerNdc, camera);
      const hits = raycaster.intersectObjects(clickableProxies, false);
      if (hits.length > 0 && hits[0].object.userData.nodeId) {
        const hitId = String(hits[0].object.userData.nodeId);
        setSelectedNodeId(hitId);
        const found = nodesRef.current.find((item) => item.id === hitId);
        if (found) {
          fireJetParticles3D(activeJets, found.position, found.id, found.activity, 18, Math.floor( performance.now() ));
        }
      }
    };

    domEl.addEventListener('pointerdown', onPointerDown);
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);

    const onContextLost = (e: Event) => {
      e.preventDefault();
      setWebglLost(true);
    };
    const onContextRestored = () => {
      setWebglLost(false);
    };
    domEl.addEventListener('webglcontextlost', onContextLost);
    domEl.addEventListener('webglcontextrestored', onContextRestored);

    const onResize = () => {
      if (!container) return;
      const w = Math.max(320, container.clientWidth);
      const h = Math.max(420, container.clientHeight);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', onResize);

    if (!isSoftwareGl) {
      renderer.compile(scene, camera);
    }

    // Pre-allocated reusable math vectors (Zero GC in render loop!)
    const _camGoal = new THREE.Vector3();
    const _lookGoal = new THREE.Vector3();
    const _currentLook = new THREE.Vector3(0, 0, 0);
    const _tmpColor = new THREE.Color();
    let sonarPhase = 0;

    // 10. Frame-Rate Independent Loop + Software-WebGL `afterDraw` Pacing
    let frameOrTimerId = 0;
    let disposed = false;
    let lastNowMs = performance.now();

    function afterDraw(cb: () => void) {
      const gl = renderer.getContext() as WebGL2RenderingContext;
      if (gl && typeof gl.fenceSync === 'function') {
        const sync = gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE, 0);
        gl.flush();
        const poll = () => {
          if (disposed) return;
          const state = sync && gl.getSyncParameter(sync, gl.SYNC_STATUS);
          if (state === gl.UNSIGNALED) {
            frameOrTimerId = window.setTimeout(poll, 6);
          } else {
            if (sync) gl.deleteSync(sync);
            frameOrTimerId = window.setTimeout(cb, 80);
          }
        };
        frameOrTimerId = window.setTimeout(poll, 6);
      } else {
        frameOrTimerId = window.setTimeout(cb, 85);
      }
    }

    function tick() {
      if (disposed) return;
      const nowMs = performance.now();
      const dtMs = Math.min(100, Math.max(1, nowMs - lastNowMs));
      const dtSec = dtMs / 1000;
      const timeSec = nowMs / 1000;
      lastNowMs = nowMs;

      // Consume queued jet burst from React UI actions
      if (jetTriggerRef.current) {
        const req = jetTriggerRef.current;
        jetTriggerRef.current = null;
        fireJetParticles3D(activeJets, req.origin, req.ownerId, req.activity, 24, Math.floor(nowMs));
      }

      // Rotate central Sovereign Astrolabe & Holographic Azimuth Compass
      coreCrystal.rotation.y += dtSec * 0.45;
      coreCrystal.rotation.x += dtSec * 0.22;
      innerGimbal.rotation.z += dtSec * 0.55;
      innerGimbal.rotation.x = Math.sin(timeSec * 0.6) * 0.5;
      outerGimbal.rotation.z -= dtSec * 0.28;
      compassDial.rotation.z += dtSec * 0.035;

      const currentNodes = nodesRef.current;
      const activeSelId = selectedIdRef.current;
      const selectedDatum = currentNodes.find((n) => n.id === activeSelId) ?? null;
      const connectedToSelected = new Set<string>(selectedDatum?.connections ?? []);

      // Update 24 Estate Nodes with Gravity + Motion Honesty
      for (const datum of currentNodes) {
        const entry = nodeEntries.get(datum.id);
        if (!entry) continue;

        const motion = computeMotionHonesty(datum.activity, timeSec, entry.seed);
        const grav = gravityOf(datum.eventCount, datum.workload);
        const baseScale = 0.68 + grav * 0.28;
        const isSelected = datum.id === activeSelId;
        const isNeighbor = connectedToSelected.has(datum.id);

        entry.group.position.set(
          entry.basePos.x + motion.dx,
          entry.basePos.y + motion.dy,
          entry.basePos.z + motion.dz
        );

        const targetScale = baseScale * motion.scaleMultiplier * (isSelected ? 1.28 : 1.0);
        entry.group.scale.setScalar(targetScale);

        entry.ringMesh.rotation.z += dtSec * (datum.activity === 'thinking' ? 1.4 : 0.45);
        entry.ringMesh.rotation.x += dtSec * 0.35;

        const hex = ACTIVITY_HEX[datum.activity];
        entry.hullMat.color.setHex(hex);
        entry.hullMat.emissive.setHex(hex);
        entry.hullMat.emissiveIntensity = isSelected ? 0.85 : isNeighbor ? 0.5 : 0.28;
        entry.ringMat.color.setHex(hex);
        entry.haloMat.color.setHex(hex);
        entry.haloMat.opacity = isSelected ? 0.28 : blastRef.current && !isNeighbor ? 0.04 : 0.13;
      }

      // Update 3D Sovereign Target Lock Reticle (billboarded toward camera)
      if (selectedDatum && selectedDatum.id !== 'CORE-ONEBRAIN') {
        const selEntry = nodeEntries.get(selectedDatum.id);
        if (selEntry) {
          reticleGroup.visible = true;
          reticleGroup.position.x = THREE.MathUtils.damp(reticleGroup.position.x, selEntry.group.position.x, 8.5, dtSec);
          reticleGroup.position.y = THREE.MathUtils.damp(reticleGroup.position.y, selEntry.group.position.y, 8.5, dtSec);
          reticleGroup.position.z = THREE.MathUtils.damp(reticleGroup.position.z, selEntry.group.position.z, 8.5, dtSec);
          reticleGroup.lookAt(camera.position);
          reticleOuter.rotation.z += dtSec * 0.9;
          reticleInner.rotation.z -= dtSec * 1.4;
        }
      } else {
        reticleGroup.visible = false;
      }

      // Update Causal Edges & Flowing Data Photons
      for (const edge of edgeEntries) {
        const fromE = nodeEntries.get(edge.fromId);
        const toE = nodeEntries.get(edge.toId);
        if (!fromE || !toE) continue;

        const posAttr = edge.line.geometry.getAttribute('position') as THREE.BufferAttribute;
        posAttr.setXYZ(0, fromE.group.position.x, fromE.group.position.y, fromE.group.position.z);
        posAttr.setXYZ(1, toE.group.position.x, toE.group.position.y, toE.group.position.z);
        posAttr.needsUpdate = true;

        const touchesSelected = edge.fromId === activeSelId || edge.toId === activeSelId;
        if (blastRef.current && touchesSelected) {
          edge.lineMat.color.setHex(0xf43f5e);
          edge.lineMat.opacity = 0.82;
        } else if (touchesSelected) {
          edge.lineMat.color.setHex(0xf59e0b);
          edge.lineMat.opacity = 0.65;
        } else {
          edge.lineMat.color.setHex(0x334155);
          edge.lineMat.opacity = blastRef.current ? 0.08 : 0.24;
        }

        edge.progress = (edge.progress + dtSec * edge.speed) % 1;
        edge.photon.position.lerpVectors(fromE.group.position, toE.group.position, edge.progress);
      }

      // Update Sonar / Blast Cascade Shockwave
      if (blastRef.current && selectedDatum) {
        const selEntry = nodeEntries.get(selectedDatum.id);
        if (selEntry) {
          sonarPhase = (sonarPhase + dtSec * 0.65) % 1;
          sonarMesh.position.copy(selEntry.group.position);
          const radius = 2 + sonarPhase * 28;
          sonarMesh.scale.set(radius, radius, 1);
          sonarMat.opacity = (1 - sonarPhase) * 0.65;
        }
      } else {
        sonarMat.opacity = 0;
      }

      // Advance 3D Jet Particles (`0.94^(dt/16.7)`)
      stepJetParticles3D(activeJets, dtMs);
      const count = Math.min(MAX_JET_POINTS, activeJets.length);
      for (let i = 0; i < MAX_JET_POINTS; i++) {
        if (i < count) {
          const p = activeJets[i];
          jetPositions[i * 3] = p.x;
          jetPositions[i * 3 + 1] = p.y;
          jetPositions[i * 3 + 2] = p.z;
          _tmpColor.setHex(ACTIVITY_HEX[p.activity]).multiplyScalar(Math.max(0.15, p.life));
          jetColors[i * 3] = _tmpColor.r;
          jetColors[i * 3 + 1] = _tmpColor.g;
          jetColors[i * 3 + 2] = _tmpColor.b;
        } else {
          jetPositions[i * 3] = 0;
          jetPositions[i * 3 + 1] = -9999;
          jetPositions[i * 3 + 2] = 0;
        }
      }
      jetGeo.attributes.position.needsUpdate = true;
      jetGeo.attributes.color.needsUpdate = true;

      // CineCam Smooth Exponential Damping (`THREE.MathUtils.damp`) + Keyboard Orbit Delta
      if (orbitDeltaRef.current !== 0) {
        orbitAzimuth += orbitDeltaRef.current;
        orbitDeltaRef.current = 0;
      }
      orbitAzimuth += dtSec * 0.045;
      if (selectedDatum && selectedDatum.id !== 'CORE-ONEBRAIN') {
        const selEntry = nodeEntries.get(selectedDatum.id);
        if (selEntry) {
          _lookGoal.copy(selEntry.group.position);
          const dirX = selEntry.basePos.x || 1;
          const dirZ = selEntry.basePos.z || 1;
          const len = Math.hypot(dirX, dirZ) || 1;
          _camGoal.set(
            selEntry.basePos.x + (dirX / len) * 22,
            selEntry.basePos.y + 9,
            selEntry.basePos.z + (dirZ / len) * 22
          );
        }
      } else {
        _lookGoal.set(0, 0, 0);
        _camGoal.set(Math.sin(orbitAzimuth) * 48, 15, Math.cos(orbitAzimuth) * 48);
      }

      camera.position.x = THREE.MathUtils.damp(camera.position.x, _camGoal.x, 3.6, dtSec);
      camera.position.y = THREE.MathUtils.damp(camera.position.y, _camGoal.y, 3.6, dtSec);
      camera.position.z = THREE.MathUtils.damp(camera.position.z, _camGoal.z, 3.6, dtSec);

      _currentLook.x = THREE.MathUtils.damp(_currentLook.x, _lookGoal.x, 4.2, dtSec);
      _currentLook.y = THREE.MathUtils.damp(_currentLook.y, _lookGoal.y, 4.2, dtSec);
      _currentLook.z = THREE.MathUtils.damp(_currentLook.z, _lookGoal.z, 4.2, dtSec);
      camera.lookAt(_currentLook);

      renderer.render(scene, camera);

      if (isSoftwareGl) {
        afterDraw(tick);
      } else {
        frameOrTimerId = window.requestAnimationFrame(tick);
      }
    }

    tick();

    return () => {
      disposed = true;
      window.cancelAnimationFrame(frameOrTimerId);
      window.clearTimeout(frameOrTimerId);
      domEl.removeEventListener('pointerdown', onPointerDown);
      domEl.removeEventListener('webglcontextlost', onContextLost);
      domEl.removeEventListener('webglcontextrestored', onContextRestored);
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
      window.removeEventListener('resize', onResize);

      envTexture.dispose();
      compassTex.dispose();
      compassDialGeo.dispose();
      compassDialMat.dispose();
      pylonGeo.dispose();
      pylonMat.dispose();
      pylonInstanced.dispose();
      reticleOuterGeo.dispose();
      reticleOuterMat.dispose();
      reticleInnerGeo.dispose();
      reticleInnerMat.dispose();
      coreCrystalGeo.dispose();
      coreCrystalMat.dispose();
      innerGimbalGeo.dispose();
      innerGimbalMat.dispose();
      outerGimbalGeo.dispose();
      outerGimbalMat.dispose();
      spireGeo.dispose();
      spireMat.dispose();
      horizonRingGeo.dispose();
      horizonRingMat.dispose();
      Object.values(coreGeos).forEach((g) => g.dispose());
      nodeRingGeo.dispose();
      nodeCapGeo.dispose();
      nodeHaloGeo.dispose();
      hitProxyGeo.dispose();
      hitProxyMat.dispose();
      photonGeo.dispose();
      sonarGeo.dispose();
      sonarMat.dispose();
      jetGeo.dispose();
      jetMat.dispose();
      starGeo.dispose();
      starMat.dispose();
      renderer.dispose();
      if (domEl.parentNode === container) {
        container.removeChild(domEl);
      }
    };
  }, []);

  const stuckCount = nodes.filter((n) => n.activity === 'stuck').length;
  const thinkingCount = nodes.filter((n) => n.activity === 'thinking').length;

  return (
    <section
      aria-label="Fleet Reactor 2100 Spatial Operating Room"
      className="relative w-full min-h-[760px] sm:min-h-[680px] h-[calc(100vh-7.5rem)] rounded-2xl overflow-hidden border border-slate-800 bg-[#04070f] text-slate-100 select-none"
    >
      {/* Dedicated Isolated WebGL Canvas Container (Zero backdrop-filter over WebGL!) */}
      <div
        ref={canvasMountRef}
        data-testid="reactor-3d-canvas"
        className="absolute inset-0 w-full h-full cursor-crosshair"
      />

      {/* Top-Left Sovereign Genesis Mothership HUD (Unobstructed Center Viewport) */}
      <div className="relative z-10 pointer-events-none p-3.5 sm:p-6 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div className="pointer-events-auto max-w-lg bg-[#070B16]/92 border border-slate-800/90 rounded-xl p-3.5 sm:p-4 space-y-2">
          <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono text-amber-400">
            <span>ARGON · GENESIS 2100</span>
            <span aria-hidden="true">·</span>
            <span>IDP {idpHeadSha.slice(0, 10)}</span>
            <span aria-hidden="true">·</span>
            <span>{nodes.length} ORBITAL NODES</span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white leading-tight">
            See the whole.{' '}
            <span className="font-editorial italic font-medium text-amber-300">
              Move the real.
            </span>
          </h1>

          <p className="text-xs text-slate-300 leading-relaxed">
            Motion is physical truth: thinking breathes ({thinkingCount}), blocked jitters ({stuckCount}), Optimus signs ({optimusEventCount} events), Greenlane holds {greenlaneReadyCount} ready lanes.
          </p>

          {/* MORPH Mode & Quick Camera Presets */}
          <div className="pt-1 flex flex-wrap items-center gap-1.5">
            <button
              type="button"
              onClick={() => {
                setSelectedNodeId('CORE-ONEBRAIN');
                setBlastActive(false);
              }}
              className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition-colors whitespace-nowrap ${
                selectedNodeId === 'CORE-ONEBRAIN'
                  ? 'bg-amber-500 text-slate-950 font-semibold'
                  : 'bg-slate-900 text-slate-300 hover:text-white border border-slate-800'
              }`}
            >
              Wide Orbit
            </button>
            <button
              type="button"
              onClick={() => setSelectedNodeId('CORE-OPTIMUS')}
              className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition-colors whitespace-nowrap ${
                selectedNodeId === 'CORE-OPTIMUS'
                  ? 'bg-cyan-500 text-slate-950 font-semibold'
                  : 'bg-slate-900 text-slate-300 hover:text-white border border-slate-800'
              }`}
            >
              Focus Optimus
            </button>
            <button
              type="button"
              onClick={() => setSelectedNodeId('INC-2468')}
              className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition-colors whitespace-nowrap ${
                selectedNodeId === 'INC-2468'
                  ? 'bg-rose-500 text-white font-semibold'
                  : 'bg-slate-900 text-rose-300 hover:text-white border border-slate-800'
              }`}
            >
              Drill #2468 Vault
            </button>
            <button
              type="button"
              onClick={onSwitchToMatrix}
              className="px-2.5 py-1 text-[11px] font-medium bg-slate-900 text-slate-200 hover:bg-slate-800 border border-slate-700 rounded-md transition-colors whitespace-nowrap"
            >
              Tactical Matrix
            </button>
          </div>
        </div>

        {/* Top-Right Compact Audio Briefing & Live Probe Trigger */}
        <div className="pointer-events-auto hidden sm:flex items-center gap-2 self-start bg-[#070B16]/92 border border-slate-800/90 rounded-xl p-2">
          <button
            type="button"
            onClick={() => setChimesEnabled((v) => !v)}
            aria-label={chimesEnabled ? 'Mute telemetry sound effects' : 'Enable telemetry sound effects'}
            className="px-2.5 py-1.5 text-[11px] font-mono text-slate-300 hover:text-white bg-slate-900 border border-slate-800 rounded-lg transition-colors whitespace-nowrap"
          >
            {chimesEnabled ? 'SFX ON' : 'SFX OFF'}
          </button>

          {!isPlayingBriefing ? (
            <button
              type="button"
              onClick={onPlayBriefing}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-200 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg transition-colors whitespace-nowrap"
            >
              <Volume2 className="w-3.5 h-3.5 text-amber-400" aria-hidden="true" />
              Audio Brief
            </button>
          ) : (
            <button
              type="button"
              onClick={onStopBriefing}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-500 rounded-lg transition-colors whitespace-nowrap"
            >
              <VolumeX className="w-3.5 h-3.5" aria-hidden="true" />
              Stop Audio
            </button>
          )}

          <button
            type="button"
            onClick={() => onNavigateTab('optimus')}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap"
          >
            Optimus Ledger
            <ArrowUpRight className="w-3.5 h-3.5" aria-hidden="true" />
          </button>
        </div>
      </div>

      {webglLost && (
        <div
          role="alert"
          className="relative z-20 mx-6 max-w-md bg-rose-950/95 border border-rose-500/60 rounded-xl p-3 text-xs text-rose-100"
        >
          WebGL context interrupted — awaiting automatic GPU/driver restoration or switch to Tactical Matrix.
        </div>
      )}

      {briefingScript && (
        <div className="relative z-10 mx-6 max-w-xl bg-[#070B16]/95 border border-amber-500/40 rounded-xl p-3 text-xs text-slate-200 leading-relaxed flex items-start justify-between gap-3">
          <div>
            <span className="font-mono text-amber-400 mr-2">CAPTAIN SITREP:</span>
            {briefingScript}
          </div>
          {isPlayingBriefing && (
            <button
              type="button"
              onClick={onStopBriefing}
              className="px-2 py-1 text-[11px] font-mono text-rose-300 hover:text-white bg-rose-950/70 border border-rose-700/60 rounded shrink-0"
            >
              Stop
            </button>
          )}
        </div>
      )}

      {/* Unified Collapsible Bottom Center Command & Voice 2100 Dock (Three.js Skill §5) */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 w-[min(940px,94%)] flex flex-col items-center">
        <button
          type="button"
          onClick={() => setDockCollapsed((c) => !c)}
          aria-expanded={!dockCollapsed}
          className="inline-flex items-center gap-1.5 px-3.5 py-1 text-[11px] font-mono text-slate-300 hover:text-white bg-[#070B16]/95 border border-b-0 border-slate-700 rounded-t-lg transition-colors cursor-pointer whitespace-nowrap"
        >
          {dockCollapsed ? (
            <>
              <ChevronUp className="w-3.5 h-3.5 text-amber-400" />
              Show Controls &amp; Voice 2100
            </>
          ) : (
            <>
              <ChevronDown className="w-3.5 h-3.5 text-cyan-400" />
              Hide Controls (Zen Viewport)
            </>
          )}
        </button>

        {!dockCollapsed && (
          <div className="w-full bg-[#070B16]/95 border border-slate-700/90 rounded-xl p-4 space-y-3 shadow-2xl">
            {/* Row 1: Selected Node Telemetry & Physical Controls */}
            {selectedNode && (
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-slate-800/90">
                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="font-semibold text-white">{selectedNode.label}</span>
                    <span className="text-slate-600" aria-hidden="true">·</span>
                    <span className="font-mono text-cyan-300">{selectedNode.shaOrPointer}</span>
                    <span className="text-slate-600" aria-hidden="true">·</span>
                    <span className="font-mono text-slate-400">
                      {ACTIVITY_LABEL[selectedNode.activity]} · Gravity {gravityOf(selectedNode.eventCount, selectedNode.workload).toFixed(2)}g · Auth {selectedNode.authority}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 truncate">{selectedNode.detail}</p>
                </div>

                <div className="flex flex-wrap items-center gap-2 min-w-0 w-full md:w-auto">
                  <label htmlFor="reactor-node-picker" className="sr-only">
                    Select orbital node
                  </label>
                  <select
                    id="reactor-node-picker"
                    value={selectedNodeId}
                    onChange={(e) => {
                      const id = e.target.value;
                      setSelectedNodeId(id);
                      triggerNodeJet(nodes.find((n) => n.id === id));
                    }}
                    className="w-full sm:w-auto max-w-full px-2.5 py-1.5 text-xs font-mono bg-slate-900 text-slate-200 border border-slate-700 rounded-lg truncate"
                  >
                    {nodes.map((n) => (
                      <option key={n.id} value={n.id}>
                        {n.label} ({n.activity})
                      </option>
                    ))}
                  </select>

                  <button
                    type="button"
                    onClick={() => {
                      setBlastActive((b) => !b);
                      triggerNodeJet(selectedNode);
                    }}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors whitespace-nowrap ${
                      blastActive
                        ? 'bg-rose-600 text-white border-rose-500'
                        : 'bg-slate-900 text-slate-200 border-slate-700 hover:border-rose-500/60'
                    }`}
                  >
                    <Radio className="w-3.5 h-3.5" aria-hidden="true" />
                    {blastActive ? 'Stop Sonar Cascade' : 'Blast Cascade'}
                  </button>

                  <button
                    type="button"
                    disabled={actionBusy}
                    onClick={() => {
                      if (selectedNode.formation) {
                        executeCandidateAction({
                          targetNodeId: selectedNode.id,
                          actionKind: 'EXECUTE_LEGION',
                          formation: selectedNode.formation,
                          repo: selectedNode.repo ?? 'chidionyema/idp',
                          summaryText: `Execute ${selectedNode.label}: ${selectedNode.detail}`,
                        });
                      } else {
                        onNavigateTab(selectedNode.actionTab);
                      }
                    }}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-950 bg-cyan-400 hover:bg-cyan-300 disabled:opacity-50 rounded-lg transition-colors whitespace-nowrap"
                  >
                    <Play className="w-3 h-3" aria-hidden="true" />
                    {selectedNode.formation ? `Run ${selectedNode.formation}` : `Open ${selectedNode.actionTab}`}
                  </button>
                </div>
              </div>
            )}

            {/* Row 2: Voice 2100 Speculative Intent Compiler & 0.90 Clarification Handshake */}
            <form onSubmit={handleSpeculativeSubmit} className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
              <button
                type="button"
                onClick={toggleInlineDictation}
                aria-label={isInlineListening ? 'Stop live voice dictation' : 'Start live voice dictation or open Voice Stage'}
                className={`inline-flex items-center justify-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-lg transition-colors whitespace-nowrap shrink-0 ${
                  isInlineListening
                    ? 'bg-rose-600 hover:bg-rose-500 text-white'
                    : 'bg-amber-400 hover:bg-amber-300 text-slate-950'
                }`}
              >
                {isInlineListening ? (
                  <>
                    <Square className="w-3.5 h-3.5" aria-hidden="true" />
                    Stop Mic
                  </>
                ) : (
                  <>
                    <Mic className="w-3.5 h-3.5" aria-hidden="true" />
                    Speak
                  </>
                )}
              </button>

              <div className="relative flex-1 min-w-0">
                <label htmlFor="voice-2100-input" className="sr-only">
                  Voice 2100 speculative command bar
                </label>
                <input
                  id="voice-2100-input"
                  type="text"
                  value={utterance}
                  onChange={(e) => setUtterance(e.target.value)}
                  placeholder="Voice 2100 telepathic bar — speak or type 'verify optimus evidence', 'captain sitrep', 'run sniper on idp 2468', or 'fix main'…"
                  className="w-full px-3.5 py-2 text-xs bg-slate-900/95 border border-slate-700 rounded-lg text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-amber-400"
                />
              </div>

              {speculation && speculation.ok && (
                <span
                  className={`px-2.5 py-1.5 text-[11px] font-mono tabular-nums whitespace-nowrap shrink-0 ${
                    speculation.clarificationNeeded ? 'text-amber-300' : 'text-emerald-400'
                  }`}
                >
                  conf {(speculation.confidence * 100).toFixed(0)}% {speculation.clarificationNeeded ? '(<90% clarify)' : '(locked)'}
                </span>
              )}

              <button
                type="submit"
                disabled={actionBusy || !speculation || !speculation.ok || speculation.clarificationNeeded}
                className="inline-flex items-center justify-center gap-1.5 px-4 py-2 text-xs font-semibold text-slate-950 bg-cyan-400 hover:bg-cyan-300 disabled:opacity-40 rounded-lg transition-colors whitespace-nowrap shrink-0"
              >
                {actionBusy ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Crosshair className="w-3.5 h-3.5" />}
                Execute Intent
              </button>
            </form>

            {/* Quick Captain Vocal Directives + Keyboard Hint */}
            <div className="flex flex-wrap items-center justify-between gap-2 text-[11px]">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="font-mono text-slate-400 mr-0.5">Quick Voice:</span>
                {[
                  ['Captain Sitrep', 'give me a captain sitrep'],
                  ['Verify Optimus', 'verify optimus signed evidence'],
                  ['Audit #2468', 'run adversarial on idp 2468 vault'],
                  ['<0.90 Clarify', 'fix main'],
                ].map(([lbl, cmd]) => (
                  <button
                    key={lbl}
                    type="button"
                    onClick={() => setUtterance(cmd)}
                    className="px-2 py-0.5 font-mono text-slate-300 hover:text-amber-300 bg-slate-900/90 hover:bg-slate-800 border border-slate-800 rounded transition-colors whitespace-nowrap"
                  >
                    {lbl}
                  </button>
                ))}
              </div>
              <span className="hidden lg:inline font-mono text-slate-500">
                Keys: [1–3] Locks · [←/→] Orbit · [Space] Sonar · [H] Zen HUD
              </span>
            </div>

            {/* Voice 2100 0.90 Clarification Handshake Drawer (`kind="clarify"` on steer subject) */}
            {speculation && speculation.ok && speculation.clarificationNeeded && speculation.clarifyRow && (
              <div
                role="region"
                aria-label="Voice 2100 Clarification Handshake"
                className="p-3 bg-amber-950/35 border border-amber-500/40 rounded-lg space-y-2"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono text-amber-300">
                  <span>0.90 CLARIFICATION HANDSHAKE · {speculation.clarifyRow.subject}</span>
                  <span>kind=clarify</span>
                </div>
                <p className="text-xs text-slate-200">{speculation.clarifyRow.question}</p>
                <div className="flex flex-wrap gap-2 pt-0.5">
                  {speculation.clarifyRow.candidateActions.map((cand) => (
                    <button
                      key={cand.label}
                      type="button"
                      disabled={actionBusy}
                      onClick={() =>
                        executeCandidateAction({
                          targetNodeId: cand.targetNodeId,
                          actionKind: cand.actionKind,
                          targetTab: cand.targetTab,
                          formation: cand.formation,
                          repo: cand.repo,
                          summaryText: cand.utterance,
                        })
                      }
                      className="px-3 py-1.5 text-xs font-medium text-amber-100 bg-slate-900 hover:bg-amber-500 hover:text-slate-950 border border-amber-500/40 rounded-lg transition-colors text-left"
                    >
                      {cand.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {speculateError && (
              <p role="alert" className="text-xs font-mono text-rose-400">
                [SCHEMA_V2_ARMOR] {speculateError}
              </p>
            )}

            {statusBanner && (
              <p role="status" className="text-xs font-mono text-cyan-300">
                {statusBanner}
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  );
};
