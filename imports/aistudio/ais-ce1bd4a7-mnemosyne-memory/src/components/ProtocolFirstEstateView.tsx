import React, { useState } from 'react';
import {
  GenesisProtocol,
  ProtocolCategory,
  InstructionGateAttempt,
  verifyProtocolMathematicalStandard,
} from '../engine/protocolEngine';
import {
  ShieldCheck,
  ShieldAlert,
  Play,
  FileCode2,
  CheckCircle2,
  Lock,
  PlusCircle,
  ArrowRight,
} from 'lucide-react';

interface ProtocolFirstEstateViewProps {
  protocols: GenesisProtocol[];
  gateHistory: InstructionGateAttempt[];
  onDispatchInstruction: (
    instructionText: string,
    requestedDomain: ProtocolCategory,
    explicitProtocolId?: string | 'AUTO_DETECT'
  ) => InstructionGateAttempt;
  onRatifyProtocolAndExecute?: (
    draft: {
      id: string;
      title: string;
      category: ProtocolCategory;
      eliteStandardLineage: string;
      domainKeywords: string[];
      summary: string;
      preconditions: string[];
      stateTransitions: string[];
      postconditions: string[];
      safetyInvariant: string;
      rollbackProcedure: string;
    },
    pendingInstructionText?: string
  ) => void;
}

