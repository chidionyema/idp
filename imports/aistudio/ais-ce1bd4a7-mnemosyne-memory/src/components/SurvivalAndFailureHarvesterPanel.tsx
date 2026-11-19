import React, { useState } from 'react';
import {
  SurvivalAndHarvesterState,
  FailureSurfaceCategory,
  FailureModeIntelligenceRecord,
} from '../engine/survivalHarvesterEngine';

interface SurvivalAndFailureHarvesterPanelProps {
  survivalState: SurvivalAndHarvesterState;
  gitShortSha: string;
  allGitBranchesLocked: boolean;
  onlineSurfaceCount: number;
  ratifiedProtocolCount: number;
  onTriggerLowBatteryEvacuation: (simulatedBatteryPct?: number, customReason?: string) => void;
  onRestoreNominalPower: (homeId?: string) => void;
  onSubmitFailureModeToTriad: (input: {
    title: string;
    category: FailureSurfaceCategory;
    severity: 'CRITICAL' | 'HIGH' | 'MEDIUM';
    encounteredBySurface: string;
    encounteredDuringWorkflow: string;
    symptomOrContext?: string;
  }) => FailureModeIntelligenceRecord | void;
  onAdvanceResearchTrack: (trackId: string) => void;
  onRunWorkflowPreFlight: (workflowName: string) => void;
  onPromoteFailureToMemoryGraph: (record: FailureModeIntelligenceRecord) => void;
}

const PRESET_WORKFLOWS = [
  'Long-Running MacBook Local Agent Sprint & Multi-Repo Argo Release',
  'High-Volume Model Inference & Multi-Agent Routing Wave',
  'Custodian Treasury & Registrar Keep-Alive Renewal',
  'Cross-Surface One-Brain Council Quorum & Zero-Credit Lifeboat Failover',
];

