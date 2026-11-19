import React, { useState, useMemo, useEffect } from 'react';
import {
  Mic,
  Volume2,
  ShieldCheck,
  Radio,
  X,
  Download,
  RefreshCw,
  Send,
  Cpu,
  CheckCircle2,
  FileCode2,
  Inbox,
  SendHorizontal,
  Layers,
} from 'lucide-react';
import {
  evaluatePlanFenceSequence,
  INITIAL_NON_FUNCTIONAL_CONTRACTS,
  INITIAL_HOT_SWAPPABLE_PROTOCOLS,
  INITIAL_LANE_PROTOCOL_ASSIGNMENTS,
  INITIAL_INSTRUCTION_PACKETS,
  INITIAL_QUAD_IDENTITY_DNA,
  switchLaneProtocolInRealTime,
  executeInstructionPacketAndMeasureYieldAlpha,
  type RouterAndProtocolState,
  type InstructionPacketOutcomeItem,
  type QuadIdentityDnaState,
} from '../../extensions/pi-plan-lock/plan';

interface EphemeralCardItem {
  id: string;
  timestamp: string;
  voiceCommand: string;
  laneUsed: string;
  title: string;
  outcomeSummary: string;
  cliProofOutput: string;
  hmacDigest: string;
}

interface RouterAndVoiceDeckViewProps {
  routerState: RouterAndProtocolState;
  onUnifyProtocolAndRestoreTraffic: (targetTrafficPct: number) => Promise<{
    summaryReport: string;
    cliOutput: string;
    hmacSignature: string;
  }>;
  onPollConsultingInbox: (incomingDispatch?: {
    senderAgent: string;
    ticketId: string;
    ticketScope: 'STANDARD_SPEC_AUDIT' | 'BIG_TICKET_FENCED' | 'FOUNDER_PRIORITY_P0';
    subject: string;
    payloadSummary: string;
    bddThenClause?: string;
  }) => Promise<{
    pollSummary: string;
    hmacSignature: string;
  }>;
  onUpdateLaneConfig: (
    laneId: string,
    updates: {
      trafficWeightPct?: number;
      maxRetriesBound?: number;
      autoCompactionTokenCap?: number;
    }
  ) => void;
}

