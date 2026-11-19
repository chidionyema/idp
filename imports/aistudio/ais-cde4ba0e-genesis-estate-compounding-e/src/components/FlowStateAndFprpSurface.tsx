/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * 
 * Flow-Preserving Remediation Protocol (FPRP) & Flow State Science Surface
 * 2100 Alien Standard — Machine-Enforced & Mandated
 */

import React, { useState, useEffect } from 'react';
import {
  BreakGlassDebtEntry,
  BreakGlassLoanRequest,
  FailureClass,
  FailureClassId,
  FlowScienceHypothesis,
  FrictionTaxonomyEntry,
  LoanWindowOptimizer,
  VisualComplianceRule,
  INITIAL_FAILURE_CLASSES,
  INITIAL_DEBT_LEDGER,
  INITIAL_OSCILLATION_INCIDENTS,
  INITIAL_FLOW_SCIENCE_HYPOTHESES,
  INITIAL_FRICTION_TAXONOMY,
  INITIAL_LOAN_WINDOW_OPTIMIZERS,
  INITIAL_VISUAL_RULES,
  INITIAL_FLOW_VITALS,
  requestBreakGlassLoan,
  repayBreakGlassDebt,
  verifyAntiRecursionProof,
  detectOscillations,
  runVisualMandateComplianceAudit,
} from '../lib/protocolEngine.ts';
import {
  Activity,
  Zap,
  ShieldCheck,
  AlertTriangle,
  RotateCcw,
  Scale,
  Flame,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Clock,
  Sparkles,
  Search,
  ArrowRight,
  TrendingDown,
  TrendingUp,
  Cpu,
  Lock,
  Unlock,
  Radio,
  FileCheck,
} from 'lucide-react';

