// FleetView CP2: the board. Every agent session in the estate on one page, live, no reload.
//
// The data comes from the backend CP1 ships (`GET /api/proxy/fleetview/sessions`) and its event stream
// (`GET /api/proxy/fleetview/stream`). Everything that decides WHAT the page says lives in `fleet.ts`,
// which is pure and tested; this file draws it.
//
// Both URLs are reached through the discovery API (not as raw `/api/proxy/...`). `fetchApi` is the
// Backstage HTTP client; it ships a `plugin://` middleware that translates `plugin://proxy/...` into
// the concrete backend URL -- otherwise the relative path lands on `:3100` and the dev server returns
// the SPA shell instead. `EventSource` cannot go through that middleware (it bypasses fetchApi), so
// the stream URL is built explicitly from `discoveryApi.getBaseUrl('proxy')`.
//
// Three states are drawn differently on purpose (see fleet.ts): an unavailable source is an
// error, an empty estate is an empty state, and a live board with a silent runtime carries that
// gap in its own sentence. A page that showed all three as "no sessions" would render an outage
// as a quiet day -- the failure this estate names everywhere else.
//
// The page top comes from `modules/shell` like every other page here (crew#843); drawing our own
// header is what produced four differently-sized titles in the first place.
import { useEffect, useState } from 'react';
import { Progress } from '@backstage/core-components';
import {
  discoveryApiRef,
  fetchApiRef,
  useApi,
} from '@backstage/frontend-plugin-api';
import dagre from 'dagre';
import {
  Background,
  ReactFlow,
  ReactFlowProvider,
  type Edge as RFEdge,
  type Node as RFNode,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Chip, EstatePage, Fold, Section, Sheet, Summary } from '../shell';
import { EstateMap } from './EstateMap';
import {
  attentionReason,
  capabilityLabel,
  capabilityTitle,
  isStale,
  NUDGEABLE_RUNTIMES,
  order,
  prLabel,
  spendLabel,
  stateLabel,
  summarise,
  timelineFor,
} from './fleetBoard';
import type { Board, Note, SessionsEnvelope, Signal } from './fleetBoard';

export const TITLE = 'Fleet';
export const LEAD =
  'Every agent session in the estate, what each is doing, and what it has cost.';

const POLL_MS = 15000;

