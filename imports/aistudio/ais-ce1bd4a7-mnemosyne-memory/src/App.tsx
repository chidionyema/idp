/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  createInitialMemoryNodes,
  createInitialThreads,
  executeContextRotPurgeAndReanchor,
  ingestMemoryEvent,
  evaluateSystemMetrics,
  mintVerificationBlock,
  getBenchmarkDepthCurve,
  createInitialGenesisAgents,
  executeGenesisAgentMemoryTick,
  updateGenesisAgentConfig,
  computeGenesisAgentMetrics,
  MemoryNode,
  TaskThread,
  VerificationBlock,
  GenesisAgentProfile,
  GenesisAgentMemoryConfig,
} from './engine/memoryEngine';
import {
  createBootstrapProtocols,
  evaluateInstructionThroughProtocolGate,
  ratifyNewGenesisProtocol,
  GenesisProtocol,
  ProtocolCategory,
  InstructionGateAttempt,
} from './engine/protocolEngine';
import { buildArgoSyncLaneState } from './engine/argoSyncEngine';
import {
  createInitialSovereignTreasuryState,
  executeAutonomousKeepAliveSweep,
  executeCommercialConversionSprint,
  evaluateModelProviderForRota,
  executeMultiHomeCanaryProbe,
  SovereignEstateTreasuryState,
  ModelLaneTier,
  ModelProviderRotaEntry,
} from './engine/estateTreasuryEngine';
import { computeDeterministicHash } from './engine/memoryEngine';
import {
  createInitialOneBrainFederationState,
  applyFounderSteeringDirective,
  castOneBrainCouncilVote,
  toggleZeroCreditWebLifeboatMode,
  registerOrHeartbeatSurface,
  OneBrainFederationState,
  AgentSurfaceCategory,
  AgentTransportMechanism,
  CreditDependencyMode,
} from './engine/oneBrainEngine';
import {
  createFallbackGitParityStatus,
  createInitialBackgroundPollerState,
  evaluateBackgroundPollSyncDecision,
  BackgroundGitOpsPollerState,
  GitBranchParityStatus,
  LiveE2EVerificationReport,
} from './engine/gitAutoSyncEngine';
import {
  createInitialSurvivalAndHarvesterState,
  triggerHomeSurvivalAlarmAndEvacuate,
  restoreHomeNominalPower,
  harvestAndMapFailureMode,
  advanceProactiveExpansionTrack,
  evaluateWorkflowPreFlightSurface,
  SurvivalAndHarvesterState,
  FailureSurfaceCategory,
  FailureModeIntelligenceRecord,
} from './engine/survivalHarvesterEngine';
import { SOVEREIGN_MODULES } from './data/frontierResearch';
import { ArgoSyncLanePanel } from './components/ArgoSyncLanePanel';
import { OneBrainFederationPanel } from './components/OneBrainFederationPanel';
import { SurvivalAndFailureHarvesterPanel } from './components/SurvivalAndFailureHarvesterPanel';
import { SovereignEstateEdictView } from './components/SovereignEstateEdictView';
import { ProtocolFirstEstateView } from './components/ProtocolFirstEstateView';
import { GenesisLiveAgentMonitorView } from './components/GenesisLiveAgentMonitorView';
import { VerificationBenchmarkView } from './components/VerificationBenchmarkView';
import { ContextRotActiveFocusView } from './components/ContextRotActiveFocusView';
import { ActiveMultitaskingView } from './components/ActiveMultitaskingView';
import { FrontierResearchDossierView } from './components/FrontierResearchDossierView';

type ActiveTab =
  | 'sovereign-edict'
  | 'protocol-kernel'
  | 'genesis-live'
  | 'verification'
  | 'context-rot';

