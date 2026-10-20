// The Greenlane live on /fleet: the batch under test and each of its checks, every lane's age and
// why it is red, the last batches' outcomes, and where push-to-land time goes. Source is
// useGreenlaneLive (`GET /fleetview/greenlane/live`); nothing is computed here but the layout.
import { Chip, Summary } from '../shell';
import {
  short,
  useGreenlaneLive,
  type GreenlaneCheck,
  type GreenlaneView,
} from './useGreenlaneLive';

const mins = (v: number | null | undefined) =>
  typeof v === 'number' ? `${Math.round(v)}m` : '?';

const PASSED = new Set(['success', 'skipped', 'neutral']);

const mark = (c: GreenlaneCheck) => {
  if (c.status !== 'completed') return '●';
  return PASSED.has(c.conclusion ?? '') ? '✓' : '✕';
};

export function GreenlaneBody({ view }: { view: GreenlaneView }) {
  const t = view.timings;
  const b = view.batch;
  return (
    <div data-testid="greenlane-panel">
      <Summary>{view.sentence || 'Greenlane read.'}</Summary>
      <Chip>
        push to land p50 {mins(t.queue_to_land_min.p50)} · p90{' '}
        {mins(t.queue_to_land_min.p90)} (n=
        {t.queue_to_land_min.n})
      </Chip>{' '}
      <Chip>
        batch cycle p50 {mins(t.batch_cycle_min.p50)} · p90{' '}
        {mins(t.batch_cycle_min.p90)} (n=
        {t.batch_cycle_min.n})
      </Chip>{' '}
      {Object.entries(t.outcomes).map(([k, n]) => (
        <span key={k}>
          <Chip>
            {k} {n}
          </Chip>{' '}
        </span>
      ))}
      {b && (
        <div data-testid="greenlane-batch" style={{ marginTop: 8 }}>
          <div>
            batch {b.id ?? '?'} · {b.lanes.map(short).join(', ') || 'no lanes'}{' '}
            · {mins(b.age_min)} under test
          </div>
          {b.checks_error && <Chip>checks unreadable: {b.checks_error}</Chip>}
          {(b.checks ?? []).map(c => (
            <div key={c.name} data-testid="greenlane-check">
              {mark(c)}{' '}
              {c.url ? (
                <a href={c.url} target="_blank" rel="noopener">
                  {c.name}
                </a>
              ) : (
                c.name
              )}{' '}
              — {c.status === 'completed' ? c.conclusion : c.status}
            </div>
          ))}
        </div>
      )}
      {view.lanes.length > 0 && (
        <div style={{ marginTop: 8 }}>
          {view.lanes.map(l => (
            <div key={l.name} data-testid="greenlane-lane">
              {short(l.name)} · {l.status} · {mins(l.age_min)} queued
              {l.attempts > 1 ? ` · attempt ${l.attempts}` : ''}
              {l.reason ? ` · ${l.reason.split(' https://')[0]}` : ''}
            </div>
          ))}
        </div>
      )}
      {view.recent.length > 0 && (
        <div style={{ marginTop: 8, opacity: 0.75 }}>
          {view.recent.slice(0, 5).map((r, i) => (
            <div key={`${r.id}-${i}`} data-testid="greenlane-recent">
              batch {r.id ?? '?'} {r.outcome}
              {r.action ? `/${r.action}` : ''} · {r.lanes.map(short).join(', ')}{' '}
              · took {mins(r.took_min)} · {mins(r.ago_min)} ago
              {r.reason ? ` · ${r.reason}` : ''}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function GreenlanePanel() {
  const loaded = useGreenlaneLive();
  if (loaded.state === 'loading')
    return <Summary>reading the Greenlane…</Summary>;
  if (loaded.state === 'unavailable') {
    return (
      <Summary testId="greenlane-unavailable">
        Greenlane unreadable: {loaded.error}
      </Summary>
    );
  }
  return <GreenlaneBody view={loaded.view} />;
}
