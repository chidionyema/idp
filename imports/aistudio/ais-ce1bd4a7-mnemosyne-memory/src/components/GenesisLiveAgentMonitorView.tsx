import React, { useState } from 'react';
import {
  GenesisAgentProfile,
  GenesisAgentMemoryConfig,
  AgentMemoryBlock,
} from '../engine/memoryEngine';
import {
  Play,
  Pause,
  Sliders,
  Zap,
  Pin,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Plus,
  Layers,
} from 'lucide-react';

interface GenesisLiveAgentMonitorViewProps {
  agents: GenesisAgentProfile[];
  selectedAgentId: string;
  liveStreamEnabled: boolean;
  onSelectAgent: (agentId: string) => void;
  onToggleLiveStream: () => void;
  onStepAgentTick: (
    agentId: string,
    customStimulus?: {
      label: string;
      content: string;
      surprise: number;
      salience: number;
    }
  ) => void;
  onUpdateAgentConfig: (
    agentId: string,
    partialConfig: Partial<GenesisAgentMemoryConfig>,
    applyToAll?: boolean
  ) => void;
  onTogglePinBlock: (agentId: string, blockId: string) => void;
  onEvictBlock: (agentId: string, blockId: string) => void;
  onRegisterNewAgent: (name: string, role: string, ramBudget: number) => void;
}

