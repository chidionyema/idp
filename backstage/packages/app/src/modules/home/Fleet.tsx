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
  type Edge as RFEdge,
  type Node as RFNode,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Chip, EstatePage, Fold, Section, Summary } from '../shell';
import { EstateMap } from './EstateMap';
import {
  attentionReason,
  NUDGEABLE_RUNTIMES,
  summarise,
} from './fleetBoard';
import type { Board, Note, SessionsEnvelope, Signal } from './fleetBoard';
import { ACTIVITY_WORD, ACTIVITY_SENTENCE, motionFor, ringStyleFor, needsAPerson } from './fleetMotion';
import FleetCanvas from './FleetCanvas';
import FleetVoice from './FleetVoice';
import type { Activity } from './fleetMotion';
import type { Activity } from './fleetMotion';

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
  // What voice narrows the fleet to, and which agent it selected. The PAGE owns them so the
  // canvas and the voice bar cannot disagree about what is being shown.
  const [voiceActivity, setVoiceActivity] = useState<Activity | null>(null);
  const [voiceSelected, setVoiceSelected] = useState<string | null>(null);

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
              @keyframes fleet-mic { 0%,100%{box-shadow:0 0 0 0 rgba(239,68,68,.4)} 70%{box-shadow:0 0 0 8px rgba(239,68,68,0)} }
            `}</style>
            {/* THE CANVAS, not a grid of cards. The research was unambiguous: "tables and
                cards force serial reading -- a fleet of 30 agents cannot be READ, it must be
                SEEN." Every agent is a node whose radius is the work it has done, whose pulse
                is the state it is in, and whose ring says whether it is blocked. See
                FleetCanvas.tsx and docs/specs/2026-09-18-fleet-interface-design.md. */}
            <FleetCanvas
              sessions={board.sessions}
              board={board}
              // THE PAGE OWNS THESE TWO, so voice and the canvas are looking at the same truth.
              // Voice cannot narrow a fleet or select an agent if the canvas keeps that state to
              // itself -- which is exactly why FleetVoice was built, tested, and connected to
              // nothing.
              activityFilter={voiceActivity}
              selectedSessionId={voiceSelected}
              onSelectSession={setVoiceSelected}
              // The deck is a CONTROL SURFACE, not a read-only panel: without these the page
              // rendered a canvas whose steer, note and history sections had no data and no
              // destination. Found by a test asserting "not yet read" against a deck that said
              // "No notes or signals yet" -- the props existed on the canvas and nothing passed
              // them.
              signalsBySession={signalsBySession}
              notesBySession={notesBySession}
              onRequestSignals={loadSignals}
              onRequestNotes={loadNotes}
              onSubmitSteer={async (sessionId, runtime, text) => {
                const res = await fetchApi.fetch('plugin://proxy/fleetview/nudge', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ session_id: sessionId, runtime, by: 'founder', text }),
                });
                const body = (await res.json()) as { ok?: boolean; error?: string };
                if (res.ok && body.ok !== false) void loadSignals(sessionId);
                return { ok: res.ok && body.ok !== false, error: body.error ?? `HTTP ${res.status}` };
              }}
              onAddNote={async (sessionId, author, note) => {
                const res = await fetchApi.fetch('plugin://proxy/fleetview/notes', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ session_id: sessionId, note, author }),
                });
                await res.json();
                void loadNotes(sessionId);
              }}
            />

            {/* VOICE. The whole point of it is that a person does not type: they say "what is
                stuck" and the canvas narrows, or "stop <agent>" and the agent is selected with
                the deck open. A mutation NEVER sends -- the deck opens pre-filled and the person
                presses a button they can see, which is the research's "show the target before
                executing" as a hard rule. */}
            <FleetVoice
              sessions={board.sessions}
              onFilter={setVoiceActivity}
              onHighlight={setVoiceSelected}
              onOpenDeck={(sessionId) => setVoiceSelected(sessionId)}
              // ASK THE FLEET. Everything that is not a command goes to the backend, which reads
              // the SAME sessions the board is showing and answers in one or two spoken
              // sentences. This is the join that was missing: the component had no model call at
              // all, so voice could filter the board and answer nothing else.
              onAsk={async (question) => {
                const res = await fetchApi.fetch('plugin://proxy/fleetview/voice', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ question }),
                });
                const body = (await res.json()) as { answer?: string; error?: string; detail?: string };
                if (!res.ok || !body.answer) {
                  throw new Error(body.error ?? `HTTP ${res.status}`);
                }
                return body.answer;
              }}
            />
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
                style={{ flex:1, fontSize:13, background:T.surface1, color:T.textPrimary, border:'1px solid #30363d', borderRadius:6, padding:'6px 10px' }} />
              <button type="button" disabled={blastLoading} onClick={() => void checkBlastRadius()}
                aria-label="check blast radius"
                style={{ fontSize:13, fontWeight:700, background:T.surface3, color:T.textPrimary, border:'1px solid #30363d', borderRadius:6, padding:'6px 14px', cursor:'pointer' }}>
                {blastLoading ? '…' : 'Check'}
              </button>
            </Box>
            {blastError && <Typography variant="caption" style={{ color:'#ef4444', display:'block', marginTop:6 }}>{blastError}</Typography>}
            {blastResult && (
              <div data-testid="blast-radius-result" style={{ marginTop:8, fontSize:13, color:T.textSecondary }}>
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
                style={{ flex:1, fontSize:13, background:T.surface1, color:T.textPrimary, border:'1px solid #30363d', borderRadius:6, padding:'6px 10px' }} />
              <button type="button" disabled={receiptsLoading} onClick={() => void checkReceipts()}
                aria-label="check receipts"
                style={{ fontSize:13, fontWeight:700, background:T.surface3, color:T.textPrimary, border:'1px solid #30363d', borderRadius:6, padding:'6px 14px', cursor:'pointer' }}>
                {receiptsLoading ? '…' : 'Check'}
              </button>
            </Box>
            {receiptsError && <Typography variant="caption" style={{ color:'#ef4444', display:'block', marginTop:6 }}>{receiptsError}</Typography>}
            {receiptsResults && (
              <ul data-testid="check-receipts-result" style={{ marginTop:8, fontSize:13, color:T.textSecondary, paddingLeft:16 }}>
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