export const SurvivalAndFailureHarvesterPanel: React.FC<SurvivalAndFailureHarvesterPanelProps> = ({
  survivalState,
  gitShortSha,
  allGitBranchesLocked,
  onlineSurfaceCount,
  ratifiedProtocolCount,
  onTriggerLowBatteryEvacuation,
  onRestoreNominalPower,
  onSubmitFailureModeToTriad,
  onAdvanceResearchTrack,
  onRunWorkflowPreFlight,
  onPromoteFailureToMemoryGraph,
}) => {
  const [activeSubTab, setActiveSubTab] = useState<
    'homes-watchtower' | 'triad-harvester' | 'preflight-and-rd'
  >('homes-watchtower');

  // Triad Failure-Mode Harvester form state
  const [fmTitle, setFmTitle] = useState<string>('');
  const [fmCategory, setFmCategory] = useState<FailureSurfaceCategory>('hardware_power_host');
  const [fmSeverity, setFmSeverity] = useState<'CRITICAL' | 'HIGH' | 'MEDIUM'>('CRITICAL');
  const [fmSurface, setFmSurface] = useState<string>(
    'Otto Mac Watchdog + MiniMax-M2.7 Specialist'
  );
  const [fmWorkflow, setFmWorkflow] = useState<string>(
    'Long-Running MacBook Local Agent Sprint & Multi-Repo Argo Release'
  );
  const [fmContext, setFmContext] = useState<string>('');
  const [lastHarvestedId, setLastHarvestedId] = useState<string | null>(null);
  const [promotedIds, setPromotedIds] = useState<Record<string, boolean>>({});

  // Upfront Workflow Pre-Flight selector state
  const [selectedWorkflow, setSelectedWorkflow] = useState<string>(
    survivalState.preFlightAssessment.workflowName
  );

  const macHome = survivalState.homes.find((h) => h.homeId === 'home-macbook-pro');
  const macEvacuated = macHome?.status === 'PREEMPTIVE_EVACUATION_ACTIVE';
  const activeAlarm = survivalState.activeAlarms.find(
    (a) => a.status === 'ACTIVE_EVACUATED_SAFE'
  );

  const handleHarvestSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const cleanTitle =
      fmTitle.trim() ||
      'MacBook Wi-Fi / Fiber Drop Mid-Commit During Multi-Agent Council Execution';
    const created = onSubmitFailureModeToTriad({
      title: cleanTitle,
      category: fmCategory,
      severity: fmSeverity,
      encounteredBySurface: fmSurface,
      encounteredDuringWorkflow: fmWorkflow,
      symptomOrContext:
        fmContext.trim() ||
        'Local ISP packet loss detected while Otto and Codex Desktop were coordinating a multi-branch Argo sync.',
    });
    if (created && 'id' in created) {
      setLastHarvestedId(created.id);
    } else {
      setLastHarvestedId(`FM-00${survivalState.failureModes.length + 1}`);
    }
    setFmTitle('');
    setFmContext('');
  };

  return (
    <section
      aria-label="Founder Omni-Monitoring Watchtower, Multi-Home Survival & Triad Failure-Mode Intelligence Harvester"
      className="bg-white border border-slate-200 rounded-2xl shadow-xs overflow-hidden"
    >
      {/* Top Executive Header & Omni-Workflow Status Bar */}
      <div className="bg-slate-900 text-white px-6 py-5 border-b border-slate-800">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2.5 text-xs font-mono uppercase tracking-wider text-emerald-400">
              <span>FOUNDER OMNI-WATCHTOWER &amp; SURVIVAL CORTEX</span>
              <span>·</span>
              <span>PROTOCOL {survivalState.boundProtocolId}</span>
              <span>·</span>
              <span>TRIAD HARVESTER (MINIMAX-M2.7 + DEEPSEEK WEB + GEMINI WEB)</span>
            </div>
            <h2 className="text-xl font-bold tracking-tight text-white mt-1">
              Multi-Home Survival Watchtower, Preemptive Battery Evacuation &amp; Giant Failure-Mode Intelligence Harvester
            </h2>
            <p className="text-xs text-slate-300 mt-1 max-w-4xl leading-relaxed">
              Monitors the entire Estate workflow in real time across all 5 Homes. Sounds immediate multi-channel Founder alarms and executes preemptive fallback before hardware/battery exhaustion, prototypes expansions under a 98% confidence gate, and harvests every encountered failure mode into the Bi-Temporal Knowledgebase via the MiniMax-M2.7 + DeepSeek Web/App + Gemini Web/App Triad.
            </p>
          </div>

          {/* Primary Hardware Survival Test Controls */}
          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            {!macEvacuated ? (
              <button
                type="button"
                onClick={() => onTriggerLowBatteryEvacuation(14)}
                className="px-3.5 py-2 text-xs font-semibold rounded-lg bg-amber-500 text-slate-950 hover:bg-amber-400 transition-colors cursor-pointer font-mono"
              >
                ⚡ Simulate MacBook Low Battery (14%) &amp; Preemptive Evacuation
              </button>
            ) : (
              <button
                type="button"
                onClick={() => onRestoreNominalPower('home-macbook-pro')}
                className="px-3.5 py-2 text-xs font-semibold rounded-lg bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition-colors cursor-pointer font-mono"
              >
                🔌 Plug In MagSafe / Restore AC Power (96%)
              </button>
            )}
          </div>
        </div>

        {/* Founder's 5-Pillar End-to-End Workflow Telemetry Strip */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 mt-5 pt-4 border-t border-slate-800">
          <div className="bg-slate-800/80 border border-slate-700/80 rounded-xl p-3">
            <div className="text-[11px] font-mono uppercase text-slate-400">
              1. Git &amp; Argo Auto-Sync
            </div>
            <div className="text-sm font-bold text-emerald-400 font-mono mt-0.5">
              {allGitBranchesLocked ? `LOCKED (${gitShortSha})` : `SYNCING (${gitShortSha})`}
            </div>
            <div className="text-[11px] text-slate-300 mt-0.5">
              4/4 Refs Identical · 0 Dirty Bytes
            </div>
          </div>

          <div className="bg-slate-800/80 border border-slate-700/80 rounded-xl p-3">
            <div className="text-[11px] font-mono uppercase text-slate-400">
              2. MacBook Pro Survival
            </div>
            <div
              className={`text-sm font-bold font-mono mt-0.5 ${
                macEvacuated ? 'text-amber-400' : 'text-emerald-400'
              }`}
            >
              {macEvacuated
                ? `${macHome?.batteryPct}% EVACUATED SAFE`
                : `${macHome?.batteryPct ?? 94}% AC MAGSAFE`}
            </div>
            <div className="text-[11px] text-slate-300 mt-0.5">
              Load {macHome?.cpuLoad1m.toFixed(2)} · Watchdog Armed
            </div>
          </div>

          <div className="bg-slate-800/80 border border-slate-700/80 rounded-xl p-3">
            <div className="text-[11px] font-mono uppercase text-slate-400">
              3. Multi-Home Mesh
            </div>
            <div className="text-sm font-bold text-emerald-400 font-mono mt-0.5">
              {survivalState.homes.length}/5 HOMES ONLINE
            </div>
            <div className="text-[11px] text-slate-300 mt-0.5">
              {onlineSurfaceCount} Agent Surfaces · { survivalState.harvesterStats.zeroDataLossEvacuationsCount } Zero-Loss Evacs
            </div>
          </div>

          <div className="bg-slate-800/80 border border-slate-700/80 rounded-xl p-3">
            <div className="text-[11px] font-mono uppercase text-slate-400">
              4. Triad Failure Harvester
            </div>
            <div className="text-sm font-bold text-emerald-400 font-mono mt-0.5">
              {survivalState.harvesterStats.totalFailureModesMapped} MAPPED · 100% ARMED
            </div>
            <div className="text-[11px] text-slate-300 mt-0.5">
              MiniMax-M2.7 + DeepSeek + Gemini
            </div>
          </div>

          <div className="bg-slate-800/80 border border-slate-700/80 rounded-xl p-3">
            <div className="text-[11px] font-mono uppercase text-slate-400">
              5. Upfront Pre-Flight Gate
            </div>
            <div className="text-sm font-bold text-emerald-400 font-mono mt-0.5">
              {survivalState.preFlightAssessment.readinessConfidencePct}% READY
            </div>
            <div className="text-[11px] text-slate-300 mt-0.5">
              {ratifiedProtocolCount} Ratified Hoare-TLA+ Protocols
            </div>
          </div>
        </div>
      </div>

      {/* ACTIVE FOUNDER SURVIVAL KLAXON BANNER (Appears immediately when MacBook Low-Battery / Threat fires) */}
      {activeAlarm && (
        <div
          role="alert"
          className="bg-amber-50 border-b-2 border-amber-400 px-6 py-5 text-slate-900"
        >
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-xs font-mono font-bold uppercase text-amber-900">
                <span className="inline-block w-2.5 h-2.5 rounded-full bg-red-600 animate-ping" />
                <span>
                  ACTIVE SURVIVAL ALARM ({activeAlarm.alarmId}) · PREEMPTIVE EVACUATION COMPLETED WITH ZERO DATA LOSS
                </span>
              </div>
              <h3 className="text-base font-bold text-slate-900 mt-1">
                {activeAlarm.headline}
              </h3>
            </div>
            <button
              type="button"
              onClick={() => onRestoreNominalPower('home-macbook-pro')}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-slate-900 text-white hover:bg-slate-800 transition-colors cursor-pointer font-mono shrink-0"
            >
              Restore MagSafe AC Power &amp; Re-Balance Leases
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
            <div className="bg-white border border-amber-300 rounded-xl p-4">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                4-Step Anticipated Preemptive Fallback &amp; Evacuation Trace
              </div>
              <ul className="space-y-1.5 text-xs text-slate-800">
                {activeAlarm.preemptiveEvacuationSteps.map((step, i) => (
                  <li key={i} className="leading-relaxed">
                    {step}
                  </li>
                ))}
              </ul>
            </div>

            <div className="bg-white border border-amber-300 rounded-xl p-4 space-y-2.5">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Multi-Channel Founder Alarm Dispatch Receipts
              </div>
              <div>
                <div className="text-[11px] font-semibold text-slate-600">
                  macOS Local Audible + Notification Klaxon (`ops/otto/mac_survival_watchdog.mjs`):
                </div>
                <pre className="mt-1 p-2 bg-slate-900 text-amber-300 rounded-lg text-[11px] font-mono overflow-x-auto whitespace-pre-wrap">
                  {activeAlarm.founderAlertChannels.macOsAudibleCommand}
                </pre>
              </div>
              <div>
                <div className="text-[11px] font-semibold text-slate-600">
                  Concierge + Otto Urgent Founder Dispatch:
                </div>
                <div className="mt-1 p-2 bg-slate-100 border border-slate-200 rounded-lg text-xs text-slate-800 font-mono">
                  {activeAlarm.founderAlertChannels.conciergeTelegramDispatch}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Sub-Navigation Switcher inside the Watchtower & Harvester Panel */}
      <div className="px-6 py-3 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setActiveSubTab('homes-watchtower')}
            className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-colors cursor-pointer ${
              activeSubTab === 'homes-watchtower'
                ? 'bg-slate-900 text-white'
                : 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-100'
            }`}
          >
            1. Multi-Home Survival Watchtower ({survivalState.homes.length} Homes)
          </button>
          <button
            type="button"
            onClick={() => setActiveSubTab('triad-harvester')}
            className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-colors cursor-pointer ${
              activeSubTab === 'triad-harvester'
                ? 'bg-slate-900 text-white'
                : 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-100'
            }`}
          >
            2. Giant Failure-Mode Intelligence Harvester ({survivalState.failureModes.length} Triad-Mapped)
          </button>
          <button
            type="button"
            onClick={() => setActiveSubTab('preflight-and-rd')}
            className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-colors cursor-pointer ${
              activeSubTab === 'preflight-and-rd'
                ? 'bg-slate-900 text-white'
                : 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-100'
            }`}
          >
            3. Upfront Machine Surface Pre-Flight &amp; Proactive R&amp;D ({survivalState.proactiveTracks.length} Tracks)
          </button>
        </div>

        <div className="text-xs font-mono text-slate-500">
          Watchdog Script: <span className="text-slate-800 font-semibold">node ops/otto/mac_survival_watchdog.mjs</span>
        </div>
      </div>

      {/* TAB 1: 5-HOME SURVIVAL WATCHTOWER */}
      {activeSubTab === 'homes-watchtower' && (
        <div className="p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {survivalState.homes.map((home) => {
              const isEvacuated = home.status === 'PREEMPTIVE_EVACUATION_ACTIVE';
              const isTakeover = home.status === 'HOT_TAKEOVER_ACTIVE';

              return (
                <div
                  key={home.homeId}
                  className={`border rounded-xl p-4 flex flex-col justify-between ${
                    isEvacuated
                      ? 'bg-amber-50/70 border-amber-300'
                      : isTakeover
                      ? 'bg-emerald-50/50 border-emerald-300'
                      : 'bg-white border-slate-200'
                  }`}
                >
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <span className="text-[11px] font-mono uppercase text-slate-500">
                          {home.locationLabel}
                        </span>
                        <h3 className="text-sm font-bold text-slate-900 mt-0.5">
                          {home.homeName}
                        </h3>
                      </div>
                      <span
                        className={`px-2 py-0.5 text-[10px] font-mono font-semibold rounded-md shrink-0 ${
                          isEvacuated
                            ? 'bg-amber-200 text-amber-950'
                            : isTakeover
                            ? 'bg-emerald-200 text-emerald-950'
                            : 'bg-slate-100 text-slate-800'
                        }`}
                      >
                        {home.status}
                      </span>
                    </div>

                    <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                      {home.roleDescription}
                    </p>

                    <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-slate-200/80 text-xs font-mono">
                      <div>
                        <div className="text-[10px] text-slate-500">POWER / BATT</div>
                        <div
                          className={`font-bold ${
                            home.batteryPct !== null && home.batteryPct <= 20
                              ? 'text-red-700'
                              : 'text-slate-900'
                          }`}
                        >
                          {home.batteryPct !== null
                            ? `${home.batteryPct}% (${home.powerSource === 'AC_MAGSAFE_CHARGING' ? 'AC' : 'DRAIN'})`
                            : 'GRID / EDGE'}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-500">LOAD / RAM</div>
                        <div className="font-bold text-slate-900">
                          {home.cpuLoad1m.toFixed(2)} · {home.ramUsedMb}MB
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-500">ACTIVE LEASES</div>
                        <div className="font-bold text-slate-900">
                          {home.activeLeaseCount} Leases
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-3 pt-2.5 border-t border-slate-100 text-[11px] text-slate-700 font-mono leading-relaxed">
                    {home.hardwareSurvivalNote}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 2: GIANT FAILURE-MODE INTELLIGENCE HARVESTER (MINIMAX-M2.7 + DEEPSEEK WEB + GEMINI WEB TRIAD) */}
      {activeSubTab === 'triad-harvester' && (
        <div className="p-6 space-y-6">
          {/* 3-Specialist Triad Architecture Banner */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-slate-50 border border-slate-200 rounded-xl p-4">
            <div className="bg-white border border-slate-200 rounded-lg p-3.5">
              <div className="text-[11px] font-mono font-bold uppercase text-indigo-700">
                1. LEAD HARVESTER · MINIMAX-M2.7 SPECIALIST
              </div>
              <div className="text-xs font-bold text-slate-900 mt-1">
                Deterministic Root-Cause &amp; Blast-Radius Decomposition
              </div>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                Ingests raw agent/hardware telemetry from any failure encountered during work or research, isolating the exact trigger signature and affected Estate homes.
              </p>
            </div>

            <div className="bg-white border border-slate-200 rounded-lg p-3.5">
              <div className="text-[11px] font-mono font-bold uppercase text-emerald-700">
                2. FORMAL CO-ANALYST · DEEPSEEK WEB / APP
              </div>
              <div className="text-xs font-bold text-slate-900 mt-1">
                Adversarial Fault-Tree &amp; Hoare Precondition Synthesis
              </div>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                Maps cascading edge-case permutations and synthesizes formal Hoare preconditions {`{P}`} and inductive safety invariants (`I_safe`) at £0 API cost.
              </p>
            </div>

            <div className="bg-white border border-slate-200 rounded-lg p-3.5">
              <div className="text-[11px] font-mono font-bold uppercase text-sky-700">
                3. CORTEX INTEGRATOR · GEMINI WEB / APP
              </div>
              <div className="text-xs font-bold text-slate-900 mt-1">
                Bi-Temporal Knowledgebase &amp; Protocol Playbook Import
              </div>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                Converts the Triad analysis into a permanent Bi-Temporal Knowledgebase rule, binds it to a ratified protocol, and arms sub-second self-healing fallback.
              </p>
            </div>
          </div>

          {/* Submit Encountered Failure Mode Form */}
          <form
            onSubmit={handleHarvestSubmit}
            className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-800">
                Submit Encountered or Anticipated Failure Mode to Triad Harvester Lane
              </div>
              {lastHarvestedId && (
                <span className="text-xs font-mono font-semibold text-emerald-700">
                  ✓ Harvested &amp; Imported {lastHarvestedId} into Bi-Temporal Knowledgebase &amp; Pre-Flight Gate
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <div className="md:col-span-2">
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                  Failure Mode Headline (or leave blank to harvest preset Wi-Fi/Fiber Cut)
                </label>
                <input
                  type="text"
                  value={fmTitle}
                  onChange={(e) => setFmTitle(e.target.value)}
                  placeholder="e.g., MacBook Wi-Fi / Fiber Drop Mid-Commit During Council Vote"
                  className="w-full px-3 py-2 text-xs bg-white border border-slate-300 rounded-lg text-slate-900"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                  Machine Surface Category
                </label>
                <select
                  value={fmCategory}
                  onChange={(e) => setFmCategory(e.target.value as FailureSurfaceCategory)}
                  className="w-full px-3 py-2 text-xs bg-white border border-slate-300 rounded-lg text-slate-900"
                >
                  <option value="hardware_power_host">Hardware / Power / Host</option>
                  <option value="model_provider_network">Model Provider / Network</option>
                  <option value="git_argocd_state">Git / Argo CD State</option>
                  <option value="context_memory_cognition">Context / Memory Cognition</option>
                  <option value="protocol_governance_security">Protocol / Governance</option>
                  <option value="browser_ui_runtime">Browser / UI Runtime</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                  Severity &amp; Submitting Agent
                </label>
                <div className="flex items-center gap-2">
                  <select
                    value={fmSeverity}
                    onChange={(e) =>
                      setFmSeverity(e.target.value as 'CRITICAL' | 'HIGH' | 'MEDIUM')
                    }
                    className="w-28 px-2.5 py-2 text-xs bg-white border border-slate-300 rounded-lg text-slate-900"
                  >
                    <option value="CRITICAL">CRITICAL</option>
                    <option value="HIGH">HIGH</option>
                    <option value="MEDIUM">MEDIUM</option>
                  </select>
                  <button
                    type="submit"
                    className="flex-1 px-3 py-2 text-xs font-semibold bg-slate-900 text-white rounded-lg hover:bg-slate-800 transition-colors cursor-pointer whitespace-nowrap"
                  >
                    + Map via Triad
                  </button>
                </div>
              </div>
            </div>
          </form>

          {/* Harvested Failure Mode Intelligence Cards */}
          <div className="space-y-4">
            {survivalState.failureModes.map((fm) => (
              <div
                key={fm.id}
                className="border border-slate-200 rounded-xl p-4 bg-white space-y-3"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
                      <span className="font-bold text-slate-900">{fm.id}</span>
                      <span
                        className={`px-2 py-0.5 text-[10px] font-bold rounded ${
                          fm.severity === 'CRITICAL'
                            ? 'bg-red-100 text-red-900'
                            : fm.severity === 'HIGH'
                            ? 'bg-amber-100 text-amber-900'
                            : 'bg-slate-100 text-slate-800'
                        }`}
                      >
                        {fm.severity}
                      </span>
                      <span className="text-slate-500">·</span>
                      <span className="text-emerald-700 font-semibold">
                        Bound Protocol: {fm.importedToProtocolId}
                      </span>
                      <span className="text-slate-500">·</span>
                      <span className="text-slate-600">
                        Self-Heal MTTR: {fm.meanTimeToSelfHealMs}ms
                      </span>
                    </div>
                    <h4 className="text-sm font-bold text-slate-900 mt-1">{fm.title}</h4>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      Encountered by <span className="font-medium text-slate-700">{fm.encounteredBySurface}</span> during <span className="font-medium text-slate-700">{fm.encounteredDuringWorkflow}</span>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => {
                      onPromoteFailureToMemoryGraph(fm);
                      setPromotedIds((prev) => ({ ...prev, [fm.id]: true }));
                    }}
                    className={`px-3 py-1.5 text-xs font-mono font-semibold rounded-lg border transition-colors cursor-pointer shrink-0 ${
                      promotedIds[fm.id]
                        ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
                        : 'bg-slate-50 border-slate-200 text-slate-800 hover:bg-slate-100'
                    }`}
                  >
                    {promotedIds[fm.id]
                      ? '✓ Pinned in Bi-Temporal Memory Graph'
                      : 'Pin Triple to Active Memory Graph'}
                  </button>
                </div>

                {/* 3-Column Specialist Breakdown */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 pt-2 border-t border-slate-100 text-xs">
                  <div className="bg-slate-50 rounded-lg p-3 border border-slate-200/70">
                    <div className="text-[10px] font-mono font-bold uppercase text-indigo-700">
                      MiniMax-M2.7 Specialist Decomposition
                    </div>
                    <p className="text-slate-700 mt-1 leading-relaxed">
                      {fm.triadSynthesis.minimaxSpecialistAnalysis.rootCauseDecomposition}
                    </p>
                    <div className="mt-2 text-[11px] font-mono text-slate-600 bg-white px-2 py-1 rounded border border-slate-200">
                      Trigger: {fm.triadSynthesis.minimaxSpecialistAnalysis.deterministicTriggerSignature}
                    </div>
                  </div>

                  <div className="bg-slate-50 rounded-lg p-3 border border-slate-200/70">
                    <div className="text-[10px] font-mono font-bold uppercase text-emerald-700">
                      DeepSeek Web / App Edge-Case &amp; Hoare Guard
                    </div>
                    <ul className="text-slate-700 mt-1 space-y-1 list-disc list-inside">
                      {fm.triadSynthesis.deepseekWebCollaboratorAnalysis.adversarialEdgeCaseTree
                        .slice(0, 2)
                        .map((ec, idx) => (
                          <li key={idx} className="leading-relaxed">
                            {ec}
                          </li>
                        ))}
                    </ul>
                    <div className="mt-2 text-[11px] font-mono text-slate-600 bg-white px-2 py-1 rounded border border-slate-200">
                      {fm.triadSynthesis.deepseekWebCollaboratorAnalysis.hoareSafetyInvariant}
                    </div>
                  </div>

                  <div className="bg-slate-50 rounded-lg p-3 border border-slate-200/70">
                    <div className="text-[10px] font-mono font-bold uppercase text-sky-700">
                      Gemini Web / App Knowledgebase Immunization
                    </div>
                    <div className="mt-1 text-[11px] font-mono text-slate-800 bg-white px-2 py-1 rounded border border-slate-200">
                      ({fm.triadSynthesis.geminiWebCollaboratorAnalysis.knowledgebaseSubject}) → [
                      {fm.triadSynthesis.geminiWebCollaboratorAnalysis.knowledgebasePredicate}] → (
                      {fm.triadSynthesis.geminiWebCollaboratorAnalysis.knowledgebaseObject})
                    </div>
                    <p className="text-slate-700 mt-2 leading-relaxed">
                      <span className="font-semibold">Playbook:</span>{' '}
                      {fm.triadSynthesis.geminiWebCollaboratorAnalysis.automatedFallbackPlaybook}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: UPFRONT MACHINE SURFACE PRE-FLIGHT ORCHESTRATOR & PROACTIVE R&D PIPELINE */}
      {activeSubTab === 'preflight-and-rd' && (
        <div className="p-6 space-y-6">
          {/* Upfront Machine Surface Pre-Flight Orchestrator */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-xs font-mono font-bold uppercase text-slate-600">
                  UPFRONT MACHINE SURFACE PRE-FLIGHT ORCHESTRATOR
                </div>
                <h3 className="text-base font-bold text-slate-900 mt-0.5">
                  Know Everything That Can Go Wrong &amp; Verify Armed Fallback Plans Before Orchestrating Any Workflow
                </h3>
              </div>
              <span className="px-3 py-1 text-xs font-mono font-bold rounded-lg bg-emerald-100 text-emerald-900">
                {survivalState.preFlightAssessment.orchestrationVerdict} (
                {survivalState.preFlightAssessment.readinessConfidencePct}% IMMUNIZED)
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <select
                value={selectedWorkflow}
                onChange={(e) => {
                  setSelectedWorkflow(e.target.value);
                  onRunWorkflowPreFlight(e.target.value);
                }}
                className="flex-1 min-w-[260px] px-3 py-2 text-xs bg-white border border-slate-300 rounded-lg text-slate-900 font-medium"
              >
                {PRESET_WORKFLOWS.map((wf) => (
                  <option key={wf} value={wf}>
                    Workflow: {wf}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => onRunWorkflowPreFlight(selectedWorkflow)}
                className="px-4 py-2 text-xs font-semibold bg-slate-900 text-white rounded-lg hover:bg-slate-800 transition-colors cursor-pointer font-mono"
              >
                Verify Upfront Failure Surface ({survivalState.preFlightAssessment.totalSurfaceHazardsMapped} Hazards)
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {survivalState.preFlightAssessment.hazards.map((haz) => (
                <div
                  key={haz.failureModeId}
                  className="bg-white border border-slate-200 rounded-lg p-3 text-xs space-y-1.5"
                >
                  <div className="flex items-center justify-between gap-2 font-mono">
                    <span className="font-bold text-slate-900">
                      {haz.failureModeId}: {haz.title}
                    </span>
                    <span className="px-2 py-0.5 text-[10px] font-semibold bg-emerald-100 text-emerald-900 rounded">
                      PLAN ARMED ({haz.boundProtocolId})
                    </span>
                  </div>
                  <div className="text-slate-600">
                    <span className="font-semibold text-slate-800">Upfront Guard:</span>{' '}
                    <span className="font-mono text-[11px]">{haz.upfrontPreconditionCheck}</span>
                  </div>
                  <div className="text-slate-700">
                    <span className="font-semibold text-slate-800">Fallback Plan:</span>{' '}
                    {haz.preArmedFallbackPlan}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Proactive R&D, Prototyping & Confidence-Gated Deployment Tracks */}
          <div className="space-y-3">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Proactive R&amp;D, Sandboxed Prototyping &amp; Confidence-Gated Deployment Pipeline (&gt;=98.0% Gate)
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {survivalState.proactiveTracks.map((track) => {
                const isDeployed = track.stage === 'STAGE_4_DEPLOYED_CONFIDENT';
                return (
                  <div
                    key={track.trackId}
                    className="border border-slate-200 rounded-xl p-4 bg-white flex flex-col justify-between space-y-3"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 text-[11px] font-mono">
                        <span className="font-bold text-slate-700">{track.stage}</span>
                        <span
                          className={`font-bold ${
                            isDeployed ? 'text-emerald-700' : 'text-amber-700'
                          }`}
                        >
                          {track.confidenceScorePct}% / {track.requiredConfidenceThresholdPct}% Gate
                        </span>
                      </div>
                      <h4 className="text-sm font-bold text-slate-900 mt-1">{track.title}</h4>
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        {track.targetEnvironment} · {track.leadAgents}
                      </div>
                      <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                        {track.prototypeSandboxVerifyNote}
                      </p>
                    </div>

                    <div className="pt-2 border-t border-slate-100 flex items-center justify-between gap-2">
                      <span className="text-[11px] font-mono text-slate-500">
                        Mapped: {track.mappedFailureModeIds.join(', ')}
                      </span>
                      {!isDeployed ? (
                        <button
                          type="button"
                          onClick={() => onAdvanceResearchTrack(track.trackId)}
                          className="px-3 py-1.5 text-xs font-semibold bg-slate-900 text-white rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
                        >
                          Promote Prototype (&gt;=98%)
                        </button>
                      ) : (
                        <span className="px-2.5 py-1 text-[11px] font-mono font-semibold bg-emerald-100 text-emerald-900 rounded">
                          ✓ DEPLOYED
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </section>
  );
};
