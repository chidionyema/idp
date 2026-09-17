// FleetView CP9: the board view. Same session records as /fleet, rolled up for a founder or
// buyer's board. Four tiles, one sentence each, live.
//
// Reads the same /api/proxy/fleetview/sessions endpoint as Fleet.tsx and polls on the same
// POLL_MS interval. The SSE stream is optional here -- the board does not need sub-second
// freshness, so the poll is sufficient. Each of the four sections answers one of the four
// standing questions a founder or buyer opens this page to answer:
//
//   Fleet now:        How many sessions, by state and runtime?
//   Waiting on you:   Which sessions need a human right now?
//   Spend today:      What did this cost, ranked by session?
//   Pull requests:    What PRs are open from agent sessions?
//
// The page says plainly when data is unavailable. It never renders silence as health.
import { useEffect, useState } from 'react';
import { Progress } from '@backstage/core-components';
import {
  discoveryApiRef,
  fetchApiRef,
  useApi,
} from '@backstage/frontend-plugin-api';
import { Chip, EstatePage, Section, Sheet, Summary } from '../shell';
import {
  attentionReason,
  needsAttention,
  order,
  prLabel,
  spendLabel,
  summarise,
} from './fleetBoard';
import type { Board as BoardData, Session, SessionsEnvelope } from './fleetBoard';

export const TITLE = 'Board';
export const LEAD =
  'The fleet at a glance — what is running, what needs you, what it has cost, and what is in review.';

const POLL_MS = 30_000;

// A single session's spend label for the Spend today table. Returns null when unmeasured so
// the table only shows rows that have real spend data.
function sessionSpendLabel(s: Session): string | null {
  if (s.spend_usd === null || s.spend_usd === undefined) return null;
  return `$${s.spend_usd.toFixed(2)}`;
}

function spendTotal(sessions: Session[]): number {
  return sessions.reduce((sum, s) => sum + (s.spend_usd ?? 0), 0);
}

