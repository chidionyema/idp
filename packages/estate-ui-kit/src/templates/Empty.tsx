import * as React from 'react';
import { Button } from '../components/Button';

export type EmptyProps = { title: string; text: string; action?: { label: string; href: string } };

/** An empty state names what would be here and the one thing to do about it. Never a mock row. */
export function Empty(p: EmptyProps) {
  return (
    <div className="rounded-md border border-dashed border-border-strong p-8 flex flex-col items-start gap-3">
      <p className="font-display font-bold text-lg">{p.title}</p>
      <p className="text-sm text-text-2 max-w-(--size-measure)">{p.text}</p>
      {p.action && <Button asChild variant="secondary"><a href={p.action.href}>{p.action.label}</a></Button>}
    </div>
  );
}
