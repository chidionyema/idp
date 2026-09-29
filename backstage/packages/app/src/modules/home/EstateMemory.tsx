// FleetView: estate memory, live. The laptop router captures every exchange from every harness
// (platform/llm/graph_capture.py) and bin/estate-graph-drain turns idle sessions into graph
// entities -- no agent is asked to do either. `GET /fleetview/memory` (src/memory.py) reads the
// spool, the graph and the drain's last log line; this polls it so the founder watches the graph
// grow. An unreadable part shows its reason, never a zero.
import { useEffect, useState } from 'react';
import { fetchApiRef, useApi } from '@backstage/frontend-plugin-api';
import { Chip } from '../shell';

type Part = { available: boolean; error?: string; [k: string]: unknown };
type Memory = { spool: Part; graph: Part; drain: Part };

const POLL_MS = 10_000;

function Row({ label, part, show }: { label: string; part?: Part; show: string }) {
  return (
    <div data-testid={`memory-${label}`}>
      <strong>{label}</strong>{' '}
      {part?.available ? show : <Chip>unavailable: {part?.error ?? 'no answer yet'}</Chip>}
    </div>
  );
}

export function EstateMemory() {
  const fetchApi = useApi(fetchApiRef);
  const [memory, setMemory] = useState<Memory | undefined>();
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    let cancelled = false;
    const read = async () => {
      try {
        const res = await fetchApi.fetch('plugin://proxy/fleetview/memory');
        const body = (await res.json()) as Memory;
        if (!cancelled) {
          setMemory(body);
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

  if (error) return <Chip>memory unavailable: {error}</Chip>;
  const s = memory?.spool;
  const g = memory?.graph;
  return (
    <div>
      <Row
        label="captured"
        part={s}
        show={`${s?.exchanges_waiting} exchanges in ${s?.sessions_waiting} sessions waiting, last ${s?.last_capture_at ?? 'never'}`}
      />
      <Row
        label="graph"
        part={g}
        show={`${g?.entities} entities, ${g?.relations} relations, ${g?.sessions_ingested} sessions ingested, updated ${g?.updated_at}`}
      />
      <Row label="drain" part={memory?.drain} show={String(memory?.drain?.last_run ?? '')} />
    </div>
  );
}
