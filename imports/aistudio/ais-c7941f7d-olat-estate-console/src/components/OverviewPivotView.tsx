import React, { useState } from 'react';
import {
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Cpu,
  Database,
  FileCheck2,
  Inbox,
  Send,
  ShieldCheck,
} from 'lucide-react';
import {
  FleetSummaryMetrics,
  InstructionRecord,
  SpecialistAgent,
  getNextCanonicalEvent,
  ProtocolEvent,
} from '../lib/protocolEngine';

interface OverviewPivotViewProps {
  metrics: FleetSummaryMetrics;
  instructions: InstructionRecord[];
  agents: SpecialistAgent[];
  onNavigate: (tab: 'overview' | 'fleet' | 'protocols' | 'yield' | 'evals') => void;
  onStepAgent: (agentId: string, event: ProtocolEvent) => void;
  onOpenNewInstruction: () => void;
}

const QUAD_LAYERS = [
  {
    index: '01',
    name: 'Strict Estate Protocol Layer',
    code: 'PRT-ESTATE-CORE',
    summary:
      'Replaces ad-hoc prompt chains and fragile infrastructure with deterministic input/output contracts, mandatory claim schemas, and cryptographic proof invariants.',
    mechanism: 'Schema-locked instruction payloads & proof token validators (PRF-*, LEDGER-*, DIFF-*)',
    outcome: 'Eliminates hallucinated state transitions before any estate ledger write occurs.',
  },
  {
    index: '02',
    name: 'Event-Driven State Machine Layer',
    code: 'FSM-HEADLESS-7S',
    summary:
      'Every specialist transitions strictly through 7 verified states triggered by signed events—never relying on human laptop sessions or open browser tabs.',
    mechanism: 'IDLE → INBOX_QUEUED → CLAIMED → EXECUTING_PROTOCOL → PROOF_ATTACHED → OUTBOX_DISPATCHED → YIELD_AUDITED',
    outcome: '100% deterministic replay and crash recovery across long-running estate workflows.',
  },
  {
    index: '03',
    name: 'Persistent Estate Memory Layer',
    code: 'MEM-QUAD-STORE',
    summary:
      'Shared, versioned semantic and episodic memory across lease covenants, parcel title chains, and CAM caps with zero local laptop state.',
    mechanism: 'Scoped key-value & proof-hash checkpoints (Estate-Global, Protocol-State, Claim-Ledger)',
    outcome: 'Sub-200ms headless worker hydration across multi-week property transactions.',
  },
  {
    index: '04',
    name: 'Agent Kit & Private Inbox/Outbox Layer',
    code: 'AGENTKIT-V3.4',
    summary:
      'Autonomous specialist squads consume work exclusively from Private Inboxes and emit signed proof bundles to Private Outboxes.',
    mechanism: 'Sandboxed Agent Kit tools + isolated asynchronous Inbox/Outbox queues',
    outcome: 'Full end-to-end workflow automation from instruction issuance to Founder Yield review.',
  },
];

