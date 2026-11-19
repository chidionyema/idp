import React, { useState } from 'react';
import { EstateState, ForgedTool } from '../engine/ottoEngine';
import { Wrench, BookOpen, Plus } from 'lucide-react';

interface ToolForgeCatechismViewProps {
  state: EstateState;
  onForgeTool: (input: {
    name: string;
    language: ForgedTool['language'];
    bottleneckSolved: string;
    targetRepo: string;
  }) => void;
}

export const ToolForgeCatechismView: React.FC<ToolForgeCatechismViewProps> = ({
  state,
  onForgeTool,
}) => {
  const [name, setName] = useState('');
  const [language, setLanguage] = useState<ForgedTool['language']>('Python 3.12');
  const [bottleneckSolved, setBottleneckSolved] = useState('');
  const [targetRepo, setTargetRepo] = useState('idp');
  const [error, setError] = useState<string | null>(null);

  const handleForgeSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !bottleneckSolved.trim()) {
      setError('Provide both a CLI tool name and the estate bottleneck it resolves.');
      return;
    }
    setError(null);
    onForgeTool({
      name: name.trim(),
      language,
      bottleneckSolved: bottleneckSolved.trim(),
      targetRepo,
    });
    setName('');
    setBottleneckSolved('');
  };

  return (
    <div className="space-y-8">
      {/* Pillar 1: AUTO_TOOL_FORGING */}
      <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
          <div>
            <div className="text-xs font-mono text-slate-500 dark:text-slate-400 tabular-nums">
              PILLAR 01 · AUTO_TOOL_FORGING · propose/&lt;mission-id&gt;/auto-tool
            </div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50 mt-1">
              Autonomous Tool Synthesis & Estate Automation Modules
            </h1>
            <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
              Otto continuously sweeps <code className="font-mono text-xs">idp</code>,{' '}
              <code className="font-mono text-xs">argon</code>, and{' '}
              <code className="font-mono text-xs">argon-sync</code> for missing capabilities, synthesizes tested Python,
              Rust, and Node.js CLI tools, and stages them on <code className="font-mono text-xs">propose/&lt;mission-id&gt;/auto-tool</code>.
            </p>
          </div>
          <div className="text-xs font-mono text-slate-500 dark:text-slate-400 tabular-nums shrink-0">
            Total Forged Tools: <strong className="text-emerald-500">{state.forgedTools.length}</strong>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {state.forgedTools.map((tool) => (
            <div
              key={tool.id}
              className="border border-slate-200 dark:border-slate-800 rounded-lg p-5 flex flex-col justify-between space-y-4"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs font-mono text-slate-500 dark:text-slate-400 tabular-nums">
                  <span>{tool.language}</span>
                  <span className="text-emerald-500 font-semibold">{tool.testsPassed} tests passed</span>
                </div>
                <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100 font-mono">
                  {tool.name}
                </h2>
                <div className="text-xs font-mono text-slate-500 dark:text-slate-400">
                  Path: {tool.targetPath} · {tool.proposalBranch}
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                  {tool.bottleneckSolved}
                </p>
              </div>

              <div className="space-y-2">
                <pre className="p-3 rounded bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-300 overflow-x-auto">
                  {tool.sourceSnippet}
                </pre>
                <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400 tabular-nums">
                  Receipt: {tool.binaryOrScriptHash}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Forge New Tool Form */}
        <form
          onSubmit={handleForgeSubmit}
          className="pt-6 border-t border-slate-200 dark:border-slate-800 grid grid-cols-1 md:grid-cols-4 gap-4"
        >
          <div>
            <label
              htmlFor="forge-tool-name"
              className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1"
            >
              Tool Binary / Script Name
            </label>
            <input
              id="forge-tool-name"
              type="text"
              placeholder="e.g., otto-cargo-cache-prune"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg text-slate-900 dark:text-slate-100"
            />
          </div>

          <div>
            <label
              htmlFor="forge-tool-lang"
              className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1"
            >
              Execution Runtime
            </label>
            <select
              id="forge-tool-lang"
              value={language}
              onChange={(e) => setLanguage(e.target.value as ForgedTool['language'])}
              className="w-full px-3 py-2 text-xs font-mono bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg text-slate-900 dark:text-slate-100"
            >
              <option value="Python 3.12">Python 3.12</option>
              <option value="Rust 2024">Rust 2024</option>
              <option value="Node.js ESM">Node.js ESM</option>
            </select>
          </div>

          <div className="md:col-span-2">
            <label
              htmlFor="forge-tool-bottleneck"
              className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1"
            >
              Bottleneck Solved Across Estate
            </label>
            <div className="flex gap-2">
              <input
                id="forge-tool-bottleneck"
                type="text"
                placeholder="e.g., Deduplicates incremental Rust rlib artifacts across 25 idp worktrees"
                value={bottleneckSolved}
                onChange={(e) => setBottleneckSolved(e.target.value)}
                className="flex-1 px-3 py-2 text-xs bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg text-slate-900 dark:text-slate-100"
              />
              <button
                type="submit"
                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                Forge Auto-Tool
              </button>
            </div>
          </div>

          {error ? (
            <div className="md:col-span-4 text-xs font-mono text-rose-500">{error}</div>
          ) : null}
        </form>
      </section>

      {/* Pillar 3: CATECHISM_RATCHET */}
      <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 space-y-5">
        <div className="pb-4 border-b border-slate-200 dark:border-slate-800">
          <div className="text-xs font-mono text-slate-500 dark:text-slate-400 tabular-nums">
            PILLAR 03 · CATECHISM_RATCHET · SUBORDINATE AGENT TEACHING
          </div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 mt-1">
            Permanent Operational Catechism Laws
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Every architecture gap or pre-push refusal is ratcheted into a permanent rule and injected into the prompt-space
            of Claude, Codex, and Pi so the estate never repeats a failure mode.
          </p>
        </div>

        <div className="divide-y divide-slate-200 dark:divide-slate-800">
          {state.catechismRules.map((rule) => (
            <div key={rule.id} className="py-4 first:pt-0 last:pb-0 space-y-1.5">
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono text-slate-500 dark:text-slate-400 tabular-nums">
                <span>
                  <strong className="text-slate-900 dark:text-slate-100">{rule.id}</strong> · {rule.code} · {rule.domain}
                </span>
                <span>
                  Propagated to: <strong className="text-emerald-500">{rule.propagatedTo.join(', ')}</strong> · CI Enforced
                </span>
              </div>
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                {rule.title}
              </h3>
              <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                {rule.directive}
              </p>
              <div className="text-xs font-mono text-slate-500 dark:text-slate-400">
                Synthesized From: {rule.synthesizedFrom}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};
