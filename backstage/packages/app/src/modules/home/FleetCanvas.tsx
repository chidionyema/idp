import React, {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  Button,
  IconButton,
  TextField,
  Tooltip,
} from '@mui/material';
import { capabilityLabel, NUDGEABLE_RUNTIMES, stateLabel } from './fleetBoard';
import type { Note, Session, Signal } from './fleetBoard';
import { ACTIVITY_WORD } from './fleetMotion';
import type { Activity } from './fleetMotion';

/* ------------------------------------------------------------------------------------------------
 * FleetCanvas v2 — the fleet as a live canvas AND a control surface.
 *
 * Two jobs, one file. The canvas answers "what is the fleet doing right now" at a glance; the
 * command deck answers "and what do I do about it" without leaving the picture. They share the
 * same selection state, which is why they live together: a panel that opens somewhere else on the
 * page is a second screen, and a second screen is where attention goes to die.
 *
 * Everything here is deterministic given the data. The force layout is seeded from the session-id
 * set, so the same fleet draws the same picture on every poll -- a fleet that rearranges itself
 * every three seconds is unreadable, and unreadable is the same as absent.
 * ---------------------------------------------------------------------------------------------- */

/* ------------------------------------------------------------------------------------------------
 * Types
 * ---------------------------------------------------------------------------------------------- */

export interface FleetCanvasProps {
  sessions: Session[];
  board: { state: string; summary?: string; sessions: Session[] };
  onSubmitSteer?: (
    sessionId: string,
    runtime: string,
    text: string,
  ) => Promise<{ ok: boolean; error?: string }>;
  onAddNote?: (sessionId: string, author: string, note: string) => Promise<void>;
  signalsBySession?: Record<string, Signal[]>;
  notesBySession?: Record<string, Note[]>;
  onRequestSignals?: (sessionId: string) => void;
  onRequestNotes?: (sessionId: string) => void;
  /**
   * CONTROLLABLE FROM OUTSIDE. The canvas owned these two pieces of state, so NOTHING could drive
   * it -- which is why FleetVoice was built, tested and connected to nothing: voice had no way to
   * narrow the fleet or select an agent. Both are now props with the internal state as the
   * default, the standard controlled/uncontrolled pattern: pass a value and the canvas follows it.
   */
  activityFilter?: Activity | null;
  selectedSessionId?: string | null;
  /**
   * THE SPOTLIGHT. A session id that is drawn LARGE, centred, and pulled forward of the fleet.
   *
   * This is the interaction that makes the canvas something other than a chart. Saying "show me
   * pi" detaches that node from the swarm, glides it to the middle at ~3x, dims everything else,
   * and the deck beside it speaks that agent's real state. You do not find the agent on a grid;
   * the agent comes to you.
   *
   * Kept separate from `selectedSessionId` on purpose: selecting opens the deck (a table of
   * facts), spotlighting is the presentation (the agent is brought forward). A caller can do one
   * without the other.
   */
  spotlightSessionId?: string | null;
  /** Fired when the reader selects a node, so a parent can mirror the selection for voice. */
  onSelectSession?: (sessionId: string | null) => void;
  onRequestReceipt?: (
    sessionId: string,
  ) => { status: string; verdict?: string; reason?: string } | undefined;
}

/* ------------------------------------------------------------------------------------------------
 * Tokens. Sizes are 11/12/13/14/16 only; spacing is 4/8/12/16/24/32/48 only; radii are 4/8/999
 * only. These are not suggestions -- a canvas that invents a 15px label reads as a different
 * product from the page it sits on.
 * ---------------------------------------------------------------------------------------------- */

const T = {
  bg: '#0b0d10',
  surface: '#12151a',
  surface2: '#171b21',
  border: '#242a33',
  textPrimary: '#e6e9ee',
  textMuted: '#8b93a1',
  accent: '#5b9dff',
  green: '#22c55e',
  amber: '#f59e0b',
  red: '#ef4444',
  violet: '#a78bfa',
} as const;

const FONT_MONO =
  'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace';

/* ------------------------------------------------------------------------------------------------
 * Deterministic randomness.
 *
 * The layout must be a pure function of the data. Math.random() would give a different picture on
 * every render, and a picture that changes when nothing changed teaches the reader to ignore it.
 * hashString() seeds makeRng() from the session-id set, so the same fleet always lands the same
 * way -- and a fleet that gains one agent only moves that agent.
 * ---------------------------------------------------------------------------------------------- */

