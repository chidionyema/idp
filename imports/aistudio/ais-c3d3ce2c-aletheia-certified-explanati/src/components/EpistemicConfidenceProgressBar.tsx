/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import {
  evaluateEpistemicConfidenceRobustness,
  type MathematicalRobustnessTier,
} from '../core/epistemicCalculus';

interface EpistemicConfidenceProgressBarProps {
  score: number;
  recordId: string;
  variant?: 'compact' | 'detailed';
}

function getTierStyles(tier: MathematicalRobustnessTier): {
  barFillClass: string;
  textClass: string;
  glyph: string;
  shortTierLabel: string;
} {
  switch (tier) {
    case 'IRREFUTABLE_ROBUSTNESS':
      return {
        barFillClass: 'bg-emerald-400',
        textClass: 'text-emerald-400',
        glyph: '●',
        shortTierLabel: 'High Robustness',
      };
    case 'BOUNDED_ROBUSTNESS':
      return {
        barFillClass: 'bg-cyan-400',
        textClass: 'text-cyan-300',
        glyph: '●',
        shortTierLabel: 'Bounded Robustness',
      };
    case 'FRAGILE_CORRESPONDENCE':
      return {
        barFillClass: 'bg-amber-400',
        textClass: 'text-amber-300',
        glyph: '▲',
        shortTierLabel: 'Fragile Robustness',
      };
    case 'CRITICAL_VULNERABILITY':
      return {
        barFillClass: 'bg-rose-500',
        textClass: 'text-rose-400',
        glyph: '✖',
        shortTierLabel: 'Critical Fragility',
      };
  }
}

export const EpistemicConfidenceProgressBar: React.FC<
  EpistemicConfidenceProgressBarProps
> = ({ score, recordId, variant = 'compact' }) => {
  const assessment = evaluateEpistemicConfidenceRobustness(score);
  const styles = getTierStyles(assessment.tier);
  const roundedPct = Math.round(assessment.percentage);

  if (variant === 'compact') {
    return (
      <div className="mt-2 pt-2 border-t border-slate-800/70 space-y-1.5">
        <div className="flex items-center justify-between gap-2 text-[11px] font-mono whitespace-nowrap">
          <span className="text-slate-400">Epistemic Confidence</span>
          <span className={`${styles.textClass} font-semibold tabular-nums`}>
            {styles.glyph} {assessment.score.toFixed(2)} ({assessment.percentage.toFixed(0)}%)
          </span>
        </div>
        <div
          role="progressbar"
          aria-label={`${recordId} epistemic_confidence_score mathematical robustness`}
          aria-valuenow={roundedPct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuetext={`${assessment.score.toFixed(2)} (${assessment.percentage.toFixed(1)}%) — ${assessment.label}`}
          className="h-2 w-full bg-slate-950 rounded-sm border border-slate-800/90 overflow-hidden"
        >
          <div
            style={{ width: `${assessment.percentage}%` }}
            className={`h-full ${styles.barFillClass} transition-all duration-150`}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[#090D16] border border-slate-800/90 rounded-md p-3.5 space-y-2">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono uppercase tracking-wider text-slate-300 font-semibold">
            Mathematical Robustness (epistemic_confidence_score)
          </span>
        </div>
        <div className="flex items-center gap-3 font-mono text-xs tabular-nums">
          <span className={`${styles.textClass} font-semibold`}>
            {styles.glyph} {assessment.label}
          </span>
          <span className="text-slate-100 font-bold text-sm">
            {assessment.score.toFixed(2)}{' '}
            <span className="text-slate-400 font-normal">
              ({assessment.percentage.toFixed(1)}%)
            </span>
          </span>
        </div>
      </div>

      <div
        role="progressbar"
        aria-label={`Active record ${recordId} epistemic_confidence_score mathematical robustness`}
        aria-valuenow={roundedPct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuetext={`${assessment.score.toFixed(2)} out of 1.00 (${assessment.percentage.toFixed(1)}%) — ${assessment.label}`}
        className="relative h-3.5 w-full bg-slate-950 rounded border border-slate-800 overflow-hidden"
      >
        {/* Reference threshold markers at 0.25, 0.55, 0.80 */}
        <div
          aria-hidden="true"
          style={{ left: '25%' }}
          className="absolute inset-y-0 w-px bg-slate-700/70 z-10"
        />
        <div
          aria-hidden="true"
          style={{ left: '55%' }}
          className="absolute inset-y-0 w-px bg-slate-700/70 z-10"
        />
        <div
          aria-hidden="true"
          style={{ left: '80%' }}
          className="absolute inset-y-0 w-px bg-slate-700/70 z-10"
        />
        <div
          style={{ width: `${assessment.percentage}%` }}
          className={`h-full ${styles.barFillClass} transition-all duration-150`}
        />
      </div>

      <div className="flex justify-between text-[11px] font-mono text-slate-400 tabular-nums">
        <span>0.00 (Refuted)</span>
        <span>0.25 (Fragile)</span>
        <span>0.55 (Bounded)</span>
        <span>0.80 (Certified Robust)</span>
        <span>1.00 (Irrefutable)</span>
      </div>
    </div>
  );
};
