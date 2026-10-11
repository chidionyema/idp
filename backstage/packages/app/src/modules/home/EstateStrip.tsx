// The estate in one glance, on every surface the founder opens: green lane, router burn,
// newest verified research. One poll of `plugin://proxy/fleetview/estate` (routes.estate_envelope)
// feeds all three segments, so /fleet and /face can never show two different estates -- the same
// envelope the voice's brief reads (voice.estate_block).
//
// HONESTY RULES (the estate's §3, drawn not narrated): a segment whose source did not answer
// renders "unavailable" WITH ITS REASON, never a green dot, never a fabricated zero. A measured
// burn of $0.00 is rendered as $0.00 -- measured-zero and not-measured look different here, the
// same contract spendLabel already enforces one column over.
import { useEffect, useRef, useState } from 'react';
import { fetchApiRef, useApi } from '@backstage/frontend-plugin-api';
import { Chip } from '../shell/atoms';
import { REFRESH_MS } from './timing';

export type EstateEnvelope = {
  generated_at?: string;
  green?: {
    available?: boolean;
    error?: string;
    main?: { green?: boolean; sha?: string };
    state?: { lanes?: Record<string, { status?: string; reason?: string }> };
    work_lost?: unknown[];
  };
  burn?: { measured?: boolean; total_usd?: number; calls?: number; reason?: string };
  research?: {
    available?: boolean;
    error?: string;
    count?: number;
    claims?: { created_at: string; status: string; statement: string }[];
  };
};

export type LoadedEstate =
  | { state: 'loading' }
  | { state: 'error'; error: string }
  | { state: 'ready'; body: EstateEnvelope };

export const parseEstate = (body: unknown): LoadedEstate => {
  if (typeof body !== 'object' || body === null) {
    return { state: 'error', error: 'the estate envelope was not an object' };
  }
  return { state: 'ready', body: body as EstateEnvelope };
};

export const useEstateStrip = (): LoadedEstate => {
  // The client arrives through a ref: useApi is stable in a real Backstage app, but a test
  // (or any embedder) may hand back a fresh object per render, and an effect keyed on that
  // identity would re-fetch and re-render forever. The effect runs once per mount and reads
  // the latest client through the ref.
  const fetchApi = useApi(fetchApiRef);
  const fetchRef = useRef(fetchApi);
  fetchRef.current = fetchApi;
  const [loaded, setLoaded] = useState<LoadedEstate>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    let inFlight = false;
    const tick = async () => {
      // One read at a time: a slow /estate must never let ticks stack, or completion order
      // can step the screen ready@t1 -> ready@t0 -- stale data wearing a fresh label.
      if (inFlight) return;
      inFlight = true;
      try {
        const r = await fetchRef.current.fetch('plugin://proxy/fleetview/estate');
        const body = (await r.json()) as unknown;
        const next: LoadedEstate = r.ok
          ? parseEstate(body)
          : { state: 'error', error: `/estate answered ${r.status}` };
        if (!cancelled) setLoaded(next);
      } catch (e) {
        if (!cancelled) {
          setLoaded({ state: 'error', error: String((e as Error)?.message ?? e) });
        }
      } finally {
        inFlight = false;
      }
    };
    tick();
    const timer = setInterval(tick, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  return loaded;
};

const MAX_LINE = 96;

const trim = (s: string, max = MAX_LINE) => (s.length > max ? `${s.slice(0, max - 1)}…` : s);

export function EstateStrip() {
  const loaded = useEstateStrip();

  if (loaded.state === 'loading') {
    return (
      <div data-testid="estate-strip" data-state="loading">
        <Chip>Estate: loading…</Chip>
      </div>
    );
  }
  if (loaded.state === 'error') {
    return (
      <div data-testid="estate-strip" data-state="error">
        <Chip title={loaded.error}>Estate: unavailable</Chip>
      </div>
    );
  }

  const { green, burn, research } = loaded.body;

  // GREEN: the lane's own verdict. Unreadable is unavailable with a reason, never green.
  // A main object the source did not supply is 'unknown', not RED -- RED is a measured fact.
  let greenChip = <Chip title={green?.error ?? 'the lane did not answer'}>Green: unavailable</Chip>;
  if (green?.available) {
    const lanes = green.state?.lanes ?? {};
    const redLanes = Object.entries(lanes)
      .filter(([, l]) => (l?.status ?? '') !== 'green')
      .map(([name, l]) => `${name}${l?.reason ? ` (${l.reason})` : ''}`);
    const lost = green.work_lost?.length ?? 0;
    const mainGreen = green.main?.green;
    if (mainGreen === undefined) {
      greenChip = <Chip title='the lane answered without main state'>Green: main unknown</Chip>;
    } else if (mainGreen && redLanes.length === 0 && lost === 0) {
      greenChip = <Chip title={`main ${green.main?.sha ?? ''}`}>Green: main green, all lanes green</Chip>;
    } else {
      const bits: string[] = [];
      if (!mainGreen) bits.push('main RED');
      if (redLanes.length) bits.push(`red: ${redLanes.join(', ')}`);
      if (lost) bits.push(`${lost} closed PR(s) with nowhere to land`);
      greenChip = <Chip title={bits.join('; ')}>Green: attention</Chip>;
    }
  }

  // BURN: measured-zero is a number; not-measured is a reason.
  let burnChip = <Chip title={burn?.reason ?? 'the router did not answer'}>Burn: not measured</Chip>;
  if (burn?.measured) {
    const usd = (burn.total_usd ?? 0).toFixed(2);
    burnChip = (
      <Chip title={`${burn.calls ?? 0} tagged calls through the router`}>Burn: ${usd}</Chip>
    );
  }

  // RESEARCH: the department's newest verified claim, or its absence with a reason.
  let researchChip = (
    <Chip title={research?.error ?? 'the research department did not answer'}>
      Research: unavailable
    </Chip>
  );
  if (research?.available) {
    const claim = (research.claims ?? [])[0];
    researchChip = claim ? (
      <Chip title={`${claim.status} · ${claim.created_at}`}>
        {`${trim(claim.statement, 72)} · ${claim.status} ${String(claim.created_at ?? '').slice(11, 16)}`.trimEnd()}
      </Chip>
    ) : (
      <Chip>Research: no claims yet</Chip>
    );
  }

  return (
    <div data-testid="estate-strip" data-state="ready">
      {greenChip}
      {burnChip}
      {researchChip}
    </div>
  );
}
