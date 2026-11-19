import React, { useState, useEffect } from 'react';
import { Sun, Moon } from 'lucide-react';
import {
  INITIAL_SPECIALIST_FLEET,
  INITIAL_INSTRUCTIONS,
  INITIAL_MEMORY_ENTRIES,
  INITIAL_EVAL_SCENARIOS,
  INITIAL_TRAINING_MODULES,
  INITIAL_BUILD_HISTORY_INCIDENTS,
  INITIAL_ENGINEER_TRANSITION_STEPS,
  INITIAL_FOUNDER_DAY_ZERO_CONFIG,
  INITIAL_OKE_CARNAGE_EPISODES,
  INITIAL_RESEARCH_DAG_NODES,
  INITIAL_PLATFORM_WORKLOADS,
  INITIAL_AGENTS_MD_POINTERS,
  INITIAL_PREDICTIVE_EARLY_WARNINGS,
  INITIAL_PROCESS_OPEN_LOOPS,
  INITIAL_SELF_DIAGNOSTIC_ITEMS,
  INITIAL_CHIEF_ENGINEER_EDGE_CASES,
  INITIAL_BOOTSTRAP_STEPS,
  INITIAL_TELEGRAM_OTT_MESSAGES,
  INITIAL_AUTONOMOUS_PM_QA_TASKS,
  SpecialistAgent,
  InstructionRecord,
  MemoryEntry,
  EvalScenario,
  TrainingModule,
  BuildHistoryIncident,
  EngineerTransitionStep,
  FounderDayZeroConfig,
  OkeCarnageTrainingEpisode,
  EphemeralUiCardSpec,
  PlatformWorkloadUnit,
  ResearchDagStageNode,
  AgentsMdPointerEntry,
  PredictiveEarlyWarning,
  ProcessOpenLoopGap,
  SelfDiagnosticLoopItem,
  ChiefEngineerEdgeCaseGuard,
  BootstrapStepSpec,
  TelegramOttMessage,
  AutonomousPmQaTask,
  ProtocolEvent,
  computeFleetMetrics,
  synthesizeInboxAndBuildHistory,
  resolveVoiceDirectiveToEphemeralSurface,
  transitionAgentState,
  calculateYield,
  computeLyapunovEstateManifold,
  evaluateDayZeroAutonomyAcceptance,
  processTelegramOttCommand,
} from './lib/protocolEngine';
import { OverviewPivotView } from './components/OverviewPivotView';
import { GenesisSpineSynthesisView } from './components/GenesisSpineSynthesisView';
import { DayZeroFounderControlView } from './components/DayZeroFounderControlView';
import { ResearchMlYieldGovernanceView } from './components/ResearchMlYieldGovernanceView';
import { GenesisBootstrapMathOttView } from './components/GenesisBootstrapMathOttView';
import { SpecialistFleetView } from './components/SpecialistFleetView';
import { ProtocolStateMemoryView } from './components/ProtocolStateMemoryView';
import { InstructionYieldLedgerView } from './components/InstructionYieldLedgerView';
import { EvalsTrainingPresentationView } from './components/EvalsTrainingPresentationView';
import { NewInstructionModal } from './components/NewInstructionModal';
import { FounderCockpit } from './components/FounderCockpit';
import { WwfdDailyDeck } from './components/WwfdDailyDeck';
import { EstateIntelligenceSurface } from './components/EstateIntelligenceSurface';
import { CompoundingEngineeringSurface } from './components/CompoundingEngineeringSurface';
import { AlienOrganismHeartbeatSurface } from './components/AlienOrganismHeartbeatSurface';

type ActiveTab =
  | 'organism'
  | 'bootstrap'
  | 'compounding'
  | 'cockpit'
  | 'wwfd'
  | 'intelligence_surface'
  | 'intelligence'
  | 'dayzero'
  | 'spine'
  | 'overview'
  | 'fleet'
  | 'protocols'
  | 'yield'
  | 'evals';

