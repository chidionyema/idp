import React, { useState } from 'react';
import { MemoryNode } from '../engine/memoryEngine';
import { Sparkles, RefreshCw, PlusCircle, CheckCircle2, AlertCircle } from 'lucide-react';

interface ContextRotActiveFocusViewProps {
  nodes: MemoryNode[];
  onIngestFact: (input: {
    subject: string;
    predicate: string;
    object: string;
    category: MemoryNode['category'];
  }) => { supersededIds: string[]; newNodeId: string };
  onPurgeAndReanchor: () => {
    evictedNoiseCount: number;
    reanchoredCount: number;
    tokensReclaimed: number;
  };
  onSimulateRotWave: () => void;
}

export const ContextRotActiveFocusView: React.FC<ContextRotActiveFocusViewProps> = ({
  nodes,
  onIngestFact,
  onPurgeAndReanchor,
  onSimulateRotWave,
}) => {
  const [subject, setSubject] = useState('');
  const [predicate, setPredicate] = useState('');
  const [objectVal, setObjectVal] = useState('');
  const [category, setCategory] = useState<MemoryNode['category']>('architecture_invariant');
  const [tierFilter, setTierFilter] = useState<'all' | 'working_focus' | 'archived_superseded' | 'episodic_buffer'>('all');
  const [validationError, setValidationError] = useState<string | null>(null);
  const [actionBanner, setActionBanner] = useState<string | null>(null);

  const prefixSinkNodes = nodes.filter((n) => n.contextPositionZone === 'prefix_sink');
  const middleTroughNodes = nodes.filter((n) => n.contextPositionZone === 'middle_trough');
  const recencyAnchorNodes = nodes.filter((n) => n.contextPositionZone === 'recency_anchor');

  const filteredNodes = nodes.filter((n) => (tierFilter === 'all' ? true : n.tier === tierFilter));

  const handleSubmitFact = (e: React.FormEvent) => {
    e.preventDefault();
    if (!subject.trim() || !predicate.trim() || !objectVal.trim()) {
      setValidationError('All three fields (Entity Subject, Relational Predicate, and Fact Value) are required.');
      return;
    }
    setValidationError(null);
    const res = onIngestFact({
      subject,
      predicate,
      object: objectVal,
      category,
    });

    if (res.supersededIds.length > 0) {
      setActionBanner(
        `Bi-Temporal Resolution: Ingested ${res.newNodeId} and atomically invalidated superseded edge(s) [${res.supersededIds.join(', ')}] with t_invalid.`
      );
    } else {
      setActionBanner(
        `Ingested node ${res.newNodeId} through Titans Surprise Gate and updated Non-Fungible Verification Ledger.`
      );
    }
    setSubject('');
    setPredicate('');
    setObjectVal('');
  };

  const handleApplyPreset = (preset: {
    subject: string;
    predicate: string;
    object: string;
    category: MemoryNode['category'];
  }) => {
    setValidationError(null);
    setSubject(preset.subject);
    setPredicate(preset.predicate);
    setObjectVal(preset.object);
    setCategory(preset.category);
  };

  const handleExecutePurge = () => {
    const res = onPurgeAndReanchor();
    setActionBanner(
      `Context Rot Purge Complete: Evicted ${res.evictedNoiseCount} distractor noise block(s), re-anchored ${res.reanchoredCount} high-salience invariant(s) out of the middle trough, and reclaimed ${res.tokensReclaimed} tokens.`
    );
  };

  const handleTriggerRotWave = () => {
    onSimulateRotWave();
    setActionBanner(
      'Simulated Adversarial Context Rot Wave: Injected distractor noise and stranded a high-salience invariant inside the 35%–65% Middle Attention Trough. Click "Purge Context Rot & Re-Anchor Focus" to resolve.'
    );
  };

  return (
    <div className="space-y-8">
      {/* Header & Direct Rot Purge Control */}
      <section className="bg-white border border-slate-200 rounded-xl p-6">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="max-w-3xl space-y-2">
            <div className="text-xs text-slate-500">
              Active Memory &amp; Active Focus Inspector · Lost-in-the-Middle U-Curve Mitigation
            </div>
            <h1 className="text-2xl font-bold text-slate-900">
              Context Rot Eradication &amp; Bi-Temporal Focus Engine
            </h1>
            <p className="text-sm text-slate-600 leading-relaxed">
              Context rot occurs through three compounding failure modes: (1) <strong>Lost-in-the-Middle attention decay</strong> inside the 35%–65% token depth trough, (2) <strong>stale contradictory facts</strong> co-existing in append-only logs, and (3) <strong>low-surprise distractor telemetry</strong> diluting softmax attention mass. Inspect and resolve all three below.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <button
              type="button"
              onClick={handleTriggerRotWave}
              className="px-3.5 py-2.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer"
            >
              Simulate Adversarial Rot Wave
            </button>
            <button
              type="button"
              onClick={handleExecutePurge}
              className="px-4 py-2.5 text-sm font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors inline-flex items-center gap-2 whitespace-nowrap shrink-0 cursor-pointer"
            >
              <RefreshCw className="w-4 h-4" />
              Purge Context Rot &amp; Re-Anchor Focus
            </button>
          </div>
        </div>

        {actionBanner && (
          <div
            role="status"
            className="mt-4 p-3.5 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-900 flex items-center gap-2"
          >
            <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
            <span>{actionBanner}</span>
          </div>
        )}

        {/* 3-Zone Attention Window Topology */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6 pt-6 border-t border-slate-200">
          {/* Zone 1: Prefix Sink */}
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-semibold text-slate-900 whitespace-nowrap">
                Zone 1 · Prefix Sink (0%–15%)
              </span>
              <span className="text-xs font-mono tabular-nums text-emerald-700 font-semibold whitespace-nowrap shrink-0">
                99.2% Attention
              </span>
            </div>
            <p className="text-xs text-slate-500">
              StreamingLLM Attention Sink + Pinned System Invariants. Protected from eviction.
            </p>
            <div className="space-y-2 pt-1">
              {prefixSinkNodes.map((n) => (
                <div key={n.id} className="bg-white border border-slate-200 rounded p-2.5 text-xs">
                  <div className="flex items-center justify-between font-mono text-[11px] text-slate-500">
                    <span>{n.id} · {n.subject}</span>
                    <span className="tabular-nums">Salience {n.salience.toFixed(2)}</span>
                  </div>
                  <div className="text-slate-900 font-medium mt-1">{n.object}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Zone 2: Middle Attention Trough */}
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-semibold text-slate-900 whitespace-nowrap">
                Zone 2 · Middle Trough (35%–65%)
              </span>
              <span
                className={`text-xs font-mono tabular-nums font-semibold whitespace-nowrap shrink-0 ${
                  middleTroughNodes.length === 0 ? 'text-emerald-700' : 'text-amber-700'
                }`}
              >
                {middleTroughNodes.length === 0 ? '0 Stranded (Clean)' : `${middleTroughNodes.length} Vulnerable Node(s)`}
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Classic U-Curve degradation zone. High-salience nodes here must be re-anchored; noise must be evicted.
            </p>
            <div className="space-y-2 pt-1">
              {middleTroughNodes.length === 0 ? (
                <div className="bg-white border border-slate-200 rounded p-3 text-xs text-emerald-800">
                  Zero critical facts or distractors stranded in the middle attention trough.
                </div>
              ) : (
                middleTroughNodes.map((n) => (
                  <div key={n.id} className="bg-white border border-amber-300 rounded p-2.5 text-xs">
                    <div className="flex items-center justify-between font-mono text-[11px] text-amber-800">
                      <span>{n.id} · {n.category}</span>
                      <span className="tabular-nums">Salience {n.salience.toFixed(2)}</span>
                    </div>
                    <div className="text-slate-900 font-medium mt-1">
                      {n.subject}: {n.object}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Zone 3: Recency Anchor */}
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-semibold text-slate-900 whitespace-nowrap">
                Zone 3 · Recency Anchor (85%–100%)
              </span>
              <span className="text-xs font-mono tabular-nums text-emerald-700 font-semibold whitespace-nowrap shrink-0">
                98.7% Attention
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Active working scratchpad &amp; most recent bi-temporal contradiction updates.
            </p>
            <div className="space-y-2 pt-1">
              {recencyAnchorNodes.map((n) => (
                <div key={n.id} className="bg-white border border-slate-200 rounded p-2.5 text-xs">
                  <div className="flex items-center justify-between font-mono text-[11px] text-slate-500">
                    <span>{n.id} · {n.subject}</span>
                    <span className="tabular-nums">Surprise {n.surpriseScore.toFixed(2)}</span>
                  </div>
                  <div className="text-slate-900 font-medium mt-1">{n.object}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Bi-Temporal Fact & Contradiction Injection Form + Complete Node Table */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        <section className="lg:col-span-5 bg-white border border-slate-200 rounded-xl p-6 space-y-5">
          <div className="border-b border-slate-200 pb-3">
            <h2 className="text-base font-bold text-slate-900">
              Inject Episodic Event or Contradiction
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Test bi-temporal contradiction resolution by updating an existing <span className="font-mono">(Subject, Predicate)</span> pair or injecting new architectural directives.
            </p>
          </div>

          {/* Quick-Fill Scenario Presets */}
          <div className="space-y-2">
            <div className="text-xs font-medium text-slate-600">Load Test Scenario Preset:</div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() =>
                  handleApplyPreset({
                    subject: 'RateLimiter_Gateway',
                    predicate: 'configured_burst_ceiling',
                    object: '12,000 req/s with eBPF XDP kernel bypass',
                    category: 'runtime_metric',
                  })
                }
                className="px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors cursor-pointer"
              >
                Supersede RateLimiter (Contradiction)
              </button>
              <button
                type="button"
                onClick={() =>
                  handleApplyPreset({
                    subject: 'Auth_Token_Policy',
                    predicate: 'enforces_ttl',
                    object: '5 minutes hardware-bound WebAuthn FIDO2 assertion',
                    category: 'security_policy',
                  })
                }
                className="px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors cursor-pointer"
              >
                Supersede Auth Policy
              </button>
              <button
                type="button"
                onClick={() =>
                  handleApplyPreset({
                    subject: 'Telemetry_Noise_994',
                    predicate: 'emitted_routine_heartbeat',
                    object: 'Pod us-east-1c routine GC sweep completed in 4ms',
                    category: 'distractor_noise',
                  })
                }
                className="px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors cursor-pointer"
              >
                Inject Distractor Noise
              </button>
            </div>
          </div>

          <form onSubmit={handleSubmitFact} className="space-y-4" noValidate>
            <div>
              <label htmlFor="mem-subject" className="block text-xs font-semibold text-slate-700 mb-1">
                Entity Subject
              </label>
              <input
                id="mem-subject"
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="e.g. RateLimiter_Gateway or VectorIndex_Engine"
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
              />
            </div>

            <div>
              <label htmlFor="mem-predicate" className="block text-xs font-semibold text-slate-700 mb-1">
                Relational Predicate
              </label>
              <input
                id="mem-predicate"
                type="text"
                value={predicate}
                onChange={(e) => setPredicate(e.target.value)}
                placeholder="e.g. configured_burst_ceiling or uses_storage_backend"
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
              />
            </div>

            <div>
              <label htmlFor="mem-object" className="block text-xs font-semibold text-slate-700 mb-1">
                Fact Specification / Object Value
              </label>
              <input
                id="mem-object"
                type="text"
                value={objectVal}
                onChange={(e) => setObjectVal(e.target.value)}
                placeholder="e.g. 12,000 req/s with eBPF token bucket"
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
              />
            </div>

            <div>
              <label htmlFor="mem-category" className="block text-xs font-semibold text-slate-700 mb-1">
                Semantic Category
              </label>
              <select
                id="mem-category"
                value={category}
                onChange={(e) => setCategory(e.target.value as MemoryNode['category'])}
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-slate-900"
              >
                <option value="architecture_invariant">Architecture Invariant (High Salience)</option>
                <option value="security_policy">Security Policy (High Salience)</option>
                <option value="user_directive">Executive / Founder Directive (Pinned)</option>
                <option value="runtime_metric">Runtime Metric / Capacity Spec</option>
                <option value="distractor_noise">Distractor Telemetry Noise (Low Surprise)</option>
              </select>
            </div>

            {validationError && (
              <div role="alert" className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                <span>{validationError}</span>
              </div>
            )}

            <button
              type="submit"
              className="w-full py-2.5 px-4 text-sm font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors inline-flex items-center justify-center gap-2 cursor-pointer"
            >
              <PlusCircle className="w-4 h-4" />
              Ingest Memory Event &amp; Resolve Contradictions
            </button>
          </form>
        </section>

        {/* Bi-Temporal Knowledge Graph Table */}
        <section className="lg:col-span-7 bg-white border border-slate-200 rounded-xl p-6">
          <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-200">
            <div>
              <h2 className="text-base font-bold text-slate-900">
                Bi-Temporal Memory Graph &amp; Salience Ledger ({filteredNodes.length} Nodes)
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Every edge tracks <span className="font-mono">validFromStep</span> and <span className="font-mono">validUntilStep</span>. Superseded facts are never deleted from audit history but strictly excluded from Active Focus.
              </p>
            </div>

            {/* Interactive Filter Tabs */}
            <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg">
              {(
                [
                  { id: 'all', label: 'All Nodes' },
                  { id: 'working_focus', label: 'Active Focus' },
                  { id: 'archived_superseded', label: 'Superseded' },
                  { id: 'episodic_buffer', label: 'Episodic / Noise' },
                ] as const
              ).map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setTierFilter(tab.id)}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer whitespace-nowrap ${
                    tierFilter === tab.id
                      ? 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          <div className="overflow-x-auto mt-4">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 text-xs font-semibold text-slate-500">
                  <th className="py-2.5 pr-3">Node / Lineage</th>
                  <th className="py-2.5 px-3">Subject → Predicate → Object</th>
                  <th className="py-2.5 px-3 text-right">Salience / Surprise</th>
                  <th className="py-2.5 px-3">Bi-Temporal Window</th>
                  <th className="py-2.5 pl-3 text-right">Attention Zone</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 text-xs">
                {filteredNodes.map((node) => {
                  const isSuperseded = node.validUntilStep !== null;
                  return (
                    <tr
                      key={node.id}
                      className={isSuperseded ? 'bg-slate-50/70 text-slate-400' : 'hover:bg-slate-50'}
                    >
                      <td className="py-3 pr-3 align-top">
                        <div className="font-mono font-semibold text-slate-900">{node.id}</div>
                        <div className="text-[11px] text-slate-500 mt-0.5">{node.category}</div>
                      </td>
                      <td className="py-3 px-3 align-top">
                        <div className="text-[11px] font-mono text-slate-500">{node.situationalPrefix}</div>
                        <div className={`font-medium mt-0.5 ${isSuperseded ? 'line-through text-slate-400' : 'text-slate-900'}`}>
                          <span className="font-mono">{node.subject}</span> · {node.predicate} →{' '}
                          <span className="font-semibold">{node.object}</span>
                        </div>
                      </td>
                      <td className="py-3 px-3 text-right font-mono tabular-nums align-top">
                        <div className="text-slate-800">Sal: {node.salience.toFixed(2)}</div>
                        <div className="text-slate-500">Surp: {node.surpriseScore.toFixed(2)}</div>
                      </td>
                      <td className="py-3 px-3 font-mono tabular-nums align-top">
                        <div>t_valid: Step {node.validFromStep}</div>
                        <div className={isSuperseded ? 'text-amber-700 font-semibold' : 'text-emerald-700'}>
                          {isSuperseded
                            ? `t_invalid: Step ${node.validUntilStep} (→ ${node.supersededById})`
                            : 't_invalid: null (ACTIVE)'}
                        </div>
                      </td>
                      <td className="py-3 pl-3 text-right font-mono align-top">
                        <div>{node.contextPositionZone}</div>
                        <div className="text-slate-400 tabular-nums">{node.tokens} tok</div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
};
