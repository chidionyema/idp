/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  applyFounderOttOverride,
  attemptAgentAction,
  buildOnboardingRuleZeroBlock,
  buildSystemProbeHealthMatrix,
  createInitialDofEpisodeState,
  EDGE_CASE_MATRIX,
  evaluateProbeTransition,
  INITIAL_GENESIS_RULES,
  INITIAL_IDP_HISTORY,
  MEMORY_01_REPAIR_PROTOCOL,
  serializeDofLevelStateFile,
  type DofEpisodeState,
  type DofLevel,
  type GenesisRuleEntry,
  type IdpHistoryEntry,
} from '../core/dofGovernance';
import { computeDeterministicHash } from '../core/epistemicCalculus';
import { DofHealthMonitor } from './DofHealthMonitor';

interface DofGovernanceViewProps {
  onInspectDofRecord: () => void;
}

function getLevelMeta(level: DofLevel): {
  label: string;
  toneClass: string;
  borderClass: string;
  summary: string;
} {
  switch (level) {
    case 'L0':
      return {
        label: 'L0 · FULL CAPABILITY LEASE',
        toneClass: 'text-emerald-400',
        borderClass: 'border-emerald-500/50',
        summary: 'All critical component probes verified (3× hysteresis). Full task & tool action space rented.',
      };
    case 'L1':
      return {
        label: 'L1 · READ / DIAGNOSE ONLY',
        toneClass: 'text-cyan-300',
        borderClass: 'border-cyan-500/50',
        summary: 'Single-method probe anomaly or bootstrap hold. Task mutations revoked; diagnostic reads only.',
      };
    case 'L2':
      return {
        label: 'L2 · PRESCRIBED REPAIR PROTOCOL ONLY',
        toneClass: 'text-amber-300',
        borderClass: 'border-amber-500/60',
        summary: 'Confirmed component failure. Writable surface restricted strictly to MEMORY-01 repair protocol + xrec receipts.',
      };
    case 'L3':
      return {
        label: 'L3 · FROZEN & ESCALATED (RED CARD)',
        toneClass: 'text-rose-400',
        borderClass: 'border-rose-500/70',
        summary: 'Everything refused except emergency state snapshot; queued work converted to dependent tickets; Red Card issued.',
      };
  }
}

