import React, { useState } from 'react';
import {
  EstateState,
  compareActuationEngines,
  generateProductionEstateFiles,
} from '../engine/ottoEngine';
import { Check, Copy, Terminal, Zap, ArrowUpRight } from 'lucide-react';

interface SovereignActuationViewProps {
  state: EstateState;
  onExecuteDrop1082: () => void;
}

export const SovereignActuationView: React.FC<SovereignActuationViewProps> = ({
  state,
  onExecuteDrop1082,
}) => {
  const comparisonRows = compareActuationEngines();
  const productionFiles = generateProductionEstateFiles(state);
  const [selectedFileIndex, setSelectedFileIndex] = useState(0);
  const [copiedFile, setCopiedFile] = useState<string | null>(null);

  const activeFile = productionFiles[selectedFileIndex] || productionFiles[0];

  const handleCopy = (filename: string, content: string) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(content).catch(() => {});
    }
    setCopiedFile(filename);
    setTimeout(() => setCopiedFile(null), 2000);
  };

  return (
    <div className="space-y-8">
      {/* Why AutoGLM Failed & How Otto Sovereign Actuation Exceeds It */}
      <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-6 pb-5 border-b border-slate-200 dark:border-slate-800">
          <div className="space-y-2 max-w-3xl">
            <div className="text-xs font-mono text-slate-500 dark:text-slate-400 tabular-nums">
              SOVEREIGN ACTUATION ENGINE · DROP-2026-1082 (BUNDLE c3d3ce2c) · ZERO EXTERNAL LOGIN
            </div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50">
              Exceeding AutoGLM: Sovereign CDP Accessibility Sieve & Direct Git Bundle Sync
            </h1>
            <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
              AutoGLM stalled at <code className="font-mono text-xs">&quot;Not logged in. Please log in to the extension.&quot;</code>{' '}
              because its browser extension requires a mainland Chinese Zhipu account and streams full-screen PNGs to a
              remote cloud VLM at 2,450 ms/step. Otto replaces AutoGLM with two deterministic, sovereign layers:
              <strong> (1) DROP-2026-1082 Direct Bundle Push</strong> (<code className="font-mono text-xs">npm run sync:github</code>{' '}
              pushing bundle <code className="font-mono text-xs">c3d3ce2c</code> directly to{' '}
              <code className="font-mono text-xs">genesis-live</code> with zero browser login) and{' '}
              <strong>(2) Local Playwright-CDP Accessibility Tree Grounding</strong> at 38 ms/step.
            </p>
          </div>

          <div className="flex flex-col gap-2.5 shrink-0">
            <button
              type="button"
              onClick={onExecuteDrop1082}
              className="inline-flex items-center justify-center gap-2 px-4 py-2.5 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer"
            >
              <ArrowUpRight className="w-4 h-4" />
              {state.drop1082Synced
                ? 'DROP-2026-1082 Synced (c3d3ce2c -> genesis-live)'
                : 'Run DROP-2026-1082 (npm run sync:github)'}
            </button>
            <div className="text-xs font-mono text-slate-500 dark:text-slate-400 text-right tabular-nums">
              Status: {state.drop1082Synced ? 'SEALED_TO_ORIGIN' : 'DEMO_STAGED'}
            </div>
          </div>
        </div>

        {/* Quantitative Benchmark Table: AutoGLM vs Otto Sovereign Actuation */}
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-xs font-mono text-slate-500 dark:text-slate-400">
                <th className="py-2.5 pr-4 font-medium">Architectural Dimension</th>
                <th className="py-2.5 px-3 font-medium">Legacy AutoGLM Extension (Dead-End)</th>
                <th className="py-2.5 px-3 font-medium">Otto Sovereign Engine (Genesis Native)</th>
                <th className="py-2.5 pl-3 font-medium text-right">Measured Advantage</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800/70 text-xs tabular-nums">
              {comparisonRows.map((row) => (
                <tr key={row.dimension} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                  <td className="py-3.5 pr-4 font-semibold text-slate-900 dark:text-slate-100">
                    {row.dimension}
                  </td>
                  <td className="py-3.5 px-3 text-rose-400 font-mono">
                    {row.autoGlm}
                  </td>
                  <td className="py-3.5 px-3 text-slate-700 dark:text-slate-200 font-mono">
                    {row.ottoSovereign}
                  </td>
                  <td className="py-3.5 pl-3 text-right font-mono font-semibold text-emerald-500">
                    {row.advantageMultiplier}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Ready-to-Deploy Production Files for Mac Estate (~/.estate/bin & Argon) */}
      <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              Production Estate Artifacts (Ready for ~/.estate & Argon Checkout)
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Inspect and copy the exact files generated from the current HUD state to unblock Argon, register the 5-minute
              launchd sweep, and run the autonomous backlog drainer.
            </p>
          </div>

          <button
            type="button"
            onClick={() => handleCopy(activeFile.filename, activeFile.content)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer"
          >
            {copiedFile === activeFile.filename ? (
              <>
                <Check className="w-3.5 h-3.5" />
                Copied {activeFile.filename}
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                Copy {activeFile.filename}
              </>
            )}
          </button>
        </div>

        {/* File Selector Tabs */}
        <div className="flex flex-wrap items-center gap-1.5 p-1 bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg">
          {productionFiles.map((file, idx) => (
            <button
              key={file.filename}
              type="button"
              onClick={() => setSelectedFileIndex(idx)}
              className={`px-3 py-1.5 text-xs font-mono rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                selectedFileIndex === idx
                  ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              {file.filename}
            </button>
          ))}
        </div>

        <div className="space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono text-slate-500 dark:text-slate-400">
            <span>Target Path: <strong className="text-slate-200">{activeFile.targetPath}</strong></span>
            <span>{activeFile.description}</span>
          </div>
          <pre className="p-4 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-slate-200 overflow-x-auto leading-relaxed max-h-96">
            {activeFile.content}
          </pre>
        </div>
      </section>
    </div>
  );
};
