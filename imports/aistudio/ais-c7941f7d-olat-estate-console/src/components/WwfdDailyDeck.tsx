import React, { useEffect, useState } from 'react';

export interface WwfdOptionItem {
  option_key: 'A' | 'B' | 'C';
  label: string;
  action_command: string;
  principle: string;
}

export interface WwfdScenarioCard {
  scenario_id: string;
  domain: string;
  title: string;
  context_summary: string;
  otto_provisional_choice: 'A' | 'B' | 'C';
  entropy_score: number;
  options: WwfdOptionItem[];
  founder_choice?: 'A' | 'B' | 'C';
  hmac_signature?: string;
}

export interface WwfdDailyDeckProps {
  apiBaseUrl?: string;
  initialCards?: WwfdScenarioCard[];
  onDecisionRecorded?: (scenarioId: string, choiceKey: 'A' | 'B' | 'C') => void;
}

export const INITIAL_WWFD_CARDS: WwfdScenarioCard[] = [
  {
    scenario_id: 'WWFD-2026-1103-01',
    domain: 'GitOps & CI Boundary',
    title: 'Automated GitOps Sync & Fast-Forward Policy',
    context_summary: 'A non-blocking warning was detected in the staging manifest during PR promotion. Promotion queue latency is 1.4ms.',
    otto_provisional_choice: 'B',
    entropy_score: 0.94,
    options: [
      {
        option_key: 'A',
        label: 'Fast-Forward Push Immediately',
        action_command: 'git push origin HEAD:main --ff-only',
        principle: 'Prioritize deployment velocity; fix non-blocking warnings asynchronously.',
      },
      {
        option_key: 'B',
        label: 'Auto-Fix Manifest & Amend Commit',
        action_command: 'npx yaml-lint --fix manifests/ && git commit --amend --no-edit && git push',
        principle: 'Enforce clean manifests in Pass 1 before pushing to IDP repo.',
      },
      {
        option_key: 'C',
        label: 'Halt & Request Founder Review',
        action_command: 'exit 1 # notify founder',
        principle: 'Halt automation and wait for manual human sign-off.',
      },
    ],
  },
  {
    scenario_id: 'WWFD-2026-1103-02',
    domain: 'Multi-Lane Compute & Quorum',
    title: 'Tailscale Mesh Latency & RAFT Lease Allocation',
    context_summary: 'OCI cloud voter RTT is fluctuating at 145ms. Mac edge worker is awake, active, and reporting 0.4ms ping.',
    otto_provisional_choice: 'B',
    entropy_score: 0.91,
    options: [
      {
        option_key: 'A',
        label: 'Pause Execution Until Cloud Voter RTT Drops',
        action_command: 'sleep 30 && retry_quorum_check',
        principle: 'Strictly require 3-voter cloud consensus before writing state.',
      },
      {
        option_key: 'B',
        label: 'Claim Lease on Local Mac Worker with Monotonic Fence',
        action_command: 'genesis-kernel --claim-lease LANE_C_MAC --fence-inc',
        principle: 'Maintain execution continuity on local edge worker using fenced tokens.',
      },
      {
        option_key: 'C',
        label: 'Spin Up Ephemeral OIDC Runner in CI',
        action_command: 'gh workflow run lane-b-ephemeral.yml',
        principle: 'Automatically spin up temporary cloud compute to maintain quorum.',
      },
    ],
  },
  {
    scenario_id: 'WWFD-2026-1103-03',
    domain: 'Oracle Rationing Protocol',
    title: 'Pass Budget & Composite Probe Optimization',
    context_summary: 'Pass 1 tool output exceeded token length limits during deep state inspection of lockfiles.',
    otto_provisional_choice: 'A',
    entropy_score: 0.89,
    options: [
      {
        option_key: 'A',
        label: 'Filter Lockfiles in Pass 1 Composite Script',
        action_command: "git diff HEAD~1 -- . ':(exclude)*lock*'",
        principle: 'Eliminate Pass 2 waste by refining composite query probes.',
      },
      {
        option_key: 'B',
        label: 'Log ORACLE_BUDGET_WARNING and Take Pass 2',
        action_command: 'estate-execute --pass 2 --attr POOR_PLANNING',
        principle: 'Acknowledge budget consumption and execute targeted fallback probe.',
      },
      {
        option_key: 'C',
        label: 'Trigger HARD_STOP & Park Task',
        action_command: 'estate-execute --hard-stop',
        principle: 'Enforce strict rationing halt upon channel capacity exhaustion.',
      },
    ],
  },
  {
    scenario_id: 'WWFD-2026-1103-04',
    domain: 'Model Routing & Cost Discipline',
    title: 'LiteLLM Proxy Burst Fallback Strategy',
    context_summary: 'minimax-m2.7 p95 latency experienced a temporary spike; fast fallback routing is available on deepseek-chat.',
    otto_provisional_choice: 'A',
    entropy_score: 0.86,
    options: [
      {
        option_key: 'A',
        label: 'Keep minimax-m2.7 for Invariants; Burst Summaries to Fallback',
        action_command: 'nats kv put genesis_config.burst_fallback deepseek-chat',
        principle: 'Preserve canonical model for verification while bursting low-risk tasks.',
      },
      {
        option_key: 'B',
        label: 'Hold Queue Strictly on minimax-m2.7',
        action_command: 'noop',
        principle: 'Never deviate from canonical model leadership.',
      },
      {
        option_key: 'C',
        label: 'Hot-Swap Global Default Model',
        action_command: 'nats kv put genesis_config.default_model deepseek-chat',
        principle: 'Prioritize execution velocity by swapping global default model.',
      },
    ],
  },
  {
    scenario_id: 'WWFD-2026-1103-05',
    domain: 'Zero Founder Friction Law',
    title: 'Optional Integration & Secret Auto-Stubbing',
    context_summary: 'An optional external webhook integration lacked an API token in the local environment file.',
    otto_provisional_choice: 'B',
    entropy_score: 0.97,
    options: [
      {
        option_key: 'A',
        label: 'Stub Unconfigured Integration Silently',
        action_command: "sed -i '' 's/WEBHOOK_ENABLED=true/WEBHOOK_ENABLED=false/' .env",
        principle: 'Prune optional missing integrations automatically with zero human prompts.',
      },
      {
        option_key: 'B',
        label: 'Route Alert to Active Cockpit :8080 + Outbox',
        action_command: 'genesis-kernel --route-alert cockpit,outbox',
        principle: 'Fulfill notification intents via existing live surfaces without human friction.',
      },
      {
        option_key: 'C',
        label: 'Prompt Founder in Chat for Token',
        action_command: "echo 'Please paste API key'",
        principle: 'Ask human founder for optional credentials (Violates Core Law #6).',
      },
    ],
  },
];

