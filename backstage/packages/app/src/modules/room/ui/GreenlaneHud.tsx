/**
 * greenlane, live: whether main is green on the commit it is actually at, and every lane's
 * verdict -- what the ~80s tick decided, and why. The backend (fleetview_backend/greenlane.py)
 * runs `bin/idp-greenlane status`; this renders the same JSON the engine itself acts on.
 *
 * `main.green` is the engine's verdict, not this file's opinion, and the required-check
 * conclusions arrive with it -- so a founder looking at a red main can see WHICH check is red
 * instead of a colour they have to go and interrogate. The panel colours by the engine's own
 * rule (bin/idp-greenlane:278: green when every required conclusion is success, skipped or
 * neutral); a second opinion here would sooner or later contradict the verdict printed above it.
 *
 * And a lane that cannot be read says so, never a green main. "I could not read this" and "this
 * did not run" are different facts and the founder acts differently on each.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

export type Call = (init?: RequestInit) => Promise<Response>;

export type Lane = { head?: string; reason?: string; status?: string };
export type Greenlane = {
  available: boolean;
  error?: string;
  alarm?: boolean;
  main?: { green?: boolean; sha?: string; required?: Record<string, string> };
  open_prs?: Array<{ number: number; head: string; user: string }>;
  state?: {
    available?: boolean;
    error?: string;
    lanes?: Record<string, Lane>;
    landed_total?: number;
    candidates_total?: number;
  };
  invariants?: { work_lost?: number; open_prs_not_raised_by_engine?: number };
  read_at?: string;
};

/** bin/idp-greenlane:278. Not a heuristic: the same three values the engine accepts. */
export const GREEN = ['success', 'skipped', 'neutral'];

/** The required checks that are not green, in the engine's own vocabulary. */
export function notGreen(required: Record<string, string> = {}): Array<[string, string]> {
  return Object.entries(required).filter(([, v]) => !GREEN.includes(v));
}

/** Lane statuses counted, worst first, so the pill can lead with what is red. */
export const LANE_ORDER = ['red', 'conflict', 'testing', 'pending', 'landed'];

export function laneCounts(lanes: Record<string, Lane> = {}): Array<[string, number]> {
  const c = new Map<string, number>();
  for (const l of Object.values(lanes)) {
    const s = l.status || 'unknown';
    c.set(s, (c.get(s) || 0) + 1);
  }
  return [...c.entries()].sort(
    (a, b) => LANE_ORDER.indexOf(a[0]) - LANE_ORDER.indexOf(b[0]),
  );
}

export function laneTone(status: string): string {
  switch (status) {
    case 'red':
      return 'text-rose-300 border-rose-400/40';
    case 'conflict':
      return 'text-amber-200 border-amber-400/40';
    case 'landed':
      return 'text-emerald-300 border-emerald-400/40';
    case 'testing':
      return 'text-cyan-200 border-cyan-400/40';
    default:
      return 'text-white/60 border-white/15';
  }
}

/** The pill's words. A green main is the only thing that says green, and it must have been read. */
export function laneLabel(lane: Greenlane | null, err: string | null): string {
  if (err) return 'lanes · unreachable';
  if (!lane) return 'lanes · …';
  if (!lane.available) return 'lanes · unreadable';
  const red = laneCounts(lane.state?.lanes).find(([s]) => s === 'red')?.[1] ?? 0;
  const main = `lanes · main ${lane.main?.green ? 'green' : 'red'}`;
  const redPart = red ? ` · ${red} red` : '';
  const alarmPart = lane.alarm && lane.main?.green ? ' · alarm' : '';
  return `${main}${redPart}${alarmPart}`;
}

export function laneToneFor(lane: Greenlane | null, err: string | null): string {
  if (err || (lane && !lane.available)) return 'text-rose-300 border-rose-400/40';
  if (!lane) return 'text-white/80 border-white/15';
  if (!lane.main?.green || lane.alarm) return 'text-rose-300 border-rose-400/40';
  return 'text-white/80 border-white/15';
}