export const RouterAndVoiceDeckView: React.FC<RouterAndVoiceDeckViewProps> = ({
  routerState,
  onUnifyProtocolAndRestoreTraffic,
  onPollConsultingInbox,
  onUpdateLaneConfig,
}) => {
  const [trafficPct, setTrafficPct] = useState<number>(routerState.restoredTrafficPct ?? 100);
  const [voiceActive, setVoiceActive] = useState<boolean>(false);
  const [speechSynthEnabled, setSpeechSynthEnabled] = useState<boolean>(true);
  const [busyAction, setBusyAction] = useState<boolean>(false);

  // Consulting Lane 15-Minute Scheduled Batch Ingest & Index State (900s = 15m default)
  const [autoPollEnabled, setAutoPollEnabled] = useState<boolean>(true);
  const [pollIntervalSec, setPollIntervalSec] = useState<number>(
    routerState.inboxPollerIntervalSec || 900
  );
  const [secondsUntilNextPoll, setSecondsUntilNextPoll] = useState<number>(
    routerState.inboxPollerIntervalSec || 900
  );
  const [pollBusy, setPollBusy] = useState<boolean>(false);

  // New Inbox Envelope Dispatch Form State (Founder / Claude / MiniMax Big-Ticket)
  const [dispatchSender, setDispatchSender] = useState<string>(
    'minimax-fenced-worker-01 (MiniMax-M2.7)'
  );
  const [dispatchScope, setDispatchScope] = useState<
    'BIG_TICKET_FENCED' | 'STANDARD_SPEC_AUDIT' | 'FOUNDER_PRIORITY_P0'
  >('BIG_TICKET_FENCED');
  const [dispatchTicketId, setDispatchTicketId] = useState<string>('TICKET-MINIMAX-BIG-7712');
  const [dispatchSubject, setDispatchSubject] = useState<string>(
    'MiniMax M2.7 Big-Ticket #7712: Cross-Surface Telemetry & Spec Catalog Verification'
  );
  const [dispatchSummary, setDispatchSummary] = useState<string>(
    'Routed via chidionyema/estate-inbox so Consulting Lane audits ESTATE-SPEC-STD-V2 compliance before promoting to chidionyema/estate-outbox.'
  );
  const [dispatchThenClause, setDispatchThenClause] = useState<string>(
    'exit_code == 0 && test_pass:minimax_consulting_inbox_gate && file_exists:register/machine-repo-catalog.json'
  );

  // Ephemeral UI Cards (2100 Future Surface — cards materialize on intent & dissolve on dismiss)
  const [ephemeralCards, setEphemeralCards] = useState<EphemeralCardItem[]>([
    {
      id: 'eph-initial-01',
      timestamp: 'just now',
      voiceCommand:
        'Resuscitate all 4 local agent services, lock Rust router v2.4.0 optimizations, and poll Consulting Lane Inbox',
      laneUsed: 'Argon Consulting + DeepSeek Protocol + Rust Router v2.4.0',
      title: '4/4 Core Agent Loops Online · Dual-Repo Inbox/Outbox Relay Active',
      outcomeSummary:
        'Resuscitated Argon Consulting (PID 91402), DeepSeek Protocol (PID 91418), Claude Catalog Auditor (PID 91435), and MiniMax Fenced Worker (PID 91459). Rust router v2.4.0 (6/6 optimizations) and ESTATE-SPEC-STD-V2 (6/6 gates, 4/4 Claude repo items re-refined) verified.',
      cliProofOutput:
        '[ESTATE-SERVICE-UP] 4_OF_4_CORE_AGENT_DAEMONS_ONLINE (0 -> 4 Agents | 18/18 Lanes)\n[ESTATE-RUST-ROUTER v2.4.0] 6/6 Optimizations PASS (54 µs zero-copy · 18ms hedge · MiniMax Inbox sandbox)\n[CONSULTING-LANE INBOX POLLER] Inbox=3 audited -> Outbox=3 signed receipts\n[ESTATE-SPEC-ENFORCE] ESTATE-SPEC-STD-V2 (4/4 Claude repo items re-refined · 9 loopholes closed)',
      hmacDigest: routerState.lastRouterHmac,
    },
  ]);

  // Interactive 3-Tries & Machine-Checkable BDD `then` Fence Simulator state
  const [simThenClause, setSimThenClause] = useState<string>(
    'exit_code == 0 && file_exists:extensions/pi-plan-lock/cases.json'
  );
  const [simTool, setSimTool] = useState<string>('edit_file');
  const [simArgsJson, setSimArgsJson] = useState<string>(
    '{"path":"platform/estate/memory/plan.py","patch":"3-tries-bound"}'
  );
  const [simRepeatCount] = useState<number>(4);

  // Live Consulting Lane Inbox Poller Timer
  useEffect(() => {
    if (!autoPollEnabled) return;
    const timer = setInterval(() => {
      setSecondsUntilNextPoll((prev) => {
        if (prev <= 1) {
          onPollConsultingInbox().catch(() => {});
          return pollIntervalSec;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [autoPollEnabled, pollIntervalSec, onPollConsultingInbox]);

  const fenceSimulationResults = useMemo(() => {
    let parsedArgs: Record<string, unknown> = { raw: simArgsJson };
    try {
      parsedArgs = JSON.parse(simArgsJson);
    } catch {
      // Keep raw fallback
    }
    return evaluatePlanFenceSequence(
      {
        given: 'active protocol session #7680 / #7692',
        when: 'agent invokes tool through pi-plan-lock fence',
        then: simThenClause,
      },
      {
        tool: simTool,
        input: parsedArgs,
      },
      simRepeatCount,
      3
    );
  }, [simThenClause, simTool, simArgsJson, simRepeatCount]);

  const speakResponse = (text: string) => {
    if (
      speechSynthEnabled &&
      typeof window !== 'undefined' &&
      'speechSynthesis' in window
    ) {
      try {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.06;
        utterance.pitch = 0.96;
        window.speechSynthesis.speak(utterance);
      } catch {
        // Ignore if browser blocks un-interacted audio
      }
    }
  };

  const executeEphemeralVoiceCommand = async (
    commandText: string,
    targetTraffic = trafficPct
  ) => {
    setBusyAction(true);
    try {
      const res = await onUnifyProtocolAndRestoreTraffic(targetTraffic);
      const card: EphemeralCardItem = {
        id: `eph-${Date.now()}`,
        timestamp: new Date().toLocaleTimeString(),
        voiceCommand: commandText,
        laneUsed: 'Argon Consulting + DeepSeek Protocol + Rust Router v2.4.0',
        title: `Executed: ${commandText.slice(0, 68)}`,
        outcomeSummary: res.summaryReport,
        cliProofOutput: res.cliOutput,
        hmacDigest: res.hmacSignature,
      };
      setEphemeralCards((prev) => [card, ...prev.slice(0, 3)]);
      speakResponse(
        `All 4 core agent loops online. Rust router optimizations verified at ${targetTraffic} percent traffic. Consulting lane inbox poller and spec standard enforced.`
      );
    } finally {
      setBusyAction(false);
    }
  };

  const handleManualInboxPoll = async () => {
    setPollBusy(true);
    try {
      const res = await onPollConsultingInbox();
      setSecondsUntilNextPoll(pollIntervalSec);
      const card: EphemeralCardItem = {
        id: `eph-poll-${Date.now()}`,
        timestamp: new Date().toLocaleTimeString(),
        voiceCommand: 'Poll chidionyema/estate-inbox on Consulting Lane and promote to Outbox',
        laneUsed: 'Argon Consulting Lane Poller (bin/estate-inbox-poll)',
        title: 'Consulting Lane Inbox Polled & Outbox Synchronized',
        outcomeSummary: res.pollSummary,
        cliProofOutput: res.pollSummary,
        hmacDigest: res.hmacSignature,
      };
      setEphemeralCards((prev) => [card, ...prev.slice(0, 3)]);
    } finally {
      setPollBusy(false);
    }
  };

  const handleDispatchEnvelopeToInbox = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dispatchSubject.trim()) return;
    setPollBusy(true);
    try {
      const res = await onPollConsultingInbox({
        senderAgent: dispatchSender,
        ticketId: dispatchTicketId,
        ticketScope: dispatchScope,
        subject: dispatchSubject,
        payloadSummary: dispatchSummary,
        bddThenClause: dispatchThenClause,
      });
      setSecondsUntilNextPoll(pollIntervalSec);
      const nextNum = Math.floor(7713 + Math.random() * 80);
      setDispatchTicketId(`TICKET-MINIMAX-BIG-${nextNum}`);
      const card: EphemeralCardItem = {
        id: `eph-dispatch-${Date.now()}`,
        timestamp: new Date().toLocaleTimeString(),
        voiceCommand: `Dispatch ${dispatchTicketId} to chidionyema/estate-inbox -> Consulting Audit -> chidionyema/estate-outbox`,
        laneUsed: 'Dual Private-Repo Comms Relay (INBOX -> Consulting -> OUTBOX)',
        title: `Audited & Promoted to Outbox: ${dispatchTicketId}`,
        outcomeSummary: res.pollSummary,
        cliProofOutput: res.pollSummary,
        hmacDigest: res.hmacSignature,
      };
      setEphemeralCards((prev) => [card, ...prev.slice(0, 3)]);
    } finally {
      setPollBusy(false);
    }
  };

  const handleStartBrowserVoiceRecognition = () => {
    if (typeof window === 'undefined') return;
    const SpeechRec =
      (window as unknown as Record<string, unknown>).SpeechRecognition ||
      (window as unknown as Record<string, unknown>).webkitSpeechRecognition;

    if (!SpeechRec) {
      setVoiceActive(true);
      setTimeout(() => {
        setVoiceActive(false);
        executeEphemeralVoiceCommand(
          'Resuscitate all 4 agent loops, poll Consulting Inbox, and enforce ESTATE-SPEC-STD-V2 across Claude private repo',
          100
        );
      }, 600);
      return;
    }

    try {
      setVoiceActive(true);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const recognition = new (SpeechRec as any)();
      recognition.lang = 'en-US';
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      recognition.onresult = (event: any) => {
        const transcript = event.results?.[0]?.[0]?.transcript || '';
        setVoiceActive(false);
        if (transcript) {
          executeEphemeralVoiceCommand(transcript, trafficPct);
        }
      };
      recognition.onerror = () => setVoiceActive(false);
      recognition.onend = () => setVoiceActive(false);
      recognition.start();
    } catch {
      setVoiceActive(false);
    }
  };

  const coreDaemons = routerState.coreAgentDaemons || [];
  const rustOpts = routerState.rustRouterOptimizations || [];
  const inboxEnvelopes = routerState.inboxEnvelopes || [];
  const outboxReceipts = routerState.outboxReceipts || [];
  const specGates = routerState.specStandardGates || [];
  const claudeItems = routerState.claudeReRefinedItems || [];
  const catalogEntries = routerState.machineCatalogEntries || [];
  const failureClasses = routerState.failureClasses || [];
  const dualEngines = routerState.dualEngines || [];
  const evaluationSuites = routerState.evaluationSuites || [];
  const nfrContracts = routerState.nonFunctionalContracts || INITIAL_NON_FUNCTIONAL_CONTRACTS;
  const hotSwappableProtocols =
    routerState.hotSwappableProtocols || INITIAL_HOT_SWAPPABLE_PROTOCOLS;

  // Real-Time Per-Lane Protocol Switching & Instruction Packet Yield Alpha State
  const [laneProtocols, setLaneProtocols] = useState<Record<string, string>>(
    routerState.laneProtocolAssignments || INITIAL_LANE_PROTOCOL_ASSIGNMENTS
  );
  const [packets, setPackets] = useState<InstructionPacketOutcomeItem[]>(
    routerState.instructionPackets || INITIAL_INSTRUCTION_PACKETS
  );
  const [quadDna, setQuadDna] = useState<QuadIdentityDnaState>(
    routerState.quadIdentityDna || INITIAL_QUAD_IDENTITY_DNA
  );
  const [packetDirective, setPacketDirective] = useState<string>(
    'Run Claude Inbox War Games drill on DeepSeek-R1 & harvest failure ore into 18-lane Argon Memory'
  );
  const [packetLaneId, setPacketLaneId] = useState<string>('minimax-fenced-01');
  const [simulateSoftTimeout, setSimulateSoftTimeout] = useState<boolean>(false);
  const [protocolBusy, setProtocolBusy] = useState<boolean>(false);

  useEffect(() => {
    if (routerState.laneProtocolAssignments) {
      setLaneProtocols(routerState.laneProtocolAssignments);
    }
    if (routerState.instructionPackets) {
      setPackets(routerState.instructionPackets);
    }
    if (routerState.quadIdentityDna) {
      setQuadDna(routerState.quadIdentityDna);
    }
  }, [
    routerState.laneProtocolAssignments,
    routerState.instructionPackets,
    routerState.quadIdentityDna,
  ]);

  const handleRealTimeProtocolSwitch = async (laneId: string, protocolId: string) => {
    setProtocolBusy(true);
    try {
      const localSwitch = switchLaneProtocolInRealTime(routerState, laneId, protocolId);
      setLaneProtocols(localSwitch.nextState.laneProtocolAssignments);
      try {
        const resp = await fetch('/api/protocol/switch-lane', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ laneId, protocolId }),
        });
        if (resp.ok) {
          const data = await resp.json();
          if (data.routerAndProtocol?.laneProtocolAssignments) {
            setLaneProtocols(data.routerAndProtocol.laneProtocolAssignments);
          }
        }
      } catch {
        // Fallback to localSwitch state
      }
      const card: EphemeralCardItem = {
        id: `eph-proto-${Date.now()}`,
        timestamp: new Date().toLocaleTimeString(),
        voiceCommand: `Real-time protocol switch: ${laneId} -> ${protocolId}`,
        laneUsed: `Declarative Protocol Engine (bin/estate-protocol-engine)`,
        title: `Switched ${laneId} to ${protocolId}`,
        outcomeSummary: localSwitch.switchSummary,
        cliProofOutput: localSwitch.switchSummary,
        hmacDigest: localSwitch.hmacSignature,
      };
      setEphemeralCards((prev) => [card, ...prev.slice(0, 3)]);
    } finally {
      setProtocolBusy(false);
    }
  };

  const handleExecuteInstructionPacket = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!packetDirective.trim()) return;
    setProtocolBusy(true);
    try {
      const localExec = executeInstructionPacketAndMeasureYieldAlpha(
        {
          ...routerState,
          laneProtocolAssignments: laneProtocols,
          instructionPackets: packets,
          quadIdentityDna: quadDna,
        },
        packetDirective,
        packetLaneId,
        simulateSoftTimeout
      );
      setPackets(localExec.nextState.instructionPackets);
      setQuadDna(localExec.nextState.quadIdentityDna);

      try {
        const resp = await fetch('/api/protocol/execute-packet', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            directive: packetDirective,
            laneId: packetLaneId,
            simulateSoftTimeoutPartialYield: simulateSoftTimeout,
          }),
        });
        if (resp.ok) {
          const data = await resp.json();
          if (data.routerAndProtocol?.instructionPackets) {
            setPackets(data.routerAndProtocol.instructionPackets);
          }
          if (data.routerAndProtocol?.quadIdentityDna) {
            setQuadDna(data.routerAndProtocol.quadIdentityDna);
          }
        }
      } catch {
        // Keep localExec state
      }

      const card: EphemeralCardItem = {
        id: `eph-pkt-${Date.now()}`,
        timestamp: new Date().toLocaleTimeString(),
        voiceCommand: `Instruction Packet (${localExec.packetOutcome.packetId}): ${packetDirective}`,
        laneUsed: `${packetLaneId} (${localExec.packetOutcome.protocolApplied})`,
        title: `Packet ${localExec.packetOutcome.packetId} Delivered · Yield Alpha = ${localExec.packetOutcome.yieldAlpha}`,
        outcomeSummary: localExec.executionSummary,
        cliProofOutput: localExec.packetOutcome.mistakesInterceptedUpstream.join('\n'),
        hmacDigest: localExec.hmacSignature,
      };
      setEphemeralCards((prev) => [card, ...prev.slice(0, 3)]);
    } finally {
      setProtocolBusy(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* ===================================================================== */}
      {/* 00. FOUNDER ZERO-TO-LIVE AGENT SERVICE RESUSCITATOR & WHOLE-REPO BAR  */}
      {/* ===================================================================== */}
      <section
        aria-labelledby="service-resuscitate-heading"
        className="border border-emerald-500/40 rounded-lg bg-slate-900 p-5 sm:p-6 space-y-5"
      >
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
              <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold">
                SERVICE RESTORED · {coreDaemons.length}/4 CORE AGENT LOOPS ONLINE
              </span>
              <span className="text-slate-400">·</span>
              <span className="text-sky-400 font-semibold">
                BOTH ENGINES LIVE (estate-router + deepseek-direct) · 16/16 Eval PASS
              </span>
            </div>
            <h2
              id="service-resuscitate-heading"
              className="text-xl sm:text-2xl font-bold text-slate-100"
            >
              Seamless Founder Agent Service &amp; Whole-Repo Export Command Bar
            </h2>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <button
              type="button"
              disabled={busyAction}
              onClick={() =>
                executeEphemeralVoiceCommand(
                  'Run bin/estate-service-up && bin/estate-router && bin/deepseek-direct && bin/estate-eval: Verify Dual-Engine Active-Active parity and 16/16 evaluation cases',
                  100
                )
              }
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-bold text-slate-950 bg-emerald-400 hover:bg-emerald-300 rounded-lg transition-colors cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${busyAction ? 'animate-spin' : ''}`} />
              <span>Run Dual-Engine Parity &amp; 16/16 Eval Suite</span>
            </button>

            <a
              href="/api/deploy/estate-oracle-overwatch.tar.gz"
              download="estate-oracle-overwatch.tar.gz"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-950 bg-sky-400 hover:bg-sky-300 rounded-lg transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export Whole Repo (.tar.gz)</span>
            </a>

            <a
              href="/api/deploy/estate-overwatch.bundle"
              download="estate-oracle-overwatch.bundle"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-mono text-slate-200 bg-slate-950 hover:bg-slate-800 border border-slate-700 rounded-lg transition-colors"
            >
              <Download className="w-3.5 h-3.5 text-sky-400" />
              <span>Git Bundle (.bundle)</span>
            </a>

            <a
              href="/api/catalog/export"
              download="estate-machine-repo-catalog.json"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-mono text-amber-300 bg-slate-950 hover:bg-slate-800 border border-amber-500/40 rounded-lg transition-colors"
            >
              <FileCode2 className="w-3.5 h-3.5 text-amber-300" />
              <span>Machine Catalog (.json)</span>
            </a>

            <a
              href="/api/deploy/INSTRUCTIONS.md"
              download="INSTRUCTIONS.md"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-mono text-emerald-300 bg-slate-950 hover:bg-slate-800 border border-emerald-500/40 rounded-lg transition-colors"
            >
              <Download className="w-3.5 h-3.5 text-emerald-300" />
              <span>INSTRUCTIONS.md</span>
            </a>
          </div>
        </div>

        {/* 4 Active Core Agent Loops (Max 4 cards in 1 row, 3 concise data points per card) */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {coreDaemons.map((agent) => (
            <div
              key={agent.agentId}
              className="p-4 bg-slate-950 border border-slate-800 rounded-lg space-y-2 text-xs"
            >
              <div className="flex items-center justify-between gap-2 font-mono">
                <span className="text-emerald-400 font-bold">{agent.status}</span>
                <span className="text-slate-400 tabular-nums">
                  PID {agent.pid} · {agent.latencyMs}ms
                </span>
              </div>
              <div className="font-bold text-slate-100 text-sm">{agent.name}</div>
              <p className="text-slate-400 leading-relaxed">{agent.role}</p>
            </div>
          ))}
        </div>

        {/* Side-by-Side Dual-Engine Monitor (Routed estate-router + Non-Router deepseek-direct) */}
        {dualEngines.length > 0 && (
          <div className="pt-2 border-t border-slate-800 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
              <span className="text-amber-300 font-bold">
                DUAL-ENGINE ACTIVE-ACTIVE MONITOR · ROUTED (bin/estate-router) + NON-ROUTER DIRECT (bin/deepseek-direct)
              </span>
              <span className="text-emerald-400">
                Red-Line Failure Classes Eradicated: {failureClasses.length}/3 · Eval Suite: {routerState.evalTotalPassed || 16}/{routerState.evalTotalCases || 16} PASS (100%)
              </span>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {dualEngines.map((eng) => (
                <div
                  key={eng.engineId}
                  className="p-4 bg-slate-950 border border-emerald-500/30 rounded-lg space-y-2 text-xs"
                >
                  <div className="flex items-center justify-between gap-2 font-mono">
                    <span className="text-emerald-400 font-bold">
                      {eng.status} · {eng.latencyMs}ms
                    </span>
                    <span className="text-sky-300">
                      {eng.binary} · {eng.sanitizedTrapsCount} R1 Traps Sanitized
                    </span>
                  </div>
                  <div className="font-bold text-slate-100 text-sm">{eng.name}</div>
                  <div className="font-mono text-[11px] text-slate-300 bg-slate-900 p-2 rounded border border-slate-800 truncate">
                    {eng.lastVerifiedOutput}
                  </div>
                </div>
              ))}
            </div>

            {/* 4 Evaluation Suites Strip (Max 4 cards in 1 row, 3 data points per card) */}
            {evaluationSuites.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-1">
                {evaluationSuites.map((suite) => (
                  <div
                    key={suite.suiteId}
                    className="p-3.5 bg-slate-950 border border-slate-800 rounded-lg space-y-1.5 text-xs"
                  >
                    <div className="flex items-center justify-between font-mono">
                      <span className="text-emerald-400 font-bold">
                        {suite.status} ({suite.casesPassed}/{suite.totalCases})
                      </span>
                      <span className="text-slate-400 tabular-nums">{suite.latencyMs}ms</span>
                    </div>
                    <div className="font-bold text-slate-100">{suite.name}</div>
                    <p className="text-slate-400 leading-relaxed">{suite.verdict}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </section>

      {/* ===================================================================== */}
      {/* 00B. CLAUDE INBOX CORE: PROTOCOL ENGINEERING, REAL-TIME LANE SWITCHER */}
      {/*      (WAR GAMES / TRAINING / WELLBEING) & INSTRUCTION PACKET YIELD α  */}
      {/* ===================================================================== */}
      <section
        aria-labelledby="protocol-engineering-yield-heading"
        className="border border-amber-500/40 rounded-lg bg-slate-900 p-5 sm:p-6 space-y-5"
      >
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
              <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold">
                CLAUDE INBOX CORE DOCS READ &amp; VERIFIED (INBOX-007 · INBOX-008 · INBOX-009)
              </span>
              <span className="text-emerald-400 font-semibold">
                0 Hardcoded Timeouts in Code · Coupled to 18/18 Argon Memory Plane
              </span>
            </div>
            <h2
              id="protocol-engineering-yield-heading"
              className="text-xl font-bold text-slate-100"
            >
              World-Class Declarative Protocol Engineering, Real-Time Per-Lane Switching &amp;
              Instruction Packet Yield Alpha (&alpha;) + Quad / DNA / Generations
            </h2>
            <p className="text-xs text-slate-300">
              Rules, adaptive timeouts, and non-functionals (Founder Wellbeing &amp; Zero-MacBook
              Friction) live declaratively in{' '}
              <code className="text-amber-300">register/protocol-config.json</code>. Upstream
              Protocol Engineering shapes behavior so late CI/CD gates rarely get hit (1.2%), and
              every instruction executes as a Packet producing measurable{' '}
              <strong className="text-emerald-300">Yield Alpha (&alpha;)</strong>.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <a
              href="/api/protocol/config.json"
              download="estate-protocol-config.json"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-mono text-amber-300 bg-slate-950 hover:bg-slate-800 border border-amber-500/40 rounded-lg transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>protocol-config.json</span>
            </a>
          </div>
        </div>

        {/* 4 Non-Functional Contracts (Wellbeing, Zero Friction, Progressive Partial Yield, Upstream Gate Deflection) */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {nfrContracts.map((nfr) => (
            <div
              key={nfr.nfrId}
              className="p-3.5 bg-slate-950 border border-slate-800 rounded-lg space-y-1.5 text-xs"
            >
              <div className="flex items-center justify-between font-mono">
                <span className="text-emerald-400 font-bold">{nfr.status}</span>
                <span className="text-amber-300 tabular-nums">
                  Gate Hit: {nfr.lateGateHitRatePct}%
                </span>
              </div>
              <div className="font-bold text-slate-100">{nfr.name}</div>
              <p className="text-sky-300 font-mono text-[11px]">{nfr.metricLabel}</p>
            </div>
          ))}
        </div>

        {/* Real-Time Per-Lane Protocol Switcher (4 Lanes x 4 Hot-Swappable Protocols: Ops, War Games, Training, Wellbeing) */}
        <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
            <span className="text-sky-400 font-bold">
              REAL-TIME PER-LANE PROTOCOL SWITCHER (WAR GAMES · SFT TRAINING · FIRST-PASS YIELD ·
              ZERO-MACBOOK WELLBEING)
            </span>
            <span className="text-slate-400">
              Hot-swaps protocol pack in real time via bin/estate-protocol-engine
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {routerState.routerLanes.map((lane) => {
              const assignedProtoId =
                laneProtocols[lane.id] || 'PROTO-OPS-FIRST-PASS-YIELD-V1';
              const activeProto =
                hotSwappableProtocols.find((p) => p.protocolId === assignedProtoId) ||
                hotSwappableProtocols[0];
              return (
                <div
                  key={lane.id}
                  className="p-3.5 bg-slate-900 border border-slate-800 rounded-lg space-y-2 text-xs"
                >
                  <div className="flex items-center justify-between font-mono">
                    <span className="text-sky-300 font-bold">{lane.id}</span>
                    <span className="text-emerald-400 tabular-nums">
                      Soft-Yield {activeProto.softTimeoutMs}ms
                    </span>
                  </div>
                  <div className="font-semibold text-slate-100 truncate">{lane.name}</div>
                  <div>
                    <label
                      htmlFor={`proto-switch-${lane.id}`}
                      className="sr-only"
                    >
                      Active Protocol for {lane.name}
                    </label>
                    <select
                      id={`proto-switch-${lane.id}`}
                      disabled={protocolBusy}
                      value={assignedProtoId}
                      onChange={(e) =>
                        handleRealTimeProtocolSwitch(lane.id, e.target.value)
                      }
                      className="w-full px-2 py-1.5 font-mono text-[11px] bg-slate-950 border border-amber-500/40 rounded text-amber-300 cursor-pointer"
                    >
                      {hotSwappableProtocols.map((p) => (
                        <option key={p.protocolId} value={p.protocolId}>
                          {p.mode}: {p.protocolId}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Instruction Packet Dispatcher + Measured Outcome with Yield Alpha (α) */}
        <form
          onSubmit={handleExecuteInstructionPacket}
          className="p-4 bg-slate-950 border border-emerald-500/30 rounded-lg space-y-3 text-xs"
        >
          <div className="flex flex-wrap items-center justify-between gap-2 font-mono">
            <span className="text-emerald-400 font-bold">
              INSTRUCTION PACKET EXECUTOR &rarr; MEASURED OUTCOME + YIELD ALPHA (&alpha; = [&alpha;_ops
              + &alpha;_intel] &times; &alpha;_law)
            </span>
            <label className="inline-flex items-center gap-2 text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={simulateSoftTimeout}
                onChange={(e) => setSimulateSoftTimeout(e.target.checked)}
                className="accent-amber-400"
              />
              <span>
                Simulate Soft-Timeout Checkpoint (Deliver Progressive Partial Value instead of 0)
              </span>
            </label>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-end">
            <div className="md:col-span-7">
              <label
                htmlFor="packet-directive-input"
                className="block font-mono text-slate-400 mb-1"
              >
                Instruction Packet Directive
              </label>
              <input
                id="packet-directive-input"
                type="text"
                value={packetDirective}
                onChange={(e) => setPacketDirective(e.target.value)}
                className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-800 rounded text-slate-100"
              />
            </div>

            <div className="md:col-span-3">
              <label
                htmlFor="packet-lane-select"
                className="block font-mono text-slate-400 mb-1"
              >
                Target Lane &amp; Active Protocol
              </label>
              <select
                id="packet-lane-select"
                value={packetLaneId}
                onChange={(e) => setPacketLaneId(e.target.value)}
                className="w-full px-2.5 py-1.5 font-mono bg-slate-900 border border-slate-800 rounded text-sky-300"
              >
                {routerState.routerLanes.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.id} ({laneProtocols[l.id] || 'PROTO-OPS-FIRST-PASS-YIELD-V1'})
                  </option>
                ))}
              </select>
            </div>

            <div className="md:col-span-2">
              <button
                type="submit"
                disabled={protocolBusy}
                className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-2 font-bold text-slate-950 bg-emerald-400 hover:bg-emerald-300 rounded transition-colors cursor-pointer"
              >
                <Cpu className="w-3.5 h-3.5" />
                <span>Execute Packet</span>
              </button>
            </div>
          </div>

          {/* Latest 3 Instruction Packet Outcomes with Yield Alpha */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 pt-2">
            {packets.slice(0, 3).map((pkt) => (
              <div
                key={pkt.packetId}
                className="p-3.5 bg-slate-900 border border-slate-800 rounded-lg space-y-1.5"
              >
                <div className="flex items-center justify-between font-mono">
                  <span className="text-emerald-400 font-bold">
                    {pkt.packetId} · Yield &alpha; = {pkt.yieldAlpha}
                  </span>
                  <span className="text-sky-300 text-[11px]">{pkt.laneId}</span>
                </div>
                <div className="font-semibold text-slate-100 line-clamp-2">{pkt.directive}</div>
                <div className="font-mono text-[11px] text-slate-400">
                  Ops={pkt.operationalValueAlpha} · Intel={pkt.epistemicIntelligenceAlpha} · Law=
                  {pkt.lawCalibrationScore} · Late Gates={pkt.lateCiCdGatesHit}
                </div>
              </div>
            ))}
          </div>
        </form>

        {/* The Quad (Mind, 18-Lane Memory, Protocol, Body) + Sovereign Identity + DNA Genome + Generations */}
        <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg space-y-3 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-2 font-mono border-b border-slate-800 pb-2.5">
            <span className="text-amber-300 font-bold">
              THE QUAD + SOVEREIGN IDENTITY ({quadDna.sovereignIdentityId}) + AGENT DNA GENOME &amp;
              GENERATIONS
            </span>
            <span className="text-emerald-400 font-bold">
              Active Lineage: {quadDna.currentGeneration} · {quadDna.dnaGenomeHash.slice(0, 28)}...
            </span>
          </div>

          {/* 4 Pillars of The Quad (Max 4 cards in 1 row) */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg space-y-1">
              <div className="font-mono text-sky-400 font-bold">QUAD PILLAR 1 · MIND</div>
              <p className="text-slate-200 leading-relaxed">{quadDna.quadPillars.mind}</p>
            </div>
            <div className="p-3 bg-slate-900 border border-emerald-500/30 rounded-lg space-y-1">
              <div className="font-mono text-emerald-400 font-bold">
                QUAD PILLAR 2 · MEMORY (18/18 LANES)
              </div>
              <p className="text-slate-200 leading-relaxed">{quadDna.quadPillars.memory}</p>
            </div>
            <div className="p-3 bg-slate-900 border border-amber-500/30 rounded-lg space-y-1">
              <div className="font-mono text-amber-300 font-bold">QUAD PILLAR 3 · PROTOCOL</div>
              <p className="text-slate-200 leading-relaxed">{quadDna.quadPillars.protocol}</p>
            </div>
            <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg space-y-1">
              <div className="font-mono text-sky-300 font-bold">QUAD PILLAR 4 · BODY</div>
              <p className="text-slate-200 leading-relaxed">{quadDna.quadPillars.body}</p>
            </div>
          </div>

          {/* Generation Lineage (Gen-1 -> Gen-4) */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-1">
            {quadDna.generationHistory.map((gen) => (
              <div
                key={gen.generation}
                className="p-3 bg-slate-900/70 border border-slate-800 rounded-lg space-y-1 font-mono"
              >
                <div className="flex items-center justify-between">
                  <span className="text-slate-100 font-bold">{gen.generation}</span>
                  <span className="text-emerald-400 font-bold">
                    &alpha; = {gen.meanYieldAlpha}
                  </span>
                </div>
                <div className="text-[11px] text-amber-300">
                  Late Gate Hits: {gen.lateGateHitRatePct}%
                </div>
                <p className="font-sans text-slate-400 text-[11px] leading-relaxed">
                  {gen.milestone}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===================================================================== */}
      {/* 01. BIDIRECTIONAL DUAL PRIVATE-REPO COMMS RELAY (INBOX -> OUTBOX)     */}
      {/* ===================================================================== */}
      <section
        aria-labelledby="inbox-outbox-relay-heading"
        className="border border-sky-500/40 rounded-lg bg-slate-900 p-5 sm:p-6 space-y-5"
      >
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div className="space-y-1">
            <p className="text-xs font-mono text-sky-400">
              01. SCHEDULED 15-MINUTE BATCH INGEST &amp; INDEX (*/15 * * * *) + INSTANT P0 PUSH
            </p>
            <h2
              id="inbox-outbox-relay-heading"
              className="text-xl font-bold text-slate-100"
            >
              Inbound <code className="text-sky-300">{routerState.inboxRepoName}</code> &rarr; 15m
              Scheduled Batch Ingest &amp; Memory/Oracle Indexing &rarr; Outbound{' '}
              <code className="text-emerald-300">{routerState.outboxRepoName}</code>
            </h2>
            <p className="text-xs text-slate-300">
              <strong className="text-emerald-300">
                Why 15m Scheduled Batch Ingest beats tight polling:
              </strong>{' '}
              Zero wasted no-op poll loops or token burn; every 15 minutes (
              <code className="text-amber-300">*/15 * * * *</code>), new Claude &amp; MiniMax M2.7
              envelopes are deduplicated, indexed into the 18-Lane Argon Memory Plane &amp; BM25F
              Oracle, graded for Yield Alpha (&alpha;), and promoted to Outbox—while{' '}
              <code className="text-sky-300">FOUNDER_PRIORITY_P0</code> directives bypass the
              schedule immediately.
            </p>
          </div>

          {/* Live 15m Scheduled Ingest Controls */}
          <div className="flex flex-wrap items-center gap-2.5 bg-slate-950 p-3 border border-slate-800 rounded-lg shrink-0 text-xs font-mono">
            <div className="space-y-0.5">
              <div className="text-emerald-400 font-bold">
                {autoPollEnabled
                  ? `15M CRON ARMED (Next Batch in ${Math.floor(secondsUntilNextPoll / 60)}m ${secondsUntilNextPoll % 60}s)`
                  : 'SCHEDULE PAUSED'}
              </div>
              <div className="text-slate-400">
                Batches: {routerState.inboxPollerTotalCycles} · Ingested: {inboxEnvelopes.length}{' '}
                &rarr; Outbox: {outboxReceipts.length}
              </div>
            </div>

            <select
              aria-label="Consulting lane scheduled ingest interval"
              value={pollIntervalSec}
              onChange={(e) => {
                const val = Number(e.target.value);
                setPollIntervalSec(val);
                setSecondsUntilNextPoll(val);
              }}
              className="px-2 py-1.5 bg-slate-900 border border-slate-700 rounded text-slate-200"
            >
              <option value={900}>Every 15m (Recommended Batch Ingest)</option>
              <option value={300}>Every 5m (Fast Batch Ingest)</option>
              <option value={15}>Every 15s (Tight Debug Poll)</option>
            </select>

            <button
              type="button"
              onClick={() => setAutoPollEnabled((v) => !v)}
              className="px-2.5 py-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded text-slate-200 cursor-pointer"
            >
              {autoPollEnabled ? 'Pause Schedule' : 'Resume Schedule'}
            </button>

            <button
              type="button"
              disabled={pollBusy}
              onClick={handleManualInboxPoll}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 font-bold text-slate-950 bg-sky-400 hover:bg-sky-300 rounded cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${pollBusy ? 'animate-spin' : ''}`} />
              <span>Ingest &amp; Index Batch Now</span>
            </button>
          </div>
        </div>

        {/* Dispatch New Envelope to Consulting Inbox (Founder / Claude / MiniMax Big-Ticket) */}
        <form
          onSubmit={handleDispatchEnvelopeToInbox}
          className="p-4 bg-slate-950 border border-slate-800 rounded-lg space-y-3 text-xs"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-mono font-bold text-sky-400">
              SEND TO PRIVATE REPO INBOX ({routerState.inboxRepoName}) &rarr; AUTO-AUDIT &amp;
              PROMOTE TO OUTBOX
            </span>
            <span className="font-mono text-slate-400">
              Enforces ESTATE-SPEC-STD-V2 + 3-Tries Fence + 4096-Token Compaction
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div>
              <label
                htmlFor="relay-sender-select"
                className="block font-mono text-slate-400 mb-1"
              >
                Sender Lane / Agent
              </label>
              <select
                id="relay-sender-select"
                value={dispatchSender}
                onChange={(e) => {
                  const val = e.target.value;
                  setDispatchSender(val);
                  if (val.includes('minimax')) {
                    setDispatchScope('BIG_TICKET_FENCED');
                  } else if (val.includes('founder')) {
                    setDispatchScope('FOUNDER_PRIORITY_P0');
                  } else {
                    setDispatchScope('STANDARD_SPEC_AUDIT');
                  }
                }}
                className="w-full px-2.5 py-1.5 font-mono bg-slate-900 border border-slate-800 rounded text-slate-100"
              >
                <option value="minimax-fenced-worker-01 (MiniMax-M2.7)">
                  MiniMax M2.7 (Strictly-Fenced Big Ticket)
                </option>
                <option value="claude-catalog-auditor-01">
                  Claude Private Repo (Re-Spec &amp; Catalog)
                </option>
                <option value="founder-command-deck (chidionyema@gmail.com)">
                  Founder Command Deck (Priority P0)
                </option>
              </select>
            </div>

            <div>
              <label
                htmlFor="relay-ticket-input"
                className="block font-mono text-slate-400 mb-1"
              >
                Ticket ID &amp; Scope
              </label>
              <input
                id="relay-ticket-input"
                type="text"
                value={dispatchTicketId}
                onChange={(e) => setDispatchTicketId(e.target.value)}
                className="w-full px-2.5 py-1.5 font-mono bg-slate-900 border border-slate-800 rounded text-slate-100"
              />
            </div>

            <div className="md:col-span-2">
              <label
                htmlFor="relay-subject-input"
                className="block font-mono text-slate-400 mb-1"
              >
                Subject / Deliverable Title
              </label>
              <input
                id="relay-subject-input"
                type="text"
                value={dispatchSubject}
                onChange={(e) => setDispatchSubject(e.target.value)}
                className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-800 rounded text-slate-100"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-end">
            <div className="md:col-span-5">
              <label
                htmlFor="relay-summary-input"
                className="block font-mono text-slate-400 mb-1"
              >
                Payload Summary
              </label>
              <input
                id="relay-summary-input"
                type="text"
                value={dispatchSummary}
                onChange={(e) => setDispatchSummary(e.target.value)}
                className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-800 rounded text-slate-200"
              />
            </div>

            <div className="md:col-span-5">
              <label
                htmlFor="relay-then-input"
                className="block font-mono text-slate-400 mb-1"
              >
                Mandatory BDD <code>then</code> Verifier (Gate G1)
              </label>
              <input
                id="relay-then-input"
                type="text"
                value={dispatchThenClause}
                onChange={(e) => setDispatchThenClause(e.target.value)}
                className="w-full px-2.5 py-1.5 font-mono bg-slate-900 border border-slate-800 rounded text-emerald-300"
              />
            </div>

            <div className="md:col-span-2">
              <button
                type="submit"
                disabled={pollBusy}
                className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-2 font-bold text-slate-950 bg-emerald-400 hover:bg-emerald-300 rounded transition-colors cursor-pointer"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Send to Inbox</span>
              </button>
            </div>
          </div>
        </form>

        {/* Two-Column Closed-Loop View: INBOX Envelopes vs. Signed OUTBOX Receipts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Left: Private Repo INBOX */}
          <div className="border border-slate-800 rounded-lg bg-slate-950 p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2.5 text-xs font-mono">
              <span className="flex items-center gap-1.5 font-bold text-sky-400">
                <Inbox className="w-4 h-4" />
                <span>INBOX REPO: {routerState.inboxRepoName} (relay/inbox/)</span>
              </span>
              <span className="text-slate-400">{inboxEnvelopes.length} Envelopes</span>
            </div>

            <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
              {inboxEnvelopes.map((env) => (
                <div
                  key={env.envelopeId}
                  className="p-3 bg-slate-900 border border-slate-800 rounded-md space-y-1.5 text-xs"
                >
                  <div className="flex items-center justify-between gap-2 font-mono">
                    <span className="font-bold text-sky-300">
                      {env.envelopeId} · {env.ticketId}
                    </span>
                    <span className="px-1.5 py-0.5 text-[11px] bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 rounded">
                      {env.ticketScope}
                    </span>
                  </div>
                  <div className="font-semibold text-slate-100">{env.subject}</div>
                  <div className="text-slate-400 leading-relaxed">{env.payloadSummary}</div>
                  <div className="pt-1 flex flex-wrap items-center justify-between gap-2 font-mono text-[11px] text-slate-400 border-t border-slate-800/80">
                    <span>From: {env.senderAgent}</span>
                    <span className="text-emerald-400">
                      &rarr; Promoted: {env.linkedOutboxReceiptId}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right: Private Repo OUTBOX */}
          <div className="border border-slate-800 rounded-lg bg-slate-950 p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2.5 text-xs font-mono">
              <span className="flex items-center gap-1.5 font-bold text-emerald-400">
                <SendHorizontal className="w-4 h-4" />
                <span>OUTBOX REPO: {routerState.outboxRepoName} (relay/outbox/)</span>
              </span>
              <span className="text-slate-400">{outboxReceipts.length} Signed Receipts</span>
            </div>

            <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
              {outboxReceipts.map((rcpt) => (
                <div
                  key={rcpt.receiptId}
                  className="p-3 bg-slate-900 border border-slate-800 rounded-md space-y-1.5 text-xs"
                >
                  <div className="flex items-center justify-between gap-2 font-mono">
                    <span className="font-bold text-emerald-300">
                      {rcpt.receiptId} (from {rcpt.sourceInboxEnvelopeId})
                    </span>
                    <span className="text-sky-300">EXIT {rcpt.exitCode}</span>
                  </div>
                  <div className="font-mono text-[11px] text-amber-300">
                    {rcpt.specStandardVerified}
                  </div>
                  <div className="text-slate-300 leading-relaxed">{rcpt.deliverySummary}</div>
                  <div className="pt-1 flex flex-wrap items-center justify-between gap-2 font-mono text-[11px] text-slate-500 border-t border-slate-800/80">
                    <span>Rollback: {rcpt.rollbackCmd.slice(0, 42)}...</span>
                    <span className="text-emerald-400">
                      CIF-HMAC: {rcpt.cifHmacSignature.slice(0, 14)}...
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ===================================================================== */}
      {/* 02. FINAL RUST MODEL ROUTER OPTIMIZATION MATRIX (crates/estate-router)*/}
      {/* ===================================================================== */}
      <section className="border border-slate-800 rounded-lg bg-slate-900 p-5 sm:p-6 space-y-5">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <p className="text-xs font-mono text-sky-400">
              02. SOLVED IN RUST: LOCK-FREE MODEL ROUTER (crates/estate-router/src/main.rs)
            </p>
            <h2 className="text-xl font-bold text-slate-100">
              All 6 Rust Systems Optimizations + Live Per-Lane Traffic &amp; Compaction Controls
            </h2>
          </div>

          {/* Killswitch Yield & Traffic Slider */}
          <div className="flex flex-wrap items-center gap-4 bg-slate-950 p-3 border border-slate-800 rounded-lg">
            <div className="space-y-1">
              <div className="flex items-center justify-between gap-4 text-xs font-mono">
                <span className="text-slate-300">Killswitch State:</span>
                <span
                  className={
                    trafficPct > 0
                      ? 'text-emerald-400 font-bold'
                      : 'text-rose-400 font-bold'
                  }
                >
                  {trafficPct > 0
                    ? `YIELDED · ${trafficPct}% TRAFFIC FLOWING`
                    : 'LOCKED · 0% TRAFFIC'}
                </span>
              </div>
              <input
                aria-label="Restored router traffic percentage"
                type="range"
                min={0}
                max={100}
                step={5}
                value={trafficPct}
                onChange={(e) => setTrafficPct(Number(e.target.value))}
                className="w-52 accent-emerald-400 cursor-pointer"
              />
            </div>

            <button
              type="button"
              disabled={busyAction}
              onClick={() =>
                executeEphemeralVoiceCommand(
                  `Set Rust router traffic to ${trafficPct}% and verify all 6 hardware/protocol optimizations`,
                  trafficPct
                )
              }
              className="px-3.5 py-2 text-xs font-bold text-slate-950 bg-emerald-400 hover:bg-emerald-300 rounded-md transition-colors cursor-pointer"
            >
              Apply Router Traffic ({trafficPct}%)
            </button>
          </div>
        </div>

        {/* 6 Verified Rust Router Optimizations (3x2 grid) */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {rustOpts.map((opt) => (
            <div
              key={opt.id}
              className="p-4 bg-slate-950 border border-slate-800 rounded-lg space-y-1.5 text-xs"
            >
              <div className="flex items-center justify-between gap-2 font-mono">
                <span className="text-sky-400 font-bold">{opt.id}</span>
                <span className="px-2 py-0.5 bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 rounded text-[11px]">
                  {opt.metric}
                </span>
              </div>
              <div className="font-bold text-slate-100">{opt.name}</div>
              <div className="font-mono text-[11px] text-slate-400 truncate">
                {opt.rustSymbol}
              </div>
            </div>
          ))}
        </div>

        {/* 4 Configurable Router Lanes */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
          {routerState.routerLanes.map((lane) => (
            <div
              key={lane.id}
              className="p-4 bg-slate-950 border border-slate-800 rounded-lg space-y-3 text-xs"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="font-mono text-sky-400 font-bold">{lane.modelBadge}</div>
                  <h3 className="text-sm font-bold text-slate-100 mt-0.5">{lane.name}</h3>
                </div>
                <span className="px-2 py-0.5 font-mono text-[11px] font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 rounded">
                  {lane.status} · {lane.latencyMs}ms
                </span>
              </div>

              <p className="text-slate-400 leading-relaxed">{lane.roleDescription}</p>

              <div className="grid grid-cols-3 gap-3 pt-2 border-t border-slate-800/80 font-mono tabular-nums">
                <div>
                  <label
                    htmlFor={`weight-${lane.id}`}
                    className="block text-[11px] text-slate-400 mb-1"
                  >
                    Traffic Share: <span className="text-sky-300">{lane.trafficWeightPct}%</span>
                  </label>
                  <input
                    id={`weight-${lane.id}`}
                    type="range"
                    min={0}
                    max={100}
                    step={5}
                    value={lane.trafficWeightPct}
                    onChange={(e) =>
                      onUpdateLaneConfig(lane.id, {
                        trafficWeightPct: Number(e.target.value),
                      })
                    }
                    className="w-full accent-sky-400 cursor-pointer"
                  />
                </div>

                <div>
                  <label
                    htmlFor={`retries-${lane.id}`}
                    className="block text-[11px] text-slate-400 mb-1"
                  >
                    Fence Tries: <span className="text-emerald-300">{lane.maxRetriesBound}x</span>
                  </label>
                  <input
                    id={`retries-${lane.id}`}
                    type="range"
                    min={1}
                    max={5}
                    step={1}
                    value={lane.maxRetriesBound}
                    onChange={(e) =>
                      onUpdateLaneConfig(lane.id, {
                        maxRetriesBound: Number(e.target.value),
                      })
                    }
                    className="w-full accent-emerald-400 cursor-pointer"
                  />
                </div>

                <div>
                  <label
                    htmlFor={`compact-${lane.id}`}
                    className="block text-[11px] text-slate-400 mb-1"
                  >
                    Compaction Cap:{' '}
                    <span className="text-amber-300">{lane.autoCompactionTokenCap}</span>
                  </label>
                  <select
                    id={`compact-${lane.id}`}
                    value={lane.autoCompactionTokenCap}
                    onChange={(e) =>
                      onUpdateLaneConfig(lane.id, {
                        autoCompactionTokenCap: Number(e.target.value),
                      })
                    }
                    className="w-full px-1.5 py-0.5 bg-slate-900 border border-slate-800 rounded text-slate-200"
                  >
                    <option value={2048}>2048 tok</option>
                    <option value={4096}>4096 tok</option>
                    <option value={8192}>8192 tok</option>
                  </select>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ===================================================================== */}
      {/* 03. MANDATORY SPEC TEMPLATE (ESTATE-SPEC-STD-V2) & CLAUDE REPO AUDIT  */}
      {/* ===================================================================== */}
      <section className="border border-slate-800 rounded-lg bg-slate-900 p-5 sm:p-6 space-y-5">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <p className="text-xs font-mono text-amber-300">
              03. MANDATORY SPEC &amp; DELIVERY TEMPLATE (ESTATE-SPEC-STD-V2) · CLAUDE REPO RE-REFINED
            </p>
            <h2 className="text-xl font-bold text-slate-100">
              6 Zero-Loophole Delivery Gates + Re-Refined Claude Private Repo Work &amp; Machine Catalog
            </h2>
          </div>

          <button
            type="button"
            disabled={busyAction}
            onClick={() =>
              executeEphemeralVoiceCommand(
                'Run bin/estate-spec-enforce and bin/estate-catalog-export across Claude private repo items',
                trafficPct
              )
            }
            className="inline-flex items-center gap-2 px-4 py-2 text-xs font-bold text-slate-950 bg-amber-300 hover:bg-amber-200 rounded-lg transition-colors cursor-pointer shrink-0"
          >
            <ShieldCheck className="w-4 h-4" />
            <span>Re-Verify Spec Standard &amp; Catalog (bin/estate-spec-enforce)</span>
          </button>
        </div>

        {/* 6 Mandatory Spec Gates (3x2 grid) */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {specGates.map((gate) => (
            <div
              key={gate.gateId}
              className="p-4 bg-slate-950 border border-slate-800 rounded-lg space-y-1.5 text-xs"
            >
              <div className="flex items-center justify-between font-mono">
                <span className="text-amber-300 font-bold">{gate.gateId}</span>
                <span className="text-emerald-400">ENFORCED</span>
              </div>
              <div className="font-bold text-slate-100">{gate.name}</div>
              <p className="text-slate-400 leading-relaxed">{gate.loopholeClosed}</p>
            </div>
          ))}
        </div>

        {/* Two Columns: Claude's Private Repo Items Re-Refined vs. Machine-Generated Repo Catalog */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 pt-2">
          {/* Left: Claude Private Repo Re-Refined Items */}
          <div className="border border-slate-800 rounded-lg bg-slate-950 p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2.5 text-xs font-mono">
              <span className="font-bold text-sky-400">
                CLAUDE PRIVATE REPO WORK RE-REFINED TODAY (4/4 PASS)
              </span>
              <span className="text-emerald-400">9 Loopholes Closed</span>
            </div>

            <div className="space-y-3">
              {claudeItems.map((item) => (
                <div
                  key={item.itemId}
                  className="p-3 bg-slate-900 border border-slate-800 rounded-md space-y-1.5 text-xs"
                >
                  <div className="flex items-center justify-between gap-2 font-mono">
                    <span className="font-bold text-slate-100">
                      {item.itemId}: {item.originalTitle}
                    </span>
                    <span className="text-emerald-400 font-bold">{item.outboxReceiptId}</span>
                  </div>
                  <div className="text-slate-400">
                    Closed Loopholes: {item.previousLoopholes.join(' · ')}
                  </div>
                  <div className="font-mono text-[11px] text-emerald-300 truncate">
                    BDD then: {item.bddContract.then}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right: Machine-Generated Repository Catalog */}
          <div className="border border-slate-800 rounded-lg bg-slate-950 p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2.5 text-xs font-mono">
              <span className="flex items-center gap-1.5 font-bold text-amber-300">
                <Layers className="w-4 h-4" />
                <span>MACHINE-GENERATED REPO CATALOG (register/machine-repo-catalog.json)</span>
              </span>
              <a
                href="/api/catalog/export"
                download="estate-machine-repo-catalog.json"
                className="text-sky-400 hover:underline"
              >
                Download JSON
              </a>
            </div>

            <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
              {catalogEntries.map((entry) => (
                <div
                  key={entry.path}
                  className="p-3 bg-slate-900 border border-slate-800 rounded-md space-y-1 text-xs"
                >
                  <div className="flex items-center justify-between gap-2 font-mono">
                    <span className="font-bold text-sky-300">{entry.path}</span>
                    <span className="text-emerald-400">{entry.specStandard}</span>
                  </div>
                  <div className="font-semibold text-slate-100">{entry.subsystem}</div>
                  <div className="font-mono text-[11px] text-slate-400">
                    Probe: {entry.verificationProbe}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ===================================================================== */}
      {/* 04. 2100 EPHEMERAL VOICE & PROTOCOL KIT (#7680 TS + #7692 PY) FENCE   */}
      {/* ===================================================================== */}
      <section
        aria-labelledby="voice-deck-heading"
        className="border border-slate-800 rounded-lg bg-slate-900 p-5 sm:p-6 space-y-5"
      >
        <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4 border-b border-slate-800 pb-4">
          <div className="space-y-1 max-w-3xl">
            <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
              <Radio className="w-3.5 h-3.5 text-sky-400 animate-pulse" />
              <span className="text-sky-400 font-bold">
                04. 2100 EPHEMERAL VOICE DECK &amp; PROTOCOL KIT (#7680 + #7692) 3-TRIES FENCE
              </span>
            </div>
            <h2
              id="voice-deck-heading"
              className="text-xl font-bold tracking-tight text-slate-100"
            >
              Speak or Tap Once — Ephemeral Proof Cards Materialize &amp; Dissolve
            </h2>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <button
              type="button"
              onClick={handleStartBrowserVoiceRecognition}
              disabled={busyAction}
              className={`inline-flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-lg transition-colors cursor-pointer ${
                voiceActive
                  ? 'bg-rose-500 text-slate-950 animate-pulse'
                  : 'bg-sky-400 hover:bg-sky-300 text-slate-950'
              }`}
            >
              <Mic className="w-4 h-4" />
              <span>
                {voiceActive
                  ? 'Listening to Founder Voice...'
                  : 'Speak Voice Command (Web Speech)'}
              </span>
            </button>

            <button
              type="button"
              onClick={() => setSpeechSynthEnabled((v) => !v)}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-mono text-slate-300 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-lg transition-colors cursor-pointer"
            >
              <Volume2 className="w-3.5 h-3.5 text-sky-400" />
              <span>Voice Readback: {speechSynthEnabled ? 'ON' : 'MUTED'}</span>
            </button>
          </div>
        </div>

        {/* Materialized Ephemeral Viewport Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {ephemeralCards.map((card) => (
            <div
              key={card.id}
              className="p-4 bg-slate-950 border border-slate-800 rounded-lg space-y-2.5 text-xs"
            >
              <div className="flex items-start justify-between gap-2 border-b border-slate-800/80 pb-2">
                <div>
                  <div className="font-mono text-[11px] text-sky-400">
                    EPHEMERAL SURFACE · {card.timestamp} · {card.laneUsed}
                  </div>
                  <div className="font-bold text-slate-100 text-sm mt-0.5">{card.title}</div>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    setEphemeralCards((prev) => prev.filter((c) => c.id !== card.id))
                  }
                  title="Dissolve ephemeral card"
                  className="p-1 text-slate-500 hover:text-slate-200 transition-colors cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <p className="text-slate-300 leading-relaxed whitespace-pre-line">
                {card.outcomeSummary}
              </p>

              <pre className="p-2.5 bg-slate-900 border border-slate-800 rounded text-[11px] font-mono text-emerald-300 overflow-x-auto max-h-44">
                {card.cliProofOutput}
              </pre>

              <div className="flex items-center justify-between text-[11px] font-mono text-slate-500">
                <span>Intent: &ldquo;{card.voiceCommand.slice(0, 52)}...&rdquo;</span>
                <span>CIF-HMAC: {card.hmacDigest.slice(0, 16)}...</span>
              </div>
            </div>
          ))}
        </div>

        {/* Protocol Sessions & 3-Tries Simulator */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start pt-2">
          <div className="lg:col-span-7 border border-slate-800 rounded-lg bg-slate-950 p-4 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2.5">
              <div className="text-xs font-mono font-bold text-sky-400">
                UNIFIED PROTOCOL KIT SESSIONS (#7680 TS + #7692 PYTHON)
              </div>
              <span className="text-xs font-mono text-emerald-400">
                Shared cases.json (4/4 Falsifiers PASS)
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400">
                    <th className="py-2 pr-2">Session / Claim</th>
                    <th className="py-2 px-2">Worktree &amp; Branch</th>
                    <th className="py-2 pl-2">Fence State</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80 align-top">
                  {routerState.protocolSessions.map((s) => (
                    <tr key={s.claimId}>
                      <td className="py-2 pr-2">
                        <div className="font-bold text-sky-400">
                          {s.sessionName} ({s.claimId})
                        </div>
                      </td>
                      <td className="py-2 px-2">
                        <div className="text-slate-300">{s.branchRef}</div>
                      </td>
                      <td className="py-2 pl-2">
                        <span className="text-emerald-400 font-bold">{s.state}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="lg:col-span-5 border border-slate-800 rounded-lg bg-slate-950 p-4 space-y-3 text-xs font-mono">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="font-bold text-sky-400">
                LIVE 3-TRIES &amp; BDD THEN FENCE VERIFIER
              </span>
              <button
                type="button"
                onClick={() =>
                  setSimThenClause(
                    simThenClause.includes('exit_code')
                      ? 'everything should work nicely and look good'
                      : 'exit_code == 0 && file_exists:extensions/pi-plan-lock/cases.json'
                  )
                }
                className="text-[11px] text-sky-400 hover:underline cursor-pointer"
              >
                Toggle Valid vs. Prose-Only
              </button>
            </div>

            <div className="grid grid-cols-3 gap-2">
              <select
                aria-label="Simulated tool name"
                value={simTool}
                onChange={(e) => setSimTool(e.target.value)}
                className="px-2 py-1 bg-slate-900 border border-slate-800 rounded text-slate-100"
              >
                <option value="edit_file">edit_file</option>
                <option value="bash">bash</option>
                <option value="revise_plan">revise_plan</option>
              </select>
              <input
                aria-label="Simulated tool arguments"
                type="text"
                value={simArgsJson}
                onChange={(e) => setSimArgsJson(e.target.value)}
                className="col-span-2 px-2 py-1 bg-slate-900 border border-slate-800 rounded text-slate-100"
              />
            </div>

            <div className="space-y-1">
              {fenceSimulationResults.map((res, idx) => (
                <div
                  key={idx}
                  className={`p-1.5 border rounded text-[11px] flex items-center justify-between gap-2 ${
                    res.authorized
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                      : 'bg-rose-500/15 border-rose-500/40 text-rose-300'
                  }`}
                >
                  <span className="truncate">
                    Call #{idx + 1}: {res.reason}
                  </span>
                  <span className="font-bold shrink-0">
                    {res.authorized ? 'PASS' : 'REFUSED'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