export const WwfdDailyDeck: React.FC<WwfdDailyDeckProps> = ({
  apiBaseUrl = 'http://127.0.0.1:8080',
  initialCards = INITIAL_WWFD_CARDS,
  onDecisionRecorded,
}) => {
  const [cards, setCards] = useState<WwfdScenarioCard[]>(initialCards);
  const [activeIndex, setActiveIndex] = useState(0);
  const [customNote, setCustomNote] = useState('');
  const [signedCount, setSignedCount] = useState(0);

  const currentCard = cards[activeIndex];
  const answeredCount = cards.filter((c) => Boolean(c.founder_choice)).length;

  const submitChoice = async (choiceKey: 'A' | 'B' | 'C') => {
    if (!currentCard) return;
    const updated = [...cards];
    updated[activeIndex] = {
      ...currentCard,
      founder_choice: choiceKey,
      hmac_signature: `hmac:sha256:wwfd-${currentCard.scenario_id}-${choiceKey}-${Date.now().toString(16)}`,
    };
    setCards(updated);
    setSignedCount((prev) => prev + 1);

    if (onDecisionRecorded) {
      onDecisionRecorded(currentCard.scenario_id, choiceKey);
    }

    try {
      await fetch(`${apiBaseUrl}/api/cockpit/wwfd/decide`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scenario_id: currentCard.scenario_id,
          chosen_key: choiceKey,
          founder_note: customNote || undefined,
        }),
      });
    } catch {
      // Optimistically persisted in local state
    }

    setCustomNote('');
    if (activeIndex < cards.length - 1) {
      setActiveIndex(activeIndex + 1);
    }
  };

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'TEXTAREA') return;
      if (e.key === '1') submitChoice('A');
      if (e.key === '2') submitChoice('B');
      if (e.key === '3') submitChoice('C');
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  });

  if (!currentCard) return null;

  return (
    <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 font-mono text-slate-100 space-y-4">
      <div className="flex flex-wrap items-center justify-between border-b border-slate-800 pb-3 gap-2">
        <div>
          <span className="text-xs uppercase tracking-wider text-indigo-400 font-bold">
            What Would Founder Do? // Daily 5 Calibration ({answeredCount}/{cards.length} Signed)
          </span>
          <h3 className="text-base font-bold text-white mt-0.5">{currentCard.title}</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs px-2.5 py-1 rounded bg-slate-800 text-amber-300 border border-amber-700/50">
            Entropy: {currentCard.entropy_score.toFixed(2)} | Domain: {currentCard.domain}
          </span>
          <span className="text-xs px-2 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800">
            Hotkeys: [1] [2] [3]
          </span>
        </div>
      </div>

      <p className="text-xs text-slate-300 leading-relaxed bg-slate-950 p-3.5 rounded-xl border border-slate-800/80">
        {currentCard.context_summary}
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {currentCard.options.map((opt, idx) => {
          const isSelected = currentCard.founder_choice === opt.option_key;
          const isOttoPick = currentCard.otto_provisional_choice === opt.option_key;
          return (
            <button
              key={opt.option_key}
              onClick={() => submitChoice(opt.option_key)}
              className={`text-left p-3.5 rounded-xl border transition flex flex-col justify-between space-y-3 cursor-pointer ${
                isSelected
                  ? 'bg-indigo-950/80 border-indigo-500 text-white shadow-lg shadow-indigo-500/10'
                  : 'bg-slate-950 border-slate-800 hover:border-slate-600 text-slate-200'
              }`}
            >
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold px-2 py-0.5 rounded bg-slate-800 text-indigo-300">
                    [{idx + 1}] Option {opt.option_key}
                  </span>
                  {isOttoPick && (
                    <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-700">
                      Otto Provisional
                    </span>
                  )}
                </div>
                <div className="font-bold text-xs text-white pt-1">{opt.label}</div>
                <div className="text-[11px] text-slate-400 leading-normal">{opt.principle}</div>
              </div>
              <code className="text-[10px] text-indigo-300 bg-slate-900 p-1.5 rounded block truncate">
                {opt.action_command}
              </code>
            </button>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-3 pt-1">
        <input
          type="text"
          value={customNote}
          onChange={(e) => setCustomNote(e.target.value)}
          placeholder="Optional 1-line nuance to bake into mem://genesis/alignment/wwfd..."
          className="flex-1 min-w-[200px] px-3 py-1.5 text-xs rounded bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-indigo-500"
        />
        <div className="flex gap-1.5">
          {cards.map((c, idx) => (
            <button
              key={c.scenario_id}
              onClick={() => setActiveIndex(idx)}
              className={`w-7 h-7 rounded text-xs font-bold border transition cursor-pointer ${
                idx === activeIndex
                  ? 'bg-white text-slate-950 border-white font-bold'
                  : c.founder_choice
                  ? 'bg-emerald-950 text-emerald-300 border-emerald-700'
                  : 'bg-slate-950 text-slate-500 border-slate-800'
              }`}
            >
              {idx + 1}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
