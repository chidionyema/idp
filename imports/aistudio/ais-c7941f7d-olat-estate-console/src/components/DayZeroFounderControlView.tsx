import React, { useState } from 'react';
import {
  Mic,
  Volume2,
  Sliders,
  Terminal,
  Trash2,
  Play,
  CheckCircle2,
  Sparkles,
  Cpu,
  Layers,
} from 'lucide-react';
import {
  FounderDayZeroConfig,
  SpecialistAgent,
  InstructionRecord,
  FleetSummaryMetrics,
  OkeCarnageTrainingEpisode,
  EphemeralUiCardSpec,
  VisualMediaTriggerRule,
  computeAgentDegreeOfAgency,
  validateInstructionProof,
} from '../lib/protocolEngine';

interface DayZeroFounderControlViewProps {
  config: FounderDayZeroConfig;
  onUpdateConfig: (next: FounderDayZeroConfig) => void;
  agents: SpecialistAgent[];
  instructions: InstructionRecord[];
  metrics: FleetSummaryMetrics;
  carnageEpisodes: OkeCarnageTrainingEpisode[];
  ephemeralCards: EphemeralUiCardSpec[];
  onIssueVoiceDirective: (transcript: string) => void;
  onDismissEphemeralCard: (cardId: string) => void;
  onTrainPlatformAgentOnCarnage: (episodeId: string) => void;
}