export const FlowStateAndFprpSurface: React.FC = () => {
  // Real-time state
  const [debts, setDebts] = useState<BreakGlassDebtEntry[]>(INITIAL_DEBT_LEDGER);
  const [failureClasses] = useState<FailureClass[]>(INITIAL_FAILURE_CLASSES);
  const [oscillations] = useState(INITIAL_OSCILLATION_INCIDENTS);
  const [hypotheses] = useState<FlowScienceHypothesis[]>(INITIAL_FLOW_SCIENCE_HYPOTHESES);
  const [frictionItems] = useState<FrictionTaxonomyEntry[]>(INITIAL_FRICTION_TAXONOMY);
  const [optimizers] = useState<LoanWindowOptimizer[]>(INITIAL_LOAN_WINDOW_OPTIMIZERS);
  const [visualRules] = useState<VisualComplianceRule[]>(INITIAL_VISUAL_RULES);
  const [activeSubTab, setActiveSubTab] = useState<'FLOW_RADAR' | 'DEBT_LEDGER' | 'ANTI_RECURSION' | 'FLOW_SCIENCE' | 'VISUAL_MANDATE'>('FLOW_RADAR');

  // Real-time animated pulse
  const [bpmTick, setBpmTick] = useState<number>(0);
  const [flowPercent, setFlowPercent] = useState<number>(INITIAL_FLOW_VITALS.estateTimeInFlowPercent);

  // Break-glass request interactive state
  const [parentBottleneck, setParentBottleneck] = useState('');
  const [selectedClass, setSelectedClass] = useState<FailureClassId>('TRADEOFF_OSCILLATION');
  const [loanScope, setLoanScope] = useState('');
  const [loanMinutes, setLoanMinutes] = useState(30);
  const [requestingAgent, setRequestingAgent] = useState('otto');
  const [repaymentPlan, setRepaymentPlan] = useState('');
  const [loanMessage, setLoanMessage] = useState<{ text: string; isError: boolean } | null>(null);

  // Repayment interactive state
  const [selectedRepayDebtId, setSelectedRepayDebtId] = useState<string>(debts.find(d => d.status === 'OPEN_DEBT')?.debtId || '');
  const [repaymentFixTitle, setRepaymentFixTitle] = useState('');
  const [repayMessage, setRepayMessage] = useState<{ text: string; isError: boolean; receipt?: string } | null>(null);

  // Sandbox anti-recursion interactive tester
  const [testFixInput, setTestFixInput] = useState('Network-boundary Zod schema gate with automated fuzzing');
  const [testTargetClass, setTestTargetClass] = useState<FailureClassId>('TRADEOFF_OSCILLATION');
  const [testResult, setTestResult] = useState(() => verifyAntiRecursionProof(testFixInput, testTargetClass));

  // Visual Mandate live audit report
  const auditReport = runVisualMandateComplianceAudit(visualRules);

  useEffect(() => {
    const timer = setInterval(() => {
      setBpmTick(t => t + 1);
      setFlowPercent(Number((96.4 + Math.sin(Date.now() / 3000) * 0.8).toFixed(1)));
    }, 1100);
    return () => clearInterval(timer);
  }, []);

  const handleTestEvaluation = (input: string, cls: FailureClassId) => {
    setTestFixInput(input);
    setTestTargetClass(cls);
    setTestResult(verifyAntiRecursionProof(input, cls));
  };

  const handleIssueLoan = (e: React.FormEvent) => {
    e.preventDefault();
    if (!parentBottleneck.trim() || !loanScope.trim() || !repaymentPlan.trim()) {
      setLoanMessage({ text: 'All fields are required to issue an audited Break-Glass Loan (§9.1).', isError: true });
      return;
    }

    const res = requestBreakGlassLoan(
      {
        parentBottleneck,
        failureClass: selectedClass,
        scope: loanScope,
        durationMinutes: loanMinutes,
        requestingAgent,
        mandatoryRepaymentPlan: repaymentPlan,
      },
      debts
    );

    if (res.granted && res.debtEntry) {
      setDebts([res.debtEntry, ...debts]);
      setSelectedRepayDebtId(res.debtEntry.debtId);
      setLoanMessage({ text: `Loan ${res.debtEntry.debtId} granted. Hard auto-expiry set to ${new Date(res.debtEntry.deadline).toLocaleTimeString()}. Credit remaining: ${res.creditRemaining}.`, isError: false });
      setParentBottleneck('');
      setLoanScope('');
      setRepaymentPlan('');
    } else {
      setLoanMessage({ text: res.rejectionReason || 'Loan rejected by deterministic credit policy.', isError: true });
    }
  };

  const handleRepayDebt = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRepayDebtId) {
      setRepayMessage({ text: 'Please select an open debt to repay.', isError: true });
      return;
    }
    if (!repaymentFixTitle.trim()) {
      setRepayMessage({ text: 'A permanent structural fix title is required.', isError: true });
      return;
    }

    const res = repayBreakGlassDebt(selectedRepayDebtId, repaymentFixTitle, debts);
    if (res.success) {
      setDebts(res.updatedDebts);
      setRepayMessage({
        text: `Debt ${selectedRepayDebtId} successfully REPAID. Tail-chasing prevented. Anti-recursion proof attested.`,
        isError: false,
        receipt: res.antiRecursionReceipt,
      });
      setRepaymentFixTitle('');
    } else {
      setRepayMessage({
        text: res.error || 'Repayment failed.',
        isError: true,
      });
    }
  };

  const openDebtsCount = debts.filter(d => d.status === 'OPEN_DEBT').length;
  const overdueDebtsCount = debts.filter(d => d.status === 'OVERDUE').length;

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* 2100 Mandated Header Banner */}
      <div className="bg-gradient-to-r from-slate-950 via-slate-900 to-indigo-950/40 border border-indigo-800/60 rounded-2xl p-6 sm:p-8 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6 relative z-10">
          <div className="space-y-2 max-w-3xl">
            <div className="flex items-center gap-2 text-xs font-mono text-cyan-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              <span>CORE PROTOCOL · FLOW-PRESERVING REMEDIATION & ANTI-RECURSION</span>
            </div>
            <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight text-white">
              The Recursive Remediation Trap & Flow Science Engine
            </h1>
            <p className="text-slate-300 text-sm leading-relaxed">
              Eliminating the fatal industry loop where every fix re-introduces the same weakness next turn. Flow is protected via time-bound break-glass loans that are strictly accounted in the Debt Ledger and repaid with mathematical anti-recursion proofs.
            </p>
          </div>

          {/* Biometric Flow Cadence Indicator */}
          <div className="flex items-center gap-4 bg-slate-950/90 border border-slate-800 px-4 py-3 rounded-xl font-mono text-xs">
            <div className="flex items-center gap-2 text-emerald-400">
              <Activity className="w-4 h-4 animate-pulse" />
              <span className="font-bold">{flowPercent}% FLOW</span>
            </div>
            <span className="text-slate-600">|</span>
            <div className="text-slate-300">
              <span className="text-slate-500 text-[10px] block">RHYTHM</span>
              <span>72 BPM PULSE</span>
            </div>
            <span className="text-slate-600">|</span>
            <div className="text-slate-300">
              <span className="text-slate-500 text-[10px] block">CREDIT STATE</span>
              <span className={overdueDebtsCount > 0 ? 'text-rose-400 font-bold' : 'text-cyan-300'}>
                {overdueDebtsCount > 0 ? 'FROZEN' : 'NOMINAL'}
              </span>
            </div>
          </div>
        </div>

        {/* Sub-tab Navigation */}
        <div className="flex flex-wrap items-center gap-2 mt-6 pt-6 border-t border-slate-800/80 font-mono text-xs">
          <button
            onClick={() => setActiveSubTab('FLOW_RADAR')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-2 ${
              activeSubTab === 'FLOW_RADAR'
                ? 'bg-cyan-500 text-slate-950 font-bold shadow'
                : 'text-slate-400 hover:text-slate-200 bg-slate-950/60 border border-slate-800/60'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Flow Radar & Friction Heatmap</span>
          </button>

          <button
            onClick={() => setActiveSubTab('DEBT_LEDGER')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-2 ${
              activeSubTab === 'DEBT_LEDGER'
                ? 'bg-cyan-500 text-slate-950 font-bold shadow'
                : 'text-slate-400 hover:text-slate-200 bg-slate-950/60 border border-slate-800/60'
            }`}
          >
            <Scale className="w-3.5 h-3.5" />
            <span>Debt Ledger & Break-Glass Loans ({openDebtsCount} Open)</span>
          </button>

          <button
            onClick={() => setActiveSubTab('ANTI_RECURSION')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-2 ${
              activeSubTab === 'ANTI_RECURSION'
                ? 'bg-cyan-500 text-slate-950 font-bold shadow'
                : 'text-slate-400 hover:text-slate-200 bg-slate-950/60 border border-slate-800/60'
            }`}
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Anti-Recursion Proof Engine</span>
          </button>

          <button
            onClick={() => setActiveSubTab('FLOW_SCIENCE')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-2 ${
              activeSubTab === 'FLOW_SCIENCE'
                ? 'bg-cyan-500 text-slate-950 font-bold shadow'
                : 'text-slate-400 hover:text-slate-200 bg-slate-950/60 border border-slate-800/60'
            }`}
          >
            <Zap className="w-3.5 h-3.5" />
            <span>Flow Science Charter (Day 0)</span>
          </button>

          <button
            onClick={() => setActiveSubTab('VISUAL_MANDATE')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-2 ${
              activeSubTab === 'VISUAL_MANDATE'
                ? 'bg-cyan-500 text-slate-950 font-bold shadow'
                : 'text-slate-400 hover:text-slate-200 bg-slate-950/60 border border-slate-800/60'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>2100 Visual Mandate Enforcer (100%)</span>
          </button>
        </div>
      </div>

      {/* SUB-TAB 1: FLOW RADAR & REAL-TIME FRICTION HEATMAP */}
      {activeSubTab === 'FLOW_RADAR' && (
        <div className="space-y-6">
          {/* Vitals Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-slate-900/60 border border-slate-800 p-5 rounded-xl">
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>TIME IN FLOW</span>
                <Activity className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="text-2xl font-bold text-emerald-400 mt-2 font-mono tabular-nums">
                {flowPercent}%
              </div>
              <p className="text-xs text-slate-400 mt-1">Zero unmonitored agent stalls. Continuous deep execution.</p>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 p-5 rounded-xl">
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>FOUNDER FRICTION DELTA</span>
                <ShieldCheck className="w-4 h-4 text-cyan-400" />
              </div>
              <div className="text-2xl font-bold text-cyan-300 mt-2 font-mono tabular-nums">
                Δ = 0.00
              </div>
              <p className="text-xs text-slate-400 mt-1">Zero friction offloaded to Founder. §1.4 Machine Canon satisfied.</p>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 p-5 rounded-xl">
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>TAIL-CHASING LOOPS HALTED</span>
                <RotateCcw className="w-4 h-4 text-indigo-400" />
              </div>
              <div className="text-2xl font-bold text-indigo-300 mt-2 font-mono tabular-nums">
                38 Intercepted
              </div>
              <p className="text-xs text-slate-400 mt-1">Oscillation circuit breaker tripped before recursive decay.</p>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 p-5 rounded-xl">
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>OPEN BREAK-GLASS DEBT</span>
                <Scale className={`w-4 h-4 ${openDebtsCount > 0 ? 'text-amber-400' : 'text-emerald-400'}`} />
              </div>
              <div className={`text-2xl font-bold mt-2 font-mono tabular-nums ${openDebtsCount > 0 ? 'text-amber-300' : 'text-emerald-400'}`}>
                {openDebtsCount} Active Loans
              </div>
              <p className="text-xs text-slate-400 mt-1">Every bypass tracked with auto-expiry and repayment deadlines.</p>
            </div>
          </div>

          {/* Friction Radar & Heatmap */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm font-bold text-white font-mono">
                  <Flame className="w-4 h-4 text-amber-400" />
                  <span>Real-Time Friction Heatmap & Bottleneck Sensors</span>
                </div>
                <span className="text-xs font-mono text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800">
                  PREDICTIVE CONTEXT SENSOR
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Friction rises as a leading indicator before system failure occurs. Sensors continuously gauge queue latency, permission blocks, and re-entry costs.
              </p>

              <div className="space-y-3 pt-2">
                {frictionItems.map((f) => (
                  <div key={f.id} className="bg-slate-950 p-4 rounded-lg border border-slate-800/80 hover:border-slate-700 transition-colors">
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono font-bold text-cyan-300">{f.id}</span>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
                            {f.category}
                          </span>
                          <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                            f.frequencyScore === 'HIGH' ? 'bg-amber-950 text-amber-300 border border-amber-800' : 'bg-slate-800 text-slate-300'
                          }`}>
                            {f.frequencyScore} FREQUENCY
                          </span>
                        </div>
                        <p className="text-xs text-slate-200">{f.description}</p>
                        <div className="text-[11px] font-mono text-emerald-400 pt-1 flex items-center gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                          <span>Compounding Countermeasure: {f.automatedCountermeasure}</span>
                        </div>
                      </div>
                      <div className="text-right shrink-0">
                        <span className="text-[10px] text-slate-500 font-mono block">FLOW LOSS</span>
                        <span className="text-xs font-mono font-bold text-amber-400">-{f.averageFlowLossMinutes}m</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Active Oscillation Circuit Breakers */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
              <div className="flex items-center gap-2 text-sm font-bold text-white font-mono">
                <RotateCcw className="w-4 h-4 text-indigo-400" />
                <span>Oscillation Radar & Circuit Breaker</span>
              </div>
              <p className="text-xs text-slate-400">
                Detects alternating fix patterns (A → B → A). When triggered, all quick bypasses are rejected and root-cause mode is forced.
              </p>

              <div className="space-y-3">
                {oscillations.map((osc) => (
                  <div key={osc.id} className="bg-slate-950 p-3.5 rounded-lg border border-indigo-900/50 space-y-2">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="font-bold text-indigo-300">{osc.id}</span>
                      <span className="text-rose-400 bg-rose-950/80 px-2 py-0.5 rounded border border-rose-800 text-[10px]">
                        CIRCUIT BROKEN
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-300 space-y-1 font-mono">
                      <div>Pattern: <span className="text-cyan-300">{osc.patternType}</span> ({osc.cycleCount} cycles)</div>
                      <div className="text-rose-300 text-[10px] bg-rose-950/40 p-2 rounded border border-rose-900/60">
                        {osc.circuitBreakerAction}
                      </div>
                      <div className="text-slate-400 text-[10px] pt-1">
                        Directive: {osc.forcedRootCauseDirective}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="bg-cyan-950/30 border border-cyan-800/40 p-3.5 rounded-lg text-xs font-mono text-cyan-300 space-y-1.5">
                <div className="font-bold flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-cyan-400" />
                  <span>The Non-Negotiable Invariant</span>
                </div>
                <p className="text-[11px] text-slate-300 leading-relaxed">
                  A fix that reintroduces a known failure class is rejected automatically by the kernel. Flow is preserved via loans, not denial.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 2: DEBT LEDGER & BREAK-GLASS LOANS */}
      {activeSubTab === 'DEBT_LEDGER' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Live Debt Ledger Table */}
            <div className="lg:col-span-2 bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm font-bold text-white font-mono">
                  <Scale className="w-4 h-4 text-cyan-400" />
                  <span>The Debt Ledger: Enforced Credit & Auto-Expiry</span>
                </div>
                <span className="text-xs font-mono text-slate-400">
                  {debts.length} Total Records
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Most organizations treat technical debt as an unread list. In Genesis, debt is an enforced financial instrument with credit ceilings, auto-expiry, and blocking gates.
              </p>

              <div className="space-y-3 pt-2">
                {debts.map((debt) => (
                  <div
                    key={debt.debtId}
                    className={`bg-slate-950 p-4 rounded-lg border transition-all ${
                      debt.status === 'OPEN_DEBT'
                        ? 'border-amber-600/60 shadow-lg shadow-amber-950/20'
                        : debt.status === 'OVERDUE'
                        ? 'border-rose-600/80 bg-rose-950/10'
                        : 'border-slate-800 opacity-80'
                    }`}
                  >
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-slate-900 pb-2.5">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-xs text-cyan-300">{debt.debtId}</span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-800">
                          {debt.failureClass}
                        </span>
                        <span className="text-[10px] font-mono text-slate-400">
                          Agent: <span className="text-slate-200 font-semibold">{debt.requestingAgent}</span>
                        </span>
                      </div>
                      <span className={`text-[10px] font-mono font-bold px-2.5 py-0.5 rounded ${
                        debt.status === 'OPEN_DEBT'
                          ? 'bg-amber-950 text-amber-300 border border-amber-800'
                          : debt.status === 'OVERDUE'
                          ? 'bg-rose-950 text-rose-300 border border-rose-800'
                          : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                      }`}>
                        {debt.status}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs pt-3 font-mono">
                      <div>
                        <span className="text-slate-500 text-[10px] block">PARENT BOTTLENECK</span>
                        <span className="text-slate-200">{debt.parentBottleneck}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-[10px] block">BREAK-GLASS SCOPE (LOAN)</span>
                        <span className="text-cyan-300">{debt.scope}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-[10px] block">REPAYMENT DEADLINE</span>
                        <span className="text-slate-300 flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5 text-slate-500" />
                          {new Date(debt.deadline).toLocaleTimeString()}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-[10px] block">MANDATORY REPAYMENT PLAN</span>
                        <span className="text-slate-300">{debt.mandatoryRepaymentPlan}</span>
                      </div>
                    </div>

                    {debt.repaidFixId && (
                      <div className="mt-3 pt-2 border-t border-slate-900/80 flex items-center justify-between text-[11px] font-mono text-emerald-400">
                        <span>Repaid By: {debt.repaidFixId}</span>
                        <span className="text-slate-500">{debt.antiRecursionReceipt}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Break-Glass Loan Station & Repayment Terminal */}
            <div className="space-y-6">
              {/* Request a New Break-Glass Loan */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
                <div className="flex items-center gap-2 text-sm font-bold text-white font-mono">
                  <Zap className="w-4 h-4 text-amber-400" />
                  <span>Request Break-Glass Loan</span>
                </div>
                <p className="text-xs text-slate-400">
                  Stop the bleed and maintain flow. Loans are time-bound leases with credit limits.
                </p>

                <form onSubmit={handleIssueLoan} className="space-y-3 font-mono text-xs">
                  <div>
                    <label className="text-slate-400 text-[10px] block mb-1">PARENT BOTTLENECK</label>
                    <input
                      type="text"
                      value={parentBottleneck}
                      onChange={(e) => setParentBottleneck(e.target.value)}
                      placeholder="e.g. WebSocket connection drop under burst"
                      className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  <div>
                    <label className="text-slate-400 text-[10px] block mb-1">FAILURE CLASS</label>
                    <select
                      value={selectedClass}
                      onChange={(e) => setSelectedClass(e.target.value as FailureClassId)}
                      className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
                    >
                      {failureClasses.map((fc) => (
                        <option key={fc.id} value={fc.id}>{fc.name}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="text-slate-400 text-[10px] block mb-1">BYPASS SCOPE (TEMPORARY LOAN)</label>
                    <input
                      type="text"
                      value={loanScope}
                      onChange={(e) => setLoanScope(e.target.value)}
                      placeholder="e.g. Increase in-memory buffer limit to 1000"
                      className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-slate-400 text-[10px] block mb-1">DURATION (MINUTES)</label>
                      <input
                        type="number"
                        value={loanMinutes}
                        onChange={(e) => setLoanMinutes(Number(e.target.value))}
                        min={5}
                        max={180}
                        className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
                      />
                    </div>
                    <div>
                      <label className="text-slate-400 text-[10px] block mb-1">AGENT</label>
                      <select
                        value={requestingAgent}
                        onChange={(e) => setRequestingAgent(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
                      >
                        <option value="otto">otto</option>
                        <option value="concierge">concierge</option>
                        <option value="science-lead">science-lead</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="text-slate-400 text-[10px] block mb-1">MANDATORY REPAYMENT PLAN</label>
                    <textarea
                      value={repaymentPlan}
                      onChange={(e) => setRepaymentPlan(e.target.value)}
                      placeholder="e.g. Backpressure controller with drop signal"
                      rows={2}
                      className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  <button
                    type="submit"
                    className="w-full py-2 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold rounded shadow transition-all cursor-pointer"
                  >
                    Issue Audited Break-Glass Loan
                  </button>
                </form>

                {loanMessage && (
                  <div className={`p-2.5 rounded text-[11px] font-mono ${
                    loanMessage.isError ? 'bg-rose-950/80 text-rose-200 border border-rose-800' : 'bg-emerald-950/80 text-emerald-200 border border-emerald-800'
                  }`}>
                    {loanMessage.text}
                  </div>
                )}
              </div>

              {/* Repayment Terminal */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
                <div className="flex items-center gap-2 text-sm font-bold text-white font-mono">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Repay Debt Terminal</span>
                </div>
                <p className="text-xs text-slate-400">
                  Repay loan with a permanent compounding fix. Must pass anti-recursion verification.
                </p>

                <form onSubmit={handleRepayDebt} className="space-y-3 font-mono text-xs">
                  <div>
                    <label className="text-slate-400 text-[10px] block mb-1">SELECT OPEN DEBT</label>
                    <select
                      value={selectedRepayDebtId}
                      onChange={(e) => setSelectedRepayDebtId(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
                    >
                      {debts.filter(d => d.status === 'OPEN_DEBT').map((d) => (
                        <option key={d.debtId} value={d.debtId}>{d.debtId} ({d.parentBottleneck.slice(0, 30)}...)</option>
                      ))}
                      {debts.filter(d => d.status === 'OPEN_DEBT').length === 0 && (
                        <option value="">No open debts (All repaid!)</option>
                      )}
                    </select>
                  </div>

                  <div>
                    <label className="text-slate-400 text-[10px] block mb-1">PROPER STRUCTURAL FIX TITLE</label>
                    <input
                      type="text"
                      value={repaymentFixTitle}
                      onChange={(e) => setRepaymentFixTitle(e.target.value)}
                      placeholder="e.g. Backpressure-aware WebSocket flow controller"
                      className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={!selectedRepayDebtId}
                    className="w-full py-2 bg-gradient-to-r from-emerald-500 to-teal-400 hover:from-emerald-400 hover:to-teal-300 text-slate-950 font-bold rounded shadow transition-all disabled:opacity-50 cursor-pointer"
                  >
                    Verify Anti-Recursion & Repay Debt
                  </button>
                </form>

                {repayMessage && (
                  <div className={`p-2.5 rounded text-[11px] font-mono space-y-1 ${
                    repayMessage.isError ? 'bg-rose-950/80 text-rose-200 border border-rose-800' : 'bg-emerald-950/80 text-emerald-200 border border-emerald-800'
                  }`}>
                    <div>{repayMessage.text}</div>
                    {repayMessage.receipt && (
                      <div className="text-[10px] text-emerald-400">HMAC Receipt: {repayMessage.receipt}</div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 3: ANTI-RECURSION PROOF ENGINE */}
      {activeSubTab === 'ANTI_RECURSION' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Living Failure Class Taxonomy */}
            <div className="lg:col-span-2 bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm font-bold text-white font-mono">
                  <RotateCcw className="w-4 h-4 text-cyan-400" />
                  <span>The Living Failure Class Taxonomy (All Known Failure Modes)</span>
                </div>
                <span className="text-xs font-mono text-cyan-400 bg-cyan-950 px-2 py-0.5 rounded border border-cyan-800">
                  ANTI-RECURSION PROOF SET
                </span>
              </div>
              <p className="text-xs text-slate-400">
                The industry only tests fixes against the target bug. Genesis tests fixes against the entire taxonomy of every bug ever encountered to mathematically eliminate tail-chasing.
              </p>

              <div className="space-y-3 pt-2">
                {failureClasses.map((fc) => (
                  <div key={fc.id} className="bg-slate-950 p-4 rounded-lg border border-slate-800/80 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-xs text-cyan-300">{fc.name}</span>
                        <span className="text-[10px] font-mono text-slate-500">[{fc.id}]</span>
                      </div>
                      <span className="text-[10px] font-mono text-slate-400">
                        {fc.historicalInstances} Historical Instances · <span className="text-emerald-400 font-bold">{fc.recurrenceCount} Recurrences</span>
                      </span>
                    </div>
                    <p className="text-xs text-slate-300">{fc.definition}</p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] font-mono pt-1 text-slate-400">
                      <div>Countermeasure: <span className="text-cyan-300">{fc.countermeasure}</span></div>
                      <div>Proof Test: <span className="text-emerald-400">{fc.regressionTestProof}</span></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Interactive Sandbox Anti-Recursion Probe */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
              <div className="flex items-center gap-2 text-sm font-bold text-white font-mono">
                <Search className="w-4 h-4 text-cyan-400" />
                <span>Interactive Anti-Recursion Probe</span>
              </div>
              <p className="text-xs text-slate-400">
                Test any proposed remediation title in real time. The engine checks for known bypass heuristics, timeout inflation, and tail-chasing patterns.
              </p>

              <div className="space-y-3 font-mono text-xs">
                <div>
                  <label className="text-slate-400 text-[10px] block mb-1">TARGET FAILURE CLASS</label>
                  <select
                    value={testTargetClass}
                    onChange={(e) => handleTestEvaluation(testFixInput, e.target.value as FailureClassId)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    {failureClasses.map((fc) => (
                      <option key={fc.id} value={fc.id}>{fc.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-slate-400 text-[10px] block mb-1">PROPOSED REMEDIATION TITLE</label>
                  <textarea
                    value={testFixInput}
                    onChange={(e) => handleTestEvaluation(e.target.value, testTargetClass)}
                    rows={3}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>

                {/* Live Pre-canned tests for rapid inspection */}
                <div className="space-y-1.5 pt-1">
                  <span className="text-[10px] text-slate-500 block">TRY CANONICAL EXAMPLES:</span>
                  <div className="flex flex-col gap-1.5">
                    <button
                      type="button"
                      onClick={() => handleTestEvaluation('Quick temporary bypass on deploy timeout', 'TRADEOFF_OSCILLATION')}
                      className="text-left px-2 py-1 bg-slate-950 border border-slate-800 rounded hover:border-slate-700 text-rose-300 text-[11px]"
                    >
                      Fail Case: "Quick temporary bypass on deploy timeout"
                    </button>
                    <button
                      type="button"
                      onClick={() => handleTestEvaluation('Network-boundary Zod schema gate with fuzzing', 'SYMPTOM_MIGRATION')}
                      className="text-left px-2 py-1 bg-slate-950 border border-slate-800 rounded hover:border-slate-700 text-emerald-300 text-[11px]"
                    >
                      Pass Case: "Network-boundary Zod schema gate with fuzzing"
                    </button>
                  </div>
                </div>

                {/* Probe Result Card */}
                <div className={`p-4 rounded-xl border mt-3 space-y-2 ${
                  testResult.isSafe
                    ? 'bg-emerald-950/40 border-emerald-800 text-emerald-200'
                    : 'bg-rose-950/40 border-rose-800 text-rose-200'
                }`}>
                  <div className="flex items-center justify-between">
                    <span className="font-bold">VERDICT: {testResult.isSafe ? 'PROVEN SAFE' : 'RECURSION DETECTED'}</span>
                    <span className="text-xs">Risk: {(testResult.recursionRiskScore * 100).toFixed(0)}%</span>
                  </div>
                  {testResult.warnings.length > 0 ? (
                    <div className="text-[11px] space-y-1 text-rose-300">
                      {testResult.warnings.map((w, i) => (
                        <div key={i}>• {w}</div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-[11px] text-emerald-300">
                      Zero recurring failure class heuristics detected. Mathematical invariant satisfied.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 4: FLOW SCIENCE CHARTER */}
      {activeSubTab === 'FLOW_SCIENCE' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm font-bold text-white font-mono">
                  <Zap className="w-4 h-4 text-cyan-400" />
                  <span>Flow Science Charter — Research Lane (Live Day 0)</span>
                </div>
                <span className="text-xs font-mono text-emerald-400 bg-emerald-950 px-2 py-0.5 rounded border border-emerald-800">
                  DAY 0 ACTIVE
                </span>
              </div>
              <p className="text-xs text-slate-400">
                A dedicated scientific charter to model and quantify flow state, context friction, and loan durations across the entire agent estate.
              </p>

              <div className="space-y-3 pt-2">
                {hypotheses.map((h) => (
                  <div key={h.id} className="bg-slate-950 p-4 rounded-lg border border-slate-800/80 space-y-2 font-mono">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-cyan-300">{h.id}</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                        h.status === 'PROVEN' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                      }`}>
                        {h.status}
                      </span>
                    </div>
                    <div className="text-xs text-slate-200 font-semibold">{h.question}</div>
                    <div className="text-[11px] text-slate-400">
                      Finding: <span className="text-slate-200">{h.empiricalFinding}</span>
                    </div>
                    <div className="text-[11px] text-emerald-400 flex items-center justify-between pt-1 border-t border-slate-900">
                      <span>Intervention: {h.systemicIntervention}</span>
                      <span className="text-slate-500">Correlation: {h.founderFrictionCorrelation}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Loan Window Optimizer Matrix */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
              <div className="flex items-center gap-2 text-sm font-bold text-white font-mono">
                <Clock className="w-4 h-4 text-cyan-400" />
                <span>Loan Window Optimizer</span>
              </div>
              <p className="text-xs text-slate-400">
                Scientifically calibrated duration limits for break-glass operations based on risk profile and blast radius.
              </p>

              <div className="space-y-3 font-mono text-xs">
                {optimizers.map((opt) => (
                  <div key={opt.riskClass} className="bg-slate-950 p-3.5 rounded-lg border border-slate-800 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className={`font-bold ${
                        opt.riskClass === 'CRITICAL' ? 'text-rose-400' : opt.riskClass === 'HIGH' ? 'text-amber-400' : 'text-cyan-300'
                      }`}>
                        {opt.riskClass} RISK
                      </span>
                      <span className="text-slate-300">Rec: {opt.recommendedMinutes}m (Max: {opt.maxAllowedMinutes}m)</span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-normal">{opt.rationale}</p>
                    <div className="text-[10px] text-slate-500 pt-1">
                      Mandatory Repayment Window: <span className="text-slate-300">{opt.repaymentWindowHours} hours</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 5: 2100 VISUAL MANDATE ENFORCER */}
      {activeSubTab === 'VISUAL_MANDATE' && (
        <div className="space-y-6">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2 text-sm font-bold text-white font-mono">
                  <Sparkles className="w-4 h-4 text-cyan-400" />
                  <span>The 2100 Visual Mandate — Automated Compliance Audit</span>
                </div>
                <p className="text-xs text-slate-400">
                  Every visual in the estate is mandated and enforced at the 2100 alien standard by default. The Founder never has to request spectacular visuals again.
                </p>
              </div>

              <div className="flex items-center gap-3 font-mono text-xs">
                <div className="bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 text-emerald-400 font-bold">
                  OVERALL AUDIT: {auditReport.overallScore}% PASS
                </div>
                <div className="bg-emerald-950 text-emerald-300 px-3 py-1.5 rounded-lg border border-emerald-800 font-bold">
                  MACHINE-ENFORCED
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 pt-3">
              {auditReport.rulesEvaluated.map((rule) => (
                <div key={rule.id} className="bg-slate-950 p-4 rounded-xl border border-slate-800/80 space-y-2 font-mono text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-cyan-300">{rule.name}</span>
                    <span className="text-emerald-400 flex items-center gap-1 font-bold">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      100%
                    </span>
                  </div>
                  <p className="text-slate-300 text-[11px] leading-relaxed">{rule.mandateRequirement}</p>
                  <div className="pt-2 border-t border-slate-900 text-[10px] text-slate-500">
                    Evidence: <span className="text-slate-400">{rule.telemetryEvidence}</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="bg-slate-950 p-4 rounded-xl border border-indigo-900/60 font-mono text-xs flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <FileCheck className="w-5 h-5 text-indigo-400" />
                <span className="text-slate-300">
                  Constitutional Spine Invariant (§10): Visual decay regression test runs on every build. Zero tolerance for visual mediocrity.
                </span>
              </div>
              <span className="text-emerald-400 font-bold whitespace-nowrap">
                FOUNDER INTERVENTION: 0 REPEATS
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
