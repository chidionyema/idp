/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  auditProsePassage,
  compileHumanVoiceRewrite,
  ESTATE_PROSE_PRESETS,
  type CommunicationChannel,
} from '../core/humanProseEngine';

interface HumanProseEngineViewProps {
  onNavigateToFlagship: () => void;
}

export const HumanProseEngineView: React.FC<HumanProseEngineViewProps> = ({
  onNavigateToFlagship,
}) => {
  const [selectedPresetId, setSelectedPresetId] = useState<string>(
    ESTATE_PROSE_PRESETS[0].id
  );
  const [channel, setChannel] = useState<CommunicationChannel>(
    ESTATE_PROSE_PRESETS[0].channel
  );
  const [draftText, setDraftText] = useState<string>(
    ESTATE_PROSE_PRESETS[0].aiDraft
  );
  const [compiledResult, setCompiledResult] = useState(() =>
    compileHumanVoiceRewrite(
      ESTATE_PROSE_PRESETS[0].aiDraft,
      ESTATE_PROSE_PRESETS[0].channel
    )
  );

  const liveDraftAudit = auditProsePassage(draftText, channel);

  const handleSelectPreset = (presetId: string) => {
    const preset =
      ESTATE_PROSE_PRESETS.find((p) => p.id === presetId) ||
      ESTATE_PROSE_PRESETS[0];
    setSelectedPresetId(preset.id);
    setChannel(preset.channel);
    setDraftText(preset.aiDraft);
    setCompiledResult(compileHumanVoiceRewrite(preset.aiDraft, preset.channel));
  };

  const handleChannelChange = (nextChannel: CommunicationChannel) => {
    setChannel(nextChannel);
    setCompiledResult(compileHumanVoiceRewrite(draftText, nextChannel));
  };

  const handleCompileRewrite = () => {
    setCompiledResult(compileHumanVoiceRewrite(draftText, channel));
  };

  const handleApplyRewriteToInput = () => {
    setDraftText(compiledResult.rewrittenText);
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 lg:py-10 space-y-8">
      {/* Header */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-end border-b border-slate-800/90 pb-6">
        <div className="lg:col-span-8 space-y-2">
          <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-slate-400">
            <span>Meridian Estate Linguistic Firewall</span>
            <span aria-hidden="true">·</span>
            <span>Written Editorial & Spoken Voice Compiler</span>
            <span aria-hidden="true">·</span>
            <span>Zero-RLHF-Slop Invariant</span>
          </div>
          <h1 className="text-2xl lg:text-4xl font-bold text-slate-100 font-display tracking-tight">
            Foundational Anti-AI-Prose & Human Voice Engine
          </h1>
          <p className="text-sm lg:text-base text-slate-300 max-w-3xl leading-relaxed">
            Synthetic prose destroys institutional credibility. Every document, audit dossier, public web page, and spoken executive briefing across the Meridian estate passes through this deterministic linguistic compiler—eliminating RLHF filler words, contrastive triads, em-dash crutches, and flat sentence-length monotony.
          </p>
        </div>

        <div className="lg:col-span-4 flex flex-wrap lg:justify-end gap-3">
          <div
            role="group"
            aria-label="Communication Channel Mode"
            className="flex items-center p-1 bg-[#0D121D] border border-slate-800 rounded-md"
          >
            <button
              type="button"
              onClick={() => handleChannelChange('written')}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-colors whitespace-nowrap shrink-0 ${
                channel === 'written'
                  ? 'bg-cyan-400 text-slate-950 font-semibold'
                  : 'text-slate-300 hover:text-slate-100'
              }`}
            >
              Written Editorial
            </button>
            <button
              type="button"
              onClick={() => handleChannelChange('spoken-voice')}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-colors whitespace-nowrap shrink-0 ${
                channel === 'spoken-voice'
                  ? 'bg-cyan-400 text-slate-950 font-semibold'
                  : 'text-slate-300 hover:text-slate-100'
              }`}
            >
              Spoken Voice / Briefing
            </button>
          </div>

          <button
            type="button"
            onClick={onNavigateToFlagship}
            className="px-3.5 py-2 text-xs font-medium text-slate-200 bg-[#111827] border border-slate-700 rounded-md hover:border-cyan-400 transition-colors whitespace-nowrap shrink-0"
          >
            View Live on Meridian Site
          </button>
        </div>
      </div>

      {/* Preset Selector Strip */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between text-xs font-mono text-slate-400">
          <span>01. Select Estate Communication Benchmark or Enter Custom Copy</span>
          <span className="tabular-nums">4 Canonical Benchmarks</span>
        </div>
        <div
          role="listbox"
          aria-label="Estate Prose Benchmarks"
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3"
        >
          {ESTATE_PROSE_PRESETS.map((preset) => {
            const isSelected = preset.id === selectedPresetId;
            return (
              <button
                key={preset.id}
                type="button"
                role="option"
                aria-selected={isSelected}
                onClick={() => handleSelectPreset(preset.id)}
                className={`text-left p-3.5 rounded-md border transition-colors flex flex-col justify-between gap-2 ${
                  isSelected
                    ? 'bg-[#111827] border-cyan-400 text-slate-100'
                    : 'bg-[#0B0F19] border-slate-800/90 text-slate-300 hover:border-slate-700'
                }`}
              >
                <div className="text-xs font-semibold font-display text-slate-100 leading-snug">
                  {preset.title}
                </div>
                <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                  <span>{preset.channel === 'spoken-voice' ? 'Spoken Voice' : 'Written Text'}</span>
                  <span className="text-cyan-300">Load Case →</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Asymmetric 5:7 Workbench */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left 5 Columns: Source Input & Violation Diagnostics */}
        <section
          aria-label="Source Draft and AI-Prose Violation Diagnostics"
          className="lg:col-span-5 bg-[#0D121D] border border-slate-800/90 rounded-lg p-5 space-y-5"
        >
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h2 className="text-sm font-bold text-slate-100 font-display">
                02. Source Communication Draft
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Analyzed in real time for RLHF vocabulary, contrastive crutches, and cadence flatness.
              </p>
            </div>
            <span
              className={`text-xs font-mono font-semibold tabular-nums whitespace-nowrap ${
                liveDraftAudit.verdict === 'ESTATE_CERTIFIED_HUMAN'
                  ? 'text-emerald-400'
                  : liveDraftAudit.verdict === 'AI_SLOP_QUARANTINED'
                    ? 'text-rose-400'
                    : 'text-amber-300'
              }`}
            >
              {liveDraftAudit.verdict === 'ESTATE_CERTIFIED_HUMAN'
                ? '● Certified Human'
                : liveDraftAudit.verdict === 'AI_SLOP_QUARANTINED'
                  ? `✖ Quarantined (${liveDraftAudit.violations.length} flags)`
                  : `▲ Advisory (${liveDraftAudit.violations.length} flag)`}
            </span>
          </div>

          <div>
            <label htmlFor="prose-source-textarea" className="sr-only">
              Source communication text to audit
            </label>
            <textarea
              id="prose-source-textarea"
              rows={6}
              value={draftText}
              onChange={(e) => setDraftText(e.target.value)}
              className="w-full p-3.5 text-sm bg-[#07090E] border border-slate-700/90 rounded-md text-slate-100 leading-relaxed focus:border-cyan-400 focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-3 gap-2.5 bg-[#080B12] p-3 rounded border border-slate-800/80 text-xs font-mono">
            <div>
              <div className="text-slate-400 text-[11px]">Human Score</div>
              <div
                className={`text-base font-bold tabular-nums ${
                  liveDraftAudit.humanAuthenticityScore >= 0.85
                    ? 'text-emerald-400'
                    : 'text-rose-400'
                }`}
              >
                {(liveDraftAudit.humanAuthenticityScore * 100).toFixed(0)}%
              </div>
            </div>
            <div>
              <div className="text-slate-400 text-[11px]">Burstiness CV</div>
              <div className="text-base font-bold text-slate-200 tabular-nums">
                {liveDraftAudit.burstinessIndex.toFixed(2)}
              </div>
            </div>
            <div>
              <div className="text-slate-400 text-[11px]">Slop Flags</div>
              <div
                className={`text-base font-bold tabular-nums ${
                  liveDraftAudit.violations.length === 0
                    ? 'text-emerald-400'
                    : 'text-rose-400'
                }`}
              >
                {liveDraftAudit.violations.length}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleCompileRewrite}
              className="flex-1 py-2.5 px-4 text-xs font-semibold text-slate-950 bg-cyan-400 rounded-md hover:bg-cyan-300 transition-colors whitespace-nowrap cursor-pointer"
            >
              Compile Human-Voice Rewrite
            </button>
            <button
              type="button"
              onClick={handleApplyRewriteToInput}
              className="py-2.5 px-3.5 text-xs font-medium text-slate-200 bg-[#141C2B] border border-slate-700 rounded-md hover:border-cyan-400 transition-colors whitespace-nowrap cursor-pointer"
            >
              Replace Draft with Certified Copy
            </button>
          </div>

          {/* Violations Breakdown */}
          <div className="space-y-2 pt-2 border-t border-slate-800/80">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400">
              <span>Detected Synthetic Signatures in Draft</span>
              <span className="tabular-nums">{liveDraftAudit.violations.length} items</span>
            </div>

            {liveDraftAudit.violations.length === 0 ? (
              <div className="p-3 rounded bg-emerald-950/20 border border-emerald-500/30 text-xs text-emerald-300 font-mono">
                ● Zero banned RLHF lexicon tokens, contrastive triads, or breath overruns detected in source draft.
              </div>
            ) : (
              <div className="max-h-64 overflow-y-auto space-y-2 pr-1">
                {liveDraftAudit.violations.map((v, idx) => (
                  <div
                    key={`${v.id}-${idx}`}
                    className="p-2.5 rounded bg-[#080B12] border border-slate-800 text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between font-mono">
                      <span className="text-rose-400 font-semibold">
                        ✖ “{v.matchedPhrase}”
                      </span>
                      <span className="text-slate-400">{v.category}</span>
                    </div>
                    <p className="text-slate-300 leading-snug">{v.rationale}</p>
                    <div className="font-mono text-[11px] text-cyan-300">
                      Action → {v.replacementSuggestion}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Right 7 Columns: Certified Human Output & Linguistic Telemetry */}
        <section
          aria-label="Certified Human-Voice Output and Linguistic Telemetry"
          className="lg:col-span-7 bg-[#0D121D] border border-slate-800/90 rounded-lg p-6 space-y-6"
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-4">
            <div>
              <h2 className="text-base font-bold text-slate-100 font-display">
                03. Certified Human-Voice Output ({channel === 'spoken-voice' ? 'Spoken Briefing Cadence' : 'Written Editorial Standard'})
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Verified against Meridian’s Zero-AI-Prose Constitution for public web, legal, and voice delivery.
              </p>
            </div>
            <span className="text-xs font-mono font-semibold text-emerald-400 whitespace-nowrap tabular-nums">
              ● {compiledResult.afterAudit.verdict} ({(compiledResult.afterAudit.humanAuthenticityScore * 100).toFixed(0)}%)
            </span>
          </div>

          {/* Rewritten Copy Display */}
          <div className="p-5 rounded-md bg-[#07090E] border border-slate-800/90 space-y-3">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400">
              <span>Compiled Estate Copy</span>
              <span className="tabular-nums">
                {compiledResult.afterAudit.sentenceCount} sentences · {compiledResult.afterAudit.wordCount} words · Mean {compiledResult.afterAudit.meanSentenceWords.toFixed(1)} words/sentence
              </span>
            </div>
            <p className="text-base lg:text-lg text-slate-100 leading-relaxed font-normal">
              {compiledResult.rewrittenText}
            </p>
          </div>

          {/* Before vs After Quantitative Telemetry */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3.5 rounded bg-[#080B12] border border-slate-800">
              <div className="text-[11px] font-mono text-slate-400">Human Authenticity</div>
              <div className="text-lg font-bold font-mono text-emerald-400 tabular-nums mt-1">
                {(compiledResult.afterAudit.humanAuthenticityScore * 100).toFixed(1)}%
              </div>
              <div className="text-[11px] font-mono text-slate-400 tabular-nums">
                was {(compiledResult.beforeAudit.humanAuthenticityScore * 100).toFixed(1)}%
              </div>
            </div>

            <div className="p-3.5 rounded bg-[#080B12] border border-slate-800">
              <div className="text-[11px] font-mono text-slate-400">Burstiness Index (σ/μ)</div>
              <div className="text-lg font-bold font-mono text-cyan-300 tabular-nums mt-1">
                {compiledResult.afterAudit.burstinessIndex.toFixed(2)}
              </div>
              <div className="text-[11px] font-mono text-slate-400 tabular-nums">
                target ≥ 0.35 (was {compiledResult.beforeAudit.burstinessIndex.toFixed(2)})
              </div>
            </div>

            <div className="p-3.5 rounded bg-[#080B12] border border-slate-800">
              <div className="text-[11px] font-mono text-slate-400">Concrete Specificity</div>
              <div className="text-lg font-bold font-mono text-slate-100 tabular-nums mt-1">
                {(compiledResult.afterAudit.concreteSpecificityScore * 100).toFixed(0)}%
              </div>
              <div className="text-[11px] font-mono text-slate-400 tabular-nums">
                numbers & active verbs
              </div>
            </div>

            <div className="p-3.5 rounded bg-[#080B12] border border-slate-800">
              <div className="text-[11px] font-mono text-slate-400">Spoken Breath Score</div>
              <div className="text-lg font-bold font-mono text-emerald-400 tabular-nums mt-1">
                {(compiledResult.afterAudit.spokenCadenceScore * 100).toFixed(0)}%
              </div>
              <div className="text-[11px] font-mono text-slate-400 tabular-nums">
                0 breath overruns
              </div>
            </div>
          </div>

          {/* Compiler Transformations Applied */}
          <div className="space-y-2">
            <h3 className="text-xs font-mono uppercase tracking-wider text-slate-400">
              Compiler Transformations Executed
            </h3>
            <ul className="space-y-1.5 text-xs font-mono text-slate-300 bg-[#080B12] p-3.5 rounded border border-slate-800">
              {compiledResult.operationsApplied.map((op, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-cyan-400 shrink-0">{i + 1}.</span>
                  <span>{op}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Foundational Estate Linguistic Rules */}
          <div className="pt-4 border-t border-slate-800 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="space-y-1">
              <div className="font-semibold text-slate-200 font-display">
                Rule 1 · Zero Contrastive Antithesis (“Not X, It’s Y”)
              </div>
              <p className="text-slate-400 leading-relaxed">
                LLMs compulsively frame statements as “not just X—it’s Y.” Meridian bans negative-positive framing across all product copy, board memos, and voice scripts. State the mechanism directly.
              </p>
            </div>
            <div className="space-y-1">
              <div className="font-semibold text-slate-200 font-display">
                Rule 2 · High Sentence-Length Burstiness & Breath Pacing
              </div>
              <p className="text-slate-400 leading-relaxed">
                Synthetic text clusters at 18–20 words per sentence. Human authority alternates 5-word factual verdicts with 24-word technical proofs, keeping spoken clauses under 24 words per breath.
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};
