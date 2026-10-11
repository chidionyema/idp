// The gates, on the board. Pending mutations (mutate proposals awaiting a human verdict) sat
// behind `/api/proxy/fleetview/mutations` with no surface: an agent waiting on the founder was
// invisible unless the founder knew the endpoint. One-click approve/reject closes that loop --
// the action posts `ledger_id` to the SAME endpoints the relay already served, so nothing new
// executes on the agent side.
//
// Every state is named: a disconnected laptop executor is a chip with its reason (not an empty
// list), a failed approve keeps its error text on the row, and a button is disabled while its
// request is in flight so a double-click cannot approve twice.
import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchApiRef, useApi } from '@backstage/frontend-plugin-api';
import { Chip, Summary } from '../shell/atoms';
import { REFRESH_MS } from './useEstate';

export type Mutation = {
  ledger_id: string;
  description?: string;
  session_id?: string;
  requested_by?: string;
  [k: string]: unknown;
};

export type MutationsEnvelope = {
  mutations?: Mutation[];
  connected?: boolean;
  error?: string;
};

type RowState = { busy: boolean; result?: string };

const label = (m: Mutation) =>
  m.description?.trim() || m.ledger_id || 'unnamed mutation';

export function GatesPanel() {
  // The client arrives through a ref (see useEstateStrip): a fresh object per render from a
  // mocked or embedded useApi must not re-arm the poll effect forever.
  const fetchApi = useApi(fetchApiRef);
  const fetchRef = useRef(fetchApi);
  fetchRef.current = fetchApi;
  const [env, setEnv] = useState<MutationsEnvelope | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const [rows, setRows] = useState<Record<string, RowState>>({});

  const load = useCallback(async () => {
    try {
      const r = await fetchRef.current.fetch('plugin://proxy/fleetview/mutations');
      const body = (await r.json()) as MutationsEnvelope;
      setEnv(body);
      setFailed(r.ok ? null : `/mutations answered ${r.status}`);
    } catch (e) {
      setFailed(String((e as Error)?.message ?? e));
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = setInterval(() => void load(), REFRESH_MS);
    return () => clearInterval(timer);
  }, [load]);

  const act = useCallback(
    async (ledgerId: string, verb: 'approve' | 'reject') => {
      setRows(c => ({ ...c, [ledgerId]: { busy: true } }));
      try {
        const r = await fetchRef.current.fetch(`plugin://proxy/fleetview/mutations/${verb}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ledger_id: ledgerId }),
        });
        const body = (await r.json().catch(() => ({}))) as { ok?: boolean; error?: string };
        const ok = r.ok && body.ok !== false;
        setRows(c => ({
          ...c,
          [ledgerId]: {
            busy: false,
            result: ok ? (verb === 'approve' ? 'Approved' : 'Rejected') : `Failed: ${body.error ?? r.status}`,
          },
        }));
        if (ok) void load();
      } catch (e) {
        setRows(c => ({
          ...c,
          [ledgerId]: { busy: false, result: `Failed: ${String((e as Error)?.message ?? e)}` },
        }));
      }
    },
    [load],
  );

  if (env === null && failed === null) {
    // Loading is its own state: an empty queue and an unreadable one are both real answers,
    // and neither may be shown before the first poll answers.
    return (
      <div data-testid="gates-panel">
        <Summary>Pending gates</Summary>
        <Chip>checking…</Chip>
      </div>
    );
  }
  if (env && env.connected === false) {
    // The laptop executor is offline: the queue is UNKNOWN, not empty. Checked before the
    // shape guard -- a torn relay that says connected:false must read as offline, not as a
    // generic unavailable.
    return (
      <div data-testid="gates-panel">
        <Chip title={env.error ?? 'the laptop executor is not connected'}>Gates: executor offline</Chip>
      </div>
    );
  }
  if (env && !Array.isArray(env.mutations)) {
    // A body that is not a queue is an unavailable source, not an empty one -- rendering an
    // erroring relay as 'nothing waits on you' would hide an agent that needs a verdict.
    return (
      <div data-testid="gates-panel">
        <Chip title={env.error ?? 'the gate source answered no queue'}>Gates: unavailable</Chip>
      </div>
    );
  }
  if (env && env.mutations?.length === 0) {
    // An empty gate queue is a real state (nothing awaits a verdict) and is drawn as one,
    // only when the source itself answered.
    return (
      <div data-testid="gates-panel">
        <Chip>Gates: nothing waits on you</Chip>
      </div>
    );
  }

  return (
    <div data-testid="gates-panel">
      <Summary>Pending gates</Summary>
      {failed && <Chip title={failed}>Gates: unavailable</Chip>}
      {(env?.mutations ?? []).map(m => {
        const row = rows[m.ledger_id] ?? { busy: false };
        return (
          <div
            key={m.ledger_id}
            data-testid={`gate-row-${m.ledger_id}`}
            style={{ display: 'flex', gap: 8, alignItems: 'center', margin: '6px 0' }}
          >
            <span style={{ flex: 1 }}>
              {label(m)}
              {m.session_id ? ` — ${m.session_id}` : ''}
              {m.requested_by ? ` (by ${m.requested_by})` : ''}
            </span>
            {row.result && <Chip title={row.result}>{row.result}</Chip>}
            <button
              type="button"
              disabled={row.busy}
              onClick={() => void act(m.ledger_id, 'approve')}
            >
              Approve
            </button>
            <button
              type="button"
              disabled={row.busy}
              onClick={() => void act(m.ledger_id, 'reject')}
            >
              Reject
            </button>
          </div>
        );
      })}
    </div>
  );
}
