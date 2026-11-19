import React, { useState, useMemo } from 'react';
import {
  CheckCircle2,
  XCircle,
  Play,
  ShieldCheck,
  Code2,
  Server,
  Layers,
} from 'lucide-react';
import {
  evaluateComposableIntent,
  type ComposableIntent,
  type EstateEntity,
  type OttoInstanceState,
} from '../engine/oracleEngine';
import { RUST_CARGO_TOML_SOURCE } from '../data/estateSeedData';

interface ComposableIntentViewProps {
  intents: ComposableIntent[];
  entities: EstateEntity[];
  ottoInstances: OttoInstanceState[];
  onReconcileSplitBrain: () => void;
}

export const ComposableIntentView: React.FC<ComposableIntentViewProps> = ({
  intents,
  entities,
  ottoInstances,
  onReconcileSplitBrain,
}) => {
  const [selectedIntentId, setSelectedIntentId] = useState<string>(
    intents[0]?.id || 'intent.otto.day0_readiness'
  );
  const [customQueryOverride, setCustomQueryOverride] = useState<string>('');
  const [evalCount, setEvalCount] = useState<number>(1);

  const activeIntent = useMemo(() => {
    const base = intents.find((i) => i.id === selectedIntentId) || intents[0];
    if (!customQueryOverride.trim()) return base;
    return {
      ...base,
      targetQuery: customQueryOverride.trim(),
    };
  }, [intents, selectedIntentId, customQueryOverride]);

  const evalReport = useMemo(
    () => evaluateComposableIntent(activeIntent, entities, ottoInstances),
    [activeIntent, entities, ottoInstances, evalCount]
  );

  return (
    <div className="space-y-10">
      {/* Section 01: Composable Intent Engine */}
      <section aria-labelledby="intent-engine-heading" className="space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 border-b border-slate-800 pb-6">
          <div className="space-y-2 max-w-3xl">
            <p className="text-xs font-mono text-sky-400">
              01. Reusable & Composable Primitives · Oracle Rationing Protocol
            </p>
            <h1
              id="intent-engine-heading"
              className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-100"
              style={{ textWrap: 'balance' }}
            >
              Declarative CIF Intent Engine vs. P<sub>oracle</sub> Shell Hacks
            </h1>
            <p className="text-sm text-slate-400 leading-relaxed">
              Under Continuous Infrastructure Falsification (CIF), an Intent is a reusable YAML
              contract evaluated deterministically in Pass 1 against the indexed{' '}
              <code className="text-slate-200">estate-graph</code>—never a hardcoded bash loop
              grepping the filesystem.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              type="button"
              onClick={() => setEvalCount((c) => c + 1)}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-slate-950 bg-sky-400 hover:bg-sky-300 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Play className="w-3.5 h-3.5" />
              <span>Evaluate Intent (Pass 1)</span>
            </button>
          </div>
        </div>

        {/* Intent Selector Tabs */}
        <div className="flex flex-wrap items-center gap-2" role="tablist" aria-label="Composable Intents">
          {intents.map((intent) => {
            const isSelected = intent.id === selectedIntentId;
            return (
              <button
                key={intent.id}
                type="button"
                role="tab"
                aria-selected={isSelected}
                onClick={() => {
                  setSelectedIntentId(intent.id);
                  setCustomQueryOverride('');
                }}
                className={`px-3.5 py-2 text-xs font-mono font-medium rounded-lg border transition-colors whitespace-nowrap shrink-0 ${
                  isSelected
                    ? 'bg-sky-500/20 text-sky-300 border-sky-500/40'
                    : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
                }`}
              >
                {intent.id} (v{intent.version})
              </button>
            );
          })}
        </div>

        {/* 2-Column Intent Contract + Live Evaluation Outcome */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left: Declarative YAML Contract */}
          <div className="lg:col-span-6 border border-slate-800 rounded-lg bg-slate-900 p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h2 className="text-sm font-bold text-slate-100">{activeIntent.name}</h2>
                <p className="text-xs text-slate-400 mt-0.5">{activeIntent.description}</p>
              </div>
              <Code2 className="w-4 h-4 text-sky-400 shrink-0" />
            </div>

            <div>
              <label
                htmlFor="intent-query-override"
                className="block text-xs font-medium text-slate-300 mb-1.5"
              >
                Composable Target Query Parameter (Pass-1 Indexed Match)
              </label>
              <input
                id="intent-query-override"
                type="text"
                value={customQueryOverride || activeIntent.targetQuery}
                onChange={(e) => setCustomQueryOverride(e.target.value)}
                className="w-full px-3 py-2 text-xs font-mono bg-slate-950 border border-slate-800 rounded-md text-slate-100 focus:outline-none focus:border-sky-500"
              />
            </div>

            <div className="space-y-1.5">
              <div className="text-xs font-mono text-slate-400">
                Declarative Contract (intents/{activeIntent.id}.yaml)
              </div>
              <pre className="p-3.5 bg-slate-950 border border-slate-800 rounded-md text-xs font-mono text-slate-200 overflow-x-auto leading-relaxed">
                {activeIntent.yamlSource}
              </pre>
            </div>
          </div>

          {/* Right: Deterministic Pass-1 Evaluation Report */}
          <div className="lg:col-span-6 border border-slate-800 rounded-lg bg-slate-900 p-5 space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                {evalReport.passed ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                ) : (
                  <XCircle className="w-5 h-5 text-rose-400 shrink-0" />
                )}
                <div>
                  <h2 className="text-sm font-bold text-slate-100">
                    {evalReport.passed
                      ? 'INTENT VERIFIED · ALL EXPECTED OUTCOMES PASSED'
                      : 'INTENT FALSIFIED · POLICY GATE VIOLATION DETECTED'}
                  </h2>
                  <p className="text-xs font-mono text-slate-400 tabular-nums">
                    Evaluation Run #{evalCount} · Pass-1 Latency: {evalReport.pass1LatencyMs} ms
                  </p>
                </div>
              </div>
            </div>

            {/* Expected Outcomes Checklist */}
            <div className="space-y-2.5">
              <h3 className="text-xs font-semibold text-slate-300">
                Expected Outcome Predicates ({evalReport.assertionResults.length})
              </h3>
              <div className="divide-y divide-slate-800 border border-slate-800 rounded-md bg-slate-950">
                {evalReport.assertionResults.map((assertion) => (
                  <div key={assertion.id} className="p-3.5 space-y-1">
                    <div className="flex items-center justify-between gap-2 text-xs font-mono">
                      <span className="font-semibold text-slate-200">{assertion.id}</span>
                      {assertion.passed ? (
                        <span className="text-emerald-400 font-medium">PASS</span>
                      ) : (
                        <span className="text-rose-400 font-medium">FAIL (FALSIFIED)</span>
                      )}
                    </div>
                    <p className="text-xs text-slate-300">{assertion.assertion}</p>
                    <p className="text-xs font-mono text-slate-400 tabular-nums">
                      Observed: {assertion.actualValue}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {!evalReport.passed && (
              <div className="p-3.5 bg-slate-950 border border-rose-500/40 rounded-md flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="text-xs text-slate-300">
                  <strong className="text-rose-300 block mb-0.5">
                    Remediation Available in Estate Kernel
                  </strong>
                  Consolidate the competing Otto v1 daemon to satisfy zero_split_brain and
                  all_cif_verified predicates.
                </div>
                <button
                  type="button"
                  onClick={onReconcileSplitBrain}
                  className="px-3.5 py-2 text-xs font-semibold bg-sky-400 hover:bg-sky-300 text-slate-950 rounded-md transition-colors whitespace-nowrap shrink-0"
                >
                  Consolidate Split-Brain Now
                </button>
              </div>
            )}

            {/* Cryptographic Receipt Signature */}
            <div className="p-3 bg-slate-950 border border-slate-800 rounded-md text-xs font-mono space-y-1">
              <div className="flex items-center justify-between text-slate-400">
                <span className="inline-flex items-center gap-1.5 text-emerald-400">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  CIF Policy Evaluation Receipt Signature
                </span>
                <span>Matched Nodes: {evalReport.matchedEntities.length}</span>
              </div>
              <div className="text-slate-300 truncate">{evalReport.receiptSignature}</div>
            </div>
          </div>
        </div>
      </section>

      {/* Section 02: Rust Spine Footprint (Cargo.toml) */}
      <section aria-labelledby="rust-spine-heading" className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2">
          <div>
            <p className="text-xs font-mono text-sky-400">
              02. Oracle Free Tier k3s Admission Spec (#7318 Pivot)
            </p>
            <h2 id="rust-spine-heading" className="text-xl font-bold text-slate-100">
              Single-Binary Rust Overwatch Footprint (teloxide + axum + sqlx)
            </h2>
          </div>
          <span className="text-xs font-mono text-slate-400 tabular-nums">
            Binary Size: 14.8 MB · Peak RSS: 18.2 MB / 20.0 MB Cap
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
          <div className="lg:col-span-7 border border-slate-800 rounded-lg bg-slate-900 p-4">
            <pre className="text-xs font-mono text-slate-200 overflow-x-auto leading-relaxed">
              {RUST_CARGO_TOML_SOURCE}
            </pre>
          </div>

          <div className="lg:col-span-5 border border-slate-800 rounded-lg bg-slate-900 p-5 flex flex-col justify-between space-y-4">
            <div className="space-y-4">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Server className="w-4 h-4 text-sky-400" />
                <span>Why This Earns Admission to the Oracle k3s Spine</span>
              </h3>

              <div className="space-y-3 text-xs text-slate-300 leading-relaxed">
                <div className="p-3 bg-slate-950 border border-slate-800 rounded-md">
                  <div className="font-mono font-semibold text-sky-400 mb-1">
                    1. teloxide (Supergroup Topic & Inline Keyboard Engine)
                  </div>
                  Manages #00-OVERWATCH 3s in-place telemetry edits, dynamic #pi-lane-* topic
                  spawning, and live status emoji transitions without webhook spam.
                </div>

                <div className="p-3 bg-slate-950 border border-slate-800 rounded-md">
                  <div className="font-mono font-semibold text-sky-400 mb-1">
                    2. axum + tokio-tungstenite (60fps TMA WebSocket Server)
                  </div>
                  Serves the zero-bloat Telegram Mini App bundle and streams real-time SQLite WAL
                  telemetry frames over WebSockets with native haptic triggers.
                </div>

                <div className="p-3 bg-slate-950 border border-slate-800 rounded-md">
                  <div className="font-mono font-semibold text-sky-400 mb-1">
                    3. sqlx + notify (Zero-Polling CIF Ledger Watcher)
                  </div>
                  Watches ~/.estate/estate.db directly via kernel kqueue/inotify events, verifying
                  HMAC-SHA256 signatures before any claim reaches the founder.
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-xs font-mono text-slate-400 tabular-nums">
              <span className="inline-flex items-center gap-1.5 text-emerald-400">
                <Layers className="w-3.5 h-3.5" />
                Admission Gate: VERIFIED_RUST_STATIC
              </span>
              <span>argon / OKE #7318: Quarantined</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
