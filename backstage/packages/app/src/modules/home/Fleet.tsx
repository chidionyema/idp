// FleetView CP2: the board. Every agent session in the estate on one page, live, no reload.
//
// The data comes from the backend CP1 ships (`GET /api/fleetview/sessions`) and its event stream
// (`GET /api/fleetview/stream`). Everything that decides WHAT the page says lives in `fleet.ts`,
// which is pure and tested; this file draws it.
//
// Three states are drawn differently on purpose (see fleet.ts): an unavailable source is an
// error, an empty estate is an empty state, and a live board with a silent runtime carries that
// gap in its own sentence. A page that showed all three as "no sessions" would render an outage
// as a quiet day -- the failure this estate names everywhere else.
//
// The page top comes from `modules/shell` like every other page here (crew#843); drawing our own
// header is what produced four differently-sized titles in the first place.
import { useEffect, useState } from 'react';
import { Progress } from '@backstage/core-components';
import { fetchApiRef, useApi } from '@backstage/frontend-plugin-api';
import { Chip, EstatePage, Section, Sheet, Summary } from '../shell';
import { order, prLabel, spendLabel, stateLabel, summarise } from './fleetBoard';
import type { Board, SessionsEnvelope } from './fleetBoard';

export const TITLE = 'Fleet';
export const LEAD =
  'Every agent session in the estate, what each is doing, and what it has cost.';

const POLL_MS = 15000;

export function Fleet() {
  const fetchApi = useApi(fetchApiRef);
  const [board, setBoard] = useState<Board>(() => summarise(null));

  useEffect(() => {
    let cancelled = false;

    const read = async () => {
      try {
        const res = await fetchApi.fetch('/api/fleetview/sessions');
        const envelope = (await res.json()) as SessionsEnvelope;
        if (!cancelled) setBoard(summarise(envelope));
      } catch (err) {
        if (!cancelled) {
          // A request that never arrived is unavailable, and the reason is the error's own text.
          // An empty list here would be a lie about the estate.
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

    // The stream replaces the old three-second poll. If it cannot be opened the page still shows
    // what it has; the interval below is the fallback so a board is never frozen on a stale row.
    let source: EventSource | undefined;
    if (typeof EventSource !== 'undefined') {
      try {
        source = new EventSource('/api/fleetview/stream');
        source.onmessage = event => {
          try {
            const frame = JSON.parse(event.data);
            setBoard(current =>
              summarise({
                available: true,
                sessions: [
                  ...current.sessions.filter(
                    s => s.session_id !== frame.session_id,
                  ),
                  ...(frame.record ? [frame.record] : []),
                ],
                unreachable: current.unreachable,
              }),
            );
          } catch {
            // A frame that will not parse is dropped; the next read reconciles. Taking the board
            // down on one bad frame would lose every other session with it.
          }
        };
      } catch {
        source = undefined;
      }
    }

    const fallback = window.setInterval(read, POLL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(fallback);
      source?.close();
    };
  }, [fetchApi]);

  if (board.state === 'loading') {
    return (
      <EstatePage title={TITLE} lead={LEAD}>
        <Progress />
      </EstatePage>
    );
  }

  return (
    <EstatePage title={TITLE} lead={LEAD}>
      <Section title="Sessions">
        <Summary>{board.summary}</Summary>
        {board.state === 'unavailable' && (
          // The word a reader scans for. The summary above carries the cause; this carries the
          // verdict, so an outage is visible without reading the sentence.
          <Chip>Unavailable</Chip>
        )}
        {board.state !== 'unavailable' && (
          <Sheet testId="fleet-sessions">
            <thead>
              <tr>
                <th>Session</th>
                <th>Runtime</th>
                <th>Task</th>
                <th>State</th>
                <th>Repo</th>
                <th>Spend</th>
                <th>Pull requests</th>
              </tr>
            </thead>
            <tbody>
              {order(board.sessions).map(s => (
                <tr key={`${s.runtime}:${s.session_id}`}>
                  <td>{s.session_id}</td>
                  <td>{s.runtime}</td>
                  <td>{s.task}</td>
                  <td>{stateLabel(s.state)}</td>
                  <td>{s.repo ?? '—'}</td>
                  <td>{spendLabel(s.spend_usd)}</td>
                  <td>{prLabel(s.pull_requests)}</td>
                </tr>
              ))}
            </tbody>
          </Sheet>
        )}
      </Section>
    </EstatePage>
  );
}
