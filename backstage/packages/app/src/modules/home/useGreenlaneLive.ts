// The Greenlane as it moves, for /face and /fleet. Polls `/fleetview/greenlane/live`
// (greenlane_live.py: one read of the engine's state.json, plus the batch's check runs) and SAYS
// what changed -- a lane that went red and why, a lane that landed and how long it waited -- so the
// founder hears the lane without watching it.
//
// HONESTY RULES (the estate's section 3): an unreadable lane is `unavailable` with its reason,
// never an empty queue. Announcements are only for changes this page watched happen: the first
// poll is a baseline, so opening the face never replays old reds or landings aloud.
import { useEffect, useRef, useState } from 'react';
import { fetchApiRef, useApi } from '@backstage/frontend-plugin-api';

export type GreenlaneLane = {
  name: string;
  status: string;
  reason: string;
  attempts: number;
  head: string;
  age_min: number | null;
};

export type GreenlaneCheck = {
  name: string;
  status: string;
  conclusion: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  url?: string | null;
};

export type GreenlaneBatch = {
  id: number | null;
  tip: string;
  lanes: string[];
  age_min: number | null;
  checks?: GreenlaneCheck[];
  checks_error?: string;
};

export type GreenlaneOutcome = {
  id: number | null;
  lanes: string[];
  outcome: string | null;
  action: string | null;
  reason: string;
  took_min: number | null;
  ago_min: number | null;
};

export type GreenlaneLanded = {
  lane: string | null;
  batch: number | null;
  waited_min: number | null;
  ago_min: number | null;
};

type Pcts = { n: number; p50: number | null; p90: number | null };

export type GreenlaneView = {
  lanes: GreenlaneLane[];
  batch: GreenlaneBatch | null;
  recent: GreenlaneOutcome[];
  landed: GreenlaneLanded[];
  timings: {
    queue_to_land_min: Pcts;
    batch_cycle_min: Pcts;
    outcomes: Record<string, number>;
  };
  sentence: string;
  read_at: string;
};

export type LoadedGreenlane =
  | { state: 'loading' }
  | { state: 'unavailable'; error: string }
  | { state: 'ready'; view: GreenlaneView };

// A batch under test moves check by check; an idle lane only needs the home heartbeat. Each poll
// is a GitHub read behind one hourly token budget (the backend caches 10s), so fast only while busy.
export const FAST_MS = 10_000;
export const SLOW_MS = 60_000;

const arr = <T>(v: unknown): T[] => (Array.isArray(v) ? (v as T[]) : []);
const emptyPcts: Pcts = { n: 0, p50: null, p90: null };

export function parseLive(status: number, body: unknown): LoadedGreenlane {
  const b = (typeof body === 'object' && body !== null ? body : {}) as Record<
    string,
    unknown
  >;
  if (status < 200 || status >= 300 || b.available === false) {
    const why =
      typeof b.error === 'string' && b.error
        ? b.error
        : `greenlane/live answered ${status}`;
    return { state: 'unavailable', error: why };
  }
  if (!Array.isArray(b.lanes)) {
    return { state: 'unavailable', error: 'greenlane/live sent no lane list' };
  }
  const t = (b.timings ?? {}) as Partial<GreenlaneView['timings']>;
  const batch = b.batch as GreenlaneBatch | null | undefined;
  return {
    state: 'ready',
    view: {
      lanes: arr<GreenlaneLane>(b.lanes).filter(
        l => typeof l?.name === 'string' && typeof l?.status === 'string',
      ),
      batch:
        batch && typeof batch.tip === 'string'
          ? { ...batch, lanes: arr<string>(batch.lanes) }
          : null,
      recent: arr<GreenlaneOutcome>(b.recent),
      landed: arr<GreenlaneLanded>(b.landed),
      timings: {
        queue_to_land_min: t.queue_to_land_min ?? emptyPcts,
        batch_cycle_min: t.batch_cycle_min ?? emptyPcts,
        outcomes: t.outcomes ?? {},
      },
      sentence: typeof b.sentence === 'string' ? b.sentence : '',
      read_at: typeof b.read_at === 'string' ? b.read_at : '',
    },
  };
}

export const short = (lane: string) => lane.replace(/^lane\//, '');

/** What the previous poll knew: which lanes were red, which landings were already seen. */
export type Seen = { red: Set<string>; landings: Set<string> };

const landingKey = (l: GreenlaneLanded) => `${l.lane}@${l.batch}`;

export function seenOf(view: GreenlaneView): Seen {
  return {
    red: new Set(
      view.lanes
        .filter(l => l.status === 'red' || l.status === 'conflict')
        .map(l => l.name),
    ),
    landings: new Set(view.landed.map(landingKey)),
  };
}

/**
 * The sentences for what changed between two polls. `prev` null is the baseline: nothing is said.
 * Short: spoken over whatever the founder is doing; the link in a reason is never read aloud.
 */
export function newsSince(prev: Seen | null, view: GreenlaneView): string[] {
  if (!prev) return [];
  const out: string[] = [];
  for (const l of view.landed) {
    if (!l.lane || prev.landings.has(landingKey(l))) continue;
    out.push(
      typeof l.waited_min === 'number'
        ? `${short(l.lane)} landed after ${Math.round(l.waited_min)} minutes.`
        : `${short(l.lane)} landed.`,
    );
  }
  for (const l of view.lanes) {
    if ((l.status !== 'red' && l.status !== 'conflict') || prev.red.has(l.name))
      continue;
    const why = (l.reason ?? '').split(' https://')[0];
    out.push(`${short(l.name)} is ${l.status}${why ? `: ${why}` : ''}.`);
  }
  return out;
}

/**
 * Polls the live Greenlane. `speak` hears each change; `onNews` gets the same lines for the
 * face's ephemeral caption.
 */
export function useGreenlaneLive(
  speak?: (text: string) => void,
  onNews?: (lines: string[]) => void,
): LoadedGreenlane {
  const fetchApi = useApi(fetchApiRef);
  const fetchRef = useRef(fetchApi);
  fetchRef.current = fetchApi;
  const speakRef = useRef(speak);
  speakRef.current = speak;
  const newsRef = useRef(onNews);
  newsRef.current = onNews;
  const [loaded, setLoaded] = useState<LoadedGreenlane>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    let inFlight = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let seen: Seen | null = null;

    const tick = async () => {
      if (inFlight) return;
      inFlight = true;
      let next: LoadedGreenlane;
      try {
        const r = await fetchRef.current.fetch(
          'plugin://proxy/fleetview/greenlane/live',
        );
        next = parseLive(r.status, await r.json().catch(() => ({})));
      } catch (e) {
        next = {
          state: 'unavailable',
          error: String((e as Error)?.message ?? e),
        };
      } finally {
        inFlight = false;
      }
      if (cancelled) return;
      setLoaded(next);
      if (next.state === 'ready') {
        const news = newsSince(seen, next.view);
        for (const line of news) speakRef.current?.(line);
        if (news.length) newsRef.current?.(news);
        seen = seenOf(next.view);
      }
      const busy = next.state === 'ready' && next.view.batch !== null;
      timer = setTimeout(tick, busy ? FAST_MS : SLOW_MS);
    };
    tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, []);

  return loaded;
}
