import React, { useState } from 'react';
import {
  AlertTriangle,
  ArrowUpRight,
  BookOpen,
  CheckCircle2,
  ClipboardCheck,
  RotateCcw,
  ShieldAlert,
  Sliders,
  XCircle,
} from 'lucide-react';
import academyPlateImg from '../assets/images/genesis_academy_simulation_1794814572059.jpg';
import type { AcademyLevel } from '../engine/founderRegoChronosPlane';
import {
  evaluateUnseenTransferPilot,
  simulateStandoutAcademyTrack,
  STANDOUT_TRACK_CATALOG,
  type StandoutTrackId,
  type TransferPilotEvaluation,
} from '../engine/genesisAcademyEngine';
import type { NavTabId } from '../types/api';

interface GenesisAcademyProps {
  onNavigateTab: (tab: NavTabId) => void;
}

const LEVELS: Array<{ id: AcademyLevel; label: string; audience: string }> = [
  { id: 'novice', label: 'Total Novice', audience: 'First-principles intuition, zero jargon' },
  { id: 'practitioner', label: 'Practitioner', audience: 'Applied quantitative systems engineering' },
  { id: 'expert', label: 'Principal / Expert', audience: 'Formal bounds, failure modes & invariants' },
  { id: 'founder', label: 'Founder & Architect', audience: 'Unit economics, moats & enterprise IP' },
];

