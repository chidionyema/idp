import * as React from 'react';
import { cn } from '../lib/cn';
import { STATE_WORD, type State } from '../../dist/tokens';

export type { State };

const tint: Record<State, string> = {
  red: 'text-state-red-ink bg-state-red-bg',
  needs: 'text-state-needs-ink bg-state-needs-bg',
  running: 'text-state-running-ink bg-state-running-bg',
  good: 'text-state-good-ink bg-state-good-bg',
  stale: 'text-state-stale-ink bg-state-stale-bg',
  blind: 'text-state-blind-ink bg-state-blind-bg',
};

/** A state is always a dot, a word and a tint; colour never carries the meaning alone (WCAG 1.4.1). `blind` is hollow. */
export function StatePill({ state, word, className }: { state: State; word?: string; className?: string }) {
  return (
    <span className={cn('inline-flex items-center gap-2 rounded-pill px-3 py-1 text-sm font-medium border border-current/30', tint[state], className)}>
      <span aria-hidden className={cn('size-2 rounded-pill', state === 'blind' ? 'border border-current' : 'bg-current')} />
      {word ?? STATE_WORD[state]}
    </span>
  );
}
export function StateDot({ state, className }: { state: State; className?: string }) {
  return <span aria-hidden className={cn('inline-block size-2 rounded-pill', state === 'blind' ? 'border border-current' : 'bg-current', tint[state].split(' ')[0], className)} />;
}