export const GenesisLiveAgentMonitorView: React.FC<GenesisLiveAgentMonitorViewProps> = ({
  agents,
  selectedAgentId,
  liveStreamEnabled,
  onSelectAgent,
  onToggleLiveStream,
  onStepAgentTick,
  onUpdateAgentConfig,
  onTogglePinBlock,
  onEvictBlock,
  onRegisterNewAgent,
}) => {
  const selectedAgent = agents.find((a) => a.id === selectedAgentId) || agents[0];

  const [stimLabel, setStimLabel] = useState('');
  const [stimContent, setStimContent] = useState('');
  const [stimSurprise, setStimSurprise] = useState(0.92);
  const [stimSalience, setStimSalience] = useState(0.94);
  const [stimError, setStimError] = useState<string | null>(null);
  const [feedbackBanner, setFeedbackBanner] = useState<string | null>(null);

  const [newAgentName, setNewAgentName] = useState('');
  const [newAgentRole, setNewAgentRole] = useState('');
  const [newAgentError, setNewAgentError] = useState<string | null>(null);

  const activeWindowBlocks = selectedAgent.memoryBlocks.filter(
    (b) => b.zone !== 'paged_archival'
  );
  const pagedArchivalBlocks = selectedAgent.memoryBlocks.filter(
    (b) => b.zone === 'paged_archival'
  );
  const usedRamTokens = activeWindowBlocks.reduce((acc, b) => acc + b.tokens, 0);
  const latestTrace = selectedAgent.recentTraces[0] || null;

  const handleInjectStimulus = (e: React.FormEvent) => {
    e.preventDefault();
    if (!stimLabel.trim() || !stimContent.trim()) {
      setStimError('Both Fact Key / Subject and Stimulus Content are required to inject into the agent pipeline.');
      return;
    }
    setStimError(null);
    onStepAgentTick(selectedAgent.id, {
      label: stimLabel.trim(),
      content: stimContent.trim(),
      surprise: stimSurprise,
      salience: stimSalience,
    });
    setFeedbackBanner(
      `Injected live stimulus "${stimLabel.trim()}" into ${selectedAgent.name} and executed 5-stage memory pipeline.`
    );
    setStimLabel('');
    setStimContent('');
  };

  const handleCreateAgent = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAgentName.trim() || !newAgentRole.trim()) {
      setNewAgentError('Please enter both an Agent Name and Operational Role.');
      return;
    }
    setNewAgentError(null);
    onRegisterNewAgent(newAgentName.trim(), newAgentRole.trim(), 4096);
    setFeedbackBanner(
      `Registered new Genesis Agent "${newAgentName.trim()}" with live real-time memory telemetry.`
    );
    setNewAgentName('');
    setNewAgentRole('');
  };

  return (
    <div className="space-y-8">
      {/* Top Executive Command Bar for Genesis Real-Time Agent Fleet */}
      <section className="bg-white border border-slate-200 rounded-xl p-6 space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-6 border-b border-slate-200 pb-5">
          <div className="max-w-3xl space-y-1.5">
            <div className="text-xs text-slate-500">
              Genesis Sovereign Memory OS · Real-Time Per-Agent Memory Configurator &amp; X-Ray Monitor
            </div>
            <h1 className="text-2xl font-bold text-slate-900">
              Live Genesis Agent Memory Telemetry &amp; Control Plane
            </h1>
            <p className="text-sm text-slate-600 leading-relaxed">
              Select any agent running on the Genesis system to inspect its exact 5-stage memory pipeline in real time, tune its Titans Surprise Gate threshold, adjust its Working Focus RAM ceiling, or toggle Bi-Temporal Atomic Invalidation on the fly.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <button
              type="button"
              onClick={onToggleLiveStream}
              className={`px-4 py-2.5 text-xs font-semibold rounded-lg border transition-colors inline-flex items-center gap-2 whitespace-nowrap cursor-pointer ${
                liveStreamEnabled
                  ? 'bg-emerald-50 border-emerald-300 text-emerald-900 hover:bg-emerald-100'
                  : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50'
              }`}
            >
              {liveStreamEnabled ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              {liveStreamEnabled ? 'Real-Time Stream: ON (2.5s Tick)' : 'Resume Real-Time Stream'}
            </button>

            <button
              type="button"
              onClick={() => {
                onStepAgentTick(selectedAgent.id);
                setFeedbackBanner(
                  `Executed manual real-time memory tick #${selectedAgent.tickCount + 1} on ${selectedAgent.name}.`
                );
              }}
              className="px-4 py-2.5 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors inline-flex items-center gap-2 whitespace-nowrap cursor-pointer"
            >
              <Zap className="w-4 h-4" />
              Step Agent Memory Tick
            </button>
          </div>
        </div>

        {feedbackBanner && (
          <div
            role="status"
            className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-900 flex items-center gap-2"
          >
            <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
            <span>{feedbackBanner}</span>
          </div>
        )}

        {/* Agent Selector Strip */}
        <div className="space-y-2">
          <div className="text-xs font-semibold text-slate-600">
            Select Active Genesis Agent to Configure &amp; Monitor ({agents.length} Agents Online):
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {agents.map((agent) => {
              const isSelected = agent.id === selectedAgent.id;
              return (
                <button
                  key={agent.id}
                  type="button"
                  onClick={() => onSelectAgent(agent.id)}
                  className={`text-left p-4 rounded-xl border transition-colors cursor-pointer flex flex-col justify-between space-y-3 ${
                    isSelected
                      ? 'bg-slate-900 text-white border-slate-900'
                      : 'bg-slate-50 text-slate-900 border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  <div>
                    <div
                      className={`text-xs font-mono tabular-nums ${
                        isSelected ? 'text-slate-300' : 'text-slate-500'
                      }`}
                    >
                      {agent.id} · Tick #{agent.tickCount} · {agent.status.toUpperCase()}
                    </div>
                    <div className="text-base font-bold mt-0.5">{agent.name}</div>
                    <div
                      className={`text-xs mt-0.5 ${
                        isSelected ? 'text-slate-300' : 'text-slate-600'
                      }`}
                    >
                      {agent.role}
                    </div>
                  </div>

                  <div
                    className={`pt-2.5 border-t flex items-center justify-between text-xs font-mono tabular-nums ${
                      isSelected
                        ? 'border-slate-700 text-emerald-300'
                        : 'border-slate-200 text-slate-700'
                    }`}
                  >
                    <span>Recall: {agent.liveMetrics.agentRecallAccuracyPct}%</span>
                    <span>Rot: {agent.liveMetrics.agentRotIndex}</span>
                    <span>RAM: {agent.liveMetrics.activeRamUtilizationPct}%</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </section>

      {/* Main Split: Left = Real-Time Memory Policy Configurator | Right = 5-Stage Live Pipeline X-Ray */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Live Per-Agent Memory Configuration Controls */}
        <section className="lg:col-span-5 bg-white border border-slate-200 rounded-xl p-6 space-y-5">
          <div className="flex items-start justify-between gap-3 border-b border-slate-200 pb-4">
            <div>
              <div className="text-xs text-slate-500 font-mono">{selectedAgent.id}</div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 mt-0.5">
                <Sliders className="w-4 h-4 text-slate-700" />
                Real-Time Memory Configuration
              </h2>
            </div>
            <button
              type="button"
              onClick={() => {
                onUpdateAgentConfig(selectedAgent.id, selectedAgent.config, true);
                setFeedbackBanner(
                  `Broadcasted ${selectedAgent.name}'s memory configuration globally across all ${agents.length} Genesis agents.`
                );
              }}
              className="px-3 py-1.5 text-xs font-semibold text-slate-800 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors cursor-pointer whitespace-nowrap"
            >
              Apply Policy to All Agents
            </button>
          </div>

          {/* Control 1: Working Focus RAM Budget */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <label htmlFor="cfg-ram-budget" className="font-semibold text-slate-800">
                1. Working Focus RAM Budget (Virtual Context Ceiling)
              </label>
              <span className="font-mono tabular-nums font-bold text-slate-900">
                {selectedAgent.config.workingRamBudgetTokens} Tokens
              </span>
            </div>
            <select
              id="cfg-ram-budget"
              value={selectedAgent.config.workingRamBudgetTokens}
              onChange={(e) =>
                onUpdateAgentConfig(selectedAgent.id, {
                  workingRamBudgetTokens: Number(e.target.value),
                })
              }
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-slate-900"
            >
              <option value={1536}>1,536 Tokens (Aggressive Paging — Ultra-Low Latency)</option>
              <option value={2048}>2,048 Tokens (Compact Sub-Agent Focus)</option>
              <option value={4096}>4,096 Tokens (Standard Genesis Sovereign Window)</option>
              <option value={8192}>8,192 Tokens (Deep Architectural Synthesis Window)</option>
            </select>
            <p className="text-[11px] text-slate-500">
              When active blocks exceed this ceiling, lowest-salience unpinned blocks page out to archival disk automatically.
            </p>
          </div>

          {/* Control 2: Titans Surprise Gate Threshold */}
          <div className="space-y-1.5 pt-2 border-t border-slate-100">
            <div className="flex items-center justify-between text-xs">
              <label htmlFor="cfg-surprise-threshold" className="font-semibold text-slate-800">
                2. Titans Surprise Gate Threshold (θ_surprise)
              </label>
              <span className="font-mono tabular-nums font-bold text-slate-900">
                θ = {selectedAgent.config.surpriseThreshold.toFixed(2)}
              </span>
            </div>
            <input
              id="cfg-surprise-threshold"
              type="range"
              min="0.15"
              max="0.90"
              step="0.05"
              value={selectedAgent.config.surpriseThreshold}
              onChange={(e) =>
                onUpdateAgentConfig(selectedAgent.id, {
                  surpriseThreshold: Number(e.target.value),
                })
              }
              className="w-full accent-slate-900 cursor-pointer"
            />
            <div className="flex justify-between text-[11px] text-slate-400 font-mono">
              <span>0.15 (Permissive)</span>
              <span>0.62 (Optimal Gate)</span>
              <span>0.90 (Strict Invariants Only)</span>
            </div>
          </div>

          {/* Control 3: Prefix Sink Allocation % */}
          <div className="space-y-1.5 pt-2 border-t border-slate-100">
            <div className="flex items-center justify-between text-xs">
              <label htmlFor="cfg-prefix-sink" className="font-semibold text-slate-800">
                3. Attention Sink Prefix Allocation (StreamingLLM / H2O)
              </label>
              <span className="font-mono tabular-nums font-bold text-slate-900">
                {selectedAgent.config.prefixSinkAllocationPct}% of Window
              </span>
            </div>
            <input
              id="cfg-prefix-sink"
              type="range"
              min="5"
              max="30"
              step="5"
              value={selectedAgent.config.prefixSinkAllocationPct}
              onChange={(e) =>
                onUpdateAgentConfig(selectedAgent.id, {
                  prefixSinkAllocationPct: Number(e.target.value),
                })
              }
              className="w-full accent-slate-900 cursor-pointer"
            />
          </div>

          {/* Control 4: Bi-Temporal Contradiction Resolution Mode */}
          <div className="space-y-1.5 pt-2 border-t border-slate-100">
            <label htmlFor="cfg-bitemporal-mode" className="block text-xs font-semibold text-slate-800">
              4. Bi-Temporal Contradiction Resolution Policy
            </label>
            <select
              id="cfg-bitemporal-mode"
              value={selectedAgent.config.bitemporalMode}
              onChange={(e) =>
                onUpdateAgentConfig(selectedAgent.id, {
                  bitemporalMode: e.target.value as GenesisAgentMemoryConfig['bitemporalMode'],
                })
              }
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-slate-900"
            >
              <option value="strict_atomic_invalidation">
                Strict Atomic Invalidation (Close t_invalid &amp; Evict Stale Edge)
              </option>
              <option value="append_only_legacy">
                Legacy Append-Only (Keep Stale Contradictions in Window — Vulnerable to Rot)
              </option>
            </select>
          </div>

          {/* Control 5: Middle-Trough Auto-Defragmentation Toggle */}
          <div className="pt-2 border-t border-slate-100 flex items-center justify-between gap-4">
            <div>
              <div className="text-xs font-semibold text-slate-800">
                5. Lost-in-the-Middle Auto-Defragmentation
              </div>
              <div className="text-[11px] text-slate-500">
                Automatically re-anchor high-salience blocks out of the 35%–65% middle trough.
              </div>
            </div>
            <button
              type="button"
              onClick={() =>
                onUpdateAgentConfig(selectedAgent.id, {
                  autoDefragMiddleTrough: !selectedAgent.config.autoDefragMiddleTrough,
                })
              }
              className={`px-3 py-1.5 text-xs font-semibold rounded-md border transition-colors cursor-pointer whitespace-nowrap ${
                selectedAgent.config.autoDefragMiddleTrough
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-slate-100 text-slate-700 border-slate-300'
              }`}
            >
              {selectedAgent.config.autoDefragMiddleTrough ? 'Enabled' : 'Disabled'}
            </button>
          </div>
        </section>

        {/* Right Column: Live 5-Stage Memory Pipeline X-Ray & Active Context Window Map */}
        <section className="lg:col-span-7 bg-white border border-slate-200 rounded-xl p-6 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
            <div>
              <div className="text-xs text-slate-500 font-mono">
                LIVE X-RAY · {selectedAgent.name.toUpperCase()} · TICK #{selectedAgent.tickCount}
              </div>
              <h2 className="text-base font-bold text-slate-900 mt-0.5">
                Real-Time 5-Stage Memory Pipeline Execution Trace
              </h2>
            </div>

            <div className="flex items-center gap-4 text-xs font-mono tabular-nums">
              <span>Noise Filtered: {selectedAgent.liveMetrics.filteredNoiseEvents}</span>
              <span>·</span>
              <span>Contradictions Fixed: {selectedAgent.liveMetrics.resolvedContradictions}</span>
              <span>·</span>
              <span>p95: {selectedAgent.liveMetrics.p95LookupMs} ms</span>
            </div>
          </div>

          {/* 5-Stage Pipeline Trace Breakdown for Latest Tick */}
          {latestTrace && (
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3 text-xs">
              <div className="flex items-center justify-between border-b border-slate-200 pb-2 font-mono text-[11px] text-slate-500">
                <span>Trace ID: {latestTrace.traceId} (Tick #{latestTrace.tick})</span>
                <span>{latestTrace.timestampIso}</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="bg-white border border-slate-200 rounded-lg p-3 space-y-1">
                  <div className="font-mono text-[11px] text-slate-500">STAGE 1 · INCOMING STIMULUS</div>
                  <div className="font-semibold text-slate-900">{latestTrace.stage1Stimulus}</div>
                </div>

                <div className="bg-white border border-slate-200 rounded-lg p-3 space-y-1">
                  <div className="font-mono text-[11px] text-slate-500">STAGE 2 · TITANS SURPRISE GATE</div>
                  <div className="flex items-center justify-between font-mono tabular-nums">
                    <span>
                      Surprise {latestTrace.stage2SurpriseGate.computedSurprise.toFixed(2)} vs θ=
                      {latestTrace.stage2SurpriseGate.thresholdUsed.toFixed(2)}
                    </span>
                    <span
                      className={`font-bold ${
                        latestTrace.stage2SurpriseGate.decision === 'PROMOTED_TO_FOCUS'
                          ? 'text-emerald-700'
                          : 'text-amber-700'
                      }`}
                    >
                      {latestTrace.stage2SurpriseGate.decision}
                    </span>
                  </div>
                </div>

                <div className="bg-white border border-slate-200 rounded-lg p-3 space-y-1">
                  <div className="font-mono text-[11px] text-slate-500">
                    STAGE 3 · BI-TEMPORAL CONTRADICTION CHECK
                  </div>
                  <div className="text-slate-800">{latestTrace.stage3BiTemporalResolution.outcome}</div>
                </div>

                <div className="bg-white border border-slate-200 rounded-lg p-3 space-y-1">
                  <div className="font-mono text-[11px] text-slate-500">
                    STAGE 4 &amp; 5 · RAM PLACEMENT &amp; SHA-256 RECEIPT
                  </div>
                  <div className="font-mono tabular-nums text-slate-800">
                    Zone: {latestTrace.stage4WindowPlacement.assignedZone} · RAM:{' '}
                    {latestTrace.stage4WindowPlacement.usedRamTokens}/
                    {latestTrace.stage4WindowPlacement.ramCeilingTokens} tok
                  </div>
                  <div className="font-mono text-[11px] text-emerald-700 truncate">
                    SHA-256: {latestTrace.stage5ReceiptHash}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Active Context Window Memory Blocks Table */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                <Layers className="w-4 h-4 text-slate-700" />
                Active Context Window RAM ({usedRamTokens} / {selectedAgent.config.workingRamBudgetTokens} Tokens · {activeWindowBlocks.length} Blocks)
              </h3>
              <span className="text-xs font-mono text-slate-500 tabular-nums">
                Archival Paged Out: {pagedArchivalBlocks.length} Block(s)
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 text-xs font-semibold text-slate-500">
                    <th className="py-2 pr-3">Block / Zone</th>
                    <th className="py-2 px-3">Fact Key &amp; Active Content</th>
                    <th className="py-2 px-3 text-right">Salience / Tokens</th>
                    <th className="py-2 pl-3 text-right">Real-Time Controls</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 text-xs">
                  {activeWindowBlocks.map((blk) => (
                    <tr key={blk.id} className="hover:bg-slate-50">
                      <td className="py-2.5 pr-3 font-mono align-top">
                        <div className="font-semibold text-slate-900">{blk.id}</div>
                        <div className="text-[11px] text-slate-500">{blk.zone}</div>
                      </td>
                      <td className="py-2.5 px-3 align-top">
                        <div className="font-mono font-semibold text-slate-900">
                          {blk.label}
                          {blk.validUntilTick !== null && (
                            <span className="ml-2 text-red-700 font-normal">
                              (STALE — Superseded at Tick #{blk.validUntilTick})
                            </span>
                          )}
                        </div>
                        <div className="text-slate-600 mt-0.5">{blk.content}</div>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono tabular-nums align-top">
                        <div className="text-slate-900">Sal: {blk.salience.toFixed(2)}</div>
                        <div className="text-slate-500">{blk.tokens} tok</div>
                      </td>
                      <td className="py-2.5 pl-3 text-right align-top whitespace-nowrap">
                        <div className="inline-flex items-center gap-1.5">
                          <button
                            type="button"
                            onClick={() => onTogglePinBlock(selectedAgent.id, blk.id)}
                            aria-label={`${blk.pinned ? 'Unpin' : 'Pin'} block ${blk.id}`}
                            className={`px-2 py-1 text-[11px] font-semibold rounded border transition-colors cursor-pointer inline-flex items-center gap-1 ${
                              blk.pinned
                                ? 'bg-slate-900 text-white border-slate-900'
                                : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
                            }`}
                          >
                            <Pin className="w-3 h-3" />
                            {blk.pinned ? 'Pinned' : 'Pin'}
                          </button>
                          <button
                            type="button"
                            onClick={() => onEvictBlock(selectedAgent.id, blk.id)}
                            aria-label={`Evict block ${blk.id} to archival storage`}
                            className="px-2 py-1 text-[11px] font-semibold text-slate-700 bg-white hover:bg-red-50 hover:text-red-700 border border-slate-300 rounded transition-colors cursor-pointer inline-flex items-center gap-1"
                          >
                            <Trash2 className="w-3 h-3" />
                            Page Out
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </div>

      {/* Bottom Split: Inject Custom Live Stimulus into Selected Agent + Register New Genesis Agent */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        <section className="lg:col-span-7 bg-white border border-slate-200 rounded-xl p-6 space-y-4">
          <div className="border-b border-slate-200 pb-3">
            <h2 className="text-base font-bold text-slate-900">
              Inject Real-Time Stimulus or Contradiction into {selectedAgent.name}
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Send a custom fact, directive, or low-surprise distractor directly into this agent and watch its configured memory gates process it immediately.
            </p>
          </div>

          <form onSubmit={handleInjectStimulus} className="space-y-4" noValidate>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="stim-label" className="block text-xs font-semibold text-slate-700 mb-1">
                  Fact Key / Subject Slot
                </label>
                <input
                  id="stim-label"
                  type="text"
                  value={stimLabel}
                  onChange={(e) => setStimLabel(e.target.value)}
                  placeholder="e.g. Primary_Inference_Topology"
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="stim-surprise" className="block text-xs font-semibold text-slate-700 mb-1">
                    Surprise (0.05–0.99)
                  </label>
                  <input
                    id="stim-surprise"
                    type="number"
                    min="0.05"
                    max="0.99"
                    step="0.05"
                    value={stimSurprise}
                    onChange={(e) => setStimSurprise(Number(e.target.value))}
                    className="w-full px-3 py-2 text-sm font-mono border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
                  />
                </div>
                <div>
                  <label htmlFor="stim-salience" className="block text-xs font-semibold text-slate-700 mb-1">
                    Salience (0.05–0.99)
                  </label>
                  <input
                    id="stim-salience"
                    type="number"
                    min="0.05"
                    max="0.99"
                    step="0.05"
                    value={stimSalience}
                    onChange={(e) => setStimSalience(Number(e.target.value))}
                    className="w-full px-3 py-2 text-sm font-mono border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
                  />
                </div>
              </div>
            </div>

            <div>
              <label htmlFor="stim-content" className="block text-xs font-semibold text-slate-700 mb-1">
                Stimulus Specification / Updated Fact Content
              </label>
              <input
                id="stim-content"
                type="text"
                value={stimContent}
                onChange={(e) => setStimContent(e.target.value)}
                placeholder="e.g. Migrated KV-cache cluster to Optical CXL 3.1 fabric with 12ns latency"
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
              />
            </div>

            {stimError && (
              <div role="alert" className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                <span>{stimError}</span>
              </div>
            )}

            <button
              type="submit"
              className="px-4 py-2.5 text-sm font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors inline-flex items-center gap-2 cursor-pointer"
            >
              <Zap className="w-4 h-4" />
              Inject Stimulus Into {selectedAgent.name}
            </button>
          </form>
        </section>

        <section className="lg:col-span-5 bg-white border border-slate-200 rounded-xl p-6 space-y-4">
          <div className="border-b border-slate-200 pb-3">
            <h2 className="text-base font-bold text-slate-900">
              Spawn &amp; Attach New Genesis Agent
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Provision a new specialized agent on the Genesis Memory OS with real-time telemetry.
            </p>
          </div>

          <form onSubmit={handleCreateAgent} className="space-y-4" noValidate>
            <div>
              <label htmlFor="new-agent-name" className="block text-xs font-semibold text-slate-700 mb-1">
                Genesis Agent Name
              </label>
              <input
                id="new-agent-name"
                type="text"
                value={newAgentName}
                onChange={(e) => setNewAgentName(e.target.value)}
                placeholder="e.g. Genesis Telemetry Synthesizer"
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
              />
            </div>

            <div>
              <label htmlFor="new-agent-role" className="block text-xs font-semibold text-slate-700 mb-1">
                Agent Operational Mandate
              </label>
              <input
                id="new-agent-role"
                type="text"
                value={newAgentRole}
                onChange={(e) => setNewAgentRole(e.target.value)}
                placeholder="e.g. Real-time anomaly detection & episodic compaction"
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
              />
            </div>

            {newAgentError && (
              <div role="alert" className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                <span>{newAgentError}</span>
              </div>
            )}

            <button
              type="submit"
              className="w-full py-2.5 px-4 text-sm font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors inline-flex items-center justify-center gap-2 cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              Attach Agent to Genesis Memory OS
            </button>
          </form>
        </section>
      </div>
    </div>
  );
};