function LaneBody({ lane, err }: { lane: Greenlane | null; err: string | null }) {
  if (err || (lane && !lane.available)) {
    return (
      <p data-testid="greenlane-error" className="text-rose-300">
        {err || lane?.error || 'the greenlane answered without a verdict.'}
      </p>
    );
  }
  if (!lane) return <p className="text-white/50">reading the lane…</p>;

  const counts = laneCounts(lane.state?.lanes);
  const broken = notGreen(lane.main?.required);
  const landed = lane.state?.landed_total;
  const landedLine =
    landed === undefined || landed === null
      ? ''
      : ` · ${landed} landed of ${lane.state?.candidates_total}`;

  return (
    <>
      <p data-testid="greenlane-main" className={lane.main?.green ? '' : 'text-rose-300'}>
        main {lane.main?.sha || 'unknown'} · {lane.main?.green ? 'green' : 'NOT green'}
      </p>
      {broken.length ? (
        <ul data-testid="greenlane-checks" className="mt-1">
          {broken.map(([name, v]) => (
            <li key={name} className="font-mono text-[10px] text-rose-200/90">
              {name} · {v}
            </li>
          ))}
        </ul>
      ) : null}

      {lane.invariants?.work_lost ? (
        <p data-testid="greenlane-work-lost" className="mt-2 text-rose-300">
          {lane.invariants.work_lost} PR(s) closed unmerged with their work in no branch and no
          main — work is lost
        </p>
      ) : (
        <p className="mt-2 text-white/45">work lost · 0</p>
      )}

      <div className="mt-2 text-[9px] uppercase tracking-wider text-white/40">
        open pull requests
        {lane.invariants?.open_prs_not_raised_by_engine
          ? ` · ${lane.invariants.open_prs_not_raised_by_engine} not raised by the engine`
          : ''}
      </div>
      {lane.open_prs?.length ? (
        <ul data-testid="greenlane-open-prs">
          {lane.open_prs.map(p => (
            <li key={p.number} className="font-mono text-[10px] text-amber-200/90">
              #{p.number} {p.head} ({p.user})
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-white/45 text-[10px]">none</p>
      )}

      <div className="mt-3 text-[9px] uppercase tracking-wider text-white/40">
        lanes · {Object.keys(lane.state?.lanes || {}).length} held
        {counts.length ? ` · ${counts.map(([s, n]) => `${n} ${s}`).join(' · ')}` : ''}
      </div>
      <ul data-testid="greenlane-lanes" className="mt-1">
        {Object.entries(lane.state?.lanes || {}).map(([name, l]) => (
          <li key={name} className="mb-1">
            <span className={`font-mono text-[10px] ${laneTone(l.status || '')}`}>
              {l.status}
            </span>{' '}
            <span className="font-mono text-[10px] text-white/80">{name}</span>
            {l.reason ? (
              <div className="text-[10px] text-white/45 truncate">{l.reason}</div>
            ) : null}
          </li>
        ))}
      </ul>
      {lane.state?.available === false ? (
        <p className="mt-2 text-amber-200 text-[10px]">
          lane state unreadable: {lane.state.error}
        </p>
      ) : null}
      <p className="mt-2 text-[9px] font-mono text-white/35">
        {lane.read_at ? `read ${lane.read_at}` : ''}
        {landedLine}
      </p>
    </>
  );
}

export default function GreenlaneHud({
  call,
  pollMs = 30_000,
}: {
  call: Call;
  pollMs?: number;
}) {
  const [open, setOpen] = useState(false);
  const [lane, setLane] = useState<Greenlane | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const callRef = useRef(call);
  callRef.current = call;
  const inFlight = useRef(false);

  const refresh = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const res = await callRef.current();
      setLane((await res.json()) as Greenlane);
      setErr(null);
    } catch (e: any) {
      setErr(`Fleet cannot reach the greenlane (${e?.message || e}).`);
    } finally {
      inFlight.current = false;
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(() => {
      if (typeof document !== 'undefined' && document.hidden) return;
      refresh();
    }, pollMs);
    return () => clearInterval(id);
  }, [pollMs, refresh]);

  const label = laneLabel(lane, err);

  return (
    <div className="absolute top-[18.5rem] right-6 z-40 pointer-events-auto flex flex-col items-end gap-2 max-w-[92vw]">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        className={`px-3 py-1.5 rounded-full bg-black/70 border backdrop-blur-md text-[11px] font-mono hover:text-white ${laneToneFor(
          lane,
          err,
        )}`}
      >
        {label}
      </button>
      {open ? (
        <div
          role="region"
          aria-label="greenlane"
          className="w-[440px] max-w-[92vw] max-h-[70vh] overflow-y-auto p-3 rounded-xl bg-black/80 border border-white/10 backdrop-blur-md text-white/85 text-[12px]"
        >
          <LaneBody lane={lane} err={err} />
        </div>
      ) : null}
    </div>
  );
}