function hashString(s: string): number {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < s.length; i += 1) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function makeRng(seed: number): () => number {
  let a = seed >>> 0;
  return function next(): number {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/* ------------------------------------------------------------------------------------------------
 * Activity vocabulary.
 *
 * `activity` is the four-state field derived server-side from evidence; `state` is elapsed-time
 * only and cannot tell a thinking agent from a wedged one. The canvas draws activity, and falls
 * back to `unknown` when the field is absent -- a node that breathes when nobody knows whether it
 * is alive is the same lie as a green dot.
 * ---------------------------------------------------------------------------------------------- */

type Activity = 'thinking' | 'waiting' | 'stuck' | 'finished' | 'unknown';

function activityOf(s: Session): Activity {
  const a = s.activity;
  if (a === 'thinking' || a === 'waiting' || a === 'stuck' || a === 'finished') return a;
  return 'unknown';
}

function activityColor(a: Activity): string {
  switch (a) {
    case 'thinking':
      return T.accent;
    case 'waiting':
      return T.amber;
    case 'stuck':
      return T.red;
    case 'finished':
      return T.green;
    default:
      return T.textMuted;
  }
}

/** The four motions from styles.css. Reused, never redefined -- the keyframes live in one place. */
function activityMotion(a: Activity): string {
  switch (a) {
    case 'thinking':
      return 'fleet-breathe 4s ease-in-out infinite';
    case 'waiting':
      return 'fleet-drift 6s ease-in-out infinite';
    case 'stuck':
      return 'fleet-jitter .125s steps(2, end) infinite';
    default:
      return 'none';
  }
}

/* ------------------------------------------------------------------------------------------------
 * Geometry helpers.
 * ---------------------------------------------------------------------------------------------- */

type Pt = { x: number; y: number };

type LaidOutNode = {
  session: Session;
  activity: Activity;
  x: number;
  y: number;
  r: number;
  /** 0..1 share of today's spend across the visible fleet. Drives the temperature arc. */
  spendShare: number;
  /** 0..1 activity level, drives the ring. */
  level: number;
};

type RepoEdge = {
  key: string;
  repo: string;
  a: LaidOutNode;
  b: LaidOutNode;
  /** Combined throughput of the two endpoints -- particle speed. */
  throughput: number;
  /** How many agents sit on this repo -- particle density. */
  density: number;
};

/** Radius: 18 at zero events, 42 at 200+. Saturating, so a runaway agent does not eat the canvas. */
function radiusFor(eventCount: number | null | undefined): number {
  // FILL THE ROOM. Measured 2026-09-19: nodes occupied 13% of the canvas, so the fleet read as
  // scattered dots on a black rectangle rather than something alive. 18..42 became 34..110 --
  // roughly three times the area -- and the curve is sqrt rather than linear because a linear map
  // makes one busy agent 5x the radius of a quiet one, which reads as a size bug rather than as
  // work done. Area should grow with events; sqrt is what makes AREA proportional.
  const n = typeof eventCount === 'number' && Number.isFinite(eventCount) ? eventCount : 0;
  // 34..92, not 34..110: measured 2026-09-19 a 345px node sat beside a 103px one and the
  // spread read as a fault. sqrt keeps AREA proportional to events; the ceiling keeps
  // the biggest agent legible next to the smallest.
  return 34 + 58 * Math.sqrt(Math.min(1, Math.max(0, n) / 400));
}

/** Activity level 0..1 from event_count, used for the ring opacity. */
function levelFor(eventCount: number | null | undefined): number {
  const n = typeof eventCount === 'number' && Number.isFinite(eventCount) ? eventCount : 0;
  return Math.min(1, Math.max(0, n) / 200);
}

/** Spend temperature: green -> amber -> red by share of the day's spend. */
function temperatureColor(share: number): string {
  if (share <= 0.33) return T.green;
  if (share <= 0.66) return T.amber;
  return T.red;
}

function arcPath(cx: number, cy: number, r: number, sweep: number): string {
  const clamped = Math.max(0, Math.min(1, sweep));
  if (clamped <= 0) return '';
  const start = -Math.PI / 2;
  const end = start + clamped * Math.PI * 2;
  const x1 = cx + r * Math.cos(start);
  const y1 = cy + r * Math.sin(start);
  const x2 = cx + r * Math.cos(end);
  const y2 = cy + r * Math.sin(end);
  const large = clamped > 0.5 ? 1 : 0;
  return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`;
}

/* ------------------------------------------------------------------------------------------------
 * Formatting. A missing value is `—`, never `0` and never `$0.00`. The distinction matters: an
 * agent that spent nothing and an agent whose spend we cannot read are different facts, and
 * collapsing them hides the second one.
 * ---------------------------------------------------------------------------------------------- */

const DASH = '—';

function fmtSpend(v: number | null | undefined): string {
  if (typeof v !== 'number' || !Number.isFinite(v)) return DASH;
  return `$${v.toFixed(2)}`;
}

function fmtCount(v: number | null | undefined): string {
  if (typeof v !== 'number' || !Number.isFinite(v)) return DASH;
  return String(v);
}

function fmtText(v: string | null | undefined): string {
  if (typeof v !== 'string' || v.length === 0) return DASH;
  return v;
}

function fmtPRs(v: string[] | null | undefined): string {
  if (!Array.isArray(v) || v.length === 0) return DASH;
  return v.join(', ');
}

function relTime(iso: string | null | undefined): string {
  if (typeof iso !== 'string' || iso.length === 0) return DASH;
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return DASH;
  const secs = Math.max(0, Math.round((Date.now() - t) / 1000));
  if (secs < 60) return `${secs}s`;
  const mins = Math.round(secs / 60);
  if (mins < 60) return `${mins}m`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h`;
  return `${Math.round(hours / 24)}d`;
}

/* ------------------------------------------------------------------------------------------------
 * Layout.
 *
 * A seeded force relaxation. O(n^2) per iteration is fine at 23 nodes and still fine at 200 with
 * the iteration cap; the point is that it runs ONCE per (session-id set, container size), never
 * per frame. The result is memoised and the render loop only reads it.
 * ---------------------------------------------------------------------------------------------- */

function layoutFleet(
  sessions: Session[],
  width: number,
  height: number,
): { nodes: LaidOutNode[]; edges: RepoEdge[] } {
  if (sessions.length === 0 || width <= 0 || height <= 0) {
    return { nodes: [], edges: [] };
  }

  const seed = hashString(sessions.map((s) => s.session_id).join('|'));
  const rng = makeRng(seed);

  // THE PAD IS THE LARGEST NODE, NOT A CONSTANT. It was 48px, written when a node's max radius
  // was 42. Measured 2026-09-19 after the nodes grew to 110px: FIVE OF TWENTY-FOUR were cut off
  // at the edges, because a fixed margin cannot contain a size that changed. Deriving it from the
  // actual largest radius means this cannot silently rot again when the sizes move -- which is
  // the failure mode a constant always has.
  const largest = sessions.reduce(
    (m, s) => Math.max(m, radiusFor(s.event_count)),
    0,
  );
  const pad = Math.max(24, largest + 18);
  const innerW = Math.max(1, width - pad * 2);
  const innerH = Math.max(1, height - pad * 2);

  // Seed positions on a jittered grid so the relaxation starts spread out rather than piled.
  const cols = Math.max(1, Math.ceil(Math.sqrt(sessions.length)));
  const rows = Math.max(1, Math.ceil(sessions.length / cols));

  const totalSpend = sessions.reduce((acc, s) => {
    const v = typeof s.spend_usd === 'number' && Number.isFinite(s.spend_usd) ? s.spend_usd : 0;
    return acc + v;
  }, 0);

  const nodes: LaidOutNode[] = sessions.map((s, i) => {
    const col = i % cols;
    const row = Math.floor(i / cols);
    const jx = (rng() - 0.5) * (innerW / cols) * 0.6;
    const jy = (rng() - 0.5) * (innerH / rows) * 0.6;
    const x = pad + ((col + 0.5) / cols) * innerW + jx;
    const y = pad + ((row + 0.5) / rows) * innerH + jy;
    const spend = typeof s.spend_usd === 'number' && Number.isFinite(s.spend_usd) ? s.spend_usd : 0;
    return {
      session: s,
      activity: activityOf(s),
      x,
      y,
      r: radiusFor(s.event_count),
      spendShare: totalSpend > 0 ? spend / totalSpend : 0,
      level: levelFor(s.event_count),
    };
  });

  // Relaxation: repulsion between all pairs, weak centring, and a hard clamp to the box.
  const iterations = sessions.length > 120 ? 60 : 140;
  const centreX = width / 2;
  const centreY = height / 2;

  for (let it = 0; it < iterations; it += 1) {
    const cooling = 1 - it / iterations;
    for (let i = 0; i < nodes.length; i += 1) {
      const a = nodes[i];
      let fx = 0;
      let fy = 0;
      for (let j = 0; j < nodes.length; j += 1) {
        if (i === j) continue;
        const b = nodes[j];
        let dx = a.x - b.x;
        let dy = a.y - b.y;
        let d2 = dx * dx + dy * dy;
        if (d2 < 0.01) {
          dx = (rng() - 0.5) * 2;
          dy = (rng() - 0.5) * 2;
          d2 = dx * dx + dy * dy;
        }
        const d = Math.sqrt(d2);
        const minGap = a.r + b.r + 16;
        const force = ((minGap * minGap) / d2) * 0.9;
        fx += (dx / d) * force;
        fy += (dy / d) * force;
      }
      // Weak pull to centre keeps the cloud from drifting off the canvas.
      fx += (centreX - a.x) * 0.004;
      fy += (centreY - a.y) * 0.004;
      a.x += fx * cooling * 8;
      a.y += fy * cooling * 8;
      a.x = Math.max(pad, Math.min(width - pad, a.x));
      a.y = Math.max(pad, Math.min(height - pad, a.y));
    }
  }

  // Repo edges: agents sharing a repo are joined. One edge per repo pair, not per agent pair --
  // a repo with six agents is one thick flow, not fifteen lines.
  const byRepo = new Map<string, LaidOutNode[]>();
  for (const n of nodes) {
    const repo = n.session.repo;
    if (typeof repo !== 'string' || repo.length === 0) continue;
    const list = byRepo.get(repo);
    if (list) list.push(n);
    else byRepo.set(repo, [n]);
  }

  const edges: RepoEdge[] = [];
  byRepo.forEach((members, repo) => {
    if (members.length < 2) return;
    // Star topology from the first member: keeps edge count linear in agents, not quadratic.
    const hub = members[0];
    for (let i = 1; i < members.length; i += 1) {
      const other = members[i];
      const throughput =
        (hub.session.event_count ?? 0) + (other.session.event_count ?? 0);
      edges.push({
        key: `${repo}:${hub.session.session_id}:${other.session.session_id}`,
        repo,
        a: hub,
        b: other,
        throughput,
        density: members.length,
      });
    }
  });

  return { nodes, edges };
}

/* ------------------------------------------------------------------------------------------------
 * The command deck.
 * ---------------------------------------------------------------------------------------------- */

type SteerState = 'idle' | 'sending' | 'sent' | 'failed';

type DeckProps = {
  session: Session;
  anchor: Pt;
  containerWidth: number;
  containerHeight: number;
  signals: Signal[];
  notes: Note[];
  onSubmitSteer?: FleetCanvasProps['onSubmitSteer'];
  onAddNote?: FleetCanvasProps['onAddNote'];
  onRequestSignals?: FleetCanvasProps['onRequestSignals'];
  onRequestNotes?: FleetCanvasProps['onRequestNotes'];
  onRequestReceipt?: FleetCanvasProps['onRequestReceipt'];
  onClose: () => void;
};

const DECK_WIDTH = 360;

function CommandDeck(props: DeckProps): JSX.Element {
  const {
    session,
    anchor,
    containerWidth,
    containerHeight,
    signals,
    notes,
    onSubmitSteer,
    onAddNote,
    onRequestSignals,
    onRequestNotes,
    onRequestReceipt,
    onClose,
  } = props;

  const activity = activityOf(session);

  const [steerText, setSteerText] = useState('');
  const [steerState, setSteerState] = useState<SteerState>('idle');
  const [steerError, setSteerError] = useState<string | null>(null);
  const [emptyWarn, setEmptyWarn] = useState(false);
  const [listening, setListening] = useState(false);
  const [noteAuthor, setNoteAuthor] = useState('');
  const [noteText, setNoteText] = useState('');
  const [noteBusy, setNoteBusy] = useState(false);
  /** Why a note was refused. A silent no-op reads as a broken button. */
  const [noteWarn, setNoteWarn] = useState<string | null>(null);
  const [taskExpanded, setTaskExpanded] = useState(false);
  const [receipt, setReceipt] = useState<
    { status: string; verdict?: string; reason?: string } | undefined
  >(undefined);
  const [receiptFetched, setReceiptFetched] = useState(false);

  const recognitionRef = useRef<any>(null);
  const sentTimerRef = useRef<number | null>(null);
  const emptyTimerRef = useRef<number | null>(null);

  // Ask for the timeline once, on open. The parent owns the data; we own the request.
  useEffect(() => {
    if (onRequestSignals) onRequestSignals(session.session_id);
    if (onRequestNotes) onRequestNotes(session.session_id);
  }, [onRequestSignals, onRequestNotes, session.session_id]);

  // Receipt is fetched on first open only. A verdict is evidence, and evidence does not change
  // because the panel was reopened.
  useEffect(() => {
    if (receiptFetched) return;
    setReceiptFetched(true);
    if (onRequestReceipt) {
      setReceipt(onRequestReceipt(session.session_id));
    } else {
      setReceipt(undefined);
    }
  }, [onRequestReceipt, session.session_id, receiptFetched]);

  useEffect(() => {
    return () => {
      if (sentTimerRef.current !== null) window.clearTimeout(sentTimerRef.current);
      if (emptyTimerRef.current !== null) window.clearTimeout(emptyTimerRef.current);
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {
          /* recognition already stopped */
        }
      }
    };
  }, []);

  const speechAvailable =
    typeof window !== 'undefined' &&
    typeof (window as any).webkitSpeechRecognition === 'function';

  const startListening = useCallback(() => {
    if (!speechAvailable) return;
    const Ctor = (window as any).webkitSpeechRecognition;
    const rec = new Ctor();
    rec.continuous = false;
    rec.interimResults = true;
    rec.lang = 'en-US';
    rec.onresult = (ev: any) => {
      let transcript = '';
      for (let i = ev.resultIndex; i < ev.results.length; i += 1) {
        transcript += ev.results[i][0].transcript;
      }
      setSteerText((prev) => (prev ? `${prev} ${transcript}` : transcript));
    };
    rec.onerror = () => setListening(false);
    rec.onend = () => setListening(false);
    recognitionRef.current = rec;
    setListening(true);
    try {
      rec.start();
    } catch {
      setListening(false);
    }
  }, [speechAvailable]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        /* already stopped */
      }
    }
    setListening(false);
  }, []);

  const submitSteer = useCallback(async () => {
    const text = steerText.trim();
    if (text.length === 0) {
      // An empty steer must not silently no-op -- the reader would believe it was sent.
      setEmptyWarn(true);
      if (emptyTimerRef.current !== null) window.clearTimeout(emptyTimerRef.current);
      emptyTimerRef.current = window.setTimeout(() => setEmptyWarn(false), 3000);
      return;
    }
    if (!onSubmitSteer) {
      setSteerState('failed');
      setSteerError('No steer channel is wired up.');
      return;
    }
    setSteerState('sending');
    setSteerError(null);
    try {
      const res = await onSubmitSteer(session.session_id, session.runtime, text);
      if (res && res.ok) {
        setSteerState('sent');
        setSteerText('');
        if (sentTimerRef.current !== null) window.clearTimeout(sentTimerRef.current);
        sentTimerRef.current = window.setTimeout(() => setSteerState('idle'), 2000);
      } else {
        setSteerState('failed');
        setSteerError(res && res.error ? res.error : 'Steer was rejected.');
      }
    } catch (err) {
      setSteerState('failed');
      setSteerError(err instanceof Error ? err.message : 'Steer failed.');
    }
  }, [steerText, onSubmitSteer, session.session_id, session.runtime]);

  const submitNote = useCallback(async () => {
    const text = noteText.trim();
    const author = noteAuthor.trim();
    // A NOTE WITH NO NAME IS NOT SENT, and it is not silently attributed either. The generated
    // canvas defaulted a blank author to 'operator', which writes a HUMAN's note into the audit
    // trail under a robot's name -- worse than refusing, because the trail is what a reader
    // trusts. The card required a name; this keeps that rule and says why, rather than posting
    // and looking like it worked.
    if (text.length === 0) {
      setNoteWarn('Write the note first.');
      return;
    }
    if (author.length === 0) {
      setNoteWarn('Add your name — an unattributed note is not worth keeping.');
      return;
    }
    if (!onAddNote) return;
    setNoteWarn(null);
    setNoteBusy(true);
    try {
      await onAddNote(session.session_id, author, text);
      setNoteText('');
      if (onRequestNotes) onRequestNotes(session.session_id);
    } finally {
      setNoteBusy(false);
    }
  }, [noteText, noteAuthor, onAddNote, session.session_id, onRequestNotes]);

  // Position: prefer the right of the node, flip left when there is no room, clamp vertically.
  const gap = 24;
  const preferRight = anchor.x + gap + DECK_WIDTH <= containerWidth - 8;
  const left = preferRight
    ? anchor.x + gap
    : Math.max(8, anchor.x - gap - DECK_WIDTH);
  const top = Math.max(8, Math.min(containerHeight - 200, anchor.y - 80));

  // Merged timeline, newest first. Notes and signals are different facts and stay labelled.
  const timeline = useMemo(() => {
    type Row = { key: string; at: number; node: JSX.Element };
    const rows: Row[] = [];
    signals.forEach((sig, i) => {
      const at = sig.created_at ? Date.parse(sig.created_at) : 0;
      const when = Number.isFinite(at) ? at : 0;
      let line: string;
      if (sig.error) {
        line = `${sig.kind} ${sig.by ?? 'operator'} failed: ${sig.error}`;
      } else if (sig.acknowledged) {
        line = `${sig.kind} ${sig.by ?? 'operator'} sent, read by the session`;
      } else {
        // NEVER "delivered" for an unread steer. Delivered is a claim about the reader.
        line = `${sig.kind} ${sig.by ?? 'operator'} sent, not yet read`;
      }
      rows.push({
        key: `sig-${sig.id ?? i}`,
        at: when,
        node: (
          <div
            key={`sig-${sig.id ?? i}`}
            style={{
              fontSize: 12,
              lineHeight: 1.5,
              color: sig.error ? T.red : T.textMuted,
              padding: '4px 0',
              borderBottom: `1px solid ${T.border}`,
            }}
          >
            {line}
          </div>
        ),
      });
    });
    notes.forEach((note, i) => {
      const at = note.created_at ? Date.parse(note.created_at) : 0;
      const when = Number.isFinite(at) ? at : 0;
      rows.push({
        key: `note-${note.id ?? i}`,
        at: when,
        node: (
          <div
            key={`note-${note.id ?? i}`}
            style={{
              fontSize: 12,
              lineHeight: 1.5,
              color: T.textPrimary,
              padding: '4px 0',
              borderBottom: `1px solid ${T.border}`,
            }}
          >
            <span style={{ color: T.textMuted }}>note {note.author ?? 'operator'}: </span>
            {note.note}
          </div>
        ),
      });
    });
    // OLDEST FIRST, matching fleetBoard.timelineFor's own contract: "one chronological read of
    // what happened to a session, oldest first". The generated canvas reversed this, so a reader
    // opening HISTORY saw the most recent event at the top and had to read upward to reconstruct
    // what happened -- the opposite of the page it replaced, for no stated reason.
    rows.sort((a, b) => a.at - b.at);
    return rows;
  }, [signals, notes]);

  const task = session.task ?? '';
  const taskLines = task.split('\n');
  const taskTruncatable = taskLines.length > 5 || task.length > 320;

  return (
    <div
      data-testid="command-deck"
      role="dialog"
      aria-label={`Command deck for ${session.session_id}`}
      style={{
        position: 'absolute',
        left,
        top,
        width: DECK_WIDTH,
        background: T.surface2,
        border: `1px solid ${T.border}`,
        borderRadius: 8,
        padding: 16,
        boxShadow: '0 8px 24px rgba(0,0,0,.5)',
        color: T.textPrimary,
        zIndex: 20,
        animation: 'fleet-deck-in 200ms ease-out',
      }}
    >
      {/* 1. Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: 999,
            background: activityColor(activity),
            animation: activityMotion(activity),
            flex: '0 0 auto',
          }}
          aria-hidden="true"
        />
        <span style={{ fontSize: 14, fontWeight: 600, fontFamily: FONT_MONO }}>
          {session.runtime}
        </span>
        <span style={{ fontSize: 12, color: T.textMuted, fontFamily: FONT_MONO }}>
          #{session.session_id.slice(-6)}
        </span>
        <span
          style={{
            fontSize: 11,
            color: activityColor(activity),
            border: `1px solid ${activityColor(activity)}`,
            borderRadius: 999,
            padding: '0 8px',
            marginLeft: 4,
          }}
        >
          {activity}
        </span>
        <button
          type="button"
          aria-label="Close command deck"
          onClick={onClose}
          style={{
            marginLeft: 'auto',
            background: 'transparent',
            border: 'none',
            color: T.textMuted,
            fontSize: 16,
            cursor: 'pointer',
            lineHeight: 1,
            padding: 4,
          }}
        >
          ×
        </button>
      </div>

      {/* 2. Task */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 11, color: T.textMuted, marginBottom: 4 }}>TASK</div>
        <div
          style={{
            fontSize: 13,
            lineHeight: 1.5,
            color: T.textPrimary,
            maxHeight: taskExpanded ? 'none' : 5 * 13 * 1.5,
            overflow: 'hidden',
            whiteSpace: 'pre-wrap',
          }}
        >
          {task.length > 0 ? task : DASH}
        </div>
        {taskTruncatable ? (
          <button
            type="button"
            onClick={() => setTaskExpanded((v) => !v)}
            style={{
              background: 'transparent',
              border: 'none',
              color: T.accent,
              fontSize: 11,
              cursor: 'pointer',
              padding: '4px 0 0 0',
            }}
          >
            {taskExpanded ? 'less' : 'more'}
          </button>
        ) : null}
      </div>

      {/* 3. Facts */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: 8,
          marginBottom: 12,
          borderTop: `1px solid ${T.border}`,
          borderBottom: `1px solid ${T.border}`,
          padding: '8px 0',
        }}
      >
        {/* STATE, which the canvas was not showing at all. `activity` is the four states the
            node DRAWS; `state` is the process's own report -- running, paused, failed, unknown --
            and `failed` is the one a reader must never have to open a panel twice to find. It is
            surfaced as a fact row with the same word the rest of the portal uses (stateLabel), so
            the page and the deck cannot disagree.

            THIS IS ALSO WHERE THE FIXTURE'S `state` FIELD IS HONOURED. Two tests asserted RUNNING
            and UNKNOWN against a canvas that rendered neither: the canvas was wrong, not the
            tests, and this is the row they were looking for. */}
        <Fact label="state" value={stateLabel(session.state)} />
        <Fact label="events" value={fmtCount(session.event_count)} />
        {/* LAST SEEN.
            `relTime` was written and then never used, which meant the deck showed events and
            spend but NOT WHEN THE AGENT LAST DID ANYTHING -- the single most important fact for
            answering "is this stuck?". It is promoted to the first row because it is what a
            person looks for, and it reads as a duration, never a timestamp: "17m" is legible at
            a glance where "2026-09-18T19:37:31Z" is not. */}
        <Fact label="last seen" value={relTime(session.updated_at)} />
        <Fact label="spend" value={fmtSpend(session.spend_usd)} />
        {/* The capability class, which the card carried and the generated canvas dropped. A
            runtime with no capability-class concept gets NOTHING here rather than a fabricated
            label -- the same rule the card followed. */}
        {capabilityLabel(session.capability_class) ? (
          <Fact label="capability" value={capabilityLabel(session.capability_class)!} />
        ) : null}
        <Fact label="repo" value={fmtText(session.repo)} />
        <Fact label="ticket" value={fmtText(session.ticket)} />
        <Fact label="PRs" value={fmtPRs(session.pull_requests)} />
      </div>

      {/* 4. Steer.
          ONLY for a runtime that has a live signal path. `NUDGEABLE_RUNTIMES` is the same set
          sessions.py enforces server-side, and a runtime outside it has no channel -- so a STEER
          button there posts a request the backend will refuse with a 422. The card grid checked
          this; the generated canvas did not, and offered steering to github-actions. A control
          that cannot work is worse than no control, which is the estate's own rule for the 422. */}
      {!NUDGEABLE_RUNTIMES.has(session.runtime) ? (
        <div style={{ fontSize: 11, color: T.textMuted, marginBottom: 12 }}>
          No steering channel for {session.runtime}.
        </div>
      ) : (
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 11, color: T.textMuted, marginBottom: 4 }}>STEER</div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
          <TextField
            value={steerText}
            onChange={(e) => setSteerText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                void submitSteer();
              }
            }}
            placeholder="Steer this agent…"
            size="small"
            multiline
            maxRows={3}
            fullWidth
            inputProps={{ 'aria-label': 'Steer text' }}
            sx={{
              '& .MuiInputBase-root': {
                fontSize: 13,
                background: T.surface,
                color: T.textPrimary,
              },
              '& .MuiOutlinedInput-notchedOutline': { borderColor: T.border },
            }}
          />
          <Tooltip
            title={
              speechAvailable
                ? 'Dictate a steer'
                : 'Speech recognition is not available in this browser'
            }
          >
            <span>
              <IconButton
                aria-label="Dictate steer"
                disabled={!speechAvailable}
                onClick={listening ? stopListening : startListening}
                size="small"
                sx={{
                  color: listening ? T.red : T.textMuted,
                  border: `1px solid ${listening ? T.red : T.border}`,
                  borderRadius: 8,
                  animation: listening ? 'fleet-breathe 1s ease-in-out infinite' : 'none',
                }}
              >
                <span style={{ fontSize: 13 }}>🎙</span>
              </IconButton>
            </span>
          </Tooltip>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8 }}>
          <Button
            variant="contained"
            size="small"
            onClick={() => void submitSteer()}
            disabled={steerState === 'sending'}
            sx={{
              fontSize: 12,
              textTransform: 'none',
              background: T.accent,
              color: '#0b0d10',
              '&:hover': { background: '#7fb2ff' },
            }}
          >
            {steerState === 'sending'
              ? '…'
              : steerState === 'sent'
                ? '✓ SENT'
                : steerState === 'failed'
                  ? '✕ FAIL'
                  : 'STEER →'}
          </Button>
          {emptyWarn ? (
            <span style={{ fontSize: 11, color: T.amber }}>Add your steer text first</span>
          ) : null}
        </div>
        {steerState === 'failed' && steerError ? (
          <div style={{ fontSize: 11, color: T.red, marginTop: 4 }}>{steerError}</div>
        ) : null}
      </div>
      )}

      {/* 5. Note */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 11, color: T.textMuted, marginBottom: 4 }}>NOTE</div>
        <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
          <TextField
            value={noteAuthor}
            onChange={(e) => setNoteAuthor(e.target.value)}
            placeholder="author"
            size="small"
            inputProps={{ 'aria-label': 'Note author' }}
            sx={{
              width: 120,
              '& .MuiInputBase-root': {
                fontSize: 12,
                background: T.surface,
                color: T.textPrimary,
              },
              '& .MuiOutlinedInput-notchedOutline': { borderColor: T.border },
            }}
          />
          <TextField
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            placeholder="note"
            size="small"
            fullWidth
            inputProps={{ 'aria-label': 'Note text' }}
            sx={{
              '& .MuiInputBase-root': {
                fontSize: 12,
                background: T.surface,
                color: T.textPrimary,
              },
              '& .MuiOutlinedInput-notchedOutline': { borderColor: T.border },
            }}
          />
        </div>
        <Button
          variant="outlined"
          size="small"
          disabled={noteBusy || noteText.trim().length === 0}
          onClick={() => void submitNote()}
          sx={{
            fontSize: 12,
            textTransform: 'none',
            color: T.textPrimary,
            borderColor: T.border,
          }}
        >
          Note
        </Button>
      </div>
      {noteWarn ? (
        <div style={{ fontSize: 11, color: T.amber, marginTop: -8, marginBottom: 12 }}>{noteWarn}</div>
      ) : null}

      {/* 6. History */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 11, color: T.textMuted, marginBottom: 4 }}>HISTORY</div>
        <div
          data-testid="deck-history"
          style={{
            maxHeight: 180,
            overflowY: 'auto',
            border: `1px solid ${T.border}`,
            borderRadius: 4,
            padding: '0 8px',
            background: T.surface,
          }}
        >
          {timeline.length === 0 ? (
            <div style={{ fontSize: 12, color: T.textMuted, padding: '8px 0' }}>
              No notes or signals yet.
            </div>
          ) : (
            timeline.map((row) => row.node)
          )}
        </div>
      </div>

      {/* 7. Receipt */}
      <div>
        <div style={{ fontSize: 11, color: T.textMuted, marginBottom: 4 }}>RECEIPT</div>
        <div data-testid="deck-receipt" style={{ fontSize: 12, color: T.textPrimary }}>
          {receipt
            ? receipt.status === 'unavailable'
              ? `unavailable — ${receipt.reason ?? 'no reason given'}`
              : `${receipt.status}${receipt.verdict ? ` — ${receipt.verdict}` : ''}`
            : 'unavailable — no receipt source is wired up'}
        </div>
      </div>
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div>
      <div style={{ fontSize: 11, color: T.textMuted }}>{label}</div>
      <div style={{ fontSize: 13, color: T.textPrimary, fontFamily: FONT_MONO }}>{value}</div>
    </div>
  );
}

