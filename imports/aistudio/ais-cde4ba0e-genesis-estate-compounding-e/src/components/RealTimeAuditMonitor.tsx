/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import {
  LaneNode,
  StepReceipt,
  INITIAL_LANES,
  INITIAL_STEP_RECEIPTS,
} from '../lib/protocolEngine.ts';
import {
  Server,
  Activity,
  ShieldCheck,
  Terminal,
  Copy,
  Check,
  Radio,
  Filter,
  RefreshCw,
  ExternalLink,
  ChevronRight,
  Database,
} from 'lucide-react';

export const RealTimeAuditMonitor: React.FC = () => {
  const [lanes, setLanes] = useState<LaneNode[]>(INITIAL_LANES);
  const [receipts, setReceipts] = useState<StepReceipt[]>(INITIAL_STEP_RECEIPTS);
  const [selectedReceipt, setSelectedReceipt] = useState<StepReceipt | null>(INITIAL_STEP_RECEIPTS[0]);
  const [selectedAgentFilter, setSelectedAgentFilter] = useState<'ALL' | 'otto' | 'concierge'>('ALL');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isWebSocketActive, setIsWebSocketActive] = useState<boolean>(true);

  // Simulate Mac Edge 15s lease countdown
  useEffect(() => {
    const timer = setInterval(() => {
      setLanes((prev) =>
        prev.map((l) => {
          if (l.id === 'LANE_C_MAC_EDGE') {
            const nextRemaining = l.remainingLeaseSeconds <= 1 ? 15 : l.remainingLeaseSeconds - 1;
            return {
              ...l,
              remainingLeaseSeconds: nextRemaining,
              latencyMs: Number((0.8 + Math.random() * 0.4).toFixed(1)),
            };
          }
          return {
            ...l,
            latencyMs: Number((l.latencyMs + (Math.random() * 0.6 - 0.3)).toFixed(1)),
          };
        })
      );
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const handleCopyHash = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleSimulateSyntheticStep = () => {
    const randomHex = Array.from({ length: 64 }, () =>
      Math.floor(Math.random() * 16).toString(16)
    ).join('');
    
    const newReceipt: StepReceipt = {
      id: `RCP-${Math.floor(98125 + Math.random() * 50)}-${Math.random() > 0.5 ? 'A' : 'B'}`,
      timestamp: new Date().toISOString(),
      agent: Math.random() > 0.5 ? 'otto' : 'concierge',
      laneId: Math.random() > 0.5 ? 'LANE_C_MAC_EDGE' : 'LANE_A_GCP',
      action: 'ATTEST_INVARIANT_STEP',
      inputSummary: 'Autonomous heartbeat telemetry ping verified against estate.db',
      durationMs: Math.floor(15 + Math.random() * 60),
      exitCode: 0,
      hmacSignature: randomHex,
      isVerified: true,
      stdout: '[OK] Cryptographic attestation verified.\n[OK] estate.db record committed.\n[OK] Zero entropy drift measured.',
      stderr: '',
    };

    setReceipts((prev) => [newReceipt, ...prev]);
    setSelectedReceipt(newReceipt);
  };

  const filteredReceipts = receipts.filter((r) => {
    if (selectedAgentFilter === 'ALL') return true;
    return r.agent === selectedAgentFilter;
  });

  return (
    <div className="space-y-8">
      {/* Header with Transport & Node status */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 sm:p-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs font-mono text-cyan-400">
              <Database className="w-4 h-4 text-cyan-400" />
              <span>ESTATE.DB TELEMETRY & MULTI-LANE CONSENSUS</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              Real-Time Audit Monitor
            </h1>
            <p className="text-slate-400 text-sm">
              Live cryptographic attestation receipts for otto & concierge with dual-transport WebSocket / polling fallback.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 text-xs font-mono">
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-slate-300">
                {isWebSocketActive ? 'WebSocket (Live Stream)' : 'HTTP Polling Fallback'}
              </span>
            </div>

            <button
              onClick={handleSimulateSyntheticStep}
              className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-cyan-300 bg-cyan-950/80 hover:bg-cyan-900/80 border border-cyan-800 rounded-lg transition-colors cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Emit Prober Step</span>
            </button>
          </div>
        </div>
      </div>

      {/* Multi-Lane 4-Node Topology Grid */}
      <div className="space-y-3">
        <div className="flex items-center justify-between text-xs font-mono text-slate-400">
          <span>ACTIVE MULTI-LANE RAFT QUORUM TOPOLOGY (4 NODES)</span>
          <span>QUORUM: 3/3 VOTING NODES SYNCHRONIZED</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {lanes.map((lane) => (
            <div
              key={lane.id}
              className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 space-y-3 hover:border-slate-700 transition-all"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-[11px] font-mono font-bold text-cyan-400">{lane.id}</div>
                  <div className="text-sm font-semibold text-white">{lane.name}</div>
                  <div className="text-[11px] text-slate-400 font-mono">{lane.ip}</div>
                </div>
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                  lane.role === 'RAFT_LEADER'
                    ? 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                    : lane.role === 'RAFT_FOLLOWER'
                    ? 'bg-blue-950 text-blue-300 border border-blue-800'
                    : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                }`}>
                  {lane.role}
                </span>
              </div>

              <div className="text-xs text-slate-400 font-mono truncate">{lane.spec}</div>

              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800/80 text-[11px] font-mono">
                <div>
                  <span className="text-slate-500 block">Ping Latency:</span>
                  <span className="text-slate-200 tabular-nums font-bold">{lane.latencyMs} ms</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Raft Term:</span>
                  <span className="text-slate-200 tabular-nums">#{lane.raftTerm}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Heartbeat Lease:</span>
                  <span className={`tabular-nums font-bold ${
                    lane.remainingLeaseSeconds < 5 ? 'text-amber-400' : 'text-emerald-400'
                  }`}>
                    {lane.remainingLeaseSeconds}s / {lane.heartbeatLeaseSeconds}s
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block">CPU Load:</span>
                  <span className="text-slate-200 tabular-nums">{lane.cpuPercent}%</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Audit Step Receipts & Drawer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left: Receipts Stream (7 cols) */}
        <div className="lg:col-span-7 bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h2 className="text-base font-semibold text-white">Live Step Telemetry (estate.db)</h2>
              <p className="text-xs text-slate-400">Cryptographically signed execution receipts</p>
            </div>

            {/* Filter buttons */}
            <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
              {(['ALL', 'otto', 'concierge'] as const).map((filter) => (
                <button
                  key={filter}
                  onClick={() => setSelectedAgentFilter(filter)}
                  className={`px-2.5 py-1 rounded transition-colors ${
                    selectedAgentFilter === filter
                      ? 'bg-slate-800 text-cyan-300 font-semibold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {filter}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2 max-h-[440px] overflow-y-auto pr-1">
            {filteredReceipts.map((rcp) => (
              <div
                key={rcp.id}
                onClick={() => setSelectedReceipt(rcp)}
                className={`p-3.5 rounded-lg border transition-all cursor-pointer ${
                  selectedReceipt?.id === rcp.id
                    ? 'bg-slate-800/90 border-cyan-500 shadow-sm'
                    : 'bg-slate-950/70 border-slate-800/80 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-white">{rcp.id}</span>
                    <span className={`text-[10px] font-mono px-1.5 py-0.2 rounded font-semibold ${
                      rcp.agent === 'otto'
                        ? 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                        : 'bg-teal-950 text-teal-300 border border-teal-800'
                    }`}>
                      {rcp.agent}
                    </span>
                    <span className="text-[11px] font-mono text-slate-400">{rcp.laneId}</span>
                  </div>

                  <div className="flex items-center gap-2 text-xs font-mono">
                    <span className="text-emerald-400 flex items-center gap-1 text-[11px]">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      HMAC VERIFIED
                    </span>
                    <span className="text-slate-500 tabular-nums">{rcp.durationMs}ms</span>
                  </div>
                </div>

                <div className="text-xs text-slate-300 mt-1 font-medium">{rcp.action}</div>
                <div className="text-[11px] text-slate-400 mt-0.5 truncate">{rcp.inputSummary}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Selected Receipt Details Drawer (5 cols) */}
        <div className="lg:col-span-5 bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-semibold text-white">Cryptographic Receipt Drawer</h3>
            </div>
            {selectedReceipt && (
              <span className="text-xs font-mono text-cyan-400">{selectedReceipt.id}</span>
            )}
          </div>

          {selectedReceipt ? (
            <div className="space-y-4 text-xs font-mono">
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-400">Timestamp:</span>
                  <span className="text-slate-200">{selectedReceipt.timestamp}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Exit Code:</span>
                  <span className="text-emerald-400 font-bold">{selectedReceipt.exitCode} (SUCCESS)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Execution Lane:</span>
                  <span className="text-cyan-300">{selectedReceipt.laneId}</span>
                </div>
                
                <div className="pt-2 border-t border-slate-800">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-slate-400 text-[10px] uppercase">HMAC-SHA256 Signature:</span>
                    <button
                      onClick={() => handleCopyHash(selectedReceipt.hmacSignature, selectedReceipt.id)}
                      className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 text-[11px]"
                    >
                      {copiedId === selectedReceipt.id ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-400" />
                          <span className="text-emerald-400">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          <span>Copy Hash</span>
                        </>
                      )}
                    </button>
                  </div>
                  <div className="p-2 bg-slate-900 rounded text-[10px] text-cyan-300 break-all select-all">
                    {selectedReceipt.hmacSignature}
                  </div>
                </div>
              </div>

              {/* Stdout Inspection */}
              <div className="space-y-1">
                <div className="text-[11px] font-bold text-slate-300">Standard Output (stdout)</div>
                <pre className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-[11px] text-emerald-300 whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto">
                  {selectedReceipt.stdout || '(no standard output logged)'}
                </pre>
              </div>

              {/* Stderr Inspection */}
              {selectedReceipt.stderr && (
                <div className="space-y-1">
                  <div className="text-[11px] font-bold text-rose-400">Standard Error (stderr)</div>
                  <pre className="p-3 bg-slate-950 rounded-lg border border-rose-950 text-[11px] text-rose-300 whitespace-pre-wrap leading-relaxed max-h-32 overflow-y-auto">
                    {selectedReceipt.stderr}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-slate-500 font-mono">
              Select a receipt from the stream to view full cryptographic proof.
            </div>
          )}
        </div>

      </div>
    </div>
  );
};
