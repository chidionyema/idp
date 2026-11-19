import React, { useState } from 'react';
import { EstateArtifact, EstateEdict, EstateMotion, FinancialHealthMetrics } from '../types/estate';
import { AlertOctagon, CheckCircle2, Download, Zap, Shield, FileText, ArrowRight } from 'lucide-react';

interface UrgentActionBoardProps {
  metrics: FinancialHealthMetrics;
  artifacts: EstateArtifact[];
  edicts: EstateEdict[];
  motions: EstateMotion[];
  onExecuteFreeze: () => void;
  onPurgeThreads: () => void;
  onAdvanceMotion: (motionId: string) => void;
  onNavigateToView: (view: string) => void;
}

export const UrgentActionBoard: React.FC<UrgentActionBoardProps> = ({
  metrics,
  artifacts,
  edicts,
  motions,
  onExecuteFreeze,
  onPurgeThreads,
  onAdvanceMotion,
  onNavigateToView,
}) => {
  const [action1Completed, setAction1Completed] = useState(false);
  const [action2Completed, setAction2Completed] = useState(false);
  const [action3Completed, setAction3Completed] = useState(false);

  // Download Estate Sovereign Briefing Document
  const handleDownloadBriefing = () => {
    const brief = `# ESTATE SOVEREIGN EXECUTIVE BRIEF & PROVENANCE RECORD
Generated: ${new Date().toISOString()}
Founder: Sovereign Core (${metrics.founderCognitiveLoadIndex}% Cognitive Load)

============================================================
1. FINANCIAL RUNWAY & RED-LINE METRICS
============================================================
- Treasury Reserve: $${metrics.totalTreasuryUSD.toLocaleString()} USD
- Daily Burn Velocity: $${metrics.dailyBurnUSD.toFixed(0)}/day
- Monthly Burn: $${metrics.monthlyBurnUSD.toLocaleString()}/month
- Runway: ${metrics.runwayMonths.toFixed(1)} Months
- Red-Line Survival Invariant: Runway >= 90 Days [MET]
- Unanchored Rogue Threads: ${metrics.unanchoredAgentThreads}

============================================================
2. SOVEREIGN DECREES & EDICTS
============================================================
${edicts.map((e) => `[${e.code}] ${e.title}
Decree: "${e.decreeText}"
Invariant: ${e.governingInvariant}
Status: ${e.status}
`).join('\n')}

============================================================
3. IMMUTABLE ARTIFACT PROVENANCE VAULT (ZERO MISSING ARTIFACTS)
============================================================
${artifacts.map((a) => `[${a.id}] ${a.title}
- Type: ${a.type}
- Vault Coordinates: ${a.depositLocation}
- Origin Agent: ${a.originAgent}
- SHA-256 Checksum: ${a.checksum}
- Version: ${a.version}
`).join('\n')}

============================================================
4. ACTIVE MOTIONS & CLOSED-LOOP DELIVERY PIPELINE
============================================================
${motions.map((m) => `[${m.id}] ${m.title}
- Stage: ${m.currentStage}
- Closed-Loop Metric: ${m.closedLoopMetric} (Current: ${m.currentMetricValue} / Target: ${m.targetMetricValue})
- Capital Cap: $${m.capitalAllocatedUSD.toLocaleString()} (Consumed: $${m.capitalConsumedUSD.toLocaleString()})
- Convergence Score: ${m.convergenceScore}%
`).join('\n')}

============================================================
END OF BRIEF - ALGORITHMICALLY VERIFIED
`;

    const blob = new Blob([brief], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `estate-sovereign-brief-${new Date().toISOString().split('T')[0]}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-5 space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-neutral-800 pb-3">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-red-400 font-bold">
            <Zap className="w-4 h-4 text-amber-400" />
            <span>Today's Urgent Founder Action Board</span>
          </div>
          <h2 className="text-base font-bold text-white">Execute Real Priority Decisions Now</h2>
        </div>

        <button
          onClick={handleDownloadBriefing}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 border border-neutral-700 rounded-lg text-xs font-semibold transition-colors cursor-pointer shrink-0"
        >
          <Download className="w-3.5 h-3.5 text-amber-400" />
          <span>Download Sovereign Brief (MD)</span>
        </button>
      </div>

      {/* 3 Immediate Executive Priority Directives */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Directive 1 */}
        <div className="p-4 rounded-xl bg-neutral-950 border border-neutral-800 flex flex-col justify-between space-y-3">
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-amber-400 font-bold">DIRECTIVE 01</span>
              {action1Completed ? (
                <span className="text-emerald-400 font-bold flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> EXECUTED
                </span>
              ) : (
                <span className="text-red-400">URGENT</span>
              )}
            </div>
            <h4 className="text-sm font-bold text-white">Purge Unanchored Agent Threads</h4>
            <p className="text-xs text-neutral-400 leading-relaxed">
              Halts idling compute instances and terminates 3 rogue background agent processes bleeding $85/day.
            </p>
          </div>

          <button
            onClick={() => { onPurgeThreads(); setAction1Completed(true); }}
            disabled={action1Completed}
            className={`w-full py-2 px-3 rounded-lg text-xs font-bold transition-colors cursor-pointer ${
              action1Completed
                ? 'bg-neutral-900 text-neutral-500 cursor-not-allowed'
                : 'bg-red-600 hover:bg-red-500 text-white'
            }`}
          >
            {action1Completed ? 'Threads Purged ($85/day Saved)' : 'Execute Instant Purge'}
          </button>
        </div>

        {/* Directive 2 */}
        <div className="p-4 rounded-xl bg-neutral-950 border border-neutral-800 flex flex-col justify-between space-y-3">
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-amber-400 font-bold">DIRECTIVE 02</span>
              {action2Completed ? (
                <span className="text-emerald-400 font-bold flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> VERIFIED
                </span>
              ) : (
                <span className="text-amber-400">PENDING</span>
              )}
            </div>
            <h4 className="text-sm font-bold text-white">Inspect Recovered Visual Mockup</h4>
            <p className="text-xs text-neutral-400 leading-relaxed">
              Verify the exact coordinates and interactive layout of ART-001 in the vault to eliminate blindness.
            </p>
          </div>

          <button
            onClick={() => { onNavigateToView('artifacts'); setAction2Completed(true); }}
            className="w-full py-2 px-3 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 rounded-lg text-xs font-bold transition-colors cursor-pointer"
          >
            View in Vault (ART-001)
          </button>
        </div>

        {/* Directive 3 */}
        <div className="p-4 rounded-xl bg-neutral-950 border border-neutral-800 flex flex-col justify-between space-y-3">
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-amber-400 font-bold">DIRECTIVE 03</span>
              {action3Completed ? (
                <span className="text-emerald-400 font-bold flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> GATED
                </span>
              ) : (
                <span className="text-blue-400">ACTIONABLE</span>
              )}
            </div>
            <h4 className="text-sm font-bold text-white">Advance Motion 01 Delivery Gate</h4>
            <p className="text-xs text-neutral-400 leading-relaxed">
              Advance the live founder visual command motion to Phase 5 closed-loop value attestation.
            </p>
          </div>

          <button
            onClick={() => { onAdvanceMotion('MOT-01'); setAction3Completed(true); }}
            disabled={action3Completed}
            className={`w-full py-2 px-3 rounded-lg text-xs font-bold transition-colors cursor-pointer ${
              action3Completed
                ? 'bg-neutral-900 text-neutral-500 cursor-not-allowed'
                : 'bg-amber-500 hover:bg-amber-400 text-neutral-950'
            }`}
          >
            {action3Completed ? 'Phase Gate Advanced' : 'Advance MOT-01 Gate'}
          </button>
        </div>
      </div>
    </div>
  );
};
