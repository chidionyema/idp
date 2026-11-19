/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  EstateComponent,
  INITIAL_ESTATE_COMPONENTS,
} from '../lib/protocolEngine.ts';
import {
  Box,
  Layers,
  ShieldAlert,
  Play,
  Lock,
  Unlock,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  Cpu,
} from 'lucide-react';

export const EstateIntelligenceSurface: React.FC = () => {
  const [components, setComponents] = useState<EstateComponent[]>(INITIAL_ESTATE_COMPONENTS);
  const [selectedComponentId, setSelectedComponentId] = useState<string>('genesis-kernel');
  const [agentDebugLock, setAgentDebugLock] = useState<boolean>(true); // Locked by default
  const [isRunningDiagnostics, setIsRunningDiagnostics] = useState<boolean>(false);
  const [lastDiagnosticRun, setLastDiagnosticRun] = useState<string>('2 minutes ago');

  const activeComponent =
    components.find((c) => c.id === selectedComponentId) || components[0];

  const handleRunPass0Diagnostics = () => {
    setIsRunningDiagnostics(true);
    setTimeout(() => {
      setIsRunningDiagnostics(false);
      setLastDiagnosticRun('Just now');
      setComponents((prev) =>
        prev.map((c) => ({
          ...c,
          status: 'HEALTHY',
          fmeaAtlas: c.fmeaAtlas.map((f) => ({
            ...f,
            lastTested: 'Just now',
            diagnosticStatus: 'PASS',
          })),
        }))
      );
    }, 800);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 sm:p-8">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-mono text-cyan-400">
              <Box className="w-4 h-4 text-cyan-400" />
              <span>ZERO EXPLORATORY DEBUGGING · SELF-DESCRIBING COMPONENT CONTRACTS</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              Estate Intelligence & FMEA Failure Atlas
            </h1>
            <p className="text-slate-400 text-sm max-w-2xl">
              All estate components expose formal machine-readable contracts, interfaces, and dependencies. Failure modes are pre-mapped with automated Pass 0 diagnostics.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            {/* AGENT_DEBUG_LOCK toggle */}
            <button
              onClick={() => setAgentDebugLock(!agentDebugLock)}
              className={`flex items-center gap-2 px-3.5 py-2 text-xs font-mono font-semibold rounded-lg border transition-all cursor-pointer ${
                agentDebugLock
                  ? 'bg-slate-950 text-slate-300 border-slate-700 hover:border-slate-500'
                  : 'bg-amber-950 text-amber-300 border-amber-700 hover:bg-amber-900/60'
              }`}
            >
              {agentDebugLock ? (
                <>
                  <Lock className="w-4 h-4 text-emerald-400" />
                  <span>AGENT_DEBUG_LOCK: ENGAGED</span>
                </>
              ) : (
                <>
                  <Unlock className="w-4 h-4 text-amber-400" />
                  <span>AGENT_DEBUG_LOCK: UNLOCKED</span>
                </>
              )}
            </button>

            {/* Run Pass 0 Diagnostics */}
            <button
              onClick={handleRunPass0Diagnostics}
              disabled={isRunningDiagnostics}
              className="flex items-center justify-center gap-2 px-4 py-2 text-xs font-semibold text-slate-950 bg-gradient-to-r from-cyan-400 to-blue-400 hover:from-cyan-300 hover:to-blue-300 rounded-lg transition-all shadow cursor-pointer disabled:opacity-50"
            >
              <Play className={`w-3.5 h-3.5 ${isRunningDiagnostics ? 'animate-spin' : ''}`} />
              <span>{isRunningDiagnostics ? 'Running Pass 0...' : 'Run Pass 0 Diagnostics'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Grid: Components Selector & Deep Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Column: Component Catalog (4 cols) */}
        <div className="lg:col-span-4 space-y-3">
          <div className="text-xs font-mono text-slate-400 uppercase tracking-wider">
            Self-Describing Modules ({components.length})
          </div>

          <div className="space-y-2">
            {components.map((comp) => (
              <div
                key={comp.id}
                onClick={() => setSelectedComponentId(comp.id)}
                className={`p-4 rounded-xl border transition-all cursor-pointer ${
                  selectedComponentId === comp.id
                    ? 'bg-slate-800/90 border-cyan-400 shadow-md'
                    : 'bg-slate-950/70 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-white">{comp.id}</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 font-semibold">
                    {comp.status}
                  </span>
                </div>
                <div className="text-xs text-slate-300 font-medium mt-1">{comp.name}</div>
                <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 mt-2 pt-2 border-t border-slate-900">
                  <span>{comp.contractVersion}</span>
                  <span>{comp.fmeaAtlas.length} FMEA modes</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: Selected Component Contract & FMEA Atlas (8 cols) */}
        <div className="lg:col-span-8 bg-slate-900/60 border border-slate-800 rounded-xl p-6 sm:p-8 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div>
              <div className="text-xs font-mono text-cyan-400">{activeComponent.contractVersion} · {activeComponent.runtime}</div>
              <h2 className="text-xl font-bold text-white mt-0.5">{activeComponent.name}</h2>
            </div>
            <div className="text-xs font-mono text-slate-400">
              Pass 0 Diagnostic: <span className="text-slate-200">{lastDiagnosticRun}</span>
            </div>
          </div>

          {/* Machine-readable Contract & Dependencies */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Interfaces */}
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
              <span className="text-xs font-mono font-bold text-slate-300 uppercase">Exposed Interfaces</span>
              <div className="space-y-1">
                {activeComponent.interfaces.map((iface, idx) => (
                  <div key={idx} className="text-xs font-mono text-cyan-300 bg-slate-900 px-2 py-1 rounded border border-slate-800 truncate">
                    {iface}
                  </div>
                ))}
              </div>
            </div>

            {/* Dependency Graph */}
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
              <span className="text-xs font-mono font-bold text-slate-300 uppercase">Dependency Lineage</span>
              <div className="text-xs font-mono space-y-1.5">
                <div>
                  <span className="text-slate-500 block text-[10px]">Upstream Dependencies:</span>
                  <span className="text-slate-300">{activeComponent.upstreamDeps.join(', ')}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px]">Downstream Consumers:</span>
                  <span className="text-slate-300">{activeComponent.downstreamDeps.join(', ')}</span>
                </div>
              </div>
            </div>
          </div>

          {/* FMEA Failure Atlas */}
          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between">
              <div className="text-xs font-mono font-bold text-slate-300 uppercase flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-cyan-400" />
                <span>Pre-Mapped Failure Atlas & Pass 0 Diagnostics</span>
              </div>
              <span className="text-xs font-mono text-emerald-400">All Invariants Pass</span>
            </div>

            <div className="space-y-3">
              {activeComponent.fmeaAtlas.map((item, idx) => (
                <div
                  key={idx}
                  className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="text-sm font-bold text-white flex items-center gap-2">
                      <span>{item.failureMode}</span>
                      <span className={`text-[10px] font-mono px-2 py-0.2 rounded font-semibold ${
                        item.severity === 'CRITICAL'
                          ? 'bg-rose-950 text-rose-300 border border-rose-800'
                          : item.severity === 'HIGH'
                          ? 'bg-amber-950 text-amber-300 border border-amber-800'
                          : 'bg-blue-950 text-blue-300 border border-blue-800'
                      }`}>
                        {item.severity}
                      </span>
                    </div>

                    <span className="text-xs font-mono text-emerald-400 flex items-center gap-1 font-semibold">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      {item.diagnosticStatus}
                    </span>
                  </div>

                  <div className="text-xs text-slate-300">
                    <span className="text-slate-500">Autonomous Mitigation: </span>
                    {item.mitigation}
                  </div>

                  <div className="text-[11px] font-mono text-cyan-400/90 pt-1 border-t border-slate-900 flex justify-between">
                    <span>Diagnostic Test: {item.pass0Diagnostic}</span>
                    <span className="text-slate-500">{item.lastTested}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
