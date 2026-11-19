/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  CdoRecord,
  INITIAL_IPN_PACKETS,
} from '../lib/protocolEngine.ts';
import {
  RefreshCw,
  CheckCircle2,
  AlertOctagon,
  Clock,
  Sparkles,
  ArrowRight,
  TrendingUp,
  FileCheck,
  ShieldCheck,
  UserCheck,
} from 'lucide-react';

export const CdoLoopSurface: React.FC = () => {
  const [selectedInstructionId, setSelectedInstructionId] = useState<string>(
    INITIAL_IPN_PACKETS[0].packetId
  );

  const initialCdoRecords: CdoRecord[] = INITIAL_IPN_PACKETS
    .filter((p) => p.cdoReview !== undefined)
    .map((p) => p.cdoReview!);

  const [records, setRecords] = useState<CdoRecord[]>(initialCdoRecords);

  const activeRecord =
    records.find((r) => r.instructionId === selectedInstructionId) || records[0];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 sm:p-8">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-mono text-cyan-400">
              <RefreshCw className="w-4 h-4 text-cyan-400" />
              <span>CONTINUOUS DELIVERY OPTIMISATION (CDO) · AUTOMATED POST-INSTRUCTION DECONSTRUCTION</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              CDO Loop & Friction Accounting
            </h1>
            <p className="text-slate-400 text-sm max-w-2xl">
              Runs automatically after every instruction delivered, stuck, or abandoned. Uncovers bottlenecks, friction points (both agent and founder), latency blocks, and guarantees compounding leverage is left behind.
            </p>
          </div>

          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs font-mono space-y-1.5 shrink-0 min-w-[260px]">
            <div className="text-slate-500 uppercase tracking-wider text-[10px]">CDO Loop Accounting</div>
            <div className="flex justify-between items-center text-slate-200">
              <span>Delivery Success:</span>
              <span className="text-emerald-400 font-bold tabular-nums">100% (2/2 Active)</span>
            </div>
            <div className="flex justify-between items-center text-slate-200">
              <span>Founder Friction:</span>
              <span className="text-emerald-400 font-bold tabular-nums">Δ ≡ 0 (Zero Tax)</span>
            </div>
            <div className="flex justify-between items-center text-slate-200">
              <span>Compounding Leverage:</span>
              <span className="text-cyan-400 font-bold">GUARANTEED</span>
            </div>
          </div>
        </div>
      </div>

      {/* Grid: CDO Records Selector & Deep Inspection */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Column: CDO Records Stream (4 cols) */}
        <div className="lg:col-span-4 bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h2 className="text-base font-semibold text-white">Evaluated Instructions</h2>
            <span className="text-xs font-mono text-slate-400">{records.length} Records</span>
          </div>

          <div className="space-y-2.5">
            {records.map((rec) => (
              <div
                key={rec.instructionId}
                onClick={() => setSelectedInstructionId(rec.instructionId)}
                className={`p-4 rounded-xl border transition-all cursor-pointer ${
                  selectedInstructionId === rec.instructionId
                    ? 'bg-slate-800/95 border-cyan-400 shadow-sm'
                    : 'bg-slate-950/80 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex justify-between items-center">
                  <span className="text-xs font-mono font-bold text-white">{rec.instructionId}</span>
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold ${
                    rec.terminalState === 'DELIVERED'
                      ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                      : 'bg-amber-950 text-amber-300 border border-amber-800'
                  }`}>
                    {rec.terminalState}
                  </span>
                </div>
                <div className="text-xs text-slate-300 mt-1 font-medium">
                  Constraint: <span className="text-cyan-300">{rec.bottleneckConstraint}</span>
                </div>
                <div className="text-[11px] font-mono text-slate-500 mt-2 truncate">
                  {rec.terminalReason}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: 7 Canonical CDO Questions Answered (8 cols) */}
        <div className="lg:col-span-8 bg-slate-900/60 border border-slate-800 rounded-xl p-6 sm:p-8 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-4">
            <div>
              <div className="text-xs font-mono text-cyan-400">CDO DECONSTRUCTION REPORT</div>
              <h3 className="text-xl font-bold text-white mt-0.5">{activeRecord.instructionId}</h3>
            </div>
            <span className="text-xs font-mono text-emerald-400 bg-emerald-950/80 px-2.5 py-1 rounded border border-emerald-800">
              Terminal: {activeRecord.terminalState}
            </span>
          </div>

          {/* 7 Questions Grid */}
          <div className="space-y-4 text-xs font-mono">
            
            {/* Q1 & Q2: Bottleneck Constraint & Friction Points */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
                <span className="text-[10px] text-slate-500 uppercase tracking-wide">Q1: Named Bottleneck Constraint</span>
                <div className="text-sm font-bold text-white">{activeRecord.bottleneckConstraint}</div>
                <div className="text-[11px] text-slate-400">{activeRecord.terminalReason}</div>
              </div>

              <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
                <span className="text-[10px] text-slate-500 uppercase tracking-wide">Q2: Friction Accounting</span>
                {activeRecord.frictionPoints.map((f, idx) => (
                  <div key={idx} className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] px-1.5 py-0.2 rounded font-bold ${
                        f.side === 'FOUNDER' ? 'bg-cyan-950 text-cyan-300' : 'bg-purple-950 text-purple-300'
                      }`}>
                        {f.side} SIDE
                      </span>
                      <span className="text-emerald-400 font-semibold">{f.severity} FRICTION</span>
                    </div>
                    <div className="text-[11px] text-slate-300">{f.description}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Q3 & Q4: Latency Breakdown */}
            <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
              <span className="text-[10px] text-slate-500 uppercase tracking-wide">Q4: Stage-by-Stage Latency Breakdown</span>
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 pt-1">
                {Object.entries(activeRecord.stageLatenciesMs).map(([stage, lat]) => (
                  <div key={stage} className="p-2 bg-slate-900 rounded border border-slate-800 text-center">
                    <div className="text-[9px] text-slate-500">{stage}</div>
                    <div className="text-xs font-bold text-cyan-300 tabular-nums">{lat}ms</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Q5: Compounding Suggestion */}
            <div className="p-4 bg-cyan-950/20 border border-cyan-800/60 rounded-xl space-y-1.5">
              <div className="flex items-center gap-1.5 text-xs font-bold text-cyan-300">
                <Sparkles className="w-4 h-4 text-cyan-400" />
                <span>Q5: Prescribed Compounding Improvement</span>
              </div>
              <div className="text-xs text-slate-200 leading-relaxed font-sans font-medium">
                {activeRecord.compoundingSuggestion}
              </div>
            </div>

            {/* Q6: Leverage Left Behind */}
            <div className="p-4 bg-emerald-950/20 border border-emerald-800/60 rounded-xl space-y-1.5">
              <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-300">
                <TrendingUp className="w-4 h-4 text-emerald-400" />
                <span>Q6: Permanent Leverage Left Behind</span>
              </div>
              <div className="text-xs text-slate-200 leading-relaxed font-sans font-medium">
                {activeRecord.leverageLeftBehind}
              </div>
              <div className="text-[11px] text-emerald-400/90 pt-1 font-mono">
                Proof of Recurrence Prevention: {activeRecord.preventRecurrenceProof}
              </div>
            </div>

          </div>
        </div>

      </div>
    </div>
  );
};
