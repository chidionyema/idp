import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Compass,
  Download,
  GitCommitHorizontal,
  History,
  Lock,
  Maximize2,
  Radio,
  Search,
  ShieldCheck,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';
import { EstateSyncMonitor } from './EstateSyncMonitor';
import { I8095LockdownPanel } from './I8095LockdownPanel';
import type {
  HistoricalIncidentReplay,
  MeridianSymphonySnapshot,
  SymphonyEdge,
  SymphonyEpistemicStatus,
  SymphonyNode,
  SymphonyNodeLayer,
} from '../engine/meridianSymphony';
import { GatewayStateSnapshot } from '../types/api';

interface MeridianSymphonyProps {
  onStateChange?: (state: GatewayStateSnapshot) => void;
}

const ZOOM_LAYERS: Array<{ layer: SymphonyNodeLayer; label: string; zoom: number }> = [
  { layer: 0, label: 'L0 · Constellation', zoom: 1 },
  { layer: 1, label: 'L1 · Subsystems', zoom: 1.18 },
  { layer: 2, label: 'L2 · Missions', zoom: 1.45 },
  { layer: 3, label: 'L3 · Atoms', zoom: 1.75 },
];

function statusColors(status: SymphonyEpistemicStatus) {
  if (status === 'LIVE_VERIFIED') {
    return {
      stroke: '#10B981',
      fill: '#0D1F1B',
      text: '#34D399',
      badge: 'text-emerald-700 border-emerald-200 bg-emerald-50',
    };
  }
  if (status === 'ARCHITECTURAL_SPEC') {
    return {
      stroke: '#38BDF8',
      fill: '#0C1A29',
      text: '#7DD3FC',
      badge: 'text-sky-700 border-sky-200 bg-sky-50',
    };
  }
  if (status === 'PARTIAL' || status === 'PENDING_INSPECTION') {
    return {
      stroke: '#F59E0B',
      fill: '#231A0B',
      text: '#FBBF24',
      badge: 'text-amber-800 border-amber-200 bg-amber-50',
    };
  }
  return {
    stroke: '#EF4444',
    fill: '#260E13',
    text: '#FCA5A5',
    badge: 'text-red-700 border-red-200 bg-red-50',
  };
}

function channelStroke(channel: SymphonyEdge['channel']) {
  if (channel === 'control') return '#38BDF8';
  if (channel === 'execution') return '#34D399';
  if (channel === 'telemetry') return '#818CF8';
  if (channel === 'evidence') return '#FBBF24';
  return '#2DD4BF';
}

function collectCausalSets(nodeId: string, edges: SymphonyEdge[]) {
  const upstream = new Set<string>();
  const downstream = new Set<string>();
  const activeEdges = new Set<string>();

  const upQueue = [nodeId];
  while (upQueue.length > 0) {
    const curr = upQueue.shift()!;
    for (const e of edges) {
      if (e.to === curr && !upstream.has(e.from) && e.from !== nodeId) {
        upstream.add(e.from);
        activeEdges.add(e.id);
        upQueue.push(e.from);
      } else if (e.to === curr && e.from === nodeId) {
        activeEdges.add(e.id);
      } else if (e.to === curr) {
        activeEdges.add(e.id);
      }
    }
  }

  const downQueue = [nodeId];
  while (downQueue.length > 0) {
    const curr = downQueue.shift()!;
    for (const e of edges) {
      if (e.from === curr && !downstream.has(e.to) && e.to !== nodeId) {
        downstream.add(e.to);
        activeEdges.add(e.id);
        downQueue.push(e.to);
      } else if (e.from === curr) {
        activeEdges.add(e.id);
      }
    }
  }

  return { upstream, downstream, activeEdges };
}

