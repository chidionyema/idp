// FleetView: Active Focus, live. The unified-memory-server owns the harness tables; its
// /harness/stats carries the approval tickets the focus controller is sitting on right now --
// who (agent), what (tool on which target), until when -- plus the active run and write
// counts. This polls /fleetview/harness so the founder watches the controller decide, not a
// counter. An unreadable part shows its reason, never a zero.
import { useEffect, useState } from 'react';
import { fetchApiRef, useApi } from '@backstage/frontend-plugin-api';
import { Chip } from '../shell';

type Part = { available: boolean; error?: string; [k: string]: unknown };
type Harness = { store: Part };

type Ticket = {
  ticket_id: string;
  agent: string;
  tool: string;
  target: string;
  created_at: string;
  expires_at: string;
};

const POLL_MS = 10_000;

function Row({ label, show }: { label: string; show: React.ReactNode }) {
  return (
    <div data-testid={`focus-${label}`}>
      <strong>{label}</strong> {show}
    </div>
  );
}

function until(iso: string): string {
  const ms = new Date(iso).getTime() - Date.now();
  if (Number.isNaN(ms)) return iso;
  if (ms <= 0) return 'expiring';
  const m = Math.round(ms / 60_000);
  return m >= 60 ? `${Math.round(m / 60)}h` : `${m}m`;
}

export function EstateHarness() {
  const fetchApi = useApi(fetchApiRef);
  const [harness, setHarness] = useState<Harness | undefined>();
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    let cancelled = false;
    const read = async () => {
      try {
        const res = await fetchApi.fetch('plugin://proxy/fleetview/harness');
        const body = (await res.json()) as Harness;
        if (!cancelled) {
          setHarness(body);
          setError(undefined);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      }
    };
    void read();
    const timer = window.setInterval(read, POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [fetchApi]);

  if (error) return <Chip>harness unavailable: {error}</Chip>;
  const store = harness?.store;
  if (!store?.available) return <Chip>unavailable: {store?.error ?? 'no answer yet'}</Chip>;

  const tickets = Array.isArray(store.pending_ticket_details)
    ? (store.pending_ticket_details as Ticket[])
    : [];
  const memories = (store.memories_by_agent ?? {}) as Record<string, number>;
  const byAgent = Object.keys(memories).length
    ? Object.entries(memories)
        .map(([k, v]) => `${k}:${v}`)
        .join(' ')
    : 'no attributed writes yet';

  return (
    <div>
      <Row
        label="deciding"
        show={
          tickets.length ? (
            <ul>
              {tickets.map(t => (
                <li key={t.ticket_id} data-testid={`focus-ticket-${t.agent}`}>
                  {t.agent}: {t.tool} on {t.target} — awaits until {until(t.expires_at)}
                </li>
              ))}
            </ul>
          ) : (
            <span data-testid="focus-idle">no decision pending</span>
          )
        }
      />
      <Row label="runs" show={String(store.active_runs ?? 0)} />
      <Row label="writes" show={`${String(store.idempotency_entries ?? 0)} remembered — ${byAgent}`} />
    </div>
  );
}