export const OverviewPivotView: React.FC<OverviewPivotViewProps> = ({
  metrics,
  instructions,
  agents,
  onNavigate,
  onStepAgent,
  onOpenNewInstruction,
}) => {
  const [selectedLayerIndex, setSelectedLayerIndex] = useState<number>(0);
  const activeLayer = QUAD_LAYERS[selectedLayerIndex];

  return (
    <div className="space-y-10">
      {/* Hero / Strategic Pivot Thesis */}
      <section className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-xl p-6 lg:p-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
          <div className="lg:col-span-7 flex flex-col justify-between space-y-6">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2 text-xs font-medium text-slate-500 dark:text-slate-400">
                <span>Strategic Pivot Architecture</span>
                <span aria-hidden="true">·</span>
                <span>Quad-Layer & Agent Kit</span>
                <span aria-hidden="true">·</span>
                <span>Zero Laptop Dependency</span>
              </div>
              <h1
                className="text-2xl sm:text-3xl lg:text-4xl font-bold tracking-tight text-slate-900 dark:text-slate-50"
                style={{ textWrap: 'balance' }}
              >
                From Heavy Infrastructure to Protocol-Driven Autonomous Estate Fleets
              </h1>
              <p className="text-sm sm:text-base text-slate-600 dark:text-slate-300 leading-relaxed max-w-2xl">
                Following infrastructure loss and delivery bottlenecks, Olat has pivoted all engineering focus away from heavy infrastructure and laptop-tethered workflows. Our specialist fleet operates headlessly on strict Estate protocols—governed by event-driven state machines, private inbox/outbox queues, and cryptographic claim-to-proof tracking measured by real Yield.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2.5 pt-2">
              <button
                type="button"
                onClick={onOpenNewInstruction}
                className="px-3.5 py-2 text-xs font-semibold text-white bg-slate-900 dark:bg-slate-100 dark:text-slate-900 rounded-lg hover:bg-slate-800 dark:hover:bg-white transition-colors whitespace-nowrap shrink-0 cursor-pointer"
              >
                Issue Estate Instruction
              </button>
              <button
                type="button"
                onClick={() => onNavigate('yield')}
                className="px-3.5 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-800 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors whitespace-nowrap shrink-0 inline-flex items-center gap-1.5 cursor-pointer"
              >
                <span>Open Founder Yield Review ({metrics.pendingFounderReviewCount} Pending)</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => onNavigate('evals')}
                className="px-3.5 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0 cursor-pointer"
              >
                View Pivot Presentation & Evals
              </button>
            </div>
          </div>

          {/* Right Column: Before vs After Pivot Shift Matrix */}
          <div className="lg:col-span-5 border border-slate-200 dark:border-slate-800 rounded-lg p-5 bg-slate-50/70 dark:bg-slate-950/60 flex flex-col justify-between space-y-4">
            <div className="space-y-1">
              <div className="text-xs font-medium text-slate-500 dark:text-slate-400">
                Founder Architectural Realignment
              </div>
              <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                Why Protocol Engineering Replaces Heavy Infra
              </h2>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1">
                <div className="font-semibold text-rose-700 dark:text-rose-400">
                  Retired: Heavy Infra & Laptop-Tethered Agents
                </div>
                <p className="text-slate-600 dark:text-slate-400">
                  High maintenance overhead, fragile state lost when developer laptops sleep, unverified agent claims, and zero measurable delivery yield.
                </p>
              </div>

              <div className="p-3 rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1">
                <div className="font-semibold text-emerald-700 dark:text-emerald-400">
                  Active Focus: Headless Specialist Fleet & Strict Protocols
                </div>
                <p className="text-slate-600 dark:text-slate-400">
                  Quad-Layer + Agent Kit workers with Private Inbox/Outbox queues, deterministic event state machines, persistent memory, and Claim → Proof → Yield auditing.
                </p>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs text-slate-600 dark:text-slate-400">
              <span>Laptop Dependency Across Fleet</span>
              <span className="font-mono font-semibold text-slate-900 dark:text-slate-100 tabular-nums">
                0.0% (100% Headless)
              </span>
            </div>
          </div>
        </div>

        {/* Full-Width 4-Column KPI Strip Below Hero Split */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-8 pt-6 border-t border-slate-200 dark:border-slate-800">
          <div className="space-y-1">
            <div className="text-xs text-slate-500 dark:text-slate-400">
              Fleet Outcome vs. Expected Yield
            </div>
            <div className="text-2xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-50">
              {metrics.averageYieldPercent.toFixed(1)}%
            </div>
            <div className="text-xs text-emerald-700 dark:text-emerald-400">
              Exceeds 100.0% baseline across {metrics.totalInstructions} estate instructions
            </div>
          </div>

          <div className="space-y-1">
            <div className="text-xs text-slate-500 dark:text-slate-400">
              Headless Specialist Autonomy
            </div>
            <div className="text-2xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-50">
              {metrics.headlessAutonomyRate}%
            </div>
            <div className="text-xs text-slate-600 dark:text-slate-400">
              {agents.length} specialist squads · {metrics.totalInboxPending} inbox events queued
            </div>
          </div>

          <div className="space-y-1">
            <div className="text-xs text-slate-500 dark:text-slate-400">
              Verified Proofs & Founder Sign-Off
            </div>
            <div className="text-2xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-50">
              {metrics.founderApprovedCount} / {metrics.totalInstructions}
            </div>
            <div className="text-xs text-amber-700 dark:text-amber-400">
              {metrics.pendingFounderReviewCount} awaiting Founder Yield review
            </div>
          </div>

          <div className="space-y-1">
            <div className="text-xs text-slate-500 dark:text-slate-400">
              Fleet Protocol Eval Pass Rate
            </div>
            <div className="text-2xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-50">
              {metrics.evalPassRate.toFixed(1)}%
            </div>
            <div className="text-xs text-slate-600 dark:text-slate-400">
              {metrics.totalOutboxDispatched} verified proof bundles in Outbox
            </div>
          </div>
        </div>
      </section>

      {/* Section 01: Interactive Quad-Layer & Agent Kit Architecture */}
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              01. Quad-Layer & Agent Kit Architecture
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">
              Select any layer below to inspect how autonomous specialist teams execute complex estate workflows without human or laptop intervention.
            </p>
          </div>
          <button
            type="button"
            onClick={() => onNavigate('protocols')}
            className="text-xs font-semibold text-slate-900 dark:text-slate-200 hover:underline inline-flex items-center gap-1.5 self-start sm:self-auto cursor-pointer"
          >
            <span>Open Protocol & State Machine Simulator</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
          <div className="lg:col-span-5 flex flex-col gap-2.5">
            {QUAD_LAYERS.map((layer, idx) => {
              const isSelected = idx === selectedLayerIndex;
              return (
                <button
                  key={layer.code}
                  type="button"
                  onClick={() => setSelectedLayerIndex(idx)}
                  className={`text-left p-4 rounded-lg border transition-colors cursor-pointer ${
                    isSelected
                      ? 'bg-slate-900 text-white border-slate-900 dark:bg-slate-100 dark:text-slate-900 dark:border-slate-100'
                      : 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/60'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-mono opacity-75">
                      Layer {layer.index} · {layer.code}
                    </span>
                    <span className="text-xs font-medium">
                      {isSelected ? 'Inspected' : 'Inspect'}
                    </span>
                  </div>
                  <div className="font-semibold text-sm mt-1">{layer.name}</div>
                </button>
              );
            })}
          </div>

          <div className="lg:col-span-7 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-lg p-6 flex flex-col justify-between space-y-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
                <div>
                  <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
                    LAYER {activeLayer.index} SPECIFICATION · {activeLayer.code}
                  </span>
                  <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100 mt-0.5">
                    {activeLayer.name}
                  </h3>
                </div>
                <Layers className="w-5 h-5 text-slate-400" />
              </div>

              <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                {activeLayer.summary}
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-1.5">
                  <div className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                    Protocol Mechanism
                  </div>
                  <div className="text-xs font-mono text-slate-800 dark:text-slate-200 leading-relaxed">
                    {activeLayer.mechanism}
                  </div>
                </div>
                <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-1.5">
                  <div className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                    Guaranteed Estate Outcome
                  </div>
                  <div className="text-xs text-slate-800 dark:text-slate-200 leading-relaxed">
                    {activeLayer.outcome}
                  </div>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500 dark:text-slate-400">
              <span>All 4 layers run headlessly inside isolated Quad-Worker containers</span>
              <button
                type="button"
                onClick={() => onNavigate('fleet')}
                className="font-semibold text-slate-900 dark:text-slate-100 hover:underline cursor-pointer"
              >
                Inspect Specialist Inbox & Outbox Queues →
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Section 02: End-to-End Instruction -> Claim -> Proof -> Outcome -> Yield Chain */}
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              02. Live Instruction-to-Yield & Founder Review Ledger
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">
              Every instruction tracks the specialist claim, cryptographic proof artifact, actual vs. expected outcome, and calculated Yield %.
            </p>
          </div>
          <button
            type="button"
            onClick={() => onNavigate('yield')}
            className="text-xs font-semibold text-slate-900 dark:text-slate-200 hover:underline inline-flex items-center gap-1.5 self-start sm:self-auto cursor-pointer"
          >
            <span>Review & Audit All Instructions</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-950/60 text-xs font-semibold text-slate-500 dark:text-slate-400">
                  <th className="py-3 px-4">Instruction & Estate Asset</th>
                  <th className="py-3 px-4">Specialist & Protocol</th>
                  <th className="py-3 px-4">Claim & Proof Token</th>
                  <th className="py-3 px-4 text-right">Expected vs Actual</th>
                  <th className="py-3 px-4 text-right">Yield %</th>
                  <th className="py-3 px-4">Founder Review</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-xs">
                {instructions.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => onNavigate('yield')}
                    className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors cursor-pointer"
                  >
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-900 dark:text-slate-100">
                        {item.title}
                      </div>
                      <div className="text-slate-500 dark:text-slate-400 mt-0.5">
                        {item.id} · {item.estateAsset}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-700 dark:text-slate-300">
                      <div>{item.specialistId}</div>
                      <div className="text-slate-500 dark:text-slate-400">{item.protocolId}</div>
                    </td>
                    <td className="py-3.5 px-4 max-w-xs">
                      <div className="text-slate-700 dark:text-slate-300 truncate">
                        {item.claimStatement}
                      </div>
                      <div className="font-mono text-slate-500 dark:text-slate-400 truncate mt-0.5">
                        {item.proofArtifact}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono tabular-nums text-slate-700 dark:text-slate-300">
                      <div>
                        {item.actualValue} / {item.expectedValue} {item.unit}
                      </div>
                      <div className="text-slate-500 dark:text-slate-400">
                        {item.expectedMetricLabel}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono tabular-nums">
                      <div
                        className={`font-bold ${
                          item.yieldPercent >= 100
                            ? 'text-emerald-700 dark:text-emerald-400'
                            : item.yieldPercent >= 95
                            ? 'text-slate-900 dark:text-slate-100'
                            : 'text-amber-700 dark:text-amber-400'
                        }`}
                      >
                        {item.yieldPercent.toFixed(1)}%
                      </div>
                      <div className="text-slate-500 dark:text-slate-400">{item.yieldGrade}</div>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="inline-flex items-center gap-1.5 font-medium">
                        {item.founderReview.status === 'Approved' ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                        ) : (
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 shrink-0" />
                        )}
                        <span
                          className={
                            item.founderReview.status === 'Approved'
                              ? 'text-emerald-700 dark:text-emerald-400'
                              : item.founderReview.status === 'Revision Requested'
                              ? 'text-rose-700 dark:text-rose-400'
                              : 'text-amber-700 dark:text-amber-400'
                          }
                        >
                          {item.founderReview.status}
                        </span>
                      </div>
                      <div className="text-slate-500 dark:text-slate-400 mt-0.5">
                        {item.stage}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Section 03: Active Headless Specialist Squads & Quick State Step */}
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              03. Autonomous Specialist Fleet Status
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">
              Headless workers operating with private Inbox/Outbox queues and deterministic state machines.
            </p>
          </div>
          <button
            type="button"
            onClick={() => onNavigate('fleet')}
            className="text-xs font-semibold text-slate-900 dark:text-slate-200 hover:underline inline-flex items-center gap-1.5 self-start sm:self-auto cursor-pointer"
          >
            <span>Manage Private Inbox & Outbox Queues</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {agents.map((agent) => {
            const nextEvent = getNextCanonicalEvent(agent.machineState);
            const unreadInbox = agent.inbox.filter((m) => !m.processed).length;
            return (
              <div
                key={agent.id}
                className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-lg p-5 flex flex-col justify-between space-y-4"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 font-mono">
                    <span>
                      {agent.id} · {agent.protocolId}
                    </span>
                    <span>Eval: {agent.evalScore.toFixed(1)}%</span>
                  </div>
                  <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                    {agent.name}
                  </h3>
                  <p className="text-xs text-slate-600 dark:text-slate-400">
                    {agent.estateDomain}
                  </p>
                </div>

                <div className="pt-3 border-t border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
                  <div className="space-y-0.5">
                    <div className="text-slate-500 dark:text-slate-400">
                      Current Machine State
                    </div>
                    <div className="font-mono font-semibold text-slate-900 dark:text-slate-100">
                      {agent.machineState} · Inbox ({unreadInbox}) · Outbox ({agent.outbox.length})
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => onStepAgent(agent.id, nextEvent)}
                    className="px-3 py-1.5 text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded-md hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors whitespace-nowrap shrink-0 cursor-pointer"
                  >
                    Trigger {nextEvent}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
};
