import { useState } from 'react';
import {
  CheckCircle2,
  Compass,
  Lock,
  Play,
  ShieldAlert,
  Terminal,
} from 'lucide-react';
import type {
  DefectLockoutState,
  DefectRingSection,
  I8095LockdownSnapshot,
  ZeroPollCheckResult,
} from '../engine/i8095Lockdown';

interface I8095LockdownPanelProps {
  i8095: I8095LockdownSnapshot;
  onFocusNode: (nodeId: string) => void;
  onRunClassASweep: () => Promise<void>;
  runningSweep: boolean;
}

type RingFilter = 'ALL' | DefectRingSection;

function lockoutBadgeClass(state: DefectLockoutState) {
  if (state === 'ENFORCED_SANDBOX') {
    return 'text-emerald-700 border-emerald-200 bg-emerald-50';
  }
  if (state === 'QUARANTINED') {
    return 'text-sky-700 border-sky-200 bg-sky-50';
  }
  if (state === 'NOT_IMPLEMENTED_EXPLICIT') {
    return 'text-slate-700 border-slate-200 bg-slate-100';
  }
  return 'text-amber-800 border-amber-200 bg-amber-50';
}

function severityClass(sev: string) {
  if (sev === 'P0 Critical') return 'text-red-700 font-semibold';
  if (sev === 'P1 High') return 'text-amber-700 font-semibold';
  return 'text-slate-600 font-medium';
}

