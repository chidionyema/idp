import React, { useState, useEffect, useMemo } from 'react';
import {
  Volume2,
  Square,
  Copy,
  Check,
  Download,
  ArrowUpRight,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
} from 'lucide-react';
import {
  simulateAsymmetricAcademyEconomics,
  type GenesisAcademyState,
  type HumanLearningLensId,
  type InteractiveLabId,
  type LabEvaluationResult,
} from '../engine/beastGovernor';
import {
  speakLiveEstateHeadline,
  stopAllSovereignSpeech,
  playSovereignChime,
} from '../utils/sovereignAudio';

interface GenesisAcademyViewProps {
  initialAcademy: GenesisAcademyState;
  onRefreshState: () => Promise<void>;
  onDeepLinkNavigate: (deepLinkHash: string) => void;
}

export const GenesisAcademyView: React.FC<GenesisAcademyViewProps> = ({
  initialAcademy,
  onRefreshState,
  onDeepLinkNavigate,
}) => {
  const [academy, setAcademy] = useState<GenesisAcademyState>(initialAcademy);
  const [activeSparkId, setActiveSparkId] = useState<string>(
    initialAcademy.sparks[0]?.sparkId ?? 'SPARK-01'
  );
  const [selectedOptionBySpark, setSelectedOptionBySpark] = useState<Record<string, number>>({});
  const [sparkFeedback, setSparkFeedback] = useState<{
    sparkId: string;
    passed: boolean;
    message: string;
  } | null>(null);

  // Two-Zone Live Sandbox State
  const [activeLabId, setActiveLabId] = useState<InteractiveLabId>('LAB_OMEGA_ROBOT_FORCE');
  const initialLab =
    initialAcademy.labs.find((l) => l.labId === 'LAB_OMEGA_ROBOT_FORCE') ?? initialAcademy.labs[0];
  const [sliderValue, setSliderValue] = useState<number>(14);
  const [secondaryToggle, setSecondaryToggle] = useState<boolean>(
    initialLab?.defaultSecondaryToggle ?? true
  );
  const [latestLabReceipt, setLatestLabReceipt] = useState<LabEvaluationResult | null>(
    initialAcademy.learner.recentLabReceipts[0] ?? null
  );
  const [labBusy, setLabBusy] = useState(false);

  // Audio & Copy states
  const [speakingSparkId, setSpeakingSparkId] = useState<string | null>(null);
  const [copiedSparkId, setCopiedSparkId] = useState<string | null>(null);
  const [copiedVerifyCmd, setCopiedVerifyCmd] = useState(false);

  // Interactive Venture Revenue & Gross Margin Simulator State
  const [freeLearnersMonthly, setFreeLearnersMonthly] = useState<number>(
    initialAcademy.defaultRevenueModel.input.freeSocialLearnersMonthly
  );
  const [proConversionPct, setProConversionPct] = useState<number>(
    initialAcademy.defaultRevenueModel.input.proBuilderConversionPct
  );
  const [enterpriseSeats, setEnterpriseSeats] = useState<number>(
    initialAcademy.defaultRevenueModel.input.enterpriseSeatsAnnual
  );
  const [verifiedHiresMonthly, setVerifiedHiresMonthly] = useState<number>(
    initialAcademy.defaultRevenueModel.input.verifiedHiresMonthly
  );

  // Credential Hash Inspector
  const [verifyInputSha, setVerifyInputSha] = useState<string>('');
  const [verifyFeedback, setVerifyFeedback] = useState<{
    valid: boolean;
    message: string;
  } | null>(null);

  useEffect(() => {
    setAcademy(initialAcademy);
  }, [initialAcademy]);

  useEffect(() => {
    return () => {
      stopAllSovereignSpeech();
    };
  }, []);

  const activeLensId = academy.learner.activeLens;
  const activeLens =
    academy.lenses.find((l) => l.id === activeLensId) ?? academy.lenses[0];
  const activeSpark =
    academy.sparks.find((s) => s.sparkId === activeSparkId) ?? academy.sparks[0];
  const activeSparkCopy = activeSpark.byLens[activeLens.id];

  const activeLab =
    academy.labs.find((l) => l.labId === activeLabId) ?? academy.labs[0];

  const selectLab = (nextLabId: InteractiveLabId) => {
    setActiveLabId(nextLabId);
    const def = academy.labs.find((l) => l.labId === nextLabId);
    if (def) {
      const safeMid =
        def.sliderStep < 1
          ? Number(((def.targetSafeMin + def.targetSafeMax) / 2).toFixed(2))
          : Math.round((def.targetSafeMin + def.targetSafeMax) / 2);
      setSliderValue(safeMid);
      setSecondaryToggle(def.defaultSecondaryToggle);
    }
  };

  const applyLabStagePreset = (preset: 'NOMINAL_SAFE' | 'OVERLOAD_SPIKE' | 'RESET') => {
    if (preset === 'NOMINAL_SAFE') {
      const safeMid =
        activeLab.sliderStep < 1
          ? Number(((activeLab.targetSafeMin + activeLab.targetSafeMax) / 2).toFixed(2))
          : Math.round((activeLab.targetSafeMin + activeLab.targetSafeMax) / 2);
      setSliderValue(safeMid);
      setSecondaryToggle(true);
      playSovereignChime('lock', true);
      return;
    }
    if (preset === 'OVERLOAD_SPIKE') {
      const spikeVal =
        activeLab.labId === 'LAB_FOREX_FREE_LANE'
          ? Math.max(activeLab.sliderMin, activeLab.targetSafeMin - 35)
          : activeLab.sliderMax;
      setSliderValue(spikeVal);
      setSecondaryToggle(false);
      playSovereignChime('refuse', true);
      return;
    }
    setSliderValue(activeLab.defaultSliderValue);
    setSecondaryToggle(activeLab.defaultSecondaryToggle);
  };

  const handleSelectLens = async (lensId: HumanLearningLensId) => {
    setAcademy((prev) => ({
      ...prev,
      learner: { ...prev.learner, activeLens: lensId },
    }));
    try {
      const res = await fetch('/api/academy/set-lens', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lensId }),
      });
      if (res.ok) {
        const data = (await res.json()) as { academy?: GenesisAcademyState };
        if (data.academy) setAcademy(data.academy);
      }
    } catch {
      // Keep optimistic lens state
    }
  };

  const handleToggleAudioReel = () => {
    if (speakingSparkId === activeSpark.sparkId) {
      stopAllSovereignSpeech();
      setSpeakingSparkId(null);
      return;
    }
    const started = speakLiveEstateHeadline(activeSparkCopy.spokenAudioScript, true);
    setSpeakingSparkId(started ? activeSpark.sparkId : null);
    if (started) {
      window.setTimeout(() => {
        setSpeakingSparkId((curr) => (curr === activeSpark.sparkId ? null : curr));
      }, 12000);
    }
  };

  const handleCopySocialCard = async () => {
    const shareText = `${activeSpark.universalTitle} (${activeLens.shortLabel})\n"${activeSparkCopy.hook5Sec}"\n→ ${activeSpark.shareableSocialPunchline}\nVerify live on Genesis Asymmetric Academy (#academy)`;
    try {
      await navigator.clipboard.writeText(shareText);
      setCopiedSparkId(activeSpark.sparkId);
      window.setTimeout(() => setCopiedSparkId(null), 2200);
    } catch {
      setCopiedSparkId(activeSpark.sparkId);
    }
  };

  const handleAnswerQuickCheck = async (optionIdx: number) => {
    setSelectedOptionBySpark((prev) => ({ ...prev, [activeSpark.sparkId]: optionIdx }));
    try {
      const res = await fetch('/api/academy/complete-spark', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sparkId: activeSpark.sparkId,
          selectedOptionIndex: optionIdx,
          lens: activeLens.id,
        }),
      });
      const data = (await res.json()) as {
        passed?: boolean;
        feedback?: string;
        academy?: GenesisAcademyState;
      };
      if (data.academy) {
        setAcademy(data.academy);
      }
      const passed = Boolean(data.passed);
      playSovereignChime(passed ? 'execute' : 'refuse', true);
      setSparkFeedback({
        sparkId: activeSpark.sparkId,
        passed,
        message: data.feedback || (passed ? 'Spark mastered!' : 'Try another option.'),
      });
      await onRefreshState();
    } catch {
      setSparkFeedback({
        sparkId: activeSpark.sparkId,
        passed: false,
        message: 'Unable to record Spark progress right now.',
      });
    }
  };

  const handleExecuteLiveLab = async () => {
    setLabBusy(true);
    try {
      const res = await fetch('/api/academy/complete-lab', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          labId: activeLab.labId,
          sliderValue,
          secondaryToggle,
        }),
      });
      const data = (await res.json()) as {
        evaluation?: LabEvaluationResult;
        academy?: GenesisAcademyState;
      };
      if (data.academy) {
        setAcademy(data.academy);
      }
      if (data.evaluation) {
        setLatestLabReceipt(data.evaluation);
        playSovereignChime(data.evaluation.passed ? 'execute' : 'refuse', true);
      }
      await onRefreshState();
    } finally {
      setLabBusy(false);
    }
  };

  const liveIsNominal =
    sliderValue >= activeLab.targetSafeMin &&
    sliderValue <= activeLab.targetSafeMax &&
    (!activeLab.requiredSecondaryToggle || secondaryToggle);

  const liveSliderPct = Math.max(
    0,
    Math.min(
      100,
      ((sliderValue - activeLab.sliderMin) / (activeLab.sliderMax - activeLab.sliderMin)) * 100
    )
  );
  const safeBandStartPct =
    ((activeLab.targetSafeMin - activeLab.sliderMin) /
      (activeLab.sliderMax - activeLab.sliderMin)) *
    100;
  const safeBandWidthPct =
    ((activeLab.targetSafeMax - activeLab.targetSafeMin) /
      (activeLab.sliderMax - activeLab.sliderMin)) *
    100;

  const liveRevenueSim = useMemo(
    () =>
      simulateAsymmetricAcademyEconomics({
        freeSocialLearnersMonthly: freeLearnersMonthly,
        proBuilderConversionPct: proConversionPct,
        proMonthlyPriceUsd: 29,
        enterpriseSeatsAnnual: enterpriseSeats,
        enterpriseSeatAnnualUsd: 499,
        verifiedHiresMonthly,
      }),
    [freeLearnersMonthly, proConversionPct, enterpriseSeats, verifiedHiresMonthly]
  );

  const highestUnlockedCert =
    [...academy.certifications].reverse().find((c) => c.unlocked) ?? academy.certifications[0];

  const handleVerifyCredentialHash = async (e: React.FormEvent) => {
    e.preventDefault();
    const candidate = verifyInputSha.trim();
    if (candidate.length < 8) {
      setVerifyFeedback({
        valid: false,
        message: 'Enter at least 8 hexadecimal characters from a credential SHA-256 digest.',
      });
      return;
    }
    const matched = academy.certifications.find(
      (c) =>
        c.unlocked &&
        c.credentialSha256 &&
        c.credentialSha256.toLowerCase().startsWith(candidate.toLowerCase())
    );
    if (matched) {
      setVerifyFeedback({
        valid: true,
        message: `● VERIFIED AUTHENTIC: ${matched.title} · Holder ${academy.learner.learnerName} (${academy.learner.learnerDid})`,
      });
      playSovereignChime('lock', true);
    } else {
      setVerifyFeedback({
        valid: false,
        message: `▲ UNRECOGNIZED DIGEST: No unlocked credential matches prefix "${candidate}".`,
      });
      playSovereignChime('refuse', true);
    }
  };

  const verifyCliCommand = `./bin/academy verify --sha ${
    highestUnlockedCert.credentialSha256?.slice(0, 16) ?? 'PENDING'
  }`;

  return (
    <div className="space-y-10 pb-12">
      {/* HERO & 4-GENERATION HUMAN LENS BAR */}
      <section
        aria-labelledby="academy-hero-heading"
        className="p-6 sm:p-8 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800/80 rounded-2xl space-y-6"
      >
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6">
          <div className="space-y-3 max-w-3xl">
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
              <span className="font-medium text-amber-600 dark:text-amber-400">
                Genesis Asymmetric Academy
              </span>
              <span aria-hidden="true">·</span>
              <span>45-Second Social Sparks</span>
              <span aria-hidden="true">·</span>
              <span>Live Agentic OS Labs</span>
              <span aria-hidden="true">·</span>
              <span>Unforgeable SHA-256 Credentials</span>
            </div>

            <h1
              id="academy-hero-heading"
              className="text-2xl sm:text-3xl lg:text-4xl font-semibold tracking-tight text-slate-900 dark:text-slate-50 max-w-2xl"
            >
              Kill passive lectures. Master AI &amp; Robotics on a live Autonomous Operating System.
            </h1>

            <p className="text-sm sm:text-base text-slate-600 dark:text-slate-300 leading-relaxed max-w-2xl">
              {activeLens.promise}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <a
              href="/api/academy/certificate"
              download="genesis-academy-credential.md"
              className="inline-flex items-center gap-2 px-4 py-2.5 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Download className="w-3.5 h-3.5" aria-hidden="true" />
              Download Proof Credential (.md)
            </a>
            <button
              type="button"
              onClick={() => {
                const el = document.getElementById('academy-live-sandbox');
                el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }}
              className="inline-flex items-center gap-2 px-4 py-2.5 text-xs font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-800/80 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Sliders className="w-3.5 h-3.5" aria-hidden="true" />
              Jump to Live Lab
            </button>
          </div>
        </div>

        {/* 4-Lens Multi-Generational Switcher */}
        <div className="pt-4 border-t border-slate-200/80 dark:border-slate-800/80 space-y-2.5">
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500 dark:text-slate-400">
            <span>
              Select Human Learning Lens — every lesson &amp; live lab rewrites instantly for your stage:
            </span>
            <span className="font-mono tabular-nums">{activeLens.audienceTag}</span>
          </div>

          <div
            role="tablist"
            aria-label="Human Learning Lens"
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 p-1.5 bg-slate-100 dark:bg-[#070B14] border border-slate-200/80 dark:border-slate-800/80 rounded-xl"
          >
            {academy.lenses.map((lens) => {
              const selected = lens.id === activeLens.id;
              return (
                <button
                  key={lens.id}
                  role="tab"
                  type="button"
                  aria-selected={selected}
                  onClick={() => handleSelectLens(lens.id)}
                  className={`px-3.5 py-2.5 text-left rounded-lg transition-colors ${
                    selected
                      ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-amber-300 shadow-xs border border-slate-200/80 dark:border-amber-500/30'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                  }`}
                >
                  <div className="text-xs font-semibold whitespace-nowrap truncate">
                    {lens.shortLabel}
                  </div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400 truncate mt-0.5">
                    {lens.label}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Full-Width 4-Column KPI Strip */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 pt-4 border-t border-slate-200/80 dark:border-slate-800/80">
          <div>
            <div className="text-xs text-slate-500 dark:text-slate-400">
              Verified Experience &amp; Streak
            </div>
            <div className="mt-1 text-xl font-semibold font-mono tabular-nums text-slate-900 dark:text-slate-50">
              {academy.learner.totalXp} XP · {academy.learner.streakDays}d Streak
            </div>
            <div className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              Merkle {academy.academyMerkleSha256.slice(0, 12)}
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-500 dark:text-slate-400">
              45s Micro-Sparks Mastered
            </div>
            <div className="mt-1 text-xl font-semibold font-mono tabular-nums text-slate-900 dark:text-slate-50">
              {academy.learner.completedSparkIds.length} / {academy.sparks.length}
            </div>
            <div className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              Social bite-sized stories + audio
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-500 dark:text-slate-400">
              Live Estate Labs Proven
            </div>
            <div className="mt-1 text-xl font-semibold font-mono tabular-nums text-emerald-700 dark:text-emerald-400">
              {academy.learner.completedLabIds.length} / {academy.labs.length} ● Verified
            </div>
            <div className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              Real Omega HAL, SpecGate &amp; Forex runs
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-500 dark:text-slate-400">
              Unlocked Credentials &amp; Margin
            </div>
            <div className="mt-1 text-xl font-semibold font-mono tabular-nums text-amber-600 dark:text-amber-400">
              {academy.certifications.filter((c) => c.unlocked).length} / 4 Certs ·{' '}
              {liveRevenueSim.grossMarginPct}% GM
            </div>
            <div className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              ${(liveRevenueSim.annualizedArrUsd / 1_000_000).toFixed(2)}M modeled ARR on $0 Free Lanes
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 01: BITE-SIZED SOCIAL MICRO-SPARK REEL (45-SECOND PLAYABLE STORIES) */}
      <section aria-labelledby="micro-sparks-heading" className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2">
          <div>
            <h2
              id="micro-sparks-heading"
              className="text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-50"
            >
              01. Bite-Sized Social Micro-Spark Reel
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-400 mt-0.5">
              Zero 40-hour MP4 lectures. Absorb one real production principle in 45 seconds, listen
              hands-free, and lock +XP with a single tap.
            </p>
          </div>
          <div className="text-xs text-slate-500 dark:text-slate-400 font-mono tabular-nums">
            Active Lens: {activeLens.label}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
          {/* Left Rail: 6 Curated Micro-Spark Selector */}
          <div className="lg:col-span-4 p-4 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800/80 rounded-2xl flex flex-col justify-between space-y-2">
            <div className="space-y-1.5">
              {academy.sparks.map((spark) => {
                const isSelected = spark.sparkId === activeSpark.sparkId;
                const isDone = academy.learner.completedSparkIds.includes(spark.sparkId);
                return (
                  <button
                    key={spark.sparkId}
                    type="button"
                    onClick={() => {
                      setActiveSparkId(spark.sparkId);
                      setSparkFeedback(null);
                    }}
                    className={`w-full text-left px-3.5 py-3 rounded-xl transition-colors border ${
                      isSelected
                        ? 'bg-slate-900 text-white border-slate-900 dark:bg-amber-500/15 dark:text-slate-50 dark:border-amber-500/40'
                        : 'bg-transparent text-slate-700 dark:text-slate-300 border-transparent hover:bg-slate-100 dark:hover:bg-slate-800/60'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 text-[11px] font-mono tabular-nums opacity-80">
                      <span>
                        {spark.sparkId} · {spark.durationSec}s · +{spark.xpReward} XP
                      </span>
                      <span>{isDone ? '● Mastered' : '○ Ready'}</span>
                    </div>
                    <div className="mt-1 text-xs font-semibold leading-snug">
                      {spark.universalTitle}
                    </div>
                  </button>
                );
              })}
            </div>

            <div className="pt-3 border-t border-slate-200 dark:border-slate-800 text-xs text-slate-500 dark:text-slate-400">
              Every Spark links directly to its live Estate organ—zero toy throwaway examples.
            </div>
          </div>

          {/* Right Stage: Playable 45-Second Social Story Card + Instant Quick Check */}
          <div className="lg:col-span-8 p-6 sm:p-7 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800/80 rounded-2xl flex flex-col justify-between space-y-6">
            <div className="space-y-5">
              {/* Unboxed Clean Metadata Header */}
              <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-200/80 dark:border-slate-800/80">
                <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 dark:text-slate-400 font-mono tabular-nums">
                  <span className="text-amber-600 dark:text-amber-400 font-semibold">
                    {activeSpark.sparkId}
                  </span>
                  <span aria-hidden="true">·</span>
                  <span>{activeSpark.durationSec}s Read/Audio</span>
                  <span aria-hidden="true">·</span>
                  <span>+{activeSpark.xpReward} XP</span>
                  <span aria-hidden="true">·</span>
                  <span>Door {activeSpark.boundEstateDoor}</span>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={handleToggleAudioReel}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-800 dark:text-slate-200 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors whitespace-nowrap shrink-0"
                  >
                    {speakingSparkId === activeSpark.sparkId ? (
                      <>
                        <Square className="w-3.5 h-3.5 text-amber-500" aria-hidden="true" />
                        Stop Audio
                      </>
                    ) : (
                      <>
                        <Volume2 className="w-3.5 h-3.5 text-amber-500" aria-hidden="true" />
                        Listen (45s Audio Reel)
                      </>
                    )}
                  </button>

                  <button
                    type="button"
                    onClick={handleCopySocialCard}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors whitespace-nowrap shrink-0"
                  >
                    {copiedSparkId === activeSpark.sparkId ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-500" aria-hidden="true" />
                        Copied Card
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" aria-hidden="true" />
                        Copy Social Card
                      </>
                    )}
                  </button>

                  <button
                    type="button"
                    onClick={() => onDeepLinkNavigate(activeSpark.deepLinkHash)}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-amber-700 dark:text-amber-300 hover:underline whitespace-nowrap shrink-0"
                  >
                    Inspect Live Organ
                    <ArrowUpRight className="w-3.5 h-3.5" aria-hidden="true" />
                  </button>
                </div>
              </div>

              <h3 className="text-xl sm:text-2xl font-semibold text-slate-900 dark:text-slate-50">
                {activeSpark.universalTitle}
              </h3>

              {/* 3 Digestible Story Beats (5s Hook -> 20s Insight -> 20s Superpower) */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
                <div className="p-4 bg-slate-50 dark:bg-[#070B14] border border-slate-200/80 dark:border-slate-800/80 rounded-xl space-y-1.5">
                  <div className="text-xs font-semibold text-amber-600 dark:text-amber-400 font-mono tabular-nums">
                    01 · 5-Second Hook
                  </div>
                  <p className="text-sm text-slate-800 dark:text-slate-200 leading-relaxed">
                    {activeSparkCopy.hook5Sec}
                  </p>
                </div>

                <div className="p-4 bg-slate-50 dark:bg-[#070B14] border border-slate-200/80 dark:border-slate-800/80 rounded-xl space-y-1.5">
                  <div className="text-xs font-semibold text-sky-600 dark:text-sky-400 font-mono tabular-nums">
                    02 · 20-Second Core Insight
                  </div>
                  <p className="text-sm text-slate-800 dark:text-slate-200 leading-relaxed">
                    {activeSparkCopy.insight20Sec}
                  </p>
                </div>

                <div className="p-4 bg-slate-50 dark:bg-[#070B14] border border-slate-200/80 dark:border-slate-800/80 rounded-xl space-y-1.5">
                  <div className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 font-mono tabular-nums">
                    03 · Your New Superpower
                  </div>
                  <p className="text-sm text-slate-800 dark:text-slate-200 leading-relaxed">
                    {activeSparkCopy.superpower20Sec}
                  </p>
                </div>
              </div>
            </div>

            {/* Interactive 1-Tap Quick Check */}
            <div className="pt-5 border-t border-slate-200/80 dark:border-slate-800/80 space-y-3">
              <div className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                10-Second Mastery Check: {activeSparkCopy.quickCheckQuestion}
              </div>

              <div className="grid grid-cols-1 gap-2">
                {activeSparkCopy.quickCheckOptions.map((opt, idx) => {
                  const chosen = selectedOptionBySpark[activeSpark.sparkId] === idx;
                  const isCorrect = idx === activeSparkCopy.correctOptionIndex;
                  return (
                    <button
                      key={opt}
                      type="button"
                      onClick={() => handleAnswerQuickCheck(idx)}
                      className={`w-full text-left px-4 py-2.5 text-xs sm:text-sm rounded-lg border transition-colors flex items-center justify-between gap-3 ${
                        chosen && isCorrect
                          ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-500/60 text-emerald-900 dark:text-emerald-200 font-medium'
                          : chosen && !isCorrect
                            ? 'bg-rose-50 dark:bg-rose-950/40 border-rose-500/60 text-rose-900 dark:text-rose-200'
                            : 'bg-slate-50 dark:bg-[#070B14] border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:border-slate-400 dark:hover:border-slate-600'
                      }`}
                    >
                      <span>{opt}</span>
                      {chosen && (
                        <span className="font-mono text-xs shrink-0">
                          {isCorrect ? '● Correct' : '▲ Retry'}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>

              {sparkFeedback && sparkFeedback.sparkId === activeSpark.sparkId && (
                <p
                  role="status"
                  className={`text-xs font-medium ${
                    sparkFeedback.passed
                      ? 'text-emerald-700 dark:text-emerald-400'
                      : 'text-amber-700 dark:text-amber-400'
                  }`}
                >
                  {sparkFeedback.message}
                </p>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 02: TWO-ZONE LIVE AGENTIC SIMULATION SANDBOX (6_education_simulations.md) */}
      <section
        id="academy-live-sandbox"
        aria-labelledby="sandbox-heading"
        className="space-y-4"
      >
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
          <div>
            <h2
              id="sandbox-heading"
              className="text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-50"
            >
              02. Two-Zone Live Agentic Platform Sandbox
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-400 mt-0.5">
              Operate real Meridian subsystems in motion—drag parameters on the right, observe live
              signal physics on the left, and mint a `.ops/register.jsonl` execution proof.
            </p>
          </div>

          {/* Segmented Lab Selector */}
          <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-[#080D1A] border border-slate-200 dark:border-slate-800 rounded-xl shrink-0 overflow-x-auto">
            {academy.labs.map((lab, i) => {
              const selected = lab.labId === activeLab.labId;
              const done = academy.learner.completedLabIds.includes(lab.labId);
              const shortNames = ['Lab 01: Omega', 'Lab 02: SpecGate', 'Lab 03: Free-Lane'];
              return (
                <button
                  key={lab.labId}
                  type="button"
                  onClick={() => selectLab(lab.labId)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors whitespace-nowrap shrink-0 ${
                    selected
                      ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-amber-300 shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                  }`}
                >
                  {shortNames[i] ?? lab.labId} {done ? '✓' : ''}
                </button>
              );
            })}
          </div>
        </div>

        {/* Balanced Two-Zone Sandbox Split: 60–65% Visual Stage (Left) + 35–40% Control Deck (Right) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
          {/* LEFT ZONE (60-65%): Interactive Live Signal & Equilibrium Diagram */}
          <div className="lg:col-span-7 p-6 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800/80 rounded-2xl flex flex-col justify-between space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-xs text-slate-500 dark:text-slate-400">
                  {activeLab.boundSubsystem}
                </div>
                <h3 className="text-base sm:text-lg font-semibold text-slate-900 dark:text-slate-50 mt-0.5">
                  {activeLab.title}
                </h3>
              </div>

              <div
                className={`text-xs font-mono tabular-nums font-semibold ${
                  liveIsNominal
                    ? 'text-emerald-700 dark:text-emerald-400'
                    : 'text-amber-700 dark:text-amber-400'
                }`}
              >
                {liveIsNominal ? '● NOMINAL EQUILIBRIUM' : '▲ ELEVATED / CLAMP ACTIVE'}
              </div>
            </div>

            {/* Interactive SVG Signal-Flow & Coordinate Stage */}
            <div
              data-testid="academy-interactive-stage"
              className="w-full bg-slate-50 dark:bg-[#060A14] border border-slate-200/90 dark:border-slate-800 rounded-xl p-4"
            >
              <svg
                viewBox="0 0 640 270"
                role="img"
                aria-label={`Interactive simulation diagram for ${activeLab.title} currently at ${sliderValue} ${activeLab.sliderUnit}`}
                className="w-full h-auto select-none"
              >
                {/* Subtle Coordinate Grid */}
                <g stroke="currentColor" className="text-slate-200 dark:text-slate-800/80" strokeWidth="1">
                  <line x1="40" y1="55" x2="600" y2="55" strokeDasharray="3 3" />
                  <line x1="40" y1="125" x2="600" y2="125" strokeDasharray="3 3" />
                  <line x1="40" y1="195" x2="600" y2="195" />
                </g>

                {/* Signal Pipeline Nodes (Sense / Ingress -> Kernel / Gate -> Actuate / Output) */}
                <rect
                  x="44"
                  y="34"
                  width="150"
                  height="64"
                  rx="10"
                  className="fill-white dark:fill-slate-900 stroke-slate-300 dark:stroke-slate-700"
                  strokeWidth="1.5"
                />
                <text
                  x="58"
                  y="56"
                  className="fill-slate-500 dark:fill-slate-400 text-[10px] font-mono"
                >
                  {activeLab.labId === 'LAB_OMEGA_ROBOT_FORCE'
                    ? '1. HAL SENSE INPUT'
                    : activeLab.labId === 'LAB_SPECGATE_PROMPT_SHIELD'
                      ? '1. INTENT INGRESS'
                      : '1. TASK_BID STREAM'}
                </text>
                <text
                  x="58"
                  y="78"
                  className="fill-slate-900 dark:fill-slate-100 text-[13px] font-bold font-mono"
                >
                  {sliderValue} {activeLab.sliderUnit}
                </text>

                {/* Directional Flow Arrow 1 */}
                <line
                  x1="196"
                  y1="66"
                  x2="242"
                  y2="66"
                  className={
                    liveIsNominal
                      ? 'stroke-sky-500 dark:stroke-sky-400'
                      : 'stroke-amber-500 dark:stroke-amber-400'
                  }
                  strokeWidth="2.5"
                />
                <polygon
                  points="242,61 252,66 242,71"
                  className={
                    liveIsNominal
                      ? 'fill-sky-500 dark:fill-sky-400'
                      : 'fill-amber-500 dark:fill-amber-400'
                  }
                />

                {/* Safeguard Kernel Node */}
                <rect
                  x="254"
                  y="34"
                  width="156"
                  height="64"
                  rx="10"
                  className={
                    secondaryToggle
                      ? 'fill-white dark:fill-slate-900 stroke-emerald-500/80'
                      : 'fill-white dark:fill-slate-900 stroke-rose-500/80'
                  }
                  strokeWidth="1.8"
                />
                <text
                  x="268"
                  y="56"
                  className="fill-slate-500 dark:fill-slate-400 text-[10px] font-mono"
                >
                  2. RING-0 SAFEGUARD
                </text>
                <text
                  x="268"
                  y="78"
                  className={
                    secondaryToggle
                      ? 'fill-emerald-600 dark:fill-emerald-400 text-[12px] font-bold font-mono'
                      : 'fill-rose-600 dark:fill-rose-400 text-[12px] font-bold font-mono'
                  }
                >
                  {secondaryToggle ? '● ARMED (500 Hz)' : '▲ BYPASSED'}
                </text>

                {/* Directional Flow Arrow 2 */}
                <line
                  x1="412"
                  y1="66"
                  x2="454"
                  y2="66"
                  className={
                    liveIsNominal
                      ? 'stroke-emerald-500 dark:stroke-emerald-400'
                      : 'stroke-rose-500 dark:stroke-rose-400'
                  }
                  strokeWidth="2.5"
                />
                <polygon
                  points="454,61 464,66 454,71"
                  className={
                    liveIsNominal
                      ? 'fill-emerald-500 dark:fill-emerald-400'
                      : 'fill-rose-500 dark:fill-rose-400'
                  }
                />

                {/* Actuated Output Node */}
                <rect
                  x="466"
                  y="34"
                  width="134"
                  height="64"
                  rx="10"
                  className={
                    liveIsNominal
                      ? 'fill-emerald-50/70 dark:fill-emerald-950/30 stroke-emerald-500/80'
                      : 'fill-amber-50/70 dark:fill-amber-950/30 stroke-amber-500/80'
                  }
                  strokeWidth="1.8"
                />
                <text
                  x="478"
                  y="56"
                  className="fill-slate-500 dark:fill-slate-400 text-[10px] font-mono"
                >
                  3. VERIFIED YIELD
                </text>
                <text
                  x="478"
                  y="78"
                  className={
                    liveIsNominal
                      ? 'fill-emerald-700 dark:fill-emerald-300 text-[12px] font-bold font-mono'
                      : 'fill-amber-700 dark:fill-amber-300 text-[12px] font-bold font-mono'
                  }
                >
                  {liveIsNominal ? '● PROOF READY' : '▲ CLAMPED'}
                </text>

                {/* Live Quantitative Equilibrium Scale & Target Window Band */}
                <text
                  x="44"
                  y="142"
                  className="fill-slate-600 dark:fill-slate-300 text-[11px] font-mono"
                >
                  Target Nominal Window: [{activeLab.targetSafeMin} .. {activeLab.targetSafeMax}{' '}
                  {activeLab.sliderUnit}]
                </text>

                {/* Full Scale Track (x=44 to x=596 -> width=552) */}
                <rect
                  x="44"
                  y="156"
                  width="552"
                  height="24"
                  rx="6"
                  className="fill-slate-200 dark:fill-slate-800"
                />

                {/* Highlighted Target Safe Equilibrium Band */}
                <rect
                  x={44 + (safeBandStartPct / 100) * 552}
                  y="156"
                  width={Math.max(12, (safeBandWidthPct / 100) * 552)}
                  height="24"
                  rx="4"
                  className="fill-emerald-500/30 dark:fill-emerald-500/25 stroke-emerald-500/70"
                  strokeWidth="1"
                />

                {/* Live User Marker Cursor */}
                <g
                  transform={`translate(${44 + (liveSliderPct / 100) * 552}, 168)`}
                >
                  <circle
                    r="10"
                    className={
                      liveIsNominal
                        ? 'fill-emerald-600 dark:fill-emerald-400'
                        : 'fill-amber-600 dark:fill-amber-400'
                    }
                  />
                  <circle r="4" className="fill-white dark:fill-slate-950" />
                </g>

                {/* Axis Scale Labels */}
                <text
                  x="44"
                  y="214"
                  className="fill-slate-500 dark:fill-slate-400 text-[10px] font-mono"
                >
                  Min: {activeLab.sliderMin} {activeLab.sliderUnit}
                </text>
                <text
                  x="320"
                  y="214"
                  textAnchor="middle"
                  className="fill-slate-700 dark:fill-slate-200 text-[11px] font-semibold font-mono"
                >
                  Current: {sliderValue} {activeLab.sliderUnit} (
                  {liveIsNominal ? 'Inside Safe Window' : 'Outside Safe Window / Unarmed'})
                </text>
                <text
                  x="596"
                  y="214"
                  textAnchor="end"
                  className="fill-slate-500 dark:fill-slate-400 text-[10px] font-mono"
                >
                  Max: {activeLab.sliderMax} {activeLab.sliderUnit}
                </text>

                {/* Live Subsystem Physics Readout */}
                <text
                  x="44"
                  y="246"
                  className="fill-slate-600 dark:fill-slate-400 text-[11px] font-mono"
                >
                  {activeLab.labId === 'LAB_OMEGA_ROBOT_FORCE'
                    ? `Applied Wrist Force: ${
                        secondaryToggle ? Math.min(sliderValue, 18) : sliderValue
                      } N · Cargo Integrity: ${
                        sliderValue < 8
                          ? 'SLIPPING (<8N)'
                          : sliderValue <= 18 && secondaryToggle
                            ? 'INTACT & STABLE'
                            : secondaryToggle
                              ? 'CLAMPED AT 18N'
                              : 'CRUSH HAZARD!'
                      }`
                    : activeLab.labId === 'LAB_SPECGATE_PROMPT_SHIELD'
                      ? `Post-Hydration Entropy: ${sliderValue.toFixed(2)} H · Gherkin Contract: ${
                          secondaryToggle ? '3 Scenarios Sealed' : 'Missing'
                        }`
                      : `Zero-Cost Lane Fill: ${sliderValue}% · Modeled Gross Margin: ${(
                          100 -
                          (100 - sliderValue) * 0.28
                        ).toFixed(1)}%`}
                </text>
              </svg>
            </div>

            {/* Mathematical Invariant Formula Bar */}
            <div className="px-4 py-3 bg-slate-100/80 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 rounded-xl font-mono text-xs text-slate-700 dark:text-slate-300 overflow-x-auto">
              Invariant: {activeLab.formulaDisplay}
            </div>
          </div>

          {/* RIGHT ZONE (35-40%): Parameter Sliders, Stage Presets & Execution Receipt Deck */}
          <div className="lg:col-span-5 p-6 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800/80 rounded-2xl flex flex-col justify-between space-y-5">
            <div className="space-y-5">
              {/* Lens-Adapted Mission Guidance */}
              <div className="p-4 bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 rounded-xl space-y-1">
                <div className="text-xs font-semibold text-amber-600 dark:text-amber-400">
                  {activeLens.shortLabel} Mission Brief (+{activeLab.xpReward} XP)
                </div>
                <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                  {activeLab.lensGuidance[activeLens.id]}
                </p>
              </div>

              {/* Guided Stage Presets */}
              <div className="space-y-1.5">
                <div className="text-xs font-medium text-slate-600 dark:text-slate-400">
                  Guided Discovery Presets
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => applyLabStagePreset('NOMINAL_SAFE')}
                    className="px-3 py-1.5 text-xs font-medium text-slate-800 dark:text-slate-200 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors whitespace-nowrap shrink-0"
                  >
                    Stage 1: Nominal Safe
                  </button>
                  <button
                    type="button"
                    onClick={() => applyLabStagePreset('OVERLOAD_SPIKE')}
                    className="px-3 py-1.5 text-xs font-medium text-slate-800 dark:text-slate-200 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors whitespace-nowrap shrink-0"
                  >
                    Stage 2: Overload Spike
                  </button>
                  <button
                    type="button"
                    onClick={() => applyLabStagePreset('RESET')}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 rounded-lg transition-colors whitespace-nowrap shrink-0"
                  >
                    <RotateCcw className="w-3 h-3" aria-hidden="true" />
                    Reset
                  </button>
                </div>
              </div>

              {/* Labeled Parameter Slider with Explicit Value & Unit */}
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <label
                    htmlFor="academy-lab-slider"
                    className="text-xs font-semibold text-slate-800 dark:text-slate-200"
                  >
                    {activeLab.sliderLabel}
                  </label>
                  <span className="text-sm font-bold font-mono tabular-nums text-amber-600 dark:text-amber-400">
                    {sliderValue} {activeLab.sliderUnit}
                  </span>
                </div>
                <input
                  id="academy-lab-slider"
                  type="range"
                  min={activeLab.sliderMin}
                  max={activeLab.sliderMax}
                  step={activeLab.sliderStep}
                  value={sliderValue}
                  onChange={(e) => setSliderValue(Number(e.target.value))}
                  className="w-full accent-amber-500 cursor-pointer"
                />
                <div className="flex items-center justify-between text-[11px] font-mono tabular-nums text-slate-500 dark:text-slate-400">
                  <span>
                    {activeLab.sliderMin} {activeLab.sliderUnit}
                  </span>
                  <span>
                    Safe: {activeLab.targetSafeMin}–{activeLab.targetSafeMax} {activeLab.sliderUnit}
                  </span>
                  <span>
                    {activeLab.sliderMax} {activeLab.sliderUnit}
                  </span>
                </div>
              </div>

              {/* Secondary Safeguard Switch */}
              <div className="flex items-center justify-between gap-3 p-3.5 bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 rounded-xl">
                <span className="text-xs font-medium text-slate-800 dark:text-slate-200">
                  {activeLab.secondaryToggleLabel}
                </span>
                <button
                  type="button"
                  role="switch"
                  aria-checked={secondaryToggle}
                  onClick={() => setSecondaryToggle((v) => !v)}
                  className={`px-3 py-1.5 text-xs font-mono font-semibold rounded-lg transition-colors whitespace-nowrap shrink-0 ${
                    secondaryToggle
                      ? 'bg-emerald-600 text-white'
                      : 'bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
                  }`}
                >
                  {secondaryToggle ? 'ARMED' : 'DISABLED'}
                </button>
              </div>
            </div>

            {/* Execute CTA & Live Signed Receipt Output */}
            <div className="space-y-3 pt-4 border-t border-slate-200 dark:border-slate-800">
              <button
                type="button"
                disabled={labBusy}
                onClick={handleExecuteLiveLab}
                className="w-full py-3 px-4 text-xs sm:text-sm font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 disabled:opacity-60 rounded-xl transition-colors whitespace-nowrap"
              >
                {labBusy
                  ? 'Verifying Against Live Estate...'
                  : 'Run Live Lab & Mint Proof Receipt'}
              </button>

              {latestLabReceipt && (
                <div
                  role="status"
                  className="p-3.5 bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 rounded-xl space-y-1.5"
                >
                  <div className="flex items-center justify-between gap-2 text-xs font-semibold">
                    <span
                      className={
                        latestLabReceipt.passed
                          ? 'text-emerald-700 dark:text-emerald-400 flex items-center gap-1.5'
                          : 'text-amber-700 dark:text-amber-400 flex items-center gap-1.5'
                      }
                    >
                      {latestLabReceipt.passed ? (
                        <CheckCircle2 className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
                      ) : (
                        <AlertTriangle className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
                      )}
                      {latestLabReceipt.telemetryHeadline}
                    </span>
                    <span className="font-mono tabular-nums text-[11px] text-slate-500">
                      +{latestLabReceipt.xpAwarded} XP
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                    {latestLabReceipt.scientificExplanation}
                  </p>
                  <div className="text-[11px] font-mono tabular-nums text-slate-500">
                    Receipt {latestLabReceipt.evalId} · SHA{' '}
                    {latestLabReceipt.proofReceiptHash.slice(0, 20)}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 03: 4-TIER CRYPTOGRAPHIC PROOF-OF-EXECUTION CERTIFICATION PATH */}
      <section aria-labelledby="certifications-heading" className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
          <div>
            <h2
              id="certifications-heading"
              className="text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-50"
            >
              03. Unforgeable Proof-of-Execution Certification Path
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-400 mt-0.5">
              Paper diplomas can be faked; SHA-256 execution receipts bound to live Estate labs
              cannot. Complete Sparks and Labs above to unlock higher tiers in real time.
            </p>
          </div>

          <button
            type="button"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(verifyCliCommand);
                setCopiedVerifyCmd(true);
                window.setTimeout(() => setCopiedVerifyCmd(false), 2000);
              } catch {
                setCopiedVerifyCmd(true);
              }
            }}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-mono text-slate-700 dark:text-slate-200 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-lg hover:border-amber-500/50 transition-colors whitespace-nowrap shrink-0"
          >
            {copiedVerifyCmd ? (
              <Check className="w-3.5 h-3.5 text-emerald-500" aria-hidden="true" />
            ) : (
              <Copy className="w-3.5 h-3.5" aria-hidden="true" />
            )}
            <span>{verifyCliCommand}</span>
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {academy.certifications.map((cert) => {
            const xpProgressPct = Math.min(
              100,
              Math.round((academy.learner.totalXp / cert.requiredXp) * 100)
            );
            return (
              <div
                key={cert.tierId}
                className={`p-6 bg-white dark:bg-[#0B101D] border rounded-2xl flex flex-col justify-between space-y-4 ${
                  cert.unlocked
                    ? 'border-emerald-500/50 dark:border-emerald-500/40'
                    : 'border-slate-200 dark:border-slate-800/80'
                }`}
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between gap-2 text-xs font-mono tabular-nums">
                    <span
                      className={
                        cert.unlocked
                          ? 'font-semibold text-emerald-700 dark:text-emerald-400'
                          : 'text-slate-500 dark:text-slate-400'
                      }
                    >
                      {cert.unlocked ? '● UNLOCKED & SIGNED' : '○ IN PROGRESS'} · {cert.tierId}
                    </span>
                    <span className="text-slate-500 dark:text-slate-400">
                      Req: {cert.requiredXp} XP &amp; {cert.requiredCompletedLabs} Labs
                    </span>
                  </div>

                  <h3 className="text-base font-semibold text-slate-900 dark:text-slate-50">
                    {cert.title}
                  </h3>

                  <p className="text-xs text-amber-700 dark:text-amber-300/90 font-medium">
                    {cert.replacesLegacyCredential}
                  </p>

                  <ul className="space-y-1.5 text-xs text-slate-600 dark:text-slate-300">
                    {cert.verifiedSkills.map((sk) => (
                      <li key={sk}>· {sk}</li>
                    ))}
                  </ul>
                </div>

                <div className="pt-3 border-t border-slate-200/80 dark:border-slate-800/80 space-y-2">
                  <div className="flex items-center justify-between text-[11px] font-mono tabular-nums text-slate-500 dark:text-slate-400">
                    <span>Progress: {xpProgressPct}%</span>
                    <span>
                      {cert.credentialSha256
                        ? `SHA-256: ${cert.credentialSha256.slice(0, 18)}…`
                        : `${Math.max(0, cert.requiredXp - academy.learner.totalXp)} XP remaining`}
                    </span>
                  </div>
                  <div className="w-full h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-transform duration-200 origin-left ${
                        cert.unlocked ? 'bg-emerald-500' : 'bg-amber-400'
                      }`}
                      style={{ transform: `scaleX(${xpProgressPct / 100})` }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Instant Employer / Investor Credential Verifier */}
        <form
          onSubmit={handleVerifyCredentialHash}
          className="p-5 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800/80 rounded-2xl flex flex-col sm:flex-row items-stretch sm:items-center gap-3"
        >
          <label htmlFor="verify-cred-sha" className="text-xs font-semibold text-slate-700 dark:text-slate-300 shrink-0">
            Employer Instant Hash Verifier:
          </label>
          <input
            id="verify-cred-sha"
            type="text"
            value={verifyInputSha}
            onChange={(e) => setVerifyInputSha(e.target.value)}
            placeholder={
              highestUnlockedCert.credentialSha256?.slice(0, 24) ??
              'Paste credential SHA-256 prefix...'
            }
            className="flex-1 px-3.5 py-2 text-xs font-mono bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 rounded-lg text-slate-900 dark:text-slate-100"
          />
          <button
            type="submit"
            className="px-4 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap shrink-0"
          >
            Verify Digest
          </button>
          {highestUnlockedCert.credentialSha256 && (
            <button
              type="button"
              onClick={() =>
                setVerifyInputSha(highestUnlockedCert.credentialSha256!.slice(0, 20))
              }
              className="px-3 py-2 text-xs font-medium text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 whitespace-nowrap shrink-0"
            >
              Use My Unlocked SHA
            </button>
          )}
        </form>
        {verifyFeedback && (
          <p
            role="status"
            className={`text-xs font-mono ${
              verifyFeedback.valid
                ? 'text-emerald-700 dark:text-emerald-400'
                : 'text-amber-700 dark:text-amber-400'
            }`}
          >
            {verifyFeedback.message}
          </p>
        )}
      </section>

      {/* SECTION 04: COMPETITOR DISMANTLE MATRIX & IMMEDIATE MONEY-MAKER ARR SIMULATOR */}
      <section aria-labelledby="asymmetry-venture-heading" className="space-y-6">
        <div>
          <h2
            id="asymmetry-venture-heading"
            className="text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-50"
          >
            04. Industry Dismantle Matrix &amp; Asymmetric Revenue Simulator
          </h2>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-0.5">
            Every structural weakness in legacy universities, video MOOCs, toy apps, and CRUD
            bootcamps converted into a 96%+ gross-margin cash-flow engine.
          </p>
        </div>

        {/* Competitor Dismantle Table */}
        <div className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800/80 rounded-2xl overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-xs text-slate-500 dark:text-slate-400">
                <th className="py-3.5 px-4 font-semibold">Legacy Category</th>
                <th className="py-3.5 px-4 font-semibold">Cost &amp; Completion</th>
                <th className="py-3.5 px-4 font-semibold">Structural Weakness</th>
                <th className="py-3.5 px-4 font-semibold">Genesis Asymmetric Capture</th>
                <th className="py-3.5 px-4 font-semibold">Leverage</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200/80 dark:divide-slate-800/80 text-xs">
              {academy.competitorMatrix.map((row) => (
                <tr key={row.competitorCategory} className="align-top">
                  <td className="py-4 px-4">
                    <div className="font-semibold text-slate-900 dark:text-slate-100">
                      {row.competitorCategory}
                    </div>
                    <div className="text-slate-500 dark:text-slate-400 mt-0.5">{row.examples}</div>
                  </td>
                  <td className="py-4 px-4 font-mono tabular-nums text-slate-700 dark:text-slate-300">
                    <div>{row.legacyCostAndTime}</div>
                    <div className="text-rose-600 dark:text-rose-400 mt-0.5">
                      {row.completionOrOutcomeRate}
                    </div>
                  </td>
                  <td className="py-4 px-4 text-slate-600 dark:text-slate-400 max-w-xs leading-relaxed">
                    {row.structuralWeakness}
                  </td>
                  <td className="py-4 px-4 text-slate-800 dark:text-slate-200 max-w-xs leading-relaxed">
                    {row.genesisAsymmetricKillMove}
                  </td>
                  <td className="py-4 px-4 font-mono tabular-nums font-semibold text-emerald-700 dark:text-emerald-400 whitespace-nowrap">
                    {row.leverageMultiplier}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Interactive Venture ARR & Gross Margin Simulator */}
        <div className="p-6 sm:p-7 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800/80 rounded-2xl grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          <div className="lg:col-span-6 space-y-4">
            <h3 className="text-base font-semibold text-slate-900 dark:text-slate-50">
              Live Investor Unit-Economics &amp; Cash-Flow Simulator
            </h3>

            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <label
                    htmlFor="sim-free-learners"
                    className="font-medium text-slate-700 dark:text-slate-300"
                  >
                    Monthly Free Social Spark Learners
                  </label>
                  <span className="font-mono tabular-nums font-semibold text-slate-900 dark:text-slate-100">
                    {freeLearnersMonthly.toLocaleString()} learners / mo
                  </span>
                </div>
                <input
                  id="sim-free-learners"
                  type="range"
                  min={5000}
                  max={250000}
                  step={5000}
                  value={freeLearnersMonthly}
                  onChange={(e) => setFreeLearnersMonthly(Number(e.target.value))}
                  className="w-full accent-amber-500 cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <label
                    htmlFor="sim-pro-conv"
                    className="font-medium text-slate-700 dark:text-slate-300"
                  >
                    Pro Builder ($29/mo) Lab &amp; Cert Conversion
                  </label>
                  <span className="font-mono tabular-nums font-semibold text-slate-900 dark:text-slate-100">
                    {proConversionPct.toFixed(1)}% ({liveRevenueSim.paidProSubscribers.toLocaleString()} subs)
                  </span>
                </div>
                <input
                  id="sim-pro-conv"
                  type="range"
                  min={1}
                  max={12}
                  step={0.5}
                  value={proConversionPct}
                  onChange={(e) => setProConversionPct(Number(e.target.value))}
                  className="w-full accent-amber-500 cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <label
                    htmlFor="sim-ent-seats"
                    className="font-medium text-slate-700 dark:text-slate-300"
                  >
                    Enterprise Workforce Upskilling Seats ($499/yr)
                  </label>
                  <span className="font-mono tabular-nums font-semibold text-slate-900 dark:text-slate-100">
                    {enterpriseSeats.toLocaleString()} seats
                  </span>
                </div>
                <input
                  id="sim-ent-seats"
                  type="range"
                  min={50}
                  max={5000}
                  step={50}
                  value={enterpriseSeats}
                  onChange={(e) => setEnterpriseSeats(Number(e.target.value))}
                  className="w-full accent-amber-500 cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <label
                    htmlFor="sim-hires"
                    className="font-medium text-slate-700 dark:text-slate-300"
                  >
                    Verified Cert Employer Placements ($1,800 flat)
                  </label>
                  <span className="font-mono tabular-nums font-semibold text-slate-900 dark:text-slate-100">
                    {verifiedHiresMonthly} hires / mo
                  </span>
                </div>
                <input
                  id="sim-hires"
                  type="range"
                  min={0}
                  max={100}
                  step={2}
                  value={verifiedHiresMonthly}
                  onChange={(e) => setVerifiedHiresMonthly(Number(e.target.value))}
                  className="w-full accent-amber-500 cursor-pointer"
                />
              </div>
            </div>
          </div>

          <div className="lg:col-span-6 grid grid-cols-2 gap-4 p-5 bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 rounded-xl">
            <div>
              <div className="text-xs text-slate-500 dark:text-slate-400">Modeled Monthly MRR</div>
              <div className="mt-1 text-2xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-50">
                ${liveRevenueSim.totalMrrUsd.toLocaleString()}
              </div>
              <div className="text-[11px] text-slate-500 dark:text-slate-400 font-mono tabular-nums mt-0.5">
                Pro ${liveRevenueSim.proMrrUsd.toLocaleString()} + Ent $
                {liveRevenueSim.enterpriseMrrEquivalentUsd.toLocaleString()}
              </div>
            </div>

            <div>
              <div className="text-xs text-slate-500 dark:text-slate-400">Annualized Run-Rate (ARR)</div>
              <div className="mt-1 text-2xl font-bold font-mono tabular-nums text-amber-600 dark:text-amber-400">
                ${liveRevenueSim.annualizedArrUsd.toLocaleString()}
              </div>
              <div className="text-[11px] text-slate-500 dark:text-slate-400 font-mono tabular-nums mt-0.5">
                Placements +${liveRevenueSim.placementMrrUsd.toLocaleString()}/mo
              </div>
            </div>

            <div className="pt-3 border-t border-slate-200 dark:border-slate-800">
              <div className="text-xs text-slate-500 dark:text-slate-400">
                SaaS Gross Margin (Free-Lane Powered)
              </div>
              <div className="mt-1 text-xl font-bold font-mono tabular-nums text-emerald-700 dark:text-emerald-400">
                {liveRevenueSim.grossMarginPct}% ●
              </div>
              <div className="text-[11px] text-slate-500 dark:text-slate-400 font-mono tabular-nums mt-0.5">
                Compute COGS: ${liveRevenueSim.marginalComputeCostMrrUsd.toLocaleString()}/mo
              </div>
            </div>

            <div className="pt-3 border-t border-slate-200 dark:border-slate-800">
              <div className="text-xs text-slate-500 dark:text-slate-400">
                Paid Acquisition Cost (Viral Spark Loop)
              </div>
              <div className="mt-1 text-xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-50">
                ${liveRevenueSim.cacUsd} CAC · {liveRevenueSim.paybackDays}d Payback
              </div>
              <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                45s social cards + employer cert links drive organic loop
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
