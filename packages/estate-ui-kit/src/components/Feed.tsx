import * as React from 'react';
import { cn } from '../lib/cn';
import { StateDot, type State } from './StatePill';

export type FeedRow = { at: string; text: string; state?: State; href?: string };

/**
 * The ledger: a read-only feed of what actually happened. When there is nothing, it says when the
 * quiet started. It never shows a mock row (Linear, Warp and Cursor fake theirs; this one cannot).
 */
export function LedgerFeed({ rows, quietSince, title = 'Today', className }: { rows: FeedRow[]; quietSince?: string; title?: string; className?: string }) {
  return (
    <section aria-label={title} className={cn('border-t border-border pt-4 font-mono text-sm', className)}>
      <div className="flex items-baseline justify-between gap-4 mb-3">
        <span className="text-xs uppercase tracking-wider text-text-2">{title}</span>
        <span className="text-xs text-text-2">{rows.length ? `${rows.length} events` : 'quiet'}</span>
      </div>
      {rows.length === 0 ? (
        <p className="text-text-2 flex items-center gap-2"><StateDot state="stale" /> quiet since {quietSince ?? 'the last event'}</p>
      ) : (
        <ol className="flex flex-col gap-2">
          {rows.map((r, i) => (
            <li key={i} className="flex gap-3 items-start">
              <StateDot state={r.state ?? 'good'} className="mt-2" />
              <time className="text-text-2 shrink-0 tabular-nums">{r.at}</time>
              {r.href ? <a href={r.href} className="text-text hover:text-accent">{r.text}</a> : <span className="text-text">{r.text}</span>}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
