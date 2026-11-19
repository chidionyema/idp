import { useEffect, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  Play,
  ShieldCheck,
  XCircle,
} from 'lucide-react';
import type {
  InterchangeableActuatorId,
  IocSandboxPreset,
  SystemFirstIocAdmissionResult,
  SystemFirstIocStateSnapshot,
} from '../types/api';

export function SystemFirstIocExplorer() {
  const [iocState, setIocState] = useState<SystemFirstIocStateSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);

  const [actuatorModel, setActuatorModel] = useState<InterchangeableActuatorId>('claude');
  const [workerQuadAttested, setWorkerQuadAttested] = useState(true);
  const [autoDecompose, setAutoDecompose] = useState(false);
  const [taskPrompt, setTaskPrompt] = useState('');
  const [proposedFilesText, setProposedFilesText] = useState('');
  const [targetHostsText, setTargetHostsText] = useState('');
  const [activePresetId, setActivePresetId] = useState<string>('PRESET_GHOST_OKE_LITELLM');
  const [evalResult, setEvalResult] = useState<SystemFirstIocAdmissionResult | null>(null);

  useEffect(() => {
    let active = true;
    void fetch('/api/ioc/state')
      .then((res) => (res.ok ? res.json() : null))
      .then((json: { snapshot?: SystemFirstIocStateSnapshot } | null) => {
        if (!active || !json?.snapshot) {
          if (active) setLoading(false);
          return;
        }
        const snap = json.snapshot;
        setIocState(snap);
        const initialPreset = snap.presets[1] ?? snap.presets[0];
        if (initialPreset) {
          setActuatorModel(initialPreset.actuatorModel);
          setWorkerQuadAttested(initialPreset.workerQuadAttested);
          setAutoDecompose(initialPreset.autoDecompose);
          setTaskPrompt(initialPreset.taskPrompt);
          setProposedFilesText(initialPreset.proposedFiles.join('\n'));
          setTargetHostsText(initialPreset.targetHosts.join(', '));
          setActivePresetId(initialPreset.presetId);
        }
        setEvalResult(snap.defaultEvaluation);
        setLoading(false);
      })
      .catch(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  async function runEvaluation(override?: {
    actuatorModel: InterchangeableActuatorId;
    workerQuadAttested: boolean;
    autoDecompose: boolean;
    taskPrompt: string;
    proposedFiles: string[];
    targetHosts: string[];
  }) {
    setEvaluating(true);
    try {
      const files =
        override?.proposedFiles ??
        proposedFilesText
          .split(/[\n,]+/)
          .map((s) => s.trim())
          .filter(Boolean);
      const hosts =
        override?.targetHosts ??
        targetHostsText
          .split(/[\n,]+/)
          .map((s) => s.trim())
          .filter(Boolean);

      const res = await fetch('/api/ioc/evaluate-admission', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          actuatorModel: override?.actuatorModel ?? actuatorModel,
          workerQuadAttested: override?.workerQuadAttested ?? workerQuadAttested,
          autoDecompose: override?.autoDecompose ?? autoDecompose,
          taskPrompt: override?.taskPrompt ?? taskPrompt,
          proposedFiles: files,
          targetHosts: hosts,
        }),
      });
      const json = (await res.json()) as { result?: SystemFirstIocAdmissionResult };
      if (json.result) {
        setEvalResult(json.result);
      }
    } finally {
      setEvaluating(false);
    }
  }

  function applyPreset(preset: IocSandboxPreset) {
    setActivePresetId(preset.presetId);
    setActuatorModel(preset.actuatorModel);
    setWorkerQuadAttested(preset.workerQuadAttested);
    setAutoDecompose(preset.autoDecompose);
    setTaskPrompt(preset.taskPrompt);
    setProposedFilesText(preset.proposedFiles.join('\n'));
    setTargetHostsText(preset.targetHosts.join(', '));
    void runEvaluation({
      actuatorModel: preset.actuatorModel,
      workerQuadAttested: preset.workerQuadAttested,
      autoDecompose: preset.autoDecompose,
      taskPrompt: preset.taskPrompt,
      proposedFiles: preset.proposedFiles,
      targetHosts: preset.targetHosts,
    });
  }

  if (loading || !iocState) {
    return (
      <div className="h-48 rounded-lg bg-white border border-slate-200 animate-pulse" aria-busy="true" />
    );
  }

  const cont = iocState.continuity;

  return (
    <div className="space-y-6">
      {/* 1. Zero-Dependency Repository DNA Continuity Strip */}
      <section className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
          <div>
            <div className="text-xs font-mono text-slate-500">
              {iocState.law} · ZERO-DEPENDENCY MODEL CONTINUITY
            </div>
            <h3 className="text-base font-semibold text-slate-900">
              Self-Extracting 4KB Repository DNA &amp; Interchangeable Actuator Binding
            </h3>
            <p className="text-xs text-slate-600 mt-0.5">
              Gemini, GLM 5.3, DeepSeek, Kimi, Claude, and ChatGPT operate as stateless compute actuators hydrated directly from repository root DNA and canonical OMNIFLOW custody.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <a
              href="/ROUTER.md"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 whitespace-nowrap"
            >
              <Download className="h-3.5 w-3.5 text-slate-500" aria-hidden="true" />
              ROUTER.md
            </a>
            <a
              href="/GENESIS_SPORE.dna"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 whitespace-nowrap"
            >
              <Download className="h-3.5 w-3.5 text-slate-500" aria-hidden="true" />
              GENESIS_SPORE.dna
            </a>
          </div>
        </div>

        <div className="border-t border-slate-200 pt-4 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-slate-200 bg-slate-50/70 rounded-md">
          <div className="px-3.5 py-2.5">
            <div className="text-[11px] font-medium text-slate-500">AGENTS.md Ratchet</div>
            <div className="mt-1 font-mono text-sm font-semibold text-emerald-700 tabular-nums">
              {cont.agentsMdLines} / 300 Lines
            </div>
            <div className="mt-0.5 text-[11px] text-slate-500">
              {cont.agentsMdWithinCeiling ? 'Locked under ceiling' : 'Ceiling violated'}
            </div>
          </div>

          <div className="px-3.5 py-2.5">
            <div className="text-[11px] font-medium text-slate-500">ROUTER.md Authority</div>
            <div className="mt-1 font-mono text-sm font-semibold text-slate-900">
              pennyd 127.0.0.1:4200
            </div>
            <div className="mt-0.5 text-[11px] text-slate-500">
              LiteLLM :4000–:4002 tombstoned
            </div>
          </div>

          <div className="px-3.5 py-2.5">
            <div className="text-[11px] font-medium text-slate-500">GENESIS_SPORE.dna (&le;4KB)</div>
            <div className="mt-1 font-mono text-sm font-semibold text-emerald-700 tabular-nums">
              {cont.genesisSporeBytes.toLocaleString()} / 4,096 B
            </div>
            <div className="mt-0.5 text-[11px] text-slate-500">
              {cont.constitutionalInvariantsCount} Invariants · {cont.catechismAntibodiesCount} Antibodies
            </div>
          </div>

          <div className="px-3.5 py-2.5">
            <div className="text-[11px] font-medium text-slate-500">Active Merkle &amp; Fence</div>
            <div className="mt-1 font-mono text-sm font-semibold text-slate-900 tabular-nums">
              Fence #{cont.monotonicFencingToken ?? 0}
            </div>
            <div className="mt-0.5 font-mono text-[11px] text-slate-500 truncate">
              Root {cont.activeMerkleRoot?.slice(0, 16)}…
            </div>
          </div>
        </div>
      </section>

      {/* 2. Interactive Pre-Token Admission & Anti-Confusion Sandbox */}
      <section className="bg-white border border-slate-200 rounded-lg p-5 space-y-5">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3">
          <div>
            <h3 className="text-base font-semibold text-slate-900">
              Interactive Pre-Token Admission &amp; Anti-Confusion Gate (0 Tokens Spent)
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Test how any interchangeable model actuator is mechanically intercepted before spending 1 inference token when referencing retired OKE/LiteLLM ghosts, dead hosts, or unsplit multi-subsystem manifests.
            </p>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {iocState.presets.map((preset) => (
              <button
                key={preset.presetId}
                type="button"
                onClick={() => applyPreset(preset)}
                className={`rounded-md border px-2.5 py-1.5 text-xs font-medium transition-colors whitespace-nowrap ${
                  activePresetId === preset.presetId
                    ? 'border-slate-900 bg-slate-900 text-white'
                    : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'
                }`}
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 pt-2 border-t border-slate-200">
          <div className="lg:col-span-5 space-y-3.5">
            <div>
              <label htmlFor="ioc-actuator-select" className="block text-xs font-medium text-slate-700 mb-1">
                Interchangeable Stateless Model Actuator
              </label>
              <select
                id="ioc-actuator-select"
                value={actuatorModel}
                onChange={(e) => setActuatorModel(e.target.value as InterchangeableActuatorId)}
                className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900"
              >
                {iocState.actuators.map((act) => (
                  <option key={act.id} value={act.id}>
                    {act.label} ({act.transportLane})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="ioc-task-prompt" className="block text-xs font-medium text-slate-700 mb-1">
                Task Prompt / Shell Command
              </label>
              <textarea
                id="ioc-task-prompt"
                rows={3}
                value={taskPrompt}
                onChange={(e) => setTaskPrompt(e.target.value)}
                className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 font-mono text-xs text-slate-900"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label htmlFor="ioc-proposed-files" className="block text-xs font-medium text-slate-700 mb-1">
                  Proposed Files Manifest
                </label>
                <textarea
                  id="ioc-proposed-files"
                  rows={3}
                  value={proposedFilesText}
                  onChange={(e) => setProposedFilesText(e.target.value)}
                  className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 font-mono text-xs text-slate-900"
                />
              </div>
              <div>
                <label htmlFor="ioc-target-hosts" className="block text-xs font-medium text-slate-700 mb-1">
                  Target External Hosts
                </label>
                <textarea
                  id="ioc-target-hosts"
                  rows={3}
                  value={targetHostsText}
                  onChange={(e) => setTargetHostsText(e.target.value)}
                  className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 font-mono text-xs text-slate-900"
                />
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
              <div className="flex flex-wrap items-center gap-4 text-xs text-slate-700">
                <label className="inline-flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={workerQuadAttested}
                    onChange={(e) => setWorkerQuadAttested(e.target.checked)}
                    className="rounded border-slate-300"
                  />
                  QUAD Attested
                </label>
                <label className="inline-flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={autoDecompose}
                    onChange={(e) => setAutoDecompose(e.target.checked)}
                    className="rounded border-slate-300"
                  />
                  Auto-Decompose (#8194)
                </label>
              </div>

              <button
                type="button"
                disabled={evaluating}
                onClick={() => void runEvaluation()}
                className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-blue-700 transition-colors whitespace-nowrap disabled:opacity-50"
              >
                <Play className="h-3.5 w-3.5" aria-hidden="true" />
                {evaluating ? 'Evaluating...' : 'Evaluate Pre-Token Gate'}
              </button>
            </div>
          </div>

          <div className="lg:col-span-7 space-y-3">
            {evalResult && (
              <div className="border border-slate-200 rounded-md overflow-hidden">
                <div
                  className={`px-4 py-3 border-b flex flex-wrap items-center justify-between gap-2 ${
                    evalResult.admitted
                      ? 'bg-emerald-50/70 border-emerald-200'
                      : 'bg-red-50/70 border-red-200'
                  }`}
                >
                  <div className="flex items-center gap-2 text-xs font-mono font-semibold">
                    {evalResult.admitted ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-700 shrink-0" aria-hidden="true" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-700 shrink-0" aria-hidden="true" />
                    )}
                    <span className={evalResult.admitted ? 'text-emerald-900' : 'text-red-900'}>
                      HTTP {evalResult.httpStatus} · {evalResult.verdictCode}
                    </span>
                  </div>
                  <div className="text-xs font-mono text-slate-600">
                    Tokens Spent: {evalResult.tokensSpent} · Actuator: {evalResult.actuatorModel}
                  </div>
                </div>

                <div className="p-4 space-y-3 bg-white text-xs">
                  <p className="text-slate-700 font-medium">{evalResult.summary}</p>

                  {evalResult.antiConfusionViolations.length > 0 && (
                    <div className="border border-red-200 bg-red-50/50 rounded p-3 space-y-2">
                      <div className="font-semibold text-red-900 flex items-center gap-1.5">
                        <AlertTriangle className="h-3.5 w-3.5 text-red-700 shrink-0" aria-hidden="true" />
                        Intercepted Retired Estate Ghost(s) — Replace Before Dispatch:
                      </div>
                      {evalResult.antiConfusionViolations.map((v) => (
                        <div key={v.domainId} className="pl-5 space-y-0.5 text-[11px]">
                          <div className="font-mono text-red-800">
                            [{v.domain}] Blocked: {v.matchedRetiredGhost}
                          </div>
                          <div className="font-mono text-emerald-800">
                            Canonical Truth: {v.canonicalReplacement}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {evalResult.decomposedChildLanes.length > 1 && (
                    <div className="border border-blue-200 bg-blue-50/40 rounded p-3 space-y-1.5">
                      <div className="font-semibold text-slate-900 flex items-center gap-1.5">
                        <ShieldCheck className="h-3.5 w-3.5 text-blue-700 shrink-0" aria-hidden="true" />
                        Compliant Single-Subsystem Child Lanes ({evalResult.decomposedChildLanes.length}):
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1">
                        {evalResult.decomposedChildLanes.map((lane) => (
                          <div key={lane.laneId} className="border border-slate-200 bg-white rounded p-2 font-mono text-[11px]">
                            <div className="font-semibold text-slate-900">{lane.laneId}</div>
                            <div className="text-slate-600 truncate">{lane.files.join(', ')}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="divide-y divide-slate-200 border border-slate-200 rounded">
                    {evalResult.gateRows.map((g) => (
                      <div key={g.gateId} className="px-3 py-2 flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="font-medium text-slate-900">{g.title}</div>
                          <div className="text-[11px] text-slate-600">{g.detail}</div>
                        </div>
                        <span
                          className={`font-mono text-[11px] font-semibold whitespace-nowrap shrink-0 ${
                            g.verdict === 'PASSED'
                              ? 'text-emerald-700'
                              : g.verdict === 'AUTO_DECOMPOSED'
                                ? 'text-blue-700'
                                : 'text-red-700'
                          }`}
                        >
                          {g.verdict}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* 3. The 8-Domain Anti-Confusion Ledger */}
      <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-base font-semibold text-slate-900">
              The Anti-Confusion Ledger · Retired Ghosts vs. Canonical Estate Truth
            </h3>
            <p className="text-xs text-slate-500">
              Authoritative 8-domain map enforced across terminal (dsh, opencode, argon), API (pennyd), and browser (TinyFish) surfaces
            </p>
          </div>
          <span className="font-mono text-xs text-slate-600">
            {iocState.antiConfusionLedger.length} Canonical Domains
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold">
                <th className="py-2.5 px-4">Domain</th>
                <th className="py-2.5 px-4">Permanently Retired / Tombstoned (Do Not Use)</th>
                <th className="py-2.5 px-4">Canonical Live Truth (Enforced Estate-Wide)</th>
                <th className="py-2.5 px-4">Mechanical Enforcement Gate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {iocState.antiConfusionLedger.map((row) => (
                <tr key={row.domainId} className="align-top hover:bg-slate-50/60">
                  <td className="py-3 px-4 font-semibold text-slate-900 whitespace-nowrap">
                    {row.domain}
                  </td>
                  <td className="py-3 px-4 font-mono text-[11px] text-red-800 max-w-xs">
                    {row.retiredTombstoned}
                  </td>
                  <td className="py-3 px-4 font-mono text-[11px] text-emerald-900 max-w-xs">
                    {row.canonicalLiveTruth}
                  </td>
                  <td className="py-3 px-4 text-slate-600 max-w-xs">
                    {row.enforcementGate}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
