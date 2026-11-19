/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  IpnPacket,
  IpnStage,
  INITIAL_IPN_PACKETS,
} from '../lib/protocolEngine.ts';
import {
  Layers,
  Send,
  CheckCircle2,
  Clock,
  Coins,
  ArrowRight,
  ShieldCheck,
  FileCheck,
  Terminal,
  Activity,
  Sparkles,
} from 'lucide-react';

const IPN_STAGES: IpnStage[] = [
  'INTAKE',
  'CLASSIFY',
  'ROUTE',
  'EXECUTE',
  'VERIFY',
  'YIELD',
  'POST_YIELD',
  'IMPROVEMENT',
];

export const InstructionPocketNetworkSurface: React.FC = () => {
  const [packets, setPackets] = useState<IpnPacket[]>(INITIAL_IPN_PACKETS);
  const [selectedPacketId, setSelectedPacketId] = useState<string>(INITIAL_IPN_PACKETS[0].packetId);
  const [newInstructionText, setNewInstructionText] = useState<string>(
    'Verify oracle alignment of historical snapshot vs Genesis fleet under strict 64MB memory limit'
  );
  const [isTransmitting, setIsTransmitting] = useState<boolean>(false);

  const activePacket = packets.find((p) => p.packetId === selectedPacketId) || packets[0];

  const handleTransmitNewPacket = () => {
    if (!newInstructionText.trim() || isTransmitting) return;

    setIsTransmitting(true);
    const newId = `IPN-2026-${Math.floor(9815 + Math.random() * 50)}`;
    const newPacket: IpnPacket = {
      packetId: newId,
      instructionText: newInstructionText,
      sender: 'founder-sovereign-0x8f2d',
      targetLane: 'LANE_SCIENCE_AUTONOMOUS',
      currentStage: 'INTAKE',
      startTime: new Date().toISOString(),
      totalLatencyMs: 45,
      tokenConsumption: 512,
      computeCostUsd: 0.0006,
      decisionsTaken: [
        'Ingested via deterministic parser',
        'Allocated hermetic research pod in Science Lane',
      ],
      alternativesRejected: [
        'Direct unmonitored production mutation (Rejected)'
      ],
      oracleAlignmentScore: 0.99,
      historyLog: [
        {
          stage: 'INTAKE',
          timestamp: new Date().toLocaleTimeString(),
          agent: 'concierge',
          durationMs: 12,
          notes: 'Packet deconstructed into formal JSON contract',
        },
      ],
    };

    setPackets((prev) => [newPacket, ...prev]);
    setSelectedPacketId(newId);

    // Simulate pipeline progression
    setTimeout(() => {
      setPackets((prev) =>
        prev.map((p) => (p.packetId === newId ? { ...p, currentStage: 'ROUTE' as IpnStage } : p))
      );
    }, 600);

    setTimeout(() => {
      setPackets((prev) =>
        prev.map((p) => (p.packetId === newId ? { ...p, currentStage: 'EXECUTE' as IpnStage } : p))
      );
    }, 1200);

    setTimeout(() => {
      setPackets((prev) =>
        prev.map((p) =>
          p.packetId === newId
            ? {
                ...p,
                currentStage: 'YIELD' as IpnStage,
                totalLatencyMs: 284,
                historyLog: [
                  ...p.historyLog,
                  { stage: 'ROUTE', timestamp: new Date().toLocaleTimeString(), agent: 'litellm-router', durationMs: 24, notes: 'Routed to Science Pod' },
                  { stage: 'EXECUTE', timestamp: new Date().toLocaleTimeString(), agent: 'science-lead', durationMs: 190, notes: 'Completed benchmark runs' },
                  { stage: 'YIELD', timestamp: new Date().toLocaleTimeString(), agent: 'otto', durationMs: 32, notes: 'Yield sealed with verified audit proof' },
                ],
              }
            : p
        )
      );
      setIsTransmitting(false);
    }, 2000);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 sm:p-8">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-mono text-cyan-400">
              <Layers className="w-4 h-4 text-cyan-400" />
              <span>INSTRUCTION POCKET NETWORK (IPN) · FULL LIFECYCLE FLOW TO YIELD</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              Instruction Pocket Network (IPN)
            </h1>
            <p className="text-slate-400 text-sm max-w-2xl">
              Every instruction ever sent in the estate flows as a traceable packet through its 8 lifecycle stages. Retained beyond yield to continuously verify oracle alignment with reality and eliminate drift.
            </p>
          </div>

          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs font-mono space-y-1.5 shrink-0 min-w-[260px]">
            <div className="text-slate-500 uppercase tracking-wider text-[10px]">IPN Network Vitals</div>
            <div className="flex justify-between items-center text-slate-200">
              <span>Packets Traced:</span>
              <span className="text-cyan-400 font-bold tabular-nums">{packets.length} Active</span>
            </div>
            <div className="flex justify-between items-center text-slate-200">
              <span>Oracle Alignment:</span>
              <span className="text-emerald-400 font-bold tabular-nums">98.4% Proven</span>
            </div>
            <div className="flex justify-between items-center text-slate-200">
              <span>Silent Drops:</span>
              <span className="text-emerald-400 font-bold tabular-nums">0 (Canon §3)</span>
            </div>
          </div>
        </div>
      </div>

      {/* 8-Stage Lifecycle Visual Pipeline Strip */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-3">
        <div className="text-xs font-mono uppercase tracking-wider text-slate-400 flex justify-between items-center">
          <span>8-Stage Deterministic Lifecycle Flow</span>
          <span className="text-cyan-400 font-bold">Packet: {activePacket.packetId}</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
          {IPN_STAGES.map((stage, idx) => {
            const isCurrent = activePacket.currentStage === stage;
            const isCompleted = IPN_STAGES.indexOf(activePacket.currentStage) >= idx;

            return (
              <div
                key={stage}
                className={`p-3 rounded-lg border text-xs font-mono transition-all flex flex-col justify-between ${
                  isCurrent
                    ? 'bg-cyan-950/80 border-cyan-400 text-cyan-200 shadow-md ring-1 ring-cyan-400/40'
                    : isCompleted
                    ? 'bg-slate-950 border-emerald-800/60 text-emerald-300'
                    : 'bg-slate-950/40 border-slate-900 text-slate-500'
                }`}
              >
                <div className="flex justify-between items-center">
                  <span className="text-[10px] opacity-70">0{idx + 1}</span>
                  {isCompleted && !isCurrent && <CheckCircle2 className="w-3 h-3 text-emerald-400" />}
                  {isCurrent && <Activity className="w-3 h-3 text-cyan-400 animate-pulse" />}
                </div>
                <div className="font-bold text-[11px] truncate mt-2">{stage}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Transmit New Packet Simulator */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
        <div className="text-xs font-mono font-bold text-white flex items-center gap-2">
          <Send className="w-4 h-4 text-cyan-400" />
          <span>TRANSMIT INSTRUCTION PACKET INTO IPN MESH</span>
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            value={newInstructionText}
            onChange={(e) => setNewInstructionText(e.target.value)}
            placeholder="Type any instruction to trace its packet flow through the lifecycle..."
            className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-cyan-200 font-mono focus:outline-none focus:border-cyan-500"
          />
          <button
            onClick={handleTransmitNewPacket}
            disabled={isTransmitting}
            className="px-6 py-2.5 text-xs font-semibold text-slate-950 bg-gradient-to-r from-cyan-400 to-teal-300 hover:from-cyan-300 hover:to-teal-200 rounded-xl transition-all shadow cursor-pointer disabled:opacity-50 whitespace-nowrap"
          >
            {isTransmitting ? 'Transmitting Packet...' : 'Transmit & Trace'}
          </button>
        </div>
      </div>

      {/* Grid: Packet Stream & Deep Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left: Active Packets (5 cols) */}
        <div className="lg:col-span-5 bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h2 className="text-base font-semibold text-white">Active Instruction Packets</h2>
            <span className="text-xs font-mono text-slate-400">{packets.length} Total</span>
          </div>

          <div className="space-y-2.5 max-h-[500px] overflow-y-auto pr-1">
            {packets.map((packet) => (
              <div
                key={packet.packetId}
                onClick={() => setSelectedPacketId(packet.packetId)}
                className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                  selectedPacketId === packet.packetId
                    ? 'bg-slate-800/95 border-cyan-400 shadow-sm'
                    : 'bg-slate-950/80 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex justify-between items-center">
                  <span className="text-xs font-mono font-bold text-white">{packet.packetId}</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 font-semibold">
                    {packet.currentStage}
                  </span>
                </div>
                <div className="text-xs text-slate-300 font-medium mt-1 line-clamp-2">
                  {packet.instructionText}
                </div>
                <div className="flex justify-between items-center text-[11px] font-mono text-slate-500 mt-2 pt-2 border-t border-slate-900">
                  <span>{packet.targetLane}</span>
                  <span className="text-emerald-400 tabular-nums">
                    {(packet.oracleAlignmentScore * 100).toFixed(0)}% Alignment
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Deep Packet Telemetry & CDO Link (7 cols) */}
        <div className="lg:col-span-7 bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-4">
            <div>
              <div className="text-xs font-mono text-cyan-400">PACKET TELEMETRY & LIFECYCLE RECONSTRUCTION</div>
              <h3 className="text-lg font-bold text-white mt-0.5">{activePacket.packetId}</h3>
            </div>
            <div className="flex items-center gap-3 text-xs font-mono">
              <span className="text-slate-400">Target: <strong className="text-slate-200">{activePacket.targetLane}</strong></span>
              <span className="text-emerald-400 font-bold tabular-nums">
                {(activePacket.oracleAlignmentScore * 100).toFixed(0)}% Oracle Verified
              </span>
            </div>
          </div>

          {/* Metrics summary */}
          <div className="grid grid-cols-3 gap-3 text-xs font-mono">
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-slate-500 block text-[10px]">Total Latency:</span>
              <span className="text-cyan-300 font-bold text-sm tabular-nums">{activePacket.totalLatencyMs} ms</span>
            </div>
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-slate-500 block text-[10px]">Token Cost:</span>
              <span className="text-slate-200 font-bold text-sm tabular-nums">{activePacket.tokenConsumption} tokens</span>
            </div>
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-slate-500 block text-[10px]">Compute Charge:</span>
              <span className="text-emerald-400 font-bold text-sm tabular-nums">${activePacket.computeCostUsd.toFixed(4)}</span>
            </div>
          </div>

          {/* Decisions & Alternatives Rejected */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
            <div className="p-3.5 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
              <span className="text-cyan-400 font-bold text-[11px] block uppercase">Decisions Taken:</span>
              <ul className="space-y-1 text-slate-300">
                {activePacket.decisionsTaken.map((d, idx) => (
                  <li key={idx} className="flex items-start gap-1">
                    <span className="text-cyan-400">•</span>
                    <span>{d}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="p-3.5 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
              <span className="text-rose-400 font-bold text-[11px] block uppercase">Alternatives Rejected:</span>
              <ul className="space-y-1 text-slate-300">
                {activePacket.alternativesRejected.map((a, idx) => (
                  <li key={idx} className="flex items-start gap-1 text-slate-400">
                    <span className="text-rose-400">✕</span>
                    <span>{a}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Stage History Log */}
          <div className="space-y-2">
            <span className="text-xs font-mono font-bold text-slate-300 uppercase">Lifecycle Transit Log:</span>
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-2 text-xs font-mono max-h-48 overflow-y-auto">
              {activePacket.historyLog.map((log, idx) => (
                <div key={idx} className="flex items-start justify-between border-b border-slate-900 pb-1.5 last:border-0">
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="text-cyan-300 font-bold">{log.stage}</span>
                      <span className="text-slate-500 text-[10px]">by {log.agent}</span>
                      <span className="text-slate-500 text-[10px]">at {log.timestamp}</span>
                    </div>
                    <div className="text-slate-400 text-[11px]">{log.notes}</div>
                  </div>
                  <span className="text-slate-500 tabular-nums text-[10px]">{log.durationMs}ms</span>
                </div>
              ))}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