export function GenesisAcademy({ onNavigateTab }: GenesisAcademyProps) {
  const [level, setLevel] = useState<AcademyLevel>('novice');
  const [trackId, setTrackId] = useState<StandoutTrackId>('reproducibility_transfer_boundaries');
  const [sliderParam, setSliderParam] = useState<number>(92);
  const [activeFaultIds, setActiveFaultIds] = useState<string[]>([]);
  const [plateImgFailed, setPlateImgFailed] = useState(false);

  // Unseen Transfer Pilot state (per-track answers + post-submission evaluation only)
  const [draftAnswersByTrack, setDraftAnswersByTrack] = useState<
    Record<string, Record<string, number | undefined>>
  >({});
  const [pilotEvaluationByTrack, setPilotEvaluationByTrack] = useState<
    Record<string, TransferPilotEvaluation | undefined>
  >({});
  const [submittingTransfer, setSubmittingTransfer] = useState(false);

  const sim = simulateStandoutAcademyTrack({
    trackId,
    level,
    sliderParam,
    activeFaultIds,
  });

  const currentAnswers = draftAnswersByTrack[trackId] ?? {};
  const currentEvaluation = pilotEvaluationByTrack[trackId];

  const completedPilotsCount = STANDOUT_TRACK_CATALOG.filter(
    (t) => pilotEvaluationByTrack[t.id]?.complete
  ).length;

  function handleSelectTrack(nextId: StandoutTrackId) {
    const meta = STANDOUT_TRACK_CATALOG.find((t) => t.id === nextId) ?? STANDOUT_TRACK_CATALOG[0];
    setTrackId(nextId);
    setSliderParam(meta.defaultSliderValue);
    setActiveFaultIds([]);
  }

  function handleToggleFault(faultId: string) {
    setActiveFaultIds((prev) =>
      prev.includes(faultId) ? prev.filter((id) => id !== faultId) : [...prev, faultId]
    );
  }

  function handleResetLab() {
    setSliderParam(sim.defaultSliderValue);
    setActiveFaultIds([]);
  }

  function handlePickTransferOption(itemId: string, optionIndex: number) {
    setDraftAnswersByTrack((prev) => ({
      ...prev,
      [trackId]: {
        ...(prev[trackId] ?? {}),
        [itemId]: optionIndex,
      },
    }));
    // Clear any prior incomplete validation error or stale score when learner changes an answer
    if (currentEvaluation) {
      setPilotEvaluationByTrack((prev) => ({
        ...prev,
        [trackId]: undefined,
      }));
    }
  }

  async function handleSubmitTransferPilot(e: React.FormEvent) {
    e.preventDefault();
    setSubmittingTransfer(true);
    try {
      const res = await fetch('/api/academy/transfer-submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          trackId,
          selectedAnswers: currentAnswers,
        }),
      });
      const evaluated = (await res.json()) as TransferPilotEvaluation;
      setPilotEvaluationByTrack((prev) => ({
        ...prev,
        [trackId]: evaluated,
      }));
    } catch {
      const fallback = evaluateUnseenTransferPilot({
        trackId,
        selectedAnswers: currentAnswers,
      });
      setPilotEvaluationByTrack((prev) => ({
        ...prev,
        [trackId]: fallback,
      }));
    } finally {
      setSubmittingTransfer(false);
    }
  }

  function handleRetakeTransferPilot() {
    setDraftAnswersByTrack((prev) => ({
      ...prev,
      [trackId]: {},
    }));
    setPilotEvaluationByTrack((prev) => ({
      ...prev,
      [trackId]: undefined,
    }));
  }

  // SVG Coordinate Helper (generous padTop = 32 so top data labels never crowd Y=100)
  const svgW = 640;
  const svgH = 244;
  const padLeft = 48;
  const padRight = 24;
  const padTop = 32;
  const padBottom = 34;
  const plotW = svgW - padLeft - padRight;
  const plotH = svgH - padTop - padBottom;

  const pts = sim.curvePoints;
  const mapX = (index: number) =>
    padLeft + (pts.length > 1 ? (index / (pts.length - 1)) * plotW : plotW / 2);
  const mapY = (valPct: number) => {
    const clampedY = Math.max(0, Math.min(100, valPct));
    return padTop + plotH - (clampedY / 100) * plotH;
  };

  const primaryPolyline = pts.map((pt, idx) => `${mapX(idx)},${mapY(pt.primaryY)}`).join(' ');
  const baselinePolyline = pts.map((pt, idx) => `${mapX(idx)},${mapY(pt.baselineY)}`).join(' ');

  const answeredCount = sim.unseenTransferItems.filter(
    (item) => typeof currentAnswers[item.id] === 'number'
  ).length;

  return (
    <div className="space-y-6">
      {/* 1. Standout Academy Header & 4-Tier Learner Depth Lens */}
      <section className="bg-white border border-slate-200 rounded-lg p-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
          <div className="lg:col-span-8 space-y-3">
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
              <span>Genesis Academy · Standout Systems Pedagogy</span>
              <span aria-hidden="true">·</span>
              <span>Tri-Representational Convergence &amp; Unseen Transfer</span>
              <span aria-hidden="true">·</span>
              <span className="font-mono tabular-nums text-slate-700">
                Transfer Pilots Scored: {completedPilotsCount}/{STANDOUT_TRACK_CATALOG.length}
              </span>
            </div>

            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 [text-wrap:balance]">
              First Principles, Boundary Counterexamples &amp; Unseen Domain Transfer.
            </h2>

            <p className="text-sm text-slate-600 max-w-2xl leading-relaxed">
              True understanding requires knowing both why a mechanism works and exactly when its
              preconditions break. Every track converges a physical isomorphism, a formal boundary
              equation, and a live Meridian production engine — then tests objective transfer in
              three unseen real-world domains.
            </p>

            {/* Learner Depth Lens Switcher */}
            <div className="pt-2">
              <div className="text-xs font-medium text-slate-700 mb-1.5">
                Select Learner Depth Lens
              </div>
              <div
                role="tablist"
                aria-label="Learner depth lens"
                className="inline-flex flex-wrap items-center gap-1 p-1 bg-slate-100 rounded-lg"
              >
                {LEVELS.map((lvl) => {
                  const active = level === lvl.id;
                  return (
                    <button
                      key={lvl.id}
                      type="button"
                      role="tab"
                      aria-selected={active}
                      onClick={() => setLevel(lvl.id)}
                      className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                        active
                          ? 'bg-white text-slate-900 shadow-xs'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      {lvl.label}
                    </button>
                  );
                })}
              </div>
              <div className="mt-1.5 text-xs text-slate-500">
                Active lens: <span className="font-medium text-slate-700">{LEVELS.find((l) => l.id === level)?.label}</span> —{' '}
                {LEVELS.find((l) => l.id === level)?.audience}
              </div>
            </div>
          </div>

          <div className="lg:col-span-4">
            <div className="rounded-lg overflow-hidden border border-slate-200 bg-slate-900 aspect-[4/3] relative">
              {!plateImgFailed ? (
                <img
                  src={academyPlateImg}
                  alt="Harmonic clockwork rings and Vandermonde mathematical lattice plate"
                  referrerPolicy="no-referrer"
                  onError={() => setPlateImgFailed(true)}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex flex-col items-center justify-center p-4 text-center text-slate-200">
                  <BookOpen className="h-7 w-7 text-blue-400 mb-2" aria-hidden="true" />
                  <span className="text-xs font-semibold">Systema Chronoscopium</span>
                </div>
              )}
              <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/85 via-black/45 to-transparent p-3 text-white">
                <div className="text-xs font-medium">
                  Track {sim.indexLabel}: {sim.shortTitle}
                </div>
                <div className="text-[11px] text-slate-300">
                  Break preconditions below, then test unseen transfer
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. 6-Track Curriculum Selector */}
      <section aria-label="Curriculum tracks">
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
          {STANDOUT_TRACK_CATALOG.map((mod) => {
            const isCurrent = mod.id === trackId;
            const evalForMod = pilotEvaluationByTrack[mod.id];
            return (
              <button
                key={mod.id}
                type="button"
                onClick={() => handleSelectTrack(mod.id)}
                className={`text-left rounded-lg border p-4 transition-colors ${
                  isCurrent
                    ? 'bg-slate-900 border-slate-900 text-white'
                    : 'bg-white border-slate-200 text-slate-900 hover:bg-slate-50'
                }`}
              >
                <div className="flex items-center justify-between gap-2 text-xs">
                  <span className={`font-mono ${isCurrent ? 'text-slate-300' : 'text-slate-500'}`}>
                    Track {mod.indexLabel}
                  </span>
                  {evalForMod?.complete && (
                    <span
                      className={`inline-flex items-center gap-1 font-mono tabular-nums font-medium ${
                        isCurrent ? 'text-emerald-300' : 'text-emerald-700'
                      }`}
                    >
                      <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                      Pilot {evalForMod.score}/3
                    </span>
                  )}
                </div>
                <div className="mt-1 text-sm font-semibold">{mod.shortTitle}</div>
                <div
                  className={`mt-0.5 text-xs truncate ${
                    isCurrent ? 'text-slate-300' : 'text-slate-500'
                  }`}
                >
                  {mod.subtitle}
                </div>
              </button>
            );
          })}
        </div>
      </section>

      {/* 3. Shared Principle & Tri-Representational Convergence Matrix */}
      <section className="bg-white border border-slate-200 rounded-lg p-6 space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-4">
          <div className="space-y-1 max-w-3xl">
            <div className="text-xs font-medium text-blue-700">
              Tri-Representational Convergence · Track {sim.indexLabel}
            </div>
            <h3 className="text-lg sm:text-xl font-bold text-slate-900">{sim.title}</h3>
            <p className="text-sm font-medium text-slate-800 pt-1">
              {sim.sharedPrincipleStatement}
            </p>
          </div>
          <button
            type="button"
            onClick={() => onNavigateTab(sim.linkedTab)}
            className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-3.5 py-2 text-xs font-medium text-slate-800 hover:bg-slate-50 transition-colors whitespace-nowrap shrink-0"
          >
            {sim.linkedTabLabel}
            <ArrowUpRight className="h-3.5 w-3.5 text-blue-700" aria-hidden="true" />
          </button>
        </div>

        {/* Depth-Adapted Synthesis Callout */}
        <div className="bg-slate-50 border border-slate-200 rounded-md p-4">
          <div className="text-xs font-semibold text-slate-900">
            {LEVELS.find((l) => l.id === level)?.label} Synthesis
          </div>
          <p className="mt-1 text-sm text-slate-700 leading-relaxed">{sim.levelSynthesis}</p>
        </div>

        {/* 3 Converging Representations (Analogy + Formal Law + Production Engine, each with Boundary Limit) */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-stretch">
          {sim.representations.map((rep) => (
            <div
              key={rep.id}
              className="border border-slate-200 rounded-lg p-4 flex flex-col justify-between space-y-3 bg-white"
            >
              <div className="space-y-2">
                <div className="text-[11px] font-mono font-semibold text-slate-500 uppercase tracking-wider">
                  {rep.label}
                </div>
                <h4 className="text-sm font-semibold text-slate-900">{rep.title}</h4>
                <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">{rep.body}</p>
              </div>
              <div className="pt-3 border-t border-slate-100 text-xs text-amber-900 bg-amber-50/60 -mx-4 -mb-4 p-3 rounded-b-lg">
                <span className="font-semibold">Boundary condition: </span>
                {rep.explicitBoundaryLimit}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 4. Interactive Mathematical Stage & Boundary Counterexample Lab */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left 8 Cols: Governing Equation + Live SVG Curve + Active Fault Consequences */}
        <div className="lg:col-span-8 bg-white border border-slate-200 rounded-lg p-6 space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-xs text-slate-500">Interactive Boundary Counterexample Stage</div>
              <h4 className="text-base font-semibold text-slate-900">
                Observe Equilibrium Under Intact vs Violated Preconditions
              </h4>
            </div>
            <span
              className={`text-xs font-mono tabular-nums font-semibold ${
                sim.boundaryViolated ? 'text-red-700' : 'text-emerald-700'
              }`}
            >
              {sim.equilibriumStatusLabel}
            </span>
          </div>

          <div className="bg-slate-50 border border-slate-200 rounded-md px-4 py-3">
            <div className="text-[11px] text-slate-500">Governing Formal Precondition Law</div>
            <div className="mt-1 text-xs sm:text-sm font-mono tabular-nums text-slate-900 overflow-x-auto">
              {sim.governingEquation}
            </div>
          </div>

          <div className="border border-slate-200 rounded-md p-3 bg-white">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-600 mb-2">
              <div className="flex flex-wrap items-center gap-4">
                <span
                  className={`inline-flex items-center gap-1.5 font-medium ${
                    sim.boundaryViolated ? 'text-red-700' : 'text-blue-700'
                  }`}
                >
                  <span
                    className={`inline-block w-3 h-0.5 ${
                      sim.boundaryViolated ? 'bg-red-600' : 'bg-blue-600'
                    }`}
                    aria-hidden="true"
                  />
                  Verified System Outcome
                </span>
                <span className="inline-flex items-center gap-1.5 text-slate-500">
                  <span className="inline-block w-3 h-0.5 bg-amber-600" aria-hidden="true" />
                  Naive &ldquo;Instructions / Badge Alone&rdquo; Assumption
                </span>
              </div>
              <span className="font-mono tabular-nums text-slate-700">
                {sim.primaryMetricLabel}: <strong>{sim.primaryMetricValue}</strong>
              </span>
            </div>

            <svg
              viewBox={`0 0 ${svgW} ${svgH}`}
              role="img"
              aria-label={`Interactive boundary curve for ${sim.title}`}
              className="w-full h-auto"
            >
              {[0, 25, 50, 75, 100].map((gridVal) => {
                const gy = mapY(gridVal);
                return (
                  <g key={gridVal}>
                    <line
                      x1={padLeft}
                      y1={gy}
                      x2={svgW - padRight}
                      y2={gy}
                      stroke="#e2e8f0"
                      strokeDasharray="3 3"
                    />
                    <text
                      x={padLeft - 8}
                      y={gy + 4}
                      textAnchor="end"
                      className="fill-slate-500 text-[10px] font-mono"
                    >
                      {gridVal}
                    </text>
                  </g>
                );
              })}

              {/* Baseline naive curve */}
              <polyline
                fill="none"
                stroke="#d97706"
                strokeWidth="2"
                strokeDasharray="5 4"
                points={baselinePolyline}
              />

              {/* Primary actual curve */}
              <polyline
                fill="none"
                stroke={sim.boundaryViolated ? '#dc2626' : '#0284c7'}
                strokeWidth="2.75"
                points={primaryPolyline}
              />

              {pts.map((pt, idx) => {
                const cx = mapX(idx);
                const cy = mapY(pt.primaryY);
                return (
                  <g key={pt.xLabel}>
                    <circle
                      cx={cx}
                      cy={cy}
                      r="4"
                      fill={sim.boundaryViolated ? '#dc2626' : '#0284c7'}
                    />
                    <text
                      x={cx}
                      y={cy - 9}
                      textAnchor="middle"
                      className="fill-slate-800 text-[10px] font-mono"
                    >
                      {pt.primaryY}
                    </text>
                    <text
                      x={cx}
                      y={svgH - 10}
                      textAnchor="middle"
                      className="fill-slate-500 text-[10px] font-mono"
                    >
                      {pt.xLabel}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          {sim.activeViolationConsequences.length > 0 && (
            <div
              role="status"
              className="rounded-md border border-red-200 bg-red-50/70 p-4 space-y-2 text-xs text-red-950"
            >
              <div className="font-semibold flex items-center gap-1.5">
                <ShieldAlert className="h-4 w-4 text-red-700 shrink-0" aria-hidden="true" />
                Active Precondition Failure Diagnosis ({sim.activeViolationConsequences.length}{' '}
                triggered)
              </div>
              <ul className="list-disc pl-5 space-y-1 leading-relaxed">
                {sim.activeViolationConsequences.map((msg) => (
                  <li key={msg}>{msg}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Right 4 Cols: Parameter Control Deck + 3 Boundary Fault Injectors */}
        <div className="lg:col-span-4 space-y-4">
          <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold text-slate-900 flex items-center gap-1.5">
                <Sliders className="h-4 w-4 text-blue-700" aria-hidden="true" />
                Parameter &amp; Counterexample Deck
              </h4>
              <button
                type="button"
                onClick={handleResetLab}
                className="inline-flex items-center gap-1 text-xs text-slate-600 hover:text-slate-900 whitespace-nowrap"
              >
                <RotateCcw className="h-3 w-3" aria-hidden="true" />
                Reset Clean State
              </button>
            </div>

            <div>
              <div className="flex justify-between text-xs font-medium text-slate-700 mb-1.5">
                <label htmlFor="academy-param-slider">{sim.sliderLabel}</label>
                <span className="font-mono tabular-nums font-semibold text-slate-900">
                  {sliderParam}
                  {sim.sliderUnit}
                </span>
              </div>
              <input
                id="academy-param-slider"
                type="range"
                min={55}
                max={98}
                step={1}
                value={sliderParam}
                onChange={(e) => setSliderParam(Number(e.target.value))}
                className="w-full accent-slate-900"
              />
              <div className="flex justify-between text-[11px] font-mono tabular-nums text-slate-400 mt-1">
                <span>55{sim.sliderUnit}</span>
                <span>76{sim.sliderUnit}</span>
                <span>98{sim.sliderUnit}</span>
              </div>
            </div>

            {/* 3 Concrete Precondition / Boundary Fault Toggles */}
            <div className="pt-3 border-t border-slate-100 space-y-2">
              <div className="text-xs font-semibold text-slate-900">
                Break a Necessary Precondition (Counterexample Lab)
              </div>
              <p className="text-[11px] text-slate-500">
                Toggle missing dependencies or shortcuts to verify that code/instructions alone
                cannot compensate:
              </p>

              <div className="space-y-2 pt-1">
                {sim.boundaryToggles.map((toggle) => {
                  const isFaultActive = activeFaultIds.includes(toggle.id);
                  return (
                    <button
                      key={toggle.id}
                      type="button"
                      aria-pressed={isFaultActive}
                      onClick={() => handleToggleFault(toggle.id)}
                      className={`w-full text-left rounded-md border p-3 text-xs transition-colors flex items-start justify-between gap-2 ${
                        isFaultActive
                          ? 'border-red-600 bg-red-50/80 text-red-950 font-medium'
                          : 'border-slate-200 bg-white text-slate-800 hover:bg-slate-50'
                      }`}
                    >
                      <span>{toggle.label}</span>
                      <span
                        className={`font-mono text-[10px] shrink-0 mt-0.5 ${
                          isFaultActive ? 'text-red-700 font-semibold' : 'text-slate-400'
                        }`}
                      >
                        {isFaultActive ? 'FAULT ON' : 'INTACT'}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 pt-3 border-t border-slate-100">
              <div>
                <div className="text-[11px] text-slate-500">{sim.primaryMetricLabel}</div>
                <div
                  className={`mt-0.5 text-lg font-bold font-mono tabular-nums ${
                    sim.boundaryViolated ? 'text-red-700' : 'text-slate-900'
                  }`}
                >
                  {sim.primaryMetricValue}
                </div>
              </div>
              <div>
                <div className="text-[11px] text-slate-500">{sim.secondaryMetricLabel}</div>
                <div className="mt-0.5 text-lg font-bold font-mono tabular-nums text-slate-900">
                  {sim.secondaryMetricValue}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 5. Objective Unseen Transfer Challenge (Evaluated Strictly After Submission) */}
      <section className="bg-white border border-slate-200 rounded-lg p-6 space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-4">
          <div className="space-y-1 max-w-3xl">
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
              <span className="font-medium text-slate-800">
                Your Unseen Transfer Challenge · Track {sim.indexLabel}
              </span>
              <span aria-hidden="true">·</span>
              <span className="font-mono tabular-nums">
                {answeredCount}/3 Unseen Items Selected
              </span>
            </div>
            <h3 className="text-xl font-bold text-slate-900">
              Apply the Governing Relationship to Three Unseen Domains
            </h3>
            <p className="text-sm text-slate-600">
              Answers are evaluated strictly after you submit all three items — testing genuine
              structural transfer rather than recall of Meridian terminology.
            </p>
          </div>

          {currentEvaluation?.complete && (
            <button
              type="button"
              onClick={handleRetakeTransferPilot}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3.5 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors whitespace-nowrap shrink-0"
            >
              <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
              Clear &amp; Re-Attempt Pilot
            </button>
          )}
        </div>

        <form onSubmit={handleSubmitTransferPilot} className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 items-stretch">
            {sim.unseenTransferItems.map((item) => {
              const pickedIdx = currentAnswers[item.id];
              const scoredItem = currentEvaluation?.complete
                ? currentEvaluation.itemResults.find((r) => r.itemId === item.id)
                : undefined;

              return (
                <fieldset
                  key={item.id}
                  className="border border-slate-200 rounded-lg p-5 flex flex-col justify-between space-y-4 bg-white"
                >
                  <div className="space-y-2">
                    <div className="text-[11px] font-mono text-slate-500">{item.domainKicker}</div>
                    <legend className="text-base font-semibold text-slate-900">{item.title}</legend>
                    <p className="text-xs sm:text-sm text-slate-700 leading-relaxed">
                      {item.scenario}
                    </p>
                  </div>

                  <div className="space-y-2 pt-1">
                    {item.options.map((optText, optIdx) => {
                      const isSelected = pickedIdx === optIdx;
                      const isSubmitted = Boolean(scoredItem);
                      const isCorrectChoice = scoredItem?.correctOptionIndex === optIdx;

                      let borderClass = 'border-slate-200 bg-white hover:bg-slate-50 text-slate-800';
                      if (isSubmitted) {
                        if (isCorrectChoice) {
                          borderClass = 'border-emerald-600 bg-emerald-50/70 text-slate-900';
                        } else if (isSelected && !scoredItem?.correct) {
                          borderClass = 'border-red-600 bg-red-50/70 text-slate-900';
                        }
                      } else if (isSelected) {
                        borderClass = 'border-slate-900 bg-slate-900/5 text-slate-900 font-medium';
                      }

                      const inputId = `${item.id}-opt-${optIdx}`;
                      return (
                        <label
                          key={inputId}
                          htmlFor={inputId}
                          className={`flex items-start gap-2.5 rounded-md border p-3 text-xs leading-relaxed cursor-pointer transition-colors ${borderClass}`}
                        >
                          <input
                            id={inputId}
                            type="radio"
                            name={item.id}
                            checked={isSelected}
                            onChange={() => handlePickTransferOption(item.id, optIdx)}
                            className="mt-0.5 accent-slate-900 shrink-0"
                          />
                          <span>{optText}</span>
                        </label>
                      );
                    })}
                  </div>

                  {scoredItem && (
                    <div className="pt-3 border-t border-slate-100 space-y-1.5 text-xs leading-relaxed">
                      <div
                        className={`font-semibold flex items-center gap-1.5 ${
                          scoredItem.correct ? 'text-emerald-800' : 'text-red-800'
                        }`}
                      >
                        {scoredItem.correct ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" aria-hidden="true" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-600 shrink-0" aria-hidden="true" />
                        )}
                        <span>
                          {scoredItem.correct
                            ? 'Objective Transfer Verified'
                            : `Incorrect — Expected: "${scoredItem.correctText}"`}
                        </span>
                      </div>
                      <p className="text-slate-700">{scoredItem.transferExplanation}</p>
                      <p className="text-slate-500">
                        <span className="font-medium text-slate-700">Why distractors fail: </span>
                        {scoredItem.distractorDiagnosis}
                      </p>
                    </div>
                  )}
                </fieldset>
              );
            })}
          </div>

          {/* Validation Error if < 3 items answered */}
          {currentEvaluation && !currentEvaluation.complete && currentEvaluation.validationError && (
            <div
              role="alert"
              className="rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-xs font-medium text-amber-950 flex items-center gap-2"
            >
              <AlertTriangle className="h-4 w-4 text-amber-700 shrink-0" aria-hidden="true" />
              <span>{currentEvaluation.validationError}</span>
            </div>
          )}

          {/* Submit Bar + Explicit Research-Pilot Epistemic Honesty */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2 border-t border-slate-100">
            <div className="text-xs text-slate-500 max-w-2xl leading-relaxed">
              <span className="font-medium text-slate-700">Research pilot</span> · Three objective
              transfer items · No claim of established long-term mastery or certified teaching
              efficacy. Your answers are evaluated after submission.
            </div>

            <button
              type="submit"
              disabled={submittingTransfer}
              className="inline-flex items-center justify-center gap-2 rounded-md bg-slate-900 px-5 py-2.5 text-xs font-semibold text-white hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0 disabled:opacity-50"
            >
              <ClipboardCheck className="h-4 w-4 text-emerald-400" aria-hidden="true" />
              {submittingTransfer ? 'Scoring Transfer…' : 'Submit and Score My Transfer'}
            </button>
          </div>
        </form>

        {/* Post-Submission Scored Pilot Receipt */}
        {currentEvaluation?.complete && (
          <div
            role="status"
            className="rounded-lg border border-slate-200 bg-slate-50 p-5 space-y-2"
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="text-sm font-bold text-slate-900 font-mono tabular-nums">
                Transfer Pilot Score: {currentEvaluation.score} / {currentEvaluation.totalItems}{' '}
                Objective Unseen Items Correct
              </div>
              <div className="text-xs font-mono tabular-nums text-slate-600">
                Pilot Receipt SHA-256: {currentEvaluation.receiptSha256.slice(0, 20)}…
              </div>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              {currentEvaluation.epistemicDisclaimer}
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
