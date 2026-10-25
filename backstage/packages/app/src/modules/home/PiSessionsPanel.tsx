// The pi-session micro-monitor, live on /fleet: the founder watches the machine, not a report.
//
// Source is `GET /fleetview/pi-sessions`, which reads `~/.estate/pi-observe/latest.json` -- the
// receipt the scheduled job writes every 600s -- and nothing else. This panel does not sample the
// process table and does not rank anything: one measurement, written once by the job that is
// actually scheduled, read by every surface.
//
// Three states, told apart on purpose: a fresh receipt (numbers), a STALE receipt (the monitor
// stopped, so the numbers are history, and the age is shown instead of presented as current), and
// BLIND (`available: false`, nothing has looked or the file is unreadable). Rendering all three as
// "0 sessions" would hide the exact defect this panel exists to surface.
import { useEffect, useState } from 'react';
import { fetchApiRef, useApi } from '@backstage/frontend-plugin-api';
import { Summary } from '../shell';

type Proc = {
  pid: number;
  verdict: string;
  age_s: number;
  cpu_s: number;
  cpu_pct?: number | null;
  rss_mb?: number | null;
  tty?: string | null;
  sockets_established?: number | null;
};

type Frame = {
  available: boolean;
  error?: string;
  receipt?: string;
  observed_at?: string | null;
  age_s?: number;
  stale?: boolean;
  stale_after_s?: number;
  host?: string | null;
  verdict?: string | null;
  blind?: string | null;
  runner?: { started_by?: string | null; job?: { label?: string; interval_s?: number } | null };
  live?: {
    count: number;
    verdicts: Record<string, number>;
    rss_mb?: number | null;
    leaked_rss_mb?: number | null;
    long_lived_cpu_s?: number | null;
    reaped?: number[];
  };
  sessions?: { in_window?: number | null; bytes_read?: number | null } | null;
  processes?: Proc[];
};

// Colour comes from the estate's own theme variables (modules/theme/buiVars.ts), never a
// literal: the kit's purity guard (packages/estate-ui-kit/guards/purity.mjs) refuses a hex
// outside tokens.ts, and a panel that paints its own colours is a second palette.
const VERDICT_INK: Record<string, string> = {
  interactive: 'var(--bui-fg-info)', // a session with a human at it
  'interactive-long-lived': 'var(--bui-fg-warning)', // busy past long_lived_after: a cost, not a defect
  'headless-leaked': 'var(--bui-fg-danger)', // no tty, no sockets, parked: the class the reaper kills
  'headless-reaped': 'var(--bui-fg-secondary)', // it was leaked and this pass killed it
  'headless-unknown': 'var(--bui-fg-secondary)', // headless but young: not graded yet
};

const VERDICT_EDGE: Record<string, string> = {
  interactive: 'var(--bui-border-info)',
  'interactive-long-lived': 'var(--bui-border-warning)',
  'headless-leaked': 'var(--bui-border-danger)',
  'headless-reaped': 'var(--bui-border-1)',
  'headless-unknown': 'var(--bui-border-1)',
};

function age(seconds?: number | null): string {
  if (seconds === null || seconds === undefined) return '?';
  if (seconds < 120) return `${Math.round(seconds)}s`;
  if (seconds < 7200) return `${Math.round(seconds / 60)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

export function PiSessionsPanel({ refreshMs = 5000 }: { refreshMs?: number }) {
  const fetchApi = useApi(fetchApiRef);
  const [frame, setFrame] = useState<Frame | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const res = await fetchApi.fetch('plugin://proxy/fleetview/pi-sessions?limit=8');
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

  if (err) return <Summary>pi sessions unreachable: {err}</Summary>;
  if (!frame) return <Summary>pi sessions: reading the receipt…</Summary>;

  // BLIND is its own state. It is never rendered as zero sessions.
  if (!frame.available) {
    return <Summary>pi sessions BLIND: {frame.error ?? 'no receipt to read'}</Summary>;
  }

  const live = frame.live ?? { count: 0, verdicts: {} };
  const rows = frame.processes ?? [];
  const reaped = live.reaped ?? [];
  const job = frame.runner?.job;
  const writer = job?.label
    ? `${job.label}${job.interval_s ? ` every ${job.interval_s}s` : ''}`
    : (frame.runner?.started_by ?? 'unknown');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
        <strong style={{ fontSize: 13 }}>pi sessions</strong>
        {Object.entries(live.verdicts)
          .sort((a, b) => b[1] - a[1])
          .map(([verdict, n]) => (
            <span
              key={verdict}
              style={{
                fontSize: 11,
                padding: '1px 6px',
                borderRadius: 9,
                color: VERDICT_INK[verdict] ?? 'var(--bui-fg-secondary)',
                border: `1px solid ${VERDICT_EDGE[verdict] ?? 'var(--bui-border-1)'}`,
              }}
            >
              {verdict} {n}
            </span>
          ))}
        <span style={{ opacity: 0.6, fontSize: 11 }}>
          {live.count} process(es), {live.rss_mb ?? 0} MB
          {frame.sessions?.in_window ? `, ${frame.sessions.in_window} session(s) touched` : ''}
        </span>
      </div>
      {/* Who looked, and how long ago. A number with no writer is not evidence (AGENTS.md 3). */}
      <div style={{ fontSize: 11, opacity: 0.75 }}>
        last pass {age(frame.age_s)} ago — {writer}
        {frame.stale ? (
          <span
            style={{
              color: 'var(--bui-fg-warning)',
            }}
          >
            {' '}
            · STALE: older than {frame.stale_after_s}s, so these numbers are history, not state
          </span>
        ) : null}
        {frame.verdict && frame.verdict !== 'ok' ? (
          <span
            style={{
              color: frame.verdict === 'BLIND' ? 'var(--bui-fg-danger)' : 'var(--bui-fg-warning)',
            }}
          >
            {' '}
            · pass verdict {frame.verdict}
            {frame.blind ? `: ${frame.blind}` : ''}
          </span>
        ) : null}
      </div>
      {(live.leaked_rss_mb ?? 0) > 0 && (
        <div
          style={{
            fontSize: 11,
            color: 'var(--bui-fg-danger)',
          }}
        >
          {live.leaked_rss_mb} MB held by leaked headless sessions — the reaper's next pass kills them
        </div>
      )}
      {reaped.length > 0 && (
        <div
          style={{
            fontSize: 11,
            color: 'var(--bui-fg-secondary)',
          }}
        >
          reaped pid(s) {reaped.join(', ')} on that pass
        </div>
      )}
      <table style={{ fontSize: 11, borderCollapse: 'collapse' }}>
        <tbody>
          {rows.map(p => (
            <tr key={p.pid}>
              <td style={{ paddingRight: 8, opacity: 0.7 }}>{p.pid}</td>
              <td
                style={{
                  paddingRight: 8,
                  color: VERDICT_INK[p.verdict] ?? 'var(--bui-fg-secondary)',
                }}
              >
                {p.verdict}
              </td>
              <td style={{ paddingRight: 8 }}>{age(p.age_s)}</td>
              <td style={{ paddingRight: 8 }}>{p.cpu_s}s cpu</td>
              <td style={{ paddingRight: 8 }}>{p.rss_mb ?? '?'} MB</td>
              <td style={{ fontFamily: 'monospace', opacity: 0.7 }}>{p.tty ?? 'no tty'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && (
        <span style={{ opacity: 0.6, fontSize: 11 }}>
          no pi processes on the host when the last pass looked — a zero with a writer and an age,
          which is a measurement
        </span>
      )}
    </div>
  );
}
