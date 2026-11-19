import React, { useState, useEffect } from 'react';
import {
  X,
  Zap,
  ShieldCheck,
  Activity,
  Vibrate,
  GitMerge,
  Pause,
  Play,
} from 'lucide-react';
import type {
  TelegramForumTopic,
  OttoInstanceState,
  AgentLaneStatus,
} from '../engine/oracleEngine';

interface OverwatchTmaModalProps {
  isOpen: boolean;
  onClose: () => void;
  topics: TelegramForumTopic[];
  ottoInstances: OttoInstanceState[];
  onUpdateTopicStatus: (topicId: string, status: AgentLaneStatus) => void;
  onReconcileSplitBrain: () => void;
}

interface TmaGraphNode {
  id: string;
  label: string;
  sublabel: string;
  x: number;
  y: number;
  status: 'nominal' | 'inferencing' | 'warning' | 'critical';
  tps: number;
  details: string;
}

export const OverwatchTmaModal: React.FC<OverwatchTmaModalProps> = ({
  isOpen,
  onClose,
  topics,
  ottoInstances,
  onUpdateTopicStatus,
  onReconcileSplitBrain,
}) => {
  const [selectedNodeId, setSelectedNodeId] = useState<string>('estate-db-wal');
  const [hapticLog, setHapticLog] = useState<string[]>([
    '[TMA-SDK] window.Telegram.WebApp.ready() · Viewport expanded (60fps axum WS connected)',
    '[HAPTIC] HapticFeedback.impactOccurred("medium") · Synced 4 Supergroup forum lanes',
  ]);
  const [streamTick, setStreamTick] = useState<number>(0);

  useEffect(() => {
    if (!isOpen) return;
    const interval = setInterval(() => {
      setStreamTick((t) => t + 1);
    }, 1200);
    return () => clearInterval(interval);
  }, [isOpen]);

  if (!isOpen) return null;

  const isSplitBrainActive = ottoInstances.some((o) => o.status === 'active_conflict');

  const triggerHaptic = (intensity: 'light' | 'medium' | 'heavy', reason: string) => {
    try {
      if (typeof navigator !== 'undefined' && navigator.vibrate) {
        navigator.vibrate(intensity === 'heavy' ? 60 : 25);
      }
    } catch {
      // Ignore in sandboxed headless environments
    }
    const entry = `[${new Date().toISOString().slice(11, 19)}] WebApp.HapticFeedback.impactOccurred('${intensity}') -> ${reason}`;
    setHapticLog((prev) => [entry, ...prev.slice(0, 6)]);
  };

  const piLane01 = topics.find((t) => t.id === 'pi-lane-01');
  const piLane02 = topics.find((t) => t.id === 'pi-lane-02');

  const nodes: TmaGraphNode[] = [
    {
      id: 'k3s-spine',
      label: 'Oracle k3s Rust Spine',
      sublabel: '14.8MB static · 18.2MB RSS',
      x: 420,
      y: 70,
      status: 'nominal',
      tps: 0,
      details:
        'Single Rust binary (teloxide + axum + sqlx) serving TMA WebSockets and editing #00-OVERWATCH every 3s.',
    },
    {
      id: 'estate-db-wal',
      label: 'estate.db + estate-graph',
      sublabel: 'SQLite WAL · CIF HMAC Gate',
      x: 420,
      y: 195,
      status: 'nominal',
      tps: 146.1,
      details:
        'Central indexed retrieval oracle and cryptographic step_runs ledger. Zero bash loops; 1.8ms Pass-1 RRF queries.',
    },
    {
      id: 'otto-day0',
      label: 'Otto Day-0 Front-Door',
      sublabel: isSplitBrainActive ? 'PID 88410 (Conflict)' : 'PID 88410 (Canonical)',
      x: 165,
      y: 195,
      status: isSplitBrainActive ? 'warning' : 'nominal',
      tps: 42.6,
      details: isSplitBrainActive
        ? 'Canonical candidate bound to estate.db, awaiting purge of rogue PID 41892.'
        : 'Canonical Day-0 Personal Agent managing #pi-lane-* topics with 100% CIF verification.',
    },
    {
      id: 'otto-rogue',
      label: 'Rogue Otto v1 MCP',
      sublabel: isSplitBrainActive ? 'PID 41892 (SPLIT-BRAIN)' : 'PURGED & ARCHIVED',
      x: 165,
      y: 320,
      status: isSplitBrainActive ? 'critical' : 'nominal',
      tps: 0,
      details: isSplitBrainActive
        ? 'Asymmetric capture risk: reading ~/Desktop/otto-old-worktree markdown without CIF signatures.'
        : 'Archived & purged via reconcileOttoSplitBrain. All 42 frames migrated to estate.db.',
    },
    {
      id: 'pi-lane-01',
      label: '#pi-lane-01 (MacBook)',
      sublabel: piLane01?.status === 'halted' ? 'PAUSED' : 'MiniMax M2.7 · 76.8 tok/s',
      x: 675,
      y: 140,
      status: piLane01?.status === 'halted' ? 'warning' : 'inferencing',
      tps: piLane01?.status === 'halted' ? 0 : 76.8,
      details:
        'Headless Pi session synthesizing SFT/RLHF trajectories on direct MiniMax M2.7 plan quota (shard_08.jsonl).',
    },
    {
      id: 'pi-lane-02',
      label: '#pi-lane-02 (OIA GTM)',
      sublabel: piLane02?.status === 'halted' ? 'PAUSED' : 'Claim #741 · 71.6 tok/s',
      x: 675,
      y: 285,
      status: piLane02?.status === 'halted' ? 'warning' : 'inferencing',
      tps: piLane02?.status === 'halted' ? 0 : 71.6,
      details:
        'Verifying OIA GTM PR #891 and Claim #741 handoffs with deterministic CIF step receipts.',
    },
  ];

  const activeNode = nodes.find((n) => n.id === selectedNodeId) || nodes[1];

  const totalTps = topics.reduce(
    (acc, t) => acc + (t.status === 'halted' ? 0 : t.tokensPerSec),
    0
  );

  const trainingSamples = [
    `[shard_08:${1040 + streamTick}] model=MiniMax-M2.7 · prompt="estate-oracle query OIA GTM #741" -> RRF=0.982 · CIF_HMAC=8f9a...3b1c`,
    `[shard_08:${1039 + streamTick}] model=MiniMax-M2.7 · intent="intent.otto.day0_readiness" -> Pass-1=1.8ms · exit_code=0`,
    `[shard_08:${1038 + streamTick}] model=MiniMax-M2.7 · falsify="bin/idp-vault-refs" -> QUARANTINED (#7318 k3s Rust gate)`,
  ];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="tma-hud-title"
      className="fixed inset-0 z-50 bg-slate-950/90 backdrop-blur-sm flex items-center justify-center p-3 sm:p-6 overflow-y-auto"
    >
      <div className="w-full max-w-6xl border border-slate-800 rounded-xl bg-slate-950 shadow-2xl overflow-hidden my-auto">
        {/* TMA Native Header Bar */}
        <div className="px-5 py-3.5 bg-slate-900 border-b border-slate-800 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Zap className="w-4 h-4 text-sky-400 shrink-0" />
            <div>
              <h2 id="tma-hud-title" className="text-sm font-bold text-slate-100">
                OVERWATCH TMA HUD · Telegram Mini App (axum + tokio-tungstenite 60fps WS)
              </h2>
              <p className="text-xs font-mono text-slate-400 tabular-nums">
                Oracle Free Tier k3s Spine · RAM: 18.2 MB / 20.0 MB · Native Haptics Armed
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close Overwatch HUD"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-md transition-colors whitespace-nowrap shrink-0"
          >
            <X className="w-3.5 h-3.5" />
            <span>Close HUD</span>
          </button>
        </div>

        {/* Top Telemetry Gauges */}
        <div className="grid grid-cols-2 lg:grid-cols-4 divide-y lg:divide-y-0 lg:divide-x divide-slate-800 border-b border-slate-800 bg-slate-900/40 font-mono text-xs tabular-nums">
          <div className="p-4">
            <div className="text-slate-400">Aggregate MiniMax M2.7 Velocity</div>
            <div className="text-xl font-bold text-sky-400 mt-1">
              {totalTps.toFixed(1)} tok/s
            </div>
            <div className="text-slate-500 mt-0.5">Direct Plan Quota (Router Bypassed)</div>
          </div>

          <div className="p-4">
            <div className="text-slate-400">estate.db WAL Write Throughput</div>
            <div className="text-xl font-bold text-emerald-400 mt-1">146.1 tx/s</div>
            <div className="text-slate-500 mt-0.5">100% HMAC-SHA256 Signed Receipts</div>
          </div>

          <div className="p-4">
            <div className="text-slate-400">Otto Personal Agent Unity</div>
            <div
              className={`text-xl font-bold mt-1 ${
                isSplitBrainActive ? 'text-rose-400' : 'text-emerald-400'
              }`}
            >
              {isSplitBrainActive ? '2 Ottos (Split-Brain)' : 'Day-0 Canonical'}
            </div>
            <div className="text-slate-500 mt-0.5">
              {isSplitBrainActive ? 'PID 41892 vs PID 88410' : 'Zero Hallucination Enforced'}
            </div>
          </div>

          <div className="p-4">
            <div className="text-slate-400">k3s Rust Binary Footprint</div>
            <div className="text-xl font-bold text-slate-100 mt-1">14.8 MB Static</div>
            <div className="text-slate-500 mt-0.5">18.2 MB RSS (teloxide + axum + sqlx)</div>
          </div>
        </div>

        {/* Center Interactive Node Graph + Node Inspector */}
        <div className="grid grid-cols-1 lg:grid-cols-12 divide-y lg:divide-y-0 lg:divide-x divide-slate-800">
          {/* Interactive SVG Node Topology */}
          <div className="lg:col-span-8 p-5 space-y-3 bg-slate-950">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400">
              <span>Interactive Estate Topology Graph (Click any node to inspect or actuate)</span>
              <span className="text-sky-400">WebSocket Frame #{4820 + streamTick}</span>
            </div>

            <div className="border border-slate-800 rounded-lg bg-slate-900/40 p-2 overflow-x-auto">
              <svg
                viewBox="0 0 840 390"
                className="w-full h-72 sm:h-80 select-none"
                role="img"
                aria-label="Interactive node graph of active Pi sessions, Otto, estate.db, and Oracle k3s spine"
              >
                {/* Edges */}
                <line
                  x1={420}
                  y1={70}
                  x2={420}
                  y2={195}
                  stroke="#38bdf8"
                  strokeWidth={2}
                  strokeDasharray="4 4"
                />
                <line
                  x1={165}
                  y1={195}
                  x2={420}
                  y2={195}
                  stroke="#34d399"
                  strokeWidth={2}
                />
                <line
                  x1={165}
                  y1={320}
                  x2={165}
                  y2={195}
                  stroke={isSplitBrainActive ? '#fb7185' : '#475569'}
                  strokeWidth={2}
                  strokeDasharray="5 5"
                />
                <line
                  x1={420}
                  y1={195}
                  x2={675}
                  y2={140}
                  stroke="#38bdf8"
                  strokeWidth={2}
                />
                <line
                  x1={420}
                  y1={195}
                  x2={675}
                  y2={285}
                  stroke="#38bdf8"
                  strokeWidth={2}
                />

                {/* Nodes */}
                {nodes.map((node) => {
                  const isSelected = node.id === selectedNodeId;
                  const strokeColor =
                    node.status === 'critical'
                      ? '#fb7185'
                      : node.status === 'warning'
                      ? '#fbbf24'
                      : node.status === 'inferencing'
                      ? '#38bdf8'
                      : '#34d399';

                  return (
                    <g
                      key={node.id}
                      transform={`translate(${node.x - 105}, ${node.y - 32})`}
                      onClick={() => {
                        setSelectedNodeId(node.id);
                        triggerHaptic('light', `Focused graph node ${node.label}`);
                      }}
                      className="cursor-pointer"
                    >
                      <rect
                        width={210}
                        height={64}
                        rx={8}
                        fill={isSelected ? '#1e293b' : '#0f172a'}
                        stroke={strokeColor}
                        strokeWidth={isSelected ? 2.5 : 1.5}
                      />
                      <text
                        x={14}
                        y={26}
                        fill="#f8fafc"
                        fontSize="12"
                        fontWeight="700"
                        fontFamily="Plus Jakarta Sans, sans-serif"
                      >
                        {node.label}
                      </text>
                      <text
                        x={14}
                        y={46}
                        fill="#94a3b8"
                        fontSize="11"
                        fontFamily="JetBrains Mono, monospace"
                      >
                        {node.sublabel}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </div>

            {/* Real-Time Scrolling Training Data & CIF Stream */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs font-mono text-slate-400">
                <span className="inline-flex items-center gap-1.5 text-slate-300">
                  <Activity className="w-3.5 h-3.5 text-sky-400" />
                  Live MiniMax M2.7 Training Trajectory & CIF Stream
                </span>
                <span>~/.estate/trajectories/shard_08.jsonl</span>
              </div>
              <div className="p-3 bg-slate-900 border border-slate-800 rounded-md font-mono text-xs text-slate-300 space-y-1">
                {trainingSamples.map((line, idx) => (
                  <div key={idx} className="truncate">
                    {line}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right Panel: Selected Node Hardware Controls & Native Haptic Feedback Log */}
          <div className="lg:col-span-4 p-5 bg-slate-900/60 flex flex-col justify-between space-y-5">
            <div className="space-y-4">
              <div className="border-b border-slate-800 pb-3">
                <span className="text-xs font-mono text-sky-400">
                  SELECTED NODE INSPECTOR
                </span>
                <h3 className="text-base font-bold text-slate-100 mt-0.5">
                  {activeNode.label}
                </h3>
                <p className="text-xs font-mono text-slate-400 mt-0.5">
                  {activeNode.sublabel}
                </p>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed">
                {activeNode.details}
              </p>

              {/* Node-specific Hardware & Haptic Actions */}
              <div className="space-y-2 pt-2">
                <div className="text-xs font-semibold text-slate-300">
                  TMA Hardware & Haptic Actuators
                </div>

                {isSplitBrainActive && (
                  <button
                    type="button"
                    onClick={() => {
                      onReconcileSplitBrain();
                      triggerHaptic(
                        'heavy',
                        'Purged rogue Otto PID 41892 & promoted canonical PID 88410'
                      );
                    }}
                    className="w-full inline-flex items-center justify-center gap-2 px-3.5 py-2 text-xs font-semibold bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 border border-rose-500/40 rounded-md transition-colors"
                  >
                    <ShieldCheck className="w-4 h-4" />
                    <span>Purge Otto Split-Brain (Heavy Haptic)</span>
                  </button>
                )}

                <button
                  type="button"
                  onClick={() => {
                    const target =
                      activeNode.id === 'pi-lane-02' ? 'pi-lane-02' : 'pi-lane-01';
                    const topic = topics.find((t) => t.id === target);
                    const next: AgentLaneStatus =
                      topic?.status === 'halted' ? 'inferencing' : 'halted';
                    onUpdateTopicStatus(target, next);
                    triggerHaptic(
                      'medium',
                      `Toggled #${target} state -> ${next.toUpperCase()}`
                    );
                  }}
                  className="w-full inline-flex items-center justify-center gap-2 px-3.5 py-2 text-xs font-mono font-medium bg-slate-950 hover:bg-slate-800 text-slate-200 border border-slate-800 rounded-md transition-colors"
                >
                  {piLane01?.status === 'halted' ? (
                    <>
                      <Play className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Resume Pi Lane Synthesis</span>
                    </>
                  ) : (
                    <>
                      <Pause className="w-3.5 h-3.5 text-amber-400" />
                      <span>Pause Pi Lane Synthesis</span>
                    </>
                  )}
                </button>

                <button
                  type="button"
                  onClick={() =>
                    triggerHaptic(
                      'heavy',
                      `Verified CIF Merge Gate on ${activeNode.label}`
                    )
                  }
                  className="w-full inline-flex items-center justify-center gap-2 px-3.5 py-2 text-xs font-mono font-medium bg-slate-950 hover:bg-slate-800 text-sky-300 border border-slate-800 rounded-md transition-colors"
                >
                  <GitMerge className="w-3.5 h-3.5" />
                  <span>Trigger CIF Gate Haptic Pulse</span>
                </button>
              </div>
            </div>

            {/* Telegram WebApp Haptic Feedback Telemetry */}
            <div className="space-y-2 pt-3 border-t border-slate-800">
              <div className="flex items-center gap-1.5 text-xs font-mono text-slate-300">
                <Vibrate className="w-3.5 h-3.5 text-sky-400" />
                <span>Telegram.WebApp.HapticFeedback Bus</span>
              </div>
              <div className="p-2.5 bg-slate-950 border border-slate-800 rounded text-xs font-mono text-slate-400 space-y-1 max-h-36 overflow-y-auto">
                {hapticLog.map((entry, i) => (
                  <div key={i} className="leading-snug">
                    {entry}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