export function Fleet() {
  const fetchApi = useApi(fetchApiRef);
  const discoveryApi = useApi(discoveryApiRef);
  const [board, setBoard] = useState<Board>(() => summarise(null));
  // Notes are fetched lazily, per session, the first time its fold is opened -- not prefetched for
  // every row on every poll, which would multiply the request count by the session count for a
  // feature most rows never open.
  const [notesBySession, setNotesBySession] = useState<Record<string, Note[]>>({});
  const [draftsBySession, setDraftsBySession] = useState<
    Record<string, { author: string; note: string }>
  >({});

  const loadNotes = async (sessionId: string) => {
    try {
      const res = await fetchApi.fetch(
        `plugin://proxy/fleetview/notes?session_id=${encodeURIComponent(sessionId)}`,
      );
      const body = (await res.json()) as { notes: Note[] };
      setNotesBySession(current => ({ ...current, [sessionId]: body.notes ?? [] }));
    } catch {
      // A notes read that fails leaves the fold showing whatever it already had (or nothing) --
      // the board's own sessions and totals do not depend on this succeeding.
    }
  };

  // CP7: trace data per session, fetched lazily when the Trace fold is opened.
  // available:false means the trace endpoint said so (e.g. Langfuse unconfigured).
  // available:true with nodes.length===0 means no spans recorded yet.
  type TraceState = { available: boolean; nodes: RFNode[]; edges: RFEdge[]; error?: string };
  const [traceBySession, setTraceBySession] = useState<Record<string, TraceState>>({});

  // CP7: ledger rows per session, fetched lazily when the Log fold is opened.
  type LedgerRow = { ts: string; source: string; text: string };
  const [ledgerBySession, setLedgerBySession] = useState<Record<string, { rows: LedgerRow[] }>>({});

  const loadTrace = async (sessionId: string) => {
    try {
      const res = await fetchApi.fetch(
        `plugin://proxy/fleetview/trace?session_id=${encodeURIComponent(sessionId)}`,
      );
      const body = (await res.json()) as {
        available: boolean;
        nodes?: { id: string; label: string }[];
        edges?: { source: string; target: string }[];
        error?: string;
      };
      if (!body.available) {
        setTraceBySession(current => ({
          ...current,
          [sessionId]: { available: false, nodes: [], edges: [], error: body.error },
        }));
        return;
      }
      const rawNodes = body.nodes ?? [];
      const rawEdges = body.edges ?? [];
      if (rawNodes.length === 0) {
        setTraceBySession(current => ({
          ...current,
          [sessionId]: { available: true, nodes: [], edges: [] },
        }));
        return;
      }
      // Lay out with dagre, same pattern as EstateMap.tsx.
      const SPAN_W = 160;
      const SPAN_H = 36;
      const g = new dagre.graphlib.Graph();
      g.setGraph({ rankdir: 'TB', nodesep: 20, ranksep: 50 });
      g.setDefaultEdgeLabel(() => ({}));
      for (const n of rawNodes) g.setNode(n.id, { width: SPAN_W, height: SPAN_H });
      for (const e of rawEdges) {
        if (g.hasNode(e.source) && g.hasNode(e.target)) g.setEdge(e.source, e.target);
      }
      dagre.layout(g);
      const rfNodes: RFNode[] = rawNodes.map(n => {
        const pos = g.node(n.id) ?? { x: 0, y: 0 };
        return {
          id: n.id,
          position: { x: pos.x - SPAN_W / 2, y: pos.y - SPAN_H / 2 },
          data: { label: n.label },
        };
      });
      const rfEdges: RFEdge[] = rawEdges.map((e, i) => ({
        id: `trace-edge-${i}`,
        source: e.source,
        target: e.target,
      }));
      setTraceBySession(current => ({
        ...current,
        [sessionId]: { available: true, nodes: rfNodes, edges: rfEdges },
      }));
    } catch {
      // A trace read that fails leaves the fold showing whatever it already had.
    }
  };

  const loadLedger = async (sessionId: string) => {
    try {
      const res = await fetchApi.fetch(
        `plugin://proxy/fleetview/ledger?session_id=${encodeURIComponent(sessionId)}`,
      );
      const body = (await res.json()) as { rows?: { ts: string; source: string; text: string }[] };
      setLedgerBySession(current => ({
        ...current,
        [sessionId]: { rows: body.rows ?? [] },
      }));
    } catch {
      // A ledger read that fails leaves the fold showing whatever it already had.
    }
  };

  // The focus panel's audit trail: every nudge attempt recorded for the session
  // (backend/src/signals.py's signals_for), merged with its notes into one chronological read.
  // Fetched lazily, same rule as notes -- only once the fold is actually opened.
  const [signalsBySession, setSignalsBySession] = useState<Record<string, Signal[]>>({});

  const loadSignals = async (sessionId: string) => {
    try {
      const res = await fetchApi.fetch(
        `plugin://proxy/fleetview/signals?session_id=${encodeURIComponent(sessionId)}`,
      );
      const body = (await res.json()) as { signals: Signal[] };
      setSignalsBySession(current => ({ ...current, [sessionId]: body.signals ?? [] }));
    } catch {
      // Same rule as loadNotes: a failed read leaves the panel showing whatever it already had.
    }
  };

  // The focus panel's auto-fetched receipt verdict (item #9, backend/src/evals.py), so opening a
  // session's panel answers "did it actually finish?" without a separate trip to the Check
  // receipts section below. Fetched once per session, not on every poll.
  type ReceiptState =
    | { status: 'loading' }
    | { status: 'done'; verdict: string; reason: string }
    | { status: 'error'; error: string };
  const [receiptsBySession, setReceiptsBySession] = useState<Record<string, ReceiptState>>({});

  const loadReceipt = async (sessionId: string) => {
    setReceiptsBySession(current => ({ ...current, [sessionId]: { status: 'loading' } }));
    try {
      const res = await fetchApi.fetch('plugin://proxy/fleetview/check-receipts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_ids: [sessionId] }),
      });
      const body = await res.json();
      if (!res.ok) {
        setReceiptsBySession(current => ({
          ...current,
          [sessionId]: { status: 'error', error: body.error ?? `HTTP ${res.status}` },
        }));
        return;
      }
      const result = (body.results ?? [])[0];
      setReceiptsBySession(current => ({
        ...current,
        [sessionId]: result
          ? { status: 'done', verdict: result.verdict, reason: result.reason }
          : { status: 'error', error: 'no verdict returned' },
      }));
    } catch (err) {
      setReceiptsBySession(current => ({
        ...current,
        [sessionId]: { status: 'error', error: err instanceof Error ? err.message : String(err) },
      }));
    }
  };

  const draftFor = (sessionId: string) =>
    draftsBySession[sessionId] ?? { author: '', note: '' };

  const submitNote = async (sessionId: string, runtime: string) => {
    const draft = draftFor(sessionId);
    if (!draft.author.trim() || !draft.note.trim()) return;
    await fetchApi.fetch('plugin://proxy/fleetview/notes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        runtime,
        note: draft.note,
        author: draft.author,
      }),
    });
    setDraftsBySession(current => ({ ...current, [sessionId]: { author: draft.author, note: '' } }));
    await loadNotes(sessionId);
  };

  // Item #6: nudge / steer a session. CP8 extends to all four runtimes. The steer text input
  // is a plain browser text field -- superwhisper (free tier, local Whisper) dictates into it;
  // nothing in the estate needs to be built for voice (spec 2026-09-08, line 22).
  const [nudgeStatusBySession, setNudgeStatusBySession] = useState<Record<string, string>>({});
  const [steerTextBySession, setSteerTextBySession] = useState<Record<string, string>>({});

  const sendNudge = async (sessionId: string, runtime: string) => {
    const by = draftFor(sessionId).author.trim();
    if (!by) {
      setNudgeStatusBySession(current => ({
        ...current,
        [sessionId]: 'Add your name in Focus above first',
      }));
      return;
    }
    const text = (steerTextBySession[sessionId] ?? '').trim();
    setNudgeStatusBySession(current => ({ ...current, [sessionId]: 'sending…' }));
    try {
      const res = await fetchApi.fetch('plugin://proxy/fleetview/nudge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, runtime, by, ...(text ? { text } : {}) }),
      });
      const body = (await res.json()) as { ok?: boolean; error?: string };
      setNudgeStatusBySession(current => ({
        ...current,
        [sessionId]: res.ok && body.ok !== false ? 'Nudged' : `Failed: ${body.error ?? res.status}`,
      }));
    } catch (err) {
      setNudgeStatusBySession(current => ({
        ...current,
        [sessionId]: `Failed: ${err instanceof Error ? err.message : String(err)}`,
      }));
    }
  };

  // Item #7: blast radius, on the board instead of a terminal. `bin/estate-twin-runtime
  // --blast-radius <node_id>` already answers "if this dies, what dies with it" over the
  // graph's edges table; this is the same query reached from a Backstage door. No session row
  // is wired to a node automatically -- FleetView sessions carry a `repo`, the graph's nodes are
  // `k8s:deployment:...`/`git:branch:...`/`code:module:...`, and guessing a match between them
  // would be exactly the fabricated claim this estate's "measured, not guessed" rule forbids.
  const [blastNodeId, setBlastNodeId] = useState('');
  const [blastResult, setBlastResult] = useState<{
    node_id: string;
    downstream: { node_id: string; hops: number; relation: string }[];
    upstream: { node_id: string; relation: string }[];
  } | null>(null);
  const [blastError, setBlastError] = useState<string | null>(null);
  const [blastLoading, setBlastLoading] = useState(false);

  const checkBlastRadius = async () => {
    const nodeId = blastNodeId.trim();
    if (!nodeId) return;
    setBlastLoading(true);
    setBlastError(null);
    setBlastResult(null);
    try {
      const res = await fetchApi.fetch(
        `plugin://proxy/fleetview/blast-radius?node_id=${encodeURIComponent(nodeId)}`,
      );
      const body = await res.json();
      if (!res.ok) {
        setBlastError(body.error ?? `HTTP ${res.status}`);
      } else {
        setBlastResult(body);
      }
    } catch (err) {
      setBlastError(err instanceof Error ? err.message : String(err));
    } finally {
      setBlastLoading(false);
    }
  };

  // Item #9: check receipts against real production Langfuse traces (backend/src/evals.py).
  // Deliberately mechanical, not a model grading a session -- see evals.py's own docstring for
  // why "no model judges another model" rules that out. Runs only when a human presses Check,
  // over the session ids they name; nothing here schedules or repeats itself.
  const [receiptsInput, setReceiptsInput] = useState('');
  const [receiptsResults, setReceiptsResults] = useState<
    { session_id: string; verdict: string; reason: string }[] | null
  >(null);
  const [receiptsError, setReceiptsError] = useState<string | null>(null);
  const [receiptsLoading, setReceiptsLoading] = useState(false);

  const checkReceipts = async () => {
    const sessionIds = receiptsInput
      .split(',')
      .map(s => s.trim())
      .filter(Boolean);
    if (sessionIds.length === 0) return;
    setReceiptsLoading(true);
    setReceiptsError(null);
    setReceiptsResults(null);
    try {
      const res = await fetchApi.fetch('plugin://proxy/fleetview/check-receipts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_ids: sessionIds }),
      });
      const body = await res.json();
      if (!res.ok) {
        setReceiptsError(body.error ?? `HTTP ${res.status}`);
      } else {
        setReceiptsResults(body.results);
      }
    } catch (err) {
      setReceiptsError(err instanceof Error ? err.message : String(err));
    } finally {
      setReceiptsLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;

    const read = async () => {
      try {
        // `plugin://proxy/fleetview/sessions` -- the discovery middleware rewrites the
        // `proxy` hostname to `${backend.baseUrl}/api/proxy` and joins the path. A bare
        // `/api/proxy/fleetview/sessions` would go to `:3100` (the SPA's origin) and hit the
        // history-API fallback instead of the backend.
        const res = await fetchApi.fetch(
          'plugin://proxy/fleetview/sessions',
        );
        const envelope = (await res.json()) as SessionsEnvelope;
        if (!cancelled) setBoard(summarise(envelope));
      } catch (err) {
        if (!cancelled) {
          // A request that never arrived is unavailable, and the reason is the error's own text.
          // An empty list here would be a lie about the estate.
          setBoard(
            summarise({
              available: false,
              error: err instanceof Error ? err.message : String(err),
            }),
          );
        }
      }
    };

    void read();

    // The stream replaces the old three-second poll. If it cannot be opened the page still shows
    // what it has; the interval below is the fallback so a board is never frozen on a stale row.
    let source: EventSource | undefined;
    if (typeof EventSource !== 'undefined') {
      // EventSource does not route through fetchApi, so the plugin:// middleware is not in
      // the path. Resolve the backend URL explicitly via discoveryApi -- wrapped in an IIFE
      // because the useEffect callback itself is not async.
      void (async () => {
        try {
          const streamBase = await discoveryApi.getBaseUrl('proxy');
          source = new EventSource(`${streamBase}/fleetview/stream`);
          source.onmessage = event => {
            try {
              const frame = JSON.parse(event.data);
              setBoard(current =>
                summarise({
                  available: true,
                  sessions: [
                    ...current.sessions.filter(
                      s => s.session_id !== frame.session_id,
                    ),
                    ...(frame.record ? [frame.record] : []),
                  ],
                  unreachable: current.unreachable,
                }),
              );
              // CP7: when a new event arrives for a session that already has its Trace fold
              // open (traceBySession has an entry), reload the trace to show new spans.
              if (frame.session_id) {
                setTraceBySession(current => {
                  if (current[frame.session_id]) {
                    void loadTrace(frame.session_id);
                  }
                  return current;
                });
              }
            } catch {
              // A frame that will not parse is dropped; the next read reconciles. Taking the board
              // down on one bad frame would lose every other session with it.
            }
          };
        } catch {
          source = undefined;
        }
      })();
    }

    const fallback = window.setInterval(read, POLL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(fallback);
      source?.close();
    };
  }, [fetchApi, discoveryApi]);

  if (board.state === 'loading') {
    return (
      <EstatePage title={TITLE} lead={LEAD}>
        <Progress />
      </EstatePage>
    );
  }

  return (
    <EstatePage title={TITLE} lead={LEAD}>
      <Section title="Estate map">
        <EstateMap />
      </Section>
      <Section title="Sessions">
        <Summary>{board.summary}</Summary>
        {board.correlatedFailure && (
          // Two or more DIFFERENT runtimes failing in the same short window is the signature of
          // a shared control-plane cause (routing, budget, identity), not three unlucky agents --
          // named here so a reader checks the shared cause first instead of debugging three rows
          // as if they were unrelated.
          <div data-testid="correlated-failure-banner">
            <Chip>
              Correlated failure: {board.correlatedFailure.runtimes.join(', ')} each failed within{' '}
              {board.correlatedFailure.windowMinutes} min — check for a shared cause before
              treating these as unrelated
            </Chip>
          </div>
        )}
        {board.attention.length > 0 && (
          // Triage, not table order: a failed or gone-quiet session surfaces here regardless of
          // where it sits in the sheet below. Built only from board.attention (fleetBoard.ts's
          // needsAttention), which itself reasons only from real, measured fields -- state and
          // isStale's elapsed-time claim. Nothing here is a new heuristic.
          <div data-testid="needs-attention">
            <Summary>Needs attention</Summary>
            <ul>
              {board.attention.map(s => (
                <li key={`${s.runtime}:${s.session_id}`}>
                  <Chip>{attentionReason(s) === 'failed' ? 'Failed' : 'Stale'}</Chip>
                  {` ${s.session_id} (${s.runtime}) — ${s.task}`}
                </li>
              ))}
            </ul>
          </div>
        )}
        {board.byRuntime.length > 0 && (
          // Every fleet gets its own chip, alphabetical, so a runtime with one session is exactly
          // as visible as one with a hundred -- the board is for every fleet, not just the
          // biggest one on a given day.
          <div data-testid="fleet-runtime-strip">
            {board.byRuntime.map(r => (
              <Chip key={r.runtime}>
                {r.runtime}: {r.total} total
                {r.running ? `, ${r.running} live` : ''}
                {r.failed ? `, ${r.failed} failed` : ''}
              </Chip>
            ))}
          </div>
        )}
        {board.state === 'unavailable' && (
          // The word a reader scans for. The summary above carries the cause; this carries the
          // verdict, so an outage is visible without reading the sentence.
          <Chip>Unavailable</Chip>
        )}
        {board.state !== 'unavailable' && (
          <Sheet testId="fleet-sessions">
            <thead>
              <tr>
                <th>Session</th>
                <th>Runtime</th>
                <th>Task</th>
                <th>State</th>
                <th>Repo</th>
                <th>Spend</th>
                <th>Capabilities</th>
                <th>Pull requests</th>
                <th>Focus</th>
                <th>Trace</th>
                <th>Log</th>
                <th>Nudge</th>
              </tr>
            </thead>
            <tbody>
              {order(board.sessions).map(s => {
                const notes = notesBySession[s.session_id] ?? [];
                const signals = signalsBySession[s.session_id] ?? [];
                const timeline = timelineFor(notes, signals);
                const receipt = receiptsBySession[s.session_id];
                const draft = draftFor(s.session_id);
                const capability = capabilityLabel(s.capability_class);
                const stale = isStale(s);
                const nudgeable = NUDGEABLE_RUNTIMES.has(s.runtime) && stale;
                return (
                  <tr key={`${s.runtime}:${s.session_id}`}>
                    <td>{s.session_id}</td>
                    <td>{s.runtime}</td>
                    <td>{s.task}</td>
                    <td>{stateLabel(s.state)}</td>
                    <td>{s.repo ?? '—'}</td>
                    <td>{spendLabel(s.spend_usd)}</td>
                    <td>
                      {/* No badge for a runtime with no capability-class concept -- a dash
                          would read as "no capabilities", which is a different, false claim. */}
                      {capability ? (
                        <Chip title={capabilityTitle(s.capabilities)}>{capability}</Chip>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td>{prLabel(s.pull_requests)}</td>
                    <td>
                      {/* The focus panel: notes and nudge attempts merged into one chronological
                          read (fleetBoard.ts's timelineFor), plus an auto-fetched receipt verdict
                          -- so opening a session answers "what happened, and did it actually
                          finish?" without a separate trip to Check receipts below. Nothing here
                          is delivered live into a running process for any runtime today (see
                          docs/founder/fleetview-voice-revisit.md). Everything is fetched once, on
                          first open, not on every poll. */}
                      <Fold
                        testId={`notes-fold-${s.session_id}`}
                        summary={notes.length ? `${notes.length} note${notes.length === 1 ? '' : 's'}` : 'Leave a note'}
                        onToggle={e => {
                          if (!e.currentTarget.open) return;
                          if (!notesBySession[s.session_id]) void loadNotes(s.session_id);
                          if (!signalsBySession[s.session_id]) void loadSignals(s.session_id);
                          if (!receiptsBySession[s.session_id]) void loadReceipt(s.session_id);
                        }}
                      >
                        <div>
                          {receipt && (
                            <div data-testid={`receipt-verdict-${s.session_id}`}>
                              {receipt.status === 'loading' && <Chip>Checking receipt…</Chip>}
                              {receipt.status === 'done' && (
                                <Chip title={receipt.reason}>Receipt: {receipt.verdict}</Chip>
                              )}
                              {receipt.status === 'error' && (
                                <Chip title={receipt.error}>Receipt: unavailable</Chip>
                              )}
                            </div>
                          )}
                          <ul data-testid={`timeline-${s.session_id}`}>
                            {timeline.map((entry, i) =>
                              entry.kind === 'note' ? (
                                <li key={`note-${i}`}>
                                  <strong>{entry.author}</strong>: {entry.text}
                                </li>
                              ) : (
                                <li key={`signal-${i}`}>
                                  <strong>{entry.by}</strong> nudged: {entry.text} —{' '}
                                  {entry.ok ? 'delivered' : `failed: ${entry.error}`}
                                </li>
                              ),
                            )}
                          </ul>
                          <input
                            aria-label={`note author for ${s.session_id}`}
                            placeholder="your name"
                            value={draft.author}
                            onChange={e =>
                              setDraftsBySession(current => ({
                                ...current,
                                [s.session_id]: { ...draftFor(s.session_id), author: e.target.value },
                              }))
                            }
                          />
                          <input
                            aria-label={`note text for ${s.session_id}`}
                            placeholder="leave a note for this session"
                            value={draft.note}
                            onChange={e =>
                              setDraftsBySession(current => ({
                                ...current,
                                [s.session_id]: { ...draftFor(s.session_id), note: e.target.value },
                              }))
                            }
                          />
                          <button
                            type="button"
                            onClick={() => void submitNote(s.session_id, s.runtime)}
                          >
                            Send
                          </button>
                        </div>
                      </Fold>
                    </td>
                    <td>
                      {/* CP7: Trace fold -- React Flow graph of recorded spans, laid out with
                          dagre. Fetched lazily on first open. Reloads on SSE events for this
                          session (the stream is the live clock; the fold shows the latest spans
                          at the moment a person opens it, then stays current while it is open). */}
                      <Fold
                        testId={`trace-fold-${s.session_id}`}
                        summary="Trace"
                        onToggle={e => {
                          if (!e.currentTarget.open) return;
                          if (!traceBySession[s.session_id]) void loadTrace(s.session_id);
                        }}
                      >
                        {(() => {
                          const t = traceBySession[s.session_id];
                          if (!t) return null;
                          if (!t.available) {
                            return <Chip>Trace unavailable: {t.error ?? 'no reason given'}</Chip>;
                          }
                          if (t.nodes.length === 0) {
                            return <Chip>No spans recorded yet</Chip>;
                          }
                          return (
                            <div style={{ width: 600, height: 300, border: '1px solid #e2e8f0', borderRadius: 6 }}>
                              <ReactFlowProvider>
                                <ReactFlow
                                  nodes={t.nodes}
                                  edges={t.edges}
                                  fitView
                                  nodesDraggable={false}
                                  nodesConnectable={false}
                                  proOptions={{ hideAttribution: true }}
                                >
                                  <Background gap={20} />
                                </ReactFlow>
                              </ReactFlowProvider>
                            </div>
                          );
                        })()}
                      </Fold>
                    </td>
                    <td>
                      {/* CP7: Log fold -- last ledger rows for this session. Laptop sessions show
                          the last 20; pod sessions point to cluster logs. Fetched lazily on
                          first open. */}
                      <Fold
                        testId={`log-fold-${s.session_id}`}
                        summary="Log"
                        onToggle={e => {
                          if (!e.currentTarget.open) return;
                          if (!ledgerBySession[s.session_id]) void loadLedger(s.session_id);
                        }}
                      >
                        {(() => {
                          const l = ledgerBySession[s.session_id];
                          if (!l) return null;
                          return (
                            <div>
                              <ul>
                                {l.rows.map((row, i) => (
                                  // eslint-disable-next-line react/no-array-index-key
                                  <li key={i}>
                                    <strong>{row.source}</strong> {row.ts}: {row.text}
                                  </li>
                                ))}
                              </ul>
                              <p>
                                <em>
                                  Laptop sessions show the last 20 ledger rows. Pod sessions: see
                                  cluster logs.
                                </em>
                              </p>
                            </div>
                          );
                        })()}
                      </Fold>
                    </td>
                    <td>
                      {/* Only a stale, sovereign-runtime session ever gets a button -- never one
                          that cannot possibly do anything (see NUDGEABLE_RUNTIMES in fleetBoard.ts). */}
                      {nudgeable ? (
                        <>
                          <input
                            aria-label={`steer text for ${s.session_id}`}
                            placeholder="steer instruction (or dictate with superwhisper)"
                            value={steerTextBySession[s.session_id] ?? ''}
                            onChange={e =>
                              setSteerTextBySession(current => ({
                                ...current,
                                [s.session_id]: e.target.value,
                              }))
                            }
                          />
                          <button
                            type="button"
                            onClick={() => void sendNudge(s.session_id, s.runtime)}
                          >
                            Steer
                          </button>
                          {nudgeStatusBySession[s.session_id] && (
                            <span> {nudgeStatusBySession[s.session_id]}</span>
                          )}
                        </>
                      ) : (
                        '—'
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </Sheet>
        )}
      </Section>
      <Section title="Blast radius">
        <Summary>
          If this node died right now, what dies with it -- the same answer{' '}
          <code>bin/estate-twin-runtime --blast-radius</code> gives at a terminal, over the
          graph's own edges. Node ids look like <code>k8s:deployment:idp:catalogue</code>.
        </Summary>
        <input
          aria-label="blast radius node id"
          placeholder="k8s:deployment:idp:catalogue"
          value={blastNodeId}
          onChange={e => setBlastNodeId(e.target.value)}
        />
        <button type="button" disabled={blastLoading} onClick={() => void checkBlastRadius()}>
          {blastLoading ? 'Checking…' : 'Check'}
        </button>
        {blastError && (
          // A graph that has never been swept and a node with no edges are different facts
          // (see blast.py) -- the error text carries which one this is, never a blank result.
          <Chip>{blastError}</Chip>
        )}
        {blastResult && (
          <div data-testid="blast-radius-result">
            <p>{blastResult.node_id}</p>
            <div>
              <strong>Upstream (depends on it)</strong>
              {blastResult.upstream.length === 0 ? (
                <p>Nothing recorded in the graph yet.</p>
              ) : (
                <ul>
                  {blastResult.upstream.map(u => (
                    <li key={u.node_id}>
                      {u.node_id} ({u.relation})
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <strong>Downstream (dies with it)</strong>
              {blastResult.downstream.length === 0 ? (
                <p>Nothing recorded in the graph yet.</p>
              ) : (
                <ul>
                  {blastResult.downstream.map(d => (
                    <li key={d.node_id}>
                      +{d.hops} {d.node_id} ({d.relation})
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </Section>
      <Section title="Check receipts">
        <Summary>
          Does a session that claims done actually have evidence behind it? Checks each named
          session's real production Langfuse trace for a success status with zero recorded
          observations -- a claimed win with no receipt. No model grades another model here;
          this is a mechanical check, the same rule <code>receipt-auditor</code> follows by hand.
          Comma-separated session ids.
        </Summary>
        <input
          aria-label="check receipts session ids"
          placeholder="session-1, session-2"
          value={receiptsInput}
          onChange={e => setReceiptsInput(e.target.value)}
        />
        <button type="button" disabled={receiptsLoading} onClick={() => void checkReceipts()}>
          {receiptsLoading ? 'Checking…' : 'Check receipts'}
        </button>
        {receiptsError && (
          // Langfuse unconfigured/unreachable is a named gap, never a silent pass (see evals.py).
          <Chip>{receiptsError}</Chip>
        )}
        {receiptsResults && (
          <ul data-testid="check-receipts-result">
            {receiptsResults.map(r => (
              <li key={r.session_id}>
                <strong>{r.session_id}</strong>: {r.verdict} — {r.reason}
              </li>
            ))}
          </ul>
        )}
      </Section>
    </EstatePage>
  );
}
