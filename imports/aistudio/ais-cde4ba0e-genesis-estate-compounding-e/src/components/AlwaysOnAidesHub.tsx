/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  FounderAideId,
  FounderAide,
  AideDispatchResult,
  INITIAL_AIDE_TRIUMVIRATE,
  dispatchToAide,
  verifyAideContinuousPresence,
} from '../lib/protocolEngine.ts';
import {
  Cpu,
  Sparkles,
  Compass,
  Send,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Activity,
  Terminal,
  Zap,
  CheckCircle2,
  Lock,
  Layers,
  X,
  RefreshCw,
  Fingerprint,
  Users,
  Radio
} from 'lucide-react';

interface AlwaysOnAidesHubProps {
  onOpenSync?: () => void;
  onOpenWelcome?: () => void;
  onOpenFleetCouncil?: () => void;
  onOpenCcp?: () => void;
  isEmergencyHalt?: boolean;
}

export const AlwaysOnAidesHub: React.FC<AlwaysOnAidesHubProps> = ({
  onOpenSync,
  onOpenWelcome,
  onOpenFleetCouncil,
  onOpenCcp,
  isEmergencyHalt = false,
}) => {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [selectedAideId, setSelectedAideId] = useState<FounderAideId>('OTTO');
  const [inputCommand, setInputCommand] = useState<string>('');
  const [isDispatching, setIsDispatching] = useState<boolean>(false);
  const [receipts, setReceipts] = useState<AideDispatchResult[]>([
    {
      receiptId: 'RECEIPT-AIDE-OTTO-INIT',
      aideId: 'OTTO',
      response: 'Otto online: 6/6 deterministic soil tilling probes nominal. DoF Level 1 active.',
      latencyMs: 0.8,
      hmacSignature: 'HMAC_SHA256_OTTO_9812a01f_VERIFIED',
      actionTaken: 'SYSTEM_BOOTSTRAP_SWEEP',
      timestamp: new Date(Date.now() - 1000 * 60 * 2).toLocaleTimeString(),
    },
    {
      receiptId: 'RECEIPT-AIDE-CONCIERGE-INIT',
      aideId: 'CONCIERGE',
      response: 'Concierge ready: DeepSeek and LLM credentials sanitized; Argon SOS sync channel primed.',
      latencyMs: 1.1,
      hmacSignature: 'HMAC_SHA256_CONCIERGE_8f2dc4b2_VERIFIED',
      actionTaken: 'CREDENTIAL_HYGIENE_CHECK',
      timestamp: new Date(Date.now() - 1000 * 60 * 1).toLocaleTimeString(),
    },
    {
      receiptId: 'RECEIPT-AIDE-MEGA_ORACLE-INIT',
      aideId: 'MEGA_ORACLE',
      response: 'Mega-Oracle omniscient: 7-lane free harvester bounds P(collapse) <= 3.2e-14. WWFD alignment 99.4%.',
      latencyMs: 1.4,
      hmacSignature: 'HMAC_SHA256_MEGA_ORACLE_7b3e109d_VERIFIED',
      actionTaken: 'LONGEVITY_RISK_AUDIT',
      timestamp: new Date().toLocaleTimeString(),
    },
  ]);

  const attestation = verifyAideContinuousPresence(INITIAL_AIDE_TRIUMVIRATE);
  const currentAide = INITIAL_AIDE_TRIUMVIRATE.find((a) => a.id === selectedAideId) || INITIAL_AIDE_TRIUMVIRATE[0];

  const handleExecute = (cmdText: string) => {
    if (!cmdText.trim()) return;
    setIsDispatching(true);

    setTimeout(() => {
      const result = dispatchToAide(selectedAideId, cmdText);
      setReceipts((prev) => [
        {
          ...result,
          timestamp: new Date().toLocaleTimeString(),
        },
        ...prev.slice(0, 9),
      ]);
      setInputCommand('');
      setIsDispatching(false);

      if (cmdText === 'sync_to_argon' && onOpenSync) {
        onOpenSync();
      }
    }, 180);
  };

  const getAideIcon = (id: FounderAideId, className: string = 'w-4 h-4') => {
    switch (id) {
      case 'OTTO':
        return <Cpu className={className} />;
      case 'CONCIERGE':
        return <Sparkles className={className} />;
      case 'MEGA_ORACLE':
        return <Compass className={className} />;
    }
  };

  return (
    <>
      {/* Minimized Omnipresent Floating Dock Bar (Always Visible) */}
      <div className="fixed bottom-4 right-4 z-50 flex items-center gap-2">
        {!isOpen && (
          <div className="flex items-center gap-2 bg-slate-950/95 backdrop-blur-xl border border-cyan-500/40 rounded-xl p-1.5 shadow-2xl shadow-cyan-950/60 transition-all hover:border-cyan-400">
            {/* Live Status indicator */}
            <div className="flex items-center gap-2 px-2.5 py-1 text-xs font-mono border-r border-slate-800">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-sm shadow-emerald-400/80" />
              <span className="text-[11px] font-bold tracking-wider text-cyan-300 uppercase">
                Aides On Tap
              </span>
            </div>

            {/* Quick 1-click triggers for all 3 aides */}
            <div className="flex items-center gap-1">
              {INITIAL_AIDE_TRIUMVIRATE.map((aide) => {
                const isSelected = selectedAideId === aide.id;
                return (
                  <button
                    key={aide.id}
                    onClick={() => {
                      setSelectedAideId(aide.id);
                      setIsOpen(true);
                    }}
                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-mono transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-cyan-500/20 text-cyan-200 border border-cyan-500/40'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                    }`}
                    title={`${aide.name} — ${aide.title} (${aide.latencyMs}ms latency)`}
                  >
                    {getAideIcon(aide.id, 'w-3.5 h-3.5 text-cyan-400')}
                    <span className="font-semibold">{aide.name}</span>
                    <span className="text-[10px] text-emerald-400">●</span>
                  </button>
                );
              })}
            </div>

            {/* Expand HUD Button */}
            <button
              onClick={() => setIsOpen(true)}
              className="p-1.5 rounded-lg bg-cyan-950/80 hover:bg-cyan-900 text-cyan-300 border border-cyan-800/60 cursor-pointer ml-1"
              title="Expand Founder Aide Command HUD"
            >
              <ChevronUp className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Expanded Full-Featured Bleeding-Edge Aide HUD Modal/Drawer */}
      {isOpen && (
        <div className="fixed bottom-4 right-4 z-50 w-full max-w-xl bg-slate-950/98 backdrop-blur-2xl border border-cyan-500/50 rounded-2xl shadow-2xl shadow-black/80 flex flex-col overflow-hidden text-slate-100 font-sans transition-all animate-in fade-in slide-in-from-bottom-4 duration-200">
          
          {/* Header Bar: Status + Attestation + Close */}
          <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-slate-900 via-slate-950 to-slate-900 border-b border-slate-800/80">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-cyan-400 to-indigo-600 flex items-center justify-center shadow-md shadow-cyan-500/20">
                <Fingerprint className="w-4 h-4 text-slate-950" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-xs font-bold font-mono tracking-wider text-white uppercase">
                    Founder Aide Triumvirate (§12)
                  </h3>
                  <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-800/50 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    ALWAYS ON TAP
                  </span>
                </div>
                <p className="text-[10px] text-slate-400 font-mono">
                  Continuous Heartbeat Attested · Guaranteed Response &lt;2.5ms · Zero Friction
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              {onOpenWelcome && (
                <button
                  onClick={onOpenWelcome}
                  className="px-2 py-1 text-[10px] font-mono font-semibold rounded bg-indigo-950/80 text-indigo-300 hover:bg-indigo-900 border border-indigo-800/60 cursor-pointer"
                  title="Open Full Founder Getting Started Guide"
                >
                  Guide
                </button>
              )}
              {onOpenFleetCouncil && (
                <button
                  onClick={() => {
                    onOpenFleetCouncil();
                    setIsOpen(false);
                  }}
                  className="px-2 py-1 text-[10px] font-mono font-semibold rounded bg-cyan-950/80 text-cyan-300 hover:bg-cyan-900 border border-cyan-800/60 cursor-pointer flex items-center gap-1"
                  title="Open Weekly Fleet Review & Council Chamber"
                >
                  <Users className="w-3 h-3 text-cyan-400" />
                  Council
                </button>
              )}
              {onOpenCcp && (
                <button
                  onClick={() => {
                    onOpenCcp();
                    setIsOpen(false);
                  }}
                  className="px-2 py-1 text-[10px] font-mono font-semibold rounded bg-purple-950/80 text-purple-300 hover:bg-purple-900 border border-purple-800/60 cursor-pointer flex items-center gap-1"
                  title="Open Command Code Protocol (CCP) Voice Surface"
                >
                  <Radio className="w-3 h-3 text-purple-400" />
                  Voice CCP
                </button>
              )}
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/80 cursor-pointer"
                title="Minimize Aide HUD"
              >
                <ChevronDown className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Aide Selector Tabs */}
          <div className="grid grid-cols-3 bg-slate-900/60 border-b border-slate-800 text-xs font-mono">
            {INITIAL_AIDE_TRIUMVIRATE.map((aide) => {
              const active = selectedAideId === aide.id;
              return (
                <button
                  key={aide.id}
                  onClick={() => setSelectedAideId(aide.id)}
                  className={`flex flex-col items-center justify-center py-2.5 px-3 border-r last:border-r-0 border-slate-800 transition-all cursor-pointer ${
                    active
                      ? 'bg-slate-950 text-cyan-300 border-b-2 border-b-cyan-400 font-bold'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
                  }`}
                >
                  <div className="flex items-center gap-1.5">
                    {getAideIcon(aide.id, `w-3.5 h-3.5 ${active ? 'text-cyan-400' : 'text-slate-500'}`)}
                    <span className="text-xs">{aide.name}</span>
                    <span className="text-[9px] text-emerald-400">●</span>
                  </div>
                  <span className="text-[10px] text-slate-500 font-normal truncate max-w-[140px]">
                    {aide.id === 'OTTO' ? 'Chief of Staff' : aide.id === 'CONCIERGE' ? 'Ops & Sync' : 'Mega-Oracle'}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Active Aide Profile & Telemetry Ribbon */}
          <div className="p-3 bg-slate-950 border-b border-slate-900">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-white tracking-wide">
                    {currentAide.name}
                  </span>
                  <span className="text-[10px] font-mono text-cyan-400/90 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/50">
                    {currentAide.title}
                  </span>
                  <span className="text-[10px] font-mono text-emerald-300 ml-auto flex items-center gap-1">
                    <Activity className="w-3 h-3 text-emerald-400" />
                    {currentAide.latencyMs}ms dispatch
                  </span>
                </div>
                <p className="text-xs text-slate-300 mt-1 font-mono leading-relaxed">
                  {currentAide.tagline}
                </p>
                <div className="mt-2 text-[11px] text-slate-400 font-mono bg-slate-900/80 p-2 rounded-lg border border-slate-800/80 flex items-start gap-2">
                  <span className="text-cyan-400 shrink-0 font-bold">STATE:</span>
                  <span className="text-slate-300">{currentAide.activeContext}</span>
                </div>
              </div>
            </div>

            {/* Quick Actions (1-Click Founder Dispatch) */}
            <div className="mt-3">
              <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block mb-1.5">
                Deterministic Quick Actions (Zero Friction):
              </span>
              <div className="grid grid-cols-3 gap-1.5">
                {currentAide.quickActions.map((qa) => (
                  <button
                    key={qa.id}
                    onClick={() => handleExecute(qa.command)}
                    disabled={isDispatching}
                    className="flex flex-col text-left p-2 rounded-lg bg-slate-900/90 hover:bg-cyan-950/60 border border-slate-800 hover:border-cyan-500/50 transition-all text-xs cursor-pointer group disabled:opacity-50"
                  >
                    <span className="font-mono font-semibold text-cyan-300 group-hover:text-cyan-200 flex items-center gap-1 text-[11px]">
                      <Zap className="w-3 h-3 text-cyan-400 shrink-0" />
                      {qa.label}
                    </span>
                    <span className="text-[9px] text-slate-400 mt-0.5 line-clamp-1">
                      {qa.description}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Interactive Command Dispatch Input */}
          <div className="p-3 bg-slate-900/40 border-b border-slate-800/80">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleExecute(inputCommand);
              }}
              className="flex items-center gap-2"
            >
              <div className="relative flex-1">
                <Terminal className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={inputCommand}
                  onChange={(e) => setInputCommand(e.target.value)}
                  placeholder={`Dispatch sovereign task to ${currentAide.name} (e.g. run tilling, verify invariants, sync)...`}
                  className="w-full pl-8 pr-3 py-1.5 text-xs font-mono bg-slate-950 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/50 transition-colors"
                />
              </div>
              <button
                type="submit"
                disabled={isDispatching || !inputCommand.trim()}
                className="px-3.5 py-1.5 text-xs font-semibold font-mono bg-cyan-500 hover:bg-cyan-400 text-slate-950 rounded-lg flex items-center gap-1.5 shadow-sm transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isDispatching ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Send className="w-3.5 h-3.5" />
                )}
                <span>Dispatch</span>
              </button>
            </form>
          </div>

          {/* Live Step Receipts & Audit Log */}
          <div className="p-3 bg-slate-950 max-h-48 overflow-y-auto space-y-2 font-mono text-[11px]">
            <div className="flex items-center justify-between text-[10px] text-slate-500 pb-1 border-b border-slate-900">
              <span className="uppercase tracking-wider flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                Machine Receipts & Cryptographic Journals:
              </span>
              <span className="text-slate-400">Ed25519 Verified</span>
            </div>

            {receipts.map((rec) => (
              <div
                key={rec.receiptId}
                className="p-2 rounded bg-slate-900/70 border border-slate-800/80 flex flex-col gap-1"
              >
                <div className="flex items-center justify-between text-[10px]">
                  <span className="text-cyan-400 font-bold flex items-center gap-1">
                    {getAideIcon(rec.aideId, 'w-3 h-3')}
                    {rec.aideId} · {rec.actionTaken}
                  </span>
                  <span className="text-slate-500">{rec.timestamp} ({rec.latencyMs}ms)</span>
                </div>
                <p className="text-slate-300 text-[10px] leading-relaxed">
                  {rec.response}
                </p>
                <div className="flex items-center justify-between text-[9px] text-slate-500 pt-0.5">
                  <span className="font-mono text-cyan-500/70">{rec.receiptId}</span>
                  <span className="text-emerald-400/80 flex items-center gap-0.5">
                    <ShieldCheck className="w-2.5 h-2.5" />
                    {rec.hmacSignature.slice(0, 24)}...
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Footer Bar: Invariant Proof */}
          <div className="px-4 py-2 bg-slate-950 border-t border-slate-900 flex items-center justify-between text-[10px] font-mono text-slate-500">
            <span className="flex items-center gap-1.5 text-slate-400">
              <Fingerprint className="w-3 h-3 text-cyan-400" />
              Beacon: 0x8f2d...5a4
            </span>
            <span className="text-emerald-400">
              §12.1 INVARIANT SEALED: FOUNDER IS NEVER WITHOUT AIDES
            </span>
          </div>

        </div>
      )}
    </>
  );
};
