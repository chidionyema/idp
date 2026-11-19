/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  History,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Database,
  Lock,
  ArrowRight,
  GitBranch,
  Terminal,
  Cpu,
  Bot,
  AlertTriangle,
} from 'lucide-react';
import { HISTORICAL_ATTEMPTS } from '../utils/optimus-engine';
import { MerkleLedgerBlock } from '../types/optimus';

interface GenesisAndHistoryViewProps {
  genesisBlock: MerkleLedgerBlock;
  onInspectGenesis: () => void;
  onNavigateToSimulator: () => void;
}

export const GenesisAndHistoryView: React.FC<GenesisAndHistoryViewProps> = ({
  genesisBlock,
  onInspectGenesis,
  onNavigateToSimulator,
}) => {
  const [activeTab, setActiveTab] = useState<'EVOLUTION' | 'AEI_POSTMORTEM' | 'GENESIS_CHAIN'>('EVOLUTION');

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-2">
        <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
          <span>PROJECT OPTIMUS GENESIS & LINEAGE</span>
          <span aria-hidden="true">·</span>
          <span className="text-indigo-400 font-semibold">FOUNDER EXECUTIVE BRIEF</span>
          <span aria-hidden="true">·</span>
          <span className="text-emerald-400">MATHEMATICAL CERTAINTY</span>
        </div>
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
          The Genesis of Zero-Circumvention: History, Failed Attempts & Mathematical Proof
        </h1>
        <p className="text-xs sm:text-sm text-slate-400 max-w-4xl leading-relaxed">
          Why every historical attempt—from local bash hooks to passive APM and AEI in IDP—failed to prevent
          unmetered code from leaking into repositories, and how Project Optimus anchors every runnable surface
          to an immutable cryptographic Genesis block.
        </p>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-2 pt-3 border-t border-slate-800/80 text-xs font-mono overflow-x-auto">
          <button
            onClick={() => setActiveTab('EVOLUTION')}
            className={`px-3 py-1.5 rounded transition-colors whitespace-nowrap ${
              activeTab === 'EVOLUTION'
                ? 'bg-indigo-600 text-white font-bold'
                : 'text-slate-400 hover:text-white bg-slate-950'
            }`}
          >
            The 5 Generations of Governance
          </button>
          <button
            onClick={() => setActiveTab('AEI_POSTMORTEM')}
            className={`px-3 py-1.5 rounded transition-colors whitespace-nowrap ${
              activeTab === 'AEI_POSTMORTEM'
                ? 'bg-indigo-600 text-white font-bold'
                : 'text-slate-400 hover:text-white bg-slate-950'
            }`}
          >
            AEI in IDP: Deep Post-Mortem
          </button>
          <button
            onClick={() => setActiveTab('GENESIS_CHAIN')}
            className={`px-3 py-1.5 rounded transition-colors whitespace-nowrap ${
              activeTab === 'GENESIS_CHAIN'
                ? 'bg-indigo-600 text-white font-bold'
                : 'text-slate-400 hover:text-white bg-slate-950'
            }`}
          >
            Genesis Block #0 & Merkle Chain of Custody
          </button>
        </div>
      </div>

      {/* Tab 1: The 5 Generations of Governance */}
      {activeTab === 'EVOLUTION' && (
        <div className="space-y-4">
          <div className="text-xs font-mono text-slate-400 uppercase">
            Historical Evolution from Fragile Bypasses to Mathematical Invariants
          </div>

          <div className="grid grid-cols-1 gap-4">
            {HISTORICAL_ATTEMPTS.map((attempt, index) => {
              const isOptimus = attempt.status === 'OPTIMUS_ACTIVE';
              return (
                <div
                  key={attempt.generation}
                  className={`p-5 rounded-xl border transition-all ${
                    isOptimus
                      ? 'bg-indigo-950/20 border-indigo-500/80 ring-1 ring-indigo-500/50 shadow-lg shadow-indigo-950/40'
                      : 'bg-slate-900/60 border-slate-800'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-3 mb-3">
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-mono font-bold text-slate-400">
                        {attempt.generation}
                      </span>
                      <h3 className="text-sm font-bold text-white">
                        {attempt.name}
                      </h3>
                    </div>

                    <span
                      className={`text-xs font-mono font-bold px-2 py-0.5 rounded inline-flex items-center gap-1.5 w-fit ${
                        isOptimus
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                          : attempt.status === 'VULNERABLE'
                          ? 'bg-amber-950 text-amber-400 border border-amber-800'
                          : 'bg-red-950 text-red-400 border border-red-800'
                      }`}
                    >
                      {isOptimus ? <ShieldCheck className="w-3.5 h-3.5" /> : <ShieldAlert className="w-3.5 h-3.5" />}
                      <span>{attempt.status}</span>
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed mb-4">
                    {attempt.description}
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs pt-3 border-t border-slate-800/60">
                    <div className="space-y-1">
                      <span className="text-[10px] font-mono uppercase text-slate-500 block">
                        Vulnerability to Circumvention
                      </span>
                      <div className="text-slate-300 leading-snug">
                        {attempt.vulnerabilityToBypass}
                      </div>
                    </div>

                    <div className="space-y-1">
                      <span className="text-[10px] font-mono uppercase text-slate-500 block">
                        Mathematical Proof & Verifiability
                      </span>
                      <div className="text-slate-300 leading-snug">
                        {attempt.mathematicalProof}
                      </div>
                    </div>

                    <div className="space-y-1">
                      <span className="text-[10px] font-mono uppercase text-slate-500 block">
                        {isOptimus ? 'Why It Succeeds' : 'Why It Failed Historically'}
                      </span>
                      <div className={isOptimus ? 'text-emerald-400 font-medium' : 'text-red-400'}>
                        {attempt.whyFailedOrSuperseded}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab 2: AEI in IDP Deep Post-Mortem */}
      {activeTab === 'AEI_POSTMORTEM' && (
        <div className="space-y-5">
          <div className="bg-amber-950/20 border border-amber-800/60 rounded-xl p-5 space-y-3">
            <div className="flex items-center gap-2 text-xs font-mono text-amber-400 font-bold">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <span>THE FOUNDER'S PRIOR ATTEMPT: WHY AEI IN IDP FAILED TO PREVENT UNMETERED PUSHES</span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              &ldquo;We even tried AEI in IDP amongst countless other attempts...&rdquo; — Automated Enforcement & Instrumentation (AEI)
              within Internal Developer Platforms (Backstage, Cortex, Port, Humanitec) was a well-intentioned attempt to enforce
              engineering standards. However, it suffered from four fatal architectural flaws that allowed unmetered code to continually leak through:
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Flaw 1 */}
            <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold text-red-400 font-mono">
                <XCircle className="w-4 h-4 text-red-400" />
                <span>FLAW 1: ASYNCHRONOUS POLLING GAP</span>
              </div>
              <h4 className="text-xs font-bold text-white">Commits Hit Remote Before IDP Evaluated</h4>
              <p className="text-xs text-slate-300 leading-relaxed">
                IDPs poll repository state on 15-minute to 6-hour cron intervals. By the time an IDP scorecard turned red,
                the unmetered code was already merged, deployed, or cherry-picked into production.
              </p>
              <div className="p-2.5 rounded bg-slate-950 border border-slate-800/80 text-[11px] font-mono text-emerald-400">
                <strong>Optimus Fix:</strong> Synchronous server-side <code className="text-white">update-ref</code> hook. The commit ref cannot update on the remote git server without a signed ticket.
              </div>
            </div>

            {/* Flaw 2 */}
            <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold text-red-400 font-mono">
                <XCircle className="w-4 h-4 text-red-400" />
                <span>FLAW 2: ESTATE SCOPE BLINDSPOTS</span>
              </div>
              <h4 className="text-xs font-bold text-white">Scripts, Agents & YAML Excluded from Catalog</h4>
              <p className="text-xs text-slate-300 leading-relaxed">
                IDP catalogs only track declared software components (e.g. catalog-info.yaml). Ad-hoc migration scripts,
                cron jobs, AI agents, devcontainer runs, and raw Terraform changes operated entirely outside the IDP&apos;s visibility.
              </p>
              <div className="p-2.5 rounded bg-slate-950 border border-slate-800/80 text-[11px] font-mono text-emerald-400">
                <strong>Optimus Fix:</strong> All 8 runnable surfaces metered at the kernel/process level via eBPF, AST probes, and admission controllers.
              </div>
            </div>

            {/* Flaw 3 */}
            <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold text-red-400 font-mono">
                <XCircle className="w-4 h-4 text-red-400" />
                <span>FLAW 3: TRIVIAL DEVELOPER BYPASSES</span>
              </div>
              <h4 className="text-xs font-bold text-white">`--no-verify` and Admin Overrides</h4>
              <p className="text-xs text-slate-300 leading-relaxed">
                When under deadline pressure, engineers or founders would pass <code className="text-red-400">--no-verify</code>,
                force push, or bypass webhook checks via branch protection exceptions, completely negating AEI rules.
              </p>
              <div className="p-2.5 rounded bg-slate-950 border border-slate-800/80 text-[11px] font-mono text-emerald-400">
                <strong>Optimus Fix:</strong> Hard invariant rule <code className="text-white">INV-NOBYP</code> strictly flags and kills any push containing bypass tokens.
              </div>
            </div>

            {/* Flaw 4 */}
            <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold text-red-400 font-mono">
                <XCircle className="w-4 h-4 text-red-400" />
                <span>FLAW 4: NO CRYPTOGRAPHIC ATTESTATION</span>
              </div>
              <h4 className="text-xs font-bold text-white">Advisory Scorecards Without Mathematical Proof</h4>
              <p className="text-xs text-slate-300 leading-relaxed">
                AEI produced soft JSON dashboards and bronze/silver badges rather than cryptographic ECDSA-signed in-toto
                attestations. It could not prove mathematically whether a binary had been modified post-check.
              </p>
              <div className="p-2.5 rounded bg-slate-950 border border-slate-800/80 text-[11px] font-mono text-emerald-400">
                <strong>Optimus Fix:</strong> SLSA Level 3 hermetic provenance + ECDSA-P256-SHA256 signatures chained into an immutable Merkle ledger.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Genesis Block #0 & Merkle Chain */}
      {activeTab === 'GENESIS_CHAIN' && (
        <div className="space-y-4">
          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Database className="w-5 h-5 text-indigo-400" />
                <h3 className="text-sm font-bold text-white">
                  Genesis Block #0: Estate Root of Verifiable Trust
                </h3>
              </div>
              <button
                onClick={onInspectGenesis}
                className="px-3 py-1 text-xs font-semibold rounded bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
              >
                Inspect Genesis Payload
              </button>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Every single ratified push, commit, agent execution, and deployment in the estate is cryptographically chained
              back to Genesis Block #0. If any past commit is altered, retroactively edited, or injected without metrics,
              the Merkle root breaks instantly and halts the estate pipeline.
            </p>

            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 font-mono text-xs space-y-2 text-slate-300">
              <div className="flex justify-between border-b border-slate-800/80 pb-1.5">
                <span className="text-slate-500">Block Height:</span>
                <span className="text-indigo-400 font-bold">#0 (GENESIS_ROOT)</span>
              </div>
              <div className="flex justify-between border-b border-slate-800/80 pb-1.5">
                <span className="text-slate-500">Timestamp:</span>
                <span className="text-white">{genesisBlock.timestamp}</span>
              </div>
              <div className="flex justify-between border-b border-slate-800/80 pb-1.5">
                <span className="text-slate-500">Genesis Block Hash:</span>
                <span className="text-emerald-400 break-all">{genesisBlock.blockHash}</span>
              </div>
              <div className="flex justify-between border-b border-slate-800/80 pb-1.5">
                <span className="text-slate-500">Previous Hash (Null Anchor):</span>
                <span className="text-slate-500 font-mono">{genesisBlock.previousHash}</span>
              </div>
              <div className="flex justify-between border-b border-slate-800/80 pb-1.5">
                <span className="text-slate-500">Root Signature:</span>
                <span className="text-indigo-300 break-all">{genesisBlock.signature}</span>
              </div>
              <div className="pt-1 text-[11px] text-slate-400">
                <strong>Attestation Directive:</strong> {genesisBlock.attestationSummary}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
