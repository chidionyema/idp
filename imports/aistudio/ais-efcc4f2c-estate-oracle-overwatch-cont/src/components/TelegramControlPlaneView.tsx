import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Play,
  Pause,
  RotateCcw,
  FileCode2,
  Plus,
  Send,
  Zap,
  RefreshCw,
} from 'lucide-react';
import {
  computeCifHmac,
  verifyCifReceipt,
  type CifStepReceipt,
  type TelegramForumTopic,
  type AgentLaneStatus,
} from '../engine/oracleEngine';

interface TelegramControlPlaneViewProps {
  topics: TelegramForumTopic[];
  receipts: CifStepReceipt[];
  selectedTopicId: string;
  onSelectTopic: (topicId: string) => void;
  onUpdateTopicStatus: (topicId: string, status: AgentLaneStatus) => void;
  onCreateForumTopic: (name: string, ticketId: string) => void;
  onAppendReceipt: (receipt: CifStepReceipt) => void;
  onLaunchTmaHud: () => void;
}

const STATUS_META: Record<
  AgentLaneStatus,
  { emoji: string; label: string; textClass: string }
> = {
  running: {
    emoji: '🟢',
    label: 'Running',
    textClass: 'text-emerald-400',
  },
  inferencing: {
    emoji: '🧠',
    label: 'MiniMax Inferencing',
    textClass: 'text-sky-400',
  },
  verified: {
    emoji: '🛡️',
    label: 'CIF Signature Verified',
    textClass: 'text-indigo-300',
  },
  halted: {
    emoji: '🔴',
    label: 'Halted / Paused',
    textClass: 'text-rose-400',
  },
};

