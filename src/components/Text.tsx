import * as React from 'react';
import { cn } from '../lib/cn';

/** Mono, uppercase, xs: the one place xs is allowed, and only in text-2 (5.4:1 on canvas). */
export function Eyebrow({ className, ...p }: React.HTMLAttributes<HTMLSpanElement>) {
  return <span className={cn('font-mono text-xs uppercase tracking-wider text-text-2', className)} {...p} />;
}
export function Display({ className, ...p }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h1 className={cn('font-display text-2xl font-bold text-text text-balance', className)} {...p} />;
}
export function Heading({ className, ...p }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn('font-display text-xl font-bold text-text text-balance', className)} {...p} />;
}
export function Lede({ className, ...p }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn('text-lg text-text-2 max-w-(--size-measure) text-pretty', className)} {...p} />;
}
export function Prose({ className, ...p }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('text-md text-text max-w-(--size-measure) flex flex-col gap-4 [&_a]:text-accent [&_a]:underline', className)} {...p} />;
}
/** Money is mono and never the smallest thing on the card (audit F11). */
export function Price({ amount, note, className }: { amount: string; note?: string; className?: string }) {
  return (
    <span className={cn('inline-flex items-baseline gap-2', className)}>
      <span className="font-mono text-lg font-medium text-text">{amount}</span>
      {note && <span className="text-sm text-text-2">{note}</span>}
    </span>
  );
}
