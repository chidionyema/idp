/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import {
  KeyLoanLease,
  FailureClass,
  BreakGlassDebtEntry,
  INITIAL_KEY_LOANS,
  INITIAL_FAILURE_CLASSES,
  INITIAL_DEBT_LEDGER,
  verifyAntiRecursionProof,
  FailureClassId,
} from '../lib/protocolEngine.ts';
import {
  Key,
  Lock,
  Unlock,
  ShieldCheck,
  AlertTriangle,
  Clock,
  Send,
  CheckCircle2,
  XCircle,
  RotateCcw,
  RefreshCw,
  Terminal,
  Zap,
} from 'lucide-react';

export const KeyLoanAndGuardrailSurface: React.FC = () => {
  const [leases, setLeases] = useState<KeyLoanLease[]>(INITIAL_KEY_LOANS);
  const [debtLedger, setDebtLedger] = useState<BreakGlassDebtEntry[]>(INITIAL_DEBT_LEDGER);
  const [failureClasses] = useState<FailureClass[]>(INITIAL_FAILURE_CLASSES);
  const [testFixTitle, setTestFixTitle] = useState<string>('Quick temporary bypass on deploy timeout');
  const [targetClass, setTargetClass] = useState<FailureClassId>('TRADEOFF_OSCILLATION');
  const [showTelegramMock, setShowTelegramMock] = useState<boolean>(true);

  // Countdown timer for active leases
  useEffect(() => {
    const timer = setInterval(() => {
      setLeases((prev) =>
        prev.map((l) => {
          if (l.approvalStatus === 'ACTIVE_LEASE' && l.remainingSeconds > 0) {
            return {
              ...l,
              remainingSeconds: l.remainingSeconds - 1,
            };
          }
          return l;
        })
      );
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const handleRevokeLease = (leaseId: string) => {
    setLeases((prev) =>
      prev.map((l) => (l.leaseId === leaseId ? { ...l, approvalStatus: 'REVOKED', remainingSeconds: 0 } : l))
    );
  };

  const handleReturnAndLock = (leaseId: string) => {
    setLeases((prev) =>
      prev.map((l) =>
        l.leaseId === leaseId
          ? {
              ...l,
              approvalStatus: 'LOCKED_AND_RETURNED',
              remainingSeconds: 0,
              lockProofReceipt: `LOCK-ACK-${Math.floor(1000 + Math.random() * 9000)}-OK`,
            }
          : l
      )
    );
  };

  const antiRecursionResult = verifyAntiRecursionProof(testFixTitle, targetClass);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 sm:p-8">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-mono text-cyan-400">
              <Key className="w-4 h-4 text-cyan-400" />
              <span>KEY LOAN PROTOCOL (KLP) & ANTI-RECURSION ENGINE</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              Guardrail Mastery & Key Loan Protocol
            </h1>
            <p className="text-slate-400 text-sm max-w-2xl">
              Eliminates the IDP history failure class where agents build guardrails and never hand back control. Founder holds root keys; all access is a time-bound lease. The engine blocks tail-chasing remediation loops.
            </p>
          </div>

          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs font-mono space-y-1.5 shrink-0 min-w-[260px]">
            <div className="text-slate-500 uppercase tracking-wider text-[10px]">Zero Standing Access Canon</div>
            <div className="flex justify-between items-center text-slate-200">
              <span>Standing Agent Keys:</span>
              <span className="text-emerald-400 font-bold tabular-nums">0 (Strictly Banned)</span>
            </div>
            <div className="flex justify-between items-center text-slate-200">
              <span>Active Leases:</span>
              <span className="text-cyan-400 font-bold tabular-nums">
                {leases.filter((l) => l.approvalStatus === 'ACTIVE_LEASE').length} Leases Open
              </span>
            </div>
            <div className="flex justify-between items-center text-slate-200">
              <span>Auto-Revoke Rate:</span>
              <span className="text-emerald-400 font-bold tabular-nums">100% Enforced</span>
            </div>
          </div>
        </div>
      </div>

      {/* Five Laws of KLP Banner */}
      <div className="bg-slate-950 p-4 sm:p-5 rounded-xl border border-slate-800 space-y-2">
        <div className="text-xs font-mono font-bold text-cyan-400 uppercase tracking-wider">
          The Five Inviolable Laws of Key Loans (§KLP)
        </div>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3 text-xs font-mono text-slate-300">
          <div className="p-2.5 bg-slate-900 rounded border border-slate-800/80">
            <span className="text-cyan-400 font-bold block text-[10px]">LAW 1: ROOT SOVEREIGNTY</span>
            Founder owns root keys. Agents hold zero standing keys.
          </div>
          <div className="p-2.5 bg-slate-900 rounded border border-slate-800/80">
            <span className="text-cyan-400 font-bold block text-[10px]">LAW 2: ALL ACCESS IS LEASE</span>
            Time-bound, purpose-bound, scope-bound, auto-revoked.
          </div>
          <div className="p-2.5 bg-slate-900 rounded border border-slate-800/80">
            <span className="text-cyan-400 font-bold block text-[10px]">LAW 3: BUILD, LOCK, RETURN</span>
            Agent locks gate and returns keys upon completion.
          </div>
          <div className="p-2.5 bg-slate-900 rounded border border-slate-800/80">
            <span className="text-cyan-400 font-bold block text-[10px]">LAW 4: DETERMINISTIC DEFAULT</span>
            Policy engine auto-approves low-risk; Founder on exceptions.
          </div>
          <div className="p-2.5 bg-slate-900 rounded border border-slate-800/80">
            <span className="text-cyan-400 font-bold block text-[10px]">LAW 5: ESTATE-OWNED</span>
            Every guardrail is code in git, tested and monitored.
          </div>
        </div>
      </div>

      {/* Active Leases Ledger */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Clock className="w-5 h-5 text-cyan-400" />
            <span>Active Key Leases & Temporary Guardrail Grants</span>
          </h2>
          <span className="text-xs font-mono text-slate-400">
            Definition of Done Requires: Lock Gate & Return Keys
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {leases.map((lease) => {
            const isActive = lease.approvalStatus === 'ACTIVE_LEASE';
            const isLocked = lease.approvalStatus === 'LOCKED_AND_RETURNED';
            const isRevoked = lease.approvalStatus === 'REVOKED';

            return (
              <div
                key={lease.leaseId}
                className={`p-5 rounded-xl border transition-all space-y-3 ${
                  isActive
                    ? 'bg-slate-900/90 border-cyan-500/80 shadow-md'
                    : isLocked
                    ? 'bg-slate-950/70 border-emerald-800/60 opacity-80'
                    : 'bg-slate-950/70 border-rose-950 opacity-60'
                }`}
              >
                <div className="flex justify-between items-center">
                  <span className="text-xs font-mono font-bold text-white">{lease.leaseId}</span>
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                    isActive
                      ? 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                      : isLocked
                      ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                      : 'bg-rose-950 text-rose-300 border border-rose-800'
                  }`}>
                    {lease.approvalStatus.replace('_', ' ')}
                  </span>
                </div>

                <div className="text-xs text-slate-300 font-medium">
                  Surface: <strong className="text-white">{lease.surface}</strong>
                </div>
                <div className="text-[11px] text-slate-400 line-clamp-2">{lease.purpose}</div>

                <div className="text-xs font-mono pt-2 border-t border-slate-800 space-y-1">
                  <div className="flex justify-between text-slate-400">
                    <span>Agent: <strong className="text-slate-200">{lease.agentId}</strong></span>
                    <span>Risk: <strong className="text-amber-400">{lease.riskClass}</strong></span>
                  </div>

                  {isActive && (
                    <div className="flex justify-between text-emerald-400 font-bold">
                      <span>Lease Countdown:</span>
                      <span className="tabular-nums">
                        {Math.floor(lease.remainingSeconds / 60)}m {lease.remainingSeconds % 60}s
                      </span>
                    </div>
                  )}

                  {isLocked && lease.lockProofReceipt && (
                    <div className="text-[10px] text-emerald-400 flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" />
                      <span>Locked & Key Returned: {lease.lockProofReceipt}</span>
                    </div>
                  )}
                </div>

                {/* Action buttons */}
                {isActive && (
                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={() => handleReturnAndLock(lease.leaseId)}
                      className="flex-1 py-1.5 px-2 bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-semibold rounded-lg transition-colors cursor-pointer"
                    >
                      Lock & Return Key
                    </button>
                    <button
                      onClick={() => handleRevokeLease(lease.leaseId)}
                      className="py-1.5 px-3 bg-rose-950 hover:bg-rose-900 text-rose-300 border border-rose-800 text-xs font-semibold rounded-lg transition-colors cursor-pointer"
                    >
                      Revoke
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Multi-Surface Telegram Notification Preview Banner */}
      {showTelegramMock && (
        <div className="bg-slate-950 p-4 sm:p-5 rounded-xl border border-sky-800/80 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-900 pb-2">
            <div className="flex items-center gap-2 text-xs font-mono font-bold text-sky-400">
              <Send className="w-4 h-4 text-sky-400" />
              <span>TELEGRAM FOUNDER SURFACE · ONE-TAP LEASE GRANT NOTIFICATION</span>
            </div>
            <button
              onClick={() => setShowTelegramMock(false)}
              className="text-xs text-slate-500 hover:text-slate-300"
            >
              Dismiss Preview
            </button>
          </div>

          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="text-xs font-mono text-slate-300 space-y-1">
              <div>
                <strong>[KLP-GRANT-REQUEST]</strong> Agent <code className="text-cyan-300">otto</code> requests temporary 30-min lease on <code className="text-amber-300">DEPLOY_GATES</code>.
              </div>
              <div className="text-slate-400 text-[11px]">
                Purpose: Deploy verified firestore.rules and sealed v1.0.26 release. Risk: MEDIUM.
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => alert('Simulated Telegram One-Tap: Grant Confirmed in <1.2s')}
                className="px-4 py-1.5 text-xs font-bold text-slate-950 bg-sky-400 hover:bg-sky-300 rounded-lg cursor-pointer"
              >
                Approve (One-Tap)
              </button>
              <button
                onClick={() => alert('Simulated Telegram One-Tap: Lease Denied')}
                className="px-3 py-1.5 text-xs font-medium text-rose-300 bg-rose-950 hover:bg-rose-900 rounded-lg border border-rose-800 cursor-pointer"
              >
                Deny
              </button>
            </div>
          </div>
        </div>
      )}

      {/* The Recursive Remediation Trap & Anti-Recursion Engine */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left: Anti-Recursion Proof Simulator (6 cols) */}
        <div className="lg:col-span-6 bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-5">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <div className="text-xs font-mono text-cyan-400">ANTI-RECURSION PROOF ENGINE</div>
              <h3 className="text-base font-bold text-white">Prove Fix Does Not Recreate the Disease</h3>
            </div>
            <ShieldCheck className="w-5 h-5 text-cyan-400" />
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1">Proposed Fix Description:</label>
              <input
                type="text"
                value={testFixTitle}
                onChange={(e) => setTestFixTitle(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-cyan-200 font-mono focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1">Target Historical Failure Class:</label>
              <select
                value={targetClass}
                onChange={(e) => setTargetClass(e.target.value as FailureClassId)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500 cursor-pointer"
              >
                {failureClasses.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name} ({f.historicalInstances} historical instances)
                  </option>
                ))}
              </select>
            </div>

            {/* Test result card */}
            <div className={`p-4 rounded-xl border ${
              antiRecursionResult.isSafe
                ? 'bg-emerald-950/30 border-emerald-800'
                : 'bg-rose-950/30 border-rose-800'
            }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {antiRecursionResult.isSafe ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  ) : (
                    <XCircle className="w-5 h-5 text-rose-400" />
                  )}
                  <span className={`text-xs font-mono font-bold ${
                    antiRecursionResult.isSafe ? 'text-emerald-300' : 'text-rose-300'
                  }`}>
                    {antiRecursionResult.isSafe ? 'PROOF VALIDATED: SAFE COMPRESSION' : 'RECURSION TRAP DETECTED: BLOCKED'}
                  </span>
                </div>
                <span className="text-xs font-mono font-bold text-slate-400">
                  Risk: {antiRecursionResult.recursionRiskScore.toFixed(2)}
                </span>
              </div>

              {antiRecursionResult.warnings.length > 0 && (
                <div className="mt-2 text-xs font-mono text-rose-300 space-y-1">
                  {antiRecursionResult.warnings.map((w, idx) => (
                    <div key={idx}>• {w}</div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right: Break-Glass Debt Ledger (6 cols) */}
        <div className="lg:col-span-6 bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-5">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <div className="text-xs font-mono text-cyan-400">BREAK-GLASS DEBT LEDGER</div>
              <h3 className="text-base font-bold text-white">Bypasses Are Loans, Never Fixes</h3>
            </div>
            <span className="text-xs font-mono text-emerald-400">Credit Limit: 2 Max</span>
          </div>

          <div className="space-y-3">
            {debtLedger.map((debt) => (
              <div
                key={debt.debtId}
                className="p-3.5 bg-slate-950 rounded-xl border border-slate-800 space-y-2 text-xs font-mono"
              >
                <div className="flex justify-between items-center">
                  <span className="font-bold text-white">{debt.debtId}</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                    debt.status === 'REPAID'
                      ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                      : 'bg-amber-950 text-amber-300 border border-amber-800'
                  }`}>
                    {debt.status}
                  </span>
                </div>

                <div className="text-slate-300 font-sans text-xs">
                  <strong>Scope:</strong> {debt.scope}
                </div>

                <div className="text-slate-400 text-[11px]">
                  <strong>Mandatory Repayment:</strong> {debt.mandatoryRepaymentPlan}
                </div>

                <div className="flex justify-between text-slate-500 text-[10px] pt-1 border-t border-slate-900">
                  <span>Class: {debt.failureClass}</span>
                  <span>Agent: {debt.requestingAgent}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
};
