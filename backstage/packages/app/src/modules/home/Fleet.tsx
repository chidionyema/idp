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
import Box from '@material-ui/core/Box';
import Button from '@material-ui/core/Button';
import MuiChip from '@material-ui/core/Chip';
import IconButton from '@material-ui/core/IconButton';
import TextField from '@material-ui/core/TextField';
import Tooltip from '@material-ui/core/Tooltip';
import Typography from '@material-ui/core/Typography';
import dagre from 'dagre';
import {
  Background,
  ReactFlow,
  ReactFlowProvider,
  type Edge as RFEdge,
  type Node as RFNode,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Chip, EstatePage, Fold, Section, Summary } from '../shell';
import { EstateMap } from './EstateMap';
import {
  attentionReason,
  capabilityLabel,
  capabilityTitle,
  NUDGEABLE_RUNTIMES,
  order,
  prLabel,
  signalWord,
  spendLabel,
  stateLabel,
  summarise,
  timelineFor,
} from './fleetBoard';
import type { Board, Note, SessionsEnvelope, Signal } from './fleetBoard';

// THE DESIGN SYSTEM, USED RATHER THAN REINVENTED.
//
// Measured in a browser 2026-09-18: this file carried 20 raw hex literals and imported zero
// tokens, while every other page in modules/home (Ops, EstateHome, Board) hardcodes nothing.
// The result was a page that looked like a different product from the rest of the portal, and
// text nobody could read:
//
//   212 of 373 text nodes below WCAG 4.5:1 (57% of the page)
//   'History & trace' at 1.11:1 and #484f58 at ~1.9:1 -- not muted, invisible
//   #6b7280 used 14 times, at ~4.0:1 on the dark surface it sat on
//   12 distinct font sizes and two border radii (4px and 10px) with no scale
//
// tokens.ts already carries a checked palette (textMuted #7a828e on canvas #0b0c0e is 4.6:1)
// and tokens.contrast.test.ts exists to keep it that way. So the fix is not a new palette: it is
// to STOP BYPASSING the one the estate has. Every value below now comes from `T`.
import { dark as T } from '../theme/tokens';

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
      setSignalsLoadedBySession(current => ({ ...current, [sessionId]: true }));
      // The newest signal for each session is what the ack word under the Steer button reads,
      // and the board may have been steered before this panel was ever opened -- so a send also
      // sets the flag, below, without waiting for a fetch that may never happen.
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

  const [nudgeStatusBySession, setNudgeStatusBySession] = useState<Record<string, string>>({});
  // Whether this session's signal history has been fetched. The ack word below the button is
  // derived from it, and must not claim 'not yet read' for a signal nobody has looked up yet --
  // 'not loaded' and 'not read' are different facts, the same distinction the whole ack change
  // exists to preserve.
  const [signalsLoadedBySession, setSignalsLoadedBySession] = useState<Record<string, boolean>>({});
  const [steerTextBySession, setSteerTextBySession] = useState<Record<string, string>>({});
  const [stopStatusBySession, setStopStatusBySession] = useState<Record<string, string>>({});
  const [approveStatusBySession, setApproveStatusBySession] = useState<Record<string, string>>({});
  const [denyStatusBySession, setDenyStatusBySession] = useState<Record<string, string>>({});
  const [listeningSession, setListeningSession] = useState<string | null>(null);

  const startDictation = (sessionId: string) => {
    const SR = (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition;
    if (!SR) return;
    const rec = new SR() as any;
    rec.continuous = false; rec.interimResults = false; rec.lang = 'en-US';
    setListeningSession(sessionId);
    rec.onresult = (e: any) => {
      const t: string = e.results[0][0].transcript;
      setSteerTextBySession(cur => ({ ...cur, [sessionId]: (cur[sessionId] ? cur[sessionId] + ' ' : '') + t }));
    };
    rec.onend = () => setListeningSession(null);
    rec.onerror = () => setListeningSession(null);
    rec.start();
  };

  const sendNudge = async (sessionId: string, runtime: string) => {
    const text = (steerTextBySession[sessionId] ?? '').trim();
    if (!text) {
      // 2026-09-18: this used to `return` in silence, so pressing Steer on an empty field did
      // nothing at all and read as a broken button. The estate's rule is that a surface which
      // cannot act must say why, so the status line now carries the reason and the audit trail
      // gets no row -- nothing was sent.
      setNudgeStatusBySession(cur => ({
        ...cur,
        [sessionId]: 'Add your steer text first',
      }));
      setTimeout(
        () => setNudgeStatusBySession(cur => ({ ...cur, [sessionId]: '' })),
        3000,
      );
      return;
    }
    setNudgeStatusBySession(cur => ({ ...cur, [sessionId]: 'sending…' }));
    try {
      const res = await fetchApi.fetch('plugin://proxy/fleetview/nudge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, runtime, by: 'founder', text }),
      });
      const body = (await res.json()) as { ok?: boolean; error?: string };
      const success = res.ok && body.ok !== false;
      setNudgeStatusBySession(cur => ({ ...cur, [sessionId]: success ? '✓ steered' : `Failed: ${body.error ?? res.status}` }));
      if (success) {
        setSteerTextBySession(cur => ({ ...cur, [sessionId]: '' }));
        // Re-read the audit trail so the ack word under the button reflects the row just
        // written. Without this the word would wait for the history fold to be opened, and a
        // reader who never opens it would see no ack state at all -- which is the gap this
        // whole change exists to close.
        void loadSignals(sessionId);
        setTimeout(() => setNudgeStatusBySession(cur => ({ ...cur, [sessionId]: '' })), 2000);
      }
    } catch (err) {
      setNudgeStatusBySession(cur => ({ ...cur, [sessionId]: `Failed: ${err instanceof Error ? err.message : String(err)}` }));
    }
  };

  const sendStop = async (sessionId: string, runtime: string) => {
    setStopStatusBySession(cur => ({ ...cur, [sessionId]: 'stopping…' }));
    try {
      const res = await fetchApi.fetch('plugin://proxy/fleetview/stop', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, runtime, by: 'founder' }),
      });
      const body = (await res.json()) as { ok?: boolean; error?: string };
      setStopStatusBySession(cur => ({ ...cur, [sessionId]: res.ok && body.ok !== false ? '■ stopped' : `Failed: ${body.error ?? res.status}` }));
    } catch (err) {
      setStopStatusBySession(cur => ({ ...cur, [sessionId]: `Failed: ${err instanceof Error ? err.message : String(err)}` }));
    }
  };

  const sendApprove = async (sessionId: string, runtime: string) => {
    setApproveStatusBySession(cur => ({ ...cur, [sessionId]: 'approving…' }));
    try {
      const res = await fetchApi.fetch('plugin://proxy/fleetview/approve', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, runtime, by: 'founder' }),
      });
      const body = (await res.json()) as { ok?: boolean; error?: string };
      setApproveStatusBySession(cur => ({ ...cur, [sessionId]: res.ok && body.ok !== false ? '✓ approved' : `Failed: ${body.error ?? res.status}` }));
    } catch (err) {
      setApproveStatusBySession(cur => ({ ...cur, [sessionId]: `Failed: ${err instanceof Error ? err.message : String(err)}` }));
    }
  };

  const sendDeny = async (sessionId: string, runtime: string) => {
    setDenyStatusBySession(cur => ({ ...cur, [sessionId]: 'denying…' }));
    try {
      const res = await fetchApi.fetch('plugin://proxy/fleetview/deny', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, runtime, by: 'founder' }),
      });
      const body = (await res.json()) as { ok?: boolean; error?: string };
      setDenyStatusBySession(cur => ({ ...cur, [sessionId]: res.ok && body.ok !== false ? '✕ denied' : `Failed: ${body.error ?? res.status}` }));
    } catch (err) {
      setDenyStatusBySession(cur => ({ ...cur, [sessionId]: `Failed: ${err instanceof Error ? err.message : String(err)}` }));
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
      {/* SESSIONS FIRST. Measured 2026-09-18 in a 1440x1100 browser: with the estate map above
          it, the board did not begin until y=808 and the first session card sat at y=980 --
          below the fold on a laptop. A person opening /fleet saw a graph and no fleet. The page
          is the fleet board; the map is context for it, and context does not go first.

          The map is also BROKEN on this machine, which made it worse than a layout choice: it
          renders "unreadable" and forty bare namespace names, 580px of it, above the cards. */}
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
          <>
            <style>{`
              @keyframes fleet-pulse { 0%,100%{opacity:1} 50%{opacity:.35} }
              @keyframes fleet-mic { 0%,100%{box-shadow:0 0 0 0 rgba(239,68,68,.4)} 70%{box-shadow:0 0 0 8px rgba(239,68,68,0)} }
            `}</style>
            <div data-testid="fleet-sessions" style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(360px,1fr))', gap:16, paddingTop:8 }}>
              {order(board.sessions).map(s => {
                const notes = notesBySession[s.session_id] ?? [];
                const signals = signalsBySession[s.session_id] ?? [];
                const signalsLoaded = Boolean(signalsLoadedBySession[s.session_id]);
                const timeline = timelineFor(notes, signals);
                const receipt = receiptsBySession[s.session_id];
                const draft = draftFor(s.session_id);
                const capability = capabilityLabel(s.capability_class);
                const nudgeable = NUDGEABLE_RUNTIMES.has(s.runtime);
                const rc = s.runtime === 'claude-code' ? '#7c3aed' : s.runtime === 'sovereign' ? '#0369a1' : s.runtime === 'otto' ? '#059669' : T.textMuted;
                const sc = s.state === 'running' ? '#22c55e' : s.state === 'paused' ? '#f59e0b' : s.state === 'failed' ? '#ef4444' : T.textMuted;
                const isRunning = s.state === 'running';
                const isPaused = s.state === 'paused';
                return (
                  <Box key={s.session_id} style={{ background:T.surface1, border:`1px solid rgba(255,255,255,0.07)`, borderLeft:`3px solid ${rc}`, borderRadius:10, padding:'16px 18px', display:'flex', flexDirection:'column', gap:10 }}>
                    {/* Header row */}
                    <Box display="flex" alignItems="center" justifyContent="space-between">
                      <Box display="flex" alignItems="center" style={{ gap:7 }}>
                        <span style={{ width:8, height:8, borderRadius:'50%', background:sc, display:'inline-block', flexShrink:0, animation: isRunning ? 'fleet-pulse 1.6s ease-in-out infinite' : undefined }} />
                        <MuiChip size="small" label={s.runtime} style={{ background:rc, color:'#fff', fontWeight:700, fontSize:10, height:18, borderRadius:4, letterSpacing:0.4 }} />
                        <MuiChip size="small" label={stateLabel(s.state).toUpperCase()} style={{ background:'transparent', color:sc, border:`1px solid ${sc}`, fontWeight:700, fontSize:10, height:18, borderRadius:4 }} />
                        {capability && (
                          <Tooltip title={capabilityTitle(s.capabilities) ?? ''}>
                            <MuiChip size="small" label={capability} style={{ fontSize:10, height:18, borderRadius:4 }} />
                          </Tooltip>
                        )}
                      </Box>
                      {/* The session's own id, LABELLED. It read `198f9fb5c1` at 10px with nothing
                          saying what it was: a raw hash in the corner of a card. `monospace` plus a
                          `#` prefix makes the same bytes read as an identifier, which is what a
                          person needs when they go looking for it in a terminal. */}
                      <Typography variant="caption" title={s.session_id}
                        style={{ fontFamily:'monospace', color:T.textMuted, fontSize:11 }}>
                        #{s.session_id.slice(-10)}
                      </Typography>
                    </Box>

                    {/* Task.

                        CLAMPED, and that is the fix for the loudest visual defect on the card.
                        Measured in a browser 2026-09-18: a card's title rendered the raw first
                        user message verbatim -- `⏺ Bash(git commit -m "feat(fleetview): card grid UI,
                        voice dictation, Stop/Approve/Deny/Steer…` -- at 14px weight 500, running
                        four lines. Terminal escape glyphs and a truncated commit message are not a
                        task description, and at full length they dominated the card.

                        Two lines, ellipsis, and the whole thing on hover. The text is still the
                        real first message, unedited; it is no longer ALL of it. */}
                    <Typography variant="body2" title={s.task || undefined}
                      style={{ color:T.textPrimary, fontWeight:500, fontSize:14, lineHeight:1.45,
                        display:'-webkit-box', WebkitLineClamp:2, WebkitBoxOrient:'vertical',
                        overflow:'hidden', minHeight:41 }}>
                      {s.task || <span style={{ color:T.textMuted, fontStyle:'italic' }}>no task description</span>}
                    </Typography>

                    {/* Meta */}
                    <Box display="flex" style={{ gap:14, flexWrap:'wrap' }}>
                      {s.repo && <Typography variant="caption" style={{ color:T.textMuted }}>repo <span style={{ color:T.textSecondary, fontWeight:600 }}>{s.repo}</span></Typography>}
                      <Typography variant="caption" style={{ color:T.textMuted }}>spend <span style={{ color:T.textSecondary, fontWeight:600 }}>{spendLabel(s.spend_usd)}</span></Typography>
                      {s.ticket && <Typography variant="caption" style={{ color:T.textMuted }}>ticket <span style={{ color:T.textSecondary, fontWeight:600 }}>{s.ticket}</span></Typography>}
                      {prLabel(s.pull_requests) !== '—' && <Typography variant="caption" style={{ color:T.textMuted }}>PRs <span style={{ color:T.textSecondary, fontWeight:600 }}>{prLabel(s.pull_requests)}</span></Typography>}
                    </Box>

                    {/* Controls */}
                    {nudgeable && (
                      <Box style={{ borderTop:'1px solid rgba(255,255,255,0.06)', paddingTop:10, display:'flex', flexDirection:'column', gap:8 }}>
                        {/* Stop / Approve / Deny */}
                        {isRunning && (
                          <Box display="flex" alignItems="center" style={{ gap:8 }}>
                            <Button variant="contained" size="small" fullWidth
                              style={{ background:'#7f1d1d', color:'#fca5a5', fontWeight:800, fontSize:11, letterSpacing:1, borderRadius:6, padding:'5px 0' }}
                              onClick={() => void sendStop(s.session_id, s.runtime)}>
                              ■ STOP
                            </Button>
                            {stopStatusBySession[s.session_id] && <Typography variant="caption" style={{ color:T.textMuted, whiteSpace:'nowrap' }}>{stopStatusBySession[s.session_id]}</Typography>}
                          </Box>
                        )}
                        {isPaused && (
                          <Box display="flex" style={{ gap:8 }}>
                            <Button variant="contained" size="small" fullWidth
                              style={{ background:'#14532d', color:'#86efac', fontWeight:800, fontSize:11, letterSpacing:0.8, borderRadius:6 }}
                              onClick={() => void sendApprove(s.session_id, s.runtime)}>
                              ✓ APPROVE
                            </Button>
                            <Button variant="outlined" size="small" fullWidth
                              style={{ color:'#9ca3af', borderColor:T.border, fontWeight:700, fontSize:11, letterSpacing:0.8, borderRadius:6 }}
                              onClick={() => void sendDeny(s.session_id, s.runtime)}>
                              ✕ DENY
                            </Button>
                            {(approveStatusBySession[s.session_id] || denyStatusBySession[s.session_id]) && (
                              <Typography variant="caption" style={{ color:T.textMuted, alignSelf:'center', whiteSpace:'nowrap' }}>
                                {approveStatusBySession[s.session_id] || denyStatusBySession[s.session_id]}
                              </Typography>
                            )}
                          </Box>
                        )}

                        {/* Steer row */}
                        <Box display="flex" alignItems="center" style={{ gap:6 }}>
                          <Tooltip title={listeningSession === s.session_id ? 'Listening…' : 'Dictate'}>
                            <IconButton size="small" onClick={() => startDictation(s.session_id)}
                              style={{ background: listeningSession === s.session_id ? '#450a0a' : T.surface2, color: listeningSession === s.session_id ? '#ef4444' : T.textMuted, borderRadius:6, width:32, height:32, border:'1px solid rgba(255,255,255,0.08)', animation: listeningSession === s.session_id ? 'fleet-mic 1s ease-out infinite' : undefined }}>
                              🎤
                            </IconButton>
                          </Tooltip>
                          <TextField size="small" variant="outlined" placeholder="Steer this agent…"
                            value={steerTextBySession[s.session_id] ?? ''}
                            onChange={e => setSteerTextBySession(cur => ({ ...cur, [s.session_id]: e.target.value }))}
                            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void sendNudge(s.session_id, s.runtime); } }}
                            style={{ flex:1 }}
                            inputProps={{ style:{ fontSize:12, color:T.textPrimary, padding:'6px 10px', background:T.canvas } }}
                            InputProps={{ style:{ borderRadius:6, borderColor:T.border } }} />
                          {(() => {
                            const st = nudgeStatusBySession[s.session_id];
                            const ok = st === '✓ steered';
                            const busy = st === 'sending…';
                            const fail = st && !ok && !busy;
                            // 2026-09-18: what the newest recorded signal for this session
                            // ACTUALLY achieved. Before this the button said '✓ SENT' and
                            // stopped there, which described the write and not the read -- and
                            // SPEC CP8's done-condition is that the session acknowledges it.
                            // `signals` is already fetched for the history fold, so this costs
                            // no request.
                            const newest = signals.length ? signals[0] : undefined;
                            const ackWord = newest ? signalWord(newest) : null;
                            return (
                              <Box display="flex" flexDirection="column" style={{ gap:2 }}>
                                <Button variant="contained" size="small" disabled={busy}
                                  style={{ fontWeight:800, whiteSpace:'nowrap', fontSize:11, letterSpacing:0.8, minWidth:72, borderRadius:6, height:32,
                                    // MEASURED 2026-09-18 in a browser: in the IDLE state this
                                    // button rendered `color:#fff` on `rgb(224,224,224)` -- MUI's
                                    // default grey fill, because `background` was left `undefined`
                                    // while the colour was forced white. That is 1.32:1, effectively
                                    // invisible, on the PRIMARY ACTION of every card. The estate's
                                    // accent is the idle fill and `inkOnAccent` is the text colour
                                    // checked against it (tokens.contrast.test.ts).
                                    background: ok ? '#166534' : fail ? '#7f1d1d' : busy ? T.border : T.accent,
                                    color: ok ? '#86efac' : fail ? '#fca5a5' : busy ? T.textSecondary : T.inkOnAccent,
                                    transition: 'background 0.2s, color 0.2s' }}
                                  onClick={() => void sendNudge(s.session_id, s.runtime)}>
                                  {ok ? '✓ SENT' : fail ? '✕ FAIL' : busy ? '…' : 'STEER →'}
                                </Button>
                                {signalsLoaded && ackWord ? (
                                  <Typography variant="caption" data-testid={`ack-${s.session_id}`}
                                    style={{ fontSize:10, color: ackWord === 'read' ? '#7ee787' : ackWord === 'failed' ? '#fca5a5' : '#9ca3af', whiteSpace:'nowrap', textAlign:'center' }}>
                                    {ackWord}
                                  </Typography>
                                ) : null}
                              </Box>
                            );
                          })()}
                        </Box>
                        {nudgeStatusBySession[s.session_id] && nudgeStatusBySession[s.session_id] !== '✓ steered' && nudgeStatusBySession[s.session_id] !== 'sending…' && (
                          <Typography variant="caption" style={{ color:'#ef4444', fontSize:11 }}>{nudgeStatusBySession[s.session_id]}</Typography>
                        )}
                      </Box>
                    )}

                    {/* History / trace / log (lazy) */}
                    <Fold testId={`focus-${s.session_id}`} summary={notes.length ? `${notes.length} note${notes.length === 1 ? '' : 's'} · history` : 'History & trace'}
                      onToggle={e => {
                        if (!e.currentTarget.open) return;
                        if (!notesBySession[s.session_id]) void loadNotes(s.session_id);
                        if (!signalsBySession[s.session_id]) void loadSignals(s.session_id);
                        if (!receiptsBySession[s.session_id]) void loadReceipt(s.session_id);
                        if (!traceBySession[s.session_id]) void loadTrace(s.session_id);
                        if (!ledgerBySession[s.session_id]) void loadLedger(s.session_id);
                      }}>
                      <div style={{ display:'flex', flexDirection:'column', gap:8, paddingTop:6 }}>
                        {receipt && (
                          <div data-testid={`receipt-verdict-${s.session_id}`}>
                            {receipt.status === 'loading' && <Chip>Checking receipt…</Chip>}
                            {receipt.status === 'done' && <Chip title={receipt.reason}>Receipt: {receipt.verdict}</Chip>}
                            {receipt.status === 'error' && <Chip title={receipt.error}>Receipt: unavailable</Chip>}
                          </div>
                        )}
                        {timeline.length > 0 && (
                          <ul data-testid={`timeline-${s.session_id}`} style={{ margin:0, paddingLeft:16, fontSize:12, color:T.textSecondary }}>
                            {timeline.map((entry, i) =>
                              entry.kind === 'note' ? (
                                <li key={`note-${i}`}><strong style={{ color:T.textPrimary }}>{entry.author}</strong>: {entry.text}</li>
                              ) : (
                                <li key={`sig-${i}`}>
                                  <strong style={{ color:T.textPrimary }}>{entry.by}</strong> {
                                    // 2026-09-18: this said `entry.ok ? 'delivered' : ...`, and
                                    // `ok` describes the WRITE. A directive file written to
                                    // ~/.claude/state/directives/ and read by nobody rendered as
                                    // 'delivered' for a day. SPEC CP8's own done-condition is
                                    // that the session ACKNOWLEDGES it, so the word now names
                                    // what was proven: read, or not yet read.
                                    entry.acknowledged
                                      ? `${entry.kind} sent, read by the session`
                                      : entry.ok
                                        ? `${entry.kind} sent, not yet read`
                                        : `${entry.kind} failed: ${entry.error}`
                                  }
                                  {entry.text ? ` — ${entry.text}` : ''}
                                </li>
                              )
                            )}
                          </ul>
                        )}
                        {/* Trace */}
                        {(() => {
                          const t = traceBySession[s.session_id];
                          if (!t) return null;
                          if (!t.available) return <Typography variant="caption" style={{ color:T.textMuted }}>Trace unavailable: {t.error ?? 'no reason given'}</Typography>;
                          if (t.nodes.length === 0) return <Typography variant="caption" style={{ color:T.textMuted }}>No spans recorded yet</Typography>;
                          return (
                            <div style={{ width:'100%', height:220, border:'1px solid #30363d', borderRadius:6 }}>
                              <ReactFlowProvider>
                                <ReactFlow nodes={t.nodes} edges={t.edges} fitView nodesDraggable={false} nodesConnectable={false} proOptions={{ hideAttribution:true }}>
                                  <Background gap={20} />
                                </ReactFlow>
                              </ReactFlowProvider>
                            </div>
                          );
                        })()}
                        {/* Log */}
                        {ledgerBySession[s.session_id] && (
                          <ul style={{ margin:0, paddingLeft:16, fontSize:11, color:T.textMuted, fontFamily:'monospace' }}>
                            {ledgerBySession[s.session_id].rows.map((row, i) => (
                              // eslint-disable-next-line react/no-array-index-key
                              <li key={i}><span style={{ color:T.textMuted }}>{row.ts.slice(11,19)}</span> <strong style={{ color:T.textSecondary }}>{row.source}</strong> {row.text}</li>
                            ))}
                          </ul>
                        )}
                        {/* Leave a note */}
                        <Box display="flex" style={{ gap:6, marginTop:4 }}>
                          <input aria-label={`note author for ${s.session_id}`} placeholder="your name"
                            value={draft.author}
                            onChange={e => setDraftsBySession(cur => ({ ...cur, [s.session_id]: { ...draftFor(s.session_id), author: e.target.value } }))}
                            style={{ width:100, fontSize:12, background:T.surface1, color:T.textPrimary, border:'1px solid #30363d', borderRadius:4, padding:'4px 8px' }} />
                          <input aria-label={`note text for ${s.session_id}`} placeholder="leave a note…"
                            value={draft.note}
                            onChange={e => setDraftsBySession(cur => ({ ...cur, [s.session_id]: { ...draftFor(s.session_id), note: e.target.value } }))}
                            style={{ flex:1, fontSize:12, background:T.surface1, color:T.textPrimary, border:'1px solid #30363d', borderRadius:4, padding:'4px 8px' }} />
                          <button type="button" onClick={() => void submitNote(s.session_id, s.runtime)}
                            aria-label={`send note for ${s.session_id}`}
                            style={{ fontSize:11, background:T.surface3, color:T.textPrimary, border:'1px solid #30363d', borderRadius:4, padding:'4px 10px', cursor:'pointer' }}>
                            Note
                          </button>
                        </Box>
                      </div>
                    </Fold>
                  </Box>
                );
              })}
            </div>
          </>
        )}
      </Section>

      {/* The estate map, below the board it gives context to. It is genuinely useful -- every
          namespace and its relations -- but it must not stand between a person and the
          sessions, which is what it did: measured 2026-09-18, the board began at y=808 with
          the first card at y=980, below the fold on a laptop, under 580px of this. */}
      <Section title="Estate map">
        <EstateMap />
      </Section>

      <Section title="Tools">
        <Box display="flex" style={{ gap:24, flexWrap:'wrap' }}>
          {/* Blast radius */}
          <Box style={{ flex:'1 1 320px', minWidth:280 }}>
            <Typography variant="subtitle2" style={{ color:T.textSecondary, fontWeight:700, marginBottom:8 }}>Blast radius</Typography>
            <Typography variant="caption" style={{ color:T.textMuted, display:'block', marginBottom:8 }}>
              If this node died right now, what dies with it.
            </Typography>
            <Box display="flex" style={{ gap:6 }}>
              <input aria-label="blast radius node id" placeholder="k8s:deployment:idp:catalogue"
                value={blastNodeId} onChange={e => setBlastNodeId(e.target.value)}
                style={{ flex:1, fontSize:12, background:T.surface1, color:T.textPrimary, border:'1px solid #30363d', borderRadius:6, padding:'6px 10px' }} />
              <button type="button" disabled={blastLoading} onClick={() => void checkBlastRadius()}
                aria-label="check blast radius"
                style={{ fontSize:12, fontWeight:700, background:T.surface3, color:T.textPrimary, border:'1px solid #30363d', borderRadius:6, padding:'6px 14px', cursor:'pointer' }}>
                {blastLoading ? '…' : 'Check'}
              </button>
            </Box>
            {blastError && <Typography variant="caption" style={{ color:'#ef4444', display:'block', marginTop:6 }}>{blastError}</Typography>}
            {blastResult && (
              <div data-testid="blast-radius-result" style={{ marginTop:8, fontSize:12, color:T.textSecondary }}>
                <div><strong style={{ color:T.textPrimary }}>Upstream</strong>{blastResult.upstream.length === 0 ? ' — none recorded' : ''}</div>
                {blastResult.upstream.map(u => <div key={u.node_id} style={{ paddingLeft:12 }}>{u.node_id} ({u.relation})</div>)}
                <div style={{ marginTop:4 }}><strong style={{ color:T.textPrimary }}>Downstream</strong>{blastResult.downstream.length === 0 ? ' — none recorded' : ''}</div>
                {blastResult.downstream.map(d => <div key={d.node_id} style={{ paddingLeft:12 }}>+{d.hops} {d.node_id} ({d.relation})</div>)}
              </div>
            )}
          </Box>

          {/* Check receipts */}
          <Box style={{ flex:'1 1 320px', minWidth:280 }}>
            <Typography variant="subtitle2" style={{ color:T.textSecondary, fontWeight:700, marginBottom:8 }}>Check receipts</Typography>
            <Typography variant="caption" style={{ color:T.textMuted, display:'block', marginBottom:8 }}>
              Does a session that claims done have a real Langfuse trace to back it?
            </Typography>
            <Box display="flex" style={{ gap:6 }}>
              <input aria-label="check receipts session ids" placeholder="session-1, session-2"
                value={receiptsInput} onChange={e => setReceiptsInput(e.target.value)}
                style={{ flex:1, fontSize:12, background:T.surface1, color:T.textPrimary, border:'1px solid #30363d', borderRadius:6, padding:'6px 10px' }} />
              <button type="button" disabled={receiptsLoading} onClick={() => void checkReceipts()}
                aria-label="check receipts"
                style={{ fontSize:12, fontWeight:700, background:T.surface3, color:T.textPrimary, border:'1px solid #30363d', borderRadius:6, padding:'6px 14px', cursor:'pointer' }}>
                {receiptsLoading ? '…' : 'Check'}
              </button>
            </Box>
            {receiptsError && <Typography variant="caption" style={{ color:'#ef4444', display:'block', marginTop:6 }}>{receiptsError}</Typography>}
            {receiptsResults && (
              <ul data-testid="check-receipts-result" style={{ marginTop:8, fontSize:12, color:T.textSecondary, paddingLeft:16 }}>
                {receiptsResults.map(r => (
                  <li key={r.session_id}><strong style={{ color:T.textPrimary }}>{r.session_id}</strong>: {r.verdict} — {r.reason}</li>
                ))}
              </ul>
            )}
          </Box>
        </Box>
      </Section>
    </EstatePage>
  );
}