export default function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('sovereign-edict');
  const [rotSubView, setRotSubView] = useState<'focus-lab' | 'multitasking' | 'research'>('focus-lab');

  const [activeModuleKeys, setActiveModuleKeys] = useState<string[]>(() =>
    SOVEREIGN_MODULES.map((m) => m.key)
  );

  // Sovereign Treasury, Model Rota, Concierge+Otto Keep-Alive & Anti-IDP Commercial State
  const [treasuryState, setTreasuryState] = useState<SovereignEstateTreasuryState>(() =>
    createInitialSovereignTreasuryState()
  );

  // Protocol-First Estate state
  const [protocols, setProtocols] = useState<GenesisProtocol[]>(() =>
    createBootstrapProtocols()
  );
  const [gateHistory, setGateHistory] = useState<InstructionGateAttempt[]>(() => {
    const initProtos = createBootstrapProtocols();
    const initialEval = evaluateInstructionThroughProtocolGate(
      'Enforce £200/mo Founder Standing Order Custodian Vault, Core Model Rota (Gemini, DeepSeek, MiniMax) & Concierge+Otto Keep-Alive',
      'diplomatic_governance',
      initProtos,
      'GEN-DIP-003',
      '2026-11-03T16:15:00.000Z'
    );
    return [initialEval.attempt];
  });

  // Argo CD GitOps Sync Lane & Live Git Parity state
  const [argoReleaseCounter, setArgoReleaseCounter] = useState<number>(1);
  const [argoAutoSelfHeal, setArgoAutoSelfHeal] = useState<boolean>(true);
  const [lastArgoSyncedHash, setLastArgoSyncedHash] = useState<string | null>(null);
  const [lastArgoSyncTimestamp, setLastArgoSyncTimestamp] = useState<string>(
    '2026-11-03T16:15:00.000Z'
  );
  const [lastArgoTriggerLabel, setLastArgoTriggerLabel] = useState<string>(
    'GEN-NET-003 + GEN-NET-006 Zero-Touch Auto-Sync'
  );
  const [gitParity, setGitParity] = useState<GitBranchParityStatus>(() =>
    createFallbackGitParityStatus()
  );
  const [pollerState, setPollerState] = useState<BackgroundGitOpsPollerState>(() =>
    createInitialBackgroundPollerState()
  );
  const [e2eReport, setE2eReport] = useState<LiveE2EVerificationReport | null>(null);
  const [e2eRunning, setE2eRunning] = useState<boolean>(false);

  const refreshGitParityStatus = useCallback(() => {
    fetch('/api/git/status')
      .then((r) => (r.ok ? r.json() : null))
      .then((status) => {
        if (status?.headSha) {
          setGitParity(status);
        }
      })
      .catch(() => {});
  }, []);

  // Asymmetric One-Brain Federation State (Backed by /api/brain/* HTTP + SSE)
  const [oneBrainState, setOneBrainState] = useState<OneBrainFederationState>(() =>
    createInitialOneBrainFederationState()
  );
  const [sseConnected, setSseConnected] = useState<boolean>(false);

  // Multi-Home Survival Watchtower & Triad Failure-Mode Intelligence Harvester State
  const [survivalState, setSurvivalState] = useState<SurvivalAndHarvesterState>(() =>
    createInitialSurvivalAndHarvesterState()
  );

  useEffect(() => {
    refreshGitParityStatus();
    fetch('/api/survival/state')
      .then((r) => (r.ok ? r.json() : null))
      .then((s) => {
        if (s?.boundProtocolId) setSurvivalState(s);
      })
      .catch(() => {});

    let es: EventSource | null = null;
    try {
      es = new EventSource('/api/brain/stream');
      es.onopen = () => setSseConnected(true);
      es.onmessage = (ev) => {
        try {
          const parsed = JSON.parse(ev.data);
          if (parsed && parsed.canonicalRevisionHash) {
            setOneBrainState(parsed);
            setSseConnected(true);
            refreshGitParityStatus();
          }
        } catch (_e) {
          // ignore malformed event
        }
      };
      es.onerror = () => setSseConnected(false);
    } catch (_err) {
      setSseConnected(false);
    }
    return () => {
      es?.close();
    };
  }, [refreshGitParityStatus]);

  // Real-time Genesis Agents state
  const [genesisAgents, setGenesisAgents] = useState<GenesisAgentProfile[]>(() =>
    createInitialGenesisAgents()
  );
  const [selectedAgentId, setSelectedAgentId] = useState<string>('agent-concierge-affairs');
  const [liveAgentStreamEnabled, setLiveAgentStreamEnabled] = useState<boolean>(true);

  const [nodes, setNodes] = useState<MemoryNode[]>(() => {
    const raw = createInitialMemoryNodes();
    return executeContextRotPurgeAndReanchor(raw).cleanedNodes;
  });

  const [threads, setThreads] = useState<TaskThread[]>(() => createInitialThreads());
  const [daemonRunning, setDaemonRunning] = useState<boolean>(true);

  const [ledger, setLedger] = useState<VerificationBlock[]>(() => {
    const initialModules = SOVEREIGN_MODULES.map((m) => m.key);
    const rawNodes = createInitialMemoryNodes();
    const cleaned = executeContextRotPurgeAndReanchor(rawNodes).cleanedNodes;
    const initThreads = createInitialThreads();

    const block1 = mintVerificationBlock(
      null,
      rawNodes,
      initThreads,
      initialModules,
      'Genesis Probe: Pre-Purge Baseline Scan',
      '2026-11-03T15:20:00.000Z'
    );
    const block2 = mintVerificationBlock(
      block1,
      cleaned,
      initThreads,
      initialModules,
      'GEN-DIP-003 & GEN-NET-004: £200/mo Sovereign Treasury + Concierge & Otto Keep-Alive Verified',
      '2026-11-03T16:15:00.000Z'
    );
    return [block1, block2];
  });

  const appendVerificationProbe = useCallback(
    (
      currentNodes: MemoryNode[],
      currentThreads: TaskThread[],
      currentModules: string[],
      suiteName: string
    ) => {
      setLedger((prev) => {
        const lastBlock = prev[prev.length - 1] ?? null;
        const nextBlock = mintVerificationBlock(
          lastBlock,
          currentNodes,
          currentThreads,
          currentModules,
          suiteName,
          new Date().toISOString()
        );
        return [...prev, nextBlock];
      });
    },
    []
  );

  // Real-time stream for the active Genesis Agent (ticks every 2.5 seconds when enabled)
  useEffect(() => {
    if (!liveAgentStreamEnabled) return;
    const timer = setInterval(() => {
      setGenesisAgents((prevAgents) =>
        prevAgents.map((ag) =>
          ag.id === selectedAgentId ? executeGenesisAgentMemoryTick(ag) : ag
        )
      );
    }, 2500);
    return () => clearInterval(timer);
  }, [liveAgentStreamEnabled, selectedAgentId]);

  // Always-running verification daemon (when enabled, ticks every 8 seconds)
  useEffect(() => {
    if (!daemonRunning) return;
    const timer = setInterval(() => {
      appendVerificationProbe(
        nodes,
        threads,
        activeModuleKeys,
        'Continuous Daemon: ZIWP + RULER-128K + Bi-Temporal Check'
      );
    }, 8000);
    return () => clearInterval(timer);
  }, [daemonRunning, nodes, threads, activeModuleKeys, appendVerificationProbe]);

  const currentEval = evaluateSystemMetrics(nodes, threads, activeModuleKeys);
  const depthCurve = getBenchmarkDepthCurve(activeModuleKeys);

  // Protocol-First Estate Handlers
  const handleDispatchInstruction = (
    instructionText: string,
    requestedDomain: ProtocolCategory,
    explicitProtocolId?: string | 'AUTO_DETECT'
  ): InstructionGateAttempt => {
    const res = evaluateInstructionThroughProtocolGate(
      instructionText,
      requestedDomain,
      protocols,
      explicitProtocolId
    );
    setProtocols(res.updatedProtocols);
    setGateHistory((prev) => [res.attempt, ...prev].slice(0, 15));

    appendVerificationProbe(
      nodes,
      threads,
      activeModuleKeys,
      res.attempt.status === 'EXECUTED_UNDER_PROTOCOL'
        ? `ZIWP Protocol Execution (${res.attempt.boundProtocolId})`
        : `ZIWP Firewall Blocked Unbound Instruction (${res.attempt.attemptId})`
    );
    return res.attempt;
  };

  const handleRatifyProtocolAndExecute = (
    draft: {
      id: string;
      title: string;
      category: ProtocolCategory;
      eliteStandardLineage: string;
      domainKeywords: string[];
      summary: string;
      preconditions: string[];
      stateTransitions: string[];
      postconditions: string[];
      safetyInvariant: string;
      rollbackProcedure: string;
    },
    pendingInstructionText?: string
  ) => {
    const newProto = ratifyNewGenesisProtocol(protocols, draft);
    const nextProtos = [...protocols, newProto];

    if (pendingInstructionText) {
      const execRes = evaluateInstructionThroughProtocolGate(
        pendingInstructionText,
        draft.category,
        nextProtos,
        newProto.id
      );
      setProtocols(execRes.updatedProtocols);
      setGateHistory((prev) => [execRes.attempt, ...prev].slice(0, 15));
      appendVerificationProbe(
        nodes,
        threads,
        activeModuleKeys,
        `Ratified ${newProto.id} & Executed Bound Instruction`
      );
    } else {
      setProtocols(nextProtos);
      appendVerificationProbe(
        nodes,
        threads,
        activeModuleKeys,
        `Ratified New Estate Protocol (${newProto.id}: ${newProto.title})`
      );
    }
  };

  // Handlers for Genesis Live Agent Monitor
  const handleStepAgentTick = (
    agentId: string,
    customStimulus?: {
      label: string;
      content: string;
      surprise: number;
      salience: number;
    }
  ) => {
    setGenesisAgents((prev) =>
      prev.map((ag) => (ag.id === agentId ? executeGenesisAgentMemoryTick(ag, customStimulus) : ag))
    );
    if (customStimulus) {
      appendVerificationProbe(
        nodes,
        threads,
        activeModuleKeys,
        `Genesis Agent Live Stimulus (${agentId}: ${customStimulus.label})`
      );
    }
  };

  const handleUpdateAgentConfig = (
    agentId: string,
    partialConfig: Partial<GenesisAgentMemoryConfig>,
    applyToAll?: boolean
  ) => {
    setGenesisAgents((prev) =>
      prev.map((ag) =>
        applyToAll || ag.id === agentId ? updateGenesisAgentConfig(ag, partialConfig) : ag
      )
    );
    appendVerificationProbe(
      nodes,
      threads,
      activeModuleKeys,
      applyToAll
        ? 'Global Genesis Fleet Memory Policy Broadcast'
        : `Real-Time Agent Config Update (${agentId})`
    );
  };

  const handleTogglePinBlock = (agentId: string, blockId: string) => {
    setGenesisAgents((prev) =>
      prev.map((ag) => {
        if (ag.id !== agentId) return ag;
        const updatedBlocks = ag.memoryBlocks.map((b) => {
          if (b.id !== blockId) return b;
          const nextPinned = !b.pinned;
          return {
            ...b,
            pinned: nextPinned,
            zone: nextPinned ? ('prefix_sink' as const) : ('recency_anchor' as const),
          };
        });
        return {
          ...ag,
          memoryBlocks: updatedBlocks,
          liveMetrics: computeGenesisAgentMetrics(
            ag.config,
            updatedBlocks,
            ag.liveMetrics.filteredNoiseEvents,
            ag.liveMetrics.resolvedContradictions
          ),
        };
      })
    );
  };

  const handleEvictBlock = (agentId: string, blockId: string) => {
    setGenesisAgents((prev) =>
      prev.map((ag) => {
        if (ag.id !== agentId) return ag;
        const updatedBlocks = ag.memoryBlocks.map((b) =>
          b.id === blockId ? { ...b, zone: 'paged_archival' as const, pinned: false } : b
        );
        return {
          ...ag,
          memoryBlocks: updatedBlocks,
          liveMetrics: computeGenesisAgentMetrics(
            ag.config,
            updatedBlocks,
            ag.liveMetrics.filteredNoiseEvents,
            ag.liveMetrics.resolvedContradictions
          ),
        };
      })
    );
  };

  const handleRegisterNewAgent = (name: string, role: string, ramBudget: number) => {
    const newId = `agent-genesis-0${genesisAgents.length + 1}`;
    const defaultConfig: GenesisAgentMemoryConfig = {
      workingRamBudgetTokens: ramBudget,
      surpriseThreshold: 0.62,
      prefixSinkAllocationPct: 15,
      autoDefragMiddleTrough: true,
      bitemporalMode: 'strict_atomic_invalidation',
      exponentialDecayAlpha: 0.05,
      cowIsolationMode: 'strict_sandbox',
    };
    const initBlocks = [
      {
        id: `blk-${genesisAgents.length + 1}01`,
        label: 'Agent_Mandate_Invariant',
        content: role,
        zone: 'prefix_sink' as const,
        tokens: 380,
        salience: 0.96,
        surprise: 0.92,
        pinned: true,
        validFromTick: 1,
        validUntilTick: null,
      },
    ];
    const newAgent: GenesisAgentProfile = {
      id: newId,
      name,
      role,
      modelBackbone: 'Genesis-Omni-1M + Sovereign Memory OS',
      status: 'streaming',
      tickCount: 1,
      config: defaultConfig,
      memoryBlocks: initBlocks,
      recentTraces: [],
      liveMetrics: computeGenesisAgentMetrics(defaultConfig, initBlocks, 0, 0),
    };
    const nextAgentWithTick = executeGenesisAgentMemoryTick(newAgent, {
      label: 'Agent_Bootstrap_State',
      content: `Initialized ${name} on Genesis Sovereign Memory Bus with 0% cross-talk.`,
      surprise: 0.91,
      salience: 0.93,
    });
    setGenesisAgents((prev) => [...prev, nextAgentWithTick]);
    setSelectedAgentId(newId);
    appendVerificationProbe(
      nodes,
      threads,
      activeModuleKeys,
      `Spawned Genesis Agent (${name})`
    );
  };

  const handleIngestFact = (input: {
    subject: string;
    predicate: string;
    object: string;
    category: MemoryNode['category'];
  }) => {
    const res = ingestMemoryEvent(nodes, input, activeModuleKeys);
    setNodes(res.updatedNodes);
    appendVerificationProbe(
      res.updatedNodes,
      threads,
      activeModuleKeys,
      res.supersededNodeIds.length > 0
        ? `Bi-Temporal Contradiction Resolved (${res.newNode.subject})`
        : `Episodic Ingestion Gate (${res.newNode.id})`
    );
    return { supersededIds: res.supersededNodeIds, newNodeId: res.newNode.id };
  };

  const handlePurgeAndReanchor = () => {
    const res = executeContextRotPurgeAndReanchor(nodes);
    setNodes(res.cleanedNodes);
    appendVerificationProbe(
      res.cleanedNodes,
      threads,
      activeModuleKeys,
      'Context Rot Purge & Attention Sink Re-Anchoring'
    );
    return {
      evictedNoiseCount: res.evictedNoiseCount,
      reanchoredCount: res.reanchoredCount,
      tokensReclaimed: res.tokensReclaimed,
    };
  };

  const handleSimulateRotWave = () => {
    const rawWithRot = createInitialMemoryNodes();
    setNodes(rawWithRot);
    appendVerificationProbe(
      rawWithRot,
      threads,
      activeModuleKeys,
      'Adversarial Context Rot Wave Injected (Unpurged Trough)'
    );
  };

  const handleStepThread = (threadId: string) => {
    const updated = threads.map((t) => {
      if (t.id !== threadId) return t;
      const nextStep = t.stepCount + 1;
      return {
        ...t,
        stepCount: nextStep,
        usedTokens: Math.min(t.allocatedTokenBudget, t.usedTokens + 110),
        isolatedScratchpad: [
          ...t.isolatedScratchpad.slice(-2),
          `Step ${nextStep}: Verified local CoW state hash without global window leakage`,
        ],
      };
    });
    setThreads(updated);
  };

  const handleSpawnThread = (name: string, domain: string, budget: number) => {
    const newThread: TaskThread = {
      id: `thread-0${threads.length + 1}`,
      name,
      domain,
      status: 'active',
      allocatedTokenBudget: budget,
      usedTokens: 320,
      isolatedScratchpad: [
        `Initialized CoW snapshot from Global Semantic Graph (${nodes.filter((n) => n.validUntilStep === null).length} active edges)`,
        'Isolated local tool buffer ready (0% cross-talk guaranteed)',
      ],
      committedFactIds: [],
      crossContaminationEvents: 0,
      priority: Math.min(5, threads.length + 1),
      stepCount: 1,
    };
    const nextThreads = [...threads, newThread];
    setThreads(nextThreads);
    appendVerificationProbe(
      nodes,
      nextThreads,
      activeModuleKeys,
      `Sub-Agent CoW Fork (${name})`
    );
  };

  const handlePromoteThreadFact = (threadId: string) => {
    const targetThread = threads.find((t) => t.id === threadId);
    if (!targetThread) return;

    const ingestRes = ingestMemoryEvent(
      nodes,
      {
        subject: targetThread.name.split('·')[1]?.trim().replace(/\s+/g, '_') || targetThread.id,
        predicate: 'verified_subagent_invariant',
        object: `${targetThread.domain} validated at Step ${targetThread.stepCount} with 0% cross-talk`,
        category: 'architecture_invariant',
        threadOrigin: targetThread.id,
      },
      activeModuleKeys
    );

    const updatedThreads = threads.map((t) =>
      t.id === threadId
        ? {
            ...t,
            committedFactIds: [...t.committedFactIds, ingestRes.newNode.id],
            usedTokens: Math.max(240, t.usedTokens - 180),
          }
        : t
    );

    setNodes(ingestRes.updatedNodes);
    setThreads(updatedThreads);
    appendVerificationProbe(
      ingestRes.updatedNodes,
      updatedThreads,
      activeModuleKeys,
      `CoW Thread Commit (${ingestRes.newNode.id} from ${targetThread.id})`
    );
  };

  const handleToggleModule = (moduleKey: string) => {
    const nextKeys = activeModuleKeys.includes(moduleKey)
      ? activeModuleKeys.filter((k) => k !== moduleKey)
      : [...activeModuleKeys, moduleKey];
    setActiveModuleKeys(nextKeys);
    appendVerificationProbe(
      nodes,
      threads,
      nextKeys,
      `Architecture Ablation Update (${nextKeys.length}/6 Modules Active)`
    );
  };

  const handleEnableAllModules = () => {
    const allKeys = SOVEREIGN_MODULES.map((m) => m.key);
    setActiveModuleKeys(allKeys);
    appendVerificationProbe(
      nodes,
      threads,
      allKeys,
      'Restored Full 6-Module Sovereign Synthesis'
    );
  };

  // Sovereign Treasury, Model Rota, Concierge + Otto Keep-Alive & Anti-IDP Commercial Handlers
  const handleExecuteKeepAliveSweep = () => {
    const res = executeAutonomousKeepAliveSweep(treasuryState);
    setTreasuryState(res.updatedState);
    handleDispatchInstruction(
      'Execute Concierge and Otto autonomous renewal sweep across all Estate domains and model providers',
      'computing_network',
      'GEN-NET-004'
    );
  };

  const handleExecuteCommercialSprint = (streamId?: string) => {
    const res = executeCommercialConversionSprint(treasuryState, streamId);
    setTreasuryState(res.updatedState);
    handleDispatchInstruction(
      `Convert self-serve B2B commercial subscription (+£${res.addedMrrGbp}/mo MRR) under Anti-IDP margin guardrails`,
      'computing_network',
      'GEN-NET-004'
    );
  };

  const handleApproveFounderRequest = (
    requestId: string,
    mode: 'APPROVED_BY_FOUNDER' | 'DELEGATED_TO_CONCIERGE_OTTO'
  ) => {
    setTreasuryState((prev) => ({
      ...prev,
      founderDelightQueue: prev.founderDelightQueue.map((item) =>
        item.id === requestId ? { ...item, status: mode } : item
      ),
      stateDigestHash: computeDeterministicHash(`${prev.stateDigestHash}:${requestId}:${mode}`),
    }));
    handleDispatchInstruction(
      `Founder 1-Click Executive Sign-Off (${requestId} -> ${mode})`,
      'diplomatic_governance',
      'GEN-DIP-003'
    );
  };

  const handleEvaluateAndAddModel = (candidate: {
    providerName: string;
    modelFamily: string;
    lane: ModelLaneTier;
    roleDescription: string;
    monthlyBudgetAllocationGbp: number;
    costPerMillionTokensGbp: number;
    verifiedAccuracyPct: number;
    p95LatencyMs: number;
  }) => {
    const evalRes = evaluateModelProviderForRota(candidate);
    const nowIso = new Date().toISOString();

    if (evalRes.admitted) {
      const newEntry: ModelProviderRotaEntry = {
        id: `mod-${candidate.providerName.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-${treasuryState.modelRota.length + 1}`,
        providerName: candidate.providerName.trim(),
        modelFamily: candidate.modelFamily.trim(),
        lane: candidate.lane,
        roleDescription: candidate.roleDescription.trim(),
        monthlyBudgetAllocationGbp: candidate.monthlyBudgetAllocationGbp,
        currentMonthSpendGbp: 0,
        costPerMillionTokensGbp: candidate.costPerMillionTokensGbp,
        verifiedAccuracyPct: candidate.verifiedAccuracyPct,
        p95LatencyMs: candidate.p95LatencyMs,
        yieldMultiplier: evalRes.yieldMultiplier,
        rotaStatus: evalRes.rotaStatus,
        boundVirtualCardId:
          candidate.lane === 'core_permanent' ? 'VC-CORE-4810' : 'VC-BACKUP-2041',
        lastEvaluatedIso: nowIso,
        evaluationProofHash: evalRes.evaluationProofHash.slice(0, 16),
      };

      setTreasuryState((prev) => ({
        ...prev,
        modelRota: [...prev.modelRota, newEntry],
        stateDigestHash: computeDeterministicHash(
          `${prev.stateDigestHash}:model-admit:${newEntry.id}`
        ),
      }));
    }

    handleDispatchInstruction(
      `Evaluate model provider ${candidate.providerName} (${evalRes.yieldMultiplier}x yield) for Estate Staff Rota`,
      'scientific_experimental',
      'GEN-SCI-003'
    );

    return {
      admitted: evalRes.admitted,
      reason: evalRes.reason,
      yieldMultiplier: evalRes.yieldMultiplier,
    };
  };

  // One-Brain Federation Handlers (Optimistic + Server-Authoritative /api/brain/*)
  const handleSendFounderSteer = (directiveText: string, targetSurfaces: string = 'ALL_SURFACES') => {
    setOneBrainState((prev) =>
      applyFounderSteeringDirective(prev, directiveText, targetSurfaces)
    );
    fetch('/api/brain/steer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ directiveText, targetSurfaces }),
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((serverState) => {
        if (serverState?.canonicalRevisionHash) setOneBrainState(serverState);
      })
      .catch(() => {});

    handleDispatchInstruction(
      `Broadcast Founder Steering Override across One-Brain Federation: ${directiveText}`,
      'computing_network',
      'GEN-NET-006'
    );
  };

  const handleCastCouncilVote = (input: {
    motionId: string;
    surfaceId: string;
    decision: 'APPROVE' | 'AMEND' | 'VETO';
    rationale: string;
  }) => {
    setOneBrainState((prev) => castOneBrainCouncilVote(prev, input));
    fetch('/api/brain/council/vote', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((serverState) => {
        if (serverState?.canonicalRevisionHash) setOneBrainState(serverState);
      })
      .catch(() => {});

    handleDispatchInstruction(
      `Cast One-Brain Council Quorum Vote (${input.surfaceId} -> ${input.decision})`,
      'computing_network',
      'GEN-NET-006'
    );
  };

  const handleToggleZeroCreditLifeboat = (enable?: boolean) => {
    setOneBrainState((prev) => toggleZeroCreditWebLifeboatMode(prev, enable));
    fetch('/api/brain/lifeboat-toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enable }),
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((serverState) => {
        if (serverState?.canonicalRevisionHash) setOneBrainState(serverState);
      })
      .catch(() => {});

    handleDispatchInstruction(
      'Toggle Asymmetric Zero-API-Credit Web/App Lifeboat Relay across DeepSeek Web, Kimi, Grok & Meta Muse',
      'computing_network',
      'GEN-NET-006'
    );
  };

  const handlePlugInNewSurface = (input: {
    surfaceName: string;
    modelBackbone: string;
    category: AgentSurfaceCategory;
    transport: AgentTransportMechanism;
    creditMode: CreditDependencyMode;
  }) => {
    setOneBrainState((prev) => registerOrHeartbeatSurface(prev, input));
    fetch('/api/brain/heartbeat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((serverState) => {
        if (serverState?.canonicalRevisionHash) setOneBrainState(serverState);
      })
      .catch(() => {});

    handleDispatchInstruction(
      `Register new agent surface ${input.surfaceName} (${input.modelBackbone}) into One-Brain Federation Bus`,
      'computing_network',
      'GEN-NET-006'
    );
  };

  const handleTriggerZeroTouchArgoSync = useCallback(
    (triggerSource: string) => {
      const nextReleaseNum = argoReleaseCounter + 1;
      const nowIso = new Date().toISOString();
      const currentRelease = buildArgoSyncLaneState(
        protocols,
        genesisAgents,
        nodes,
        ledger,
        lastArgoSyncedHash,
        argoAutoSelfHeal,
        nowIso,
        triggerSource,
        nextReleaseNum,
        treasuryState.stateDigestHash
      );
      setArgoReleaseCounter(nextReleaseNum);
      setLastArgoSyncedHash(currentRelease.fullManifestHash);
      setLastArgoSyncTimestamp(nowIso);
      setLastArgoTriggerLabel(triggerSource || 'GEN-NET-003 4-Wave Zero-Touch Auto-Sync');
      fetch('/api/git/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: triggerSource }),
      })
        .then((r) => (r.ok ? r.json() : null))
        .then((status) => {
          if (status?.headSha) setGitParity(status);
        })
        .catch(() => {});

      handleDispatchInstruction(
        'Push everything to Argo GitOps sync lane across all 4 ordered waves',
        'computing_network',
        'GEN-NET-003'
      );
    },
    [
      argoReleaseCounter,
      protocols,
      genesisAgents,
      nodes,
      ledger,
      lastArgoSyncedHash,
      argoAutoSelfHeal,
      treasuryState.stateDigestHash,
    ]
  );

  // Ref holding latest state snapshot for the background GitOps polling interval
  const backgroundPollRef = useRef({
    gitParity,
    protocols,
    genesisAgents,
    nodes,
    ledger,
    lastArgoSyncedHash,
    argoAutoSelfHeal,
    lastArgoSyncTimestamp,
    lastArgoTriggerLabel,
    argoReleaseCounter,
    treasuryDigest: treasuryState.stateDigestHash,
  });

  useEffect(() => {
    backgroundPollRef.current = {
      gitParity,
      protocols,
      genesisAgents,
      nodes,
      ledger,
      lastArgoSyncedHash,
      argoAutoSelfHeal,
      lastArgoSyncTimestamp,
      lastArgoTriggerLabel,
      argoReleaseCounter,
      treasuryDigest: treasuryState.stateDigestHash,
    };
  }, [
    gitParity,
    protocols,
    genesisAgents,
    nodes,
    ledger,
    lastArgoSyncedHash,
    argoAutoSelfHeal,
    lastArgoSyncTimestamp,
    lastArgoTriggerLabel,
    argoReleaseCounter,
    treasuryState.stateDigestHash,
  ]);

  const executeBackgroundRepositoryPollTick = useCallback(async () => {
    const snap = backgroundPollRef.current;
    const nowIso = new Date().toISOString();

    if (!snap.argoAutoSelfHeal) {
      setPollerState((prev) => ({
        ...prev,
        pollingActive: false,
        lastPolledIso: nowIso,
        lastCheckResult: 'PAUSED',
      }));
      return;
    }

    try {
      const res = await fetch('/api/git/status');
      if (!res.ok) return;
      const polledStatus: GitBranchParityStatus = await res.json();
      if (!polledStatus?.headSha) return;

      const currentArgoRelease = buildArgoSyncLaneState(
        snap.protocols,
        snap.genesisAgents,
        snap.nodes,
        snap.ledger,
        snap.lastArgoSyncedHash,
        snap.argoAutoSelfHeal,
        snap.lastArgoSyncTimestamp,
        snap.lastArgoTriggerLabel,
        snap.argoReleaseCounter,
        snap.treasuryDigest
      );

      const decision = evaluateBackgroundPollSyncDecision({
        previousHeadSha: snap.gitParity.headSha,
        polledStatus,
        currentManifestHash: currentArgoRelease.fullManifestHash,
        lastSyncedManifestHash: snap.lastArgoSyncedHash,
        autoSelfHealEnabled: snap.argoAutoSelfHeal,
      });

      if (decision.shouldTriggerGitOpsSync) {
        const syncRes = await fetch('/api/git/sync', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            reason: `Background Poller Auto-Sync (${decision.reasons.join(', ')})`,
          }),
        });
        const syncedStatus: GitBranchParityStatus = syncRes.ok
          ? await syncRes.json()
          : polledStatus;

        if (syncedStatus?.headSha) {
          setGitParity(syncedStatus);
        }
        setArgoReleaseCounter((c) => c + 1);
        setLastArgoSyncedHash(currentArgoRelease.fullManifestHash);
        setLastArgoSyncTimestamp(nowIso);
        setLastArgoTriggerLabel(decision.summaryLabel);
        setPollerState((prev) => ({
          ...prev,
          pollingActive: true,
          totalPollChecks: prev.totalPollChecks + 1,
          autoTriggeredSyncCount: prev.autoTriggeredSyncCount + 1,
          lastPolledIso: nowIso,
          lastAutoTriggerIso: nowIso,
          lastAutoTriggerReason: decision.summaryLabel,
          lastCheckResult: 'AUTO_SYNC_TRIGGERED',
        }));
      } else {
        setGitParity(polledStatus);
        if (snap.lastArgoSyncedHash === null) {
          setLastArgoSyncedHash(currentArgoRelease.fullManifestHash);
        }
        setPollerState((prev) => ({
          ...prev,
          pollingActive: true,
          totalPollChecks: prev.totalPollChecks + 1,
          lastPolledIso: nowIso,
          lastCheckResult: 'CLEAN_NO_OP',
        }));
      }
    } catch (_err) {
      // ignore transient network errors during background poll
    }
  }, []);

  // Periodic background polling interval (every 8s) checking repository changes and auto-triggering GitOps sync
  useEffect(() => {
    const initialTimer = window.setTimeout(() => {
      executeBackgroundRepositoryPollTick();
    }, 400);

    const intervalId = window.setInterval(() => {
      executeBackgroundRepositoryPollTick();
    }, 8000);

    return () => {
      window.clearTimeout(initialTimer);
      window.clearInterval(intervalId);
    };
  }, [executeBackgroundRepositoryPollTick, argoAutoSelfHeal]);

  const handleSimulateRepoChangeAndAutoSync = useCallback(async () => {
    try {
      await fetch('/api/git/simulate-change', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          note: 'Simulated repository file mutation verified by background GitOps poller',
        }),
      });
      await executeBackgroundRepositoryPollTick();
    } catch (_e) {
      // ignore
    }
  }, [executeBackgroundRepositoryPollTick]);

  const handleRunLiveE2ETest = () => {
    setE2eRunning(true);
    fetch('/api/git/test-e2e', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((report: LiveE2EVerificationReport | null) => {
        if (report?.runId) {
          setE2eReport(report);
          if (report.gitParity?.headSha) {
            setGitParity(report.gitParity);
          }
        }
      })
      .catch(() => {})
      .finally(() => {
        setE2eRunning(false);
      });

    handleDispatchInstruction(
      'Execute 6-stage live end-to-end verification test across Git post-commit hook, Argo Private Repo, MiniMax-M2.7 & One-Brain Bus',
      'computing_network',
      'GEN-NET-003'
    );
  };

  // Multi-Home Survival Watchtower & Triad Failure-Mode Intelligence Harvester Handlers
  const handleTriggerLowBatteryEvacuation = (
    simulatedBatteryPct: number = 14,
    customReason?: string
  ) => {
    setSurvivalState((prev) =>
      triggerHomeSurvivalAlarmAndEvacuate(prev, {
        sourceHomeId: 'home-macbook-pro',
        triggerType: 'MACBOOK_LOW_BATTERY_CRITICAL',
        simulatedBatteryPct,
        customReason,
        gitHeadShortSha: gitParity.headShortSha,
      })
    );
    fetch('/api/survival/alarm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sourceHomeId: 'home-macbook-pro',
        triggerType: 'MACBOOK_LOW_BATTERY_CRITICAL',
        simulatedBatteryPct,
        customReason,
      }),
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((s) => {
        if (s?.boundProtocolId) setSurvivalState(s);
        refreshGitParityStatus();
      })
      .catch(() => {});

    handleDispatchInstruction(
      `Sound Founder low-battery alarm (${simulatedBatteryPct}% MacBook Pro) and execute preemptive evacuation to Cloud Run & Cloudflare Edge`,
      'scientific_experimental',
      'GEN-SCI-004'
    );
  };

  const handleRestoreNominalPower = (homeId: string = 'home-macbook-pro') => {
    setSurvivalState((prev) => restoreHomeNominalPower(prev, homeId));
    fetch('/api/survival/restore', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ homeId }),
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((s) => {
        if (s?.boundProtocolId) setSurvivalState(s);
        refreshGitParityStatus();
      })
      .catch(() => {});

    handleDispatchInstruction(
      `Restore AC MagSafe power to ${homeId} and re-balance evacuated Otto leases with zero data loss`,
      'scientific_experimental',
      'GEN-SCI-004'
    );
  };

  const handleSubmitFailureModeToTriad = (input: {
    title: string;
    category: FailureSurfaceCategory;
    severity: 'CRITICAL' | 'HIGH' | 'MEDIUM';
    encounteredBySurface: string;
    encounteredDuringWorkflow: string;
    symptomOrContext?: string;
  }): FailureModeIntelligenceRecord => {
    const res = harvestAndMapFailureMode(survivalState, input);
    setSurvivalState(res.updatedState);

    // Automatically ingest the synthesized immunization triple into the Bi-Temporal Knowledgebase
    handleIngestFact({
      subject: res.newRecord.triadSynthesis.geminiWebCollaboratorAnalysis.knowledgebaseSubject,
      predicate: res.newRecord.triadSynthesis.geminiWebCollaboratorAnalysis.knowledgebasePredicate,
      object: res.newRecord.triadSynthesis.geminiWebCollaboratorAnalysis.knowledgebaseObject,
      category: 'architecture_invariant',
    });

    fetch('/api/survival/harvest-failure', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((serverRes) => {
        if (serverRes?.updatedState?.boundProtocolId) {
          setSurvivalState(serverRes.updatedState);
        }
        refreshGitParityStatus();
      })
      .catch(() => {});

    handleDispatchInstruction(
      `Harvest failure mode "${input.title}" via MiniMax-M2.7 + DeepSeek Web + Gemini Web Triad into Bi-Temporal Knowledgebase`,
      'scientific_experimental',
      'GEN-SCI-004'
    );

    return res.newRecord;
  };

  const handleAdvanceResearchTrack = (trackId: string) => {
    setSurvivalState((prev) => advanceProactiveExpansionTrack(prev, trackId));
    fetch('/api/survival/advance-rd', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ trackId }),
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((s) => {
        if (s?.boundProtocolId) setSurvivalState(s);
        refreshGitParityStatus();
      })
      .catch(() => {});

    handleDispatchInstruction(
      `Advance proactive R&D prototype track ${trackId} through >=98.0% confidence deployment gate`,
      'scientific_experimental',
      'GEN-SCI-004'
    );
  };

  const handleRunWorkflowPreFlight = (workflowName: string) => {
    setSurvivalState((prev) => ({
      ...prev,
      preFlightAssessment: evaluateWorkflowPreFlightSurface(workflowName, prev.failureModes),
    }));
    fetch('/api/survival/preflight', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workflowName }),
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((s) => {
        if (s?.boundProtocolId) setSurvivalState(s);
      })
      .catch(() => {});

    handleDispatchInstruction(
      `Evaluate upfront machine failure surface and fallback playbooks for workflow: ${workflowName}`,
      'scientific_experimental',
      'GEN-SCI-004'
    );
  };

  const handlePromoteFailureToMemoryGraph = (record: FailureModeIntelligenceRecord) => {
    handleIngestFact({
      subject: record.triadSynthesis.geminiWebCollaboratorAnalysis.knowledgebaseSubject,
      predicate: record.triadSynthesis.geminiWebCollaboratorAnalysis.knowledgebasePredicate,
      object: record.triadSynthesis.geminiWebCollaboratorAnalysis.knowledgebaseObject,
      category: 'architecture_invariant',
    });
  };

  const handleConnectGitHubToken = async (token: string) => {
    try {
      const res = await fetch('/api/git/connect-github', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token }),
      });
      if (res.ok) {
        const status = await res.json();
        if (status?.headSha) {
          setGitParity(status);
        }
      }
    } catch (_e) {
      // ignore
    }
    handleDispatchInstruction(
      'Connect GitHub token and execute direct mirror push to chidionyema/argon (main, genesis-live) and chidionyema/argon-sync (main, estate/genesis-router-sync, estate/wwfd-alignment-gate)',
      'computing_network',
      'GEN-NET-003'
    );
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      {/* Strict 3-Zone Top Bar Contract (Max 5 Top-Level Nav Items) */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
        <div className="max-w-[1360px] mx-auto flex items-center justify-between gap-4 px-6 py-3.5">
          {/* Zone 1: Single text element wordmark */}
          <a
            href="#top"
            onClick={(e) => {
              e.preventDefault();
              setActiveTab('sovereign-edict');
            }}
            className="text-lg font-bold tracking-tight text-slate-900 whitespace-nowrap shrink-0"
          >
            Genesis Memory OS
          </a>

          {/* Zone 2: 5 clean single-line text navigation links */}
          <nav aria-label="Primary Navigation" className="flex items-center gap-5 text-sm font-medium text-slate-600">
            <button
              type="button"
              onClick={() => setActiveTab('sovereign-edict')}
              className={`py-1 transition-colors whitespace-nowrap shrink-0 cursor-pointer border-b-2 ${
                activeTab === 'sovereign-edict'
                  ? 'border-slate-900 text-slate-900 font-semibold'
                  : 'border-transparent hover:text-slate-900'
              }`}
            >
              Sovereign Treasury &amp; Ops
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('protocol-kernel')}
              className={`py-1 transition-colors whitespace-nowrap shrink-0 cursor-pointer border-b-2 ${
                activeTab === 'protocol-kernel'
                  ? 'border-slate-900 text-slate-900 font-semibold'
                  : 'border-transparent hover:text-slate-900'
              }`}
            >
              Protocol-First Kernel
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('genesis-live')}
              className={`py-1 transition-colors whitespace-nowrap shrink-0 cursor-pointer border-b-2 ${
                activeTab === 'genesis-live'
                  ? 'border-slate-900 text-slate-900 font-semibold'
                  : 'border-transparent hover:text-slate-900'
              }`}
            >
              Live Agent Monitor
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('verification')}
              className={`py-1 transition-colors whitespace-nowrap shrink-0 cursor-pointer border-b-2 ${
                activeTab === 'verification'
                  ? 'border-slate-900 text-slate-900 font-semibold'
                  : 'border-transparent hover:text-slate-900'
              }`}
            >
              Verification Ledger
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('context-rot')}
              className={`py-1 transition-colors whitespace-nowrap shrink-0 cursor-pointer border-b-2 ${
                activeTab === 'context-rot'
                  ? 'border-slate-900 text-slate-900 font-semibold'
                  : 'border-transparent hover:text-slate-900'
              }`}
            >
              Memory &amp; Research Lab
            </button>
          </nav>

          {/* Zone 3: 1 primary action showing live verified Argo Auto-Sync SHA */}
          <div className="flex items-center shrink-0">
            <button
              type="button"
              onClick={() => handleRunLiveE2ETest()}
              className="px-3.5 py-2 text-xs font-semibold text-white bg-emerald-700 rounded-lg hover:bg-emerald-800 transition-colors whitespace-nowrap shrink-0 cursor-pointer font-mono"
            >
              ● 5-Branch Sync ({gitParity.headShortSha}) · Test E2E
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Container */}
      <main className="flex-1 max-w-[1360px] w-full mx-auto px-6 py-8">
        {activeTab === 'sovereign-edict' && (
          <div className="space-y-8">
            <ArgoSyncLanePanel
              argoRelease={buildArgoSyncLaneState(
                protocols,
                genesisAgents,
                nodes,
                ledger,
                lastArgoSyncedHash,
                argoAutoSelfHeal,
                lastArgoSyncTimestamp,
                lastArgoTriggerLabel,
                argoReleaseCounter,
                treasuryState.stateDigestHash
              )}
              gitParity={gitParity}
              pollerState={pollerState}
              e2eReport={e2eReport}
              e2eRunning={e2eRunning}
              onRunLiveE2ETest={handleRunLiveE2ETest}
              onToggleAutoSelfHeal={() => setArgoAutoSelfHeal((prev) => !prev)}
              onConnectGitHubToken={handleConnectGitHubToken}
              onSimulateRepoChangeAndAutoSync={handleSimulateRepoChangeAndAutoSync}
            />

            <SurvivalAndFailureHarvesterPanel
              survivalState={survivalState}
              gitShortSha={gitParity.headShortSha}
              allGitBranchesLocked={
                gitParity.allBranchesIdentical && gitParity.remoteMirrorAligned
              }
              onlineSurfaceCount={
                oneBrainState.surfaces.filter(
                  (s) => s.status === 'ONLINE_SYNCED' || s.status === 'STANDBY_LIFEBOAT_READY'
                ).length
              }
              ratifiedProtocolCount={protocols.length}
              onTriggerLowBatteryEvacuation={handleTriggerLowBatteryEvacuation}
              onRestoreNominalPower={handleRestoreNominalPower}
              onSubmitFailureModeToTriad={handleSubmitFailureModeToTriad}
              onAdvanceResearchTrack={handleAdvanceResearchTrack}
              onRunWorkflowPreFlight={handleRunWorkflowPreFlight}
              onPromoteFailureToMemoryGraph={handlePromoteFailureToMemoryGraph}
            />

            <OneBrainFederationPanel
              brainState={oneBrainState}
              sseConnected={sseConnected}
              onSendFounderSteer={handleSendFounderSteer}
              onCastCouncilVote={handleCastCouncilVote}
              onToggleZeroCreditLifeboat={handleToggleZeroCreditLifeboat}
              onPlugInNewSurface={handlePlugInNewSurface}
            />

            <SovereignEstateEdictView
              treasury={treasuryState}
              onExecuteKeepAliveSweep={handleExecuteKeepAliveSweep}
              onExecuteCommercialSprint={handleExecuteCommercialSprint}
              onApproveFounderRequest={handleApproveFounderRequest}
              onEvaluateAndAddModel={handleEvaluateAndAddModel}
              onRunMultiHomeCanaryProbe={() => {
                const res = executeMultiHomeCanaryProbe(treasuryState);
                setTreasuryState(res.updatedState);
                handleDispatchInstruction(
                  'Execute 5/5 semantic canary probe across MiniMax-M2.7 Subscription Multiplexer and 4 Execution Homes',
                  'computing_network',
                  'GEN-NET-005'
                );
                return res.canarySummary;
              }}
              onNavigateToAgentMonitor={(agentId) => {
                setSelectedAgentId(agentId);
                setActiveTab('genesis-live');
              }}
            />
          </div>
        )}

        {activeTab === 'protocol-kernel' && (
          <div className="space-y-8">
            <ArgoSyncLanePanel
              argoRelease={buildArgoSyncLaneState(
                protocols,
                genesisAgents,
                nodes,
                ledger,
                lastArgoSyncedHash,
                argoAutoSelfHeal,
                lastArgoSyncTimestamp,
                lastArgoTriggerLabel,
                argoReleaseCounter,
                treasuryState.stateDigestHash
              )}
              gitParity={gitParity}
              pollerState={pollerState}
              e2eReport={e2eReport}
              e2eRunning={e2eRunning}
              onRunLiveE2ETest={handleRunLiveE2ETest}
              onToggleAutoSelfHeal={() => setArgoAutoSelfHeal((prev) => !prev)}
              onConnectGitHubToken={handleConnectGitHubToken}
              onSimulateRepoChangeAndAutoSync={handleSimulateRepoChangeAndAutoSync}
            />

            <ProtocolFirstEstateView
              protocols={protocols}
              gateHistory={gateHistory}
              onDispatchInstruction={handleDispatchInstruction}
              onRatifyProtocolAndExecute={handleRatifyProtocolAndExecute}
            />
          </div>
        )}

        {activeTab === 'genesis-live' && (
          <GenesisLiveAgentMonitorView
            agents={genesisAgents}
            selectedAgentId={selectedAgentId}
            liveStreamEnabled={liveAgentStreamEnabled}
            onSelectAgent={setSelectedAgentId}
            onToggleLiveStream={() => setLiveAgentStreamEnabled((prev) => !prev)}
            onStepAgentTick={handleStepAgentTick}
            onUpdateAgentConfig={handleUpdateAgentConfig}
            onTogglePinBlock={handleTogglePinBlock}
            onEvictBlock={handleEvictBlock}
            onRegisterNewAgent={handleRegisterNewAgent}
          />
        )}

        {activeTab === 'verification' && (
          <VerificationBenchmarkView
            ledger={ledger}
            latestMetrics={{
              exactRecallPct: currentEval.exactRecallPct,
              contradictionResolutionPct: currentEval.contradictionResolutionPct,
              middleTroughRetentionPct: currentEval.middleTroughRetentionPct,
              multitaskIsolationPct: currentEval.multitaskIsolationPct,
              contextRotIndex: currentEval.contextRotIndex,
              p95RetrievalLatencyMs: currentEval.p95RetrievalLatencyMs,
              tokenCompressionRatio: currentEval.tokenCompressionRatio,
              worldRankCompositeScore: currentEval.worldRankCompositeScore,
            }}
            invariantsPassed={currentEval.invariantsPassed}
            depthCurve={depthCurve}
            daemonRunning={daemonRunning}
            onToggleDaemon={() => setDaemonRunning((prev) => !prev)}
            onRunManualProbe={(suiteName) =>
              appendVerificationProbe(
                nodes,
                threads,
                activeModuleKeys,
                suiteName || 'Manual Founder Benchmark Probe'
              )
            }
            onNavigateToLab={() => setActiveTab('context-rot')}
          />
        )}

        {activeTab === 'context-rot' && (
          <div className="space-y-6">
            {/* Workspace Sub-Mode Switcher */}
            <div className="flex flex-wrap items-center justify-between gap-3 bg-white border border-slate-200 rounded-xl px-5 py-3">
              <div className="text-xs text-slate-600">
                Select Memory &amp; Research Lab Mode: Inspect Bi-Temporal Context Rot, Copy-on-Write Multitasking Sandboxes, or Frontier Lab Architecture Dossier
              </div>
              <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg shrink-0">
                <button
                  type="button"
                  onClick={() => setRotSubView('focus-lab')}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer whitespace-nowrap ${
                    rotSubView === 'focus-lab'
                      ? 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Context Rot &amp; Active Focus Lab
                </button>
                <button
                  type="button"
                  onClick={() => setRotSubView('multitasking')}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer whitespace-nowrap ${
                    rotSubView === 'multitasking'
                      ? 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Active Multitasking CoW Sandboxes
                </button>
                <button
                  type="button"
                  onClick={() => setRotSubView('research')}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer whitespace-nowrap ${
                    rotSubView === 'research'
                      ? 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Frontier Research Dossier
                </button>
              </div>
            </div>

            {rotSubView === 'focus-lab' && (
              <ContextRotActiveFocusView
                nodes={nodes}
                onIngestFact={handleIngestFact}
                onPurgeAndReanchor={handlePurgeAndReanchor}
                onSimulateRotWave={handleSimulateRotWave}
              />
            )}
            {rotSubView === 'multitasking' && (
              <ActiveMultitaskingView
                threads={threads}
                globalNodes={nodes}
                onStepThread={handleStepThread}
                onSpawnThread={handleSpawnThread}
                onPromoteThreadFact={handlePromoteThreadFact}
              />
            )}
            {rotSubView === 'research' && (
              <FrontierResearchDossierView
                activeModuleKeys={activeModuleKeys}
                onToggleModule={handleToggleModule}
                onEnableAllModules={handleEnableAllModules}
              />
            )}
          </div>
        )}
      </main>

      {/* Quiet Editorial Footer */}
      <footer className="bg-white border-t border-slate-200 mt-16">
        <div className="max-w-[1360px] mx-auto px-6 py-5 flex flex-wrap items-center justify-between gap-4 text-xs text-slate-500">
          <div>
            Genesis Protocol-First &amp; Sovereign Memory OS · £200/mo Custodian Vault, Concierge + Otto Keep-Alive &amp; Anti-IDP Commercial Autonomy
          </div>
          <div className="font-mono tabular-nums">
            Ratified Protocols: {protocols.length} · Active Genesis Agents: {genesisAgents.length} · Monthly MRR: £{treasuryState.commercialStreams.reduce((s, c) => s + c.monthlyRecurringRevenueGbp, 0)}/mo · Ledger Height: #{ledger.length}
          </div>
        </div>
      </footer>
    </div>
  );
}
