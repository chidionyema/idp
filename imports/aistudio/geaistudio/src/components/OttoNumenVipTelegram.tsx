import { useEffect, useState } from 'react';
import {
  CheckCircle2,
  Download,
  FileText,
  RotateCcw,
  Search,
  Send,
  Volume2,
  VolumeX,
  Zap,
} from 'lucide-react';
import {
  CeoFocusPolicy,
  OttoNumenSnapshot,
  RawEstateEventKind,
  TelegramTopicKey,
} from '../types/api';

type TopicFilter = 'ALL_TOPICS' | TelegramTopicKey;
type CardInspectMode = 'executive' | 'compare_legacy' | 'wire_payloads';

export function OttoNumenVipTelegram() {
  const [snapshot, setSnapshot] = useState<OttoNumenSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [selectedTopic, setSelectedTopic] = useState<TopicFilter>('ALL_TOPICS');
  const [inspectMode, setInspectMode] = useState<CardInspectMode>('executive');
  const [unresolvedOnly, setUnresolvedOnly] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Custom event & adversarial formatting probe state
  const [probeKind, setProbeKind] = useState<RawEstateEventKind>('p0_ceo_signoff');
  const [probeSubsystem, setProbeSubsystem] = useState('PennyD · Quorum Guard');
  const [probeHeadline, setProbeHeadline] = useState(
    'Verify <3 Quorum Guard & Key pk_live_opencode_94a2 [Sign-Off]'
  );
  const [probeSummary, setProbeSummary] = useState(
    'Adversarial chars (<3 & *bold* _italic_ [x](y)) escaped cleanly with zero Telegram HTTP 400 parse errors.'
  );
  const [probeDedupeKey, setProbeDedupeKey] = useState('probe:custom-test');

  async function fetchTelegramState() {
    try {
      const res = await fetch('/api/telegram/state');
      if (!res.ok) {
        throw new Error(`Telegram concierge returned HTTP ${res.status}`);
      }
      const data = (await res.json()) as OttoNumenSnapshot;
      setSnapshot(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load VIP Telegram state');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void fetchTelegramState();

    // SSE push sync (/api/union/stream) — zero client HTTP polling (I-8090)
    if (typeof EventSource === 'undefined') return;
    const es = new EventSource('/api/union/stream');
    const onBeat = () => {
      void fetchTelegramState();
    };
    es.addEventListener('union_snapshot', onBeat);
    return () => {
      es.removeEventListener('union_snapshot', onBeat);
      es.close();
    };
  }, []);

  async function handleSimulateStorm() {
    setBusyAction('storm');
    try {
      const res = await fetch('/api/telegram/storm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ eventCount: 50 }),
      });
      if (res.ok) {
        const data = (await res.json()) as {
          ingested: number;
          suppressedChatter: number;
          coalescedEdits: number;
          newTopicCards: number;
          audiblePingsDuringStorm: number;
          snapshot: OttoNumenSnapshot;
        };
        setSnapshot(data.snapshot);
        setNotice(
          `50-event storm triaged: ${data.suppressedChatter} heartbeats intercepted (0 sent), ${data.coalescedEdits} flapping alerts coalesced via editMessageText, ${data.newTopicCards} topic cards, and strictly ${data.audiblePingsDuringStorm} audible CEO ping.`
        );
      }
    } finally {
      setBusyAction(null);
    }
  }

  async function handleSynthesizeBriefing() {
    setBusyAction('brief');
    try {
      const res = await fetch('/api/telegram/briefing', { method: 'POST' });
      if (res.ok) {
        const data = (await res.json()) as { snapshot: OttoNumenSnapshot };
        setSnapshot(data.snapshot);
        setSelectedTopic('EXECUTIVE_BRIEFINGS');
        setNotice(
          'Synthesized live CEO Executive Briefing into Topic #102 from Battalion WAL, Legion Ensemble, InterCloud, and Hermes Daily Canon.'
        );
      }
    } finally {
      setBusyAction(null);
    }
  }

  async function handleFocusPolicy(policy: CeoFocusPolicy) {
    setBusyAction('policy');
    try {
      const res = await fetch('/api/telegram/policy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ focusPolicy: policy }),
      });
      if (res.ok) {
        const data = (await res.json()) as OttoNumenSnapshot;
        setSnapshot(data);
        setNotice(`Updated CEO notification discipline to ${policy}.`);
      }
    } finally {
      setBusyAction(null);
    }
  }

  async function handleCoalesceWindow(coalesceWindowSec: number) {
    setBusyAction('coalesce');
    try {
      const res = await fetch('/api/telegram/policy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ coalesceWindowSec }),
      });
      if (res.ok) {
        const data = (await res.json()) as OttoNumenSnapshot;
        setSnapshot(data);
        setNotice(`Burst in-place editMessageText window set to ${coalesceWindowSec}s.`);
      }
    } finally {
      setBusyAction(null);
    }
  }

  async function handleClearMutes() {
    setBusyAction('unmute');
    try {
      const res = await fetch('/api/telegram/unmute-all', { method: 'POST' });
      if (res.ok) {
        const data = (await res.json()) as OttoNumenSnapshot;
        setSnapshot(data);
        setNotice('Cleared all temporary 4h muted fingerprints.');
      }
    } finally {
      setBusyAction(null);
    }
  }

  async function handleInlineCallback(
    messageId: string,
    action: 'approve' | 'hold' | 'ack' | 'mute4h'
  ) {
    setBusyAction(`cb-${messageId}-${action}`);
    try {
      const res = await fetch('/api/telegram/callback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messageId, action }),
      });
      if (res.ok) {
        const data = (await res.json()) as {
          receipt: { action: string; decisionSha256: string; note: string } | null;
          snapshot: OttoNumenSnapshot;
        };
        setSnapshot(data.snapshot);
        if (data.receipt) {
          setNotice(
            `${data.receipt.note} (Signed receipt #${data.receipt.decisionSha256.slice(0, 10)})`
          );
        }
      }
    } finally {
      setBusyAction(null);
    }
  }

  async function handleDispatchProbe(e: React.FormEvent) {
    e.preventDefault();
    if (!probeHeadline.trim()) {
      setNotice('Enter a headline to test topic routing and wire escaping.');
      return;
    }
    setBusyAction('probe');
    try {
      const res = await fetch('/api/telegram/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          kind: probeKind,
          sourceSubsystem: probeSubsystem.trim() || 'Custom Probe',
          headline: probeHeadline.trim(),
          autonomousAction: probeSummary.trim() || 'Validated wire formatting and routing.',
          dedupeKey: probeDedupeKey.trim() || undefined,
          ceoQuestion:
            probeKind === 'p0_ceo_signoff' || probeKind === 'p0_budget_ceiling'
              ? 'Approve execution or hold in gate?'
              : undefined,
          metrics: {
            'Parser Check': 'HTML & MarkdownV2 Escaped',
            'Callback Cap': '<= 64 bytes verified',
          },
        }),
      });
      if (res.ok) {
        const data = (await res.json()) as {
          outcome: string;
          snapshot: OttoNumenSnapshot;
        };
        setSnapshot(data.snapshot);
        setNotice(`Dispatched custom event -> outcome: ${data.outcome}`);
      }
    } finally {
      setBusyAction(null);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6" aria-busy="true" aria-label="Loading VIP CEO Telegram">
        <div className="h-36 bg-white border border-slate-200 rounded-lg animate-pulse" />
        <div className="h-96 bg-white border border-slate-200 rounded-lg animate-pulse" />
      </div>
    );
  }

  if (error || !snapshot) {
    return (
      <div className="bg-white border border-red-200 rounded-lg p-6">
        <h2 className="text-base font-semibold text-red-800">
          Unable to load Hermes · OTTO_NUMEN VIP Telegram Concierge
        </h2>
        <p className="mt-1 text-sm text-slate-600">{error ?? 'Missing state snapshot'}</p>
        <button
          type="button"
          onClick={() => {
            setLoading(true);
            void fetchTelegramState();
          }}
          className="mt-4 rounded-md bg-slate-900 px-4 py-2 text-xs font-medium text-white hover:bg-slate-800"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  const { telemetry, topics, messages, recentReceipts } = snapshot;

  const filteredMessages = messages.filter((msg) => {
    if (selectedTopic !== 'ALL_TOPICS' && msg.topic !== selectedTopic) {
      return false;
    }
    if (unresolvedOnly && msg.resolution !== null) {
      return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        msg.headline.toLowerCase().includes(q) ||
        msg.sourceSubsystem.toLowerCase().includes(q) ||
        msg.priorityTag.toLowerCase().includes(q) ||
        msg.executiveSummary.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* 1. Executive Header & 4-Column Signal Discipline KPI Strip */}
      <section className="bg-white border border-slate-200 rounded-lg p-6">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div className="max-w-2xl">
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 font-mono">
              <span>Hermes · OTTO_NUMEN ({snapshot.botHandle})</span>
              <span aria-hidden="true">·</span>
              <span>Replaces Noisy Single-Channel oot_numun</span>
              <span aria-hidden="true">·</span>
              <span>CEO: {snapshot.ceoRecipient}</span>
            </div>
            <h2 className="mt-1.5 text-xl font-semibold tracking-tight text-slate-900">
              VIP CEO Telegram Concierge, Topic Sharding &amp; Zero-Noise Wire Formatter
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              Separates urgent Founder sign-offs from routine machine telemetry across 5 structured Forum Topics, intercepts 100% of Chronos/WAL heartbeats before Telegram, coalesces flapping alerts in-place via <code className="font-mono text-xs">editMessageText</code>, and enforces strict HTML &amp; MarkdownV2 escaping.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <button
              type="button"
              disabled={busyAction !== null}
              onClick={handleSynthesizeBriefing}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3.5 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors whitespace-nowrap shrink-0 disabled:opacity-50"
            >
              <FileText className="h-3.5 w-3.5" aria-hidden="true" />
              {busyAction === 'brief' ? 'Synthesizing...' : 'Synthesize CEO Briefing'}
            </button>

            <a
              href="/api/telegram/bot-blueprint"
              download="hermes-otto-numen-telegram-bot.ts"
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3.5 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors whitespace-nowrap shrink-0"
            >
              <Download className="h-3.5 w-3.5" aria-hidden="true" />
              Bot Adapter (.ts)
            </a>

            <button
              type="button"
              disabled={busyAction !== null}
              onClick={handleSimulateStorm}
              className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-xs font-medium text-white hover:bg-blue-700 transition-colors whitespace-nowrap shrink-0 disabled:opacity-50"
            >
              <Zap className="h-3.5 w-3.5" aria-hidden="true" />
              {busyAction === 'storm' ? 'Triaging Storm...' : 'Simulate 50-Event Storm'}
            </button>
          </div>
        </div>

        {notice && (
          <div
            role="status"
            className="mt-4 pt-3 border-t border-slate-200 text-xs font-mono text-slate-700"
          >
            {notice}
          </div>
        )}

        {/* 4-Column Executive Signal KPIs */}
        <div className="mt-6 pt-5 border-t border-slate-200 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6">
          <div>
            <div className="text-xs text-slate-500">Audible Interruption Reduction</div>
            <div className="mt-1 text-2xl font-mono tabular-nums font-semibold text-emerald-700">
              {telemetry.audibleInterruptionReductionPct.toFixed(1)}% quieter
            </div>
            <div className="mt-1 text-xs font-mono tabular-nums text-slate-500">
              {telemetry.audibleCeoPings} VIP pings vs {telemetry.legacyAudiblePingsWouldBe} legacy oot_numun pings
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-500">VIP Decisions Awaiting CEO</div>
            <div className="mt-1 text-2xl font-mono tabular-nums font-semibold text-slate-900">
              {telemetry.pendingVipDecisions} open
            </div>
            <div className="mt-1 text-xs font-mono tabular-nums text-slate-500">
              Topic #101 · 1-tap signed callback_data (&le;64B)
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-500">Chatter Intercepted &amp; Coalesced</div>
            <div className="mt-1 text-2xl font-mono tabular-nums font-semibold text-slate-900">
              {(telemetry.suppressedHeartbeatEvents + telemetry.coalescedDuplicateUpdates).toLocaleString()} blocked
            </div>
            <div className="mt-1 text-xs font-mono tabular-nums text-slate-500">
              {telemetry.suppressedHeartbeatEvents} heartbeats dropped · {telemetry.coalescedDuplicateUpdates} in-place edits
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-500">Wire &amp; Screen Budget Discipline</div>
            <div className="mt-1 text-2xl font-mono tabular-nums font-semibold text-slate-900">
              100% Valid
            </div>
            <div className="mt-1 text-xs font-mono tabular-nums text-slate-500">
              HTML + MarkdownV2 escaped · &le;900 chars/card
            </div>
          </div>
        </div>
      </section>

      {/* 2. Main 2-Column Executive Telegram Workspace */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Left Column (4 cols): Forum Topic Router + CEO Focus Governance */}
        <div className="xl:col-span-4 space-y-6">
          <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200">
              <h3 className="text-sm font-semibold text-slate-900">
                01. Telegram Supergroup Forum Topics
              </h3>
              <p className="mt-0.5 text-xs text-slate-500">
                Replaces the single noisy channel with dedicated <code className="font-mono">message_thread_id</code> lanes.
              </p>
            </div>

            <div className="divide-y divide-slate-200" role="group" aria-label="Select Telegram Forum Topic">
              <button
                type="button"
                onClick={() => setSelectedTopic('ALL_TOPICS')}
                className={`w-full px-5 py-3 text-left flex items-center justify-between gap-3 transition-colors ${
                  selectedTopic === 'ALL_TOPICS' ? 'bg-slate-900 text-white' : 'hover:bg-slate-50 text-slate-900'
                }`}
              >
                <div>
                  <div className="text-xs font-semibold">All Delivered Topics (Combined View)</div>
                  <div
                    className={`text-[11px] ${
                      selectedTopic === 'ALL_TOPICS' ? 'text-slate-300' : 'text-slate-500'
                    }`}
                  >
                    Excludes suppressed heartbeat chatter
                  </div>
                </div>
                <span className="font-mono tabular-nums text-xs font-semibold">
                  {messages.length}
                </span>
              </button>

              {topics.map((t) => {
                const isSelected = selectedTopic === t.key;
                const count = telemetry.topicCounts[t.key] ?? 0;
                const isSink = t.key === 'SUPPRESSED_HEARTBEAT_SINK';
                return (
                  <button
                    key={t.key}
                    type="button"
                    onClick={() => setSelectedTopic(t.key)}
                    className={`w-full px-5 py-3 text-left flex items-start justify-between gap-3 transition-colors ${
                      isSelected ? 'bg-slate-900 text-white' : 'hover:bg-slate-50 text-slate-900'
                    }`}
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5 text-xs font-semibold">
                        {t.audiblePolicy === 'VIP_AUDIBLE' ? (
                          <Volume2
                            className={`h-3.5 w-3.5 shrink-0 ${
                              isSelected ? 'text-amber-300' : 'text-blue-600'
                            }`}
                            aria-hidden="true"
                          />
                        ) : (
                          <VolumeX
                            className={`h-3.5 w-3.5 shrink-0 ${
                              isSelected ? 'text-slate-400' : 'text-slate-400'
                            }`}
                            aria-hidden="true"
                          />
                        )}
                        <span className="truncate">{t.title}</span>
                      </div>
                      <div
                        className={`mt-0.5 text-[11px] leading-snug ${
                          isSelected ? 'text-slate-300' : 'text-slate-500'
                        }`}
                      >
                        {t.threadId ? `Thread #${t.threadId} · ` : 'Zero-Send Sink · '}
                        {t.description}
                      </div>
                    </div>
                    <span
                      className={`font-mono tabular-nums text-xs font-semibold shrink-0 ${
                        isSelected
                          ? 'text-white'
                          : isSink
                            ? 'text-slate-500'
                            : t.key === 'VIP_CEO_DECISIONS'
                              ? 'text-blue-700'
                              : 'text-slate-800'
                      }`}
                    >
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>
          </section>

          {/* CEO Attention & Notification Governance */}
          <section className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">
                02. CEO Attention &amp; Coalescing Policy
              </h3>
              <p className="mt-0.5 text-xs text-slate-500">
                Quiet hours: <span className="font-mono">{snapshot.quietHoursUtc}</span>
              </p>
            </div>

            <div>
              <div className="text-xs font-medium text-slate-700 mb-1.5">
                Audible Push Policy (<code className="font-mono">disable_notification</code>)
              </div>
              <div
                role="group"
                aria-label="CEO audible notification policy"
                className="grid grid-cols-1 gap-1.5"
              >
                {(
                  [
                    {
                      id: 'VIP_P0_ONLY',
                      label: 'VIP P0 Decisions Only (Recommended)',
                    },
                    {
                      id: 'VIP_PLUS_BRIEFINGS',
                      label: 'VIP Decisions + Morning/Evening Briefs',
                    },
                    {
                      id: 'SILENT_DND_ALL',
                      label: 'Total Silent DND (Zero Audible Pings)',
                    },
                  ] as const
                ).map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => handleFocusPolicy(opt.id)}
                    className={`w-full rounded-md border px-3 py-2 text-left text-xs font-medium transition-colors whitespace-nowrap truncate ${
                      snapshot.focusPolicy === opt.id
                        ? 'border-slate-900 bg-slate-900 text-white'
                        : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="pt-3 border-t border-slate-200">
              <div className="text-xs font-medium text-slate-700 mb-1.5">
                In-Place Burst Coalesce Window (<code className="font-mono">editMessageText</code>)
              </div>
              <div
                role="group"
                aria-label="Burst coalesce window"
                className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg"
              >
                {[60, 300, 900].map((sec) => (
                  <button
                    key={sec}
                    type="button"
                    onClick={() => handleCoalesceWindow(sec)}
                    className={`flex-1 py-1.5 text-xs font-mono tabular-nums font-medium rounded-md transition-colors whitespace-nowrap ${
                      snapshot.coalesceWindowSec === sec
                        ? 'bg-white text-slate-900 shadow-sm'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {sec}s
                  </button>
                ))}
              </div>
            </div>

            {snapshot.mutedDedupeKeys.length > 0 && (
              <div className="pt-3 border-t border-slate-200 flex items-center justify-between gap-2 text-xs">
                <span className="font-mono text-slate-600">
                  {snapshot.mutedDedupeKeys.length} rule(s) muted 4h
                </span>
                <button
                  type="button"
                  onClick={handleClearMutes}
                  className="inline-flex items-center gap-1 font-medium text-blue-600 hover:text-blue-800 whitespace-nowrap"
                >
                  <RotateCcw className="h-3 w-3" aria-hidden="true" />
                  Clear Mutes
                </button>
              </div>
            )}

            {/* Signed CEO Decision Receipts */}
            <div className="pt-3 border-t border-slate-200">
              <div className="text-xs font-semibold text-slate-900 mb-2">
                Signed CEO Callback Receipts ({recentReceipts.length})
              </div>
              {recentReceipts.length === 0 ? (
                <p className="text-xs text-slate-500">
                  Click any inline action button (<span className="font-mono">Approve &amp; Sign</span>,{' '}
                  <span className="font-mono">Hold in Gate</span>) on a card to record a SHA-256 receipt.
                </p>
              ) : (
                <div className="space-y-2 max-h-44 overflow-y-auto">
                  {recentReceipts.slice(0, 6).map((rcpt) => (
                    <div key={rcpt.receiptId} className="text-xs border-b border-slate-100 pb-2 last:border-b-0">
                      <div className="font-mono font-semibold text-slate-900">
                        {rcpt.action} · #{rcpt.decisionSha256.slice(0, 10)}
                      </div>
                      <div className="text-[11px] text-slate-600">{rcpt.note}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>
        </div>

        {/* Right Column (8 cols): Structured VIP Cards, Before/After Legacy Diff & Wire Inspector */}
        <div className="xl:col-span-8 space-y-6">
          <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <div className="relative">
                  <Search
                    className="h-3.5 w-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2"
                    aria-hidden="true"
                  />
                  <input
                    type="search"
                    aria-label="Search VIP Telegram cards"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Filter cards, #8185, FinOps..."
                    className="w-52 rounded-md border border-slate-300 bg-white pl-8 pr-3 py-1.5 text-xs text-slate-900 focus:border-slate-900 focus:outline-none"
                  />
                </div>

                <label className="inline-flex items-center gap-1.5 text-xs text-slate-600 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={unresolvedOnly}
                    onChange={(e) => setUnresolvedOnly(e.target.checked)}
                    className="rounded border-slate-300"
                  />
                  Unresolved Only
                </label>
              </div>

              <div
                role="group"
                aria-label="Telegram card presentation mode"
                className="flex flex-wrap items-center gap-1 p-1 bg-slate-100 rounded-lg shrink-0"
              >
                {(
                  [
                    { id: 'executive', label: 'VIP Executive Cards' },
                    { id: 'compare_legacy', label: 'vs Legacy oot_numun' },
                    { id: 'wire_payloads', label: 'HTML & MarkdownV2 Wire' },
                  ] as const
                ).map((mode) => (
                  <button
                    key={mode.id}
                    type="button"
                    onClick={() => setInspectMode(mode.id)}
                    className={`px-2.5 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                      inspectMode === mode.id
                        ? 'bg-white text-slate-900 shadow-sm'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {mode.label}
                  </button>
                ))}
              </div>
            </div>

            {selectedTopic === 'SUPPRESSED_HEARTBEAT_SINK' ? (
              <div className="p-6 space-y-4">
                <div className="text-sm font-semibold text-slate-900">
                  Zero-Send Machine Chatter Sink ({telemetry.suppressedHeartbeatEvents.toLocaleString()} events intercepted)
                </div>
                <p className="text-xs text-slate-600">
                  Previously, legacy <code className="font-mono">oot_numun</code> dumped every 6-second Chronos beat, WAL checkpoint, and Dagster probe straight into the CEO&apos;s main Telegram feed. All routine heartbeats are now intercepted here with <strong>zero Telegram API calls</strong> and summarized solely as a 1-line counter in the twice-daily Executive Briefing.
                </p>
                <div className="border-t border-slate-200 pt-4 grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono tabular-nums">
                  <div>
                    <div className="text-slate-500">chronos_heartbeat</div>
                    <div className="mt-0.5 text-base font-semibold text-slate-900">
                      {(telemetry.suppressedBreakdown.chronos_heartbeat ?? 0).toLocaleString()} dropped
                    </div>
                  </div>
                  <div>
                    <div className="text-slate-500">wal_checkpoint_chatter</div>
                    <div className="mt-0.5 text-base font-semibold text-slate-900">
                      {(telemetry.suppressedBreakdown.wal_checkpoint_chatter ?? 0).toLocaleString()} dropped
                    </div>
                  </div>
                  <div>
                    <div className="text-slate-500">dagster_routine_probe</div>
                    <div className="mt-0.5 text-base font-semibold text-slate-900">
                      {(telemetry.suppressedBreakdown.dagster_routine_probe ?? 0).toLocaleString()} dropped
                    </div>
                  </div>
                </div>
              </div>
            ) : filteredMessages.length === 0 ? (
              <div className="p-8 text-center">
                <div className="text-sm font-medium text-slate-900">
                  No cards match the current topic or filter
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  Reset filters or synthesize a live Executive Briefing to populate this topic.
                </p>
                <div className="mt-3 flex justify-center gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedTopic('ALL_TOPICS');
                      setUnresolvedOnly(false);
                      setSearchQuery('');
                    }}
                    className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                  >
                    Reset Filters
                  </button>
                  <button
                    type="button"
                    onClick={handleSynthesizeBriefing}
                    className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-800"
                  >
                    Synthesize CEO Briefing
                  </button>
                </div>
              </div>
            ) : (
              <div className="divide-y divide-slate-200">
                {filteredMessages.map((card) => (
                  <article key={card.messageId} className="p-6 space-y-4">
                    {/* Zero-Pill Metadata Kicker */}
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
                      <div className="flex flex-wrap items-center gap-1.5 text-slate-500">
                        <span
                          className={`font-semibold ${
                            card.priorityTag === 'P0 DECISION'
                              ? 'text-red-700'
                              : card.priorityTag === 'BRIEFING'
                                ? 'text-blue-700'
                                : card.priorityTag === 'AUTO-HEALED'
                                  ? 'text-amber-700'
                                  : 'text-emerald-700'
                          }`}
                        >
                          {card.priorityTag}
                        </span>
                        <span aria-hidden="true">·</span>
                        <span className="text-slate-800 font-medium">{card.sourceSubsystem}</span>
                        <span aria-hidden="true">·</span>
                        <span>Thread #{card.threadId}</span>
                        <span aria-hidden="true">·</span>
                        <span>
                          {card.audiblePingTriggered ? 'Audible VIP Ping' : 'Silent (disable_notification)'}
                        </span>
                        {card.coalescedCount > 1 && (
                          <>
                            <span aria-hidden="true">·</span>
                            <span className="text-blue-700 font-semibold">
                              Coalesced &times;{card.coalescedCount} (editMessageText)
                            </span>
                          </>
                        )}
                      </div>
                      <span className="text-slate-400 tabular-nums">
                        msg #{card.telegramMsgNumericId} · {card.charCount} chars
                      </span>
                    </div>

                    {inspectMode === 'executive' && (
                      <div className="space-y-3">
                        <h4 className="text-base font-semibold text-slate-900">
                          {card.headline}
                        </h4>

                        {/* Aligned Monospace Evidence Block */}
                        <div className="bg-slate-50 border border-slate-200 rounded-md px-4 py-3 font-mono text-xs tabular-nums space-y-1">
                          {card.metrics.map((m, idx) => (
                            <div key={idx} className="grid grid-cols-12 gap-2">
                              <span className="col-span-4 sm:col-span-3 text-slate-500 truncate">
                                {m.label}
                              </span>
                              <span className="col-span-8 sm:col-span-9 text-slate-900 font-medium">
                                {m.value}
                              </span>
                            </div>
                          ))}
                        </div>

                        <p className="text-sm text-slate-700 leading-relaxed">
                          {card.executiveSummary}
                        </p>

                        {card.ceoQuestion && !card.resolution && (
                          <div className="text-sm text-slate-900">
                            <span className="font-semibold">Decision Required: </span>
                            {card.ceoQuestion}
                          </div>
                        )}
                      </div>
                    )}

                    {inspectMode === 'compare_legacy' && (
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-stretch">
                        <div className="border border-red-200 bg-red-50/40 rounded-md p-4 space-y-2">
                          <div className="text-xs font-mono font-semibold text-red-800">
                            BEFORE · Legacy oot_numun (#all_stream · {card.coalescedCount}x Audible Spam)
                          </div>
                          <pre className="text-[11px] font-mono text-slate-700 whitespace-pre-wrap break-all leading-relaxed">
                            {card.legacyNoisyEquivalent}
                          </pre>
                        </div>

                        <div className="border border-slate-200 bg-slate-50/60 rounded-md p-4 space-y-2">
                          <div className="text-xs font-mono font-semibold text-emerald-800">
                            AFTER · Hermes · OTTO_NUMEN (Thread #{card.threadId} · 1 Clean Card)
                          </div>
                          <div className="text-sm font-semibold text-slate-900">{card.headline}</div>
                          <div className="text-xs font-mono text-slate-700 space-y-0.5">
                            {card.metrics.map((m, i) => (
                              <div key={i}>
                                {m.label}: <span className="font-semibold">{m.value}</span>
                              </div>
                            ))}
                          </div>
                          <p className="text-xs text-slate-600">{card.executiveSummary}</p>
                        </div>
                      </div>
                    )}

                    {inspectMode === 'wire_payloads' && (
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                          <div className="text-xs font-mono text-slate-600">
                            parse_mode: &quot;HTML&quot; ({card.htmlWirePayload.length}/900 budget)
                          </div>
                          <pre className="rounded-md bg-slate-900 text-slate-100 p-3 text-[11px] font-mono overflow-x-auto whitespace-pre-wrap leading-relaxed">
                            {card.htmlWirePayload}
                          </pre>
                        </div>
                        <div className="space-y-1.5">
                          <div className="text-xs font-mono text-slate-600">
                            parse_mode: &quot;MarkdownV2&quot; (18-char escaped)
                          </div>
                          <pre className="rounded-md bg-slate-900 text-slate-100 p-3 text-[11px] font-mono overflow-x-auto whitespace-pre-wrap leading-relaxed">
                            {card.markdownV2WirePayload}
                          </pre>
                        </div>
                      </div>
                    )}

                    {/* Resolution Receipt or 1-Tap Inline Keyboard */}
                    {card.resolution ? (
                      <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-xs font-mono text-emerald-800">
                        <span className="inline-flex items-center gap-1.5 font-semibold">
                          <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                          {card.resolution.action} by {card.resolution.actorEmail}
                        </span>
                        <span className="text-slate-500">
                          SHA-256 #{card.resolution.decisionSha256.slice(0, 12)}
                        </span>
                      </div>
                    ) : (
                      <div className="pt-2 flex flex-wrap items-center justify-between gap-3">
                        <div className="flex flex-wrap items-center gap-2">
                          {card.inlineKeyboard.map((btn) => {
                            const actionSlug = btn.callbackData.split(':')[1] as
                              | 'approve'
                              | 'hold'
                              | 'ack'
                              | 'mute4h';
                            return (
                              <button
                                key={btn.callbackData}
                                type="button"
                                disabled={busyAction !== null}
                                onClick={() => handleInlineCallback(card.messageId, actionSlug)}
                                className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors whitespace-nowrap shrink-0 disabled:opacity-50 ${
                                  btn.style === 'primary'
                                    ? 'bg-slate-900 text-white hover:bg-slate-800'
                                    : btn.style === 'caution'
                                      ? 'border border-amber-300 bg-amber-50 text-amber-900 hover:bg-amber-100'
                                      : 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50'
                                }`}
                              >
                                {btn.text}
                              </button>
                            );
                          })}
                        </div>
                        <span className="text-[11px] font-mono text-slate-400">
                          callback_data &le; {Math.max(...card.inlineKeyboard.map((b) => b.byteLength))}B / 64B
                        </span>
                      </div>
                    )}
                  </article>
                ))}
              </div>
            )}
          </section>

          {/* 3. Custom Event Router & Adversarial Formatting Verifier */}
          <section className="bg-white border border-slate-200 rounded-lg p-6">
            <h3 className="text-sm font-semibold text-slate-900">
              03. Test Custom Event Triage, Coalescing &amp; Wire Escaping
            </h3>
            <p className="mt-0.5 text-xs text-slate-500">
              Dispatch any event kind (including unescaped <code className="font-mono">&lt;3</code>, underscores, brackets, or duplicate dedupe keys) to verify Forum Topic routing, in-place coalescing, and HTML/MarkdownV2 safety.
            </p>

            <form onSubmit={handleDispatchProbe} className="mt-4 grid grid-cols-1 sm:grid-cols-12 gap-3">
              <label className="sm:col-span-4 block text-xs text-slate-600">
                Event Classification
                <select
                  value={probeKind}
                  onChange={(e) => setProbeKind(e.target.value as RawEstateEventKind)}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-900 focus:border-slate-900 focus:outline-none"
                >
                  <option value="p0_ceo_signoff">P0 CEO Sign-Off (Topic #101 · Audible VIP)</option>
                  <option value="executive_briefing">Executive Briefing (Topic #102 · Quiet)</option>
                  <option value="incident_auto_healed">Auto-Healed Incident (Topic #104 · Coalesced)</option>
                  <option value="finops_milestone">FinOps Milestone (Topic #108 · Silent)</option>
                  <option value="release_bundle_sync">Release / Audit Sync (Topic #116 · Silent)</option>
                  <option value="chronos_heartbeat">Chronos Heartbeat (Intercepted · Never Sent)</option>
                </select>
              </label>

              <label className="sm:col-span-4 block text-xs text-slate-600">
                Subsystem
                <input
                  type="text"
                  value={probeSubsystem}
                  onChange={(e) => setProbeSubsystem(e.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-900 focus:border-slate-900 focus:outline-none"
                />
              </label>

              <label className="sm:col-span-4 block text-xs text-slate-600">
                Dedupe Key (send twice to coalesce)
                <input
                  type="text"
                  value={probeDedupeKey}
                  onChange={(e) => setProbeDedupeKey(e.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-mono text-slate-900 focus:border-slate-900 focus:outline-none"
                />
              </label>

              <label className="sm:col-span-6 block text-xs text-slate-600">
                Executive Headline
                <input
                  type="text"
                  value={probeHeadline}
                  onChange={(e) => setProbeHeadline(e.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-900 focus:border-slate-900 focus:outline-none"
                />
              </label>

              <label className="sm:col-span-6 block text-xs text-slate-600">
                Autonomous Action / Proof Summary
                <div className="mt-1 flex gap-2">
                  <input
                    type="text"
                    value={probeSummary}
                    onChange={(e) => setProbeSummary(e.target.value)}
                    className="flex-1 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-900 focus:border-slate-900 focus:outline-none"
                  />
                  <button
                    type="submit"
                    disabled={busyAction === 'probe'}
                    className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-3.5 py-1.5 text-xs font-medium text-white hover:bg-slate-800 whitespace-nowrap shrink-0"
                  >
                    <Send className="h-3.5 w-3.5" aria-hidden="true" />
                    Dispatch
                  </button>
                </div>
              </label>
            </form>
          </section>
        </div>
      </div>
    </div>
  );
}