export function Board() {
  const fetchApi = useApi(fetchApiRef);
  const discoveryApi = useApi(discoveryApiRef);
  const [board, setBoard] = useState<BoardData>(() => summarise(null));

  useEffect(() => {
    let cancelled = false;

    const read = async () => {
      try {
        const res = await fetchApi.fetch('plugin://proxy/fleetview/sessions');
        const envelope = (await res.json()) as SessionsEnvelope;
        if (!cancelled) setBoard(summarise(envelope));
      } catch (err) {
        if (!cancelled) {
          setBoard(
            summarise({
              available: false,
              error: err instanceof Error ? err.message : String(err),
            }),
          );
        }
      }
    };

    void read();

    // SSE stream: optional for the board view. If it opens, it keeps the board current;
    // if it cannot open (EventSource blocked or backend unavailable), the poll fallback
    // covers it. The board does not need sub-second updates so a poll is sufficient either way.
    let source: EventSource | undefined;
    if (typeof EventSource !== 'undefined') {
      void (async () => {
        try {
          const streamBase = await discoveryApi.getBaseUrl('proxy');
          source = new EventSource(`${streamBase}/fleetview/stream`);
          source.onmessage = event => {
            try {
              const frame = JSON.parse(event.data);
              setBoard(current =>
                summarise({
                  available: true,
                  sessions: [
                    ...current.sessions.filter(s => s.session_id !== frame.session_id),
                    ...(frame.record ? [frame.record] : []),
                  ],
                  unreachable: current.unreachable,
                }),
              );
            } catch {
              // A bad frame is dropped; the next poll reconciles.
            }
          };
        } catch {
          source = undefined;
        }
      })();
    }

    const fallback = window.setInterval(read, POLL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(fallback);
      source?.close();
    };
  }, [fetchApi, discoveryApi]);

  if (board.state === 'loading') {
    return (
      <EstatePage title={TITLE} lead={LEAD}>
        <Progress />
      </EstatePage>
    );
  }

  if (board.state === 'unavailable') {
    return (
      <EstatePage title={TITLE} lead={LEAD}>
        <Chip>{board.summary}</Chip>
      </EstatePage>
    );
  }

  const sessions = order(board.sessions);

  // Waiting on you: sessions that need a human.
  const attention = needsAttention(sessions);

  // Spend today: sessions with real spend data, descending.
  const withSpend = sessions
    .filter(s => s.spend_usd !== null && s.spend_usd !== undefined)
    .sort((a, b) => (b.spend_usd ?? 0) - (a.spend_usd ?? 0));

  // Pull requests: all sessions with non-empty pull_requests, flattened.
  const prRows: { session_id: string; runtime: string; label: string }[] = [];
  for (const s of sessions) {
    for (const pr of s.pull_requests ?? []) {
      prRows.push({ session_id: s.session_id, runtime: s.runtime, label: pr });
    }
  }

  return (
    <EstatePage title={TITLE} lead={LEAD}>
      {/* 1. Fleet now */}
      <Section title="Fleet now" testId="board-fleet-now">
        <Summary>{board.summary}</Summary>
        {board.state === 'empty' ? (
          <Chip>No sessions running.</Chip>
        ) : (
          <Sheet testId="board-fleet-now-table">
            <thead>
              <tr>
                <th>Runtime</th>
                <th>Running</th>
                <th>Waiting</th>
                <th>Failed</th>
              </tr>
            </thead>
            <tbody>
              {board.byRuntime.map(r => (
                <tr key={r.runtime} data-testid="board-runtime-row">
                  <td>{r.runtime}</td>
                  <td>{r.running}</td>
                  <td>{sessions.filter(s => s.runtime === r.runtime && s.state === 'paused').length}</td>
                  <td>{r.failed}</td>
                </tr>
              ))}
            </tbody>
          </Sheet>
        )}
      </Section>

      {/* 2. Waiting on you */}
      <Section title="Waiting on you" testId="board-waiting">
        {attention.length === 0 ? (
          <Summary>Nothing needs your attention right now.</Summary>
        ) : (
          <Sheet testId="board-waiting-table">
            <thead>
              <tr>
                <th>Session</th>
                <th>Runtime</th>
                <th>Why</th>
              </tr>
            </thead>
            <tbody>
              {attention.map(s => {
                const reason = attentionReason(s);
                return (
                  <tr key={`${s.runtime}:${s.session_id}`} data-testid="board-waiting-row">
                    <td>{s.session_id}</td>
                    <td>{s.runtime}</td>
                    <td>
                      {reason === 'failed'
                        ? 'Session failed'
                        : reason === 'stale'
                          ? 'No update in a while — session may be stuck'
                          : 'Needs attention'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </Sheet>
        )}
      </Section>

      {/* 3. Spend today */}
      <Section title="Spend today" testId="board-spend">
        {withSpend.length === 0 ? (
          <Summary>
            No spend data available — LiteLLM proxy not configured.
          </Summary>
        ) : (
          <>
            <Sheet testId="board-spend-table">
              <thead>
                <tr>
                  <th>Session</th>
                  <th>Runtime</th>
                  <th>Spend</th>
                </tr>
              </thead>
              <tbody>
                {withSpend.map(s => (
                  <tr key={`${s.runtime}:${s.session_id}`} data-testid="board-spend-row">
                    <td>{s.session_id}</td>
                    <td>{s.runtime}</td>
                    <td>{sessionSpendLabel(s)}</td>
                  </tr>
                ))}
              </tbody>
            </Sheet>
            <Summary>Total today: {spendLabel(spendTotal(withSpend))}</Summary>
          </>
        )}
      </Section>

      {/* 4. Pull requests */}
      <Section title="Pull requests" testId="board-prs">
        {prRows.length === 0 ? (
          <Summary>No pull requests open.</Summary>
        ) : (
          <Sheet testId="board-prs-table">
            <thead>
              <tr>
                <th>Session (runtime)</th>
                <th>PR</th>
              </tr>
            </thead>
            <tbody>
              {prRows.map((r, i) => (
                // eslint-disable-next-line react/no-array-index-key
                <tr key={i} data-testid="board-pr-row">
                  <td>
                    {r.session_id} ({r.runtime})
                  </td>
                  <td>{prLabel([r.label])}</td>
                </tr>
              ))}
            </tbody>
          </Sheet>
        )}
      </Section>
    </EstatePage>
  );
}
