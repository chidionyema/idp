import React, { useState } from 'react';
import {
  ShieldCheck,
  Database,
  Play,
  RotateCcw,
  Plus,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import {
  AgentMachineState,
  ProtocolEvent,
  MemoryEntry,
  transitionAgentState,
} from '../lib/protocolEngine';

interface ProtocolStateMemoryViewProps {
  memoryEntries: MemoryEntry[];
  onAddMemoryEntry: (
    key: string,
    scope: 'Estate-Global' | 'Protocol-State' | 'Claim-Ledger',
    valueSummary: string
  ) => void;
}

const CANONICAL_STATES: AgentMachineState[] = [
  'IDLE',
  'INBOX_QUEUED',
  'CLAIMED',
  'EXECUTING_PROTOCOL',
  'PROOF_ATTACHED',
  'OUTBOX_DISPATCHED',
  'YIELD_AUDITED',
  'HALTED_VIOLATION',
];

const ALL_EVENTS: ProtocolEvent[] = [
  'ENQUEUE_INBOX',
  'ACQUIRE_CLAIM',
  'RUN_AGENT_KIT',
  'ATTACH_PROOF',
  'DISPATCH_OUTBOX',
  'RECORD_YIELD',
  'FLAG_VIOLATION',
  'RESET_HEADLESS',
];

const ESTATE_PROTOCOLS = [
  {
    id: 'PRT-LEASE-401',
    name: 'Commercial Lease CPI & Covenant Protocol',
    invariants: 'Requires base index date, CPI ceiling formula, and signed schedule diff hash before Outbox dispatch.',
    proofFormat: 'PRF-LEASE-<ID> · sha256:<8-hex>',
    targetYield: '100% clause reconciliation with zero manual spreadsheet edits',
  },
  {
    id: 'PRT-TITLE-209',
    name: 'Parcel Chain-of-Title & Easement Protocol',
    invariants: 'Mandates 40-year grantor-grantee index continuity and plat survey polygon hash verification.',
    proofFormat: 'LEDGER-TITLE-<ID> · sha256:<8-hex>',
    targetYield: '100% encumbrance clearance prior to debt or refinancing lock',
  },
  {
    id: 'PRT-CAM-315',
    name: 'CAM & CapEx Pro-Rata Recovery Protocol',
    invariants: 'Enforces lease expense-stop caps and capital amortization schedules on every vendor invoice.',
    proofFormat: 'DIFF-CAM-<ID> · sha256:<8-hex>',
    targetYield: 'Full pass-through leakage recovery audited against tenant ledgers',
  },
  {
    id: 'PRT-CURE-112',
    name: 'Delinquency Cure & Escrow Draw Protocol',
    invariants: 'Blocks escrow draw unless statutory cure window has elapsed and proof-of-service hash is attached.',
    proofFormat: 'PRF-CURE-<ID> · sha256:<8-hex>',
    targetYield: 'Automated statutory compliance and zero premature notice defects',
  },
];

export const ProtocolStateMemoryView: React.FC<ProtocolStateMemoryViewProps> = ({
  memoryEntries,
  onAddMemoryEntry,
}) => {
  const [simState, setSimState] = useState<AgentMachineState>('EXECUTING_PROTOCOL');
  const [simLog, setSimLog] = useState<
    Array<{
      id: string;
      from: AgentMachineState;
      event: ProtocolEvent;
      to: AgentMachineState;
      valid: boolean;
      reason: string;
    }>
  >([
    {
      id: 'SIM-03',
      from: 'CLAIMED',
      event: 'RUN_AGENT_KIT',
      to: 'EXECUTING_PROTOCOL',
      valid: true,
      reason: 'Agent Kit invoked headless Estate tools without human/laptop loop.',
    },
    {
      id: 'SIM-02',
      from: 'INBOX_QUEUED',
      event: 'ACQUIRE_CLAIM',
      to: 'CLAIMED',
      valid: true,
      reason: 'Specialist locked deterministic execution claim in Quad-Layer.',
    },
    {
      id: 'SIM-01',
      from: 'IDLE',
      event: 'ENQUEUE_INBOX',
      to: 'INBOX_QUEUED',
      valid: true,
      reason: 'Private Inbox accepted signed Estate instruction payload.',
    },
  ]);

  const [scopeFilter, setScopeFilter] = useState<string>('ALL');
  const [memKey, setMemKey] = useState<string>('');
  const [memScope, setMemScope] = useState<'Estate-Global' | 'Protocol-State' | 'Claim-Ledger'>('Protocol-State');
  const [memValue, setMemValue] = useState<string>('');
  const [memError, setMemError] = useState<string>('');

  const handleFireEvent = (event: ProtocolEvent) => {
    const result = transitionAgentState(simState, event);
    setSimState(result.nextState);
    setSimLog((prev) => [
      {
        id: `SIM-0${prev.length + 1}`,
        from: simState,
        event,
        to: result.nextState,
        valid: result.valid,
        reason: result.reason,
      },
      ...prev.slice(0, 7),
    ]);
  };

  const handleCommitMemory = (e: React.FormEvent) => {
    e.preventDefault();
    if (!memKey.trim() || !memKey.includes('.')) {
      setMemError('Memory key must use dotted namespace notation (e.g., estate.parcel_b.easement_hash).');
      return;
    }
    if (!memValue.trim() || memValue.trim().length < 10) {
      setMemError('Memory value summary must be at least 10 characters.');
      return;
    }
    setMemError('');
    onAddMemoryEntry(memKey.trim(), memScope, memValue.trim());
    setMemKey('');
    setMemValue('');
  };

  const filteredMemory =
    scopeFilter === 'ALL'
      ? memoryEntries
      : memoryEntries.filter((m) => m.scope === scopeFilter);

  return (
    <div className="space-y-10">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-5">
        <div className="text-xs font-medium text-slate-500 dark:text-slate-400">
          Protocol Engineering · Event-Driven State Machines · Headless Memory
        </div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50 mt-1">
          Strict Estate Protocols, Deterministic FSM & Memory Ledger
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-400 mt-1 max-w-3xl">
          Verify how event-driven state machines enforce protocol invariants and block unverified transitions before any side effect reaches the Private Outbox.
        </p>
      </div>

      {/* Section 01: Interactive Event-Driven State Machine Verifier */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        <div className="lg:col-span-7 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-lg p-6 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 dark:border-slate-800 pb-4">
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                01. Event-Driven State Machine Simulator
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Dispatch valid or out-of-order events to test strict protocol transition guards
              </p>
            </div>
            <div className="font-mono text-xs px-3 py-1.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-semibold">
              Active State: {simState}
            </div>
          </div>

          {/* Visual State Graph Nodes */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            {CANONICAL_STATES.map((st, idx) => {
              const isCurrent = st === simState;
              return (
                <div
                  key={st}
                  className={`p-3 rounded-md border text-xs font-mono transition-colors ${
                    isCurrent
                      ? 'bg-slate-900 text-white border-slate-900 dark:bg-slate-100 dark:text-slate-900 dark:border-slate-100 font-bold'
                      : 'bg-slate-50 dark:bg-slate-950 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-800'
                  }`}
                >
                  <div className="text-[10px] opacity-70">0{idx + 1}</div>
                  <div className="truncate mt-0.5">{st}</div>
                </div>
              );
            })}
          </div>

          {/* Event Trigger Buttons */}
          <div className="space-y-2.5">
            <div className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              Trigger Protocol Event on Current State ({simState}):
            </div>
            <div className="flex flex-wrap gap-2">
              {ALL_EVENTS.map((ev) => (
                <button
                  key={ev}
                  type="button"
                  onClick={() => handleFireEvent(ev)}
                  className="px-3 py-1.5 text-xs font-mono font-medium rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                >
                  {ev}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Transition Audit Trace */}
        <div className="lg:col-span-5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-lg p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              Deterministic Transition Guard Log
            </h3>
            <button
              type="button"
              onClick={() => setSimState('IDLE')}
              className="text-xs text-slate-500 hover:text-slate-900 dark:hover:text-white inline-flex items-center gap-1 cursor-pointer"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Reset</span>
            </button>
          </div>

          <div className="divide-y divide-slate-200 dark:divide-slate-800 text-xs max-h-80 overflow-y-auto">
            {simLog.map((entry) => (
              <div key={entry.id} className="py-2.5 space-y-1">
                <div className="flex items-center justify-between font-mono">
                  <span className="inline-flex items-center gap-1.5 font-semibold">
                    {entry.valid ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5 text-rose-600 dark:text-rose-400 shrink-0" />
                    )}
                    <span
                      className={
                        entry.valid
                          ? 'text-emerald-700 dark:text-emerald-400'
                          : 'text-rose-700 dark:text-rose-400'
                      }
                    >
                      {entry.event}
                    </span>
                  </span>
                  <span className="text-slate-500 dark:text-slate-400">
                    {entry.from} → {entry.to}
                  </span>
                </div>
                <p className="text-slate-600 dark:text-slate-400">{entry.reason}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Section 02: Strict Estate Protocol Specifications */}
      <section className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            02. Canonical Estate Protocol Registry
          </h2>
          <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">
            Strict protocols govern every specialist squad, mandating structured claims and cryptographic proofs.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {ESTATE_PROTOCOLS.map((prt) => (
            <div
              key={prt.id}
              className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-lg p-5 space-y-2.5"
            >
              <div className="flex items-center justify-between text-xs font-mono text-slate-500 dark:text-slate-400">
                <span className="font-semibold text-slate-900 dark:text-slate-100">
                  {prt.id}
                </span>
                <span>Proof Schema: {prt.proofFormat}</span>
              </div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                {prt.name}
              </h3>
              <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                {prt.invariants}
              </p>
              <div className="pt-2 border-t border-slate-200 dark:border-slate-800 text-xs text-emerald-700 dark:text-emerald-400 font-medium">
                Expected Yield Standard: {prt.targetYield}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Section 03: Persistent Headless Estate Memory Store */}
      <section className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-lg p-6 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 inline-flex items-center gap-2">
              <Database className="w-4 h-4 text-slate-500" />
              <span>03. Persistent Headless Estate Memory Store ({filteredMemory.length})</span>
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Shared state and proof checkpoints allowing headless specialists to resume workflows without laptop state
            </p>
          </div>

          {/* Interactive Scope Filter Control */}
          <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-lg self-start">
            {(['ALL', 'Estate-Global', 'Protocol-State', 'Claim-Ledger'] as const).map((sc) => (
              <button
                key={sc}
                type="button"
                onClick={() => setScopeFilter(sc)}
                className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                  scopeFilter === sc
                    ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-xs'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                {sc === 'ALL' ? 'All Scopes' : sc}
              </button>
            ))}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400">
                <th className="py-2.5 px-3">Memory Key Namespace</th>
                <th className="py-2.5 px-3">Scope</th>
                <th className="py-2.5 px-3">Committed State / Checkpoint Value</th>
                <th className="py-2.5 px-3 text-right">Revision</th>
                <th className="py-2.5 px-3 text-right">Last Hydrated</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
              {filteredMemory.map((m) => (
                <tr key={m.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                  <td className="py-3 px-3 font-mono font-semibold text-slate-900 dark:text-slate-100">
                    {m.key}
                  </td>
                  <td className="py-3 px-3 text-slate-600 dark:text-slate-400">
                    {m.scope}
                  </td>
                  <td className="py-3 px-3 text-slate-700 dark:text-slate-300">
                    {m.valueSummary}
                  </td>
                  <td className="py-3 px-3 text-right font-mono tabular-nums text-slate-700 dark:text-slate-300">
                    v{m.version}
                  </td>
                  <td className="py-3 px-3 text-right font-mono tabular-nums text-slate-500 dark:text-slate-400">
                    {m.updatedAt}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Commit New Memory Entry Form */}
        <form
          onSubmit={handleCommitMemory}
          className="pt-4 border-t border-slate-200 dark:border-slate-800 space-y-3"
        >
          <div className="text-xs font-semibold text-slate-900 dark:text-slate-100">
            Commit Deterministic Checkpoint to Estate Memory
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
            <div className="sm:col-span-4">
              <label
                htmlFor="mem-key-input"
                className="block text-xs text-slate-600 dark:text-slate-400 mb-1"
              >
                Dotted Memory Key
              </label>
              <input
                id="mem-key-input"
                type="text"
                placeholder="estate.harborview.cam_cap_v2"
                value={memKey}
                onChange={(e) => setMemKey(e.target.value)}
                className="w-full px-3 py-2 text-xs font-mono rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
              />
            </div>

            <div className="sm:col-span-3">
              <label
                htmlFor="mem-scope-select"
                className="block text-xs text-slate-600 dark:text-slate-400 mb-1"
              >
                Memory Scope
              </label>
              <select
                id="mem-scope-select"
                value={memScope}
                onChange={(e) =>
                  setMemScope(
                    e.target.value as 'Estate-Global' | 'Protocol-State' | 'Claim-Ledger'
                  )
                }
                className="w-full px-3 py-2 text-xs rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
              >
                <option value="Protocol-State">Protocol-State</option>
                <option value="Estate-Global">Estate-Global</option>
                <option value="Claim-Ledger">Claim-Ledger</option>
              </select>
            </div>

            <div className="sm:col-span-5">
              <label
                htmlFor="mem-value-input"
                className="block text-xs text-slate-600 dark:text-slate-400 mb-1"
              >
                Checkpoint Value & Proof Hash
              </label>
              <div className="flex gap-2">
                <input
                  id="mem-value-input"
                  type="text"
                  placeholder="Verified 5% HVAC pass-through ceiling sha256:88a1f02c"
                  value={memValue}
                  onChange={(e) => setMemValue(e.target.value)}
                  className="flex-1 px-3 py-2 text-xs rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                />
                <button
                  type="submit"
                  className="px-3.5 py-2 text-xs font-semibold text-white bg-slate-900 dark:bg-slate-100 dark:text-slate-900 rounded-md hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0 inline-flex items-center gap-1 cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Commit Key</span>
                </button>
              </div>
            </div>
          </div>
          {memError && (
            <p role="alert" className="text-xs text-rose-600 dark:text-rose-400 font-medium">
              {memError}
            </p>
          )}
        </form>
      </section>
    </div>
  );
};
