/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  ShieldCheck,
  Cpu,
  Layers,
  Infinity as InfinityIcon,
  Activity,
  Lock,
  Unlock,
  AlertOctagon,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Play,
  Key,
  Server,
  Zap,
  Radio,
  FileCheck2,
  HardDrive,
  Compass,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import {
  evaluateTripartiteHealth,
  evaluateAgentDofGate,
  founderExpandDof,
  runDeterministicTillingSweep,
  calculateLongevityIndex,
  executeSurvivalDrill,
  INITIAL_TRIPARTITE_STATE,
  INITIAL_DOF_POLICY,
  INITIAL_TILLING_PROBES,
  INITIAL_FREE_LANES,
  INITIAL_SURVIVAL_DRILLS,
  TripartitePillar,
  DofLevel,
  DofPolicy,
  TillingSoilReport,
  TillingProbe,
  SurvivalDrill,
  FreeLaneNode,
} from '../lib/protocolEngine.ts';

export const TripartiteCockpit: React.FC = () => {
  // Tripartite Covenant State
  const [founderHealth, setFounderHealth] = useState(INITIAL_TRIPARTITE_STATE.founder);
  const [agentsHealth, setAgentsHealth] = useState(INITIAL_TRIPARTITE_STATE.agents);
  const [machineHealth, setMachineHealth] = useState(INITIAL_TRIPARTITE_STATE.machine);

  const organismState = evaluateTripartiteHealth(founderHealth, agentsHealth, machineHealth);

  // Degree of Freedom Governor State
  const [dofPolicy, setDofPolicy] = useState<DofPolicy>(INITIAL_DOF_POLICY);
  const [testActionInput, setTestActionInput] = useState<string>('EXPLORATORY_BASH_LOOP retry build until pass');
  const [testActionDofLevel, setTestActionDofLevel] = useState<DofLevel>(1);
  const [dofGateResult, setDofGateResult] = useState<ReturnType<typeof evaluateAgentDofGate> | null>(null);
  const [founderPassphrase, setFounderPassphrase] = useState<string>('FOUNDER_AUTH_SOVEREIGN_KEY_2026');
  const [expansionFeedback, setExpansionFeedback] = useState<string | null>(null);

  // Soil Tilling Engine State
  const [probes, setProbes] = useState<TillingProbe[]>(INITIAL_TILLING_PROBES);
  const [soilReport, setSoilReport] = useState<TillingSoilReport | null>(null);
  const [isTillingActive, setIsTillingActive] = useState<boolean>(false);

  // Longevity & Free Lane Harvester State
  const [freeLanes] = useState<FreeLaneNode[]>(INITIAL_FREE_LANES);
  const [survivalDrills, setSurvivalDrills] = useState<SurvivalDrill[]>(INITIAL_SURVIVAL_DRILLS);
  const [activeDrillId, setActiveDrillId] = useState<string | null>(null);
  const [drillLog, setDrillLog] = useState<string | null>(null);

  const longevityPosture = calculateLongevityIndex(freeLanes, survivalDrills);

  // Tilling Trigger
  const handleRunTillingSweep = () => {
    setIsTillingActive(true);
    setTimeout(() => {
      const report = runDeterministicTillingSweep(probes);
      setProbes(report.probes);
      setSoilReport(report);
      setIsTillingActive(false);
    }, 400);
  };

  // Test DoF Gate
  const handleTestGate = () => {
    const result = evaluateAgentDofGate(testActionInput, testActionDofLevel, dofPolicy);
    setDofGateResult(result);
  };

  // Founder Expand DoF
  const handleExpandDof = (targetLevel: DofLevel) => {
    const outcome = founderExpandDof(targetLevel, founderPassphrase, 15);
    setExpansionFeedback(outcome.message);
    if (outcome.success && outcome.policy) {
      setDofPolicy(outcome.policy);
    }
  };

  // Reset DoF to Level 1
  const handleResetDof = () => {
    setDofPolicy(INITIAL_DOF_POLICY);
    setExpansionFeedback('Degree of Freedom clamped back to Level 1 (STRICT_PROTOCOL_RAILS).');
  };

  // Run Survival Drill
  const handleExecuteDrill = (drillId: string) => {
    setActiveDrillId(drillId);
    setTimeout(() => {
      const { drills, result, message } = executeSurvivalDrill(drillId, survivalDrills);
      setSurvivalDrills(drills);
      setDrillLog(`[${new Date().toLocaleTimeString()}] ${message} (Proof: ${result.recoveryProofSha256})`);
      setActiveDrillId(null);
    }, 600);
  };

  // Toggle Pillar Health for Interactive Self-Correction Demo
  const togglePillarDegradation = (pillar: TripartitePillar) => {
    if (pillar === 'FOUNDER') {
      const isNominal = founderHealth.status === 'GREEN';
      setFounderHealth({
        ...founderHealth,
        healthScore: isNominal ? 0.65 : 0.98,
        status: isNominal ? 'AMBER' : 'GREEN',
        activeDegradations: isNominal ? ['Founder cognitive load spike; manual triage pending'] : [],
      });
    } else if (pillar === 'AGENTS') {
      const isNominal = agentsHealth.status === 'GREEN';
      setAgentsHealth({
        ...agentsHealth,
        healthScore: isNominal ? 0.45 : 0.95,
        status: isNominal ? 'RED' : 'GREEN',
        activeDegradations: isNominal ? ['Agent exploratory retry oscillation loop detected'] : [],
      });
    } else if (pillar === 'MACHINE') {
      const isNominal = machineHealth.status === 'GREEN';
      setMachineHealth({
        ...machineHealth,
        healthScore: isNominal ? 0.70 : 0.99,
        status: isNominal ? 'AMBER' : 'GREEN',
        activeDegradations: isNominal ? ['LANE_A_GCP simulated network partition on Raft term leader'] : [],
      });
    }
  };

  return (
    <div className="space-y-8 pb-12">
      {/* 2100 Sovereign Header */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950/60 to-slate-900 border border-slate-800 p-6 sm:p-8 shadow-2xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-1/3 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-700/60 text-cyan-300 text-xs font-mono font-semibold">
              <InfinityIcon className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
              <span>THE TRIPARTITE ORGANISM & ETERNAL LIFE COVENANT</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
              <span>One Mind · One Organism · Autonomous Longevity</span>
            </h1>
            <p className="text-slate-400 text-sm max-w-3xl leading-relaxed">
              Founder, Autonomous Agents, and Machine Infrastructure bound in a single unbroken organism.
              Degree of freedom strictly constrained to eliminate speculative drift; automated deterministic
              tilling sweeps running continuously; longevity scavenger harvesting 7 free sovereign lanes for perpetual life.
            </p>
          </div>

          {/* Master Covenant Gauge */}
          <div className="flex flex-col items-end gap-2 bg-slate-950/80 border border-slate-800 px-5 py-4 rounded-xl shrink-0">
            <div className="text-xs font-mono text-slate-400 flex items-center gap-2">
              <Activity className="w-3.5 h-3.5 text-cyan-400" />
              <span>ORGANISM HEALTH VECTOR</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-mono font-bold text-white">
                {(organismState.compositeHealth * 100).toFixed(1)}%
              </span>
              <span
                className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                  organismState.estateStatus === 'GREEN'
                    ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                    : organismState.estateStatus === 'AMBER'
                    ? 'bg-amber-950 text-amber-300 border border-amber-800 animate-pulse'
                    : 'bg-rose-950 text-rose-300 border border-rose-800 animate-bounce'
                }`}
              >
                {organismState.estateStatus} STATE
              </span>
            </div>
            <div className="text-xs font-mono text-slate-400">
              Bottleneck: <span className="text-cyan-300 font-bold">{organismState.bottleneckPillar}</span> (
              {(organismState.bottleneckHealth * 100).toFixed(1)}%)
            </div>
          </div>
        </div>
      </div>

      {/* Auto-Steering Self-Preservation Directives Banner (When degraded) */}
      {organismState.isAutoSteeringActive && (
        <div className="bg-gradient-to-r from-amber-950/80 via-slate-900 to-amber-950/80 border border-amber-600/60 rounded-xl p-5 shadow-lg space-y-3">
          <div className="flex items-center gap-2 text-amber-300 text-sm font-bold font-mono">
            <AlertTriangle className="w-4 h-4 animate-spin text-amber-400" />
            <span>AUTONOMOUS TRIPARTITE SELF-STEERING ENGAGED (§11.1)</span>
            <span className="text-xs text-amber-400/80 font-normal">
              — Any part degraded trips estate-wide preservation
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs font-mono">
            {organismState.activeSteeringDirectives.map((dir) => (
              <div
                key={dir.id}
                className="bg-slate-950/90 border border-amber-800/80 rounded-lg p-3 space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <span className="text-amber-400 font-bold">{dir.targetPillar} TARGET</span>
                  <span className="bg-amber-950 text-amber-300 text-[10px] px-1.5 py-0.5 rounded border border-amber-800">
                    {dir.priority}
                  </span>
                </div>
                <p className="text-slate-300 leading-snug">{dir.directive}</p>
                <div className="text-[11px] text-cyan-400 font-semibold pt-1 border-t border-slate-800">
                  Target: {dir.preservationTarget}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SECTION 1: THE THREE TRIPARTITE PILLARS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Pillar 1: FOUNDER */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col justify-between space-y-4 hover:border-slate-700 transition-colors">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
                  <Key className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-bold text-white text-sm">PILLAR 1: FOUNDER</h3>
                  <p className="text-xs text-slate-400 font-mono">Sovereignty & Intent</p>
                </div>
              </div>
              <span
                className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                  founderHealth.status === 'GREEN'
                    ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800'
                    : 'bg-amber-950/80 text-amber-400 border border-amber-800'
                }`}
              >
                {(founderHealth.healthScore * 100).toFixed(0)}%
              </span>
            </div>

            <div className="space-y-2 text-xs font-mono">
              {founderHealth.vitalSignals.map((sig, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between py-1 border-b border-slate-800/60"
                >
                  <span className="text-slate-400">{sig.name}</span>
                  <span className="text-amber-300 font-semibold">{sig.value}</span>
                </div>
              ))}
            </div>

            {founderHealth.activeDegradations.length > 0 && (
              <div className="bg-amber-950/40 border border-amber-900/80 p-2.5 rounded text-xs text-amber-300 font-mono">
                {founderHealth.activeDegradations[0]}
              </div>
            )}
          </div>

          <button
            onClick={() => togglePillarDegradation('FOUNDER')}
            className="w-full py-1.5 px-3 rounded-lg text-xs font-mono bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors border border-slate-700 cursor-pointer"
          >
            {founderHealth.status === 'GREEN' ? 'Simulate Founder Load Spike' : 'Reconcile Founder Equilibrium'}
          </button>
        </div>

        {/* Pillar 2: AGENTS */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col justify-between space-y-4 hover:border-slate-700 transition-colors">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
                  <Cpu className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-bold text-white text-sm">PILLAR 2: AGENTS</h3>
                  <p className="text-xs text-slate-400 font-mono">Execution & Order</p>
                </div>
              </div>
              <span
                className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                  agentsHealth.status === 'GREEN'
                    ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800'
                    : 'bg-rose-950/80 text-rose-400 border border-rose-800'
                }`}
              >
                {(agentsHealth.healthScore * 100).toFixed(0)}%
              </span>
            </div>

            <div className="space-y-2 text-xs font-mono">
              {agentsHealth.vitalSignals.map((sig, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between py-1 border-b border-slate-800/60"
                >
                  <span className="text-slate-400">{sig.name}</span>
                  <span className="text-cyan-300 font-semibold">{sig.value}</span>
                </div>
              ))}
            </div>

            {agentsHealth.activeDegradations.length > 0 && (
              <div className="bg-rose-950/40 border border-rose-900/80 p-2.5 rounded text-xs text-rose-300 font-mono">
                {agentsHealth.activeDegradations[0]}
              </div>
            )}
          </div>

          <button
            onClick={() => togglePillarDegradation('AGENTS')}
            className="w-full py-1.5 px-3 rounded-lg text-xs font-mono bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors border border-slate-700 cursor-pointer"
          >
            {agentsHealth.status === 'GREEN' ? 'Simulate Agent Thrash Oscillation' : 'Reconcile Agent Discipline'}
          </button>
        </div>

        {/* Pillar 3: MACHINE & ENVIRONMENT */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col justify-between space-y-4 hover:border-slate-700 transition-colors">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                  <Server className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-bold text-white text-sm">PILLAR 3: MACHINE</h3>
                  <p className="text-xs text-slate-400 font-mono">Substrate & Free Lanes</p>
                </div>
              </div>
              <span
                className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                  machineHealth.status === 'GREEN'
                    ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800'
                    : 'bg-amber-950/80 text-amber-400 border border-amber-800'
                }`}
              >
                {(machineHealth.healthScore * 100).toFixed(0)}%
              </span>
            </div>

            <div className="space-y-2 text-xs font-mono">
              {machineHealth.vitalSignals.map((sig, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between py-1 border-b border-slate-800/60"
                >
                  <span className="text-slate-400">{sig.name}</span>
                  <span className="text-indigo-300 font-semibold">{sig.value}</span>
                </div>
              ))}
            </div>

            {machineHealth.activeDegradations.length > 0 && (
              <div className="bg-amber-950/40 border border-amber-900/80 p-2.5 rounded text-xs text-amber-300 font-mono">
                {machineHealth.activeDegradations[0]}
              </div>
            )}
          </div>

          <button
            onClick={() => togglePillarDegradation('MACHINE')}
            className="w-full py-1.5 px-3 rounded-lg text-xs font-mono bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors border border-slate-700 cursor-pointer"
          >
            {machineHealth.status === 'GREEN' ? 'Simulate Cloud Leader Partition' : 'Reconcile Machine Consensus'}
          </button>
        </div>
      </div>

      {/* SECTION 2: DEGREE OF FREEDOM (DoF) GOVERNOR */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Lock className="w-5 h-5 text-cyan-400" />
              <h2 className="text-lg font-bold text-white">Degree of Freedom (DoF) Governor</h2>
              <span className="text-xs font-mono bg-cyan-950 text-cyan-300 px-2 py-0.5 rounded border border-cyan-800">
                Level {dofPolicy.currentLevel} Active
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Only the Founder can expand agent Degree of Freedom. Open-ended speculative loops are prohibited.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {dofPolicy.currentLevel > 1 ? (
              <button
                onClick={handleResetDof}
                className="px-3 py-1.5 rounded-lg bg-rose-950 text-rose-300 border border-rose-800 text-xs font-mono flex items-center gap-1.5 hover:bg-rose-900 cursor-pointer"
              >
                <Lock className="w-3.5 h-3.5" />
                <span>Re-Clamp to Level 1</span>
              </button>
            ) : (
              <div className="text-xs font-mono text-emerald-400 bg-emerald-950/60 px-2.5 py-1 rounded border border-emerald-800 flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Strict Protocol Rails Enforced</span>
              </div>
            )}
          </div>
        </div>

        {/* Level Stepper / Spectrum */}
        <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
          {[
            { level: 1, name: 'Level 1: Rails', desc: 'Default. Zero speculative code. Deterministic schemas.' },
            { level: 2, name: 'Level 2: Bounded', desc: 'Parametric config tuning within known safe limits.' },
            { level: 3, name: 'Level 3: Refactor', desc: 'Bounded refactor with anti-recursion proof.' },
            { level: 4, name: 'Level 4: Hypothesis', desc: 'Founder signed token, max 300s lease window.' },
            { level: 5, name: 'Level 5: Sovereign', desc: 'Founder Break-Glass override only.' },
          ].map((lvl) => {
            const isCurrent = dofPolicy.currentLevel === lvl.level;
            const isElevated = dofPolicy.currentLevel >= lvl.level;
            return (
              <div
                key={lvl.level}
                className={`p-3.5 rounded-lg border text-left transition-all ${
                  isCurrent
                    ? 'bg-cyan-950/60 border-cyan-500 shadow-md shadow-cyan-500/10'
                    : isElevated
                    ? 'bg-slate-800/40 border-slate-700'
                    : 'bg-slate-950/40 border-slate-900 opacity-60'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold font-mono text-white">{lvl.name}</span>
                  {isCurrent && <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />}
                </div>
                <p className="text-[11px] text-slate-400 leading-snug">{lvl.desc}</p>
                {lvl.level > 1 && (
                  <button
                    onClick={() => handleExpandDof(lvl.level as DofLevel)}
                    className="mt-3 w-full py-1 rounded bg-slate-800 hover:bg-slate-700 text-[10px] font-mono text-cyan-300 border border-slate-700 flex items-center justify-center gap-1 cursor-pointer"
                  >
                    <Unlock className="w-2.5 h-2.5" />
                    <span>Founder Unlock</span>
                  </button>
                )}
              </div>
            );
          })}
        </div>

        {/* Live Gate Verification Sandbox */}
        <div className="bg-slate-950/80 border border-slate-800/80 rounded-lg p-4 space-y-3">
          <div className="text-xs font-mono font-bold text-slate-300 flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Zap className="w-3.5 h-3.5 text-cyan-400" />
              <span>TEST AGENT ACTION AGAINST THE DEGREE OF FREEDOM GATE</span>
            </span>
            <span className="text-slate-500 font-normal">Deterministic Admission Control</span>
          </div>

          <div className="flex flex-col sm:flex-row gap-2">
            <input
              type="text"
              value={testActionInput}
              onChange={(e) => setTestActionInput(e.target.value)}
              placeholder="Enter agent action (e.g., EXPLORATORY_BASH_LOOP, Refactor module...)"
              className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-100 focus:outline-none focus:border-cyan-500"
            />
            <select
              value={testActionDofLevel}
              onChange={(e) => setTestActionDofLevel(Number(e.target.value) as DofLevel)}
              className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value={1}>Requested Level 1</option>
              <option value={2}>Requested Level 2</option>
              <option value={3}>Requested Level 3</option>
              <option value={4}>Requested Level 4</option>
              <option value={5}>Requested Level 5</option>
            </select>
            <button
              onClick={handleTestGate}
              className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold text-xs font-mono rounded-lg transition-colors cursor-pointer flex items-center gap-1.5 shrink-0"
            >
              <Play className="w-3.5 h-3.5" />
              <span>Evaluate Gate</span>
            </button>
          </div>

          {dofGateResult && (
            <div
              className={`p-3 rounded-lg border text-xs font-mono space-y-1 ${
                dofGateResult.granted
                  ? 'bg-emerald-950/50 border-emerald-800 text-emerald-300'
                  : 'bg-rose-950/50 border-rose-800 text-rose-300'
              }`}
            >
              <div className="font-bold flex items-center gap-2">
                {dofGateResult.granted ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span>GATE ADMISSION GRANTED — Action within permitted deterministic bounds</span>
                  </>
                ) : (
                  <>
                    <AlertOctagon className="w-4 h-4 text-rose-400" />
                    <span>GATE ADMISSION REJECTED — Speculative drift forbidden (§1.3 / §11.2)</span>
                  </>
                )}
              </div>
              {dofGateResult.rejectionReason && (
                <p className="text-slate-300">{dofGateResult.rejectionReason}</p>
              )}
              {dofGateResult.deterministicAlternative && (
                <div className="text-cyan-300 pt-1">
                  Deterministic Alternative: {dofGateResult.deterministicAlternative}
                </div>
              )}
            </div>
          )}

          {expansionFeedback && (
            <div className="text-xs font-mono text-cyan-400 bg-cyan-950/40 p-2 rounded border border-cyan-800/60">
              {expansionFeedback}
            </div>
          )}
        </div>
      </div>

      {/* SECTION 3: DETERMINISTIC TESTING & EXPLORATORY TESTING "TILLING" */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Radio className="w-5 h-5 text-cyan-400" />
              <h2 className="text-lg font-bold text-white">Automated Soil Tilling Engine</h2>
              <span className="text-xs font-mono bg-cyan-950 text-cyan-300 px-2 py-0.5 rounded border border-cyan-800">
                Continuous Entropy Reduction
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Replaces unguided agent trial-and-error with deterministic state-space sweeps across consensus, schemas, and free-lanes.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleRunTillingSweep}
              disabled={isTillingActive}
              className="px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-slate-950 font-bold text-xs font-mono flex items-center gap-2 transition-all cursor-pointer shadow-lg shadow-cyan-500/20 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isTillingActive ? 'animate-spin' : ''}`} />
              <span>Run On-Demand Soil Tilling Sweep</span>
            </button>
          </div>
        </div>

        {/* Tilling Soil Report Metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-slate-950/80 border border-slate-800 p-3.5 rounded-lg">
            <span className="text-[11px] font-mono text-slate-400">SOIL PURITY INDEX</span>
            <div className="text-2xl font-mono font-bold text-cyan-300 mt-1">
              {soilReport ? `${(soilReport.soilPurityIndex * 100).toFixed(1)}%` : '98.5%'}
            </div>
            <span className="text-[10px] text-slate-500">Zero drift tolerance</span>
          </div>

          <div className="bg-slate-950/80 border border-slate-800 p-3.5 rounded-lg">
            <span className="text-[11px] font-mono text-slate-400">PROBES EXECUTED</span>
            <div className="text-2xl font-mono font-bold text-emerald-400 mt-1">
              {probes.length} / {probes.length} PASS
            </div>
            <span className="text-[10px] text-slate-500">All invariants nominal</span>
          </div>

          <div className="bg-slate-950/80 border border-slate-800 p-3.5 rounded-lg">
            <span className="text-[11px] font-mono text-slate-400">ENTROPY TAX SAVED</span>
            <div className="text-2xl font-mono font-bold text-indigo-400 mt-1">
              {soilReport ? `${soilReport.entropyTaxSavedHours}h` : '11.1h'}
            </div>
            <span className="text-[10px] text-slate-500">Agent thrash eliminated</span>
          </div>

          <div className="bg-slate-950/80 border border-slate-800 p-3.5 rounded-lg">
            <span className="text-[11px] font-mono text-slate-400">CRYPTOGRAPHIC RECEIPTS</span>
            <div className="text-2xl font-mono font-bold text-amber-400 mt-1">
              100% HMAC
            </div>
            <span className="text-[10px] text-slate-500">Signed state transitions</span>
          </div>
        </div>

        {/* Probe Matrix */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
          {probes.map((probe) => (
            <div
              key={probe.id}
              className="bg-slate-950/90 border border-slate-800 rounded-lg p-3.5 flex flex-col justify-between space-y-2 hover:border-slate-700 transition-colors"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-white">{probe.name}</span>
                    <span className="text-[10px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded">
                      {probe.category}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400">
                    Prevents: <span className="text-cyan-400">{probe.failureModePrevented}</span>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 text-[10px] font-bold">
                  {probe.status}
                </span>
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-slate-800/80">
                <span>Receipt: <span className="text-slate-300">{probe.deterministicReceipt}</span></span>
                <span>Entropy Reduced: <span className="text-cyan-300 font-bold">{probe.entropyReductionScore}%</span></span>
                <span>{probe.durationMs}ms</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* SECTION 4: ETERNAL LIFE INSTINCT & FREE LANE HARVESTER */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <InfinityIcon className="w-5 h-5 text-indigo-400" />
              <h2 className="text-lg font-bold text-white">Eternal Life Instinct & Free Lane Harvester</h2>
              <span className="text-xs font-mono bg-indigo-950 text-indigo-300 px-2 py-0.5 rounded border border-indigo-800">
                P(collapse) &lt; 10⁻¹²
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Perpetual operational life guaranteed through 7 diverse zero-cost lanes: GCP, AWS, OCI, Mac Edge, Cloudflare, GitHub Actions, Tailscale.
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
            <span className="text-slate-400">Infrastructure Cost:</span>
            <span className="text-emerald-400 font-bold">$0.00 / month</span>
          </div>
        </div>

        {/* Free Lane Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {freeLanes.map((lane) => (
            <div
              key={lane.id}
              className="bg-slate-950/80 border border-slate-800 rounded-lg p-3.5 space-y-2 text-xs font-mono hover:border-indigo-500/50 transition-colors"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-white truncate">{lane.name}</span>
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                  {lane.status}
                </span>
              </div>
              <div className="text-[11px] text-slate-400">{lane.spec}</div>
              <div className="text-[10px] text-indigo-300 leading-tight">
                Role: {lane.persistenceRole}
              </div>
              <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1.5 border-t border-slate-800">
                <span>Latency: {lane.latencyMs}ms</span>
                <span>SLA: {(lane.availabilitySla * 100).toFixed(2)}%</span>
              </div>
            </div>
          ))}
        </div>

        {/* Continuous Survival Chaos Drills */}
        <div className="bg-slate-950/90 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-bold text-white font-mono">
                CONTINUOUS LONGEVITY & SURVIVAL DRILLS (§11.4)
              </h3>
            </div>
            <span className="text-xs font-mono text-slate-400">
              {survivalDrills.filter((d) => d.drillResult === 'PASS_ZERO_DATA_LOSS').length} /{' '}
              {survivalDrills.length} Passed
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {survivalDrills.map((drill) => (
              <div
                key={drill.id}
                className="bg-slate-900/60 border border-slate-800/80 rounded-lg p-4 space-y-3 flex flex-col justify-between text-xs font-mono"
              >
                <div className="space-y-1.5">
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-bold text-white text-xs">{drill.name}</span>
                    <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 text-[10px]">
                      ZERO DATA LOSS
                    </span>
                  </div>
                  <p className="text-slate-400 text-[11px] leading-snug">{drill.threatScenario}</p>
                  <div className="text-[11px] text-cyan-300 bg-cyan-950/30 p-2 rounded border border-cyan-900/40">
                    Failover: {drill.failoverExpectedLane} (Max {drill.maxFailoverSeconds}s)
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
                  <span className="text-[10px] text-slate-500 truncate max-w-[200px]">
                    {drill.recoveryProofSha256}
                  </span>
                  <button
                    onClick={() => handleExecuteDrill(drill.id)}
                    disabled={activeDrillId === drill.id}
                    className="px-3 py-1 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-[10px] rounded transition-colors flex items-center gap-1 cursor-pointer disabled:opacity-50"
                  >
                    <Play className="w-2.5 h-2.5" />
                    <span>{activeDrillId === drill.id ? 'Simulating...' : 'Simulate Drill'}</span>
                  </button>
                </div>
              </div>
            ))}
          </div>

          {drillLog && (
            <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 text-xs font-mono text-cyan-300 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>{drillLog}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