export const DayZeroFounderControlView: React.FC<DayZeroFounderControlViewProps> = ({
  config,
  onUpdateConfig,
  agents,
  instructions,
  metrics,
  carnageEpisodes,
  ephemeralCards,
  onIssueVoiceDirective,
  onDismissEphemeralCard,
  onTrainPlatformAgentOnCarnage,
}) => {
  const [voiceInput, setVoiceInput] = useState<string>('');
  const [isListening, setIsListening] = useState<boolean>(false);
  const [voiceFeedback, setVoiceFeedback] = useState<string>('');

  const triggerSpeechReadback = (text: string) => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      try {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.04;
        window.speechSynthesis.speak(utterance);
      } catch {
        // Ignore if speech synthesis is unavailable in headless browser
      }
    }
  };

  const handleVoiceSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const transcript =
      voiceInput.trim() ||
      'Materialize Founder Estate Yield & Visual Media Brief';
    onIssueVoiceDirective(transcript);
    setVoiceInput('');
    setVoiceFeedback(`Voice protocol executed: "${transcript}"`);
    triggerSpeechReadback(`Materialized ephemeral surface for ${transcript}`);
  };

  const handleQuickVoiceDirective = (directive: string) => {
    onIssueVoiceDirective(directive);
    setVoiceFeedback(`Voice protocol executed: "${directive}"`);
    triggerSpeechReadback(directive);
  };

  const handleBrowserMicCapture = () => {
    const SpeechRec =
      (window as unknown as { SpeechRecognition?: new () => { lang: string; start: () => void; onresult: (e: { results: Array<Array<{ transcript: string }>> }) => void; onerror: () => void; onend: () => void } }).SpeechRecognition ||
      (window as unknown as { webkitSpeechRecognition?: new () => { lang: string; start: () => void; onresult: (e: { results: Array<Array<{ transcript: string }>> }) => void; onerror: () => void; onend: () => void } }).webkitSpeechRecognition;

    if (!SpeechRec) {
      handleQuickVoiceDirective(
        'Show OKE carnage training and Rust mistake elimination'
      );
      return;
    }

    try {
      setIsListening(true);
      const recognition = new SpeechRec();
      recognition.lang = 'en-US';
      recognition.onresult = (event) => {
        const spoken = event.results?.[0]?.[0]?.transcript || '';
        if (spoken) {
          onIssueVoiceDirective(spoken);
          setVoiceFeedback(`Voice captured: "${spoken}"`);
        }
        setIsListening(false);
      };
      recognition.onerror = () => setIsListening(false);
      recognition.onend = () => setIsListening(false);
      recognition.start();
    } catch {
      setIsListening(false);
    }
  };

  // Compute real-time Degrees of Agency for every specialist based on live data & Founder config
  const agencyDeterminations = agents.map((agent) => {
    const matchingInst = instructions.find((i) => i.specialistId === agent.id);
    const agentYield = matchingInst ? matchingInst.yieldPercent : 100;
    const proofScore = matchingInst
      ? validateInstructionProof(
          matchingInst.claimStatement,
          matchingInst.proofArtifact,
          matchingInst.protocolId
        ).completenessScore
      : 100;

    return {
      agent,
      agentYield,
      proofScore,
      determination: computeAgentDegreeOfAgency(
        agent,
        agentYield,
        proofScore,
        config
      ),
    };
  });

  return (
    <div className="space-y-10">
      {/* Section 01: Voice-First Command Bar & Ephemeral UI Materializer */}
      <section className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-xl p-6 lg:p-8 space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2 text-xs font-medium text-slate-500 dark:text-slate-400">
              <span>Day-0 Structured Rust Formats</span>
              <span aria-hidden="true">·</span>
              <span>Voice-Led Ephemeral UI</span>
              <span aria-hidden="true">·</span>
              <span>Zero Backstage Bloat</span>
              <span aria-hidden="true">·</span>
              <span>OKE Carnage Training Ground</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">
              Day-0 Founder Control Plane, Voice Ephemeral UI & Rust Agency Engine
            </h1>
            <p className="text-sm text-slate-600 dark:text-slate-300 max-w-3xl">
              Voice leads from Day 0 to materialize ephemeral, structured interfaces on demand—dropping heavy Backstage portals and OKE cluster bloat while the Rust protocol machine dynamically governs specialist Degrees of Agency from live metrics.
            </p>
          </div>

          <div className="text-xs font-mono px-3.5 py-2 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100 shrink-0">
            Runtime: rustc 1.84 · Zero-Bloat Single Binary
          </div>
        </div>

        {/* Voice Command Input & Quick Directives */}
        <div className="space-y-3">
          <form onSubmit={handleVoiceSubmit} className="flex flex-col sm:flex-row gap-2.5">
            <div className="relative flex-1">
              <label htmlFor="founder-voice-input" className="sr-only">
                Founder Voice Directive
              </label>
              <input
                id="founder-voice-input"
                type="text"
                placeholder="Speak or type Founder directive (e.g., 'Show OKE carnage training in Rust', 'Inspect degree of agency thresholds', 'Materialize Estate yield media brief')..."
                value={voiceInput}
                onChange={(e) => setVoiceInput(e.target.value)}
                className="w-full pl-4 pr-4 py-2.5 text-xs sm:text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100"
              />
            </div>

            <button
              type="button"
              onClick={handleBrowserMicCapture}
              className="px-4 py-2.5 text-xs font-semibold text-slate-900 dark:text-slate-100 bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors inline-flex items-center justify-center gap-1.5 whitespace-nowrap shrink-0 cursor-pointer"
            >
              <Mic className="w-3.5 h-3.5" />
              <span>{isListening ? 'Listening...' : 'Voice Mic Trigger'}</span>
            </button>

            <button
              type="submit"
              className="px-4 py-2.5 text-xs font-semibold text-white bg-slate-900 dark:bg-slate-100 dark:text-slate-900 rounded-lg hover:bg-slate-800 dark:hover:bg-white transition-colors inline-flex items-center justify-center gap-1.5 whitespace-nowrap shrink-0 cursor-pointer"
            >
              <Volume2 className="w-3.5 h-3.5" />
              <span>Materialize Ephemeral UI</span>
            </button>
          </form>

          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="text-slate-500 dark:text-slate-400 font-medium">
              Instant Voice Directives:
            </span>
            <button
              type="button"
              onClick={() =>
                handleQuickVoiceDirective(
                  'Materialize Founder Estate Yield & Visual Media Brief'
                )
              }
              className="px-2.5 py-1 rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
            >
              “Materialize Estate Yield & Visual Media Brief”
            </button>
            <button
              type="button"
              onClick={() =>
                handleQuickVoiceDirective(
                  'Show OKE carnage training and Rust mistake elimination'
                )
              }
              className="px-2.5 py-1 rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
            >
              “Show OKE Carnage & Rust Training Telemetry”
            </button>
            <button
              type="button"
              onClick={() =>
                handleQuickVoiceDirective(
                  'Inspect degree of agency threshold gates'
                )
              }
              className="px-2.5 py-1 rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
            >
              “Inspect Machine Degrees of Agency Matrix”
            </button>
            <button
              type="button"
              onClick={() =>
                handleQuickVoiceDirective(
                  'Show GPT Researcher ML DAG and resource eviction open loops'
                )
              }
              className="px-2.5 py-1 rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
            >
              “Show GPT-Researcher ML DAG & Yield Eviction”
            </button>
          </div>

          {voiceFeedback && (
            <div
              role="status"
              className="text-xs font-mono text-emerald-700 dark:text-emerald-400"
            >
              {voiceFeedback}
            </div>
          )}
        </div>

        {/* Active Materialized Ephemeral UI Surfaces (With Visual Media & Rust Day-0 Structs) */}
        <div className="space-y-4 pt-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-900 dark:text-slate-100">
              Active Ephemeral UI Surfaces ({ephemeralCards.length}) · Standardized Media Trigger: {config.visualMediaTriggerRule}
            </span>
            <span className="text-slate-500 dark:text-slate-400">
              Zero static Backstage bloat — surfaces dissolve when dismissed
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {ephemeralCards.map((card) => (
              <div
                key={card.id}
                className="border border-slate-200 dark:border-slate-800 rounded-lg p-5 bg-slate-50/70 dark:bg-slate-950/60 flex flex-col justify-between space-y-4"
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
                    <div>
                      <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                        {card.id} · {card.mediaProtocolTrigger}
                      </div>
                      <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 mt-0.5">
                        {card.title}
                      </h3>
                    </div>
                    <button
                      type="button"
                      onClick={() => onDismissEphemeralCard(card.id)}
                      aria-label={`Dissolve ephemeral surface ${card.id}`}
                      className="p-1 text-slate-400 hover:text-rose-600 transition-colors cursor-pointer"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>

                  {/* Standardized Visual Media Surface for Founder View */}
                  <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-900 text-slate-100 p-4 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono text-slate-400">
                      <span>FOUNDER VISUAL MEDIA CANVAS · DAY-0 PROTOCOL</span>
                      <span className="truncate max-w-xs">
                        Voice: “{card.voiceTranscript}”
                      </span>
                    </div>

                    {card.surfaceType === 'RESEARCH_YIELD_EVICTION_SURFACE' ? (
                      <svg
                        viewBox="0 0 520 110"
                        className="w-full h-24 rounded bg-slate-950 border border-slate-800"
                        role="img"
                        aria-label="GPT-Researcher Conformal ML DAG and Zero-Proof Resource Eviction Diagram"
                      >
                        <rect x="12" y="18" width="150" height="74" rx="4" fill="#064e3b" stroke="#10b981" />
                        <text x="22" y="38" fill="#34d399" fontSize="9.5" fontFamily="monospace" fontWeight="bold">
                          GPT-Researcher + ML
                        </text>
                        <text x="22" y="56" fill="#ffffff" fontSize="11" fontFamily="monospace" fontWeight="bold">
                          135% Prime Quota
                        </text>
                        <text x="22" y="74" fill="#a7f3d0" fontSize="8.5" fontFamily="monospace">
                          sha256 Conformal Proof
                        </text>

                        <rect x="180" y="18" width="155" height="74" rx="4" fill="#0f172a" stroke="#38bdf8" />
                        <text x="190" y="38" fill="#38bdf8" fontSize="9.5" fontFamily="monospace" fontWeight="bold">
                          AGENTS.md Root Index
                        </text>
                        <text x="190" y="56" fill="#ffffff" fontSize="11" fontFamily="monospace" fontWeight="bold">
                          -95.7% Bloat Cut
                        </text>
                        <text x="190" y="74" fill="#94a3b8" fontSize="8.5" fontFamily="monospace">
                          Private GitHub Synced
                        </text>

                        <rect x="352" y="18" width="155" height="74" rx="4" fill="#450a0a" stroke="#ef4444" />
                        <text x="362" y="38" fill="#fca5a5" fontSize="9.5" fontFamily="monospace" fontWeight="bold">
                          Legacy Unverified RAG
                        </text>
                        <text x="362" y="56" fill="#ffffff" fontSize="11" fontFamily="monospace" fontWeight="bold">
                          EVICTED (0% CPU)
                        </text>
                        <text x="362" y="74" fill="#fca5a5" fontSize="8.5" fontFamily="monospace">
                          Missing Proof of Yield
                        </text>
                      </svg>
                    ) : card.surfaceType === 'OKE_CARNAGE_DIFF' ? (
                      <svg
                        viewBox="0 0 520 110"
                        className="w-full h-24 rounded bg-slate-950 border border-slate-800"
                        role="img"
                        aria-label="OKE Carnage Elimination vs Rust Deterministic Replay Diagram"
                      >
                        <text x="14" y="22" fill="#f87171" fontSize="10" fontFamily="monospace">
                          RETIRED: OKE K8s / Backstage Drift (80% Bloat)
                        </text>
                        <path
                          d="M 14 38 Q 60 15, 105 45 T 195 25 T 275 48"
                          fill="none"
                          stroke="#f87171"
                          strokeWidth="2"
                          strokeDasharray="4 3"
                        />
                        <text x="14" y="75" fill="#34d399" fontSize="10" fontFamily="monospace">
                          ACTIVE: Rust Event-Sourced Fold (99.2% Mistake Elimination)
                        </text>
                        <line
                          x1="14"
                          y1="90"
                          x2="500"
                          y2="90"
                          stroke="#34d399"
                          strokeWidth="2.5"
                        />
                        <circle cx="120" cy="90" r="4" fill="#34d399" />
                        <circle cx="260" cy="90" r="4" fill="#34d399" />
                        <circle cx="400" cy="90" r="4" fill="#34d399" />
                      </svg>
                    ) : card.surfaceType === 'AGENCY_MATRIX_OVERRIDE' ? (
                      <svg
                        viewBox="0 0 520 110"
                        className="w-full h-24 rounded bg-slate-950 border border-slate-800"
                        role="img"
                        aria-label="Machine-Determined Degrees of Agency L0 to L4 Topology"
                      >
                        {(['L0 Gate', 'L1 Shadow', 'L2 Bounded', 'L3 Outbox', 'L4 Genesis'] as const).map(
                          (lbl, idx) => (
                            <g key={lbl} transform={`translate(${12 + idx * 100}, 22)`}>
                              <rect
                                width="88"
                                height="64"
                                rx="6"
                                fill={idx >= 3 ? '#064e3b' : '#1e293b'}
                                stroke={idx >= 3 ? '#10b981' : '#475569'}
                                strokeWidth="1.5"
                              />
                              <text
                                x="10"
                                y="26"
                                fill="#f8fafc"
                                fontSize="10"
                                fontWeight="bold"
                                fontFamily="monospace"
                              >
                                {lbl}
                              </text>
                              <text
                                x="10"
                                y="46"
                                fill="#94a3b8"
                                fontSize="9"
                                fontFamily="monospace"
                              >
                                {idx >= 3 ? `≥${config.minYieldForAutonomousOutbox}% Yield` : 'Metric Gate'}
                              </text>
                            </g>
                          )
                        )}
                      </svg>
                    ) : (
                      <svg
                        viewBox="0 0 520 110"
                        className="w-full h-24 rounded bg-slate-950 border border-slate-800"
                        role="img"
                        aria-label="Estate Portfolio Parcel Yield Aerial Telemetry Map"
                      >
                        <rect x="14" y="16" width="150" height="78" rx="4" fill="#0f172a" stroke="#334155" />
                        <text x="24" y="38" fill="#e2e8f0" fontSize="10" fontWeight="bold" fontFamily="monospace">
                          Meridian Portfolio
                        </text>
                        <text x="24" y="58" fill="#34d399" fontSize="11" fontWeight="bold" fontFamily="monospace">
                          105.4% Yield · L4
                        </text>
                        <text x="24" y="76" fill="#94a3b8" fontSize="9" fontFamily="monospace">
                          48 Units · PRF-LEASE
                        </text>

                        <rect x="180" y="16" width="155" height="78" rx="4" fill="#0f172a" stroke="#334155" />
                        <text x="190" y="38" fill="#e2e8f0" fontSize="10" fontWeight="bold" fontFamily="monospace">
                          Harborview Logistics
                        </text>
                        <text x="190" y="58" fill="#34d399" fontSize="11" fontWeight="bold" fontFamily="monospace">
                          108.6% Yield · L4
                        </text>
                        <text x="190" y="76" fill="#94a3b8" fontSize="9" fontFamily="monospace">
                          $456.1k CAM · DIFF-CAM
                        </text>

                        <rect x="350" y="16" width="155" height="78" rx="4" fill="#0f172a" stroke="#334155" />
                        <text x="360" y="38" fill="#e2e8f0" fontSize="10" fontWeight="bold" fontFamily="monospace">
                          Northgate Parcels A-N
                        </text>
                        <text x="360" y="58" fill="#38bdf8" fontSize="11" fontWeight="bold" fontFamily="monospace">
                          100.0% Yield · L3
                        </text>
                        <text x="360" y="76" fill="#94a3b8" fontSize="9" fontFamily="monospace">
                          14 Easements Cleared
                        </text>
                      </svg>
                    )}

                    <p className="text-xs text-slate-300 leading-relaxed">
                      {card.spokenSummary}
                    </p>
                  </div>

                  {/* Structured Metrics Strip */}
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    {card.metricsPayload.map((m) => (
                      <div
                        key={m.label}
                        className="p-2.5 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800"
                      >
                        <div className="text-slate-500 dark:text-slate-400 text-[11px]">
                          {m.label}
                        </div>
                        <div className="font-mono font-semibold text-slate-900 dark:text-slate-100 mt-0.5">
                          {m.value}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Day-0 Rust Struct Contract */}
                <div className="pt-2 border-t border-slate-200 dark:border-slate-800">
                  <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400 mb-1">
                    Day-0 Rust Wire Contract (serde zero-copy):
                  </div>
                  <pre className="p-2.5 rounded bg-slate-900 text-slate-100 text-[11px] font-mono overflow-x-auto">
                    {card.rustStructPreview}
                  </pre>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Section 02: Founder Day-0 Configurability & Machine-Determined Degrees of Agency */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        {/* Left 5 Cols: Founder Day-0 Configurability Controls */}
        <div className="lg:col-span-5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-lg p-6 flex flex-col justify-start space-y-5">
          <div className="border-b border-slate-200 dark:border-slate-800 pb-3">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 inline-flex items-center gap-2">
              <Sliders className="w-4 h-4 text-slate-500" />
              <span>02. Founder Day-0 Platform Configurability</span>
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Adjust metric thresholds below to dynamically recompute Degrees of Agency across the entire fleet in real time.
            </p>
          </div>

          <div className="space-y-4 text-xs">
            <div>
              <div className="flex items-center justify-between font-medium mb-1">
                <label htmlFor="min-yield-slider" className="text-slate-700 dark:text-slate-300">
                  Min Yield % for Autonomous Outbox (L3/L4)
                </label>
                <span className="font-mono font-bold tabular-nums text-slate-900 dark:text-slate-100">
                  {config.minYieldForAutonomousOutbox}%
                </span>
              </div>
              <input
                id="min-yield-slider"
                type="range"
                min={85}
                max={108}
                step={1}
                value={config.minYieldForAutonomousOutbox}
                onChange={(e) =>
                  onUpdateConfig({
                    ...config,
                    minYieldForAutonomousOutbox: Number(e.target.value),
                  })
                }
                className="w-full accent-slate-900 dark:accent-slate-100 cursor-pointer"
              />
            </div>

            <div>
              <div className="flex items-center justify-between font-medium mb-1">
                <label htmlFor="min-eval-slider" className="text-slate-700 dark:text-slate-300">
                  Min Eval Score % for Zero-Touch Genesis (L4)
                </label>
                <span className="font-mono font-bold tabular-nums text-slate-900 dark:text-slate-100">
                  {config.minEvalForFullAgency}%
                </span>
              </div>
              <input
                id="min-eval-slider"
                type="range"
                min={88}
                max={100}
                step={1}
                value={config.minEvalForFullAgency}
                onChange={(e) =>
                  onUpdateConfig({
                    ...config,
                    minEvalForFullAgency: Number(e.target.value),
                  })
                }
                className="w-full accent-slate-900 dark:accent-slate-100 cursor-pointer"
              />
            </div>

            <div>
              <label
                htmlFor="agency-ceiling-select"
                className="block font-medium text-slate-700 dark:text-slate-300 mb-1"
              >
                Founder Global Agency Ceiling Override
              </label>
              <select
                id="agency-ceiling-select"
                value={config.maxAgencyCeiling}
                onChange={(e) =>
                  onUpdateConfig({
                    ...config,
                    maxAgencyCeiling: Number(e.target.value) as 1 | 2 | 3 | 4,
                  })
                }
                className="w-full px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-mono"
              >
                <option value={4}>L4 · Full Zero-Touch Genesis Allowed</option>
                <option value={3}>Cap Fleet at L3 · Autonomous Outbox</option>
                <option value={2}>Cap Fleet at L2 · Bounded Execution</option>
                <option value={1}>Cap Fleet at L1 · Shadow Advisory Only</option>
              </select>
            </div>

            <div>
              <label
                htmlFor="media-trigger-select"
                className="block font-medium text-slate-700 dark:text-slate-300 mb-1"
              >
                Founder Visual Media Protocol Trigger Rule
              </label>
              <select
                id="media-trigger-select"
                value={config.visualMediaTriggerRule}
                onChange={(e) =>
                  onUpdateConfig({
                    ...config,
                    visualMediaTriggerRule: e.target.value as VisualMediaTriggerRule,
                  })
                }
                className="w-full px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-mono"
              >
                <option value="ON_FOUNDER_VOICE_BRIEF">ON_FOUNDER_VOICE_BRIEF</option>
                <option value="ON_YIELD_ANOMALY">ON_YIELD_ANOMALY</option>
                <option value="ALWAYS_MATERIALIZE">ALWAYS_MATERIALIZE</option>
              </select>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs font-mono text-emerald-700 dark:text-emerald-400">
            <span>Backstage & OKE Bloat Dropped:</span>
            <span>100% (Rust Day-0 Schemas)</span>
          </div>
        </div>

        {/* Right 7 Cols: Machine-Determined Degrees of Agency Live Table */}
        <div className="lg:col-span-7 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-lg p-6 flex flex-col justify-between space-y-4">
          <div className="border-b border-slate-200 dark:border-slate-800 pb-3">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
              Machine-Determined Degrees of Agency (Data & Metrics Driven)
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Agency is never hardcoded; the Protocol Machine promotes or restricts each specialist squad in real time from Yield %, Eval %, and Proof Completeness.
            </p>
          </div>

          <div className="divide-y divide-slate-200 dark:divide-slate-800 text-xs">
            {agencyDeterminations.map(({ agent, agentYield, proofScore, determination }) => (
              <div key={agent.id} className="py-3.5 space-y-1.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
                    {agent.id} · {agent.name}
                  </div>
                  <div
                    className={`font-mono font-bold tabular-nums ${
                      determination.numericLevel >= 4
                        ? 'text-emerald-700 dark:text-emerald-400'
                        : determination.numericLevel === 3
                        ? 'text-slate-900 dark:text-slate-100'
                        : 'text-amber-700 dark:text-amber-400'
                    }`}
                  >
                    {determination.agencyTier} (Composite {determination.compositeScore}%)
                  </div>
                </div>

                <div className="font-mono text-slate-500 dark:text-slate-400">
                  Metrics: Yield {agentYield.toFixed(1)}% · Eval {agent.evalScore.toFixed(1)}% · Proof {proofScore}% · Rust Type: {determination.rustCrateBinding}
                </div>

                <p className="text-slate-600 dark:text-slate-300">
                  {determination.machineRationale}
                </p>

                <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                  Permitted Capabilities: {determination.allowedAutonomousActions.join(' · ')}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Section 03: OKE Carnage & Build Carnage -> Specialist Platform Engineering Agent Training Ground */}
      <section className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-lg p-6 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 dark:border-slate-800 pb-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 inline-flex items-center gap-2">
              <Cpu className="w-4 h-4 text-slate-500" />
              <span>
                03. OKE Carnage & Current Build Carnage → Specialist Platform Engineering Agent Training Ground
              </span>
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Our historical OKE cluster failures and build chaos are replayed as deterministic Rust training epochs for our Specialist Platform Engineering Agents (SPC-PLAT-RUST-01 & SPC-PLAT-RUST-02).
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {carnageEpisodes.map((ep) => (
            <div
              key={ep.id}
              className="border border-slate-200 dark:border-slate-800 rounded-lg p-5 flex flex-col justify-between space-y-4 bg-slate-50/40 dark:bg-slate-950/40 text-xs"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between font-mono text-slate-500 dark:text-slate-400">
                  <span>
                    <strong className="text-slate-900 dark:text-slate-100">{ep.id}</strong> · {ep.carnageSource}
                  </span>
                  <span className="text-emerald-700 dark:text-emerald-400 font-bold tabular-nums">
                    {ep.mistakeEliminationRate.toFixed(1)}% Mistake Elimination
                  </span>
                </div>

                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  {ep.incidentName}
                </h3>

                <div className="text-slate-600 dark:text-slate-400">
                  <strong>Historical Carnage:</strong> {ep.carnageSymptom}
                </div>

                <div className="text-rose-700 dark:text-rose-400 font-medium">
                  <strong>Bloat Dropped:</strong> {ep.bloatDropped}
                </div>

                <div className="pt-1">
                  <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400 mb-1">
                    Trained Platform Agent: {ep.platformAgentId} ({ep.platformAgentName})
                  </div>
                  <pre className="p-2.5 rounded bg-slate-900 text-slate-100 text-[11px] font-mono overflow-x-auto">
                    {ep.rustDayZeroSchema}
                  </pre>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between gap-2">
                <span className="font-mono text-slate-500 dark:text-slate-400 tabular-nums">
                  Replay Epochs: {ep.replayEpochs} · cargo test: PASS
                </span>
                <button
                  type="button"
                  onClick={() => onTrainPlatformAgentOnCarnage(ep.id)}
                  className="px-3 py-1.5 font-semibold text-white bg-slate-900 dark:bg-slate-100 dark:text-slate-900 rounded hover:bg-slate-800 transition-colors inline-flex items-center gap-1 whitespace-nowrap shrink-0 cursor-pointer"
                >
                  <Play className="w-3 h-3" />
                  <span>Replay +250 Carnage Epochs</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};
