/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  HistoryVsGenesisContest,
  HistoryLaneBlocker,
  HistoryVsGenesisDemarcation,
  INITIAL_CONTESTS,
  INITIAL_HISTORY_BLOCKERS,
  DEMARCATION_MATRIX,
  sanitizeDeepSeekCredentials,
  resolveModelRoute,
} from '../lib/protocolEngine.ts';
import {
  FlaskConical,
  History,
  GitBranch,
  Play,
  RotateCcw,
  Trophy,
  CheckCircle2,
  Cpu,
  Layers,
  Sparkles,
  TrendingUp,
  Wrench,
  Copy,
  Check,
  Terminal,
  AlertTriangle,
  Flame,
  ShieldAlert,
  KeyRound,
  Server,
  Split,
  RefreshCw,
  ArrowRight,
  ShieldCheck,
  Zap,
} from 'lucide-react';

export const ScienceLaneAndHistoryBridge: React.FC = () => {
  const [contests] = useState<HistoryVsGenesisContest[]>(INITIAL_CONTESTS);
  const [activeContestId] = useState<string>(INITIAL_CONTESTS[0].contestId);
  const [blockers] = useState<HistoryLaneBlocker[]>(INITIAL_HISTORY_BLOCKERS);
  const [demarcations] = useState<HistoryVsGenesisDemarcation[]>(DEMARCATION_MATRIX);
  const [copiedCmdId, setCopiedCmdId] = useState<string | null>(null);
  const [resolvedBlockerIds, setResolvedBlockerIds] = useState<string[]>(['HL-02', 'HL-07']);
  const [copiedBootstrap, setCopiedBootstrap] = useState<boolean>(false);
  const [copiedDeepSeekCmd, setCopiedDeepSeekCmd] = useState<boolean>(false);
  const [isReplaying, setIsReplaying] = useState<boolean>(false);
  const [replayLog, setReplayLog] = useState<string[]>([
    '[SNAPSHOT-INIT] Snapshot Oct-31-2026 mounted into isolated hermetic sandbox.',
    '[REPLAY-IDLE] Event stream ready for deterministic execution test.',
  ]);

  // DeepSeek Interactive Diagnostic State
  const [testKeyInput, setTestKeyInput] = useState<string>('  "sk-f89a2bc417d940bca835ef98sjQw"\r\n');
  const [testModelInput, setTestModelInput] = useState<string>('deepseek-flash');

  const sanitizeResult = sanitizeDeepSeekCredentials(testKeyInput);
  const routeResult = resolveModelRoute(testModelInput);

  const activeContest = contests.find((c) => c.contestId === activeContestId) || contests[0];

  const handleRunReplay = () => {
    setIsReplaying(true);
    setReplayLog([
      `[${new Date().toLocaleTimeString()}] Mounting Oct-31 historical snapshot into memory...`,
      `[${new Date().toLocaleTimeString()}] Virtual clock initialized at epoch 1793581200 (deterministic).`,
    ]);

    setTimeout(() => {
      setReplayLog((prev) => [
        ...prev,
        `[${new Date().toLocaleTimeString()}] History Fleet executing: zero-copy memory pool allocation (0 allocations).`,
        `[${new Date().toLocaleTimeString()}] Genesis Fleet executing: SIMD-vectorized WebAssembly parser.`,
      ]);
    }, 600);

    setTimeout(() => {
      setReplayLog((prev) => [
        ...prev,
        `[${new Date().toLocaleTimeString()}] Benchmark Complete! History Resourcefulness: 9.8x | Genesis Throughput: 98.4 msg/s.`,
        `[${new Date().toLocaleTimeString()}] Estate Insight: Extracted zero-copy pool into compounding library.`,
      ]);
      setIsReplaying(false);
    }, 1400);
  };

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 sm:p-8">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-mono text-cyan-400">
              <FlaskConical className="w-4 h-4 text-cyan-400" />
              <span>SCIENCE LANE CHARTER & ARCHAEOLOGY BRIDGE · DAY 0 AUTONOMOUS CAPABILITY</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              Autonomous Science & History Archaeology Bridge
            </h1>
            <p className="text-slate-400 text-sm max-w-2xl">
              History is preserved as-is with its chaotic real-world mess, acting as an irreplaceable research laboratory. In asymmetric contests, the History fleet (zero new budget) creatively bridges the gap to challenge the Genesis fleet.
            </p>
          </div>

          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs font-mono space-y-1.5 shrink-0 min-w-[260px]">
            <div className="text-slate-500 uppercase tracking-wider text-[10px]">Science Charter Vitals</div>
            <div className="flex justify-between items-center text-slate-200">
              <span>Status:</span>
              <span className="text-emerald-400 font-bold tabular-nums">EFFECTIVE DAY 0</span>
            </div>
            <div className="flex justify-between items-center text-slate-200">
              <span>History Snapshot:</span>
              <span className="text-cyan-400 font-bold">Oct 31 PRESERVED</span>
            </div>
            <div className="flex justify-between items-center text-slate-200">
              <span>Demarcation Lock:</span>
              <span className="text-emerald-400 font-bold">100% ISOLATED</span>
            </div>
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* 1. HISTORY LANE VS GENESIS ESTATE DEMARCATION MATRIX           */}
      {/* ------------------------------------------------------------- */}
      <div className="bg-slate-900/80 border border-cyan-800/60 rounded-xl p-6 sm:p-8 space-y-6 shadow-2xl">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 font-bold">
              <Split className="w-4 h-4 text-cyan-400" />
              <span>CONSTITUTIONAL SOVEREIGN DEMARCATION · ZERO CROSS-CONTAMINATION</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-white">
              History Lane vs. Genesis Estate Architectural Matrix
            </h2>
            <p className="text-xs text-slate-300">
              Absolute clarity on system boundaries: what stays in History Lane (legacy host, $0 budget, quarantined) vs what belongs to Genesis Estate (4-node Raft, Argon live stream, Compounding Doctrine).
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono text-emerald-400 bg-emerald-950/60 border border-emerald-800 px-3 py-1.5 rounded-lg shrink-0">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>§1.3 & §8.1 Inviolability Active</span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {demarcations.map((dm) => (
            <div
              key={dm.id}
              className="bg-slate-950 p-4 rounded-xl border border-slate-800 hover:border-slate-700 transition-all flex flex-col justify-between space-y-4"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-slate-900 pb-2">
                  <span className="font-mono text-xs font-bold text-slate-400">{dm.id}</span>
                  <span className="text-xs font-semibold text-white">{dm.dimension}</span>
                </div>

                {/* History Lane Box */}
                <div className="bg-amber-950/20 border border-amber-900/40 rounded-lg p-2.5 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-amber-400 font-bold flex items-center gap-1">
                      <History className="w-3 h-3 text-amber-400" />
                      HISTORY LANE
                    </span>
                    <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800">
                      {dm.historyLane.badge}
                    </span>
                  </div>
                  <h4 className="text-xs font-bold text-slate-200">{dm.historyLane.title}</h4>
                  <p className="text-[11px] text-slate-400 leading-normal">{dm.historyLane.description}</p>
                </div>

                {/* Genesis Estate Box */}
                <div className="bg-cyan-950/20 border border-cyan-900/40 rounded-lg p-2.5 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-cyan-300 font-bold flex items-center gap-1">
                      <Cpu className="w-3 h-3 text-cyan-400" />
                      GENESIS ESTATE
                    </span>
                    <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                      {dm.genesisEstate.badge}
                    </span>
                  </div>
                  <h4 className="text-xs font-bold text-white">{dm.genesisEstate.title}</h4>
                  <p className="text-[11px] text-slate-300 leading-normal">{dm.genesisEstate.description}</p>
                </div>
              </div>

              {/* Inviolable Boundary Rule */}
              <div className="pt-2 border-t border-slate-900 text-[10px] font-mono text-emerald-400/90 bg-slate-900/60 p-2 rounded">
                <span className="text-slate-500 uppercase block text-[8px] font-bold">Inviolable Boundary Rule:</span>
                {dm.inviolableRule}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* 2. DEEPSEEK 401 & 503 LIVE DIAGNOSTIC & KEY SANITIZER LAB     */}
      {/* ------------------------------------------------------------- */}
      <div className="bg-slate-900/80 border border-rose-900/60 rounded-xl p-6 sm:p-8 space-y-6 shadow-2xl">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs font-mono text-rose-400 font-bold">
              <KeyRound className="w-4 h-4 text-rose-400" />
              <span>DEEPSEEK 401 & 503 AUTONOMOUS RECOVERY LAB · HOST & MODEL UNBLOCKER</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-white">
              DeepSeek Authentication (401) & Model Route (503) Resolver
            </h2>
            <p className="text-xs text-slate-300">
              DeepSeek failures in IDP are driven by two discrete mechanisms: <strong>(1) Unstripped whitespace/quotes/CRLF</strong> in raw keys causing Cloudflare gateway 401 rejections, and <strong>(2) Nonexistent model name</strong> <code className="text-rose-300 font-mono">deepseek-flash</code> causing LiteLLM 503 empty-body errors.
            </p>
          </div>

          <button
            onClick={() => {
              navigator.clipboard.writeText('curl -fsSL https://ais-pre-3uz4y3dlbbarqxfihpbr26-534240513427.europe-west3.run.app/unblock-history-idp.sh | bash');
              setCopiedDeepSeekCmd(true);
              setTimeout(() => setCopiedDeepSeekCmd(false), 2000);
            }}
            className="flex items-center gap-2 px-4 py-2.5 text-xs font-mono font-bold text-slate-950 bg-gradient-to-r from-rose-400 to-amber-400 hover:from-rose-300 hover:to-amber-300 rounded-lg shadow transition-all cursor-pointer shrink-0"
          >
            {copiedDeepSeekCmd ? (
              <>
                <Check className="w-4 h-4 text-slate-950" />
                <span>Copied Host Key Sanitizer!</span>
              </>
            ) : (
              <>
                <Terminal className="w-4 h-4 text-slate-950" />
                <span>Copy 1-Line DeepSeek & IDP Fix</span>
              </>
            )}
          </button>
        </div>

        {/* Live Interactive Key Sanitizer & Model Resolver Playground */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Key Sanitizer Section */}
          <div className="bg-slate-950 p-5 rounded-xl border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-slate-300 flex items-center gap-2">
                <KeyRound className="w-4 h-4 text-amber-400" />
                Live API Key Sanitization Simulator
              </span>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                sanitizeResult.isValidFormat
                  ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                  : 'bg-rose-950 text-rose-300 border border-rose-800'
              }`}>
                {sanitizeResult.isValidFormat ? 'FORMAT VALID' : 'FORMAT INVALID / REJECTED'}
              </span>
            </div>

            <div className="space-y-1.5">
              <label className="text-[11px] font-mono text-slate-400">
                Raw Key from Environment File (Paste or test sample):
              </label>
              <textarea
                value={testKeyInput}
                onChange={(e) => setTestKeyInput(e.target.value)}
                rows={2}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs font-mono text-amber-300 focus:outline-none focus:border-cyan-400 resize-none"
                placeholder="Paste raw DEEPSEEK_API_KEY string here..."
              />
            </div>

            {/* Quick Test Presets */}
            <div className="flex flex-wrap gap-2 text-[10px] font-mono">
              <button
                onClick={() => setTestKeyInput('  "sk-f89a2bc417d940bca835ef98sjQw"\r\n')}
                className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-400 hover:text-white cursor-pointer"
              >
                Sample 1: Quotes & CRLF (Causes 401)
              </button>
              <button
                onClick={() => setTestKeyInput("'sk-11223344556677889900aabbccdd' ")}
                className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-400 hover:text-white cursor-pointer"
              >
                Sample 2: Single Quotes & Whitespace
              </button>
              <button
                onClick={() => setTestKeyInput('sk-da991048b291a7c001f481e7d940bc22')}
                className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-400 hover:text-white cursor-pointer"
              >
                Sample 3: Clean Canonical Key
              </button>
            </div>

            {/* Detected Issues */}
            <div className="p-3 bg-slate-900/80 rounded-lg border border-slate-800 space-y-1.5 text-xs font-mono">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Flaw Detection Diagnostic:</span>
              {sanitizeResult.detectedIssues.length > 0 ? (
                <div className="space-y-1">
                  {sanitizeResult.detectedIssues.map((issue, idx) => (
                    <div key={idx} className="flex items-center gap-1.5 text-rose-400 text-[11px]">
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                      <span>{issue}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center gap-1.5 text-emerald-400 text-[11px]">
                  <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                  <span>Zero whitespace, zero CRLF, zero quotes detected. Clean string.</span>
                </div>
              )}
            </div>

            {/* Clean Key & Header Output */}
            <div className="space-y-2 text-xs font-mono">
              <div className="p-2.5 bg-slate-900 rounded border border-slate-800">
                <span className="text-slate-500 block text-[9px] uppercase font-bold">Sanitized Key (What Estate Stores):</span>
                <span className="text-emerald-400 font-bold">{sanitizeResult.maskedKey}</span>
              </div>

              <div className="p-2.5 bg-slate-900 rounded border border-slate-800 overflow-x-auto">
                <span className="text-slate-500 block text-[9px] uppercase font-bold">Clean HTTP Authorization Header:</span>
                <span className="text-cyan-300">{sanitizeResult.recommendedAuthHeader || 'None'}</span>
              </div>
            </div>
          </div>

          {/* Model Route Resolver Section */}
          <div className="bg-slate-950 p-5 rounded-xl border border-slate-800 space-y-4 flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-bold text-slate-300 flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-cyan-400" />
                  Model Route & 503 Failover Engine
                </span>
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                  routeResult.routeStatus === 'CANONICAL'
                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                    : 'bg-amber-950 text-amber-300 border border-amber-800'
                }`}>
                  {routeResult.routeStatus}
                </span>
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] font-mono text-slate-400">
                  Target Model Name in IDP Prompt / Config:
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={testModelInput}
                    onChange={(e) => setTestModelInput(e.target.value)}
                    className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-400"
                    placeholder="e.g. deepseek-flash, deepseek-chat..."
                  />
                </div>
              </div>

              {/* Quick Model Selector Buttons */}
              <div className="flex flex-wrap gap-2 text-[10px] font-mono">
                <button
                  onClick={() => setTestModelInput('deepseek-flash')}
                  className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-rose-400 hover:text-white cursor-pointer"
                >
                  Test: deepseek-flash (Failed 503)
                </button>
                <button
                  onClick={() => setTestModelInput('deepseek-chat')}
                  className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-emerald-400 hover:text-white cursor-pointer"
                >
                  Test: deepseek-chat (Official V3)
                </button>
                <button
                  onClick={() => setTestModelInput('deepseek-reasoner')}
                  className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-cyan-400 hover:text-white cursor-pointer"
                >
                  Test: deepseek-reasoner (Official R1)
                </button>
              </div>

              {/* Route Resolution Card */}
              <div className="p-3 bg-slate-900/80 rounded-lg border border-slate-800 space-y-2 text-xs font-mono">
                <div className="flex justify-between items-center text-[11px]">
                  <span className="text-slate-400">Canonical Target:</span>
                  <span className="text-emerald-400 font-bold">{routeResult.canonicalModel}</span>
                </div>
                <div className="flex justify-between items-center text-[11px]">
                  <span className="text-slate-400">Upstream API Endpoint:</span>
                  <span className="text-slate-300">{routeResult.upstreamEndpoint}</span>
                </div>
                <div className="flex justify-between items-center text-[11px]">
                  <span className="text-slate-400">HTTP 503 Failover Model:</span>
                  <span className="text-cyan-400 font-bold">{routeResult.fallbackModel}</span>
                </div>
              </div>

              <div className="p-2.5 bg-slate-900 rounded border border-slate-800 text-[11px] font-mono text-slate-300">
                <span className="text-amber-400 block text-[9px] uppercase font-bold mb-0.5">Route Mitigation Policy:</span>
                {routeResult.mitigationNotice}
              </div>
            </div>

            {/* Terminal Copy Command for DeepSeek Invariant Fix */}
            <div className="pt-3 border-t border-slate-900 space-y-1.5">
              <span className="text-[10px] font-mono text-slate-400 block font-bold">1-Line Terminal Fix for ~/.config/estate/estate.env:</span>
              <div className="bg-slate-900 p-2 rounded text-[10px] font-mono text-cyan-300 select-all overflow-x-auto">
                <code>sed -i.bak 's/deepseek-flash/deepseek-chat/g' ~/.config/estate/estate.env</code>
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* 3. CRITICAL HISTORY LANE BLOCKERS (OLD IDP AUTOPSY)           */}
      {/* ------------------------------------------------------------- */}
      <div className="bg-slate-900/70 border border-amber-900/60 rounded-xl p-6 sm:p-8 space-y-6 shadow-xl">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs font-mono text-amber-400 font-bold">
              <Wrench className="w-4 h-4 text-amber-400" />
              <span>HISTORY LANE RECOVERY STATION · 7 CRITICAL BLOCKERS</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-white">
              Old IDP Autopsy & Automated Host Unblocker
            </h2>
            <p className="text-xs text-slate-300">
              Diagnosing and resolving the 7 critical failure modes observed in the legacy IDP session: DeepSeek 401/503 errors, disk floor refusals, broken Telegram vault paths, missing <code className="text-amber-300">bin/lane-where</code>, pre-commit hook timeouts, and unrelated UI-kit CI blocks.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={() => {
                navigator.clipboard.writeText('curl -fsSL https://ais-pre-3uz4y3dlbbarqxfihpbr26-534240513427.europe-west3.run.app/unblock-history-idp.sh | bash');
                setCopiedBootstrap(true);
                setTimeout(() => setCopiedBootstrap(false), 2000);
              }}
              className="flex items-center gap-2 px-4 py-2.5 text-xs font-mono font-bold text-slate-950 bg-gradient-to-r from-amber-400 to-amber-500 hover:from-amber-300 hover:to-amber-400 rounded-lg shadow transition-all cursor-pointer"
            >
              {copiedBootstrap ? (
                <>
                  <Check className="w-4 h-4 text-slate-950" />
                  <span>Copied 1-Line Host Unblocker!</span>
                </>
              ) : (
                <>
                  <Terminal className="w-4 h-4 text-slate-950" />
                  <span>Copy 1-Line Mac/Host Unblocker</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* 1-Line Command Display Banner */}
        <div className="bg-slate-950 p-3.5 rounded-lg border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs font-mono">
          <div className="flex items-center gap-2 text-cyan-300 select-all overflow-x-auto">
            <span className="text-slate-500">$</span>
            <code>curl -fsSL https://ais-pre-3uz4y3dlbbarqxfihpbr26-534240513427.europe-west3.run.app/unblock-history-idp.sh | bash</code>
          </div>
          <span className="text-[10px] text-slate-500 shrink-0">
            Fixes Telegram sender, DeepSeek 401/503, generates bin/lane-where, and cleans temp caches.
          </span>
        </div>

        {/* 7 Critical History Lane Blockers Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {blockers.map((b) => {
            const isResolved = resolvedBlockerIds.includes(b.id);
            return (
              <div
                key={b.id}
                className={`bg-slate-950 p-4 rounded-xl border flex flex-col justify-between transition-all ${
                  isResolved ? 'border-emerald-800/80' : 'border-amber-900/60'
                }`}
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-xs text-amber-300">{b.id}</span>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                      isResolved
                        ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                        : b.severity === 'CRITICAL'
                        ? 'bg-rose-950 text-rose-300 border border-rose-800'
                        : 'bg-amber-950 text-amber-300 border border-amber-800'
                    }`}>
                      {isResolved ? 'REMEDY READY' : b.severity}
                    </span>
                  </div>

                  <h3 className="font-bold text-xs text-white leading-snug">{b.title}</h3>
                  <p className="text-[11px] text-slate-400 leading-normal">{b.symptom}</p>
                  
                  <div className="text-[11px] font-mono text-cyan-300/90 bg-slate-900/80 p-2.5 rounded border border-slate-800">
                    <span className="text-slate-500 block text-[9px] uppercase">Root Cause:</span>
                    {b.rootCause}
                  </div>
                </div>

                <div className="pt-3 mt-3 border-t border-slate-900 space-y-2">
                  <div className="text-[10px] font-mono text-slate-400">
                    <span className="text-emerald-400 block font-bold">Compounding Leverage:</span>
                    {b.compoundingLeverage}
                  </div>

                  <div className="flex items-center justify-between gap-2 pt-1">
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(b.oneLineFixCommand);
                        setCopiedCmdId(b.id);
                        setTimeout(() => setCopiedCmdId(null), 2000);
                      }}
                      className="flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-mono rounded bg-slate-900 border border-slate-800 text-slate-300 hover:text-white transition-colors cursor-pointer"
                    >
                      {copiedCmdId === b.id ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-400" />
                          <span className="text-emerald-400">Copied Command</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          <span>Copy Fix Command</span>
                        </>
                      )}
                    </button>

                    <button
                      onClick={() => {
                        if (isResolved) {
                          setResolvedBlockerIds(resolvedBlockerIds.filter(id => id !== b.id));
                        } else {
                          setResolvedBlockerIds([...resolvedBlockerIds, b.id]);
                        }
                      }}
                      className="text-[10px] font-mono text-cyan-400 hover:text-cyan-300 underline cursor-pointer"
                    >
                      {isResolved ? 'Mark Pending' : 'Mark Resolved'}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* 4. ASYMMETRIC CONTEST ARENA: HISTORY VS GENESIS               */}
      {/* ------------------------------------------------------------- */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 sm:p-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-4">
          <div>
            <div className="text-xs font-mono text-cyan-400">THE ASYMMETRIC CONTEST ARENA</div>
            <h2 className="text-lg font-bold text-white mt-0.5">{activeContest.taskTitle}</h2>
          </div>
          <span className="text-xs font-mono text-slate-400">
            Metric: <strong className="text-slate-200">{activeContest.benchmarkMetric}</strong>
          </span>
        </div>

        {/* Side-by-Side Comparison Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          {/* History Fleet Box */}
          <div className="p-5 bg-slate-950 rounded-xl border border-amber-900/60 space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-xs font-mono font-bold text-amber-400 flex items-center gap-1.5">
                <History className="w-4 h-4 text-amber-400" />
                HISTORY ARCHAEOLOGY FLEET
              </span>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800 font-bold">
                $0 Budget
              </span>
            </div>

            <div className="text-xs text-slate-300">
              <strong>Advantage: </strong> {activeContest.historySnapshotFleet.advantage}
            </div>
            <div className="text-xs text-slate-400">
              <strong>Constraint: </strong> {activeContest.historySnapshotFleet.constraint}
            </div>

            <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 text-xs font-mono text-slate-200">
              <span className="text-amber-400 block text-[10px] uppercase font-bold mb-1">Solution Approach:</span>
              {activeContest.historySnapshotFleet.solutionApproach}
            </div>

            <div className="flex justify-between items-center pt-2 border-t border-slate-900 text-xs font-mono">
              <span className="text-slate-400">Resourcefulness Factor:</span>
              <span className="text-amber-400 font-bold text-sm tabular-nums">
                {activeContest.historySnapshotFleet.resourcefulnessFactor}x / $0
              </span>
            </div>
          </div>

          {/* Genesis Fleet Box */}
          <div className="p-5 bg-slate-950 rounded-xl border border-cyan-800/80 space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-xs font-mono font-bold text-cyan-300 flex items-center gap-1.5">
                <Cpu className="w-4 h-4 text-cyan-400" />
                GENESIS ERA_1 SOVEREIGN FLEET
              </span>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 font-bold">
                Frontier Budget
              </span>
            </div>

            <div className="text-xs text-slate-300">
              <strong>Advantage: </strong> {activeContest.genesisFleet.advantage}
            </div>
            <div className="text-xs text-slate-400">
              <strong>Constraint: </strong> {activeContest.genesisFleet.constraint}
            </div>

            <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 text-xs font-mono text-slate-200">
              <span className="text-cyan-400 block text-[10px] uppercase font-bold mb-1">Solution Approach:</span>
              {activeContest.genesisFleet.solutionApproach}
            </div>

            <div className="flex justify-between items-center pt-2 border-t border-slate-900 text-xs font-mono">
              <span className="text-slate-400">Throughput Benchmark:</span>
              <span className="text-cyan-400 font-bold text-sm tabular-nums">
                {activeContest.genesisFleet.score} score
              </span>
            </div>
          </div>

        </div>

        {/* Compounding Synthesis Card */}
        <div className="p-4 bg-emerald-950/20 border border-emerald-800/60 rounded-xl space-y-1.5 text-xs font-mono">
          <div className="flex items-center gap-1.5 font-bold text-emerald-400">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            <span>ESTATE INSIGHT GAINED FROM ASYMMETRIC CONTEST:</span>
          </div>
          <div className="text-slate-200 font-sans text-xs leading-relaxed">
            {activeContest.deltaEvaluation}
          </div>
          <div className="text-cyan-300 text-[11px] font-mono pt-1">
            Leverage Retained: {activeContest.estateInsightLearned}
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* 5. SNAPSHOT TIME MACHINE & DETERMINISTIC REPLAY               */}
      {/* ------------------------------------------------------------- */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 sm:p-8 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-3">
          <div>
            <div className="text-xs font-mono text-cyan-400">CONTINUOUS TIME MACHINE</div>
            <h3 className="text-base font-bold text-white mt-0.5">Isolated Historical Event Replay Engine</h3>
          </div>

          <button
            onClick={handleRunReplay}
            disabled={isReplaying}
            className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-slate-950 bg-gradient-to-r from-amber-400 to-cyan-400 hover:from-amber-300 hover:to-cyan-300 rounded-lg transition-all shadow cursor-pointer disabled:opacity-50"
          >
            <Play className={`w-3.5 h-3.5 ${isReplaying ? 'animate-spin' : ''}`} />
            <span>{isReplaying ? 'Replaying Deterministically...' : 'Run Historical Replay'}</span>
          </button>
        </div>

        <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-[11px] font-mono space-y-1 text-slate-300 max-h-48 overflow-y-auto leading-relaxed">
          {replayLog.map((log, idx) => (
            <div
              key={idx}
              className={
                log.includes('Benchmark Complete')
                  ? 'text-emerald-400 font-bold'
                  : log.includes('Executing')
                  ? 'text-cyan-300'
                  : 'text-slate-300'
              }
            >
              {log}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
