/**
 * greenlane, quietly: one dot. It is loud only when something needs a person -- the engine's
 * alarm, a red lane, a conflict, a main that is not green, or a batch that has been under test too
 * long -- and the detail opens by voice ("how's the lane?") or by touching the dot, then fades on
 * its own a few seconds after the last touch.
 *
 * Nothing here decides anything. The backend (fleetview_backend/greenlane.py) runs
 * `bin/idp-greenlane status`; that JSON carries `brief` (greenlane/brief.py), which holds `loud`
 * and the three answers the detail gives: what is landing and for how long, what is stuck and why,
 * what is red and who owns it. The spoken answer is the same brief's `summary`. A second opinion
 * here would sooner or later contradict the one the engine acts on.
 *
 * A lane that cannot be read says so, never a quiet dot: "I could not read this" and "nothing is
 * wrong" are different facts and the founder acts differently on each.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

export type Call = (init?: RequestInit) => Promise<Response>;

export type Brief = {
  loud: boolean;
  summary: string;
  landing: { lanes: string[]; minutes: number | null } | null;
  waiting: number;
  stuck: Array<{ lane: string; why: string; status: string }>;
  red: Array<{ lane: string; why: string; owner: string }>;
  main_red: string[];
  work_lost: number;
};
export type Greenlane = {
  available: boolean;
  error?: string;
  alarm?: boolean;
  brief?: Brief;
  read_at?: string;
};

/** How long the detail stays after the last touch. Touching it keeps it alive. */
export const FADE_MS = 8_000;

const short = (lane: string) => lane.replace(/^lane\//, '');

/** Is the dot loud? An unreadable lane is loud: silence must mean "read, and fine". */
export function isLoud(lane: Greenlane | null, err: string | null): boolean {
  if (err || (lane && !lane.available)) return true;
  if (!lane) return false;
  return lane.brief ? lane.brief.loud : Boolean(lane.alarm);
}

/** The words beside a loud dot; a quiet dot has none. */
export function loudLabel(lane: Greenlane | null, err: string | null): string {
  if (err) return 'lanes · unreachable';
  if (lane && !lane.available) return 'lanes · unreadable';
  const b = lane?.brief;
  if (!b) return lane?.alarm ? 'lanes · alarm' : '';
  const n = b.red.length + b.stuck.length;
  if (b.main_red.length) return 'lanes · main red';
  if (b.work_lost) return 'lanes · work lost';
  if (n) return `lanes · ${n} need you`;
  return 'lanes · alarm';
}

function Section({ title, empty, children }: { title: string; empty: string; children?: any }) {
  const has = Array.isArray(children) ? children.length > 0 : Boolean(children);
  return (
    <section className="mt-2 first:mt-0">
      <div className="text-[12px] uppercase tracking-wider text-white/60">{title}</div>
      {has ? children : <p className="text-white/60 text-[12px]">{empty}</p>}
    </section>
  );
}

function Detail({ lane, err }: { lane: Greenlane | null; err: string | null }) {
  if (err || (lane && !lane.available)) {
    return (
      <p data-testid="greenlane-error" className="text-rose-300">
        {err || lane?.error || 'the greenlane answered without a verdict.'}
      </p>
    );
  }
  if (!lane) return <p className="text-white/60">reading the lane…</p>;
  const b = lane.brief;
  if (!b) return <p className="text-amber-200">the greenlane sent no brief; update the backend.</p>;

  return (
    <>
      {b.main_red.length ? (
        <p data-testid="greenlane-main" className="text-rose-300 mb-2">
          main is not green: {b.main_red.join(', ')}
        </p>
      ) : null}
      {b.work_lost ? (
        <p data-testid="greenlane-work-lost" className="text-rose-300 mb-2">
          {b.work_lost} PR(s) closed with their work in no branch and no main — work is lost
        </p>
      ) : null}

      <Section title="landing" empty={b.waiting ? `nothing under test · ${b.waiting} waiting` : 'nothing landing'}>
        {b.landing && b.landing.lanes.length ? (
          <div data-testid="greenlane-landing">
            <div className="text-white/85">
              {b.landing.lanes.map(short).join(', ')}
              {b.landing.minutes !== null ? ` · ${b.landing.minutes} min` : ''}
            </div>
            {b.waiting ? <div className="text-white/60">{b.waiting} waiting</div> : null}
          </div>
        ) : null}
      </Section>

      <Section title="stuck" empty="nothing stuck">
        {b.stuck.map(s => (
          <div key={s.lane} data-testid="greenlane-stuck" className="text-amber-200/90">
            {short(s.lane)} <span className="text-white/60">— {s.why}</span>
          </div>
        ))}
      </Section>

      <Section title="red" empty="nothing red">
        {b.red.map(r => (
          <div key={r.lane} data-testid="greenlane-red" className="text-rose-200/90">
            {short(r.lane)} <span className="text-white/60">— {r.why} · {r.owner}</span>
          </div>
        ))}
      </Section>
    </>
  );
}

export default function GreenlaneHud({
  call,
  pollMs = 30_000,
  summon = 0,
  fadeMs = FADE_MS,
}: {
  call: Call;
  pollMs?: number;
  /** Bump this to open the detail (a spoken "how's the lane?"). It fades after `fadeMs`. */
  summon?: number;
  fadeMs?: number;
}) {
  const [open, setOpen] = useState(false);
  const [lane, setLane] = useState<Greenlane | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const callRef = useRef(call);
  callRef.current = call;
  const inFlight = useRef(false);
  const fade = useRef<any>(null);

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

  const arm = useCallback(() => {
    clearTimeout(fade.current);
    fade.current = setTimeout(() => setOpen(false), fadeMs);
  }, [fadeMs]);
  useEffect(() => () => clearTimeout(fade.current), []);

  // A spoken question opens the detail on fresh data, then lets it go.
  useEffect(() => {
    if (!summon) return;
    refresh();
    setOpen(true);
    arm();
  }, [summon, arm, refresh]);

  const toggle = () => {
    if (open) {
      clearTimeout(fade.current);
      setOpen(false);
      return;
    }
    setOpen(true);
    arm();
  };

  const loud = isLoud(lane, err);
  const label = loud ? loudLabel(lane, err) : '';

  return (
    <div className="pointer-events-auto flex flex-col items-end gap-2 max-w-[92vw]">
      <button
        type="button"
        onClick={toggle}
        aria-expanded={open}
        aria-label={label || 'greenlane · all quiet'}
        data-testid="greenlane-dot"
        data-loud={loud ? 'true' : 'false'}
        className={
          loud
            ? 'flex items-center gap-2 px-3 py-1.5 rounded-full bg-black/70 border border-rose-400/40 backdrop-blur-md text-[12px] font-mono text-rose-300'
            : 'p-2 rounded-full'
        }
      >
        <span
          className={`block rounded-full ${
            loud ? 'h-2 w-2 bg-rose-400 animate-pulse' : 'h-1.5 w-1.5 bg-white/25'
          }`}
        />
        {label}
      </button>
      {open ? (
        <div
          role="region"
          aria-label="greenlane"
          onPointerDown={arm}
          onPointerMove={arm}
          onScroll={arm}
          className="w-[440px] max-w-[92vw] max-h-[70vh] overflow-y-auto p-3 rounded-xl bg-black/80 border border-white/10 backdrop-blur-md text-white/85 text-[12px]"
        >
          <Detail lane={lane} err={err} />
        </div>
      ) : null}
    </div>
  );
}
