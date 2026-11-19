import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  Cpu,
  Sparkles,
  Radio,
  Clock,
  Layers,
  FileCode,
  Send,
  HelpCircle,
  Coins,
  CheckCircle2,
  Lock,
} from 'lucide-react';
import { EstateTelemetry } from '../types';

interface HeaderProps {
  telemetry: EstateTelemetry;
  activeTab: 'cockpit' | 'lab' | 'telegram' | 'ledger';
  setActiveTab: (tab: 'cockpit' | 'lab' | 'telegram' | 'ledger') => void;
  geminiEnrichmentEnabled: boolean;
  setGeminiEnrichmentEnabled: (enabled: boolean) => void;
  totalModelSpendUsd: number;
  totalTokensEnriched: number;
  onOpenDofGateModal: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  telemetry,
  activeTab,
  setActiveTab,
  geminiEnrichmentEnabled,
  setGeminiEnrichmentEnabled,
  totalModelSpendUsd,
  totalTokensEnriched,
  onOpenDofGateModal,
}) => {
  const [utcTime, setUtcTime] = useState('');
  const [showCostExplainer, setShowCostExplainer] = useState(false);

  useEffect(() => {
    const update = () => {
      const now = new Date();
      setUtcTime(now.toUTCString().slice(17, 25) + ' UTC');
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="border-b border-zinc-800/80 bg-zinc-950/90 backdrop-blur-md sticky top-0 z-40">
      {/* Top Telemetry Ticker */}
      <div className="flex flex-wrap items-center justify-between border-b border-zinc-900 px-4 py-1.5 text-xs text-zinc-400">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 text-zinc-300 font-mono">
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="font-semibold text-zinc-100">GENESIS OPS COCKPIT</span>
            <span className="text-zinc-600">|</span>
            <Clock className="w-3.5 h-3.5 text-zinc-500" />
            <span>{utcTime || 'LIVE UTC'}</span>
          </div>

          {/* DOF-Gate Status */}
          <button
            onClick={onOpenDofGateModal}
            className={`flex items-center gap-1.5 px-2 py-0.5 rounded font-mono text-[11px] transition-colors border ${
              telemetry.dofGate.status === 'LOCKED_AWAITING_CREDENTIAL'
                ? 'bg-rose-950/50 border-rose-800/60 text-rose-300 hover:bg-rose-900/60'
                : 'bg-emerald-950/50 border-emerald-800/60 text-emerald-300 hover:bg-emerald-900/60'
            }`}
          >
            {telemetry.dofGate.status === 'LOCKED_AWAITING_CREDENTIAL' ? (
              <Lock className="w-3 h-3 text-rose-400" />
            ) : (
              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            )}
            <span>DOF-GATE: {telemetry.dofGate.status === 'LOCKED_AWAITING_CREDENTIAL' ? 'LOCKED (CREDENTIAL)' : 'UNBLOCKED'}</span>
          </button>

          {/* ARM VM Piper Lane */}
          <div className="hidden sm:flex items-center gap-1.5 px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 font-mono text-[11px] text-zinc-300">
            <Cpu className="w-3 h-3 text-cyan-400" />
            <span>ARM VM: 4 CORES ($0 ESTATE TTS)</span>
          </div>

          {/* Telegram Spooler Status */}
          <div className="hidden md:flex items-center gap-1.5 px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 font-mono text-[11px] text-zinc-300">
            <Radio className="w-3 h-3 text-emerald-400" />
            <span>SPOOLER: PERSISTENT</span>
          </div>
        </div>

        {/* Gemini Cost & Model Spend Explainer */}
        <div className="relative flex items-center gap-2 mt-1 sm:mt-0">
          <div
            className={`flex items-center gap-2 px-2.5 py-1 rounded-md border text-xs cursor-pointer transition-all ${
              geminiEnrichmentEnabled
                ? 'bg-purple-950/40 border-purple-500/50 text-purple-200'
                : 'bg-zinc-900 border-zinc-800 text-zinc-400'
            }`}
            onClick={() => setShowCostExplainer(!showCostExplainer)}
            title="Click for Gemini cost & token breakdown"
          >
            <Coins className="w-3.5 h-3.5 text-amber-400" />
            <span className="font-mono font-medium">
              Model Spend: ${totalModelSpendUsd.toFixed(5)}
            </span>
            <span className="text-[10px] px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-300 font-mono">
              {geminiEnrichmentEnabled ? 'Enrichment ON' : '$0 Heuristic Core'}
            </span>
            <HelpCircle className="w-3 h-3 text-zinc-500 hover:text-zinc-300" />
          </div>

          {/* Cost Explainer Modal / Dropdown */}
          {showCostExplainer && (
            <div className="absolute right-0 top-8 w-80 p-3.5 rounded-lg bg-zinc-900 border border-zinc-700 shadow-2xl z-50 text-xs text-zinc-300">
              <div className="flex items-center justify-between pb-2 border-b border-zinc-800 mb-2">
                <span className="font-semibold text-zinc-100 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                  Is Gemini Enrichment Costly?
                </span>
                <button
                  onClick={() => setShowCostExplainer(false)}
                  className="text-zinc-500 hover:text-zinc-200 text-xs"
                >
                  ✕
                </button>
              </div>
              <p className="text-zinc-300 mb-2 leading-relaxed">
                <strong className="text-emerald-400">Practically zero (~1/100 of a cent).</strong>
                Because our <span className="text-zinc-100">dream-cycle extractive core</span> already strips 99% of noisy agent JSONL before Gemini sees it, each brief sends only ~500 tokens and generates ~200 tokens.
              </p>
              <div className="bg-zinc-950 p-2 rounded border border-zinc-800 space-y-1 font-mono text-[11px] mb-2">
                <div className="flex justify-between text-zinc-400">
                  <span>Gemini 2.5 Flash Input:</span>
                  <span className="text-zinc-200">$0.075 / 1M tokens</span>
                </div>
                <div className="flex justify-between text-zinc-400">
                  <span>Gemini 2.5 Flash Output:</span>
                  <span className="text-zinc-200">$0.30 / 1M tokens</span>
                </div>
                <div className="flex justify-between text-purple-400 font-semibold pt-1 border-t border-zinc-800">
                  <span>Cost per 60-90s brief:</span>
                  <span>~$0.00011 USD</span>
                </div>
                <div className="flex justify-between text-emerald-400">
                  <span>10,000 briefs cost:</span>
                  <span>~$1.10 USD (Free Tier: $0)</span>
                </div>
              </div>
              <p className="text-[11px] text-zinc-400">
                • <strong>Toggle OFF</strong>: Pure $0 estate-side heuristic synthesis.<br />
                • <strong>Toggle ON</strong>: High-cadence executive briefing dialogue with verifiable SHA-256 receipts.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Main Bar with Navigation & Quick Controls */}
      <div className="px-4 py-2.5 flex flex-wrap items-center justify-between gap-3">
        {/* Brand & Tagline */}
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-indigo-500 via-sky-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-sky-500/20">
            <Radio className="w-5 h-5 text-white animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-white tracking-wide">
                GENESIS <span className="text-sky-400 font-mono text-sm">VOICE SURFACE</span>
              </h1>
              <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-zinc-800 text-zinc-300 border border-zinc-700">
                v2.4-ESTATE
              </span>
            </div>
            <p className="text-xs text-zinc-400 hidden sm:block">
              Voice-First Ops Cockpit for Autonomous Agent Legions • 60–90s Briefs & Telegram Spooler
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-1 bg-zinc-900/90 p-1 rounded-lg border border-zinc-800">
          <button
            onClick={() => setActiveTab('cockpit')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === 'cockpit'
                ? 'bg-zinc-800 text-white shadow-sm border border-zinc-700'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
            }`}
          >
            <Layers className="w-3.5 h-3.5 text-sky-400" />
            <span>Legions (5)</span>
          </button>

          <button
            onClick={() => setActiveTab('lab')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === 'lab'
                ? 'bg-zinc-800 text-white shadow-sm border border-zinc-700'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
            }`}
          >
            <FileCode className="w-3.5 h-3.5 text-amber-400" />
            <span>Extractive Lab ($0)</span>
          </button>

          <button
            onClick={() => setActiveTab('telegram')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === 'telegram'
                ? 'bg-zinc-800 text-white shadow-sm border border-zinc-700'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
            }`}
          >
            <Send className="w-3.5 h-3.5 text-emerald-400" />
            <span>Telegram Spooler</span>
          </button>

          <button
            onClick={() => setActiveTab('ledger')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === 'ledger'
                ? 'bg-zinc-800 text-white shadow-sm border border-zinc-700'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
            }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-purple-400" />
            <span>Receipt Ledger</span>
          </button>
        </div>

        {/* Gemini Enrichment Switch Toggle */}
        <div className="flex items-center gap-2">
          <div
            onClick={() => setGeminiEnrichmentEnabled(!geminiEnrichmentEnabled)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border cursor-pointer select-none transition-all ${
              geminiEnrichmentEnabled
                ? 'bg-gradient-to-r from-purple-950/80 to-indigo-950/80 border-purple-500/60 text-purple-200 shadow-md shadow-purple-900/20'
                : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:border-zinc-700'
            }`}
          >
            <Sparkles className={`w-4 h-4 ${geminiEnrichmentEnabled ? 'text-purple-400 animate-spin' : 'text-zinc-500'}`} />
            <div className="text-left">
              <div className="flex items-center gap-1.5 text-xs font-semibold leading-none">
                <span>Gemini Enrichment</span>
                <span
                  className={`text-[9px] px-1 py-0.5 rounded uppercase font-mono ${
                    geminiEnrichmentEnabled ? 'bg-purple-800/60 text-purple-200' : 'bg-zinc-800 text-zinc-400'
                  }`}
                >
                  {geminiEnrichmentEnabled ? 'ON' : 'OFF'}
                </span>
              </div>
              <div className="text-[10px] text-zinc-400 font-mono mt-0.5">
                {geminiEnrichmentEnabled ? 'gemini-2.5-flash (~$0.0001)' : '$0.00 Estate Heuristics'}
              </div>
            </div>
            {/* Toggle switch visual */}
            <div
              className={`w-9 h-5 rounded-full p-0.5 transition-colors ml-1 ${
                geminiEnrichmentEnabled ? 'bg-purple-600' : 'bg-zinc-700'
              }`}
            >
              <div
                className={`w-4 h-4 rounded-full bg-white transition-transform ${
                  geminiEnrichmentEnabled ? 'translate-x-4' : 'translate-x-0'
                }`}
              />
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