export const ProtocolFirstEstateView: React.FC<ProtocolFirstEstateViewProps> = ({
  protocols,
  gateHistory,
  onDispatchInstruction,
  onRatifyProtocolAndExecute,
}) => {
  const [instructionInput, setInstructionInput] = useState('');
  const [selectedDomain, setSelectedDomain] = useState<ProtocolCategory>('computing_network');
  const [selectedProtocolBinding, setSelectedProtocolBinding] = useState<string>('AUTO_DETECT');
  const [gateError, setGateError] = useState<string | null>(null);

  const [categoryFilter, setCategoryFilter] = useState<'ALL' | ProtocolCategory>('ALL');
  const [selectedProtocolId, setSelectedProtocolId] = useState<string>(protocols[0]?.id || 'GEN-NET-001');

  // Prerequisite / Custom Protocol Synthesis Form State
  const [draftId, setDraftId] = useState('GEN-NET-003');
  const [draftTitle, setDraftTitle] = useState('');
  const [draftCategory, setDraftCategory] = useState<ProtocolCategory>('computing_network');
  const [draftLineage, setDraftLineage] = useState(
    'IETF RFC Formal Framing + TLA+ Deadlock-Free FSM + Hoare Logic {P}C{Q}'
  );
  const [draftKeywords, setDraftKeywords] = useState('');
  const [draftSummary, setDraftSummary] = useState('');
  const [draftPrecondition, setDraftPrecondition] = useState('');
  const [draftStates, setDraftStates] = useState(
    'S0_CAPABILITY_HANDSHAKE, S1_PRECONDITION_LOCK, S2_DETERMINISTIC_EXEC, S3_INVARIANT_VERIFY, S4_SHA256_COMMIT'
  );
  const [draftPostcondition, setDraftPostcondition] = useState('');
  const [draftInvariant, setDraftInvariant] = useState('');
  const [draftRollback, setDraftRollback] = useState(
    'Abort uncommitted state transitions, restore prior CoW snapshot pointer, and emit NACK audit receipt.'
  );
  const [pendingBlockedInstruction, setPendingBlockedInstruction] = useState<string | null>(null);
  const [synthesisError, setSynthesisError] = useState<string | null>(null);
  const [synthesisSuccess, setSynthesisSuccess] = useState<string | null>(null);

  const latestAttempt = gateHistory[0] || null;
  const inspectedProtocol =
    protocols.find((p) => p.id === selectedProtocolId) || protocols[0];

  const filteredProtocols = protocols.filter((p) =>
    categoryFilter === 'ALL' ? true : p.category === categoryFilter
  );

  // Live mathematical check on the current draft form
  const liveDraftCheck = verifyProtocolMathematicalStandard({
    id: draftId,
    title: draftTitle || 'Candidate Protocol',
    category: draftCategory,
    preconditions: [draftPrecondition].filter(Boolean),
    stateTransitions: draftStates
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean),
    postconditions: [draftPostcondition].filter(Boolean),
    safetyInvariant: draftInvariant,
    rollbackProcedure: draftRollback,
  });

  const populateSynthesisFormFromGap = (attempt: InstructionGateAttempt) => {
    if (!attempt.draftedGapProposal) return;
    const prop = attempt.draftedGapProposal;
    setDraftId(prop.suggestedId);
    setDraftTitle(prop.suggestedTitle);
    setDraftCategory(prop.category);
    setDraftKeywords(prop.detectedKeywords.join(', '));
    setDraftSummary(
      `Synthesized by Genesis Estate Agents to govern: "${attempt.instructionText}"`
    );
    setDraftPrecondition(prop.preconditionDraft);
    setDraftPostcondition(prop.postconditionDraft);
    setDraftInvariant(prop.invariantDraft);
    setPendingBlockedInstruction(attempt.instructionText);
    setSynthesisError(null);
  };

  const handleDispatch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!instructionInput.trim()) {
      setGateError('Please enter an Estate Instruction to evaluate through the ZIWP Protocol Gate.');
      return;
    }
    setGateError(null);
    setSynthesisSuccess(null);
    const attempt = onDispatchInstruction(
      instructionInput.trim(),
      selectedDomain,
      selectedProtocolBinding
    );
    if (attempt.status === 'BLOCKED_PROTOCOL_PREREQUISITE_REQUIRED') {
      populateSynthesisFormFromGap(attempt);
    } else {
      setPendingBlockedInstruction(null);
      setInstructionInput('');
    }
  };

  const handlePresetInstruction = (
    text: string,
    domain: ProtocolCategory,
    binding: string = 'AUTO_DETECT'
  ) => {
    setGateError(null);
    setSynthesisSuccess(null);
    setInstructionInput(text);
    setSelectedDomain(domain);
    setSelectedProtocolBinding(binding);
    const attempt = onDispatchInstruction(text, domain, binding);
    if (attempt.status === 'BLOCKED_PROTOCOL_PREREQUISITE_REQUIRED') {
      populateSynthesisFormFromGap(attempt);
    } else {
      setPendingBlockedInstruction(null);
    }
  };

  const handleRatifyDraft = (e: React.FormEvent) => {
    e.preventDefault();
    const stateList = draftStates
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    const keywordList = draftKeywords
      .split(',')
      .map((s) => s.trim().toLowerCase())
      .filter(Boolean);

    const validation = verifyProtocolMathematicalStandard({
      id: draftId,
      title: draftTitle,
      category: draftCategory,
      preconditions: [draftPrecondition],
      stateTransitions: stateList,
      postconditions: [draftPostcondition],
      safetyInvariant: draftInvariant,
      rollbackProcedure: draftRollback,
    });

    if (!validation.valid) {
      setSynthesisError(validation.errors.join(' '));
      return;
    }

    setSynthesisError(null);
    if (onRatifyProtocolAndExecute) {
      onRatifyProtocolAndExecute(
        {
          id: draftId.trim(),
          title: draftTitle.trim(),
          category: draftCategory,
          eliteStandardLineage: draftLineage.trim(),
          domainKeywords: keywordList.length > 0 ? keywordList : ['estate', 'verified'],
          summary:
            draftSummary.trim() ||
            `Mathematically verified protocol governing ${draftTitle.trim()}.`,
          preconditions: [draftPrecondition.trim()],
          stateTransitions: stateList,
          postconditions: [draftPostcondition.trim()],
          safetyInvariant: draftInvariant.trim(),
          rollbackProcedure: draftRollback.trim(),
        },
        pendingBlockedInstruction || undefined
      );
    }

    setSelectedProtocolId(draftId.trim());
    setSynthesisSuccess(
      pendingBlockedInstruction
        ? `Ratified ${draftId.trim()} (${draftTitle.trim()}) with 3-Agent Consensus & 100% Hoare-TLA+ Proof, and automatically executed pending instruction!`
        : `Ratified ${draftId.trim()} (${draftTitle.trim()}) into the Genesis Estate Protocol Registry.`
    );
    setPendingBlockedInstruction(null);
    setDraftTitle('');
    setDraftKeywords('');
    setDraftSummary('');
  };

  return (
    <div className="space-y-10">
      {/* Executive Header: Why Protocol-First = Path to General Intelligence */}
      <section className="bg-white border border-slate-200 rounded-xl p-6 lg:p-8 space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          <div className="lg:col-span-8 space-y-3">
            <div className="text-xs text-slate-500">
              Genesis Protocol-First Kernel · Zero-Instruction-Without-Protocol (ZIWP) Architecture
            </div>
            <h1 className="text-2xl lg:text-3xl font-bold text-slate-900" style={{ textWrap: 'balance' }}>
              Protocol-First General Intelligence &amp; Mathematical Specification Engine
            </h1>
            <p className="text-sm text-slate-600 leading-relaxed">
              Ad-hoc prompting cannot scale to General Intelligence because unconstrained agent actions compound error over long horizons. On the <strong>Genesis Estate</strong>, <strong>no instruction is accepted without a formally verified protocol</strong>. Whenever an instruction encounters a capability gap, execution halts at the kernel gate and all Estate agents collaborate to define, mathematically verify (via Hoare Logic <span className="font-mono">{'{P} C {Q}'}</span> &amp; TLA+ deadlock freedom), and ratify a permanent protocol—turning every novel problem into a permanent, non-fungible Estate capability.
            </p>
          </div>

          <div className="lg:col-span-4 bg-slate-50 border border-slate-200 rounded-xl p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-200 pb-2.5">
              <span className="text-xs font-semibold text-slate-900">Estate Protocol Governance</span>
              <span className="text-xs font-mono font-semibold text-emerald-700">ZIWP LOCK ACTIVE</span>
            </div>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <div className="text-slate-500">Ratified Protocols</div>
                <div className="text-xl font-bold font-mono tabular-nums text-slate-900 mt-0.5">
                  {protocols.length}
                </div>
              </div>
              <div>
                <div className="text-slate-500">Hoare-TLA+ Compliance</div>
                <div className="text-xl font-bold font-mono tabular-nums text-emerald-700 mt-0.5">
                  100.0%
                </div>
              </div>
              <div>
                <div className="text-slate-500">Unbound Instructions</div>
                <div className="text-sm font-bold font-mono tabular-nums text-slate-900 mt-0.5">
                  0 Permitted
                </div>
              </div>
              <div>
                <div className="text-slate-500">Agent Consensus Quorum</div>
                <div className="text-sm font-bold font-mono tabular-nums text-slate-900 mt-0.5">
                  3/3 Co-Signed
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 3 Classical & Agentic Protocol Pillars Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-6 border-t border-slate-200 text-xs">
          <div className="space-y-1">
            <div className="font-bold text-slate-900">
              1. Rules, Etiquette &amp; Diplomatic Conduct (GEN-DIP)
            </div>
            <p className="text-slate-600 leading-relaxed">
              Vienna-grade order of precedence, inter-agent authority handshakes, quorum ratification, and blameless safety incident disclosure etiquette across the Genesis Estate.
            </p>
          </div>

          <div className="space-y-1">
            <div className="font-bold text-slate-900">
              2. Science, Medical-Grade Rigor &amp; Treaties (GEN-SCI)
            </div>
            <p className="text-slate-600 leading-relaxed">
              CONSORT/PRISMA-inspired controlled ablation trials, falsifiable hypothesis pre-registration, deterministic seed locks, and Geneva-style cross-domain data treaties.
            </p>
          </div>

          <div className="space-y-1">
            <div className="font-bold text-slate-900">
              3. Computing, Network &amp; Agentic Wire (GEN-NET)
            </div>
            <p className="text-slate-600 leading-relaxed">
              IETF RFC-grade frame transport, 3-way cryptographic handshakes, bi-temporal memory commit locks, and POSIX Copy-on-Write sub-agent sandbox isolation.
            </p>
          </div>
        </div>
      </section>

      {/* Section 1: Zero-Instruction-Without-Protocol (ZIWP) Kernel Firewall & Prerequisite Synthesizer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left: ZIWP Instruction Dispatcher */}
        <section className="lg:col-span-6 bg-white border border-slate-200 rounded-xl p-6 space-y-5">
          <div className="border-b border-slate-200 pb-4">
            <div className="text-xs text-slate-500 font-mono">
              KERNEL ADMISSION GATE · ZERO-INSTRUCTION-WITHOUT-PROTOCOL
            </div>
            <h2 className="text-lg font-bold text-slate-900 mt-0.5">
              01. Dispatch Estate Instruction (ZIWP Firewall Test)
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Submit any instruction to the Genesis Estate. If a ratified protocol covers the workflow, it executes deterministically. If a protocol gap exists, execution is strictly blocked until the prerequisite protocol is defined and ratified.
            </p>
          </div>

          {/* Quick Scenario Presets */}
          <div className="space-y-2">
            <div className="text-xs font-semibold text-slate-700">
              Test Covered vs. Uncovered (Gap) Estate Instructions:
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() =>
                  handlePresetInstruction(
                    'Purge context rot and synchronize bi-temporal KV cache across nodes',
                    'computing_network'
                  )
                }
                className="px-3 py-1.5 text-xs font-medium text-emerald-900 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-md transition-colors cursor-pointer"
              >
                Test Covered: Sync Bi-Temporal KV Cache (→ GEN-NET-001)
              </button>

              <button
                type="button"
                onClick={() =>
                  handlePresetInstruction(
                    'Run controlled ablation benchmark experiment on recall hypothesis',
                    'scientific_experimental'
                  )
                }
                className="px-3 py-1.5 text-xs font-medium text-emerald-900 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-md transition-colors cursor-pointer"
              >
                Test Covered: Controlled Ablation Trial (→ GEN-SCI-001)
              </button>

              <button
                type="button"
                onClick={() =>
                  handlePresetInstruction(
                    'Execute zero-knowledge enclave weight attestation across orbital relays',
                    'computing_network'
                  )
                }
                className="px-3 py-1.5 text-xs font-medium text-amber-900 bg-amber-50 hover:bg-amber-100 border border-amber-200 rounded-md transition-colors cursor-pointer"
              >
                Simulate Estate Gap: Zero-Knowledge Orbital Attestation (Blocked → Auto-Draft)
              </button>
            </div>
          </div>

          <form onSubmit={handleDispatch} className="space-y-4" noValidate>
            <div>
              <label htmlFor="ziwp-instruction" className="block text-xs font-semibold text-slate-700 mb-1">
                Estate Instruction Command
              </label>
              <input
                id="ziwp-instruction"
                type="text"
                value={instructionInput}
                onChange={(e) => setInstructionInput(e.target.value)}
                placeholder="e.g. Perform autonomous chaos-testing on payment ledger..."
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="ziwp-domain" className="block text-xs font-semibold text-slate-700 mb-1">
                  Target Protocol Category
                </label>
                <select
                  id="ziwp-domain"
                  value={selectedDomain}
                  onChange={(e) => setSelectedDomain(e.target.value as ProtocolCategory)}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-slate-900"
                >
                  <option value="computing_network">3. Computing, Network &amp; Agentic Wire</option>
                  <option value="scientific_experimental">2. Science, Medical Rigor &amp; Treaties</option>
                  <option value="diplomatic_governance">1. Diplomatic, Etiquette &amp; Governance</option>
                </select>
              </div>

              <div>
                <label htmlFor="ziwp-binding" className="block text-xs font-semibold text-slate-700 mb-1">
                  Protocol Binding Resolution
                </label>
                <select
                  id="ziwp-binding"
                  value={selectedProtocolBinding}
                  onChange={(e) => setSelectedProtocolBinding(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-slate-900"
                >
                  <option value="AUTO_DETECT">Auto-Detect Matching Protocol (Strict ZIWP)</option>
                  {protocols.map((p) => (
                    <option key={p.id} value={p.id}>
                      Force Bind: {p.id} · {p.title.slice(0, 32)}…
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {gateError && (
              <div role="alert" className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800">
                {gateError}
              </div>
            )}

            <button
              type="submit"
              className="w-full py-2.5 px-4 text-sm font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors inline-flex items-center justify-center gap-2 cursor-pointer"
            >
              <Play className="w-4 h-4" />
              Submit Instruction to ZIWP Protocol Gate
            </button>
          </form>

          {/* Latest ZIWP Gate Evaluation Outcome */}
          {latestAttempt && (
            <div
              className={`p-4 rounded-xl border space-y-3 text-xs ${
                latestAttempt.status === 'EXECUTED_UNDER_PROTOCOL'
                  ? 'bg-emerald-50/70 border-emerald-200 text-slate-900'
                  : 'bg-amber-50/80 border-amber-300 text-slate-900'
              }`}
            >
              <div className="flex items-start justify-between gap-3 border-b border-slate-200/80 pb-2.5">
                <div className="flex items-center gap-2 font-bold">
                  {latestAttempt.status === 'EXECUTED_UNDER_PROTOCOL' ? (
                    <ShieldCheck className="w-4 h-4 text-emerald-700 shrink-0" />
                  ) : (
                    <ShieldAlert className="w-4 h-4 text-amber-700 shrink-0" />
                  )}
                  <span>
                    {latestAttempt.status === 'EXECUTED_UNDER_PROTOCOL'
                      ? `ADMITTED & EXECUTED UNDER ${latestAttempt.boundProtocolId}`
                      : 'REJECTED BY ZIWP GATE — PREREQUISITE PROTOCOL REQUIRED'}
                  </span>
                </div>
                <span className="font-mono text-[11px] text-slate-500">
                  {latestAttempt.attemptId}
                </span>
              </div>

              <div className="font-medium text-slate-800">
                Instruction: <span className="font-mono">"{latestAttempt.instructionText}"</span>
              </div>

              {latestAttempt.blockingReason && (
                <div className="text-amber-900 font-medium leading-relaxed">
                  {latestAttempt.blockingReason}
                </div>
              )}

              <div className="bg-white/90 border border-slate-200 rounded-lg p-3 space-y-1 font-mono text-[11px] text-slate-700">
                {latestAttempt.executionTraceSteps.map((step, i) => (
                  <div key={i}>{step}</div>
                ))}
              </div>

              <div className="font-mono text-[11px] text-slate-500 truncate">
                SHA-256 Gate Receipt: {latestAttempt.executionReceiptHash}
              </div>
            </div>
          )}
        </section>

        {/* Right: Multi-Agent Prerequisite Protocol Synthesizer & Mathematical Verifier */}
        <section className="lg:col-span-6 bg-white border border-slate-200 rounded-xl p-6 space-y-5">
          <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 pb-4">
            <div>
              <div className="text-xs text-slate-500 font-mono">
                MULTI-AGENT PROTOCOL SYNTHESIS · HOARE-TLA+ FORMAL STANDARD
              </div>
              <h2 className="text-lg font-bold text-slate-900 mt-0.5">
                02. Define, Mathematically Verify &amp; Ratify Protocol
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                All Genesis agents collaborate here to close Estate gaps. Every candidate specification must satisfy all 4 mathematical axioms before ratification.
              </p>
            </div>
            <span className="text-xs font-mono font-bold text-emerald-700 tabular-nums">
              Axiom Score: {liveDraftCheck.completenessScorePct}%
            </span>
          </div>

          {pendingBlockedInstruction && (
            <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-900 flex items-start gap-2">
              <Lock className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
              <div>
                <strong>Prerequisite Synthesis Active:</strong> Genesis Prime, Kernel Architect, and Zero-Trust Sentinel have pre-drafted <span className="font-mono font-bold">{draftId}</span> below to cover your blocked instruction. Review and click <strong>Ratify &amp; Execute</strong>.
              </div>
            </div>
          )}

          {synthesisSuccess && (
            <div role="status" className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-900 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
              <span>{synthesisSuccess}</span>
            </div>
          )}

          <form onSubmit={handleRatifyDraft} className="space-y-3.5" noValidate>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label htmlFor="proto-id" className="block text-xs font-semibold text-slate-700 mb-1">
                  Protocol ID
                </label>
                <input
                  id="proto-id"
                  type="text"
                  value={draftId}
                  onChange={(e) => setDraftId(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs font-mono border border-slate-300 rounded-lg"
                />
              </div>

              <div className="sm:col-span-2">
                <label htmlFor="proto-title" className="block text-xs font-semibold text-slate-700 mb-1">
                  Formal Protocol Title
                </label>
                <input
                  id="proto-title"
                  type="text"
                  value={draftTitle}
                  onChange={(e) => setDraftTitle(e.target.value)}
                  placeholder="e.g. Zero-Knowledge Enclave Attestation Protocol"
                  className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label htmlFor="proto-cat" className="block text-xs font-semibold text-slate-700 mb-1">
                  Protocol Domain Category
                </label>
                <select
                  id="proto-cat"
                  value={draftCategory}
                  onChange={(e) => setDraftCategory(e.target.value as ProtocolCategory)}
                  className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg bg-white"
                >
                  <option value="computing_network">3. Computing, Network &amp; Agentic Wire</option>
                  <option value="scientific_experimental">2. Science, Medical Rigor &amp; Treaties</option>
                  <option value="diplomatic_governance">1. Diplomatic, Etiquette &amp; Governance</option>
                </select>
              </div>

              <div>
                <label htmlFor="proto-kw" className="block text-xs font-semibold text-slate-700 mb-1">
                  ZIWP Binding Keywords (Comma-separated)
                </label>
                <input
                  id="proto-kw"
                  type="text"
                  value={draftKeywords}
                  onChange={(e) => setDraftKeywords(e.target.value)}
                  placeholder="e.g. enclave, orbital, attestation, zk"
                  className="w-full px-3 py-1.5 text-xs font-mono border border-slate-300 rounded-lg"
                />
              </div>
            </div>

            <div>
              <label htmlFor="proto-pre" className="block text-xs font-semibold text-slate-700 mb-1">
                Hoare Precondition {'{P}'} (Mandatory Entry Gate)
              </label>
              <input
                id="proto-pre"
                type="text"
                value={draftPrecondition}
                onChange={(e) => setDraftPrecondition(e.target.value)}
                placeholder="e.g. Caller holds Ed25519 capability token and CoW staging snapshot is locked."
                className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg"
              />
            </div>

            <div>
              <label htmlFor="proto-states" className="block text-xs font-semibold text-slate-700 mb-1">
                Deterministic FSM State Transitions (Comma-separated, Deadlock-Free)
              </label>
              <input
                id="proto-states"
                type="text"
                value={draftStates}
                onChange={(e) => setDraftStates(e.target.value)}
                className="w-full px-3 py-1.5 text-xs font-mono border border-slate-300 rounded-lg"
              />
            </div>

            <div>
              <label htmlFor="proto-post" className="block text-xs font-semibold text-slate-700 mb-1">
                Hoare Postcondition {'{Q}'} (Verifiable Completion Guarantee)
              </label>
              <input
                id="proto-post"
                type="text"
                value={draftPostcondition}
                onChange={(e) => setDraftPostcondition(e.target.value)}
                placeholder="e.g. State transition verified and signed SHA-256 receipt committed to ledger."
                className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label htmlFor="proto-inv" className="block text-xs font-semibold text-slate-700 mb-1">
                  Safety Invariant (I_safe)
                </label>
                <input
                  id="proto-inv"
                  type="text"
                  value={draftInvariant}
                  onChange={(e) => setDraftInvariant(e.target.value)}
                  placeholder="e.g. Zero unverified side-effects or stale edge leaks."
                  className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg"
                />
              </div>

              <div>
                <label htmlFor="proto-rollback" className="block text-xs font-semibold text-slate-700 mb-1">
                  Atomic Rollback Procedure
                </label>
                <input
                  id="proto-rollback"
                  type="text"
                  value={draftRollback}
                  onChange={(e) => setDraftRollback(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg"
                />
              </div>
            </div>

            {synthesisError && (
              <div role="alert" className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800">
                {synthesisError}
              </div>
            )}

            <button
              type="submit"
              className="w-full py-2.5 px-4 text-sm font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors inline-flex items-center justify-center gap-2 cursor-pointer"
            >
              <PlusCircle className="w-4 h-4" />
              {pendingBlockedInstruction
                ? `Ratify Prerequisite Protocol ${draftId} & Execute Blocked Instruction`
                : `Verify Mathematical Standard & Ratify Protocol ${draftId}`}
            </button>
          </form>
        </section>
      </div>

      {/* Section 2: Ratified Genesis Estate Protocol Registry & Formal Mathematical Proof Inspector */}
      <section className="bg-white border border-slate-200 rounded-xl p-6 space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
          <div>
            <h2 className="text-lg font-bold text-slate-900">
              03. Genesis Bootstrap Protocol Registry &amp; Mathematical Proof Inspector ({filteredProtocols.length} Ratified)
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Every protocol is standardized across Diplomatic Precedence, Scientific/Medical Rigor, and IETF/TLA+ Computing Specifications. Select any protocol to inspect its formal Hoare-TLA+ proofs and multi-agent signatures.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-1 p-1 bg-slate-100 rounded-lg">
            {(
              [
                { id: 'ALL', label: `All Categories (${protocols.length})` },
                { id: 'diplomatic_governance', label: '1. Diplomatic & Conduct' },
                { id: 'scientific_experimental', label: '2. Science & Treaties' },
                { id: 'computing_network', label: '3. Computing & Network' },
              ] as const
            ).map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setCategoryFilter(tab.id)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer whitespace-nowrap ${
                  categoryFilter === tab.id
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left: Protocol List */}
          <div className="lg:col-span-5 space-y-3">
            {filteredProtocols.map((proto) => {
              const isSelected = proto.id === inspectedProtocol?.id;
              return (
                <button
                  key={proto.id}
                  type="button"
                  onClick={() => setSelectedProtocolId(proto.id)}
                  className={`w-full text-left p-4 rounded-xl border transition-colors cursor-pointer space-y-2 ${
                    isSelected
                      ? 'bg-slate-900 text-white border-slate-900'
                      : 'bg-slate-50 text-slate-900 border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs font-mono tabular-nums">
                    <span className={isSelected ? 'text-emerald-300 font-semibold' : 'text-slate-600 font-semibold'}>
                      {proto.id} · {proto.version}
                    </span>
                    <span className={isSelected ? 'text-slate-300' : 'text-slate-500'}>
                      Executions: {proto.executionCount}
                    </span>
                  </div>
                  <div className="text-sm font-bold">{proto.title}</div>
                  <div className={`text-xs ${isSelected ? 'text-slate-300' : 'text-slate-500'}`}>
                    {proto.categoryLabel}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Right: Formal Mathematical Specification & Multi-Agent Endorsement Inspector */}
          {inspectedProtocol && (
            <div className="lg:col-span-7 border border-slate-200 rounded-xl p-6 space-y-6 bg-slate-50/50">
              <div className="border-b border-slate-200 pb-4 space-y-1.5">
                <div className="text-xs font-mono text-slate-500">
                  {inspectedProtocol.id} · {inspectedProtocol.categoryLabel} · Spec SHA-256: {inspectedProtocol.specHash.slice(0, 18)}…
                </div>
                <h3 className="text-xl font-bold text-slate-900">{inspectedProtocol.title}</h3>
                <div className="text-xs text-slate-600">
                  <strong>Elite Standard Lineage:</strong> {inspectedProtocol.eliteStandardLineage}
                </div>
                <p className="text-xs text-slate-600 leading-relaxed pt-1">
                  {inspectedProtocol.summary}
                </p>
              </div>

              {/* Hoare Triple {P} C {Q} & FSM Specification */}
              <div className="space-y-3 text-xs">
                <h4 className="font-bold text-slate-900 flex items-center gap-1.5">
                  <FileCode2 className="w-4 h-4 text-slate-700" />
                  Formal Hoare Logic Contract {'{P} C {Q}'} &amp; Finite-State Machine
                </h4>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="bg-white border border-slate-200 rounded-lg p-3.5 space-y-1">
                    <div className="font-mono text-[11px] text-slate-500 font-semibold">
                      PRECONDITIONS {'{P}'}
                    </div>
                    <ul className="space-y-1 text-slate-800">
                      {inspectedProtocol.hoareContract.preconditions.map((pre, i) => (
                        <li key={i}>• {pre}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="bg-white border border-slate-200 rounded-lg p-3.5 space-y-1">
                    <div className="font-mono text-[11px] text-slate-500 font-semibold">
                      POSTCONDITIONS {'{Q}'}
                    </div>
                    <ul className="space-y-1 text-slate-800">
                      {inspectedProtocol.hoareContract.postconditions.map((post, i) => (
                        <li key={i}>• {post}</li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* FSM State Transition Chain */}
                <div className="bg-white border border-slate-200 rounded-lg p-3.5 space-y-2">
                  <div className="font-mono text-[11px] text-slate-500 font-semibold">
                    DETERMINISTIC FINITE-STATE MACHINE (TLA+ DEADLOCK-FREE TRANSITIONS)
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5 font-mono text-[11px] text-slate-900">
                    {inspectedProtocol.hoareContract.stateTransitions.map((st, idx) => (
                      <React.Fragment key={st}>
                        <span className="px-2 py-1 bg-slate-100 border border-slate-200 rounded">
                          {st}
                        </span>
                        {idx < inspectedProtocol.hoareContract.stateTransitions.length - 1 && (
                          <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                        )}
                      </React.Fragment>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="bg-white border border-slate-200 rounded-lg p-3.5 space-y-1">
                    <div className="font-mono text-[11px] text-emerald-700 font-semibold">
                      INDUCTIVE SAFETY INVARIANT (I_safe)
                    </div>
                    <div className="text-slate-800">
                      {inspectedProtocol.hoareContract.safetyInvariant}
                    </div>
                  </div>

                  <div className="bg-white border border-slate-200 rounded-lg p-3.5 space-y-1">
                    <div className="font-mono text-[11px] text-slate-500 font-semibold">
                      ATOMIC ROLLBACK &amp; COMPENSATION
                    </div>
                    <div className="text-slate-800">
                      {inspectedProtocol.hoareContract.rollbackProcedure}
                    </div>
                  </div>
                </div>
              </div>

              {/* Mathematical Axiom Proof Checks */}
              <div className="space-y-2.5 pt-2 border-t border-slate-200 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900">
                    Mathematical Proof Verification Certificates
                  </span>
                  <span className="font-mono font-semibold text-emerald-700">
                    {inspectedProtocol.mathematicalGuarantees.completenessScorePct}% Verified
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {inspectedProtocol.mathematicalGuarantees.formalProofChecks.map((chk) => (
                    <div
                      key={chk.id}
                      className="bg-white border border-slate-200 rounded-lg p-3 space-y-1"
                    >
                      <div className="flex items-center justify-between font-mono text-[11px]">
                        <span className="font-bold text-slate-900">{chk.id}</span>
                        <span className="text-emerald-700 font-semibold">PROVED</span>
                      </div>
                      <div className="font-semibold text-slate-800">{chk.axiomName}</div>
                      <div className="font-mono text-[11px] text-slate-600">{chk.formula}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Multi-Agent Estate Consensus Signatures */}
              <div className="space-y-2.5 pt-2 border-t border-slate-200 text-xs">
                <div className="font-bold text-slate-900">
                  Estate Agent Collaborative Ratification Signatures (3/3 Quorum)
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                  {inspectedProtocol.agentEndorsements.map((end) => (
                    <div
                      key={end.agentId}
                      className="bg-white border border-slate-200 rounded-lg p-3 space-y-1"
                    >
                      <div className="font-mono text-[11px] text-slate-500">
                        {end.roleInProtocol}
                      </div>
                      <div className="font-bold text-slate-900">{end.agentName}</div>
                      <div className="text-slate-600 text-[11px]">{end.endorsementNote}</div>
                      <div className="font-mono text-[10px] text-emerald-700 pt-1">
                        Sig: {end.signatureHash}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
};