export function MeridianSymphony({ onStateChange }: MeridianSymphonyProps) {
  const [snapshot, setSnapshot] = useState<MeridianSymphonySnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<'live' | 'historical' | 'i8095' | 'sync_wake'>('live');
  const [semanticLayer, setSemanticLayer] = useState<SymphonyNodeLayer>(3);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNodeId, setSelectedNodeId] = useState<string>('estate_knowledge_graph');
  const [traceCausal, setTraceCausal] = useState(true);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string>('INC-01');
  const [runningActionId, setRunningActionId] = useState<string | null>(null);
  const [actionBanner, setActionBanner] = useState<string | null>(null);

  const draggingRef = useRef<{ active: boolean; startX: number; startY: number; origX: number; origY: number }>({
    active: false,
    startX: 0,
    startY: 0,
    origX: 0,
    origY: 0,
  });

  async function loadSymphony() {
    setLoading(true);
    try {
      const res = await fetch('/api/symphony');
      if (res.ok) {
        const data = (await res.json()) as MeridianSymphonySnapshot;
        setSnapshot(data);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadSymphony();
  }, []);

  async function handleAuthorizedAction(actionId: string) {
    setRunningActionId(actionId);
    setActionBanner(null);
    try {
      const res = await fetch('/api/symphony/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ actionId }),
      });
      if (res.ok) {
        const json = (await res.json()) as {
          actionOutcome: string;
          symphony: MeridianSymphonySnapshot;
          state: GatewayStateSnapshot;
        };
        setSnapshot(json.symphony);
        onStateChange?.(json.state);
        setActionBanner(json.actionOutcome);
      }
    } finally {
      setRunningActionId(null);
    }
  }

  function handleDownloadSpec() {
    window.location.assign('/api/symphony/spec');
  }

  const visibleNodes = useMemo(() => {
    if (!snapshot) return [];
    return snapshot.nodes.filter((n) => n.minZoomLevel <= semanticLayer);
  }, [snapshot, semanticLayer]);

  const visibleNodeIds = useMemo(() => new Set(visibleNodes.map((n) => n.id)), [visibleNodes]);

  const visibleEdges = useMemo(() => {
    if (!snapshot) return [];
    return snapshot.edges.filter(
      (e) =>
        e.minZoomLevel <= semanticLayer && visibleNodeIds.has(e.from) && visibleNodeIds.has(e.to)
    );
  }, [snapshot, semanticLayer, visibleNodeIds]);

  const activeIncident: HistoricalIncidentReplay | null = useMemo(() => {
    if (!snapshot || viewMode !== 'historical') return null;
    return snapshot.incidents.find((i) => i.id === selectedIncidentId) ?? snapshot.incidents[0] ?? null;
  }, [snapshot, viewMode, selectedIncidentId]);

  const incidentNodeIds = useMemo(() => {
    if (!activeIncident) return new Set<string>();
    return new Set(activeIncident.causalChain.map((c) => c.nodeId));
  }, [activeIncident]);

  const causalTrace = useMemo(() => {
    if (!traceCausal) {
      return { upstream: new Set<string>(), downstream: new Set<string>(), activeEdges: new Set<string>() };
    }
    return collectCausalSets(selectedNodeId, visibleEdges);
  }, [traceCausal, selectedNodeId, visibleEdges]);

  const searchMatches = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return new Set<string>();
    return new Set(
      visibleNodes
        .filter(
          (n) =>
            n.label.toLowerCase().includes(q) ||
            n.id.toLowerCase().includes(q) ||
            n.subtitle.toLowerCase().includes(q) ||
            n.owner.toLowerCase().includes(q)
        )
        .map((n) => n.id)
    );
  }, [visibleNodes, searchQuery]);

  const selectedNode: SymphonyNode | null = useMemo(() => {
    if (!snapshot) return null;
    return (
      snapshot.nodes.find((n) => n.id === selectedNodeId) ??
      snapshot.nodes.find((n) => n.id === 'estate_knowledge_graph') ??
      null
    );
  }, [snapshot, selectedNodeId]);

  if (loading && !snapshot) {
    return (
      <div className="space-y-4">
        <div className="h-28 bg-white border border-slate-200 rounded-lg animate-pulse" />
        <div className="h-[540px] bg-slate-900 border border-slate-800 rounded-lg animate-pulse" />
      </div>
    );
  }

  if (!snapshot) return null;

  const nodeMap = new Map(visibleNodes.map((n) => [n.id, n]));

  return (
    <div className="space-y-6">
      {/* Top Convergence Header */}
      <section className="bg-white border border-slate-200 rounded-lg p-5">
        <div className="flex flex-col gap-4">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
            <div className="min-w-0 max-w-3xl">
              <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono">
                <span className="font-semibold text-blue-700">{snapshot.missionId}</span>
                <span className="text-slate-400">&middot;</span>
                <span className="font-semibold text-amber-700">
                  DEVELOPMENT_STAGE_CONCEPT &mdash; G7 FLEET ACCEPTANCE PENDING
                </span>
              </div>
              <h2 className="mt-1 text-base font-semibold text-slate-900">
                Meridian Symphony &mdash; Estate Knowledge &amp; Causal Constellation
              </h2>
              <p className="mt-1 text-xs text-slate-600">
                Unified causal graph linking Founder Intent (GENESIS / QUAD) through Workforce &amp; Resource execution (LEGION / BATTALION / CHRONOS) to Independent Evidence (BEAST / KARMA / IDP #8169). Unverified or unimplemented surfaces stay visibly flagged.
              </p>
            </div>

            <button
              type="button"
              onClick={handleDownloadSpec}
              className="inline-flex items-center justify-center gap-1.5 rounded-md bg-slate-900 px-3.5 py-2 text-xs font-medium text-white hover:bg-slate-800 whitespace-nowrap shrink-0 self-start"
            >
              <Download className="h-3.5 w-3.5 text-blue-400" aria-hidden="true" />
              Download Final Spec (.md)
            </button>
          </div>

          <div
            role="group"
            aria-label="Symphony observatory mode"
            className="flex flex-wrap items-center gap-1 p-1 bg-slate-100 rounded-lg w-fit max-w-full"
          >
            <button
              type="button"
              onClick={() => setViewMode('live')}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md whitespace-nowrap ${
                viewMode === 'live'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Compass className="h-3.5 w-3.5" aria-hidden="true" />
              Live Constellation
            </button>
            <button
              type="button"
              onClick={() => {
                setViewMode('historical');
                setSemanticLayer(3);
              }}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md whitespace-nowrap ${
                viewMode === 'historical'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <History className="h-3.5 w-3.5" aria-hidden="true" />
              Historical KARMA Replay
            </button>
            <button
              type="button"
              onClick={() => setViewMode('i8095')}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md whitespace-nowrap ${
                viewMode === 'i8095'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Lock className="h-3.5 w-3.5" aria-hidden="true" />
              I-8095 Class-A Lockdown
            </button>
            <button
              type="button"
              onClick={() => setViewMode('sync_wake')}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md whitespace-nowrap ${
                viewMode === 'sync_wake'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Radio className="h-3.5 w-3.5" aria-hidden="true" />
              Sync, Wake &amp; Guarantees
            </button>
          </div>
        </div>

        {/* Truthfulness Counts Bar */}
        <div className="mt-4 pt-4 border-t border-slate-200 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs">
          <div>
            <div className="text-slate-500">Graph Nodes</div>
            <div className="mt-0.5 font-mono tabular-nums text-base font-semibold text-slate-900">
              {snapshot.counts.totalNodes}
            </div>
          </div>
          <div>
            <div className="text-slate-500">LIVE_VERIFIED</div>
            <div className="mt-0.5 font-mono tabular-nums text-base font-semibold text-emerald-700">
              {snapshot.counts.liveVerified}
            </div>
          </div>
          <div>
            <div className="text-slate-500">ARCHITECTURAL_SPEC</div>
            <div className="mt-0.5 font-mono tabular-nums text-base font-semibold text-sky-700">
              {snapshot.counts.architecturalSpec}
            </div>
          </div>
          <div>
            <div className="text-slate-500">PARTIAL</div>
            <div className="mt-0.5 font-mono tabular-nums text-base font-semibold text-amber-700">
              {snapshot.counts.partial}
            </div>
          </div>
          <div>
            <div className="text-slate-500">PENDING_INSPECTION</div>
            <div className="mt-0.5 font-mono tabular-nums text-base font-semibold text-amber-700">
              {snapshot.counts.pendingInspection}
            </div>
          </div>
          <div>
            <div className="text-slate-500">UNKNOWN</div>
            <div className="mt-0.5 font-mono tabular-nums text-base font-semibold text-red-700">
              {snapshot.counts.unknown}
            </div>
          </div>
        </div>
      </section>

      {actionBanner && (
        <div
          role="status"
          className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-xs font-medium text-emerald-900"
        >
          {actionBanner}
        </div>
      )}

      {/* Historical KARMA Incident Bar when active */}
      {viewMode === 'historical' && activeIncident && (
        <section className="bg-white border border-slate-200 rounded-lg p-5">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">
                Historical Incident Causal Replay &amp; KARMA Retention
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Select an estate incident to trace its causal chain across the constellation, inspect the retained correction, and verify recurrence count.
              </p>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {snapshot.incidents.map((inc) => (
                <button
                  key={inc.id}
                  type="button"
                  onClick={() => {
                    setSelectedIncidentId(inc.id);
                    const firstNode = inc.causalChain[0]?.nodeId;
                    if (firstNode) setSelectedNodeId(firstNode);
                  }}
                  className={`rounded-md border px-2.5 py-1.5 text-xs font-mono ${
                    selectedIncidentId === inc.id
                      ? 'border-slate-900 bg-slate-900 text-white'
                      : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  {inc.id} &middot; {inc.severity === 'RESOLVED' ? '0 recur' : 'OPEN'}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-4 border-t border-slate-200 pt-4 text-xs">
            <div className="lg:col-span-2 space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono font-semibold text-slate-900">{activeIncident.id}</span>
                <span className="font-semibold text-slate-900">{activeIncident.title}</span>
                <span
                  className={`font-mono font-semibold ${
                    activeIncident.severity === 'RESOLVED' ? 'text-emerald-700' : 'text-amber-700'
                  }`}
                >
                  [{activeIncident.severity} &middot; Recurrences: {activeIncident.recurrenceCount}]
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
                {activeIncident.causalChain.map((step) => (
                  <button
                    key={step.step}
                    type="button"
                    onClick={() => setSelectedNodeId(step.nodeId)}
                    className="text-left rounded border border-slate-200 bg-slate-50 p-2.5 hover:border-blue-400"
                  >
                    <div className="font-mono text-[11px] text-slate-500">
                      Step {step.step} &middot; {step.label}
                    </div>
                    <div className="mt-1 text-slate-800 leading-snug">{step.detail}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded border border-slate-200 bg-slate-50 p-3 space-y-2">
              <div className="text-[11px] font-semibold text-slate-600 uppercase tracking-wide">
                KARMA Retained Correction
              </div>
              <div className="text-slate-900">{activeIncident.karmaCorrection}</div>
              <div className="pt-1 border-t border-slate-200 font-mono text-[11px] text-emerald-700">
                Evidence: {activeIncident.evidenceRef}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* I-8095 NASA Class-A Mechanical Lockdown View */}
      {viewMode === 'i8095' && snapshot.i8095 && (
        <I8095LockdownPanel
          i8095={snapshot.i8095}
          runningSweep={runningActionId === 'run_i8095_lockdown_sweep'}
          onRunClassASweep={() => handleAuthorizedAction('run_i8095_lockdown_sweep')}
          onFocusNode={(nodeId) => {
            setSelectedNodeId(nodeId);
            setSemanticLayer(3);
            setViewMode('live');
          }}
        />
      )}

      {/* Real-Time Bundle Sync, Session Wake & Production Guarantees Monitor */}
      {viewMode === 'sync_wake' && <EstateSyncMonitor />}

      {/* Main Interactive Spatial Constellation + Inspector Grid */}
      {viewMode !== 'sync_wake' && (
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Left 8 Cols: Spatial Constellation Observatory */}
        <section className="xl:col-span-8 bg-[#080D18] border border-slate-800 rounded-lg overflow-hidden text-slate-100">
          {/* Observatory Controls Bar */}
          <div className="px-4 py-3 border-b border-slate-800 bg-[#0D1526] flex flex-wrap items-center justify-between gap-3">
            {/* Semantic Zoom Levels */}
            <div className="flex flex-wrap items-center gap-1">
              {ZOOM_LAYERS.map((z) => (
                <button
                  key={z.layer}
                  type="button"
                  onClick={() => {
                    setSemanticLayer(z.layer);
                  }}
                  className={`px-2.5 py-1 rounded text-[11px] font-mono whitespace-nowrap ${
                    semanticLayer === z.layer
                      ? 'bg-sky-500/20 text-sky-300 border border-sky-400/50'
                      : 'text-slate-400 hover:text-slate-200 border border-transparent'
                  }`}
                >
                  {z.label}
                </button>
              ))}
            </div>

            {/* Search & Pan/Zoom Tools */}
            <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
              <div className="relative flex-1 min-w-[160px] sm:flex-initial">
                <Search className="h-3.5 w-3.5 text-slate-400 absolute left-2.5 top-2" aria-hidden="true" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => {
                    const val = e.target.value;
                    setSearchQuery(val);
                    const q = val.trim().toLowerCase();
                    if (q) {
                      const hit = visibleNodes.find(
                        (n) => n.label.toLowerCase().includes(q) || n.id.toLowerCase().includes(q)
                      );
                      if (hit) setSelectedNodeId(hit.id);
                    }
                  }}
                  placeholder="Search node, model, IDP..."
                  aria-label="Search estate constellation"
                  className="w-full sm:w-52 rounded border border-slate-700 bg-[#070B14] pl-8 pr-2.5 py-1 text-xs text-slate-100 placeholder:text-slate-500 focus:border-sky-400 focus:outline-none"
                />
              </div>

              <button
                type="button"
                onClick={() => setTraceCausal((v) => !v)}
                className={`rounded border px-2 py-1 text-[11px] font-mono ${
                  traceCausal
                    ? 'border-emerald-500/50 bg-emerald-500/15 text-emerald-300'
                    : 'border-slate-700 bg-[#070B14] text-slate-400'
                }`}
              >
                Trace Chain: {traceCausal ? 'ON' : 'OFF'}
              </button>

              <div className="flex items-center border border-slate-700 rounded bg-[#070B14]">
                <button
                  type="button"
                  aria-label="Zoom out"
                  onClick={() => setZoom((z) => Math.max(0.7, Number((z - 0.15).toFixed(2))))}
                  className="p-1.5 text-slate-300 hover:text-white"
                >
                  <ZoomOut className="h-3.5 w-3.5" />
                </button>
                <span className="px-2 text-[11px] font-mono tabular-nums text-slate-300">
                  {Math.round(zoom * 100)}%
                </span>
                <button
                  type="button"
                  aria-label="Zoom in"
                  onClick={() => setZoom((z) => Math.min(2.2, Number((z + 0.15).toFixed(2))))}
                  className="p-1.5 text-slate-300 hover:text-white"
                >
                  <ZoomIn className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  aria-label="Reset camera"
                  onClick={() => {
                    setZoom(1);
                    setPan({ x: 0, y: 0 });
                  }}
                  className="p-1.5 text-slate-300 hover:text-white border-l border-slate-700"
                >
                  <Maximize2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </div>

          {/* Spatial SVG Constellation Canvas */}
          <div
            className="relative h-[320px] sm:h-[560px] w-full overflow-hidden cursor-grab active:cursor-grabbing select-none"
            onMouseDown={(e) => {
              draggingRef.current = {
                active: true,
                startX: e.clientX,
                startY: e.clientY,
                origX: pan.x,
                origY: pan.y,
              };
            }}
            onMouseMove={(e) => {
              if (!draggingRef.current.active) return;
              setPan({
                x: draggingRef.current.origX + (e.clientX - draggingRef.current.startX),
                y: draggingRef.current.origY + (e.clientY - draggingRef.current.startY),
              });
            }}
            onMouseUp={() => {
              draggingRef.current.active = false;
            }}
            onMouseLeave={() => {
              draggingRef.current.active = false;
            }}
          >
            <svg
              viewBox="0 0 1160 720"
              className="h-full w-full"
              role="img"
              aria-label="Meridian Symphony Interactive Estate Graph"
            >
              <defs>
                <pattern id="symphony-grid" width="48" height="48" patternUnits="userSpaceOnUse">
                  <path d="M 48 0 L 0 0 0 48" fill="none" stroke="#131D31" strokeWidth="1" />
                </pattern>
                <radialGradient id="core-aura" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="#0EA5E9" stopOpacity="0.18" />
                  <stop offset="70%" stopColor="#10B981" stopOpacity="0.06" />
                  <stop offset="100%" stopColor="#080D18" stopOpacity="0" />
                </radialGradient>
                <marker
                  id="arrow-head"
                  markerWidth="8"
                  markerHeight="8"
                  refX="7"
                  refY="4"
                  orient="auto"
                >
                  <path d="M 0 1 L 7 4 L 0 7 z" fill="#64748B" />
                </marker>
                <marker
                  id="arrow-active"
                  markerWidth="8"
                  markerHeight="8"
                  refX="7"
                  refY="4"
                  orient="auto"
                >
                  <path d="M 0 1 L 7 4 L 0 7 z" fill="#38BDF8" />
                </marker>
              </defs>

              <rect width="1160" height="720" fill="url(#symphony-grid)" />

              <g
                transform={`translate(${580 + pan.x}, ${360 + pan.y}) scale(${zoom}) translate(-580, -360)`}
              >
                {/* Central Orbital Field around Knowledge & Causal Graph */}
                <circle cx="560" cy="345" r="245" fill="url(#core-aura)" />
                <circle
                  cx="560"
                  cy="345"
                  r="195"
                  fill="none"
                  stroke="#1E293B"
                  strokeDasharray="4 6"
                  strokeWidth="1"
                />
                <circle
                  cx="560"
                  cy="345"
                  r="305"
                  fill="none"
                  stroke="#131D31"
                  strokeDasharray="2 8"
                  strokeWidth="1"
                />

                {/* Causal Graph Edges */}
                {visibleEdges.map((edge) => {
                  const from = nodeMap.get(edge.from);
                  const to = nodeMap.get(edge.to);
                  if (!from || !to) return null;

                  const isIncidentEdge =
                    viewMode === 'historical' &&
                    incidentNodeIds.has(edge.from) &&
                    incidentNodeIds.has(edge.to);
                  const isCausalActive =
                    viewMode === 'live' && traceCausal && causalTrace.activeEdges.has(edge.id);
                  const highlighted = isIncidentEdge || isCausalActive;
                  const dimmed =
                    (viewMode === 'historical' && !isIncidentEdge) ||
                    (viewMode === 'live' && traceCausal && !isCausalActive);

                  const mx = (from.x + to.x) / 2;
                  const my = (from.y + to.y) / 2 - (from.y === to.y ? 22 : 0);

                  return (
                    <g key={edge.id} opacity={dimmed ? 0.16 : highlighted ? 1 : 0.6}>
                      <path
                        d={`M ${from.x} ${from.y} Q ${mx} ${my} ${to.x} ${to.y}`}
                        fill="none"
                        stroke={highlighted ? channelStroke(edge.channel) : '#334155'}
                        strokeWidth={highlighted ? 2 : 1.15}
                        markerEnd={highlighted ? 'url(#arrow-active)' : 'url(#arrow-head)'}
                      />
                    </g>
                  );
                })}

                {/* Constellation Nodes */}
                {visibleNodes.map((node) => {
                  const style = statusColors(node.epistemicStatus);
                  const isSelected = node.id === selectedNodeId;
                  const isIncidentHit = viewMode === 'historical' && incidentNodeIds.has(node.id);
                  const isCausalPeer =
                    viewMode === 'live' &&
                    traceCausal &&
                    (causalTrace.upstream.has(node.id) || causalTrace.downstream.has(node.id));
                  const isSearchHit = searchMatches.size > 0 && searchMatches.has(node.id);

                  const dimmed =
                    (searchMatches.size > 0 && !isSearchHit && !isSelected) ||
                    (viewMode === 'historical' && !isIncidentHit && !isSelected) ||
                    (viewMode === 'live' &&
                      traceCausal &&
                      !isSelected &&
                      !isCausalPeer &&
                      searchMatches.size === 0);

                  const isCore = node.id === 'estate_knowledge_graph';
                  const boxW = isCore ? 238 : node.minZoomLevel === 0 ? 156 : 148;
                  const boxH = isCore ? 64 : 52;

                  return (
                    <g
                      key={node.id}
                      role="button"
                      tabIndex={0}
                      aria-label={`${node.label} (${node.epistemicStatus})`}
                      transform={`translate(${node.x}, ${node.y})`}
                      opacity={dimmed ? 0.24 : 1}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedNodeId(node.id);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          setSelectedNodeId(node.id);
                        }
                      }}
                      className="cursor-pointer focus:outline-none"
                    >
                      {(isSelected || isSearchHit || isIncidentHit) && (
                        <rect
                          x={-boxW / 2 - 4}
                          y={-boxH / 2 - 4}
                          width={boxW + 8}
                          height={boxH + 8}
                          rx={6}
                          fill="none"
                          stroke={isSelected ? '#38BDF8' : '#FBBF24'}
                          strokeWidth={1.5}
                        />
                      )}

                      <rect
                        x={-boxW / 2}
                        y={-boxH / 2}
                        width={boxW}
                        height={boxH}
                        rx={4}
                        fill={style.fill}
                        stroke={style.stroke}
                        strokeWidth={isSelected || isCore ? 1.8 : 1.1}
                      />

                      <text
                        x={0}
                        y={-7}
                        textAnchor="middle"
                        fill="#F8FAFC"
                        fontSize={isCore ? 11.5 : 10.5}
                        fontWeight="700"
                        fontFamily="JetBrains Mono, monospace"
                      >
                        {node.label.length > 26 ? `${node.label.slice(0, 24)}..` : node.label}
                      </text>

                      <text
                        x={0}
                        y={8}
                        textAnchor="middle"
                        fill={style.text}
                        fontSize={8.5}
                        fontWeight="600"
                        fontFamily="JetBrains Mono, monospace"
                      >
                        {node.epistemicStatus}
                      </text>

                      <text
                        x={0}
                        y={20}
                        textAnchor="middle"
                        fill="#94A3B8"
                        fontSize={8}
                        fontFamily="Public Sans, sans-serif"
                      >
                        {node.metrics[0] ? `${node.metrics[0].label}: ${node.metrics[0].value}`.slice(0, 30) : ''}
                      </text>
                    </g>
                  );
                })}
              </g>
            </svg>
          </div>

          {/* Docked Observatory Legend Footer */}
          <div className="border-t border-slate-800 bg-[#070B14] px-4 py-2 flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono text-slate-300">
            <div className="flex flex-wrap items-center gap-4">
              <span className="text-emerald-400">&#9632; LIVE_VERIFIED</span>
              <span className="text-sky-400">&#9632; ARCHITECTURAL_SPEC</span>
              <span className="text-amber-400">&#9632; PARTIAL / PENDING</span>
              <span className="text-red-400">&#9632; UNKNOWN</span>
            </div>
            <span className="text-slate-400">Drag to pan &middot; Click any node to trace causes &amp; evidence</span>
          </div>
        </section>

        {/* Right 4 Cols: Live Node Inspector & Authorized Actions */}
        <aside className="xl:col-span-4 bg-white border border-slate-200 rounded-lg p-5 space-y-4">
          {selectedNode && (
            <>
              <div className="border-b border-slate-200 pb-3.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[11px] font-mono text-slate-500">
                    Layer L{selectedNode.minZoomLevel} &middot; {selectedNode.id}
                  </span>
                  <span
                    className={`rounded border px-2 py-0.5 text-[10px] font-mono font-semibold ${
                      statusColors(selectedNode.epistemicStatus).badge
                    }`}
                  >
                    {selectedNode.epistemicStatus}
                  </span>
                </div>
                <h3 className="mt-1.5 text-base font-semibold text-slate-900">
                  {selectedNode.label}
                </h3>
                <p className="text-xs text-slate-500">{selectedNode.subtitle}</p>
              </div>

              <p className="text-xs text-slate-700 leading-relaxed">{selectedNode.summary}</p>

              <div className="grid grid-cols-2 gap-2 text-xs border border-slate-200 rounded-md p-3 bg-slate-50">
                <div>
                  <div className="text-[11px] text-slate-500">Telemetry Source</div>
                  <div className="mt-0.5 font-mono font-medium text-slate-900">
                    {selectedNode.telemetrySource}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] text-slate-500">Accountable Owner</div>
                  <div className="mt-0.5 font-medium text-slate-900 truncate" title={selectedNode.owner}>
                    {selectedNode.owner}
                  </div>
                </div>
              </div>

              {/* Real Telemetry & Blind Signals */}
              <div>
                <div className="text-xs font-semibold text-slate-900 mb-2">
                  Measured State &amp; Telemetry
                </div>
                <div className="space-y-1.5">
                  {selectedNode.metrics.map((m) => (
                    <div
                      key={m.label}
                      className="flex items-center justify-between gap-3 rounded border border-slate-200 px-3 py-1.5 text-xs"
                    >
                      <span className="text-slate-600">{m.label}</span>
                      <span
                        className={`font-mono tabular-nums font-semibold ${
                          m.blind ? 'text-amber-700' : 'text-slate-900'
                        }`}
                      >
                        {m.value}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Causal Chain Navigation */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="border border-slate-200 rounded p-2.5">
                  <div className="text-[11px] font-semibold text-slate-500 mb-1.5">
                    Upstream Causes ({causalTrace.upstream.size})
                  </div>
                  <div className="space-y-1 max-h-24 overflow-y-auto">
                    {Array.from(causalTrace.upstream).slice(0, 5).map((uid) => {
                      const target = snapshot.nodes.find((n) => n.id === uid);
                      if (!target) return null;
                      return (
                        <button
                          key={uid}
                          type="button"
                          onClick={() => setSelectedNodeId(uid)}
                          className="w-full text-left font-mono text-[11px] text-blue-700 hover:underline truncate"
                        >
                          &larr; {target.label}
                        </button>
                      );
                    })}
                    {causalTrace.upstream.size === 0 && (
                      <span className="text-[11px] text-slate-400">Root mandate node</span>
                    )}
                  </div>
                </div>

                <div className="border border-slate-200 rounded p-2.5">
                  <div className="text-[11px] font-semibold text-slate-500 mb-1.5">
                    Downstream Effects ({causalTrace.downstream.size})
                  </div>
                  <div className="space-y-1 max-h-24 overflow-y-auto">
                    {Array.from(causalTrace.downstream).slice(0, 5).map((did) => {
                      const target = snapshot.nodes.find((n) => n.id === did);
                      if (!target) return null;
                      return (
                        <button
                          key={did}
                          type="button"
                          onClick={() => setSelectedNodeId(did)}
                          className="w-full text-left font-mono text-[11px] text-emerald-700 hover:underline truncate"
                        >
                          &rarr; {target.label}
                        </button>
                      );
                    })}
                    {causalTrace.downstream.size === 0 && (
                      <span className="text-[11px] text-slate-400">Terminal outcome</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Missing / Stale Disclosures */}
              {selectedNode.missingOrStale.length > 0 && (
                <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs">
                  <div className="flex items-center gap-1.5 font-semibold text-amber-800">
                    <AlertTriangle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                    Missing / Unverified Telemetry
                  </div>
                  <ul className="mt-1.5 space-y-1 text-amber-900 list-disc pl-4">
                    {selectedNode.missingOrStale.map((msg, idx) => (
                      <li key={idx}>{msg}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Authorized Live Actions */}
              {selectedNode.authorizedActions.length > 0 && (
                <div className="pt-2 border-t border-slate-200 space-y-2">
                  <div className="text-xs font-semibold text-slate-900">
                    Authorized Control Actions
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {selectedNode.authorizedActions.map((act) => (
                      <button
                        key={act.id}
                        type="button"
                        disabled={runningActionId === act.id}
                        onClick={() => handleAuthorizedAction(act.id)}
                        className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                      >
                        <Activity className="h-3.5 w-3.5" aria-hidden="true" />
                        {runningActionId === act.id ? 'Executing...' : act.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {actionBanner && (
                <div className="rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
                  {actionBanner}
                </div>
              )}
            </>
          )}
        </aside>
      </div>
      )}

      {/* Bottom Convergence Grid: 6-Stage Lifecycle + 7 Delivery Gates */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 6-Stage Orchestration Lifecycle */}
        <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">
                Six-Stage Orchestration Lifecycle
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Canonical convergence loop from signed founder intent to KARMA retention.
              </p>
            </div>
            <GitCommitHorizontal className="h-4 w-4 text-slate-400" aria-hidden="true" />
          </div>
          <div className="divide-y divide-slate-200">
            {snapshot.lifecycleStages.map((s) => (
              <div
                key={s.stage}
                className="px-4 sm:px-5 py-3 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 sm:gap-4 text-xs"
              >
                <div className="min-w-0">
                  <div className="font-semibold text-slate-900">
                    Stage {s.stage}: {s.name}
                  </div>
                  <div className="mt-0.5 text-slate-600">{s.contract}</div>
                </div>
                <div className="sm:text-right shrink-0">
                  <div className="font-mono font-medium text-slate-800">{s.actors}</div>
                  <div
                    className={`mt-0.5 font-mono text-[11px] font-semibold ${
                      s.status === 'ACTIVE_SANDBOX' ? 'text-emerald-700' : 'text-sky-700'
                    }`}
                  >
                    {s.status}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Seven Delivery Gates (G1-G7) */}
        <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <div className="px-4 sm:px-5 py-4 border-b border-slate-200 flex items-center justify-between gap-2">
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-slate-900">
                Seven Delivery Gates (IDP #8169)
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                G1–G6 verified in sandbox control plane; G7 live fleet acceptance remains pending.
              </p>
            </div>
            <ShieldCheck className="h-4 w-4 text-emerald-700 shrink-0" aria-hidden="true" />
          </div>
          <div className="divide-y divide-slate-200">
            {snapshot.deliveryGates.map((g) => (
              <div
                key={g.id}
                className="px-4 sm:px-5 py-3 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 sm:gap-4 text-xs"
              >
                <div className="min-w-0">
                  <div className="font-semibold text-slate-900">
                    <span className="font-mono">{g.id}</span> &middot; {g.title}
                  </div>
                  <div className="mt-0.5 text-slate-600">{g.criterion}</div>
                  <div className="mt-0.5 font-mono text-[11px] text-slate-500 break-words">
                    Evidence: {g.evidence}
                  </div>
                </div>
                <div
                  className={`font-mono text-[11px] font-semibold shrink-0 flex items-center gap-1 ${
                    g.status === 'PASS_SANDBOX' ? 'text-emerald-700' : 'text-amber-700'
                  }`}
                >
                  {g.status === 'PASS_SANDBOX' ? 'PASS_SANDBOX' : 'PENDING_FLEET_ACCEPTANCE'}
                  <ArrowRight className="h-3 w-3 shrink-0" aria-hidden="true" />
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