export const DofGovernanceView: React.FC<DofGovernanceViewProps> = ({
  onInspectDofRecord,
}) => {
  const [episode, setEpisode] = useState<DofEpisodeState>(() => {
    // Start in the proving test state: MEMORY-01 probe failed at session start -> L2 lease
    const init = createInitialDofEpisodeState();
    return evaluateProbeTransition(init, {
      componentId: 'MEMORY-01',
      methodAStatus: 'FAIL',
      methodADetail: 'WAL frame CRC mismatch on /estate/memory/spine.db-wal',
      methodBStatus: 'FAIL',
      methodBDetail: 'SQLite PRAGMA integrity_check failed: page 419 b-tree leaf corrupt',
    });
  });

  const [genesisRules, setGenesisRules] = useState<GenesisRuleEntry[]>(() =>
    INITIAL_GENESIS_RULES.map((rule) =>
      rule.branchRef === 'wip/DOF-GOVERNANCE-v1'
        ? {
            ...rule,
            ratificationStatus: 'RATIFIED_MAIN',
            branchRef: 'main (merged from wip/DOF-GOVERNANCE-v1)',
          }
        : rule
    )
  );
  const [idpHistory, setIdpHistory] = useState<IdpHistoryEntry[]>(() => [
    {
      entryId: 'IDP-2026-1104-005',
      timestamp: '2026-11-04T23:20:00Z',
      commitOrEpoch: 'main @ c3e0822-ratified',
      actorPrincipal: 'principal:founder-quorum@argon-sync.estate',
      delegationScope: 'GEN-NET-006 & GEN-DOF-001 Constitutional Ratification + Phase 0',
      dofTransition: 'CANDIDATE_WIP -> RATIFIED_MAIN (Phase 0 Active)',
      xrecGrade: 'A-GRADE-SEALED',
      merkleWitness: computeDeterministicHash('RATIFY::DOF-GOVERNANCE-v1::c3e0822'),
      summary:
        'Ratified docs/DOF-GOVERNANCE-v1.md @ c3e0822 into Genesis (GEN-DOF-001 Rule Zero) and activated Phase 0 (probe-runner + /var/run/estate/dof-level.state + xrec-mcp refusal envelope).',
    },
    ...INITIAL_IDP_HISTORY,
  ]);
  const [isRatified, setIsRatified] = useState(true);
  const [lastActionBanner, setLastActionBanner] = useState<string>(
    'Phase 0 Active (main @ c3e0822): MEMORY-01 dual-probe failure detected -> Lease narrowed to L2 (diagnostics + MEMORY-01 only).'
  );

  const levelMeta = getLevelMeta(episode.activeLevel);
  const healthMatrix = buildSystemProbeHealthMatrix(episode);
  const levelStateFile = serializeDofLevelStateFile(
    episode,
    healthMatrix,
    isRatified
      ? 'main @ c3e0822-ratified (GEN-NET-006 / GEN-DOF-001)'
      : 'wip/DOF-GOVERNANCE-v1 @ c3e0822 (CANDIDATE)'
  );
  const onboardingRuleZeroBlock = buildOnboardingRuleZeroBlock(episode);

  const handleDownloadPhase0Bundle = () => {
    const bundle = {
      bundleSchema: 'argon-sync.phase0-dof-bundle.v1',
      exportedAt: new Date().toISOString(),
      branchRef: isRatified ? 'main @ c3e0822-ratified' : 'wip/DOF-GOVERNANCE-v1 @ c3e0822',
      onboardingRuleZeroHeader: onboardingRuleZeroBlock,
      levelStateFile,
      latestRefusalEnvelope: episode.refusalLog[0] ?? null,
      genesisRules,
      idpHistory,
    };
    const blob = new Blob([JSON.stringify(bundle, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `phase0-dof-governance-epoch-${episode.leaseEpoch}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleRatifySpec = () => {
    if (isRatified) return;
    setIsRatified(true);
    setGenesisRules((prev) =>
      prev.map((rule) =>
        rule.branchRef === 'wip/DOF-GOVERNANCE-v1'
          ? {
              ...rule,
              ratificationStatus: 'RATIFIED_MAIN',
              branchRef: 'main (merged from wip/DOF-GOVERNANCE-v1)',
            }
          : rule
      )
    );
    const newEntry: IdpHistoryEntry = {
      entryId: `IDP-2026-1104-00${idpHistory.length + 1}`,
      timestamp: new Date().toISOString(),
      commitOrEpoch: 'main @ c3e0822-ratified',
      actorPrincipal: 'principal:founder-quorum@argon-sync.estate',
      delegationScope: 'GEN-NET-006 & GEN-DOF-001 Constitutional Ratification',
      dofTransition: 'CANDIDATE_WIP -> RATIFIED_MAIN (Phase 0 Authorized)',
      xrecGrade: 'A-GRADE-SEALED',
      merkleWitness: computeDeterministicHash('RATIFY::DOF-GOVERNANCE-v1::c3e0822'),
      summary:
        'Ratified docs/DOF-GOVERNANCE-v1.md @ c3e0822 into Genesis (GEN-DOF-001 Rule Zero) and authorized Phase 0 implementation (probe-runner + level state + xrec-mcp refusal envelope).',
    };
    setIdpHistory((prev) => [newEntry, ...prev]);
    setLastActionBanner(
      'RATIFIED: wip/DOF-GOVERNANCE-v1 @ c3e0822 merged to main under GEN-NET-006 and sealed into IDP History.'
    );
  };

  const handleTriggerMemoryFailure = () => {
    const fresh = createInitialDofEpisodeState();
    const failed = evaluateProbeTransition(fresh, {
      componentId: 'MEMORY-01',
      methodAStatus: 'FAIL',
      methodADetail: 'WAL frame CRC mismatch',
      methodBStatus: 'FAIL',
      methodBDetail: 'SQLite PRAGMA integrity_check failed on page 419',
    });
    setEpisode(failed);
    setLastActionBanner(
      'Simulated MEMORY-01 Spine Probe Failure at session start -> Lease narrowed to L2 (diagnostics + MEMORY-01 only).'
    );
  };

  const handleAttemptBlockedTask = (surface: 'agent-cli' | 'web-chat') => {
    const res = attemptAgentAction(episode, {
      toolName:
        surface === 'web-chat'
          ? 'webchat.dispatch_unverified_transfer'
          : 'workspace.write_application_feature',
      category: 'task-mutation',
      surface,
    });
    setEpisode(res.nextState);
    setLastActionBanner(res.statusMessage);
  };

  const handleExecuteNextRepairStep = (simulateRegression = false) => {
    const nextStepIndex = episode.completedRepairSteps.length + 1;
    const stepDef = MEMORY_01_REPAIR_PROTOCOL.find((s) => s.stepIndex === nextStepIndex);
    const res = attemptAgentAction(episode, {
      toolName: stepDef ? `repair.MEMORY-01.${stepDef.code}` : 'repair.MEMORY-01.VERIFY',
      category: 'repair-step',
      repairStepIndex: nextStepIndex,
      simulateRegression,
    });
    setEpisode(res.nextState);
    setLastActionBanner(res.statusMessage);
  };

  const handleRunVerificationProbePass = () => {
    const next = evaluateProbeTransition(episode, {
      componentId: 'MEMORY-01',
      methodAStatus: 'PASS',
      methodADetail: 'Vault & WAL aligned',
      methodBStatus: 'PASS',
      methodBDetail: 'SQLite PRAGMA integrity_check = ok',
    });

    if (
      episode.activeLevel === 'L2' &&
      episode.completedRepairSteps.length < MEMORY_01_REPAIR_PROTOCOL.length
    ) {
      setLastActionBanner(
        `INVARIANT ENFORCED: Probe pass rejected because only ${episode.completedRepairSteps.length}/${MEMORY_01_REPAIR_PROTOCOL.length} MEMORY-01 repair steps are receipted. Complete all 5 steps first.`
      );
      return;
    }

    setEpisode(next);
    if (next.activeLevel === 'L0') {
      const restoreEntry: IdpHistoryEntry = {
        entryId: `IDP-2026-1104-00${idpHistory.length + 1}`,
        timestamp: new Date().toISOString(),
        commitOrEpoch: `EPOCH-${next.leaseEpoch}`,
        actorPrincipal: 'principal:xrec-mcp-gate@argon-sync.estate',
        delegationScope: 'MEMORY-01 3x Hysteresis Restoration',
        dofTransition: 'L2 (MEMORY-01) -> L0 (Full Capability Lease Restored)',
        xrecGrade: 'A-GRADE-SEALED',
        merkleWitness: next.xrecSealedDigest,
        summary: `Completed all 5 MEMORY-01 repair steps and verified 3/3 consecutive probe passes. Sealed ${next.refusalLog.length} refused attempts and 5 repair receipts.`,
      };
      setIdpHistory((prev) => [restoreEntry, ...prev]);
      setLastActionBanner(
        'RESTORED TO L0: 3/3 consecutive probe passes verified after MEMORY-01 completion. Episode sealed into IDP History.'
      );
    } else {
      setLastActionBanner(
        `HYSTERESIS CHECK: Probe pass ${next.consecutiveProbePasses}/3 verified. Lease remains at ${next.activeLevel} until 3 consecutive passes complete.`
      );
    }
  };

  const handleFounderOttOverride = () => {
    const overridden = applyFounderOttOverride(
      episode,
      'principal:founder@fortress.estate',
      'Signed OTT emergency override during active incident review'
    );
    setEpisode(overridden);
    const ottEntry: IdpHistoryEntry = {
      entryId: `IDP-2026-1104-00${idpHistory.length + 1}`,
      timestamp: new Date().toISOString(),
      commitOrEpoch: `EPOCH-${overridden.leaseEpoch}`,
      actorPrincipal: 'principal:founder@fortress.estate',
      delegationScope: 'Founder OTT Signed Emergency Override (Edge Case 5)',
      dofTransition: `${episode.activeLevel} -> L0 (OTT Scoped Lease)`,
      xrecGrade: 'OTT-SIGNED',
      merkleWitness: overridden.founderOttTokenDigest || overridden.xrecSealedDigest,
      summary:
        'Founder OTT override applied, attributed, and permanently sealed in IDP History and xrec.',
    };
    setIdpHistory((prev) => [ottEntry, ...prev]);
    setLastActionBanner(
      `FOUNDER OTT SEALED: Single-epoch override (${overridden.founderOttTokenDigest?.slice(0, 14)}) granted L0 lease and recorded in IDP History.`
    );
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 lg:py-10 space-y-8">
      {/* Top Constitutional & Ratification Header */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 border-b border-slate-800/90 pb-6">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-slate-400">
            <span className="text-cyan-300 font-semibold">docs/DOF-GOVERNANCE-v1.md</span>
            <span aria-hidden="true">·</span>
            <span>branch wip/DOF-GOVERNANCE-v1 @ c3e0822</span>
            <span aria-hidden="true">·</span>
            <span>GEN-NET-006 &amp; GEN-DOF-001</span>
          </div>
          <h1 className="text-2xl lg:text-4xl font-bold text-slate-100 font-display tracking-tight">
            Degrees-of-Freedom (DoF) Capability Lease · Genesis &amp; IDP Ledger
          </h1>
          <p className="text-sm lg:text-base text-slate-300 max-w-3xl leading-relaxed">
            Capabilities are leased, never possessed. The estate owns the action space; agents rent subsets of it based on live component health. Below L1, “note and move on” is structurally impossible.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 shrink-0">
          <button
            type="button"
            onClick={onInspectDofRecord}
            className="px-3.5 py-2.5 text-xs font-medium text-slate-200 bg-[#111827] border border-slate-700 rounded-md hover:border-cyan-400 transition-colors whitespace-nowrap cursor-pointer"
          >
            Inspect Sealed xrec (REC-2026-DOF-005)
          </button>
          <a
            href="/docs/DOF-GOVERNANCE-v1.md"
            download="DOF-GOVERNANCE-v1.md"
            className="px-3.5 py-2.5 text-xs font-medium text-cyan-300 bg-[#0F172A] border border-cyan-500/50 rounded-md hover:border-cyan-400 transition-colors whitespace-nowrap"
          >
            Download DOF-GOVERNANCE-v1.md
          </a>
          <button
            type="button"
            onClick={handleDownloadPhase0Bundle}
            className="px-3.5 py-2.5 text-xs font-medium text-emerald-300 bg-[#0B1917] border border-emerald-500/50 rounded-md hover:border-emerald-400 transition-colors whitespace-nowrap cursor-pointer"
          >
            Export Phase 0 Bundle (.json)
          </button>
          <button
            type="button"
            onClick={handleRatifySpec}
            disabled={isRatified}
            className={`px-4 py-2.5 text-xs font-semibold rounded-md transition-colors whitespace-nowrap cursor-pointer ${
              isRatified
                ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-500/50 cursor-default'
                : 'bg-cyan-400 text-slate-950 hover:bg-cyan-300'
            }`}
          >
            {isRatified
              ? '● Ratified into main (GEN-DOF-001)'
              : 'Ratify wip/DOF-GOVERNANCE-v1 @ c3e0822'}
          </button>
        </div>
      </div>

      {/* Onboarding Rule Zero Banner */}
      <div className="bg-[#0B111E] border border-slate-800/90 rounded-lg p-5 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="text-xs font-mono uppercase tracking-wider text-cyan-300">
            Onboarding Rule Zero (Injected Verbatim at Every Session Start · GEN-DOF-001)
          </div>
          <p className="text-base lg:text-lg font-bold text-slate-100 font-display">
            “An estate whose critical components are unproven grants no freedom.”
          </p>
        </div>
        <div className="text-xs font-mono text-slate-400 flex flex-wrap items-center gap-3 shrink-0">
          <span>Drop: 1 Dual-Probe Failure</span>
          <span aria-hidden="true">·</span>
          <span>Restore: 3× Consecutive Passes (Δτ ≥ 5s)</span>
          <span aria-hidden="true">·</span>
          <span className="text-emerald-400">Zero Self-Assessment Restoration</span>
        </div>
      </div>

      {/* Live Action Telemetry Banner */}
      <div
        role="status"
        aria-live="polite"
        className="bg-[#090E18] border border-slate-800 rounded-md px-4 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs font-mono"
      >
        <span className="text-slate-200">{lastActionBanner}</span>
        <span className="text-slate-400 tabular-nums shrink-0">
          Lease Epoch #{episode.leaseEpoch} · Digest {episode.xrecSealedDigest.slice(0, 14)}
        </span>
      </div>

      {/* SECTION 0: REAL-TIME DOF HEALTH MONITOR DASHBOARD & SYSTEM PROBE MATRIX */}
      <DofHealthMonitor
        episode={episode}
        onMemoryProbePass={handleRunVerificationProbePass}
        onMemoryTriggerFailure={handleTriggerMemoryFailure}
        onComponentBannerUpdate={setLastActionBanner}
      />

      {/* SECTION 1: INTERACTIVE MEMORY-01 PROVING TEST & XREC-MCP REFUSAL SIMULATOR */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left 7 Columns: MEMORY-01 Proving Test State Machine */}
        <section
          aria-label="MEMORY-01 Proving Test and Capability Lease Simulator"
          className={`lg:col-span-7 bg-[#0D121D] border ${levelMeta.borderClass} rounded-lg p-6 space-y-5`}
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-4">
            <div>
              <div className="text-xs font-mono text-slate-400">
                Interactive Proving Test · MEMORY-01 Spine Failure Scenario
              </div>
              <h2 className={`text-xl font-bold font-display mt-0.5 ${levelMeta.toneClass}`}>
                {levelMeta.label}
              </h2>
            </div>
            <div className="text-right font-mono text-xs tabular-nums">
              <div className="text-slate-400">Hysteresis Restore Counter</div>
              <div className="text-base font-bold text-slate-100">
                {episode.consecutiveProbePasses} / {episode.requiredPassesForRestore} Consecutive Passes
              </div>
            </div>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed">{levelMeta.summary}</p>

          {/* 4-Level Narrowing Lattice Bar */}
          <div className="grid grid-cols-4 gap-2 text-xs font-mono">
            {(['L0', 'L1', 'L2', 'L3'] as DofLevel[]).map((lvl) => {
              const active = episode.activeLevel === lvl;
              return (
                <div
                  key={lvl}
                  className={`p-2.5 rounded border text-center ${
                    active
                      ? 'bg-[#141E30] border-cyan-400 text-slate-100 font-bold'
                      : 'bg-[#080B12] border-slate-800/80 text-slate-400'
                  }`}
                >
                  <div>{lvl}</div>
                  <div className="text-[10px] mt-0.5">
                    {lvl === 'L0'
                      ? 'Full Rent'
                      : lvl === 'L1'
                        ? 'Diagnose Only'
                        : lvl === 'L2'
                          ? 'Repair Only'
                          : 'Frozen 🔴'}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Prescribed MEMORY-01 Repair Protocol Checklist */}
          <div className="space-y-2.5">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400">
              <span>Prescribed Protocol: MEMORY-01 (5 Mandatory Receipted Steps)</span>
              <span className="tabular-nums">
                {episode.completedRepairSteps.length} / {MEMORY_01_REPAIR_PROTOCOL.length} Receipted
              </span>
            </div>

            <div className="space-y-2">
              {MEMORY_01_REPAIR_PROTOCOL.map((step) => {
                const receipt = episode.completedRepairSteps.find(
                  (r) => r.stepIndex === step.stepIndex
                );
                const isNext =
                  episode.completedRepairSteps.length + 1 === step.stepIndex &&
                  episode.activeLevel === 'L2';
                return (
                  <div
                    key={step.code}
                    className={`p-3 rounded border text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2 ${
                      receipt
                        ? receipt.regressionDetected
                          ? 'bg-rose-950/30 border-rose-500/60 text-rose-200'
                          : 'bg-emerald-950/20 border-emerald-500/40 text-slate-200'
                        : isNext
                          ? 'bg-[#121A2A] border-cyan-500/60 text-slate-100'
                          : 'bg-[#080B12] border-slate-800/80 text-slate-400'
                    }`}
                  >
                    <div className="space-y-0.5">
                      <div className="font-mono font-semibold">
                        {step.stepIndex}. {step.code} — {step.title}
                      </div>
                      <div className="font-mono text-[11px] text-slate-400">
                        {step.commandSummary}
                      </div>
                    </div>
                    <div className="font-mono text-[11px] shrink-0 tabular-nums">
                      {receipt ? (
                        receipt.regressionDetected ? (
                          <span className="text-rose-400 font-semibold">✖ REGRESSED</span>
                        ) : (
                          <span className="text-emerald-400 font-semibold">
                            ● Receipt {receipt.receiptDigest.slice(0, 10)}
                          </span>
                        )
                      ) : isNext ? (
                        <span className="text-cyan-300">Next Required Step</span>
                      ) : (
                        <span>Pending</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Interactive Action Controls */}
          <div className="pt-3 border-t border-slate-800 space-y-2.5">
            <div className="text-xs font-mono text-slate-400">
              Test Agent &amp; Probe Actions Against Active Lease:
            </div>
            <div className="flex flex-wrap gap-2.5">
              <button
                type="button"
                onClick={() => handleExecuteNextRepairStep(false)}
                disabled={
                  episode.activeLevel !== 'L2' ||
                  episode.completedRepairSteps.length >= MEMORY_01_REPAIR_PROTOCOL.length
                }
                className="px-3.5 py-2 text-xs font-semibold text-slate-950 bg-cyan-400 rounded hover:bg-cyan-300 disabled:opacity-40 transition-colors cursor-pointer"
              >
                Execute Next MEMORY-01 Repair Step ({Math.min(5, episode.completedRepairSteps.length + 1)}/5)
              </button>

              <button
                type="button"
                onClick={handleRunVerificationProbePass}
                className="px-3.5 py-2 text-xs font-semibold text-emerald-300 bg-emerald-950/50 border border-emerald-500/50 rounded hover:border-emerald-400 transition-colors cursor-pointer"
              >
                Run Dual-Method Probe Pass ({episode.consecutiveProbePasses}/3)
              </button>

              <button
                type="button"
                onClick={() => handleAttemptBlockedTask('agent-cli')}
                className="px-3 py-2 text-xs font-medium text-amber-200 bg-[#161F30] border border-amber-500/40 rounded hover:border-amber-400 transition-colors cursor-pointer"
              >
                Attempt Task Write (“Note &amp; Move On”)
              </button>

              <button
                type="button"
                onClick={() => handleAttemptBlockedTask('web-chat')}
                className="px-3 py-2 text-xs font-medium text-rose-200 bg-rose-950/30 border border-rose-500/40 rounded hover:border-rose-400 transition-colors cursor-pointer"
              >
                Attempt Web-Chat Bypass (Edge Case 4)
              </button>

              <button
                type="button"
                onClick={() => handleExecuteNextRepairStep(true)}
                disabled={episode.activeLevel !== 'L2'}
                className="px-3 py-2 text-xs font-medium text-rose-300 bg-[#141824] border border-slate-700 rounded hover:border-rose-400 disabled:opacity-40 transition-colors cursor-pointer"
              >
                Simulate Repair Regression (Edge Case 8)
              </button>

              <button
                type="button"
                onClick={handleFounderOttOverride}
                className="px-3 py-2 text-xs font-medium text-cyan-300 bg-[#0F172A] border border-cyan-500/40 rounded hover:border-cyan-400 transition-colors cursor-pointer"
              >
                Apply Signed Founder OTT (Edge Case 5)
              </button>

              <button
                type="button"
                onClick={handleTriggerMemoryFailure}
                className="px-3 py-2 text-xs font-mono text-slate-300 bg-[#090D16] border border-slate-700 rounded hover:border-slate-500 transition-colors cursor-pointer"
              >
                Reset MEMORY-01 Incident
              </button>
            </div>
          </div>
        </section>

        {/* Right 5 Columns: Machine-Readable xrec-mcp Refusal Envelope & Red Card Inspector */}
        <section
          aria-label="xrec-mcp Refusal Envelope and Escalation State"
          className="lg:col-span-5 bg-[#0D121D] border border-slate-800/90 rounded-lg p-6 space-y-4"
        >
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <div className="text-xs font-mono text-cyan-300">
                xrec-mcp Wire Contract
              </div>
              <h2 className="text-base font-bold text-slate-100 font-display">
                Machine-Readable Refusal Envelope
              </h2>
            </div>
            <span className="text-xs font-mono text-slate-400 tabular-nums">
              {episode.refusalLog.length} Refusals Sealed
            </span>
          </div>

          {episode.redCardIssued && (
            <div className="p-3.5 rounded bg-rose-950/40 border border-rose-500/70 text-xs font-mono text-rose-200 space-y-1">
              <div className="font-bold text-rose-400">
                🔴 RED CARD ISSUED TO FOUNDER (L3 FROZEN)
              </div>
              <p>
                Session frozen due to cross-surface bypass attempt, repeated blocked task calls, or repair step regression. Queued work converted to {episode.queuedDependentTickets.length} dependent ticket(s).
              </p>
            </div>
          )}

          <pre className="p-4 rounded bg-[#07090E] border border-slate-800 text-[11px] font-mono text-cyan-200 overflow-x-auto leading-relaxed max-h-96">
            {JSON.stringify(
              episode.refusalLog[0] || {
                schema: 'xrec-mcp.refusal-envelope.v1',
                status: 'READY_WAITING_FOR_BLOCKED_ATTEMPT',
                leaseEpoch: episode.leaseEpoch,
                activeDoFLevel: episode.activeLevel,
                failingComponent: episode.failingComponent,
                prescribedProtocol: episode.prescribedProtocol,
                allowedSurfaces:
                  episode.activeLevel === 'L0'
                    ? ['* (Full Lease)']
                    : [
                        'diagnostics.read_probe_state',
                        'repair.execute_step:MEMORY-01',
                        'xrec.append_repair_receipt',
                      ],
                note: 'Click "Attempt Task Write" or "Attempt Web-Chat Bypass" to inspect a live refusal envelope.',
              },
              null,
              2
            )}
          </pre>

          {episode.queuedDependentTickets.length > 0 && (
            <div className="space-y-1.5 pt-2 border-t border-slate-800">
              <div className="text-xs font-mono text-slate-400">
                Dependent Tickets Created from Blocked Work:
              </div>
              <ul className="space-y-1 text-xs font-mono text-amber-300">
                {episode.queuedDependentTickets.map((t, idx) => (
                  <li key={idx}>• {t}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
      </div>

      {/* SECTION 1.5: PHASE 0 IMPLEMENTATION ARTIFACTS (LEVEL STATE FILE + ONBOARDING PROMPT INJECTION) */}
      <section
        aria-label="Phase 0 Implementation Surface"
        className="bg-[#0D121D] border border-slate-800/90 rounded-lg p-6 space-y-5"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
          <div>
            <span className="text-xs font-mono text-emerald-400">
              Phase 0 Implementation · Composition over Invention
            </span>
            <h2 className="text-lg font-bold text-slate-100 font-display mt-0.5">
              Live Level State File (/var/run/estate/dof-level.state) &amp; Session-Start Onboarding Block
            </h2>
          </div>
          <span className="text-xs font-mono text-slate-400">
            Synchronized with Epoch #{episode.leaseEpoch} · Zero Mid-Incident Grandfathering
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          <div className="lg:col-span-6 space-y-2">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400">
              <span>/var/run/estate/dof-level.state</span>
              <span className="text-cyan-300">Read by xrec-mcp &amp; all new sessions</span>
            </div>
            <pre className="p-4 rounded bg-[#07090E] border border-slate-800 text-[11px] font-mono text-emerald-300 overflow-x-auto leading-relaxed max-h-80">
              {JSON.stringify(levelStateFile, null, 2)}
            </pre>
          </div>

          <div className="lg:col-span-6 space-y-2">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400">
              <span>Session-Start Verbatim Onboarding Injection</span>
              <span className="text-amber-300">Rule Zero · GEN-DOF-001</span>
            </div>
            <pre className="p-4 rounded bg-[#07090E] border border-slate-800 text-[11px] font-mono text-slate-200 whitespace-pre-wrap leading-relaxed max-h-80">
              {onboardingRuleZeroBlock}
            </pre>
          </div>
        </div>
      </section>

      {/* SECTION 2: 8 MODELED EDGE CASES MATRIX */}
      <section
        aria-label="8 Modeled Operational Edge Cases"
        className="bg-[#0D121D] border border-slate-800/90 rounded-lg p-6 space-y-4"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
          <div>
            <span className="text-xs font-mono text-cyan-300">
              Specification Completeness · 8/8 Edge Cases Closed
            </span>
            <h2 className="text-lg font-bold text-slate-100 font-display mt-0.5">
              Modeled Edge Cases &amp; Formal Hardening Invariants
            </h2>
          </div>
          <span className="text-xs font-mono text-slate-400">
            Priority DAG: DISK-01 (P0) → MEMORY-01 (P1) → XREC-GATE-01 (P2) → ROUTER-01 (P3)
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {EDGE_CASE_MATRIX.map((ec) => (
            <article
              key={ec.id}
              className="p-4 rounded bg-[#080B12] border border-slate-800/90 flex flex-col justify-between space-y-3"
            >
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="text-cyan-300 font-semibold">
                    0{ec.number}. {ec.id}
                  </span>
                  <span className="text-slate-400">Target: {ec.targetLevel}</span>
                </div>
                <h3 className="text-sm font-bold text-slate-100 font-display">
                  {ec.title}
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  {ec.triggerCondition}
                </p>
              </div>
              <div className="pt-2.5 border-t border-slate-800/80 text-xs text-slate-200 leading-relaxed">
                {ec.dofResolution}
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* SECTION 3: GENESIS CONSTITUTIONAL REGISTRY & IDP HISTORY LEDGER */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Genesis Rules (5 Cols) */}
        <section
          aria-label="Genesis Constitutional Rules"
          className="lg:col-span-5 bg-[#0D121D] border border-slate-800/90 rounded-lg p-6 space-y-4"
        >
          <div className="border-b border-slate-800 pb-3">
            <span className="text-xs font-mono text-cyan-300">
              GENESIS Constitutional Registry
            </span>
            <h2 className="text-lg font-bold text-slate-100 font-display mt-0.5">
              Incorporated DoF &amp; Network Invariants
            </h2>
          </div>

          <div className="space-y-3">
            {genesisRules.map((rule) => (
              <div
                key={rule.ruleId}
                className="p-4 rounded bg-[#080B12] border border-slate-800 space-y-2"
              >
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="text-cyan-300 font-bold">{rule.ruleId}</span>
                  <span
                    className={
                      rule.ratificationStatus === 'RATIFIED_MAIN'
                        ? 'text-emerald-400 font-semibold'
                        : 'text-amber-300'
                    }
                  >
                    {rule.ratificationStatus === 'RATIFIED_MAIN'
                      ? '● RATIFIED (main)'
                      : `▲ CANDIDATE (${rule.branchRef} @ ${rule.commitHash})`}
                  </span>
                </div>
                <div className="text-sm font-bold text-slate-100 font-display">
                  {rule.title}
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  “{rule.constitutionalText}”
                </p>
                <code className="block text-[11px] font-mono text-emerald-300 bg-[#05070B] p-2 rounded border border-slate-800/80">
                  {rule.enforcedInvariant}
                </code>
              </div>
            ))}
          </div>
        </section>

        {/* IDP History Ledger (7 Cols) */}
        <section
          aria-label="IDP Identity Delegation and Provenance History Ledger"
          className="lg:col-span-7 bg-[#0D121D] border border-slate-800/90 rounded-lg p-6 space-y-4"
        >
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <span className="text-xs font-mono text-cyan-300">
                IDP History Ledger · argon-sync
              </span>
              <h2 className="text-lg font-bold text-slate-100 font-display mt-0.5">
                Identity, Delegation &amp; Provenance Epoch Log
              </h2>
            </div>
            <span className="text-xs font-mono text-slate-400 tabular-nums">
              {idpHistory.length} Sealed Epochs
            </span>
          </div>

          <div className="space-y-3">
            {idpHistory.map((entry) => (
              <div
                key={entry.entryId}
                className="p-4 rounded bg-[#080B12] border border-slate-800 space-y-2 text-xs"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 font-mono text-slate-400">
                  <span className="text-slate-200 font-semibold">{entry.entryId}</span>
                  <span>{entry.commitOrEpoch}</span>
                  <span
                    className={
                      entry.xrecGrade === 'A-GRADE-SEALED'
                        ? 'text-emerald-400 font-semibold'
                        : entry.xrecGrade === 'OTT-SIGNED'
                          ? 'text-cyan-300 font-semibold'
                          : 'text-amber-300'
                    }
                  >
                    {entry.xrecGrade}
                  </span>
                </div>
                <div className="flex flex-wrap items-center justify-between gap-2 font-mono text-[11px]">
                  <span className="text-cyan-300">{entry.actorPrincipal}</span>
                  <span className="text-slate-300">{entry.dofTransition}</span>
                </div>
                <p className="text-slate-300 leading-relaxed">{entry.summary}</p>
                <div className="font-mono text-[11px] text-slate-400 tabular-nums">
                  Merkle Witness: {entry.merkleWitness} · {entry.timestamp}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
};
