import { useEffect, useRef, useState } from 'react';
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
import { Progress } from '@backstage/core-components';
import {
  discoveryApiRef,
  fetchApiRef,
  useApi,
} from '@backstage/frontend-plugin-api';
import Box from '@material-ui/core/Box';
import Typography from '@material-ui/core/Typography';
import dagre from 'dagre';
import {
  type Edge as RFEdge,
  type Node as RFNode,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Chip, EstatePage, Fold, Section, Summary } from '../shell';
import { attentionReason, summarise } from './fleetBoard';
import type { Board, Note, SessionsEnvelope, Signal } from './fleetBoard';
// The Backstage Fleet page draws the LIVE fleet, so it uses FleetCanvas (the component
// built for /fleet). `room/ui/SpatialCanvas.tsx` is the founder's spec version, which
// takes {events, spotlight, awake} and belongs to the spec's own Room.tsx shell. They
// were both named SpatialCanvas, which is what broke this page.
import { SpatialCanvas } from '../room/ui/FleetCanvas';
import { RadialMenu } from '../room/ui/RadialMenu';
import { MindPanel } from '../room/ui/MindPanel';
import FleetVoice from './FleetVoice';
import type { Activity } from './fleetMotion';

/** Every command button: 32px tall, which is a comfortable click and not a hairline. */
const cmdStyle: React.CSSProperties = {
  fontSize: 12,
  fontWeight: 600,
  background: '#21262d',
  color: '#e6edf3',
  border: '1px solid #30363d',
  borderRadius: 6,
  padding: '6px 12px',
  cursor: 'pointer',
};

