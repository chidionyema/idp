/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { Header } from './components/Header';
import { EstateOverview } from './components/EstateOverview';
import { SurfaceGrid } from './components/SurfaceGrid';
import { PushGateSimulator } from './components/PushGateSimulator';
import { MerkleLedgerView } from './components/MerkleLedgerView';
import { GenesisAndHistoryView } from './components/GenesisAndHistoryView';
import { PolicyStudio } from './components/PolicyStudio';
import { TelemetryAnalytics } from './components/TelemetryAnalytics';
import { LiveEvidenceView } from './components/LiveEvidenceView';
import { BlockDetailModal } from './components/BlockDetailModal';
import {
  SURFACES,
  DEFAULT_INVARIANT_RULES,
  verifyMerkleChainIntegrity,
  computeDeterministicHash,
  DEFAULT_SURFACE_LATENCY_CAPS,
  syncLatencyCapsToRules,
} from './utils/optimus-engine';
import {
  INITIAL_LEDGER_BLOCKS,
  GENESIS_BLOCK,
} from './data/seedData';
import {
  MerkleLedgerBlock,
  SurfaceType,
  GateVerificationOutcome,
  MetricPayload,
  EstateExecutiveSummary,
  SurfaceLatencyCapConfig,
} from './types/optimus';