export function I8095LockdownPanel({
  i8095,
  onFocusNode,
  onRunClassASweep,
  runningSweep,
}: I8095LockdownPanelProps) {
  const [ringFilter, setRingFilter] = useState<RingFilter>('ALL');
  const [snippet, setSnippet] = useState<string>(
    'while true; do\n  sleep 3\n  gh pr view 8164 --json mergeStateStatus\ndone'
  );
  const [guardResult, setGuardResult] = useState<ZeroPollCheckResult | null>(null);
  const [checkingGuard, setCheckingGuard] = useState(false);

  const filteredDefects = i8095.defects.filter((d) =>
    ringFilter === 'ALL' ? true : d.ringSection === ringFilter
  );

  async function runZeroPollCheck(codeToTest: string) {
    setCheckingGuard(true);
    try {
      const res = await fetch('/api/i8095/test-zero-poll', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: codeToTest }),
      });
      if (res.ok) {
        const data = (await res.json()) as ZeroPollCheckResult;
        setGuardResult(data);
      }
    } finally {
      setCheckingGuard(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header & NASA Class-A 5 Mechanical Properties */}
      <section className="bg-white border border-slate-200 rounded-lg p-5">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono">
              <span className="font-semibold text-blue-700">{i8095.instructionId}</span>
              <span className="text-slate-400">&middot;</span>
              <span className="font-semibold text-emerald-700">{i8095.targetAvailability}</span>
              <span className="text-slate-400">&middot;</span>
              <span className="text-slate-600">{i8095.issueClassEntry.issueClassId}</span>
            </div>
            <h3 className="mt-1 text-base font-semibold text-slate-900">
              {i8095.standardTitle}
            </h3>
            <p className="mt-1 text-xs text-slate-600">
              Maps all 17 defect classes (D-01 through D-17) across Geburah Rings 0–3 &amp; Infrastructure Lanes 1–3. Sandbox mechanical guards fail closed automatically; external private repo remediations remain explicitly flagged as EXTERNAL_REPO_PENDING.
            </p>
          </div>

          <button
            type="button"
            disabled={runningSweep}
            onClick={onRunClassASweep}
            className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-xs font-medium text-white hover:bg-blue-700 whitespace-nowrap shrink-0 disabled:opacity-50"
          >
            <Play className="h-3.5 w-3.5" aria-hidden="true" />
            {runningSweep ? 'Running Sweep...' : 'Run Class-A Mechanical Sweep'}
          </button>
        </div>

        {/* Summary KPI Strip */}
        <div className="mt-4 pt-4 border-t border-slate-200 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs">
          <div>
            <div className="text-slate-500">Defects Mapped</div>
            <div className="mt-0.5 font-mono tabular-nums text-base font-semibold text-slate-900">
              {i8095.counts.totalDefects}
            </div>
          </div>
          <div>
            <div className="text-slate-500">P0 Critical</div>
            <div className="mt-0.5 font-mono tabular-nums text-base font-semibold text-red-700">
              {i8095.counts.p0Critical}
            </div>
          </div>
          <div>
            <div className="text-slate-500">P1 High / P2 Med</div>
            <div className="mt-0.5 font-mono tabular-nums text-base font-semibold text-amber-700">
              {i8095.counts.p1High} / {i8095.counts.p2Medium}
            </div>
          </div>
          <div>
            <div className="text-slate-500">Enforced / Isolated</div>
            <div className="mt-0.5 font-mono tabular-nums text-base font-semibold text-emerald-700">
              {i8095.counts.enforcedOrExplicit}
            </div>
          </div>
          <div>
            <div className="text-slate-500">External Repo Pending</div>
            <div className="mt-0.5 font-mono tabular-nums text-base font-semibold text-amber-700">
              {i8095.counts.externalRepoPending}
            </div>
          </div>
          <div>
            <div className="text-slate-500">BDD Scenarios (G1–G4)</div>
            <div className="mt-0.5 font-mono tabular-nums text-base font-semibold text-emerald-700">
              {i8095.counts.bddPassed} / 4 PASS
            </div>
          </div>
        </div>

        {/* 5 NASA Class-A Non-Negotiable Mechanical Properties */}
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-3">
          {i8095.nasaProperties.map((prop) => (
            <div
              key={prop.id}
              className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between gap-1 font-mono text-[10px] text-slate-500">
                  <span>{prop.standardRef}</span>
                  <span className="text-emerald-700 font-semibold">{prop.status}</span>
                </div>
                <div className="mt-1 font-semibold text-slate-900">{prop.name}</div>
                <p className="mt-1 text-slate-600 leading-snug">{prop.requirement}</p>
              </div>
              <div className="mt-2 pt-2 border-t border-slate-200 font-mono text-[11px] text-slate-800">
                {prop.mechanicalEnforcement}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Defect Matrix D-01 through D-17 */}
      <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="px-4 sm:px-5 py-4 border-b border-slate-200 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              Estate Defect &amp; One-Swoop Remediation Ledger (D-01–D-17)
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Click any row&apos;s node target to highlight and inspect its component directly in the Meridian Symphony constellation.
            </p>
          </div>

          <div className="flex flex-wrap gap-1.5 text-xs">
            {(
              [
                { id: 'ALL', label: `All (${i8095.defects.length})` },
                {
                  id: 'Ring 1 — Core Kernel, Router, Auth & Execution Spine',
                  label: 'Ring 1 Spine (D-01–06)',
                },
                {
                  id: 'Ring 1 & Lane 3 — CI/CD, Intake Gates, Polling & Fleet Control',
                  label: 'CI / Polling (D-07–12)',
                },
                {
                  id: 'Ring 0, Ring 2 & Ring 3 — Commercial Ventures, Investor Room & Ghost Specs',
                  label: 'Ventures / Ghost (D-13–17)',
                },
              ] as const
            ).map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setRingFilter(tab.id)}
                className={`rounded-md border px-2.5 py-1.5 font-mono text-[11px] ${
                  ringFilter === tab.id
                    ? 'border-slate-900 bg-slate-900 text-white'
                    : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                <th className="py-2.5 px-4 font-medium">ID &amp; Sev</th>
                <th className="py-2.5 px-4 font-medium">Component &amp; Defect</th>
                <th className="py-2.5 px-4 font-medium">One-Swoop Permanent Fix</th>
                <th className="py-2.5 px-4 font-medium">Lockout State</th>
                <th className="py-2.5 px-4 font-medium text-right">Graph Node</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {filteredDefects.map((d) => (
                <tr key={d.id} className="hover:bg-slate-50 align-top">
                  <td className="py-3 px-4 whitespace-nowrap">
                    <div className="font-mono font-bold text-slate-900">{d.id}</div>
                    <div className={`mt-0.5 text-[11px] ${severityClass(d.severity)}`}>
                      {d.severity}
                    </div>
                  </td>
                  <td className="py-3 px-4 min-w-[230px]">
                    <div className="font-mono text-[11px] font-semibold text-slate-800 break-words">
                      {d.componentAndFile}
                    </div>
                    <div className="mt-1 text-slate-600">{d.exactDefect}</div>
                  </td>
                  <td className="py-3 px-4 min-w-[230px]">
                    <div className="text-slate-900">{d.oneSwoopFix}</div>
                    <div className="mt-1 font-mono text-[11px] text-slate-500">
                      Bound: {d.boundScenario}
                    </div>
                  </td>
                  <td className="py-3 px-4 whitespace-nowrap">
                    <span
                      className={`inline-block rounded border px-2 py-0.5 font-mono text-[10px] font-semibold ${lockoutBadgeClass(
                        d.lockoutState
                      )}`}
                    >
                      {d.lockoutState}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right whitespace-nowrap">
                    <button
                      type="button"
                      onClick={() => onFocusNode(d.linkedNodeId)}
                      className="inline-flex items-center gap-1 rounded border border-slate-300 bg-white px-2.5 py-1 font-mono text-[11px] text-blue-700 hover:border-blue-400 hover:bg-blue-50"
                    >
                      <Compass className="h-3 w-3" aria-hidden="true" />
                      {d.linkedNodeId}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Bottom 2-Col Grid: Interactive I-8090 Zero-Poll Enforcer + G1-G4 & CA1-CA5 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Interactive I-8090 Exit-78 Zero-Polling Enforcer */}
        <section className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
          <div className="flex items-start justify-between gap-2">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">
                Interactive I-8090 Zero-Polling Guard (Exit 78 Enforcer)
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Tests worker scripts or userscript code for banned sleep/poll loops (D-08, D-09, D-10).
              </p>
            </div>
            <Terminal className="h-4 w-4 text-slate-400 shrink-0" aria-hidden="true" />
          </div>

          <textarea
            value={snippet}
            onChange={(e) => setSnippet(e.target.value)}
            rows={4}
            aria-label="Zero-polling guard code snippet"
            className="w-full rounded border border-slate-300 bg-slate-950 p-3 font-mono text-xs text-slate-100 focus:border-blue-500 focus:outline-none"
          />

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={checkingGuard}
              onClick={() => void runZeroPollCheck(snippet)}
              className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-800 disabled:opacity-50"
            >
              {checkingGuard ? 'Scanning...' : 'Evaluate Guard Rules'}
            </button>
            <button
              type="button"
              onClick={() => {
                const bad = 'while true; do\n  sleep 3\n  gh pr view 8164 --json mergeStateStatus\ndone';
                setSnippet(bad);
                void runZeroPollCheck(bad);
              }}
              className="rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
            >
              Load Poll Loop (Expect Exit 78)
            </button>
            <button
              type="button"
              onClick={() => {
                const good =
                  'const ws = new WebSocket("/api/realtime/ws"); // SQLite AFTER INSERT + Arc<Notify>';
                setSnippet(good);
                void runZeroPollCheck(good);
              }}
              className="rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
            >
              Load Push Notify (Expect Exit 0)
            </button>
          </div>

          {guardResult && (
            <div
              className={`rounded-md border p-3 text-xs ${
                guardResult.allowed
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
                  : 'border-red-200 bg-red-50 text-red-900'
              }`}
            >
              <div className="flex items-center justify-between gap-2 font-mono font-semibold">
                <span>{guardResult.allowed ? 'ALLOWED' : 'LOCKED OUT'}</span>
                <span>exitCode = {guardResult.exitCode}</span>
              </div>
              <p className="mt-1">{guardResult.verdict}</p>
              {guardResult.violations.length > 0 && (
                <ul className="mt-2 list-disc pl-4 space-y-0.5 font-mono text-[11px]">
                  {guardResult.violations.map((v, idx) => (
                    <li key={idx}>
                      Line {v.line} [{v.rule}]: {v.match}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* 5-Link Correction Chain CA1-CA5 */}
          <div className="pt-3 border-t border-slate-200 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-900">
                5-Link Correction Chain (CA1–CA5)
              </span>
              <span className="font-mono text-[11px] text-slate-500">
                {i8095.issueClassEntry.registeredIn}
              </span>
            </div>
            <div className="space-y-1.5">
              {i8095.correctionChain.map((c) => (
                <div
                  key={c.link}
                  className="rounded border border-slate-200 bg-slate-50 px-3 py-2 text-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1.5"
                >
                  <div className="min-w-0">
                    <span className="font-mono font-semibold text-slate-900">{c.link}</span>{' '}
                    <span className="font-medium text-slate-800">{c.title}</span>
                    <div className="text-[11px] text-slate-600">{c.detail}</div>
                  </div>
                  <span
                    className={`font-mono text-[10px] font-semibold shrink-0 ${
                      c.status === 'ENFORCED_SANDBOX' ? 'text-emerald-700' : 'text-amber-700'
                    }`}
                  >
                    {c.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Executable BDD Verification Scenarios G1-G4 */}
        <section className="bg-white border border-slate-200 rounded-lg p-5 space-y-3">
          <div className="flex items-start justify-between gap-2">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">
                Executable BDD Scenarios (G1–G4 &middot; /api/surface/meta Probe)
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Live cryptographic, 2,500-sequence WAL survival, surface telemetry, and zero-poll verification.
              </p>
            </div>
            <Lock className="h-4 w-4 text-emerald-700 shrink-0" aria-hidden="true" />
          </div>

          <div className="space-y-2.5">
            {i8095.bddScenarios.map((sc) => (
              <div
                key={sc.id}
                className="rounded-md border border-slate-200 p-3.5 text-xs space-y-1.5"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="font-semibold text-slate-900">
                    <span className="font-mono">{sc.id}</span> &middot; {sc.title}
                  </div>
                  <span
                    className={`inline-flex items-center gap-1 font-mono text-[11px] font-semibold shrink-0 ${
                      sc.passed ? 'text-emerald-700' : 'text-red-700'
                    }`}
                  >
                    {sc.passed ? (
                      <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                    ) : (
                      <ShieldAlert className="h-3.5 w-3.5" aria-hidden="true" />
                    )}
                    {sc.passed ? 'PASS' : 'FAIL'}
                  </span>
                </div>
                <div className="text-slate-600">
                  <strong>Given</strong> {sc.given}; <strong>When</strong> {sc.when};{' '}
                  <strong>Then</strong> {sc.then}.
                </div>
                <div className="pt-1 border-t border-slate-100 font-mono text-[11px] text-slate-800 break-words">
                  Evidence: {sc.measuredEvidence}
                </div>
              </div>
            ))}
          </div>

          <div className="rounded border border-slate-200 bg-slate-50 px-3 py-2 text-[11px] font-mono text-slate-700 flex flex-wrap items-center justify-between gap-2">
            <span>
              Live /api/surface/meta: voiceGatewayConnected=
              <strong className="text-amber-700">
                {String(i8095.surfaceMetaProbe.voiceGatewayConnected)}
              </strong>{' '}
              (hardcoded={String(i8095.surfaceMetaProbe.hardcoded)})
            </span>
            <span>greenlaneProjectionAttached=true</span>
          </div>
        </section>
      </div>
    </div>
  );
}
