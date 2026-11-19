/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * 
 * GENESIS ESTATE · 2100 ALIEN TOPOLOGICAL VIEW OF ESTATE & REAL-TIME OPERATIONS
 * Core Law #7 Compounding Invariant & Three.js 3D Living Organism
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import {
  LaneNode,
  FlowStateVitals,
  INITIAL_LANES,
  INITIAL_FLOW_VITALS,
  INITIAL_IPN_PACKETS,
  IpnPacket,
  DEMARCATION_MATRIX,
} from '../lib/protocolEngine.ts';
import { Alien2DTopologicalCanvas } from './Alien2DTopologicalCanvas.tsx';
import {
  Eye,
  Radio,
  Zap,
  ShieldCheck,
  Maximize2,
  Minimize2,
  Volume2,
  VolumeX,
  Compass,
  Play,
  RotateCcw,
  Sparkles,
  Layers,
  ChevronDown,
  ChevronUp,
  Cpu,
  Activity,
  GitBranch,
  Key,
  ShieldAlert,
  Server,
  Terminal,
} from 'lucide-react';

// ==============================================================================
// 1. REUSABLE MATH HELPERS & SCRATCHPADS (ZERO GC IN RENDER LOOP)
// ==============================================================================
const _vec3 = new THREE.Vector3();
const _vec3Target = new THREE.Vector3();
const _vec3Temp = new THREE.Vector3();
const _colorTemp = new THREE.Color();

// ==============================================================================
// 2. PROCEDURAL TEXTURE GENERATORS (ZERO 404 DEPENDENCY)
// ==============================================================================
function createGlowingParticleTexture(): THREE.Texture {
  const canvas = document.createElement('canvas');
  canvas.width = 128;
  canvas.height = 128;
  const ctx = canvas.getContext('2d')!;

  const gradient = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
  gradient.addColorStop(0, 'rgba(255, 255, 255, 1)');
  gradient.addColorStop(0.2, 'rgba(56, 189, 248, 0.85)');
  gradient.addColorStop(0.5, 'rgba(14, 165, 233, 0.4)');
  gradient.addColorStop(0.8, 'rgba(3, 105, 161, 0.15)');
  gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');

  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 128, 128);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