/* ------------------------------------------------------------------------------------------------
 * The canvas.
 * ---------------------------------------------------------------------------------------------- */

export default function FleetCanvas(props: FleetCanvasProps): JSX.Element {
  const {
    sessions,
    board,
    onSubmitSteer,
    onAddNote,
    signalsBySession,
    notesBySession,
    onRequestSignals,
    onRequestNotes,
    onRequestReceipt,
    // The two controlled inputs. Destructured HERE, in the component that reads them -- the first
    // attempt put them in CommandDeck's destructuring, where they were unused, and the runtime
    // threw "selectedSessionId is not defined" while tsc stayed quiet because the reference was
    // in a scope that merely did not have it.
    activityFilter,
    selectedSessionId,
    spotlightSessionId,
    onSelectSession,
  } = props;

  const containerRef = useRef<HTMLDivElement | null>(null);
  // Container size drives the layout. ResizeObserver rather than window resize: the canvas is
  // often in a pane, and a pane can change size without the window changing.
  //
  // A MEASUREMENT OF ZERO MUST NOT RENDER NOTHING. Measured 2026-09-18: with `size.w > 0` gating
  // the whole SVG, a container that reports 0x0 -- jsdom (which implements no ResizeObserver and
  // lays out nothing), a collapsed pane, a tab that has not been shown yet -- produced a page
  // with no canvas, no nodes, no message, and NO ERROR. That is the silent-blank failure this
  // estate keeps removing, so the initial size is a real default and getBoundingClientRect is
  // only trusted once it reports something.
  const FALLBACK_W = 1200;
  // The floor only. A real container measures taller and fills it; this is what jsdom and a
  // collapsed pane get so the canvas is never blank.
  const FALLBACK_H = 640;
  const [size, setSize] = useState<{ w: number; h: number }>({
    w: FALLBACK_W,
    h: FALLBACK_H,
  });
  const [selectedIdState, setSelectedIdState] = useState<string | null>(null);
  // Controlled when the parent passes a value, internal otherwise. `undefined` means "not
  // controlled" and `null` means "controlled, nothing selected" -- conflating those is how a
  // controlled component silently stops responding to its own clicks.
  const selectedId = selectedSessionId !== undefined ? selectedSessionId : selectedIdState;
  const setSelectedId = useCallback(
    (next: string | null | ((prev: string | null) => string | null)) => {
      setSelectedIdState((prev) => {
        const resolved = typeof next === 'function' ? next(prev) : next;
        if (onSelectSession) onSelectSession(resolved);
        return resolved;
      });
    },
    [onSelectSession],
  );
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');
  const particlesDisabledLogged = useRef(false);

  // Container size drives the layout. ResizeObserver rather than window resize: the canvas is
  // often in a pane, and a pane can change size without the window changing.
  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const measure = () => {
      const rect = el.getBoundingClientRect();
      const w = Math.round(rect.width);
      const h = Math.round(rect.height);
      // Only adopt a real measurement. A 0 is "not laid out yet", and writing it back would
      // replace a usable default with nothing -- the failure described above.
      setSize(w > 0 && h > 0 ? { w, h } : { w: FALLBACK_W, h: FALLBACK_H });
    };
    measure();
    if (typeof ResizeObserver === 'function') {
      const ro = new ResizeObserver(measure);
      ro.observe(el);
      return () => ro.disconnect();
    }
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, []);

  const runtimes = useMemo(() => {
    const set = new Set<string>();
    sessions.forEach((s) => set.add(s.runtime));
    return Array.from(set).sort();
  }, [sessions]);

  // TWO FILTERS, and they compose. `filter` is the runtime chips along the top (the reader's
  // hand); `activityFilter` is what voice narrows to ("what is stuck") and what the deck's own
  // activity chip sets. Applying only one of them is why a voice query would have appeared to do
  // nothing on a runtime-filtered board.
  const visibleSessions = useMemo(() => {
    let out = sessions;
    if (filter !== 'all') out = out.filter((s) => s.runtime === filter);
    if (activityFilter) out = out.filter((s) => (s.activity ?? 'unknown') === activityFilter);
    return out;
  }, [sessions, filter, activityFilter]);

  // Layout is memoised on the session-id set and the container size. NEVER per frame.
  const layoutKey = useMemo(
    () => visibleSessions.map((s) => s.session_id).join('|'),
    [visibleSessions],
  );

  const { nodes, edges } = useMemo(
    () => layoutFleet(visibleSessions, size.w, size.h),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [layoutKey, size.w, size.h],
  );

  const nodeById = useMemo(() => {
    const m = new Map<string, LaidOutNode>();
    nodes.forEach((n) => m.set(n.session.session_id, n));
    return m;
  }, [nodes]);

  const selected = selectedId ? nodeById.get(selectedId) ?? null : null;

  // Edge particles: disabled above 120 sessions. Above that the particle layer is more pixels
  // than information, and the animation stops reading as flow.
  const particlesEnabled = sessions.length <= 120;
  useEffect(() => {
    if (!particlesEnabled && !particlesDisabledLogged.current) {
      particlesDisabledLogged.current = true;
      // eslint-disable-next-line no-console
      console.warn(
        `FleetCanvas: edge particles disabled at ${sessions.length} sessions (>120) — density would read as noise, not flow.`,
      );
    }
  }, [particlesEnabled, sessions.length]);

  const handleSelect = useCallback((id: string) => {
    setSelectedId((prev) => (prev === id ? null : id));
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, id: string) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        handleSelect(id);
      }
    },
    [handleSelect],
  );

  // Escape closes the deck. Bound at the document so it works wherever focus is.
  useEffect(() => {
    if (!selectedId) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setSelectedId(null);
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [selectedId]);

  const signals = selectedId ? signalsBySession?.[selectedId] ?? [] : [];
  const notes = selectedId ? notesBySession?.[selectedId] ?? [] : [];

  const empty = sessions.length === 0;
  const unavailable = board.state === 'unavailable';

  return (
    <div
      ref={containerRef}
      data-testid="fleet-root"
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        height: 'clamp(520px, calc(100vh - 260px), 1100px)',
        minHeight: 520,
        background: T.bg,
        overflow: 'hidden',
        fontFamily: FONT_MONO,
      }}
    >
      {/* Filter strip. Narrowing the fleet is the first thing a reader does when the board is loud. */}
      <div
        style={{
          position: 'absolute',
          top: 8,
          left: 8,
          display: 'flex',
          gap: 8,
          zIndex: 10,
          flexWrap: 'wrap',
          maxWidth: size.w - 16,
        }}
      >
        <FilterChip
          label={`all (${sessions.length})`}
          active={filter === 'all'}
          onClick={() => setFilter('all')}
          ariaLabel={`Filter: all ${sessions.length}`}
        />
        {runtimes.map((rt) => {
          const count = sessions.filter((s) => s.runtime === rt).length;
          return (
            <FilterChip
              key={rt}
              label={`${rt} (${count})`}
              active={filter === rt}
              onClick={() => setFilter(rt)}
              ariaLabel={`Filter: ${count} ${rt}`}
            />
          );
        })}
      </div>

      {unavailable ? (
        <div
          data-testid="fleet-unavailable"
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'column',
            gap: 8,
            color: T.textMuted,
          }}
        >
          <div style={{ fontSize: 16, color: T.red }}>Fleet unavailable</div>
          <div style={{ fontSize: 13 }}>{board.summary ?? 'The source could not be read.'}</div>
        </div>
      ) : empty ? (
        <div
          data-testid="fleet-empty"
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'column',
            gap: 8,
            color: T.textMuted,
          }}
        >
          <div style={{ fontSize: 16, color: T.textPrimary }}>No sessions</div>
          <div style={{ fontSize: 13 }}>{board.summary ?? 'The estate has no sessions.'}</div>
        </div>
      ) : null}

      {!empty && !unavailable ? (
        <svg
          data-testid="fleet-canvas"
          width={size.w}
          height={size.h}
          style={{ position: 'absolute', inset: 0, display: 'block' }}
          role="presentation"
        >
          <defs>
            {/* The hover glow is a light, not a border. */}
            <radialGradient id="fleet-hover-glow">
              <stop offset="0%" stopColor={T.accent} stopOpacity="0.22" />
              <stop offset="70%" stopColor={T.accent} stopOpacity="0" />
            </radialGradient>
          </defs>

          {/* The fleet breathes as one. 0.4% amplitude on the whole node layer: felt, not seen. */}
          <g
            style={{
              transformOrigin: `${size.w / 2}px ${size.h / 2}px`,
              animation: 'fleet-breathe 6s ease-in-out infinite',
              transformBox: 'fill-box',
            }}
          >
            {/* Edges and particles in ONE layer, pointer-events off. */}
            <g style={{ pointerEvents: 'none' }}>
              {edges.map((edge) => {
                const hot =
                  hoveredId === edge.a.session.session_id ||
                  hoveredId === edge.b.session.session_id ||
                  selectedId === edge.a.session.session_id ||
                  selectedId === edge.b.session.session_id;
                const stroke = hot ? T.accent : T.border;
                const midX = (edge.a.x + edge.b.x) / 2;
                const midY = (edge.a.y + edge.b.y) / 2;
                const pathId = `edge-${edge.key.replace(/[^a-zA-Z0-9_-]/g, '_')}`;
                // Speed = combined throughput, capped so it reads as flow, not strobe.
                const speed = Math.max(
                  1.2,
                  Math.min(3.5, 1.2 + edge.throughput / 120),
                );
                // Density = number of agents on the repo, 2..3 particles.
                const particleCount = edge.density >= 4 ? 3 : 2;
                return (
                  <g key={edge.key}>
                    <path
                      id={pathId}
                      d={`M ${edge.a.x} ${edge.a.y} Q ${midX} ${midY - 24} ${edge.b.x} ${edge.b.y}`}
                      fill="none"
                      stroke={stroke}
                      strokeWidth={hot ? 1.5 : 1}
                      opacity={hot ? 0.9 : 0.35}
                    />
                    {particlesEnabled
                      ? Array.from({ length: particleCount }).map((_, pi) => (
                          <circle key={pi} r={2} fill={hot ? T.accent : T.textMuted} opacity={0.8}>
                            <animateMotion
                              dur={`${speed}s`}
                              repeatCount="indefinite"
                              begin={`${(pi * speed) / particleCount}s`}
                            >
                              <mpath href={`#${pathId}`} />
                            </animateMotion>
                          </circle>
                        ))
                      : null}
                  </g>
                );
              })}
            </g>

            {/* Nodes. */}
            <g>
              {nodes.map((node) => {
                const id = node.session.session_id;
                const isSelected = selectedId === id;
                const isHovered = hoveredId === id;
                const color = activityColor(node.activity);
                const scale = isHovered ? 1.08 : 1;
                const stuck = node.activity === 'stuck';
                // A stuck node reaches out: pulled 4px toward screen centre on a 2s cycle.
                const pullX = stuck ? (size.w / 2 - node.x) * 0.02 : 0;
                const pullY = stuck ? (size.h / 2 - node.y) * 0.02 : 0;
                const ringR = node.r + 6;
                const arcR = node.r + 10;

                // THE SPOTLIGHT. When this node is named, it leaves the swarm: it glides to the
                // centre, grows to about three times its size, and the rest of the fleet fades
                // behind it. Everything is a CSS transition on transform, so the movement is one
                // smooth interpolation the browser does itself -- no per-frame work, and it reads
                // as the agent MOVING rather than the page redrawing.
                const isSpotlit = spotlightSessionId === id;
                const anySpotlit = Boolean(spotlightSessionId);
                const homeX = size.w / 2;
                const homeY = size.h / 2;
                // Offset left when the deck is beside it, so the agent is not hidden behind its
                // own panel.
                const spotX = size.w * 0.34;
                const spotY = homeY;
                const tx = isSpotlit ? spotX : node.x + pullX;
                const ty = isSpotlit ? spotY : node.y + pullY;
                const spotScale = isSpotlit ? Math.max(2.2, 120 / Math.max(1, node.r)) : 1;
                const dimmed = anySpotlit && !isSpotlit;
                return (
                  <g
                    key={id}
                    transform={`translate(${tx} ${ty}) scale(${spotScale})`}
                    style={{
                      cursor: 'pointer',
                      willChange: 'transform, opacity',
                      // 620ms on a soft overshoot: long enough to read as travel, short enough
                      // that it lands before a person finishes blinking.
                      transition: 'transform 620ms cubic-bezier(.22,1.2,.36,1), opacity 420ms ease',
                      opacity: dimmed ? 0.18 : 1,
                      animation: stuck && !isSpotlit ? 'fleet-drift 2s ease-in-out infinite' : 'none',
                    }}
                    role="button"
                    tabIndex={0}
                    // The session id as a testid, and the activity in PLAIN WORDS in the
                    // label. The label is the whole accessibility contract: motion is not
                    // available to every reader and is nothing at all under
                    // prefers-reduced-motion, so the word is the signal that always survives.
                    data-testid={`session-${id}`}
                    aria-label={`${node.session.runtime} ${id.slice(-6)}: ${ACTIVITY_WORD[node.activity]}, ${node.session.event_count ?? 0} events`}
                    onClick={() => handleSelect(id)}
                    onKeyDown={(e) => handleKeyDown(e, id)}
                    onMouseEnter={() => setHoveredId(id)}
                    onMouseLeave={() => setHoveredId((prev) => (prev === id ? null : prev))}
                  >
                    {/* Hover glow behind the node. */}
                    {isHovered ? (
                      <circle
                        r={node.r * 2.4}
                        fill="url(#fleet-hover-glow)"
                        style={{ pointerEvents: 'none' }}
                      />
                    ) : null}

                    {/* Stuck halo: expanding ring, keyframes from styles.css. The testid is what
                        makes "does a stuck node look different" a testable claim rather than a
                        matter of opinion. */}
                    {stuck ? (
                      <circle
                        data-testid="halo"
                        r={node.r + 8}
                        fill="none"
                        stroke={T.red}
                        strokeWidth={2}
                        opacity={0.6}
                        style={{
                          transformOrigin: 'center',
                          animation: 'fleet-halo 1.6s ease-out infinite',
                        }}
                      />
                    ) : null}

                    {/* Activity ring. */}
                    <circle
                      r={ringR}
                      fill="none"
                      stroke={color}
                      strokeWidth={1}
                      opacity={0.25 + node.level * 0.5}
                    />

                    {/* Cost temperature arc: sweep = share of today's spend. */}
                    {node.spendShare > 0 ? (
                      <path
                        d={arcPath(0, 0, arcR, node.spendShare)}
                        fill="none"
                        stroke={temperatureColor(node.spendShare)}
                        strokeWidth={2}
                        strokeLinecap="round"
                      />
                    ) : null}

                    {/* THE TRAIL. How much work this agent has actually done, drawn as an arc
                        behind it.

                        WHY THIS AND NOT A NUMBER. Measured 2026-09-19: one node held 411 events
                        and twenty-three held exactly one. That is the single most important fact
                        about this fleet and NOTHING on screen said it -- the label carried
                        "411 events" in 11px text nobody reads. An arc is the same fact at a
                        glance from across the room.

                        It is drawn from the event count the API already returns, not from fetched
                        history, so it costs no request and cannot disagree with the label. Stroke
                        width grows with the count too, so a busy agent has a thick hot arc and an
                        idle one a hairline -- two channels for one fact, because at 101px a thin
                        arc is invisible and at 292px a thick one is not. */}
                    {(() => {
                      const events = node.session.event_count ?? 0;
                      if (events <= 1) {
                        // EMPTY READS AS EMPTY. An agent with one event gets a dashed hairline:
                        // visible as a shape, unmistakable as nothing done.
                        return (
                          <circle
                            data-testid={`trail-${id}`}
                            r={node.r + 6}
                            fill="none"
                            stroke={T.textMuted}
                            strokeWidth={1}
                            strokeDasharray="2 6"
                            opacity={0.35}
                          />
                        );
                      }
                      // sqrt, like the radius: length should scale with work, not with the raw
                      // count, or 411 events would wrap the circle many times over.
                      const sweep = Math.min(1, Math.sqrt(events / 400));
                      const thickness = 2 + 6 * sweep;
                      return (
                        <path
                          data-testid={`trail-${id}`}
                          d={arcPath(0, 0, node.r + 6, sweep)}
                          fill="none"
                          stroke={color}
                          strokeWidth={thickness}
                          strokeLinecap="round"
                          opacity={0.28 + sweep * 0.5}
                        />
                      );
                    })()}

                    {/* The node itself. */}
                    <circle
                      r={node.r}
                      fill={T.surface}
                      stroke={color}
                      strokeWidth={isSelected ? 2.5 : 1.5}
                      style={{
                        transformOrigin: 'center',
                        transform: `scale(${scale})`,
                        transition: 'transform 180ms cubic-bezier(.34,1.56,.64,1)',
                        animation: activityMotion(node.activity),
                      }}
                    />

                    {/* Label. */}
                    <text
                      x={0}
                      y={4}
                      textAnchor="middle"
                      fontSize={11}
                      fill={T.textPrimary}
                      style={{ pointerEvents: 'none', userSelect: 'none' }}
                    >
                      {id.slice(-6)}
                    </text>
                  </g>
                );
              })}
            </g>
          </g>

          {/* Selection tether: 1px accent line from node to deck anchor, with a 3px dot that
              animates along it once. */}
          {selected ? (
            <g style={{ pointerEvents: 'none' }}>
              {(() => {
                const gap = 24;
                const preferRight = selected.x + gap + DECK_WIDTH <= size.w - 8;
                const anchorX = preferRight
                  ? selected.x + gap
                  : Math.max(8, selected.x - gap - DECK_WIDTH);
                const anchorY = Math.max(8, Math.min(size.h - 200, selected.y - 80));
                const pathId = 'fleet-tether';
                return (
                  <>
                    <path
                      id={pathId}
                      d={`M ${selected.x} ${selected.y} L ${anchorX} ${anchorY}`}
                      stroke={T.accent}
                      strokeWidth={1}
                      fill="none"
                      opacity={0.7}
                    />
                    <circle r={3} fill={T.accent}>
                      <animateMotion dur="240ms" repeatCount="1" fill="freeze">
                        <mpath href={`#${pathId}`} />
                      </animateMotion>
                    </circle>
                  </>
                );
              })()}
            </g>
          ) : null}
        </svg>
      ) : null}

      {/* The command deck. */}
      {selected ? (
        <CommandDeck
          session={selected.session}
          anchor={{ x: selected.x, y: selected.y }}
          containerWidth={size.w}
          containerHeight={size.h}
          signals={signals}
          notes={notes}
          onSubmitSteer={onSubmitSteer}
          onAddNote={onAddNote}
          onRequestSignals={onRequestSignals}
          onRequestNotes={onRequestNotes}
          onRequestReceipt={onRequestReceipt}
          onClose={() => setSelectedId(null)}
        />
      ) : null}
    </div>
  );
}

function FilterChip({
  label,
  active,
  onClick,
  ariaLabel,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  /** The spoken name. An aria-pressed button says WHETHER it is on and nothing about what it
   *  filters, so without this a screen reader heard "2 thinking, toggle button". */
  ariaLabel: string;
}): JSX.Element {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      aria-label={ariaLabel}
      style={{
        fontSize: 11,
        fontFamily: FONT_MONO,
        color: active ? '#0b0d10' : T.textMuted,
        background: active ? T.accent : T.surface2,
        border: `1px solid ${active ? T.accent : T.border}`,
        borderRadius: 999,
        padding: '4px 8px',
        cursor: 'pointer',
      }}
    >
      {label}
    </button>
  );
}
