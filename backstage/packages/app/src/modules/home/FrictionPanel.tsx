// What the doors refused, live, on /fleet: the founder watches the estate decide, not read a report.
//
// Source is `GET /fleetview/friction` (refreshed on a timer), which reads `~/.estate/friction/events.jsonl`
// -- the ledger the executor door writes the instant it steers or refuses something -- and ranks it
// through `bin/pi-observe --friction`. Nothing is counted client-side; a second ranking in React
// would be the eleventh copy of one capability.
//
// `available: false` is BLIND, and is rendered as such. An empty board and a broken board are
// different facts: "the doors refused nothing" is a zero worth trusting, "we could not read the
// ledger" is not, and a tile that showed both as nothing would hide exactly the defect it exists
// to surface.
import { useEffect, useState } from 'react';
import { fetchApiRef, useApi } from '@backstage/frontend-plugin-api';
import { Summary } from '../shell';

type Row = {
  kind: string;
  shape: string;
  count: number;
  last?: string | null;
  detail?: string;
};

type Frame = {
  available: boolean;
  error?: string;
  window_hours?: number;
  total?: number;
  kinds?: Record<string, number>;
  ceiling_kills?: number;
  disk_refusals?: number;
  top?: Row[];
  ledger?: string;
};

export type { Frame as FrictionFrame };

const KIND_COLOUR: Record<string, string> = {
  steer: '#6ea8fe', // shown the door that answers it
  'refuse-wait': '#ffb454', // a command that parks an agent
  'refuse-ceiling': '#ff8f6e', // a ceiling above the cap
  'refuse-disk': '#ff5f6d', // a full machine: the case that cost this laptop a night
  'ceiling-kill': '#d64550', // the guard-versus-guard class, idp#7013
};

export function FrictionPanel({ refreshMs = 5000 }: { refreshMs?: number }) {
  const fetchApi = useApi(fetchApiRef);
  const [frame, setFrame] = useState<Frame | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const res = await fetchApi.fetch('plugin://proxy/fleetview/friction?window_hours=24');
        const body = (await res.json()) as Frame;
        if (alive) {
          setFrame(body);
          setErr(null);
        }
      } catch (e) {
        if (alive) setErr(String(e));
      }
    };
    tick();
    const id = setInterval(tick, refreshMs);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [fetchApi, refreshMs]);

  if (err) return <Summary>Doors unreachable: {err}</Summary>;
  if (!frame) return <Summary>Doors: reading the ledger…</Summary>;

  // BLIND is its own state. It is never rendered as zero.
  if (!frame.available) {
    return <Summary>Doors BLIND: {frame.error ?? 'the friction ledger could not be read'}</Summary>;
  }

  const kinds = frame.kinds ?? {};
  const top = frame.top ?? [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
        <strong style={{ fontSize: 13 }}>Doors</strong>
        {Object.entries(kinds)
          .sort((a, b) => b[1] - a[1])
          .map(([kind, n]) => (
            <span
              key={kind}
              style={{
                fontSize: 11,
                padding: '1px 6px',
                borderRadius: 9,
                color: KIND_COLOUR[kind] ?? '#8a8f98',
                border: `1px solid ${KIND_COLOUR[kind] ?? '#8a8f98'}`,
              }}
            >
              {kind} {n}
            </span>
          ))}
        <span style={{ opacity: 0.6, fontSize: 11 }}>
          {frame.total ?? 0} in {frame.window_hours ?? 24}h
        </span>
      </div>
      {/* The two classes that are not ordinary friction, kept out of the average on purpose. */}
      {(frame.ceiling_kills ?? 0) > 0 && (
        <div style={{ fontSize: 11, color: '#d64550' }}>
          {frame.ceiling_kills} job(s) killed at the ceiling — a budget that does not fit the door
          (idp#7013)
        </div>
      )}
      {(frame.disk_refusals ?? 0) > 0 && (
        <div style={{ fontSize: 11, color: '#ff5f6d' }}>
          {frame.disk_refusals} refusal(s) for a full volume — the cleaner was not keeping up
        </div>
      )}
      <table style={{ fontSize: 11, borderCollapse: 'collapse' }}>
        <tbody>
          {top.map(r => (
            <tr key={`${r.kind}:${r.shape}`}>
              <td style={{ paddingRight: 8, color: KIND_COLOUR[r.kind] ?? '#8a8f98' }}>{r.count}</td>
              <td style={{ paddingRight: 8, opacity: 0.7 }}>{r.kind}</td>
              <td style={{ fontFamily: 'monospace' }}>{r.shape || '(unshaped)'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {top.length === 0 && (
        <span style={{ opacity: 0.6, fontSize: 11 }}>
          no refusals recorded in this window — a zero, measured from the ledger
        </span>
      )}
    </div>
  );
}