function createRunicRingTexture(): THREE.Texture {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 64;
  const ctx = canvas.getContext('2d')!;

  ctx.clearRect(0, 0, 512, 64);
  ctx.strokeStyle = 'rgba(56, 189, 248, 0.7)';
  ctx.lineWidth = 2;

  // Outer border lines
  ctx.beginPath();
  ctx.moveTo(0, 8);
  ctx.lineTo(512, 8);
  ctx.moveTo(0, 56);
  ctx.lineTo(512, 56);
  ctx.stroke();

  // Tick marks and runic telemetry markers
  for (let x = 0; x < 512; x += 16) {
    ctx.beginPath();
    ctx.moveTo(x, 16);
    ctx.lineTo(x, x % 32 === 0 ? 48 : 32);
    ctx.stroke();
  }

  // Telemetry glyph text
  ctx.fillStyle = 'rgba(125, 211, 252, 0.9)';
  ctx.font = '10px monospace';
  ctx.fillText('0x8F2D · RAFT QUORUM · ERA_1 · CANON §7 · ASYM >= 2.0 · HMAC-256', 20, 42);

  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  texture.repeat.set(2, 1);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

// ==============================================================================
// 3. TYPES & ESTATE TOPOLOGY CONTRACTS
// ==============================================================================
export type EstateSubsystemId =
  | 'SOVEREIGN_NUCLEUS'
  | 'LANE_A_GCP'
  | 'LANE_B_AWS'
  | 'LANE_C_OCI_RECOVERY'
  | 'LANE_C_MAC_EDGE'
  | 'GENESIS_KERNEL'
  | 'COMPOUNDING_CORE'
  | 'INSTRUCTION_MESH'
  | 'FLOW_FPRP_GATE'
  | 'KEY_LOAN_VAULT'
  | 'WWFD_BRIDGE'
  | 'ARGON_SYNC_BRIDGE'
  | 'HISTORY_QUARANTINE';

export interface TopologicalNodeMeta {
  id: EstateSubsystemId;
  name: string;
  category: 'TELEOLOGY' | 'QUORUM_NODE' | 'CORE_ORGAN' | 'SANDBOX';
  tagline: string;
  position: [number, number, number];
  color: string;
  accentColor: string;
  flowState: number; // 0 - 100
  latencyMs: number;
  spec: string;
  ip?: string;
  invariants: string[];
  metrics: { label: string; value: string }[];
}

export const TOPOLOGICAL_NODES: Record<EstateSubsystemId, TopologicalNodeMeta> = {
  SOVEREIGN_NUCLEUS: {
    id: 'SOVEREIGN_NUCLEUS',
    name: 'Sovereign Teleological Nucleus',
    category: 'TELEOLOGY',
    tagline: 'Root Authority & Founder Presence Attestation Beacon',
    position: [0, 0, 0],
    color: '#06b6d4',
    accentColor: '#38bdf8',
    flowState: 100,
    latencyMs: 0.1,
    spec: 'Ed25519 Beacon: 0x8f2d4e1a9c3b7f6e5a4d3c2b1a0f9e8d7c6b5a4',
    invariants: [
      '§1.1 Founder intent is non-negotiable origin',
      '§1.2 Sub-2.5ms Emergency Stop',
      '§1.3 Observation Lock: Zero execution without Founder attestation',
      '§1.4 Zero Friction Transfer: Δ_founder = 0',
    ],
    metrics: [
      { label: 'Halt Latency', value: '< 2.5 ms' },
      { label: 'Attestation', value: 'Ed25519 Verified' },
      { label: 'Observation Status', value: 'LOCKED ACTIVE' },
      { label: 'Friction Delta', value: 'Δ ≡ 0.00' },
    ],
  },
  LANE_A_GCP: {
    id: 'LANE_A_GCP',
    name: 'LANE_A_GCP (Raft Leader)',
    category: 'QUORUM_NODE',
    tagline: 'Term Authority & Primary Transaction Committer',
    position: [5.5, 0.4, 0],
    color: '#10b981',
    accentColor: '#34d399',
    flowState: 98.4,
    latencyMs: 11.2,
    spec: 'e2-micro (2 vCPU, 1 GB RAM) · europe-west3',
    ip: '100.100.1.1',
    invariants: ['§4.1 RAFT Quorum Leader, Term Authority', '§5.2 estate.db Authority & Write-Ahead Logs'],
    metrics: [
      { label: 'Raft Term', value: '#142' },
      { label: 'Log Index', value: '88,941' },
      { label: 'Heartbeat Lease', value: '5.0s / 5.0s' },
      { label: 'Consensus', value: 'HEALTHY LEADER' },
    ],
  },
  LANE_B_AWS: {
    id: 'LANE_B_AWS',
    name: 'LANE_B_AWS (Raft Follower)',
    category: 'QUORUM_NODE',
    tagline: 'Redundant Multi-Cloud Consensus Follower',
    position: [0, 0.2, 5.5],
    color: '#3b82f6',
    accentColor: '#60a5fa',
    flowState: 97.1,
    latencyMs: 14.8,
    spec: 't3.micro (2 vCPU, 1 GB RAM) · eu-central-1',
    ip: '100.100.1.2',
    invariants: ['§4.2 RAFT Quorum Follower, Redundant Consensus', '§5.1 Step Telemetry HMAC Attestation'],
    metrics: [
      { label: 'Raft Role', value: 'FOLLOWER' },
      { label: 'Commit Sync', value: '100% In-Step' },
      { label: 'Ping Latency', value: '14.8 ms' },
      { label: 'Egress Cost', value: '$0.00 (PRM Capped)' },
    ],
  },
  LANE_C_OCI_RECOVERY: {
    id: 'LANE_C_OCI_RECOVERY',
    name: 'LANE_C_OCI (Disaster Recovery)',
    category: 'QUORUM_NODE',
    tagline: 'Cold Standby Consensus Quorum Follower',
    position: [-5.5, -0.3, 0],
    color: '#8b5cf6',
    accentColor: '#a78bfa',
    flowState: 95.8,
    latencyMs: 24.5,
    spec: 'estate-recovery-vm (Ampere A1) · Frankfurt',
    ip: '100.100.1.3',
    invariants: ['§4.3 estate-recovery-vm RAFT Follower', 'Failover ready in < 450ms'],
    metrics: [
      { label: 'Raft Role', value: 'FOLLOWER (RECOVERY)' },
      { label: 'Storage Replicated', value: '100.0%' },
      { label: 'Failover SLA', value: '< 450 ms' },
      { label: 'Snapshot Freshness', value: '12s ago' },
    ],
  },
  LANE_C_MAC_EDGE: {
    id: 'LANE_C_MAC_EDGE',
    name: 'LANE_C_MAC_EDGE (Apple Silicon)',
    category: 'QUORUM_NODE',
    tagline: 'Sovereign Edge Worker with Zero Cloud Egress Canon',
    position: [0, -0.4, -5.5],
    color: '#f59e0b',
    accentColor: '#fbbf24',
    flowState: 99.2,
    latencyMs: 3.4,
    spec: 'Apple M-Series Sovereign Worker · Tailscale mesh',
    ip: '100.98.58.115',
    invariants: ['§4.4 Non-voting 15s Heartbeat Lease', '§4.5 Zero Cloud Egress Canon'],
    metrics: [
      { label: 'Worker Lease', value: '14.2s / 15.0s' },
      { label: 'Local Compute', value: '100% On-Device' },
      { label: 'Cloud Egress', value: '0 bytes (Verified)' },
      { label: 'Runner Health', value: 'ACTIVE NOMINAL' },
    ],
  },
  GENESIS_KERNEL: {
    id: 'GENESIS_KERNEL',
    name: 'Genesis Kernel & Constitutional Spine',
    category: 'CORE_ORGAN',
    tagline: 'Machine-Enforced Canon (AGENTS.md <= 107 lines)',
    position: [3.8, 3.2, 2.5],
    color: '#06b6d4',
    accentColor: '#67e8f9',
    flowState: 100,
    latencyMs: 0.2,
    spec: 'AGENTS.md ERA_1 Genesis v1.0.26',
    invariants: ['Strict <= 107 physical lines invariant', 'Self-describing module contracts (§7.1)'],
    metrics: [
      { label: 'Physical Lines', value: '66 / 107 max' },
      { label: 'Drift Rate', value: '0.00% (Machine-Audited)' },
      { label: 'Contract Schema', value: 'JSON-Schema Sealed' },
      { label: 'Status', value: 'PASS 0 DIAGNOSTICS' },
    ],
  },
  COMPOUNDING_CORE: {
    id: 'COMPOUNDING_CORE',
    name: 'Compounding Engineering Core (Law #7)',
    category: 'CORE_ORGAN',
    tagline: 'Asymmetry Engine & Point-Fix Rejection Gate',
    position: [-3.8, 3.2, 2.5],
    color: '#10b981',
    accentColor: '#6ee7b7',
    flowState: 99.4,
    latencyMs: 0.8,
    spec: 'R_asym = Δ_leverage / Δ_cost >= 2.00',
    invariants: ['§2.1 Mathematical Invariant R_asym >= 2.0', '§2.2 Point-Fix Prohibition (< 0.8 coverage)'],
    metrics: [
      { label: 'Asymmetry Ratio', value: '4.80x (>= 2.00)' },
      { label: 'Point-Fixes Blocked', value: '12 Rejected' },
      { label: 'Leverage Compounded', value: '+340% Cumulative' },
      { label: 'Automated Tests', value: '14/14 Passing' },
    ],
  },
  INSTRUCTION_MESH: {
    id: 'INSTRUCTION_MESH',
    name: 'Instruction Pocket Network (IPN)',
    category: 'CORE_ORGAN',
    tagline: 'Continuous Telemetric Packet Lifecycles with CDO Reviews',
    position: [4.2, 1.8, -3.2],
    color: '#6366f1',
    accentColor: '#818cf8',
    flowState: 96.8,
    latencyMs: 4.1,
    spec: 'End-to-End Packet Telemetry & Stage Handoffs',
    invariants: ['Every instruction is a probe', 'Full CDO review on each stage transition'],
    metrics: [
      { label: 'In-Flight Packets', value: '3 Active Packets' },
      { label: 'Handoff Drop Rate', value: '0.000%' },
      { label: 'Mean Handoff Time', value: '12.4 ms' },
      { label: 'CDO Attestation', value: '100% Signed' },
    ],
  },
  FLOW_FPRP_GATE: {
    id: 'FLOW_FPRP_GATE',
    name: 'Flow State & FPRP Anti-Recursion Gate (§9)',
    category: 'CORE_ORGAN',
    tagline: 'Debt Ledger, Break-Glass Loans & Oscillation Breaker',
    position: [-4.2, 1.8, -3.2],
    color: '#ec4899',
    accentColor: '#f472b6',
    flowState: 97.9,
    latencyMs: 1.2,
    spec: 'Flow-Preserving Remediation Protocol (FPRP)',
    invariants: ['§9.1 Break-glass as loan, never permanent fix', '§9.4 Oscillation Circuit Breaker'],
    metrics: [
      { label: 'Open Debt Loans', value: '1 Loan (3h 42m left)' },
      { label: 'Credit Freeze Status', value: 'HEALTHY UNLOCKED' },
      { label: 'Loops Blocked', value: '+14 Recursive Loops' },
      { label: 'Tail-Chasing Risk', value: 'ZERO' },
    ],
  },
  KEY_LOAN_VAULT: {
    id: 'KEY_LOAN_VAULT',
    name: 'Key Loan Protocol (KLP Vault)',
    category: 'CORE_ORGAN',
    tagline: 'Zero Standing Privileges & Ephemeral Credential Leases',
    position: [3.2, -3.0, 1.8],
    color: '#eab308',
    accentColor: '#fde047',
    flowState: 99.8,
    latencyMs: 0.4,
    spec: 'Time-Bound Token Expiration (TTL: 300s)',
    invariants: ['Zero standing agent access to sovereign secrets', 'Auto-revocation upon step completion'],
    metrics: [
      { label: 'Standing Access', value: '0 Agents' },
      { label: 'Active Leases', value: '2 Ephemeral Leases' },
      { label: 'Auto-Revoke Rate', value: '100.0%' },
      { label: 'Leak Surface', value: 'NULL' },
    ],
  },
  WWFD_BRIDGE: {
    id: 'WWFD_BRIDGE',
    name: 'WWFD Daily Calibration Compass (§6)',
    category: 'CORE_ORGAN',
    tagline: 'What Would Founder Do & Local DPO Preference Vectors',
    position: [-3.2, -3.0, 1.8],
    color: '#14b8a6',
    accentColor: '#2dd4bf',
    flowState: 98.2,
    latencyMs: 0.9,
    spec: '5-Card High-Entropy Trade-off Deck (Divergence < 0.15)',
    invariants: ['§6.1 Daily 1-keystroke trade-off calibration', '§6.3 Local DPO training tuples without egress'],
    metrics: [
      { label: 'Strategic Delta', value: '0.04 (< 0.15 limit)' },
      { label: 'DPO Tuples', value: '240 Recorded' },
      { label: 'Calibration Deck', value: '5/5 Evaluated' },
      { label: 'Otto Alignment', value: '98.8%' },
    ],
  },
  ARGON_SYNC_BRIDGE: {
    id: 'ARGON_SYNC_BRIDGE',
    name: 'Non-Destructive Argon Sync Bridge (§8)',
    category: 'CORE_ORGAN',
    tagline: 'Target: chidionyema/argon (Branch: genesis-live)',
    position: [0, 4.2, 0],
    color: '#0284c7',
    accentColor: '#38bdf8',
    flowState: 100,
    latencyMs: 1.5,
    spec: 'Refs/heads/genesis-live · Sealed Tag v1.0.26',
    invariants: ['§8.1 Upstream main inviolability (zero force-push)', '§8.2 Independent live ref with sealed release tag'],
    metrics: [
      { label: 'Target Repo', value: 'chidionyema/argon' },
      { label: 'Live Ref', value: 'genesis-live' },
      { label: 'Release Tag', value: 'v1.0.26 / v1.0.27' },
      { label: 'Bundle Size', value: '1.7 MB (Verified)' },
    ],
  },
  HISTORY_QUARANTINE: {
    id: 'HISTORY_QUARANTINE',
    name: 'History Lane Archaeological Quarantine',
    category: 'SANDBOX',
    tagline: 'Quarantined Mac Host & DeepSeek 401/503 Recovered Door',
    position: [0, -4.5, 0],
    color: '#94a3b8',
    accentColor: '#cbd5e1',
    flowState: 92.5,
    latencyMs: 18.0,
    spec: 'Legacy IDP Artifact · $0 Budget Cap · Zero Genesis Blocking',
    invariants: ['Strict non-interference with Genesis Estate', 'DeepSeek credentials sanitized & mapped to deepseek-chat'],
    metrics: [
      { label: 'DeepSeek 401 Fix', value: 'Sanitized Quotes & CRLF' },
      { label: 'DeepSeek 503 Fix', value: 'Aliased -> deepseek-chat' },
      { label: 'Disk Space Floor', value: '1500 MB Safe Purged' },
      { label: 'Launch Blocker', value: 'NONE (Quarantined)' },
    ],
  },
};

// ==============================================================================
// 4. PROCEDURAL AUDIO SYNTHESIZER (WEB AUDIO API · 432HZ HARMONIC HYPNOSIS)
// ==============================================================================
class AlienHarmonicSynthesizer {
  private ctx: AudioContext | null = null;
  private masterGain: GainNode | null = null;
  private oscDrone1: OscillatorNode | null = null;
  private oscDrone2: OscillatorNode | null = null;
  private filter: BiquadFilterNode | null = null;
  private isMuted: boolean = true;

  public init() {
    if (this.ctx) return;
    try {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      this.ctx = new AudioCtx();

      this.masterGain = this.ctx.createGain();
      this.masterGain.gain.setValueAtTime(0.0001, this.ctx.currentTime);

      this.filter = this.ctx.createBiquadFilter();
      this.filter.type = 'lowpass';
      this.filter.frequency.setValueAtTime(320, this.ctx.currentTime);
      this.filter.Q.setValueAtTime(3.5, this.ctx.currentTime);

      // Deep 432Hz Sub-Harmonic (108Hz base)
      this.oscDrone1 = this.ctx.createOscillator();
      this.oscDrone1.type = 'sine';
      this.oscDrone1.frequency.setValueAtTime(108, this.ctx.currentTime);

      // Celestial 5th Harmonic (162Hz)
      this.oscDrone2 = this.ctx.createOscillator();
      this.oscDrone2.type = 'triangle';
      this.oscDrone2.frequency.setValueAtTime(162, this.ctx.currentTime);

      const gain1 = this.ctx.createGain();
      gain1.gain.setValueAtTime(0.35, this.ctx.currentTime);
      const gain2 = this.ctx.createGain();
      gain2.gain.setValueAtTime(0.18, this.ctx.currentTime);

      this.oscDrone1.connect(gain1);
      this.oscDrone2.connect(gain2);

      gain1.connect(this.filter);
      gain2.connect(this.filter);

      this.filter.connect(this.masterGain);
      this.masterGain.connect(this.ctx.destination);

      this.oscDrone1.start();
      this.oscDrone2.start();
    } catch {
      // Audio blocked or unsupported
    }
  }

  public setMuted(muted: boolean) {
    this.isMuted = muted;
    if (!this.ctx || !this.masterGain) return;
    if (this.ctx.state === 'suspended' && !muted) {
      this.ctx.resume();
    }
    const targetGain = muted ? 0.0001 : 0.07;
    this.masterGain.gain.setTargetAtTime(targetGain, this.ctx.currentTime, 0.4);
  }

  public playHeartbeatThump() {
    if (this.isMuted || !this.ctx || !this.masterGain) return;
    try {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(80, this.ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(36, this.ctx.currentTime + 0.18);

      gain.gain.setValueAtTime(0.12, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, this.ctx.currentTime + 0.18);

      osc.connect(gain);
      gain.connect(this.masterGain);
      osc.start();
      osc.stop(this.ctx.currentTime + 0.19);
    } catch {}
  }

  public playNodeChime(freq = 540) {
    if (this.isMuted || !this.ctx || !this.masterGain) return;
    try {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(freq * 1.5, this.ctx.currentTime + 0.25);

      gain.gain.setValueAtTime(0.09, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, this.ctx.currentTime + 0.28);

      osc.connect(gain);
      gain.connect(this.masterGain);
      osc.start();
      osc.stop(this.ctx.currentTime + 0.3);
    } catch {}
  }

  public dispose() {
    try {
      this.oscDrone1?.stop();
      this.oscDrone2?.stop();
      this.ctx?.close();
    } catch {}
  }
}

// ==============================================================================
// 5. MAIN EXTRAORDINARY 3D ALIEN TOPOLOGICAL SURFACE
// ==============================================================================
interface AlienTopologicalEstateSurfaceProps {
  onSelectPacket?: (packetId: string) => void;
  onNavigateToLane?: (laneId: string) => void;
  onNavigateToFprp?: () => void;
}

export const AlienTopologicalEstateSurface: React.FC<AlienTopologicalEstateSurfaceProps> = ({
  onSelectPacket,
  onNavigateToLane,
  onNavigateToFprp,
}) => {
  // DOM & Three.js Canvas Container Ref
  const canvasMountRef = useRef<HTMLDivElement>(null);

  // Audio Synthesizer Ref
  const audioSynthRef = useRef<AlienHarmonicSynthesizer | null>(null);

  // Interactive UI State
  const [selectedSubsystem, setSelectedSubsystem] = useState<EstateSubsystemId>('SOVEREIGN_NUCLEUS');
  const [hoveredSubsystem, setHoveredSubsystem] = useState<EstateSubsystemId | null>(null);
  const [activeTabDock, setActiveTabDock] = useState<'LAYERS' | 'OPERATIONS' | 'CONSENSUS' | 'CONTROLS'>('LAYERS');
  const [isCinemaMode, setIsCinemaMode] = useState<boolean>(false);
  const [isAudioMuted, setIsAudioMuted] = useState<boolean>(true);
  const [zenDriftEnabled, setZenDriftEnabled] = useState<boolean>(true);
  const [explodedLayerSeparation, setExplodedLayerSeparation] = useState<number>(1.0);
  const [simulatedPacketsCount, setSimulatedPacketsCount] = useState<number>(3);
  const [activeFrictionFlash, setActiveFrictionFlash] = useState<boolean>(false);
  const [isWebGlFallback, setIsWebGlFallback] = useState<boolean>(false);

  // Dynamic values tracked in refs to eliminate unneeded WebGL context re-instantiation
  const explodedSeparationRef = useRef(explodedLayerSeparation);
  explodedSeparationRef.current = explodedLayerSeparation;

  const zenDriftRef = useRef(zenDriftEnabled);
  zenDriftRef.current = zenDriftEnabled;

  const hoveredSubsystemRef = useRef(hoveredSubsystem);
  hoveredSubsystemRef.current = hoveredSubsystem;

  const handleFocusNodeRef = useRef<(nodeId: EstateSubsystemId) => void>(() => {});

  // Vitals & Telemetry State
  const [vitals, setVitals] = useState<FlowStateVitals>(INITIAL_FLOW_VITALS);
  const [lanes, setLanes] = useState<LaneNode[]>(INITIAL_LANES);
  const [packets, setPackets] = useState<IpnPacket[]>(INITIAL_IPN_PACKETS);

  // Three.js mutable state stored in refs to prevent component re-instantiation
  const threeStateRef = useRef<{
    renderer: THREE.WebGLRenderer | null;
    scene: THREE.Scene | null;
    camera: THREE.PerspectiveCamera | null;
    controls: OrbitControls | null;
    nodeGroups: Map<EstateSubsystemId, THREE.Group>;
    splineCurves: THREE.CatmullRomCurve3[];
    packetMeshes: THREE.Mesh[];
    stardustParticles: THREE.Points | null;
    concentricRings: THREE.Mesh[];
    cameraTargetPos: THREE.Vector3;
    controlsTargetPos: THREE.Vector3;
    isTransitioningCamera: boolean;
    raycaster: THREE.Raycaster;
    mouse: THREE.Vector2;
  }>({
    renderer: null,
    scene: null,
    camera: null,
    controls: null,
    nodeGroups: new Map(),
    splineCurves: [],
    packetMeshes: [],
    stardustParticles: null,
    concentricRings: [],
    cameraTargetPos: new THREE.Vector3(0, 8, 18),
    controlsTargetPos: new THREE.Vector3(0, 0, 0),
    isTransitioningCamera: false,
    raycaster: new THREE.Raycaster(),
    mouse: new THREE.Vector2(-999, -999),
  });

  // Initialize Audio Engine once
  useEffect(() => {
    const synth = new AlienHarmonicSynthesizer();
    synth.init();
    audioSynthRef.current = synth;

    return () => {
      synth.dispose();
      audioSynthRef.current = null;
    };
  }, []);

  // Update audio muted state
  useEffect(() => {
    audioSynthRef.current?.setMuted(isAudioMuted);
  }, [isAudioMuted]);

  // Periodic living metabolic pulse and telemetry jitter
  useEffect(() => {
    const interval = setInterval(() => {
      setVitals((v) => ({
        ...v,
        estateTimeInFlowPercent: Number((97.2 + Math.random() * 0.5).toFixed(1)),
        averageWaitTimeMs: Number((12.8 + Math.random() * 1.2).toFixed(1)),
      }));

      // Metabolic audio pulse
      audioSynthRef.current?.playHeartbeatThump();
    }, 1200);

    return () => clearInterval(interval);
  }, []);

  // Dispatch new live instruction packet simulation
  const handleDispatchProbePacket = useCallback(() => {
    const newId = `IPN-PROBE-${Date.now().toString().slice(-4)}`;
    const newPacket: IpnPacket = {
      packetId: newId,
      instructionText: 'Sovereign Teleology Probe: Attest zero-friction invariant across 4 Raft nodes',
      sender: 'SOVEREIGN_FOUNDER',
      targetLane: 'LANE_A_GCP',
      currentStage: 'INTAKE',
      startTime: new Date().toISOString(),
      totalLatencyMs: 14.2,
      tokenConsumption: 120,
      computeCostUsd: 0.0001,
      decisionsTaken: ['Quorum Leader Verified', 'Zero Friction Confirmed'],
      alternativesRejected: ['Remote Egress Bypassed'],
      oracleAlignmentScore: 0.998,
      historyLog: [
        {
          stage: 'INTAKE',
          timestamp: new Date().toISOString(),
          agent: 'otto',
          durationMs: 4.2,
          notes: 'Probe ingested with zero founder friction offload.',
        },
      ],
    };

    setPackets((prev) => [newPacket, ...prev.slice(0, 4)]);
    setSimulatedPacketsCount((c) => c + 1);
    audioSynthRef.current?.playNodeChime(720);
  }, []);

  // Camera preset navigation
  const setCameraView = useCallback((preset: 'PANORAMA' | 'NUCLEUS' | 'QUORUM' | 'ORGANS' | 'TACTICAL') => {
    const state = threeStateRef.current;
    if (!state.camera || !state.controls) return;

    state.isTransitioningCamera = true;

    switch (preset) {
      case 'PANORAMA':
        state.cameraTargetPos.set(0, 9, 20);
        state.controlsTargetPos.set(0, 0, 0);
        break;
      case 'NUCLEUS':
        state.cameraTargetPos.set(0, 2.2, 5.5);
        state.controlsTargetPos.set(0, 0, 0);
        setSelectedSubsystem('SOVEREIGN_NUCLEUS');
        break;
      case 'QUORUM':
        state.cameraTargetPos.set(8.5, 4.0, 8.5);
        state.controlsTargetPos.set(1.5, 0, 1.5);
        setSelectedSubsystem('LANE_A_GCP');
        break;
      case 'ORGANS':
        state.cameraTargetPos.set(-7.5, 7.5, 11.0);
        state.controlsTargetPos.set(0, 2.0, 0);
        setSelectedSubsystem('COMPOUNDING_CORE');
        break;
      case 'TACTICAL':
        state.cameraTargetPos.set(0, 24, 0.1);
        state.controlsTargetPos.set(0, 0, 0);
        break;
    }

    audioSynthRef.current?.playNodeChime(480);
  }, []);

  // Focus on specific subsystem node
  const handleFocusNode = useCallback((nodeId: EstateSubsystemId) => {
    setSelectedSubsystem(nodeId);
    const meta = TOPOLOGICAL_NODES[nodeId];
    if (!meta) return;

    const state = threeStateRef.current;
    if (state.camera && state.controls) {
      state.isTransitioningCamera = true;
      const [nx, ny, nz] = meta.position;
      const sep = explodedSeparationRef.current;
      state.controlsTargetPos.set(nx, ny * sep, nz);
      state.cameraTargetPos.set(
        nx + (nx >= 0 ? 3.5 : -3.5),
        ny * sep + 2.5,
        nz + (nz >= 0 ? 4.5 : -4.5)
      );
    }

    audioSynthRef.current?.playNodeChime(600);
  }, []);

  handleFocusNodeRef.current = handleFocusNode;

  // ==============================================================================
  // 6. THREE.JS MOUNT & LIFECYCLE (ENFORCING THREE.JS SKILL DIRECTIVES)
  // ==============================================================================
  useEffect(() => {
    const mount = canvasMountRef.current;
    if (!mount) return;

    // Directives 1: Safe Capability Probe for WebGL
    const checkWebGLContext = (): boolean => {
      try {
        if (!window.WebGLRenderingContext) return false;
        const probe = document.createElement('canvas');
        const gl = (probe.getContext('webgl2') ||
          probe.getContext('webgl') ||
          probe.getContext('experimental-webgl')) as (WebGLRenderingContext | WebGL2RenderingContext | null);
        if (!gl) return false;
        const loseExt = gl.getExtension('WEBGL_lose_context');
        if (loseExt) loseExt.loseContext();
        return true;
      } catch {
        return false;
      }
    };

    if (!checkWebGLContext()) {
      console.info('[AlienTopologicalEstateSurface] WebGL not available in this environment. Seamlessly activating 2100 Sovereign 2D Vector Fallback.');
      setIsWebGlFallback(true);
      return;
    }

    // Directives 1: Software WebGL Detection
    let isSoftwareGl = false;
    try {
      const probeCanvas = document.createElement('canvas');
      const gl = (probeCanvas.getContext('webgl2') || probeCanvas.getContext('webgl')) as (WebGLRenderingContext | WebGL2RenderingContext | null);
      if (gl) {
        const ext = gl.getExtension('WEBGL_debug_renderer_info');
        const param = ext ? ext.UNMASKED_RENDERER_WEBGL : gl.RENDERER;
        const gpu = String(gl.getParameter(param));
        gl.getExtension('WEBGL_lose_context')?.loseContext();
        isSoftwareGl = /SwiftShader|llvmpipe|softpipe|Software|Basic Render/i.test(gpu);
      } else {
        isSoftwareGl = true;
      }
    } catch {
      isSoftwareGl = true;
    }

    // Initialize Renderer inside safe try-catch
    const width = mount.clientWidth || window.innerWidth;
    const height = mount.clientHeight || window.innerHeight;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: !isSoftwareGl,
        powerPreference: 'high-performance',
        alpha: true,
        failIfMajorPerformanceCaveat: false,
      });
      renderer.setSize(width, height);
      renderer.setPixelRatio(isSoftwareGl ? 1 : Math.min(window.devicePixelRatio, 2));
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.15;
      renderer.shadowMap.enabled = !isSoftwareGl;
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;

      mount.appendChild(renderer.domElement);
    } catch (webglErr) {
      console.warn('[AlienTopologicalEstateSurface] Failed to create WebGLRenderer context. Activating 2100 Sovereign 2D Fallback:', webglErr);
      setIsWebGlFallback(true);
      return;
    }

    // Initialize Scene
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x020617, 0.024);

    // Camera
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
    camera.position.set(0, 9, 20);

    // OrbitControls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = !isSoftwareGl;
    controls.dampingFactor = 0.06;
    controls.minDistance = 3.5;
    controls.maxDistance = 55;
    controls.maxPolarAngle = Math.PI / 2 + 0.25;

    // Studio Environment Reflections via RoomEnvironment
    const pmremGenerator = new THREE.PMREMGenerator(renderer);
    scene.environment = pmremGenerator.fromScene(new RoomEnvironment(), 0.04).texture;
    pmremGenerator.dispose();

    // Studio 3-Point Lighting Rig
    const ambientLight = new THREE.AmbientLight(0x0a192f, 1.2);
    scene.add(ambientLight);

    const hemiLight = new THREE.HemisphereLight(0x38bdf8, 0x020617, 1.5);
    hemiLight.position.set(0, 20, 0);
    scene.add(hemiLight);

    const keyLight = new THREE.DirectionalLight(0x67e8f9, 2.5);
    keyLight.position.set(12, 18, 10);
    keyLight.castShadow = !isSoftwareGl;
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0x818cf8, 1.2);
    fillLight.position.set(-12, -8, -10);
    scene.add(fillLight);

    // Pre-create Shared Geometries & Materials
    const particleTex = createGlowingParticleTexture();
    const runicTex = createRunicRingTexture();

    // Stardust Field (1,200 points)
    const stardustCount = 1200;
    const stardustGeo = new THREE.BufferGeometry();
    const stardustPos = new Float32Array(stardustCount * 3);
    const stardustColors = new Float32Array(stardustCount * 3);

    for (let i = 0; i < stardustCount; i++) {
      const radius = 6 + Math.random() * 26;
      const theta = Math.random() * Math.PI * 2;
      const phi = (Math.random() - 0.5) * Math.PI * 0.7;

      stardustPos[i * 3] = radius * Math.cos(theta) * Math.cos(phi);
      stardustPos[i * 3 + 1] = radius * Math.sin(phi);
      stardustPos[i * 3 + 2] = radius * Math.sin(theta) * Math.cos(phi);

      // Alien cyan, purple, and emerald hues
      const colChoice = Math.random();
      if (colChoice < 0.45) {
        stardustColors[i * 3] = 0.22;
        stardustColors[i * 3 + 1] = 0.74;
        stardustColors[i * 3 + 2] = 0.97;
      } else if (colChoice < 0.8) {
        stardustColors[i * 3] = 0.51;
        stardustColors[i * 3 + 1] = 0.36;
        stardustColors[i * 3 + 2] = 0.96;
      } else {
        stardustColors[i * 3] = 0.06;
        stardustColors[i * 3 + 1] = 0.72;
        stardustColors[i * 3 + 2] = 0.51;
      }
    }
    stardustGeo.setAttribute('position', new THREE.BufferAttribute(stardustPos, 3));
    stardustGeo.setAttribute('color', new THREE.BufferAttribute(stardustColors, 3));

    const stardustMat = new THREE.PointsMaterial({
      size: 0.35,
      map: particleTex,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      vertexColors: true,
    });
    const stardust = new THREE.Points(stardustGeo, stardustMat);
    scene.add(stardust);

    // Celestial Holographic Concentric Rings
    const ringGeo1 = new THREE.RingGeometry(5.2, 5.6, 64);
    const ringMat1 = new THREE.MeshBasicMaterial({
      map: runicTex,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.65,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const ring1 = new THREE.Mesh(ringGeo1, ringMat1);
    ring1.rotation.x = Math.PI / 2;
    scene.add(ring1);

    const ringGeo2 = new THREE.RingGeometry(7.8, 8.1, 64);
    const ringMat2 = new THREE.MeshBasicMaterial({
      color: 0x0284c7,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.35,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const ring2 = new THREE.Mesh(ringGeo2, ringMat2);
    ring2.rotation.x = Math.PI / 2;
    scene.add(ring2);

    // ==============================================================================
    // 7. BUILD 3D COMPOSITE PROCEDURAL NODES (THREE.Group · Directives §1)
    // ==============================================================================
    const nodeGroups = new Map<EstateSubsystemId, THREE.Group>();

    Object.values(TOPOLOGICAL_NODES).forEach((meta) => {
      const group = new THREE.Group();
      group.name = meta.id;
      group.position.set(meta.position[0], meta.position[1], meta.position[2]);

      const baseColor = new THREE.Color(meta.color);
      const accentColor = new THREE.Color(meta.accentColor);

      if (meta.id === 'SOVEREIGN_NUCLEUS') {
        // Hero Central Founder Nucleus (Composite 5-Part 3D Object)
        // Part 1: Outer Geodesic Icosahedron Wireframe
        const icoGeo = new THREE.IcosahedronGeometry(1.4, 2);
        const icoMat = new THREE.MeshStandardMaterial({
          color: baseColor,
          roughness: 0.1,
          metalness: 0.9,
          wireframe: true,
          emissive: baseColor,
          emissiveIntensity: 0.3,
        });
        const icoMesh = new THREE.Mesh(icoGeo, icoMat);
        group.add(icoMesh);

        // Part 2: Inner Faceted Core
        const coreGeo = new THREE.OctahedronGeometry(0.85, 1);
        const coreMat = new THREE.MeshPhysicalMaterial({
          color: accentColor,
          roughness: 0.15,
          metalness: 0.95,
          clearcoat: 1.0,
          emissive: baseColor,
          emissiveIntensity: 0.5,
        });
        const coreMesh = new THREE.Mesh(coreGeo, coreMat);
        group.add(coreMesh);

        // Part 3: Nested Plasma Halo
        const haloGeo = new THREE.TorusGeometry(1.85, 0.04, 16, 64);
        const haloMat = new THREE.MeshBasicMaterial({
          color: accentColor,
          transparent: true,
          opacity: 0.8,
          blending: THREE.AdditiveBlending,
        });
        const haloMesh = new THREE.Mesh(haloGeo, haloMat);
        haloMesh.rotation.x = Math.PI / 2.8;
        group.add(haloMesh);

        // Part 4: Vertical Energy Ring
        const vHaloMesh = haloMesh.clone();
        vHaloMesh.rotation.y = Math.PI / 2.4;
        group.add(vHaloMesh);

        // Part 5: Contact Grounding Shadow Plane
        const groundGeo = new THREE.CircleGeometry(2.4, 32);
        const groundMat = new THREE.MeshBasicMaterial({
          color: 0x082f49,
          transparent: true,
          opacity: 0.45,
          depthWrite: false,
        });
        const ground = new THREE.Mesh(groundGeo, groundMat);
        ground.rotation.x = -Math.PI / 2;
        ground.position.y = -1.5;
        group.add(ground);
      } else if (meta.category === 'QUORUM_NODE') {
        // Multi-Lane Raft Quorum Node (Composite 4-Part 3D Object)
        // Part 1: Main Core Sphere
        const sphereGeo = new THREE.SphereGeometry(0.65, 24, 24);
        const sphereMat = new THREE.MeshStandardMaterial({
          color: baseColor,
          roughness: 0.25,
          metalness: 0.8,
          emissive: baseColor,
          emissiveIntensity: 0.2,
        });
        const sphere = new THREE.Mesh(sphereGeo, sphereMat);
        group.add(sphere);

        // Part 2: Equatorial Orbital Band
        const ringGeo = new THREE.TorusGeometry(0.95, 0.03, 12, 32);
        const ringMat = new THREE.MeshBasicMaterial({
          color: accentColor,
          transparent: true,
          opacity: 0.7,
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = Math.PI / 2;
        group.add(ring);

        // Part 3: Data Shield Cage
        const cageGeo = new THREE.DodecahedronGeometry(0.85, 0);
        const cageMat = new THREE.MeshBasicMaterial({
          color: accentColor,
          wireframe: true,
          transparent: true,
          opacity: 0.4,
        });
        const cage = new THREE.Mesh(cageGeo, cageMat);
        group.add(cage);

        // Part 4: Soft Grounding Halo
        const haloGeo = new THREE.CircleGeometry(1.2, 24);
        const haloMat = new THREE.MeshBasicMaterial({
          color: 0x020617,
          transparent: true,
          opacity: 0.35,
          depthWrite: false,
        });
        const halo = new THREE.Mesh(haloGeo, haloMat);
        halo.rotation.x = -Math.PI / 2;
        halo.position.y = -0.9;
        group.add(halo);
      } else {
        // Subsystem Organ Node (Composite 3-Part 3D Object)
        // Part 1: Distinct Geometric Hull
        const hullGeo =
          meta.id === 'COMPOUNDING_CORE'
            ? new THREE.OctahedronGeometry(0.65, 0)
            : meta.id === 'INSTRUCTION_MESH'
            ? new THREE.TorusGeometry(0.55, 0.18, 16, 32)
            : meta.id === 'FLOW_FPRP_GATE'
            ? new THREE.DodecahedronGeometry(0.65, 0)
            : new THREE.BoxGeometry(0.85, 0.85, 0.85);

        const hullMat = new THREE.MeshStandardMaterial({
          color: baseColor,
          roughness: 0.35,
          metalness: 0.65,
          emissive: baseColor,
          emissiveIntensity: 0.25,
        });
        const hull = new THREE.Mesh(hullGeo, hullMat);
        group.add(hull);

        // Part 2: Outer Wireframe Lattice
        const latticeMat = new THREE.MeshBasicMaterial({
          color: accentColor,
          wireframe: true,
          transparent: true,
          opacity: 0.5,
        });
        const lattice = new THREE.Mesh(hullGeo.clone(), latticeMat);
        lattice.scale.set(1.2, 1.2, 1.2);
        group.add(lattice);

        // Part 3: Floating Beacon Crystal
        const beaconGeo = new THREE.TetrahedronGeometry(0.25);
        const beaconMat = new THREE.MeshBasicMaterial({
          color: 0xffffff,
          wireframe: true,
        });
        const beacon = new THREE.Mesh(beaconGeo, beaconMat);
        beacon.position.y = 1.0;
        group.add(beacon);
      }

      scene.add(group);
      nodeGroups.set(meta.id, group);
    });

    // ==============================================================================
    // 8. SYNAPTIC SPLINES & ENERGETIC FLOW PARTICLES
    // ==============================================================================
    const splineCurves: THREE.CatmullRomCurve3[] = [];
    const nucleusPos = new THREE.Vector3(0, 0, 0);

    // Build splines from nucleus to Quorum Nodes and Subsystem Organs
    Object.values(TOPOLOGICAL_NODES).forEach((meta) => {
      if (meta.id === 'SOVEREIGN_NUCLEUS') return;

      const targetPos = new THREE.Vector3(...meta.position);
      const midPos = new THREE.Vector3()
        .addVectors(nucleusPos, targetPos)
        .multiplyScalar(0.5)
        .add(new THREE.Vector3(0, (Math.random() - 0.5) * 1.5, 0));

      const curve = new THREE.CatmullRomCurve3([nucleusPos, midPos, targetPos]);
      splineCurves.push(curve);

      // Visual line curve
      const points = curve.getPoints(36);
      const curveGeo = new THREE.BufferGeometry().setFromPoints(points);
      const curveMat = new THREE.LineBasicMaterial({
        color: new THREE.Color(meta.color),
        transparent: true,
        opacity: 0.35,
      });
      const line = new THREE.Line(curveGeo, curveMat);
      scene.add(line);
    });

    // In-flight animated packet meshes along splines
    const packetMeshes: THREE.Mesh[] = [];
    const packetGeo = new THREE.SphereGeometry(0.12, 12, 12);
    const packetMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      blending: THREE.AdditiveBlending,
    });

    for (let i = 0; i < 18; i++) {
      const pMesh = new THREE.Mesh(packetGeo, packetMat.clone());
      (pMesh as unknown as { curveIndex: number; progress: number; speed: number }).curveIndex = i % splineCurves.length;
      (pMesh as unknown as { progress: number }).progress = Math.random();
      (pMesh as unknown as { speed: number }).speed = 0.003 + Math.random() * 0.005;
      scene.add(pMesh);
      packetMeshes.push(pMesh);
    }

    // Populate Three.js State Ref
    threeStateRef.current = {
      renderer,
      scene,
      camera,
      controls,
      nodeGroups,
      splineCurves,
      packetMeshes,
      stardustParticles: stardust,
      concentricRings: [ring1, ring2],
      cameraTargetPos: camera.position.clone(),
      controlsTargetPos: controls.target.clone(),
      isTransitioningCamera: false,
      raycaster: new THREE.Raycaster(),
      mouse: new THREE.Vector2(-999, -999),
    };

    // ==============================================================================
    // 9. ANIMATION LOOP & SOFTWARE WEBGL PACING (Directives §2 & §4)
    // ==============================================================================
    let frameId = 0;
    const clock = new THREE.Clock();

    function afterDraw(cb: () => void) {
      const gl = renderer.getContext() as WebGL2RenderingContext;
      const sync = gl.fenceSync?.(gl.SYNC_GPU_COMMANDS_COMPLETE, 0);
      gl.flush();
      const poll = () => {
        const state = sync && gl.getSyncParameter(sync, gl.SYNC_STATUS);
        if (state === gl.UNSIGNALED) {
          frameId = window.setTimeout(poll, 5);
        } else {
          if (sync) gl.deleteSync(sync);
          frameId = window.setTimeout(cb, 80);
        }
      };
      frameId = window.setTimeout(poll, 5);
    }

    function tick() {
      const delta = clock.getDelta();
      const elapsedTime = clock.getElapsedTime();

      // 1. Hypnotic Celestial Rotation
      if (stardust) stardust.rotation.y = elapsedTime * 0.015;
      if (ring1) ring1.rotation.z = -elapsedTime * 0.04;
      if (ring2) ring2.rotation.z = elapsedTime * 0.025;

      // 2. Node Group Kinematic Breathing & Rotation
      nodeGroups.forEach((group, id) => {
        const meta = TOPOLOGICAL_NODES[id];
        if (!meta) return;

        // Apply exploded layer separation dynamically
        const currentSep = explodedSeparationRef.current;
        group.position.y = meta.position[1] * currentSep;
        group.position.x = meta.position[0] * (1.0 + (currentSep - 1.0) * 0.35);
        group.position.z = meta.position[2] * (1.0 + (currentSep - 1.0) * 0.35);

        // Breathing & Rotation
        if (id === 'SOVEREIGN_NUCLEUS') {
          group.rotation.y = elapsedTime * 0.3;
          group.rotation.x = Math.sin(elapsedTime * 0.4) * 0.15;
          const scale = 1.0 + Math.sin(elapsedTime * 2.5) * 0.04;
          group.scale.set(scale, scale, scale);
        } else {
          group.rotation.y += delta * 0.5;
          const floatOffset = Math.sin(elapsedTime * 2.0 + meta.position[0]) * 0.08;
          group.position.y += floatOffset;
        }
      });

      // 3. Move Energy Packet Meshes Along Splines
      packetMeshes.forEach((mesh) => {
        const pData = mesh as unknown as { curveIndex: number; progress: number; speed: number };
        pData.progress += pData.speed;
        if (pData.progress >= 1.0) {
          pData.progress = 0;
          pData.curveIndex = (pData.curveIndex + 1) % splineCurves.length;
        }
        const curve = splineCurves[pData.curveIndex];
        if (curve) {
          curve.getPointAt(pData.progress, mesh.position);
        }
      });

      // 4. Smooth Camera Spring Damping
      const state = threeStateRef.current;
      if (state.isTransitioningCamera) {
        camera.position.lerp(state.cameraTargetPos, 0.06);
        controls.target.lerp(state.controlsTargetPos, 0.06);

        if (camera.position.distanceTo(state.cameraTargetPos) < 0.08) {
          state.isTransitioningCamera = false;
        }
      }

      // 5. Zen Hypnotic Drift (Auto-Rotation when idle)
      if (zenDriftRef.current && !state.isTransitioningCamera) {
        controls.autoRotate = true;
        controls.autoRotateSpeed = 0.4;
      } else {
        controls.autoRotate = false;
      }

      controls.update();
      renderer.render(scene, camera);

      if (isSoftwareGl) afterDraw(tick);
      else frameId = requestAnimationFrame(tick);
    }

    // Launch render loop
    tick();

    // Resize Handler
    const handleResize = () => {
      if (!mount) return;
      const w = mount.clientWidth;
      const h = mount.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener('resize', handleResize);

    // Raycasting Pointer Handler
    const handlePointerMove = (e: MouseEvent) => {
      const rect = mount.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      threeStateRef.current.mouse.set(x, y);

      threeStateRef.current.raycaster.setFromCamera(threeStateRef.current.mouse, camera);
      const intersects = threeStateRef.current.raycaster.intersectObjects(scene.children, true);

      if (intersects.length > 0) {
        let parent = intersects[0].object.parent;
        while (parent && !parent.name && parent !== scene) {
          parent = parent.parent;
        }
        if (parent && parent.name && parent.name in TOPOLOGICAL_NODES) {
          setHoveredSubsystem(parent.name as EstateSubsystemId);
          mount.style.cursor = 'pointer';
          return;
        }
      }
      setHoveredSubsystem(null);
      mount.style.cursor = 'default';
    };

    const handleClick = () => {
      const currentTarget = hoveredSubsystemRef.current;
      if (currentTarget) {
        handleFocusNodeRef.current(currentTarget);
      }
    };

    mount.addEventListener('mousemove', handlePointerMove);
    mount.addEventListener('click', handleClick);

    // Cleanup on unmount
    return () => {
      cancelAnimationFrame(frameId);
      clearTimeout(frameId);
      window.removeEventListener('resize', handleResize);
      mount.removeEventListener('mousemove', handlePointerMove);
      mount.removeEventListener('click', handleClick);

      if (renderer) {
        renderer.dispose();
        if (renderer.domElement && renderer.domElement.parentNode) {
          renderer.domElement.parentNode.removeChild(renderer.domElement);
        }
      }
      stardustGeo.dispose();
      stardustMat.dispose();
      ringGeo1.dispose();
      ringMat1.dispose();
      ringGeo2.dispose();
      ringMat2.dispose();
      particleTex.dispose();
      runicTex.dispose();
    };
  }, []);

  const activeMeta = TOPOLOGICAL_NODES[selectedSubsystem] || TOPOLOGICAL_NODES.SOVEREIGN_NUCLEUS;

  return (
    <div className="relative w-full h-[88vh] min-h-[640px] max-h-[960px] bg-slate-950 rounded-2xl border border-cyan-800/60 overflow-hidden shadow-2xl flex flex-col select-none">
      
      {/* 3D WebGL Canvas Viewport OR 2D Sovereign Vector Fallback */}
      {isWebGlFallback ? (
        <Alien2DTopologicalCanvas
          selectedSubsystem={selectedSubsystem}
          onSelectSubsystem={handleFocusNode}
          hoveredSubsystem={hoveredSubsystem}
          setHoveredSubsystem={setHoveredSubsystem}
          explodedSeparation={explodedLayerSeparation}
          zenDriftEnabled={zenDriftEnabled}
          onPlayChime={(freq) => audioSynthRef.current?.playNodeChime(freq)}
        />
      ) : (
        <div ref={canvasMountRef} className="absolute inset-0 z-0 w-full h-full cursor-grab active:cursor-grabbing" />
      )}

      {/* ==================================================================== */}
      {/* MINIMAL TOP-LEFT SPEC BADGE & TELEMETRY HUD (Directive §5: No Side Clutter) */}
      {/* ==================================================================== */}
      <div className="absolute top-4 left-4 z-20 pointer-events-none flex flex-col gap-2">
        <div className="bg-slate-950/85 backdrop-blur-md border border-cyan-800/80 rounded-xl px-4 py-2.5 shadow-xl flex items-center gap-3">
          <div className="w-3 h-3 rounded-full bg-cyan-400 shadow-md shadow-cyan-400/50" />
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono font-bold text-white text-xs tracking-wider">
                {isWebGlFallback ? '2100 ALIEN TOPOLOGY · 2D VECTOR' : '2100 ALIEN TOPOLOGICAL VIEW'}
              </span>
              <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                isWebGlFallback 
                  ? 'text-amber-300 bg-amber-950/70 border-amber-700/60'
                  : 'text-cyan-300 bg-cyan-950/70 border-cyan-700/60'
              }`}>
                {isWebGlFallback ? 'SOVEREIGN 2D FALLBACK' : 'ERA_1 · REAL-TIME 3D'}
              </span>
            </div>
            <div className="text-[11px] font-mono text-slate-400 mt-0.5">
              Target: <span className="text-cyan-300 font-semibold">{activeMeta.name}</span>
            </div>
          </div>
        </div>

        {/* Quick Node Indicator Bar */}
        <div className="bg-slate-950/80 backdrop-blur-sm border border-slate-800/80 rounded-lg px-3 py-1.5 text-[10px] font-mono text-slate-400 flex items-center gap-3">
          <span>Raft Quorum: <span className="text-emerald-400 font-bold">HEALTHY</span></span>
          <span>·</span>
          <span>Flow Rate: <span className="text-cyan-300 font-bold">{vitals.estateTimeInFlowPercent}%</span></span>
          <span>·</span>
          <span>Founder Friction: <span className="text-emerald-400 font-bold">Δ ≡ 0</span></span>
        </div>
      </div>

      {/* ==================================================================== */}
      {/* TOP-RIGHT CONTROLS & CINEMA TOGGLE */}
      {/* ==================================================================== */}
      <div className="absolute top-4 right-4 z-20 flex items-center gap-2">
        {/* Audio Mute / Unmute */}
        <button
          onClick={() => {
            const next = !isAudioMuted;
            setIsAudioMuted(next);
            if (!next) audioSynthRef.current?.playNodeChime(520);
          }}
          className={`p-2.5 rounded-xl border backdrop-blur-md transition-all cursor-pointer ${
            !isAudioMuted
              ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 shadow-lg shadow-cyan-500/20'
              : 'bg-slate-950/80 border-slate-800 text-slate-400 hover:text-white'
          }`}
          title={isAudioMuted ? 'Enable 432Hz Ambient Resonance' : 'Mute Ambient Resonance'}
        >
          {!isAudioMuted ? <Volume2 className="w-4 h-4 text-cyan-400" /> : <VolumeX className="w-4 h-4 text-slate-500" />}
        </button>

        {/* Zen Drift Auto-Rotation */}
        <button
          onClick={() => setZenDriftEnabled(!zenDriftEnabled)}
          className={`p-2.5 rounded-xl border backdrop-blur-md transition-all cursor-pointer ${
            zenDriftEnabled
              ? 'bg-slate-900/90 border-cyan-400/80 text-cyan-300'
              : 'bg-slate-950/80 border-slate-800 text-slate-400 hover:text-white'
          }`}
          title="Toggle Zen Hypnotic Orbit Drift"
        >
          <Compass className="w-4 h-4" />
        </button>

        {/* Cinema / Zen Mode Toggle */}
        <button
          onClick={() => setIsCinemaMode(!isCinemaMode)}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-950/85 backdrop-blur-md border border-slate-800 text-xs font-mono text-slate-300 hover:text-cyan-300 transition-colors shadow-lg cursor-pointer"
        >
          {isCinemaMode ? (
            <>
              <Minimize2 className="w-3.5 h-3.5" />
              <span>Show Dock</span>
            </>
          ) : (
            <>
              <Maximize2 className="w-3.5 h-3.5" />
              <span>Cinema Mode</span>
            </>
          )}
        </button>
      </div>

      {/* ==================================================================== */}
      {/* 3D HOVER RETICLE OVERLAY (When Hovering Nodes) */}
      {/* ==================================================================== */}
      {hoveredSubsystem && hoveredSubsystem !== selectedSubsystem && (
        <div className="absolute top-20 left-1/2 -translate-x-1/2 z-20 pointer-events-none bg-slate-950/90 backdrop-blur-md border border-cyan-500/80 px-4 py-2 rounded-xl shadow-2xl text-center">
          <span className="text-[10px] font-mono uppercase tracking-widest text-cyan-400 block">
            Targeting Node: Click to Focus
          </span>
          <span className="text-xs font-bold text-white font-mono">
            {TOPOLOGICAL_NODES[hoveredSubsystem].name}
          </span>
        </div>
      )}

      {/* ==================================================================== */}
      {/* UNIFIED COLLAPSIBLE BOTTOM DOCK (Three.js Directive §5: Ergonomic Dock) */}
      {/* ==================================================================== */}
      <div
        className={`absolute bottom-4 left-1/2 -translate-x-1/2 z-30 w-full max-w-4xl px-4 transition-transform duration-500 ease-out ${
          isCinemaMode ? 'translate-y-[120%]' : 'translate-y-0'
        }`}
      >
        <div className="bg-slate-950/92 backdrop-blur-xl border border-slate-800/90 rounded-2xl shadow-2xl overflow-hidden">
          
          {/* Dock Header & Navigation Tabs */}
          <div className="flex items-center justify-between border-b border-slate-800/80 px-4 py-2 text-xs font-mono">
            <div className="flex items-center gap-1">
              <button
                onClick={() => setActiveTabDock('LAYERS')}
                className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer flex items-center gap-1.5 ${
                  activeTabDock === 'LAYERS'
                    ? 'bg-slate-800 text-cyan-300 font-bold border border-cyan-800/50'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Layers className="w-3.5 h-3.5 text-cyan-400" />
                <span>Subsystems & Organs</span>
              </button>

              <button
                onClick={() => setActiveTabDock('OPERATIONS')}
                className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer flex items-center gap-1.5 ${
                  activeTabDock === 'OPERATIONS'
                    ? 'bg-slate-800 text-cyan-300 font-bold border border-cyan-800/50'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                <span>Live IPN Packets</span>
              </button>

              <button
                onClick={() => setActiveTabDock('CONSENSUS')}
                className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer flex items-center gap-1.5 ${
                  activeTabDock === 'CONSENSUS'
                    ? 'bg-slate-800 text-cyan-300 font-bold border border-cyan-800/50'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Radio className="w-3.5 h-3.5 text-emerald-400" />
                <span>Raft Quorum Matrix</span>
              </button>

              <button
                onClick={() => setActiveTabDock('CONTROLS')}
                className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer flex items-center gap-1.5 ${
                  activeTabDock === 'CONTROLS'
                    ? 'bg-slate-800 text-cyan-300 font-bold border border-cyan-800/50'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                <span>Camera & Exploded View</span>
              </button>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleDispatchProbePacket}
                className="px-2.5 py-1 bg-cyan-950/80 border border-cyan-700/80 text-cyan-300 rounded-md hover:bg-cyan-900 transition-colors flex items-center gap-1 text-[11px] font-bold cursor-pointer"
              >
                <Play className="w-3 h-3 text-cyan-400" />
                <span>Dispatch Probe</span>
              </button>

              <button
                onClick={() => setIsCinemaMode(true)}
                className="p-1 rounded text-slate-400 hover:text-white cursor-pointer"
                title="Collapse Dock (H)"
              >
                <ChevronDown className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Dock Content Body */}
          <div className="p-4 max-h-56 overflow-y-auto">
            {/* TAB 1: SUBSYSTEMS & ORGANS EXPLORER */}
            {activeTabDock === 'LAYERS' && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
                  {Object.values(TOPOLOGICAL_NODES).map((node) => {
                    const isSelected = selectedSubsystem === node.id;
                    return (
                      <button
                        key={node.id}
                        onClick={() => handleFocusNode(node.id)}
                        className={`p-2 rounded-xl border text-left text-[11px] font-mono transition-all cursor-pointer flex flex-col justify-between ${
                          isSelected
                            ? 'bg-slate-800/90 border-cyan-400 text-cyan-300 shadow-md'
                            : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                        }`}
                      >
                        <div className="flex items-center gap-1.5 truncate">
                          <span
                            className="w-2 h-2 rounded-full shrink-0"
                            style={{ backgroundColor: node.color }}
                          />
                          <span className="font-bold text-white truncate">{node.name.split(' ')[0]}</span>
                        </div>
                        <span className="text-[10px] text-slate-500 mt-1">{node.flowState}% Flow</span>
                      </button>
                    );
                  })}
                </div>

                {/* Selected Subsystem Deep Telemetry Card */}
                <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3 text-xs font-mono flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-white font-bold">{activeMeta.name}</span>
                      <span className="text-[10px] text-cyan-300 bg-cyan-950/60 px-1.5 py-0.5 rounded border border-cyan-800">
                        {activeMeta.category}
                      </span>
                    </div>
                    <p className="text-slate-400 text-[11px]">{activeMeta.tagline}</p>
                    <div className="text-[10px] text-slate-500">{activeMeta.spec}</div>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 w-full sm:w-auto shrink-0">
                    {activeMeta.metrics.map((m, idx) => (
                      <div key={idx} className="bg-slate-950 p-2 rounded-lg border border-slate-800/80 text-center">
                        <span className="text-slate-500 block text-[9px] uppercase">{m.label}</span>
                        <span className="text-cyan-300 font-bold text-[11px] tabular-nums">{m.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* TAB 2: LIVE IPN PACKETS */}
            {activeTabDock === 'OPERATIONS' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs font-mono text-slate-400">
                  <span>In-Flight Instruction Packets ({packets.length} active)</span>
                  <span className="text-emerald-400 font-bold">Flow Status: 100% Invariant Compliant</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  {packets.slice(0, 3).map((p) => (
                    <div
                      key={p.packetId}
                      onClick={() => onSelectPacket?.(p.packetId)}
                      className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl text-xs font-mono hover:border-cyan-500 transition-colors cursor-pointer space-y-1"
                    >
                      <div className="flex justify-between items-center text-[11px]">
                        <span className="text-cyan-400 font-bold">{p.packetId}</span>
                        <span className="text-emerald-400 font-semibold">{p.currentStage}</span>
                      </div>
                      <div className="text-[11px] text-slate-300 truncate">{p.instructionText}</div>
                      <div className="text-[10px] text-slate-500 flex justify-between pt-1">
                        <span>Alignment: {(p.oracleAlignmentScore * 100).toFixed(0)}%</span>
                        <span>Target: {p.targetLane.replace('LANE_', '')}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TAB 3: RAFT QUORUM MATRIX */}
            {activeTabDock === 'CONSENSUS' && (
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs font-mono">
                {lanes.map((lane) => (
                  <div
                    key={lane.id}
                    onClick={() => handleFocusNode(lane.id as EstateSubsystemId)}
                    className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl hover:border-cyan-400 transition-all cursor-pointer space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-white truncate">{lane.name}</span>
                      <span className="text-[9px] text-emerald-400 font-bold bg-emerald-950 px-1 rounded border border-emerald-800">
                        {lane.status}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-500">{lane.ip}</div>
                    <div className="flex justify-between text-[11px] text-cyan-300 pt-1">
                      <span>Latency: {lane.latencyMs}ms</span>
                      <span>Flow: {lane.flowStateScore}%</span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* TAB 4: CAMERA PRESETS & EXPLODED VIEW */}
            {activeTabDock === 'CONTROLS' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
                <div className="space-y-2">
                  <span className="text-slate-400 block text-[11px] uppercase">Camera Teleport Presets</span>
                  <div className="grid grid-cols-3 sm:grid-cols-5 gap-1.5">
                    {(['PANORAMA', 'NUCLEUS', 'QUORUM', 'ORGANS', 'TACTICAL'] as const).map((preset) => (
                      <button
                        key={preset}
                        onClick={() => setCameraView(preset)}
                        className="px-2 py-1.5 bg-slate-900 border border-slate-800 rounded-lg hover:border-cyan-400 text-slate-300 hover:text-white transition-all text-center text-[10px] cursor-pointer"
                      >
                        {preset}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-[11px]">
                    <span className="text-slate-400 uppercase">Exploded Layer Separation</span>
                    <span className="text-cyan-300 font-bold">{explodedLayerSeparation.toFixed(2)}x</span>
                  </div>
                  <input
                    type="range"
                    min="1.0"
                    max="2.5"
                    step="0.05"
                    value={explodedLayerSeparation}
                    onChange={(e) => setExplodedLayerSeparation(parseFloat(e.target.value))}
                    className="w-full accent-cyan-400 cursor-pointer"
                  />
                  <div className="flex justify-between text-[9px] text-slate-500">
                    <span>Collapsed (1.0x)</span>
                    <span>Exploded Subsystems (2.5x)</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

    </div>
  );
};