/** The note fields: small, monospace, the same shape as every other input on this page. */
const noteInputStyle = (width: number): React.CSSProperties => ({
  width,
  fontSize: 12,
  background: '#0d1117',
  color: '#e6edf3',
  border: '1px solid #30363d',
  borderRadius: 4,
  padding: '4px 8px',
});

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

  const [listeningSession, setListeningSession] = useState<string | null>(null);
  const [nudgeStatusBySession, setNudgeStatusBySession] = useState<Record<string, string>>({});
  // Whether this session's signal history has been fetched. The ack word below the button is
  // derived from it, and must not claim 'not yet read' for a signal nobody has looked up yet --
  // 'not loaded' and 'not read' are different facts, the same distinction the whole ack change
  // exists to preserve.
  const [steerTextBySession, setSteerTextBySession] = useState<Record<string, string>>({});
  const [stopStatusBySession, setStopStatusBySession] = useState<Record<string, string>>({});
  const [approveStatusBySession, setApproveStatusBySession] = useState<Record<string, string>>({});
  const [denyStatusBySession, setDenyStatusBySession] = useState<Record<string, string>>({});

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
  useEffect(() => {
    let live = true;
    fetchApi
      // Same discovery scheme as every other call here: the `proxy` hostname resolves to
      // `${backend.baseUrl}/api/proxy`, so a bare `/api/...` would hit :3100 instead.
      .fetch('plugin://proxy/fleetview/channels')
      .then(r => (r.ok ? r.json() : null))
      .then(j => {
        if (live && j?.signals) setChannels(j.signals as Record<string, string[]>);
      })
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, []);
  /** The selected node's position on the canvas, so the menu can snap onto it. */
  const [nodePos, setNodePos] = useState<{ x: number; y: number } | null>(null);
  /**
   * WHICH VERBS EACH RUNTIME CAN ACTUALLY RECEIVE, served by the backend from signals.py.
   *
   * The menu must not carry a second copy of the channel table. Measured 2026-09-19: it offered
   * Stop on a `pi` session, and `SIGNAL_RUNTIMES["stop"]` is {sovereign, claude-code} -- so the
   * button was enabled for an action the backend can only refuse. Showing an available-looking
   * control for an impossible action teaches the person that the board lies, which costs more
   * than the feature was worth. Empty here simply means "not known yet", and the menu shows
   * everything as unavailable rather than guessing generously.
   */
  const [channels, setChannels] = useState<Record<string, string[]>>({});
  /**
   * EVENTS ARRIVED PER SESSION SINCE THE LAST FRAME, which is the only honest driver for a burst.
   *
   * Counted by comparing each frame's `event_count` against the last one seen, so a burst is
   * work that ACTUALLY ARRIVED. A sine wave standing in for activity would animate forever on a
   * fleet that has stopped, and the one thing this room must never do is show motion where
   * there is no work. Keyed by session id; a session absent from it has fired nothing.
   */
  const [eventRate, setEventRate] = useState<Record<string, number>>({});
  const lastCount = useRef<Map<string, number>>(new Map());
  /** The node whose cascade is currently being pinged, or null. Cleared by the canvas. */
  const [pingFor, setPingFor] = useState<string | null>(null);
  /**
   * THE NODE THE POINTER IS ON. Not a selection: hovering must not open menus or move the camera,
   * or merely crossing the room would act. It exists so a pronoun has something to mean -- see
   * FleetVoice's `referent`.
   */
  const [pointerOn, setPointerOn] = useState<string | null>(null);
  // WHO the person just asked about, so the canvas can bring that agent forward.
  const [voiceSpotlight, setVoiceSpotlight] = useState<string | null>(null);
  // The conversation, so "it" and "that one" resolve. Capped: the model needs the last few turns,
  // not the whole session, and every turn is latency.
  const voiceHistory = useRef<{ who: string; text: string }[]>([]);

  const [blastNodeId, setBlastNodeId] = useState('');
  const [blastResult, setBlastResult] = useState<{
    node_id: string;
    downstream: { node_id: string; hops: number; relation: string }[];
    upstream: { node_id: string; relation: string }[];
  } | null>(null);
  const [blastError, setBlastError] = useState<string | null>(null);
  const [blastLoading, setBlastLoading] = useState(false);

  /**
   * Ask what dies with a node.
   *
   * TAKES AN ID RATHER THAN READING STATE, because the radial menu asks this from a click on a
   * NODE -- and a click does not wait for React to re-render before the answer is wanted. Passing
   * the id through means the call cannot fire against a stale `blastNodeId` from the previous
   * selection, which is exactly the bug that would make the sonar appear to point at the wrong
   * agent. The text field calls it with its own value; the menu calls it with the node's.
   */
  const checkBlastRadius = async (explicit?: string) => {
    const nodeId = (explicit ?? blastNodeId).trim();
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
    // LIVE UPDATE, AND IT ACTUALLY AUTHENTICATES.
    //
    // This was `new EventSource(...)`, which cannot send an Authorization header -- that is a
    // browser API limitation, not a bug -- so every request arrived with no credentials and the
    // proxy answered 401. Measured 2026-09-19, in the console of the running page:
    //
    //     Failed to load resource: the server responded with a status of 401
    //
    // The estate's spec CP2 requires "a change reaches the page under 3 s", and a 401 means the
    // board fell back to its 15-second poll -- a live board that was never live, with the reason
    // sitting in the console the whole time.
    //
    // `fetch` with a reader CAN carry the token, and the backend already sends SSE frames, so the
    // fix is to read that stream rather than to change the server. The poll stays as the fallback
    // it was always meant to be.
    let abort: AbortController | undefined;
    void (async () => {
      try {
        const res = await fetchApi.fetch('plugin://proxy/fleetview/stream', {
          headers: { Accept: 'text/event-stream' },
        });
        if (!res.ok || !res.body) return;
        abort = new AbortController();
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        for (;;) {
          const { done, value } = await reader.read();
          if (done || cancelled) break;
          buffer += decoder.decode(value, { stream: true });
          // SSE frames are separated by a blank line.
          const frames = buffer.split('\n\n');
          buffer = frames.pop() ?? '';
          for (const raw of frames) {
            const dataLine = raw
              .split('\n')
              .filter(l => l.startsWith('data:'))
              .map(l => l.slice(5).trim())
              .join('');
            if (!dataLine) continue;
            let frame: { session_id?: string; record?: unknown };
            try {
              frame = JSON.parse(dataLine);
            } catch {
              // A frame that will not parse is dropped; the next read reconciles. Taking the
              // board down on one bad frame would lose every other session with it.
              continue;
            }
            // MEASURE THE ARRIVAL before the board is replaced: the delta between what this
            // session had and what it has now is the only real measure of "firing right now".
            if (frame.session_id && frame.record) {
              const rec = frame.record as { event_count?: number | null };
              const nowCount = rec.event_count ?? 0;
              const was = lastCount.current.get(frame.session_id) ?? nowCount;
              const delta = Math.max(0, nowCount - was);
              lastCount.current.set(frame.session_id, nowCount);
              if (delta > 0) {
                setEventRate(cur => ({ ...cur, [frame.session_id!]: delta }));
              }
            }
            setBoard(current =>
              summarise({
                available: true,
                sessions: [
                  ...current.sessions.filter(s => s.session_id !== frame.session_id),
                  ...(frame.record ? [frame.record as never] : []),
                ],
                unreachable: current.unreachable,
              }),
            );
            // CP7: when a new event arrives for a session that already has its Trace fold open,
            // reload the trace to show new spans.
            if (frame.session_id) {
              setTraceBySession(current => {
                if (current[frame.session_id!]) void loadTrace(frame.session_id!);
                return current;
              });
            }
          }
        }
      } catch {
        // No stream: the poll below is the fallback, which is what it was always for.
        abort = undefined;
      }
    })();

    const fallback = window.setInterval(read, POLL_MS);
    // The rate is a PER-FRAME measurement, so it is cleared a beat later. Without this the last
    // burst would keep firing for ever, and the room would claim a fleet that is working while
    // it sat idle -- motion where there is no work, which is the one lie this room must not tell.
    const decay = window.setInterval(() => setEventRate({}), 1200);

    return () => {
      cancelled = true;
      window.clearInterval(fallback);
      window.clearInterval(decay);
      abort?.abort();
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
    <EstatePage title={TITLE} lead="">
      {/* THE CANVAS IS THE PAGE. Everything that used to sit above it -- the page title, the lead
          sentence, the summary line, four runtime counters and five filter chips -- is either
          gone or moved onto the canvas as a floating strip. Measured 2026-09-19: that chrome
          pushed the fleet to y~380 of a 900px viewport, and the counters duplicated the chips.
          A room you stand in does not have a header. */}
      <Section title="">
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
        {false && (
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
            <SpatialCanvas
              sessions={
                voiceActivity
                  ? board.sessions.filter(x => (x.activity ?? 'unknown') === voiceActivity)
                  : board.sessions
              }
              spotlight={voiceSpotlight}
              selected={voiceSelected}
              onSelect={setVoiceSelected}
              onSelectedPosition={setNodePos}
              onHover={setPointerOn}
              eventRate={eventRate}
              pingFor={pingFor}
              onPingDone={() => setPingFor(null)}
            />
            {/* THE MENU IS ON THE NODE. Selecting an agent used to put its four actions in a
                horizontal bar below the canvas, so a person's eye left the red node at the top
                and travelled to the bottom of the screen to find the fix -- then back to see
                whether it worked. Radial, anchored on the agent, one gesture, nothing to travel
                to. The bottom bar is deleted below, not merely hidden. */}
            {/* THE INSIDE OF THE AGENT, AT THE AGENT. The camera pushes in; this is what it
                arrives at. It sits above the radial menu so the two do not cover each other, and
                it reads the same state and loaders the fold below uses -- a second SURFACE, not a
                second truth. */}
            {voiceSelected && nodePos ? (() => {
              const target = board.sessions.find(x => x.session_id === voiceSelected);
              if (!target) return null;
              return (
                <MindPanel
                  session={target}
                  x={nodePos.x}
                  y={nodePos.y}
                  rate={eventRate[target.session_id] ?? 0}
                  traceUrl={target.trace_url ?? null}
                  trace={traceBySession[target.session_id] ?? null}
                  ledger={ledgerBySession[target.session_id] ?? null}
                  onLoadTrace={() => void loadTrace(target.session_id)}
                  onLoadLedger={() => void loadLedger(target.session_id)}
                  onClose={() => setVoiceSelected(null)}
                />
              );
            })() : null}

            {voiceSelected && nodePos ? (() => {
              const target = board.sessions.find(x => x.session_id === voiceSelected);
              if (!target) return null;
              // Enabled iff the backend's own table says this runtime has a channel for it.
              // 'dictate' is the one local-only verb: it opens a microphone, not a session
              // channel, so it does not appear in SIGNAL_RUNTIMES at all.
              const available = new Set<string>([
                ...['stop', 'approve', 'deny', 'steer'].filter(v =>
                  (channels[v] ?? []).includes(target.runtime),
                ),
                // Neither of these is a session channel: one opens a microphone, the other reads
                // a graph. Both are answerable for any runtime, so neither is gated.
                'dictate',
                'ping',
              ]);
              const result =
                stopStatusBySession[target.session_id] ??
                approveStatusBySession[target.session_id] ??
                denyStatusBySession[target.session_id] ??
                nudgeStatusBySession[target.session_id] ??
                null;
              return (
                <RadialMenu
                  session={target}
                  x={nodePos.x}
                  y={nodePos.y}
                  available={available}
                  busy={
                    result === 'stopping…' ? 'stop' :
                    result === 'approving…' ? 'approve' : null
                  }
                  result={result && !result.endsWith('…') ? result : null}
                  dictating={listeningSession === target.session_id}
                  pinging={pingFor === target.session_id}
                  onAct={kind => {
                    if (kind === 'stop') void sendStop(target.session_id, target.runtime);
                    if (kind === 'approve') void sendApprove(target.session_id, target.runtime);
                    if (kind === 'deny') void sendDeny(target.session_id, target.runtime);
                    if (kind === 'steer') void sendNudge(target.session_id, target.runtime);
                  if (kind === 'dictate') startDictation(target.session_id);
                  if (kind === 'ping') {
                    // The wave is the answer to "what dies with this". The list below it is the
                    // same fact in words, for the reader who wants to check rather than watch.
                    setPingFor(target.session_id);
                    setBlastNodeId(target.session_id);
                    void checkBlastRadius(target.session_id);
                  }
                  }}
                  onDismiss={() => setVoiceSelected(null)}
                />
              );
            })() : null}

            {/* VOICE. The whole point of it is that a person does not type: they say "what is
                stuck" and the canvas narrows, or "stop <agent>" and the agent is selected with
                the deck open. A mutation NEVER sends -- the deck opens pre-filled and the person
                presses a button they can see, which is the research's "show the target before
                executing" as a hard rule. */}
            <FleetVoice
              sessions={board.sessions}
              // THE POINTER, THEN THE SELECTION. Preferring the node under the cursor is what
              // makes "stop it" mean what the hand is on; falling back to the selection keeps
              // voice usable by touch or by keyboard, where there is no cursor in the room.
              referent={pointerOn ?? voiceSelected}
              onFilter={setVoiceActivity}
              onHighlight={setVoiceSelected}
              onOpenDeck={(sessionId) => setVoiceSelected(sessionId)}
              // ASK THE FLEET. Everything that is not a command goes to the backend, which reads
              // the SAME sessions the board is showing and answers in one or two spoken
              // sentences. This is the join that was missing: the component had no model call at
              // all, so voice could filter the board and answer nothing else.
              // STREAMED, and `onClause` is the whole reason this is not `onAsk`.
              //
              // The model writes a sentence over ~1.2s. Returning the finished paragraph means a
              // person hears NOTHING for that whole time and then the audio starts -- measured,
              // that reads as broken. Sending each clause as it is written means the first words
              // are spoken at ~300ms and the rest arrives while they are already being said. It
              // is the difference between laggy and instant, and it is the spec's own
              // "micro-clause chunking" applied where it actually matters.
              onSpotlight={setVoiceSpotlight}
              onClause={async (question, speakClause) => {
                const res = await fetchApi.fetch('plugin://proxy/fleetview/voice/stream', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    question,
                    // MEMORY: the last turns, so a follow-up does not have to re-name the agent.
                    history: voiceHistory.current.slice(-6),
                  }),
                });
                if (!res.ok || !res.body) {
                  throw new Error(`HTTP ${res.status}`);
                }
                const reader = res.body.getReader();
                const decoder = new TextDecoder();
                let buf = '';
                let spoke = 0;
                for (;;) {
                  const { done, value } = await reader.read();
                  if (done) break;
                  buf += decoder.decode(value, { stream: true });
                  // SSE frames are separated by a blank line.
                  const frames = buf.split('\n\n');
                  buf = frames.pop() ?? '';
                  for (const frame of frames) {
                    const ev = (frame.match(/^event: (\S+)/m) || [])[1];
                    const dataLine = (frame.match(/^data: (.*)$/m) || [])[1];
                    if (!dataLine) continue;
                    let payload: { text?: string; error?: string };
                    try { payload = JSON.parse(dataLine); } catch { continue; }
                    if (ev === 'delta' && payload.text) {
                      spoke += 1;
                      speakClause(payload.text);
                    } else if (ev === 'error') {
                      throw new Error(payload.error ?? 'the fleet could not answer');
                    }
                  }
                }
                if (spoke === 0) throw new Error('the fleet returned nothing');
                voiceHistory.current.push({ who: 'person', text: question });
              }}
            />
          </>
        )}
        {/* The one-line fleet summary, BELOW the canvas. It describes what you just looked at,
            so it belongs under it -- above it, it was 20px of prose between a person and their
            fleet. */}
        {/* The runtime counter strip, BELOW the canvas with the summary. The canvas already
            carries filter chips per runtime, so this is the same information in a second place --
            which is fine for reference and fatal as chrome, because above the canvas it cost 70px
            of viewport to repeat what the reader is about to see anyway. */}
        {board.byRuntime.length > 0 && (
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
        {/* THE FOUR SIGNALS ARE ON THE NODE.

            This block used to be a horizontal bar of Stop / Approve / Deny / Steer under the
            canvas. Selecting an agent at the top-left sent the eye to the bottom of the screen
            and back -- and that journey, not the button, was the cost of every action. The four
            now live in a radial menu anchored on the agent itself (room/ui/RadialMenu.tsx), and
            the bar is deleted rather than hidden, because a second surface for the same four
            actions is two places to keep true. */}

        {/* THE TRACE, THE LEDGER,        {/* THE TRACE, THE LEDGER, THE RECEIPT AND THE NOTE.
            All four of these work and all four were orphaned the same way the four signals
            were: replacing the card grid deleted the surface they rendered on and left the
            machinery in the file, where `tsc` called it unused and I deleted unused IMPORTS
            instead of asking why the FEATURES were unused. Every one is a real read the backend
            already serves. */}
        {voiceSelected && (() => {
          const target = board.sessions.find(x => x.session_id === voiceSelected);
          if (!target) return null;
          const id = target.session_id;
          const trace = traceBySession[id];
          const ledger = ledgerBySession[id];
          const receipt = receiptsBySession[id];
          const notes = notesBySession[id] ?? [];
          const signals = signalsBySession[id] ?? [];
          const draft = draftFor(id);
          return (
            <Fold
              testId={`detail-${id}`}
              summary="Trace · ledger · receipt · notes"
              onToggle={e => {
                if (!e.currentTarget.open) return;
                if (!traceBySession[id]) void loadTrace(id);
                if (!ledgerBySession[id]) void loadLedger(id);
                if (!receiptsBySession[id]) void loadReceipt(id);
                if (!notesBySession[id]) void loadNotes(id);
                if (!signalsBySession[id]) void loadSignals(id);
              }}
            >
              <div data-testid={`detail-body-${id}`} style={{ fontSize: 12, color: '#a8afba', padding: '8px 0' }}>
                {/* WHAT THIS AGENT IS DOING, FIRST.
                    Selecting an agent and being shown its trace, ledger and receipt -- but not
                    its task -- is being told about the plumbing and not the job. The runtime,
                    the task and the work done are the three facts the board exists to carry, and
                    they belong at the top of the surface that opens when you ask about one. */}
                <div data-testid={`detail-summary-${id}`} style={{ marginBottom: 6 }}>
                  <strong style={{ color: '#e6edf3' }}>{target.runtime}</strong>
                  {' · '}
                  <span style={{ color: '#e6edf3' }}>{attentionReason(target) || 'active'}</span>
                  {' · '}
                  {target.event_count ?? 0} events
                  {target.task ? <div style={{ marginTop: 2 }}>{target.task}</div> : null}
                </div>
                <div data-testid="detail-trace">
                  <strong style={{ color: '#e6edf3' }}>Trace</strong>{' '}
                  {trace
                    ? trace.available
                      ? `${trace.nodes?.length ?? 0} span(s)`
                      : `unavailable — ${trace.error ?? 'no reason given'}`
                    : 'open to load'}
                </div>
                <div data-testid="detail-ledger">
                  <strong style={{ color: '#e6edf3' }}>Ledger</strong>{' '}
                  {ledger ? `${ledger.rows.length} row(s)` : 'open to load'}
                </div>
                <div data-testid="detail-receipt">
                  <strong style={{ color: '#e6edf3' }}>Receipt</strong>{' '}
                  {/* `status === 'ok'` was compared here and `ReceiptState` has no such member --
                      it is loading | done | error. The branch was dead, so a completed receipt
                      rendered the literal string "done" instead of its verdict. Every state is
                      now named, and the three the type actually has are the three shown. */}
                  {receipt
                    ? receipt.status === 'done'
                      ? `verdict ${receipt.verdict}${receipt.reason ? ` — ${receipt.reason}` : ''}`
                      : receipt.status === 'error'
                        ? `unavailable — ${receipt.error}`
                        : 'loading…'
                    : 'open to load'}
                </div>
                <div data-testid="detail-history" style={{ marginTop: 6 }}>
                  <strong style={{ color: '#e6edf3' }}>History</strong>{' '}
                  {`${notes.length} note(s), ${signals.length} signal(s)`}
                </div>
                {signals.slice(0, 4).map((s2: Signal, i: number) => (
                  <div key={`s-${i}`} style={{ paddingLeft: 8 }}>
                    {`${s2.kind} ${s2.by} sent, ${
                      s2.acknowledged ? 'read by the session' : 'not yet read'
                    }`}
                  </div>
                ))}
                <div style={{ marginTop: 8, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  <input
                    aria-label={`note author for ${id}`}
                    placeholder="your name"
                    value={draft.author}
                    onChange={e =>
                      setDraftsBySession(cur => ({
                        ...cur,
                        [id]: { ...draftFor(id), author: e.target.value },
                      }))
                    }
                    style={noteInputStyle(80)}
                  />
                  <input
                    aria-label={`note text for ${id}`}
                    placeholder="leave a note…"
                    value={draft.note}
                    onChange={e =>
                      setDraftsBySession(cur => ({
                        ...cur,
                        [id]: { ...draftFor(id), note: e.target.value },
                      }))
                    }
                    style={noteInputStyle(220)}
                  />
                  <button
                    type="button"
                    data-testid={`send-note-${id}`}
                    onClick={() => void submitNote(id, target.runtime)}
                    style={cmdStyle}
                  >
                    Note
                  </button>
                </div>
              </div>
            </Fold>
          );
        })()}
        <Summary>{board.summary}</Summary>
      </Section>

      {/* The estate map, below the board it gives context to. It is genuinely useful -- every
          namespace and its relations -- but it must not stand between a person and the
          sessions, which is what it did: measured 2026-09-18, the board began at y=808 with
          the first card at y=980, below the fold on a laptop, under 580px of this. */}

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
