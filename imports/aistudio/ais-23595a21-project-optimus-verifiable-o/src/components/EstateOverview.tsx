/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  Layers,
  Database,
  Lock,
  Zap,
} from 'lucide-react';
import { EstateExecutiveSummary } from '../types/optimus';

interface EstateOverviewProps {
  summary: EstateExecutiveSummary;
  onVerifyChain: () => void;
  isVerifying: boolean;
  integrityStatus: string | null;
  onNavigateToSimulator: () => void;
}

export const EstateOverview: React.FC<EstateOverviewProps> = ({
  summary,
  onVerifyChain,
  isVerifying,
  integrityStatus,
  onNavigateToSimulator,
}) => {
  return (
    <div className="space-y-6">
      {/* Founder Mission Statement Banner */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 relative overflow-hidden">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
              <span>ESTATE INTEGRITY DIRECTIVE</span>
              <span aria-hidden="true">·</span>
              <span className="text-emerald-400 font-medium">MATHEMATICALLY VERIFIED</span>
              <span aria-hidden="true">·</span>
              <span>ZERO BYPASS TOLERANCE</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
              Every Runnable Surface Metered & Cryptographically Locked
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 max-w-3xl leading-relaxed">
              No code, script, pipeline, engine, IaC YAML, cron worker, or AI agent can touch the repository
              or runtime cluster without verifiable mathematical telemetry and an authentic cryptographic signature.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={onVerifyChain}
              disabled={isVerifying}
              className="px-4 py-2 text-xs font-semibold text-slate-200 bg-slate-800 border border-slate-700 rounded-lg hover:bg-slate-700 hover:text-white transition-colors whitespace-nowrap flex items-center gap-2"
            >
              <Lock className="w-3.5 h-3.5 text-indigo-400" />
              <span>{isVerifying ? 'Auditing Merkle Chain...' : 'Verify Cryptographic Chain'}</span>
            </button>
            <button
              onClick={onNavigateToSimulator}
              className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-500 transition-colors whitespace-nowrap flex items-center gap-2 shadow-sm shadow-indigo-900/40"
            >
              <Zap className="w-3.5 h-3.5" />
              <span>Test Ref Push Gate</span>
            </button>
          </div>
        </div>

        {integrityStatus && (
          <div className="mt-4 pt-3 border-t border-slate-800 flex items-center gap-2 text-xs font-mono text-emerald-400">
            <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{integrityStatus}</span>
          </div>
        )}
      </div>

      {/* 6 Executive Metric Tiles */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
        <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3.5 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Surface Coverage</span>
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="text-xl font-bold font-mono tabular-nums text-emerald-400">
            {summary.overallCoverageRate.toFixed(2)}%
          </div>
          <div className="text-[11px] text-slate-500">8 of 8 estate layers</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3.5 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Bypass Tolerance</span>
            <Lock className="w-3.5 h-3.5 text-indigo-400" />
          </div>
          <div className="text-xl font-bold font-mono tabular-nums text-white">
            {summary.bypassToleranceRate.toFixed(3)}%
          </div>
          <div className="text-[11px] text-slate-500">Absolute zero bypass</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3.5 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Blocked Bypasses</span>
            <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
          </div>
          <div className="text-xl font-bold font-mono tabular-nums text-red-400">
            {summary.circumventionAttemptsBlocked}
          </div>
          <div className="text-[11px] text-slate-500">Circumventions killed</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3.5 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Merkle Ledger Height</span>
            <Database className="w-3.5 h-3.5 text-blue-400" />
          </div>
          <div className="text-xl font-bold font-mono tabular-nums text-white">
            #{summary.merkleChainHeight}
          </div>
          <div className="text-[11px] text-slate-500">Immutable blocks</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3.5 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Active Invariants</span>
            <Layers className="w-3.5 h-3.5 text-purple-400" />
          </div>
          <div className="text-xl font-bold font-mono tabular-nums text-white">
            {summary.totalInvariantsEnforced}
          </div>
          <div className="text-[11px] text-slate-500">Mathematical rules</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3.5 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Attestations</span>
            <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <div className="text-xl font-bold font-mono tabular-nums text-cyan-400">
            {summary.verifiedAttestationsCount}
          </div>
          <div className="text-[11px] text-slate-500">ECDSA signed refs</div>
        </div>
      </div>
    </div>
  );
};
