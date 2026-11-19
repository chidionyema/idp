/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useMemo } from 'react';
import {
  WwfdDilemmaCard,
  DpoPairTuple,
  INITIAL_WWFD_CARDS,
} from '../lib/protocolEngine.ts';
import {
  Sparkles,
  Check,
  ChevronLeft,
  ChevronRight,
  Database,
  Download,
  Brain,
  Keyboard,
  ShieldCheck,
  Info,
} from 'lucide-react';

export const WwfdDailyDeck: React.FC = () => {
  const [cards, setCards] = useState<WwfdDilemmaCard[]>(INITIAL_WWFD_CARDS);
  const [currentCardIndex, setCurrentCardIndex] = useState<number>(0);
  const [showDpoExportModal, setShowDpoExportModal] = useState<boolean>(false);
  const [dpoTuples, setDpoTuples] = useState<DpoPairTuple[]>([]);

  const currentCard = cards[currentCardIndex];

  // 1-Keystroke Hotkey listeners [1, 2, 3] + [ArrowLeft, ArrowRight]
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (['1', '2', '3'].includes(e.key)) {
        const choiceId = parseInt(e.key, 10);
        handleSelectChoice(currentCard.id, choiceId);
      } else if (e.key === 'ArrowRight' || e.key === 'n') {
        setCurrentCardIndex((prev) => (prev < cards.length - 1 ? prev + 1 : prev));
      } else if (e.key === 'ArrowLeft' || e.key === 'p') {
        setCurrentCardIndex((prev) => (prev > 0 ? prev - 1 : prev));
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentCard, cards.length]);

  const handleSelectChoice = (cardId: string, choiceId: number) => {
    setCards((prev) =>
      prev.map((c) => (c.id === cardId ? { ...c, founderChoiceId: choiceId } : c))
    );
  };

  // Generate DPO Pairwise Tuples
  const handleExportDpo = () => {
    const tuples: DpoPairTuple[] = cards
      .filter((c) => c.founderChoiceId !== undefined)
      .map((c) => {
        const chosen = c.options.find((o) => o.id === c.founderChoiceId)?.label || '';
        // If founder chose something other than Otto, rejected is Otto's recommendation; otherwise an alternative
        const rejected =
          c.options.find(
            (o) => o.id !== c.founderChoiceId && o.id === c.ottoBaselineRecommendation.choiceId
          )?.label || c.options.find((o) => o.id !== c.founderChoiceId)?.label || '';

        return {
          cardId: c.id,
          title: c.title,
          prompt: c.scenario,
          chosenOption: chosen,
          rejectedOption: rejected,
          recordedAt: new Date().toISOString(),
          modelTarget: 'estate.db/dpo_calibration_v1',
        };
      });

    setDpoTuples(tuples);
    setShowDpoExportModal(true);
  };

  // Alignment score
  const alignmentStats = useMemo(() => {
    const decided = cards.filter((c) => c.founderChoiceId !== undefined);
    if (decided.length === 0) return { total: cards.length, decided: 0, matched: 0, percentage: 100 };
    const matched = decided.filter((c) => c.founderChoiceId === c.ottoBaselineRecommendation.choiceId).length;
    return {
      total: cards.length,
      decided: decided.length,
      matched,
      percentage: Math.round((matched / decided.length) * 100),
    };
  }, [cards]);

  return (
    <div className="space-y-8">
      {/* Deck Header */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 sm:p-8">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-mono text-cyan-400">
              <Brain className="w-4 h-4 text-cyan-400" />
              <span>WHAT WOULD FOUNDER DO (WWFD) · 5-CARD DAILY CALIBRATION DECK</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              WWFD Daily Alignment Calibration
            </h1>
            <p className="text-slate-400 text-sm max-w-2xl">
              1-keystroke hotkeys [1], [2], [3] for evaluating high-entropy trade-offs. Otto baseline recommendations are compared against Founder decisions to generate Direct Preference Optimization (DPO) tuples with zero cloud vendor egress charges.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs font-mono text-slate-300 flex items-center justify-between gap-4">
              <div>
                <span className="text-slate-500 block text-[10px]">Otto Alignment:</span>
                <span className="text-cyan-400 font-bold text-sm tabular-nums">
                  {alignmentStats.percentage}% ({alignmentStats.matched}/{alignmentStats.decided || 0})
                </span>
              </div>
              <div className="text-right">
                <span className="text-slate-500 block text-[10px]">Cards Calibrated:</span>
                <span className="text-slate-200 font-bold tabular-nums">
                  {alignmentStats.decided} / {alignmentStats.total}
                </span>
              </div>
            </div>

            <button
              onClick={handleExportDpo}
              className="flex items-center justify-center gap-2 px-4 py-2 text-xs font-semibold text-slate-950 bg-gradient-to-r from-teal-400 to-cyan-400 hover:from-teal-300 hover:to-cyan-300 rounded-lg transition-all shadow cursor-pointer"
            >
              <Database className="w-4 h-4" />
              <span>Export DPO Tuples</span>
            </button>
          </div>
        </div>
      </div>

      {/* Card Carousel Controls & Stepper */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {cards.map((c, idx) => (
            <button
              key={c.id}
              onClick={() => setCurrentCardIndex(idx)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all ${
                currentCardIndex === idx
                  ? 'bg-cyan-500 text-slate-950 font-bold shadow'
                  : c.founderChoiceId !== undefined
                  ? 'bg-slate-800 text-emerald-400 border border-emerald-800/60'
                  : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              Card {idx + 1}
              {c.founderChoiceId !== undefined && ' ✓'}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <div className="hidden sm:flex items-center gap-1 text-[11px] font-mono text-slate-400 mr-2">
            <Keyboard className="w-3.5 h-3.5 text-slate-500" />
            <span>Hotkeys: Press [1], [2], [3] or [←]/[→]</span>
          </div>

          <button
            onClick={() => setCurrentCardIndex((prev) => Math.max(0, prev - 1))}
            disabled={currentCardIndex === 0}
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={() => setCurrentCardIndex((prev) => Math.min(cards.length - 1, prev + 1))}
            disabled={currentCardIndex === cards.length - 1}
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Active Card Body */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 sm:p-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-4">
          <div>
            <div className="text-xs font-mono text-cyan-400">
              CARD {currentCardIndex + 1} OF 5 · {currentCard.category}
            </div>
            <h2 className="text-xl font-bold text-white mt-0.5">{currentCard.title}</h2>
          </div>
          <span className="text-xs font-mono text-slate-500">{currentCard.id}</span>
        </div>

        {/* Scenario description */}
        <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 text-sm text-slate-200 leading-relaxed font-mono">
          <span className="text-cyan-400 font-bold block text-xs uppercase mb-1">Dilemma Scenario:</span>
          {currentCard.scenario}
        </div>

        {/* Otto baseline autonomous recommendation */}
        <div className="p-4 bg-cyan-950/20 border border-cyan-800/60 rounded-lg space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold text-cyan-300 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
              OTTO AUTONOMOUS PROVISIONAL RECOMMENDATION
            </span>
            <span className="text-xs font-mono text-cyan-400 font-bold tabular-nums">
              Confidence: {(currentCard.ottoBaselineRecommendation.confidence * 100).toFixed(0)}%
            </span>
          </div>
          <div className="text-sm font-semibold text-white">
            Option {currentCard.ottoBaselineRecommendation.choiceId}: {currentCard.ottoBaselineRecommendation.choiceLabel}
          </div>
          <div className="text-xs text-slate-300 leading-relaxed">
            {currentCard.ottoBaselineRecommendation.rationale}
          </div>
        </div>

        {/* 3 Strategic Options */}
        <div className="space-y-3 pt-2">
          <div className="text-xs font-mono uppercase tracking-wider text-slate-400">
            Select Founder Sovereign Preference (Click or press [1], [2], [3]):
          </div>

          <div className="space-y-3">
            {currentCard.options.map((opt) => {
              const isSelected = currentCard.founderChoiceId === opt.id;
              const isOttoChoice = currentCard.ottoBaselineRecommendation.choiceId === opt.id;

              return (
                <div
                  key={opt.id}
                  onClick={() => handleSelectChoice(currentCard.id, opt.id)}
                  className={`p-4 rounded-xl border transition-all cursor-pointer relative ${
                    isSelected
                      ? 'bg-slate-800/90 border-cyan-400 shadow-md ring-1 ring-cyan-500/30'
                      : 'bg-slate-950/80 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                      <div
                        className={`w-6 h-6 rounded-md font-mono text-xs font-bold flex items-center justify-center shrink-0 ${
                          isSelected
                            ? 'bg-cyan-400 text-slate-950'
                            : 'bg-slate-800 text-slate-300'
                        }`}
                      >
                        {opt.id}
                      </div>
                      <div>
                        <div className="text-sm font-bold text-white flex items-center gap-2">
                          <span>{opt.label}</span>
                          {isOttoChoice && (
                            <span className="text-[10px] font-mono font-medium text-cyan-300 bg-cyan-950 px-1.5 py-0.2 rounded border border-cyan-800">
                              Otto Baseline
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-slate-300 mt-1">
                          <strong>Strategic Tradeoff: </strong> {opt.strategicTradeoff}
                        </div>
                        <div className="text-[11px] text-slate-400 mt-0.5">
                          <strong>Risk Profile: </strong> {opt.riskProfile}
                        </div>
                      </div>
                    </div>

                    {isSelected && (
                      <span className="text-xs font-mono font-bold text-emerald-400 flex items-center gap-1 shrink-0 bg-emerald-950/80 px-2 py-1 rounded border border-emerald-800">
                        <Check className="w-3.5 h-3.5" /> FOUNDER PREFERRED
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* DPO Export Modal */}
      {showDpoExportModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 text-cyan-400 font-mono font-bold text-sm">
                <Database className="w-4 h-4" />
                <span>DIRECT PREFERENCE OPTIMIZATION (DPO) TUPLES</span>
              </div>
              <button
                onClick={() => setShowDpoExportModal(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-300">
              Exported {dpoTuples.length} pairwise alignment tuples into local <code className="text-cyan-300">estate.db</code>. Ready for fine-tuning Otto baseline models without cloud egress charges.
            </p>

            <pre className="p-4 bg-slate-950 rounded-lg border border-slate-800 text-[11px] font-mono text-cyan-300 max-h-72 overflow-y-auto whitespace-pre-wrap">
              {JSON.stringify(dpoTuples, null, 2)}
            </pre>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowDpoExportModal(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-950 bg-cyan-400 hover:bg-cyan-300 rounded-lg cursor-pointer"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