export default function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('organism');
  const [isDark, setIsDark] = useState<boolean>(false);
  const [isNewInstructionOpen, setIsNewInstructionOpen] = useState<boolean>(false);

  const [agents, setAgents] = useState<SpecialistAgent[]>(INITIAL_SPECIALIST_FLEET);
  const [instructions, setInstructions] =
    useState<InstructionRecord[]>(INITIAL_INSTRUCTIONS);
  const [memoryEntries, setMemoryEntries] =
    useState<MemoryEntry[]>(INITIAL_MEMORY_ENTRIES);
  const [evals, setEvals] = useState<EvalScenario[]>(INITIAL_EVAL_SCENARIOS);
  const [trainingModules, setTrainingModules] = useState<TrainingModule[]>(
    INITIAL_TRAINING_MODULES
  );
  const [incidents, setIncidents] = useState<BuildHistoryIncident[]>(
    INITIAL_BUILD_HISTORY_INCIDENTS
  );
  const [transitionSteps, setTransitionSteps] = useState<EngineerTransitionStep[]>(
    INITIAL_ENGINEER_TRANSITION_STEPS
  );
  const [founderConfig, setFounderConfig] = useState<FounderDayZeroConfig>(
    INITIAL_FOUNDER_DAY_ZERO_CONFIG
  );
  const [carnageEpisodes, setCarnageEpisodes] = useState<OkeCarnageTrainingEpisode[]>(
    INITIAL_OKE_CARNAGE_EPISODES
  );
  const [workloads, setWorkloads] = useState<PlatformWorkloadUnit[]>(
    INITIAL_PLATFORM_WORKLOADS
  );
  const [dagNodes, setDagNodes] = useState<ResearchDagStageNode[]>(
    INITIAL_RESEARCH_DAG_NODES
  );
  const [pointers] = useState<AgentsMdPointerEntry[]>(INITIAL_AGENTS_MD_POINTERS);
  const [earlyWarnings, setEarlyWarnings] = useState<PredictiveEarlyWarning[]>(
    INITIAL_PREDICTIVE_EARLY_WARNINGS
  );
  const [openLoops, setOpenLoops] = useState<ProcessOpenLoopGap[]>(
    INITIAL_PROCESS_OPEN_LOOPS
  );
  const [diagnostics, setDiagnostics] = useState<SelfDiagnosticLoopItem[]>(
    INITIAL_SELF_DIAGNOSTIC_ITEMS
  );
  const [edgeCases] = useState<ChiefEngineerEdgeCaseGuard[]>(
    INITIAL_CHIEF_ENGINEER_EDGE_CASES
  );
  const [bootstrapSteps] = useState<BootstrapStepSpec[]>(INITIAL_BOOTSTRAP_STEPS);
  const [ottMessages, setOttMessages] = useState<TelegramOttMessage[]>(
    INITIAL_TELEGRAM_OTT_MESSAGES
  );
  const [pmQaTasks, setPmQaTasks] = useState<AutonomousPmQaTask[]>(
    INITIAL_AUTONOMOUS_PM_QA_TASKS
  );
  const [dampingAlpha, setDampingAlpha] = useState<number>(0.42);

  const metrics = computeFleetMetrics(instructions, agents, evals);

  const [ephemeralCards, setEphemeralCards] = useState<EphemeralUiCardSpec[]>(() => [
    resolveVoiceDirectiveToEphemeralSurface(
      'Materialize Founder Estate Yield & Visual Media Brief',
      computeFleetMetrics(
        INITIAL_INSTRUCTIONS,
        INITIAL_SPECIALIST_FLEET,
        INITIAL_EVAL_SCENARIOS
      ),
      INITIAL_FOUNDER_DAY_ZERO_CONFIG
    ),
    resolveVoiceDirectiveToEphemeralSurface(
      'Show OKE carnage training and Rust mistake elimination',
      computeFleetMetrics(
        INITIAL_INSTRUCTIONS,
        INITIAL_SPECIALIST_FLEET,
        INITIAL_EVAL_SCENARIOS
      ),
      INITIAL_FOUNDER_DAY_ZERO_CONFIG
    ),
  ]);

  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [isDark]);

  const synthesisReport = synthesizeInboxAndBuildHistory(
    agents,
    instructions,
    incidents,
    transitionSteps
  );

  const handleIssueVoiceDirective = (transcript: string) => {
    const card = resolveVoiceDirectiveToEphemeralSurface(
      transcript,
      metrics,
      founderConfig
    );
    setEphemeralCards((prev) => [card, ...prev.slice(0, 3)]);
  };

  const handleDismissEphemeralCard = (cardId: string) => {
    setEphemeralCards((prev) => prev.filter((c) => c.id !== cardId));
  };

  const handleTrainPlatformAgentOnCarnage = (episodeId: string) => {
    setCarnageEpisodes((prev) =>
      prev.map((ep) => {
        if (ep.id !== episodeId) return ep;
        return {
          ...ep,
          replayEpochs: ep.replayEpochs + 250,
          mistakeEliminationRate: Math.min(
            100,
            Number((ep.mistakeEliminationRate + 0.4).toFixed(1))
          ),
        };
      })
    );
    setAgents((prev) =>
      prev.map((ag) => ({
        ...ag,
        evalScore: Math.min(100, Number((ag.evalScore + 0.6).toFixed(1))),
      }))
    );
  };

  const handleStepAgent = (agentId: string, event: ProtocolEvent) => {
    let outcome = {
      valid: false,
      reason: 'Agent not found',
    };

    setAgents((prev) =>
      prev.map((agent) => {
        if (agent.id !== agentId) return agent;
        const res = transitionAgentState(agent.machineState, event);
        outcome = { valid: res.valid, reason: res.reason };
        if (!res.valid) return agent;

        const updatedOutbox = res.outboxAction
          ? [
              {
                id: `OUT-${450 + agent.outbox.length}`,
                timestamp: '2026-11-01 08:20 UTC',
                eventType: res.outboxAction,
                recipient: 'Founder Yield Ledger',
                proofRef: `PRF-${agent.protocolId}-AUTO · sha256:8e41a09c`,
                yieldSnapshot: '102.5% Verified Headless Yield',
                delivered: true,
              },
              ...agent.outbox,
            ]
          : agent.outbox;

        return {
          ...agent,
          machineState: res.nextState,
          outbox: updatedOutbox,
          memoryKeys: agent.memoryKeys + 1,
        };
      })
    );

    return outcome;
  };

  const handleEnqueueInboxMessage = (
    agentId: string,
    sender: string,
    eventType: ProtocolEvent,
    payloadSummary: string
  ) => {
    setAgents((prev) =>
      prev.map((agent) => {
        if (agent.id !== agentId) return agent;
        const newMsg = {
          id: `INB-${930 + agent.inbox.length}`,
          timestamp: '2026-11-01 08:22 UTC',
          eventType,
          sender,
          payloadSummary,
          processed: false,
        };
        return {
          ...agent,
          inbox: [newMsg, ...agent.inbox],
        };
      })
    );
  };

  const handleProcessInboxItem = (agentId: string, messageId: string) => {
    setAgents((prev) =>
      prev.map((agent) => {
        if (agent.id !== agentId) return agent;
        const targetMsg = agent.inbox.find((m) => m.id === messageId);
        const stepped = targetMsg
          ? transitionAgentState(agent.machineState, targetMsg.eventType)
          : null;
        return {
          ...agent,
          machineState: stepped?.valid ? stepped.nextState : agent.machineState,
          inbox: agent.inbox.map((m) =>
            m.id === messageId ? { ...m, processed: true } : m
          ),
        };
      })
    );
  };

  const handleToggleTransitionStep = (stepId: string) => {
    setTransitionSteps((prev) =>
      prev.map((s) => (s.id === stepId ? { ...s, completed: !s.completed } : s))
    );
  };

  const handleExecuteSuperSynthesis = () => {
    setAgents((prev) =>
      prev.map((agent) => ({
        ...agent,
        machineState: 'YIELD_AUDITED',
        memoryKeys: agent.memoryKeys + 4,
        inbox: agent.inbox.map((m) => ({ ...m, processed: true })),
      }))
    );
    setTransitionSteps((prev) => prev.map((s) => ({ ...s, completed: true })));
    setIncidents((prev) =>
      prev.map((inc) => ({ ...inc, status: 'Neutralized by Guard' }))
    );
  };

  const handleAddBuildIncident = (
    failureTitle: string,
    legacySymptom: string,
    rootCause: string,
    protocolMachineFix: string,
    spineStageId: string
  ) => {
    setIncidents((prev) => [
      {
        id: `BLD-HIST-0${prev.length + 1}`,
        era: 'Genesis Cutover Audit',
        timestamp: '2026-11-01 · Cutover Synthesis',
        failureTitle,
        legacySymptom,
        rootCause,
        protocolMachineFix,
        spineStageId,
        status: 'Neutralized by Guard',
      },
      ...prev,
    ]);
  };

  const handleAddMemoryEntry = (
    key: string,
    scope: 'Estate-Global' | 'Protocol-State' | 'Claim-Ledger',
    valueSummary: string
  ) => {
    setMemoryEntries((prev) => [
      {
        id: `MEM-${105 + prev.length}`,
        key,
        scope,
        valueSummary,
        version: 1,
        updatedAt: '2026-11-01 08:24 UTC',
      },
      ...prev,
    ]);
  };

  const handleUpdateInstructionOutcomeAndClaim = (
    instructionId: string,
    claimStatement: string,
    proofArtifact: string,
    actualValue: number
  ) => {
    setInstructions((prev) =>
      prev.map((inst) => {
        if (inst.id !== instructionId) return inst;
        const calc = calculateYield(
          inst.expectedValue,
          actualValue,
          inst.lowerIsBetter
        );
        return {
          ...inst,
          claimStatement,
          proofArtifact,
          actualValue,
          yieldPercent: calc.yieldPercent,
          yieldGrade: calc.grade,
          stage: 'Outcome Measured',
        };
      })
    );
  };

  const handleFounderReviewAction = (
    instructionId: string,
    decision: 'Approved' | 'Revision Requested',
    notes: string
  ) => {
    setInstructions((prev) =>
      prev.map((inst) => {
        if (inst.id !== instructionId) return inst;
        return {
          ...inst,
          stage:
            decision === 'Approved' ? 'Founder Approved' : 'Revision Requested',
          founderReview: {
            status: decision,
            notes,
            reviewedAt: '2026-11-01 08:25 UTC',
          },
        };
      })
    );
  };

  const handleCreateInstruction = (payload: {
    title: string;
    estateAsset: string;
    specialistId: string;
    protocolId: string;
    instructionSpec: string;
    expectedMetricLabel: string;
    expectedValue: number;
    actualValue: number;
    unit: string;
    claimStatement: string;
    proofArtifact: string;
  }) => {
    const calc = calculateYield(payload.expectedValue, payload.actualValue, false);
    const newId = `INS-2026-80${instructions.length + 1}`;
    const newRecord: InstructionRecord = {
      id: newId,
      title: payload.title,
      estateAsset: payload.estateAsset,
      specialistId: payload.specialistId,
      protocolId: payload.protocolId,
      instructionSpec: payload.instructionSpec,
      claimStatement: payload.claimStatement,
      proofArtifact: payload.proofArtifact,
      expectedMetricLabel: payload.expectedMetricLabel,
      expectedValue: payload.expectedValue,
      actualValue: payload.actualValue,
      unit: payload.unit,
      lowerIsBetter: false,
      yieldPercent: calc.yieldPercent,
      yieldGrade: calc.grade,
      stage: 'Outcome Measured',
      founderReview: {
        status: 'Pending Review',
        notes: 'Newly dispatched instruction awaiting Founder Yield audit.',
        reviewedAt: 'Pending',
      },
    };
    setInstructions((prev) => [newRecord, ...prev]);
    handleEnqueueInboxMessage(
      payload.specialistId,
      'Founder Command Bus',
      'ENQUEUE_INBOX',
      `${newId}: ${payload.title} (${payload.estateAsset})`
    );
    setActiveTab('yield');
  };

  const handleRunEvalSuite = () => {
    setEvals((prev) =>
      prev.map((ev) => {
        const boosted = Math.min(100, Number((ev.scorePercent + 1.2).toFixed(1)));
        return {
          ...ev,
          scorePercent: boosted,
          simulatedOutcome: boosted,
          passed: boosted >= ev.passThresholdPercent,
          lastRunAt: '2026-11-01 08:26 UTC',
        };
      })
    );
  };

  const handleExecuteTrainingBatch = (moduleId: string) => {
    setTrainingModules((prev) =>
      prev.map((mod) =>
        mod.id === moduleId
          ? {
              ...mod,
              episodesCompleted: mod.episodesCompleted + 100,
              status: 'Completed',
            }
          : mod
      )
    );
    setEvals((prev) =>
      prev.map((ev) => {
        if (ev.id === 'EVL-04' || !ev.passed) {
          const calibrated = Math.min(100, Number((ev.scorePercent + 4.8).toFixed(1)));
          return {
            ...ev,
            scorePercent: calibrated,
            simulatedOutcome: calibrated,
            passed: calibrated >= ev.passThresholdPercent,
            lastRunAt: '2026-11-01 08:27 UTC',
          };
        }
        return ev;
      })
    );
  };

  const handleAddTrainingModule = (
    title: string,
    targetSquad: string,
    protocolFocus: string,
    yieldLiftPercent: number
  ) => {
    setTrainingModules((prev) => [
      {
        id: `TRN-30${prev.length + 1}`,
        title,
        targetSquad,
        protocolFocus,
        status: 'Active Curriculum',
        yieldLiftPercent,
        episodesCompleted: 100,
      },
      ...prev,
    ]);
  };

  const handleRemediateWorkloadProof = (workloadId: string) => {
    setWorkloads((prev) =>
      prev.map((w) => {
        if (w.id !== workloadId) return w;
        return {
          ...w,
          actualOutcome: Math.max(w.expectedOutcome, Number((w.expectedOutcome * 1.03).toFixed(1))),
          proofVerified: true,
          consecutiveDeficitEpochs: 0,
          proofOfYieldToken: `PRF-${w.protocolId}-SEALED · sha256:9f41e82c (Remediated Proof of Yield)`,
        };
      })
    );
  };

  const handleEvictWorkloadNow = (workloadId: string) => {
    setWorkloads((prev) =>
      prev.map((w) => {
        if (w.id !== workloadId) return w;
        return {
          ...w,
          proofVerified: false,
          consecutiveDeficitEpochs: 3,
          proofOfYieldToken: 'NONE (Evicted by Founder Override · 0% Compute Allocation)',
        };
      })
    );
  };

  const handleMitigateEarlyWarning = (warningId: string) => {
    setEarlyWarnings((prev) =>
      prev.map((w) => (w.id === warningId ? { ...w, mitigated: true } : w))
    );
  };

  const handleCloseOpenLoop = (loopId: string) => {
    setOpenLoops((prev) =>
      prev.map((l) => (l.id === loopId ? { ...l, status: 'CLOSED_VERIFIED' } : l))
    );
  };

  const handleCloseAllLoopsAndWarnings = () => {
    setOpenLoops((prev) =>
      prev.map((l) => ({ ...l, status: 'CLOSED_VERIFIED' }))
    );
    setEarlyWarnings((prev) => prev.map((w) => ({ ...w, mitigated: true })));
    setWorkloads((prev) =>
      prev.map((w) => {
        if (w.id === 'WKL-SPC-04') {
          return {
            ...w,
            actualOutcome: 12,
            consecutiveDeficitEpochs: 0,
            proofVerified: true,
            proofOfYieldToken: 'PRF-CURE-5092 · sha256:1d09e83b (All 12 Units + Postal Hash Verified)',
          };
        }
        return w;
      })
    );
  };

  const handleRunResearchDagPass = () => {
    setDagNodes((prev) =>
      prev.map((node) => ({
        ...node,
        verifiedYieldPercent: Number((node.verifiedYieldPercent + 0.6).toFixed(1)),
        latencyMs: Math.max(60, node.latencyMs - 8),
      }))
    );
    setWorkloads((prev) =>
      prev.map((w) => {
        if (w.proofVerified && w.consecutiveDeficitEpochs === 0) {
          return {
            ...w,
            actualOutcome: Number((w.actualOutcome * 1.02).toFixed(1)),
          };
        }
        return w;
      })
    );
  };

  // --- Day-0 Self-Observation, Self-Healing, Math Manifold, Telegram OTT & PM/QA Handlers ---
  const handleHealAndAdoptDiagnostic = (id: string) => {
    setDiagnostics((prev) =>
      prev.map((d) =>
        d.id === id
          ? {
              ...d,
              status: 'IMPROVEMENT_ADOPTED',
            }
          : d
      )
    );
  };

  const handleHealAllDiagnostics = () => {
    setDiagnostics((prev) =>
      prev.map((d) => ({
        ...d,
        status: 'IMPROVEMENT_ADOPTED',
      }))
    );
    // Remediate Eastside Annex statutory cure instruction into Safe Attractor Basin (y_i >= 1.00)
    setInstructions((prev) =>
      prev.map((ins) =>
        ins.id === 'INS-2026-804'
          ? {
              ...ins,
              actualOutcome: 100.0,
              founderReviewStatus: 'APPROVED',
            }
          : ins
      )
    );
    // Also close remaining open loops and mitigate warnings so Lyapunov potential V(S_t) drops further
    handleCloseAllLoopsAndWarnings();
  };

  const handleSendTelegramOttCommand = (commandText: string) => {
    const manifold = computeLyapunovEstateManifold(
      instructions,
      openLoops,
      diagnostics,
      dampingAlpha
    );
    const acceptance = evaluateDayZeroAutonomyAcceptance(diagnostics);
    const { inboundMsg, outboundReply, actionTriggered } =
      processTelegramOttCommand(commandText, manifold, acceptance);

    setOttMessages((prev) => [outboundReply, inboundMsg, ...prev]);

    if (actionTriggered === 'HEAL_AND_ADOPT_ALL') {
      handleHealAllDiagnostics();
    } else if (actionTriggered === 'STEER_PM_BACKLOG') {
      handleApplyFounderPmNudge(
        `OTT Steer: ${commandText}`,
        `Telegram OTT Signed Directive · ${commandText}`
      );
    }
  };

  const handleApplyFounderPmNudge = (
    nudgeTitle: string,
    intentText: string
  ) => {
    const newTask: AutonomousPmQaTask = {
      id: `PM-QA-0${pmQaTasks.length + 1}`,
      sprintEpoch: 'SPRINT-GENESIS-0',
      title: nudgeTitle,
      assignedSpecialistId: 'SPC-ESTATE-03',
      founderIntentBinding: intentText,
      propertyBasedQaSpec:
        'proptest! { |(x in 0.0f64..1e6)| assert!(cbf_safety_barrier(x) >= 0.0 && yield_ratio(x) >= 1.0) } (10,000 cases)',
      qaPassRatePercent: 100.0,
      expectedYieldImpactPercent: 6.4,
      status: 'PRODUCTION_YIELDING',
    };
    setPmQaTasks((prev) => [newTask, ...prev]);
  };

  const TOP_BAR_NAV: Array<{ id: ActiveTab; label: string }> = [
    { id: 'bootstrap', label: 'Genesis Spine' },
    { id: 'fleet', label: 'Specialist Fleet' },
    { id: 'protocols', label: 'Protocols & State' },
    { id: 'yield', label: 'Instructions & Yield' },
    { id: 'evals', label: 'Evals & Brief' },
  ];

  const isGenesisGroup =
    activeTab === 'organism' ||
    activeTab === 'bootstrap' ||
    activeTab === 'compounding' ||
    activeTab === 'cockpit' ||
    activeTab === 'wwfd' ||
    activeTab === 'intelligence_surface' ||
    activeTab === 'intelligence' ||
    activeTab === 'dayzero' ||
    activeTab === 'spine' ||
    activeTab === 'overview';

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      {/* Strict 3-Zone Top Bar Contract */}
      <header className="flex items-center justify-between gap-8 px-6 py-4 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
        {/* Zone 1: Single text element wordmark */}
        <a
          href="#organism"
          onClick={(e) => {
            e.preventDefault();
            setActiveTab('organism');
          }}
          className="text-lg font-bold tracking-tight text-slate-900 dark:text-slate-50 whitespace-nowrap shrink-0 font-display"
        >
          Olat Estate
        </a>

        {/* Zone 2: 5 concise single-line text navigation links */}
        <nav
          aria-label="Primary Navigation"
          className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-600 dark:text-slate-400"
        >
          {TOP_BAR_NAV.map((item) => {
            const isActive =
              activeTab === item.id ||
              (item.id === 'bootstrap' && isGenesisGroup);
            return (
              <a
                key={item.id}
                href={`#${item.id}`}
                onClick={(e) => {
                  e.preventDefault();
                  setActiveTab(item.id);
                }}
                className={`transition-colors whitespace-nowrap shrink-0 py-1 border-b-2 ${
                  isActive
                    ? 'text-slate-900 dark:text-white border-slate-900 dark:border-white font-semibold'
                    : 'border-transparent hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                {item.label}
              </a>
            );
          })}
        </nav>

        {/* Zone 3: 1 primary action */}
        <div className="flex items-center gap-3 shrink-0">
          <button
            type="button"
            onClick={() => setIsNewInstructionOpen(true)}
            className="px-4 py-2 text-xs font-semibold text-white bg-slate-900 dark:bg-slate-100 dark:text-slate-900 rounded-lg hover:bg-slate-800 dark:hover:bg-white transition-colors whitespace-nowrap shrink-0 cursor-pointer"
          >
            Issue Instruction
          </button>
        </div>
      </header>

      {/* Workspace Sub-Toolbar (Breadcrumbs, Genesis Sub-View Switcher & Theme Toggle) */}
      <div className="bg-slate-100/80 dark:bg-slate-900/60 border-b border-slate-200 dark:border-slate-800 px-6 py-2.5">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400 font-mono">
              <span>Rust Day-0 Protocol</span>
              <span aria-hidden="true">/</span>
              <span className="font-semibold text-slate-900 dark:text-slate-100">
                {activeTab === 'organism'
                  ? 'Living Organism Twin, Sonification (432Hz) & Founder Presence'
                  : activeTab === 'bootstrap'
                  ? 'Day-0 Self-Observation, Lyapunov Math Manifold, OTT & PM/QA'
                  : activeTab === 'compounding'
                  ? 'Compounding Engineering Doctrine & Asymmetry Engine (Core Law #7)'
                  : activeTab === 'cockpit'
                  ? 'Real-Time Audit Monitor, NATS Multi-Lane Mesh & Cockpit'
                  : activeTab === 'wwfd'
                  ? 'What Would Founder Do? Daily 5 Calibration Deck'
                  : activeTab === 'intelligence_surface'
                  ? 'Self-Describing Registry, Pass 0 Dossier & Zero-Debugging'
                  : activeTab === 'intelligence'
                  ? 'Research, ML, Yield Eviction & Memory Super-View'
                  : activeTab === 'dayzero'
                  ? 'Voice Ephemeral UI, Agency & OKE Carnage'
                  : activeTab === 'spine'
                  ? '7-Stage Genesis Spine & Synthesis'
                  : activeTab === 'overview'
                  ? 'Quad-Layer & Fleet Overview'
                  : TOP_BAR_NAV.find((n) => n.id === activeTab)?.label}
              </span>
            </div>

            {isGenesisGroup && (
              <div className="flex flex-wrap items-center gap-1 p-0.5 bg-slate-200/80 dark:bg-slate-800 rounded-md">
                <button
                  type="button"
                  onClick={() => setActiveTab('organism')}
                  className={`px-2.5 py-1 text-xs font-medium rounded transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                    activeTab === 'organism'
                      ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-xs font-bold text-emerald-600 dark:text-emerald-400'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  Alien 2100 Heartbeat
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('bootstrap')}
                  className={`px-2.5 py-1 text-xs font-medium rounded transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                    activeTab === 'bootstrap'
                      ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  Day-0 Self-Heal & Math
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('compounding')}
                  className={`px-2.5 py-1 text-xs font-medium rounded transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                    activeTab === 'compounding'
                      ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-xs font-bold text-amber-600 dark:text-amber-400'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  Compounding Doctrine
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('cockpit')}
                  className={`px-2.5 py-1 text-xs font-medium rounded transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                    activeTab === 'cockpit'
                      ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  Real-Time Audit Monitor
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('wwfd')}
                  className={`px-2.5 py-1 text-xs font-medium rounded transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                    activeTab === 'wwfd'
                      ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  WWFD Daily Deck
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('intelligence_surface')}
                  className={`px-2.5 py-1 text-xs font-medium rounded transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                    activeTab === 'intelligence_surface'
                      ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  Estate Registry & FMEA
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('intelligence')}
                  className={`px-2.5 py-1 text-xs font-medium rounded transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                    activeTab === 'intelligence'
                      ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  Research, ML & Yield Eviction
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('dayzero')}
                  className={`px-2.5 py-1 text-xs font-medium rounded transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                    activeTab === 'dayzero'
                      ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  Day-0 Voice, Agency & OKE Carnage
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('spine')}
                  className={`px-2.5 py-1 text-xs font-medium rounded transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                    activeTab === 'spine'
                      ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  7-Stage Spine & Synthesis
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('overview')}
                  className={`px-2.5 py-1 text-xs font-medium rounded transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                    activeTab === 'overview'
                      ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  Quad-Layer Overview
                </button>
              </div>
            )}
          </div>

          {/* Mobile Navigation Bar */}
          <div className="flex md:hidden items-center gap-1 overflow-x-auto py-1">
            {TOP_BAR_NAV.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setActiveTab(item.id)}
                className={`px-2.5 py-1 text-xs rounded font-medium whitespace-nowrap shrink-0 cursor-pointer ${
                  activeTab === item.id
                    ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900'
                    : 'text-slate-600 dark:text-slate-400'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-4">
            <span className="hidden sm:inline text-slate-500 dark:text-slate-400 font-mono tabular-nums">
              Spine Congruence: {synthesisReport.congruencePercent.toFixed(1)}% · Fleet Yield: {metrics.averageYieldPercent.toFixed(1)}%
            </span>
            <button
              type="button"
              onClick={() => setIsDark((prev) => !prev)}
              aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
              className="px-2.5 py-1 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 inline-flex items-center gap-1.5 whitespace-nowrap shrink-0 cursor-pointer"
            >
              {isDark ? (
                <>
                  <Sun className="w-3.5 h-3.5" />
                  <span>Light Surface</span>
                </>
              ) : (
                <>
                  <Moon className="w-3.5 h-3.5" />
                  <span>Dark Surface</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Viewport */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8">
        {activeTab === 'organism' && (
          <AlienOrganismHeartbeatSurface />
        )}

        {activeTab === 'bootstrap' && (
          <GenesisBootstrapMathOttView
            instructions={instructions}
            openLoops={openLoops}
            diagnostics={diagnostics}
            edgeCases={edgeCases}
            bootstrapSteps={bootstrapSteps}
            ottMessages={ottMessages}
            pmQaTasks={pmQaTasks}
            dampingAlpha={dampingAlpha}
            onChangeDampingAlpha={setDampingAlpha}
            onHealAndAdoptDiagnostic={handleHealAndAdoptDiagnostic}
            onHealAllDiagnostics={handleHealAllDiagnostics}
            onSendTelegramOttCommand={handleSendTelegramOttCommand}
            onApplyFounderPmNudge={handleApplyFounderPmNudge}
          />
        )}

        {activeTab === 'compounding' && (
          <CompoundingEngineeringSurface />
        )}

        {activeTab === 'cockpit' && (
          <FounderCockpit />
        )}

        {activeTab === 'wwfd' && (
          <WwfdDailyDeck />
        )}

        {activeTab === 'intelligence_surface' && (
          <EstateIntelligenceSurface />
        )}

        {activeTab === 'intelligence' && (
          <ResearchMlYieldGovernanceView
            workloads={workloads}
            dagNodes={dagNodes}
            pointers={pointers}
            earlyWarnings={earlyWarnings}
            openLoops={openLoops}
            onRemediateWorkloadProof={handleRemediateWorkloadProof}
            onEvictWorkloadNow={handleEvictWorkloadNow}
            onMitigateEarlyWarning={handleMitigateEarlyWarning}
            onCloseOpenLoop={handleCloseOpenLoop}
            onCloseAllLoopsAndWarnings={handleCloseAllLoopsAndWarnings}
            onRunResearchDagPass={handleRunResearchDagPass}
          />
        )}

        {activeTab === 'dayzero' && (
          <DayZeroFounderControlView
            config={founderConfig}
            onUpdateConfig={setFounderConfig}
            agents={agents}
            instructions={instructions}
            metrics={metrics}
            carnageEpisodes={carnageEpisodes}
            ephemeralCards={ephemeralCards}
            onIssueVoiceDirective={handleIssueVoiceDirective}
            onDismissEphemeralCard={handleDismissEphemeralCard}
            onTrainPlatformAgentOnCarnage={handleTrainPlatformAgentOnCarnage}
          />
        )}

        {activeTab === 'spine' && (
          <GenesisSpineSynthesisView
            synthesisReport={synthesisReport}
            incidents={incidents}
            transitionSteps={transitionSteps}
            agents={agents}
            onToggleTransitionStep={handleToggleTransitionStep}
            onExecuteSuperSynthesis={handleExecuteSuperSynthesis}
            onAddBuildIncident={handleAddBuildIncident}
            onNavigate={setActiveTab}
          />
        )}

        {activeTab === 'overview' && (
          <OverviewPivotView
            metrics={metrics}
            instructions={instructions}
            agents={agents}
            onNavigate={setActiveTab}
            onStepAgent={handleStepAgent}
            onOpenNewInstruction={() => setIsNewInstructionOpen(true)}
          />
        )}

        {activeTab === 'fleet' && (
          <SpecialistFleetView
            agents={agents}
            onStepAgent={handleStepAgent}
            onEnqueueInboxMessage={handleEnqueueInboxMessage}
            onProcessInboxItem={handleProcessInboxItem}
          />
        )}

        {activeTab === 'protocols' && (
          <ProtocolStateMemoryView
            memoryEntries={memoryEntries}
            onAddMemoryEntry={handleAddMemoryEntry}
          />
        )}

        {activeTab === 'yield' && (
          <InstructionYieldLedgerView
            instructions={instructions}
            agents={agents}
            onUpdateInstructionOutcomeAndClaim={
              handleUpdateInstructionOutcomeAndClaim
            }
            onFounderReviewAction={handleFounderReviewAction}
            onOpenNewInstruction={() => setIsNewInstructionOpen(true)}
          />
        )}

        {activeTab === 'evals' && (
          <EvalsTrainingPresentationView
            evals={evals}
            trainingModules={trainingModules}
            metrics={metrics}
            agents={agents}
            onRunEvalSuite={handleRunEvalSuite}
            onExecuteTrainingBatch={handleExecuteTrainingBatch}
            onAddTrainingModule={handleAddTrainingModule}
          />
        )}
      </main>

      {/* Quiet Footer */}
      <footer className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-6 py-4 text-xs text-slate-500 dark:text-slate-400">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>
            Olat Estate Protocol Engineering · Rust-First Zero-Bloat Headless Architecture
          </span>
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={() => setActiveTab('bootstrap')}
              className="hover:text-slate-900 dark:hover:text-white cursor-pointer"
            >
              Day-0 Self-Heal, Math & OTT
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('intelligence')}
              className="hover:text-slate-900 dark:hover:text-white cursor-pointer"
            >
              Research, ML & Eviction Super-View
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('dayzero')}
              className="hover:text-slate-900 dark:hover:text-white cursor-pointer"
            >
              Day-0 Voice & Agency
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('yield')}
              className="hover:text-slate-900 dark:hover:text-white cursor-pointer"
            >
              Founder Yield Ledger
            </button>
          </div>
        </div>
      </footer>

      <NewInstructionModal
        isOpen={isNewInstructionOpen}
        agents={agents}
        onClose={() => setIsNewInstructionOpen(false)}
        onCreateInstruction={handleCreateInstruction}
      />
    </div>
  );
}