export const TelegramControlPlaneView: React.FC<TelegramControlPlaneViewProps> = ({
  topics,
  receipts,
  selectedTopicId,
  onSelectTopic,
  onUpdateTopicStatus,
  onCreateForumTopic,
  onAppendReceipt,
  onLaunchTmaHud,
}) => {
  const [editTickCount, setEditTickCount] = useState<number>(1428);
  const [expandedStdoutIds, setExpandedStdoutIds] = useState<Record<number, boolean>>({});
  const [expandedDiffIds, setExpandedDiffIds] = useState<Record<number, boolean>>({});
  const [newTopicTicket, setNewTopicTicket] = useState('');
  const [showNewTopicInput, setShowNewTopicInput] = useState(false);
  const [commandInput, setCommandInput] = useState('');
  const [hapticNotice, setHapticNotice] = useState<string>(
    'teloxide + axum + sqlx daemon connected to ~/.estate/estate.db'
  );

  // Simulate the 3-second editMessageText in-place pinned telemetry update
  useEffect(() => {
    const timer = setInterval(() => {
      setEditTickCount((c) => c + 1);
    }, 3000);
    return () => clearInterval(timer);
  }, []);

  const visibleReceipts =
    selectedTopicId === '00-overwatch'
      ? receipts
      : receipts.filter((r) => r.laneId === selectedTopicId);

  const activeTopic = topics.find((t) => t.id === selectedTopicId) || null;

  const totalTokensSec = topics.reduce(
    (sum, t) => sum + (t.status === 'halted' ? 0 : t.tokensPerSec),
    0
  );
  const totalWriteOps = topics.reduce(
    (sum, t) => sum + (t.status === 'halted' ? 0 : t.sqliteWriteOpsSec),
    0
  );
  const activeLanesCount = topics.filter((t) => t.status !== 'halted').length;

  const toggleStdout = (id: number) => {
    setExpandedStdoutIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const toggleDiff = (id: number) => {
    setExpandedDiffIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleTogglePauseLane = (laneId: string) => {
    const topic = topics.find((t) => t.id === laneId);
    if (!topic) return;
    const nextStatus: AgentLaneStatus =
      topic.status === 'halted' ? 'running' : 'halted';
    onUpdateTopicStatus(laneId, nextStatus);
    setHapticNotice(
      `editForumTopic("${topic.name}") -> ${STATUS_META[nextStatus].emoji} ${STATUS_META[nextStatus].label}`
    );
  };

  const handleKillAndRequeue = (receipt: CifStepReceipt) => {
    onUpdateTopicStatus(receipt.laneId, 'inferencing');
    const nextId = receipts.length > 0 ? Math.max(...receipts.map((r) => r.id)) + 1 : 200;
    const nextStep = receipt.stepIdx + 1;
    const cmd = `estate-execute --requeue --ticket ${receipt.ticketId} --step ${nextStep} --verify-cif`;
    const stdoutPayload = [
      `[REQUEUE] Killed stale worker on lane #${receipt.laneId}; respawned clean sandbox`,
      `[MINIMAX-M2.7] Re-executing step ${nextStep} for ticket ${receipt.ticketId}`,
      `[CIF-LEDGER] Captured deterministic stdout_payload & committed WAL frame #${nextId}`,
      `[VERIFY] Exit code 0 · HMAC-SHA256 signature verified against estate.db`,
    ].join('\n');

    const hmacSignature = computeCifHmac(receipt.ticketId, nextStep, cmd, stdoutPayload, 0);
    const newReceipt: CifStepReceipt = {
      id: nextId,
      ticketId: receipt.ticketId,
      stepIdx: nextStep,
      laneId: receipt.laneId,
      cmd,
      stdoutPayload,
      stderrPayload: '',
      exitCode: 0,
      hmacSignature,
      timestamp: new Date().toISOString(),
      diffSummary: `${receipt.ticketId} requeued step #${nextStep} (+18 -2 lines verified)`,
      diffPatch: `--- a/estate-ledger/${receipt.ticketId}.step\n+++ b/estate-ledger/${receipt.ticketId}.step\n@@ -1,2 +1,4 @@\n-status = "requeued"\n+status = "verified_live_cif"\n+step_idx = ${nextStep}\n+hmac = "${hmacSignature.slice(0, 24)}..."`,
      verified: true,
    };

    onAppendReceipt(newReceipt);
    setHapticNotice(
      `HapticFeedback.impactOccurred('heavy') · Requeued ${receipt.ticketId} step #${nextStep} with new CIF receipt`
    );
  };

  const handleSpawnTopic = (e: React.FormEvent) => {
    e.preventDefault();
    const cleaned = newTopicTicket.trim();
    if (!cleaned) return;
    const laneSlug = `pi-lane-0${topics.length}`;
    onCreateForumTopic(laneSlug, cleaned.toUpperCase());
    setNewTopicTicket('');
    setShowNewTopicInput(false);
    setHapticNotice(`createForumTopic("#${laneSlug}") bound to ticket ${cleaned.toUpperCase()}`);
  };

  const handleDispatchCommand = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = commandInput.trim();
    if (!trimmed) return;

    const targetLane =
      selectedTopicId === '00-overwatch' ? 'otto-front-door' : selectedTopicId;
    const topic = topics.find((t) => t.id === targetLane);
    const ticketId = topic?.ticketId || 'TICKET-OVERWATCH-CMD';
    const nextId = receipts.length > 0 ? Math.max(...receipts.map((r) => r.id)) + 1 : 201;
    const stepIdx = receipts.filter((r) => r.laneId === targetLane).length + 1;
    const fullCmd = trimmed.startsWith('estate-execute')
      ? trimmed
      : `estate-execute --ticket ${ticketId} --step ${stepIdx} -- ${trimmed}`;

    const stdoutPayload = [
      `[OTTO-FRONT-DOOR] Intercepted command on #${targetLane} -> routed through CIF kernel`,
      `[EXEC] ${fullCmd}`,
      `[ORACLE-INDEX] Cross-checked estate-graph in 1.6ms · 0 unverified assumptions`,
      `[CIF-RECEIPT] Step #${stepIdx} committed to ~/.estate/estate.db with exit_code=0`,
    ].join('\n');

    const hmacSignature = computeCifHmac(ticketId, stepIdx, fullCmd, stdoutPayload, 0);

    onAppendReceipt({
      id: nextId,
      ticketId,
      stepIdx,
      laneId: targetLane,
      cmd: fullCmd,
      stdoutPayload,
      stderrPayload: '',
      exitCode: 0,
      hmacSignature,
      timestamp: new Date().toISOString(),
      diffSummary: `estate.db step_runs +1 row (id=${nextId})`,
      diffPatch: `--- a/estate.db/step_runs\n+++ b/estate.db/step_runs\n@@ +1 @@\n+INSERT INTO step_runs VALUES (${nextId}, '${ticketId}', ${stepIdx}, '${fullCmd}', 0, '${hmacSignature.slice(0, 16)}...');`,
      verified: true,
    });

    onUpdateTopicStatus(targetLane, 'verified');
    setCommandInput('');
    setHapticNotice(
      `Signed CIF receipt #${nextId} posted to #${targetLane} (HMAC ${hmacSignature.slice(0, 8)}...)`
    );
  };

  return (
    <div className="space-y-6">
      {/* Header row */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="space-y-1.5 max-w-3xl">
          <p className="text-xs font-mono text-sky-400">
            01. Telegram Supergroup Topic Architecture & Cryptographic Receipt Cards
          </p>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-100">
            Fleet Overwatch Control Plane (teloxide + axum + sqlx)
          </h1>
          <p className="text-sm text-slate-400">
            Replaces noisy flat webhook logs with isolated Supergroup Forum Topics, a 3-second
            in-place edited pinned telemetry HUD, collapsible CIF stdout blockquotes, and HMAC-SHA256
            receipt cards.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            type="button"
            onClick={onLaunchTmaHud}
            className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-sky-300 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg transition-colors whitespace-nowrap shrink-0"
          >
            <Zap className="w-3.5 h-3.5 text-sky-400" />
            <span>Open 60fps TMA Viewport</span>
          </button>
        </div>
      </div>

      {/* Main 2-column Supergroup Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Sidebar: Supergroup Forum Topics */}
        <aside
          aria-label="Telegram Supergroup Forum Topics"
          className="lg:col-span-4 border border-slate-800 rounded-lg bg-slate-900 overflow-hidden"
        >
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-slate-100">
                ESTATE-OVERWATCH [Supergroup]
              </h2>
              <p className="text-xs text-slate-400 font-mono tabular-nums mt-0.5">
                Forum Topics Enabled · {topics.length + 1} Active Threads
              </p>
            </div>
            <button
              type="button"
              onClick={() => setShowNewTopicInput((v) => !v)}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 rounded transition-colors whitespace-nowrap shrink-0"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>New Lane</span>
            </button>
          </div>

          {showNewTopicInput && (
            <form
              onSubmit={handleSpawnTopic}
              className="p-3 bg-slate-950 border-b border-slate-800 space-y-2"
            >
              <label
                htmlFor="new-topic-ticket-id"
                className="block text-xs font-medium text-slate-300"
              >
                createForumTopic Ticket ID
              </label>
              <div className="flex gap-2">
                <input
                  id="new-topic-ticket-id"
                  type="text"
                  value={newTopicTicket}
                  onChange={(e) => setNewTopicTicket(e.target.value)}
                  placeholder="e.g. CLAIM-OIA-920"
                  className="flex-1 px-2.5 py-1.5 text-xs font-mono bg-slate-900 border border-slate-800 rounded text-slate-100 focus:outline-none focus:border-sky-500"
                />
                <button
                  type="submit"
                  className="px-3 py-1.5 text-xs font-medium bg-sky-400 text-slate-950 rounded hover:bg-sky-300 whitespace-nowrap shrink-0"
                >
                  Create
                </button>
              </div>
            </form>
          )}

          <div className="divide-y divide-slate-800/80">
            {/* Pinned Master Topic #00-OVERWATCH */}
            <button
              type="button"
              onClick={() => onSelectTopic('00-overwatch')}
              className={`w-full text-left p-3.5 transition-colors block ${
                selectedTopicId === '00-overwatch'
                  ? 'bg-slate-800/90'
                  : 'hover:bg-slate-800/40'
              }`}
            >
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="font-semibold text-sky-400">
                  📌 #00-OVERWATCH (Pinned HUD)
                </span>
                <span className="text-slate-400 tabular-nums">3s In-Place Edit</span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Master ASCII/Unicode telemetry matrix + all fleet CIF receipt streams
              </p>
            </button>

            {/* Dynamic Agent Lane Topics */}
            {topics.map((topic) => {
              const meta = STATUS_META[topic.status];
              const isSelected = selectedTopicId === topic.id;
              return (
                <div
                  key={topic.id}
                  className={`p-3.5 transition-colors ${
                    isSelected ? 'bg-slate-800/90' : 'hover:bg-slate-800/40'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <button
                      type="button"
                      onClick={() => onSelectTopic(topic.id)}
                      className="text-left flex-1 min-w-0"
                    >
                      <div className="flex items-center gap-1.5 text-xs font-mono">
                        <span aria-hidden="true">{meta.emoji}</span>
                        <span className="font-semibold text-slate-100 truncate">
                          {topic.name}
                        </span>
                        <span className="text-slate-500">·</span>
                        <span className="text-slate-400 truncate">{topic.ticketId}</span>
                      </div>
                      <p className="text-xs text-slate-400 truncate mt-1">
                        {topic.description}
                      </p>
                    </button>

                    {/* Quick Status Cycle Button (editForumTopic simulator) */}
                    <button
                      type="button"
                      onClick={() => handleTogglePauseLane(topic.id)}
                      aria-label={
                        topic.status === 'halted'
                          ? `Resume ${topic.name}`
                          : `Pause ${topic.name}`
                      }
                      className="px-2 py-1 text-xs font-mono text-slate-300 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded whitespace-nowrap shrink-0"
                    >
                      {topic.status === 'halted' ? 'Resume' : 'Pause'}
                    </button>
                  </div>

                  <div className="flex items-center justify-between text-xs font-mono text-slate-500 tabular-nums mt-2 pt-2 border-t border-slate-800/60">
                    <span className={meta.textClass}>{meta.label}</span>
                    <span>
                      {topic.status === 'halted' ? '0.0' : topic.tokensPerSec.toFixed(1)} tok/s · PID{' '}
                      {topic.pid}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </aside>

        {/* Right Main Column: Pinned #00-OVERWATCH Matrix + CIF Receipt Cards */}
        <div className="lg:col-span-8 space-y-5">
          {/* Pinned Live-Edited Telemetry Matrix */}
          <div className="border border-slate-800 rounded-lg bg-slate-900 p-4 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 text-xs font-mono text-slate-300">
                <span className="text-sky-400 font-semibold">
                  PINNED #00-OVERWATCH TELEMETRY MATRIX
                </span>
                <span aria-hidden="true">·</span>
                <span className="text-slate-400 tabular-nums">
                  editMessageText_id: #884120 (Tick #{editTickCount})
                </span>
              </div>
              <button
                type="button"
                onClick={() => setEditTickCount((c) => c + 1)}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono text-slate-300 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded transition-colors whitespace-nowrap shrink-0"
              >
                <RefreshCw className="w-3 h-3 text-sky-400" />
                <span>Force 3s Tick</span>
              </button>
            </div>

            <pre className="p-3.5 bg-slate-950 border border-slate-800 rounded-md text-xs font-mono text-slate-200 overflow-x-auto leading-relaxed tabular-nums">
{[
  '==============================================================================',
  ' ESTATE OVERWATCH SPINE  |  ORACLE FREE TIER K3S (ARM64)  |  RUST STATIC 14.8M',
  '------------------------------------------------------------------------------',
  ` ACTIVE PI FLEET         : ${activeLanesCount}/${topics.length} Lanes Nominal (MacBook M3 Max Protected)`,
  ` MINIMAX M2.7 VELOCITY   : ${totalTokensSec.toFixed(1)} tok/s (Direct Plan Quota · Router Bypassed)`,
  ` ESTATE.DB WAL THROUGHPUT: ${totalWriteOps.toFixed(1)} tx/s  (100% CIF HMAC-SHA256 Verified)`,
  ' K3S MEMORY PRESSURE     : 18.2 MB / 20.0 MB Cap (teloxide + axum + sqlx)',
  '==============================================================================',
].join('\n')}
            </pre>

            <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono text-slate-400 tabular-nums">
              <span>Last Daemon Event: {hapticNotice}</span>
              <span>Zero Scroll · In-Place Mutated</span>
            </div>
          </div>

          {/* Active Topic Header & Receipt Stream */}
          <div className="border border-slate-800 rounded-lg bg-slate-900/60 divide-y divide-slate-800">
            <div className="p-4 flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-sm font-bold text-slate-100 font-mono">
                  {activeTopic
                    ? `${STATUS_META[activeTopic.status].emoji} ${activeTopic.name} · Ticket ${activeTopic.ticketId}`
                    : '📌 All Supergroup CIF Step Receipts (#00-OVERWATCH Feed)'}
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  {activeTopic
                    ? activeTopic.description
                    : 'Showing cryptographically signed estate-execute step cards across all active lanes.'}
                </p>
              </div>
              <span className="text-xs font-mono text-slate-400 tabular-nums">
                {visibleReceipts.length} Verified Receipt Cards
              </span>
            </div>

            {/* Cryptographic Receipt Cards */}
            <div className="divide-y divide-slate-800">
              {visibleReceipts.map((receipt) => {
                const isVerified = verifyCifReceipt(receipt);
                const isStdoutOpen = !!expandedStdoutIds[receipt.id];
                const isDiffOpen = !!expandedDiffIds[receipt.id];
                const stdoutLines = receipt.stdoutPayload.split('\n');
                const previewLines = stdoutLines.slice(0, 2).join('\n');
                const topicObj = topics.find((t) => t.id === receipt.laneId);
                const isLaneHalted = topicObj?.status === 'halted';

                return (
                  <article key={receipt.id} className="p-4 space-y-3">
                    {/* Receipt Top Metadata Line (Clean unboxed text with separators) */}
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono tabular-nums">
                      <div className="flex flex-wrap items-center gap-1.5 text-slate-300">
                        <span className="text-sky-400 font-semibold">
                          #{receipt.laneId}
                        </span>
                        <span aria-hidden="true">·</span>
                        <span>
                          {receipt.ticketId}:{receipt.stepIdx}
                        </span>
                        <span aria-hidden="true">·</span>
                        <span className="text-slate-400">Receipt #{receipt.id}</span>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                        <span className="text-emerald-400 font-medium">
                          CIF-HMAC: {receipt.hmacSignature.slice(0, 8)}...
                          {receipt.hmacSignature.slice(-4)}
                        </span>
                        <span aria-hidden="true" className="text-slate-500">
                          |
                        </span>
                        <span className="text-slate-300">Exit: {receipt.exitCode}</span>
                        <span aria-hidden="true" className="text-slate-500">
                          |
                        </span>
                        <span className="text-slate-400">
                          {isVerified ? 'Signature Valid' : 'Falsified'}
                        </span>
                      </div>
                    </div>

                    {/* Executed Command */}
                    <div className="px-3 py-2 bg-slate-950 border border-slate-800 rounded font-mono text-xs text-slate-200 overflow-x-auto">
                      $ {receipt.cmd}
                    </div>

                    {/* Collapsible Stdout (<blockquote expandable> pattern) */}
                    <div className="border border-slate-800 rounded-md bg-slate-950/80 overflow-hidden">
                      <div className="px-3 py-2 flex items-center justify-between border-b border-slate-800/80 text-xs font-mono text-slate-400">
                        <span>
                          stdout_payload ({stdoutLines.length} lines captured in estate.db)
                        </span>
                        <button
                          type="button"
                          onClick={() => toggleStdout(receipt.id)}
                          className="inline-flex items-center gap-1 text-sky-400 hover:text-sky-300 whitespace-nowrap shrink-0"
                        >
                          <span>
                            {isStdoutOpen
                              ? 'Collapse Blockquote'
                              : `Expand Full Output (${stdoutLines.length} lines)`}
                          </span>
                          {isStdoutOpen ? (
                            <ChevronUp className="w-3.5 h-3.5" />
                          ) : (
                            <ChevronDown className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                      <pre className="p-3 text-xs font-mono text-slate-300 overflow-x-auto whitespace-pre-wrap leading-relaxed">
                        {isStdoutOpen
                          ? receipt.stdoutPayload
                          : `${previewLines}\n... [Expandable Telegram Blockquote: ${Math.max(
                              0,
                              stdoutLines.length - 2
                            )} more lines folded]`}
                      </pre>
                    </div>

                    {/* Optional Diff View when [ Inspect Diff ] is toggled */}
                    {isDiffOpen && (
                      <div className="p-3 bg-slate-950 border border-slate-800 rounded-md space-y-1.5">
                        <div className="text-xs font-mono text-sky-400">
                          Diff Summary: {receipt.diffSummary}
                        </div>
                        <pre className="text-xs font-mono text-slate-300 overflow-x-auto whitespace-pre-wrap">
                          {receipt.diffPatch}
                        </pre>
                      </div>
                    )}

                    {/* InlineKeyboardMarkup Hardware Controls */}
                    <div
                      className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1"
                      role="group"
                      aria-label={`Inline hardware controls for receipt ${receipt.id}`}
                    >
                      <button
                        type="button"
                        onClick={() => toggleDiff(receipt.id)}
                        className="inline-flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-mono font-medium bg-slate-950 hover:bg-slate-800 text-slate-200 border border-slate-800 rounded transition-colors whitespace-nowrap shrink-0"
                      >
                        <FileCode2 className="w-3.5 h-3.5 text-sky-400" />
                        <span>{isDiffOpen ? 'Hide Diff' : 'Inspect Diff'}</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => handleTogglePauseLane(receipt.laneId)}
                        className="inline-flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-mono font-medium bg-slate-950 hover:bg-slate-800 text-slate-200 border border-slate-800 rounded transition-colors whitespace-nowrap shrink-0"
                      >
                        {isLaneHalted ? (
                          <>
                            <Play className="w-3.5 h-3.5 text-emerald-400" />
                            <span>Resume Lane</span>
                          </>
                        ) : (
                          <>
                            <Pause className="w-3.5 h-3.5 text-amber-400" />
                            <span>Pause Lane</span>
                          </>
                        )}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleKillAndRequeue(receipt)}
                        className="inline-flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-mono font-medium bg-slate-950 hover:bg-rose-950/60 text-rose-300 border border-slate-800 hover:border-rose-500/40 rounded transition-colors whitespace-nowrap shrink-0"
                      >
                        <RotateCcw className="w-3.5 h-3.5 text-rose-400" />
                        <span>Kill & Requeue</span>
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>

            {/* Interactive Telegram Thread Dispatcher */}
            <form
              onSubmit={handleDispatchCommand}
              className="p-4 bg-slate-950 flex flex-col sm:flex-row gap-2"
            >
              <label htmlFor="telegram-dispatch-input" className="sr-only">
                Dispatch estate-execute command or Otto instruction to active topic
              </label>
              <input
                id="telegram-dispatch-input"
                type="text"
                value={commandInput}
                onChange={(e) => setCommandInput(e.target.value)}
                placeholder={`Dispatch verified step to #${
                  selectedTopicId === '00-overwatch' ? 'otto-front-door' : selectedTopicId
                } (e.g. cargo test --workspace)...`}
                className="flex-1 px-3.5 py-2 text-xs font-mono bg-slate-900 border border-slate-800 rounded-md text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-sky-500"
              />
              <button
                type="submit"
                className="inline-flex items-center justify-center gap-1.5 px-4 py-2 text-xs font-medium bg-sky-400 hover:bg-sky-300 text-slate-950 rounded-md transition-colors whitespace-nowrap shrink-0"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Execute & Sign CIF Receipt</span>
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};