export default function App() {
  const [activeTab, setActiveTab] = useState<string>('estate');
  const [ledger, setLedger] = useState<MerkleLedgerBlock[]>(INITIAL_LEDGER_BLOCKS);
  const [latencyCaps, setLatencyCaps] = useState<Record<SurfaceType, SurfaceLatencyCapConfig>>(
    DEFAULT_SURFACE_LATENCY_CAPS
  );
  const [rules, setRules] = useState(() =>
    syncLatencyCapsToRules(DEFAULT_INVARIANT_RULES, DEFAULT_SURFACE_LATENCY_CAPS)
  );
  const [selectedSurface, setSelectedSurface] = useState<SurfaceType | null>('git_commit_push');
  const [selectedBlockForModal, setSelectedBlockForModal] = useState<MerkleLedgerBlock | null>(null);
  const [isBaselineLocked, setIsBaselineLocked] = useState(false);

  const handleUpdateLatencyCap = (
    surfaceId: SurfaceType,
    updatedCap: Partial<SurfaceLatencyCapConfig>
  ) => {
    setLatencyCaps((prev) => {
      const nextCaps = {
        ...prev,
        [surfaceId]: {
          ...prev[surfaceId],
          ...updatedCap,
        },
      };
      setRules((currentRules) => syncLatencyCapsToRules(currentRules, nextCaps));
      return nextCaps;
    });
  };

  const handleResetLatencyCaps = () => {
    setLatencyCaps(DEFAULT_SURFACE_LATENCY_CAPS);
    setRules((currentRules) => syncLatencyCapsToRules(currentRules, DEFAULT_SURFACE_LATENCY_CAPS));
  };


  const [isAuditing, setIsAuditing] = useState(false);
  const [auditOutcome, setAuditOutcome] = useState<string | null>(null);

  const blockedCount = ledger.filter((b) => b.status === 'REJECTED_BLOCKED').length;
  const ratifiedCount = ledger.filter((b) => b.status === 'RATIFIED_AND_SIGNED').length;

  const executiveSummary: EstateExecutiveSummary = {
    overallCoverageRate: 100.0,
    totalSurfacesMonitored: 8,
    totalInvariantsEnforced: rules.length,
    circumventionAttemptsBlocked: blockedCount,
    verifiedAttestationsCount: ratifiedCount,
    merkleChainHeight: ledger.length > 0 ? ledger[ledger.length - 1].index : 0,
    lastRatifiedTimestamp: ledger.length > 0 ? ledger[ledger.length - 1].timestamp : new Date().toISOString(),
    bypassToleranceRate: 0.0,
    zeroTrustStatus: 'ABSOLUTE_INTEGRITY',
  };

  const handleAuditChain = () => {
    setIsAuditing(true);
    setAuditOutcome(null);

    setTimeout(() => {
      const result = verifyMerkleChainIntegrity(ledger);
      setIsAuditing(false);
      if (result.isValid) {
        setAuditOutcome(
          `MATHEMATICAL INTEGRITY VERIFIED: All ${ledger.length} blocks chained back to Genesis #0. Cryptographic signatures valid. 0 unmetered mutations detected.`
        );
      } else {
        setAuditOutcome(`INTEGRITY FAILURE at Block #${result.brokenIndex}: ${result.reason}`);
      }
    }, 600);
  };

  const handleLockDayZeroBaseline = () => {
    if (isBaselineLocked) return;

    const prevBlock = ledger[ledger.length - 1];
    const newIndex = prevBlock ? prevBlock.index + 1 : 1211;
    const timestamp = new Date().toISOString();

    const baselineHash = computeDeterministicHash(`DAY_ZERO_RATIFIED_BASELINE:${timestamp}`);

    const baselineBlock: MerkleLedgerBlock = {
      index: newIndex,
      timestamp,
      surface: 'microservice_engine',
      entityId: 'baseline-estate-day-0 (ratified-invariant-lock)',
      actor: 'founder-authority@foundry.io',
      blockHash: baselineHash,
      previousHash: prevBlock ? prevBlock.blockHash : GENESIS_BLOCK.blockHash,
      merkleRoot: computeDeterministicHash(`ROOT:${baselineHash}`),
      status: 'RATIFIED_AND_SIGNED',
      signature: `ECDSA-P256-SHA256:${computeDeterministicHash(`SIG_BASELINE:${baselineHash}`)}`,
      metricsSnapshot: {
        estate_coverage_rate: 100.0,
        active_invariants_count: rules.length,
        bypass_tolerance_rate: 0.0,
        day_zero_lock_status: 'ACTIVE',
        metric_signature_valid: true,
      },
      violationCount: 0,
      attestationSummary: 'DAY 0 OPERATIONAL BASELINE LOCKED: All 8 surfaces cryptographically pinned with exact latency & coverage boundaries.',
    };

    setLedger((prev) => [...prev, baselineBlock]);
    setIsBaselineLocked(true);
  };

  const handleAppendToLedger = (outcome: GateVerificationOutcome, payload: MetricPayload) => {
    const prevBlock = ledger[ledger.length - 1];
    const newIndex = prevBlock ? prevBlock.index + 1 : 1;

    const newBlock: MerkleLedgerBlock = {
      index: newIndex,
      timestamp: outcome.timestamp,
      surface: outcome.surface,
      entityId: outcome.entityId,
      actor: outcome.actor,
      blockHash: outcome.computedHash,
      previousHash: prevBlock ? prevBlock.blockHash : GENESIS_BLOCK.blockHash,
      merkleRoot: outcome.merkleLeaf,
      status: outcome.status,
      signature: outcome.cryptographicSignature || 'REJECTED_NO_SIGNATURE_GENERATED',
      metricsSnapshot: payload.metrics,
      violationCount: outcome.rejectionReasons.length,
      rejectionSummary: outcome.rejectionReasons.length > 0 ? outcome.rejectionReasons.join('; ') : undefined,
      attestationSummary: outcome.allowed
        ? 'Signed push ticket verified and appended to immutable Merkle chain.'
        : 'Circumvention or invariant violation intercepted. Push rejected at server-side ref gate.',
    };

    setLedger((prev) => [...prev, newBlock]);
  };

  const handleTestGateForSurface = (surface: SurfaceType) => {
    setSelectedSurface(surface);
    setActiveTab('interceptor');
  };

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Top Bar adhering to Top Bar Contract */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onSimulateClick={() => setActiveTab('interceptor')}
        blockedCount={blockedCount}
      />

      {/* Main Viewport */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-8">
        {/* Estate Overview Tab */}
        {activeTab === 'estate' && (
          <div className="space-y-8">
            <EstateOverview
              summary={executiveSummary}
              onVerifyChain={handleAuditChain}
              isVerifying={isAuditing}
              integrityStatus={auditOutcome}
              onNavigateToSimulator={() => setActiveTab('interceptor')}
            />

            <SurfaceGrid
              surfaces={SURFACES}
              selectedSurface={selectedSurface}
              onSelectSurface={(s) => setSelectedSurface(s)}
              onTestGate={handleTestGateForSurface}
            />
          </div>
        )}

        {/* Telemetry Analytics Tab (D3.js Stream & Optimization) */}
        {activeTab === 'analytics' && (
          <TelemetryAnalytics
            ledger={ledger}
            onNavigateToSimulator={() => setActiveTab('interceptor')}
            onLockDayZeroBaseline={handleLockDayZeroBaseline}
            isBaselineLocked={isBaselineLocked}
          />
        )}

        {/* Push Gate Interceptor Simulator */}
        {activeTab === 'interceptor' && (
          <PushGateSimulator
            initialSurface={selectedSurface || 'git_commit_push'}
            rules={rules}
            onAppendToLedger={handleAppendToLedger}
          />
        )}

        {/* Verifiable Merkle Ledger */}
        {activeTab === 'ledger' && (
          <MerkleLedgerView
            ledger={ledger}
            onSelectBlock={(b) => setSelectedBlockForModal(b)}
            onAuditChain={handleAuditChain}
            isAuditing={isAuditing}
            auditOutcome={auditOutcome}
          />
        )}

        {/* Genesis & History View */}
        {activeTab === 'aei_analysis' && (
          <GenesisAndHistoryView
            genesisBlock={GENESIS_BLOCK}
            onInspectGenesis={() => setSelectedBlockForModal(GENESIS_BLOCK)}
            onNavigateToSimulator={() => setActiveTab('interceptor')}
          />
        )}

        {/* Policy Studio */}
        {activeTab === 'policy' && (
          <PolicyStudio
            rules={rules}
            latencyCaps={latencyCaps}
            onUpdateLatencyCap={handleUpdateLatencyCap}
            onResetLatencyCapsToBaselines={handleResetLatencyCaps}
          />
        )}

        {/* Live Execution Evidence & Git Artifacts */}
        {activeTab === 'evidence' && <LiveEvidenceView />}
      </main>

      {/* Detail Modal */}
      <BlockDetailModal
        block={selectedBlockForModal}
        onClose={() => setSelectedBlockForModal(null)}
      />

      {/* Clean Footer adhering to Anti-Slop Rules */}
      <footer className="border-t border-slate-900 bg-[#070a10] py-6 px-6 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-300">Project Optimus</span>
            <span aria-hidden="true">·</span>
            <span>Verifiable Operational Integrity Architecture</span>
            <span aria-hidden="true">·</span>
            <span>Genesis Hash: {GENESIS_BLOCK.blockHash.substring(0, 10)}...</span>
          </div>
          <div className="flex items-center gap-4 text-slate-400">
            <button onClick={() => setActiveTab('estate')} className="hover:text-white transition-colors">
              Topology
            </button>
            <button onClick={() => setActiveTab('interceptor')} className="hover:text-white transition-colors">
              Push Interceptor
            </button>
            <button onClick={() => setActiveTab('ledger')} className="hover:text-white transition-colors">
              Merkle Ledger
            </button>
            <button onClick={() => setActiveTab('aei_analysis')} className="hover:text-white transition-colors">
              Genesis & Lineage
            </button>
            <button onClick={() => setActiveTab('policy')} className="hover:text-white transition-colors">
              Policy Studio
            </button>
            <button onClick={() => setActiveTab('evidence')} className="hover:text-white transition-colors text-emerald-400 font-semibold">
              Execution Evidence & Git
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}
