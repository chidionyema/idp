import * as React from 'react';
import { cn } from '../lib/cn';

// One card, one border token (audit F16: home had hairline cards, /packs hard 1px ink).
export function Card({ className, interactive, ...p }: React.HTMLAttributes<HTMLDivElement> & { interactive?: boolean }) {
  return (
    <div
      className={cn(
        'rounded-md border border-border bg-surface-2 p-4 flex flex-col gap-3 min-w-0',
        interactive && 'hover:border-border-strong transition-colors duration-(--motion-fast)',
        className,
      )}
      {...p}
    />
  );
}
export function CardTitle({ className, ...p }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn('font-display text-lg font-bold text-text text-balance', className)} {...p} />;
}
export function CardBody({ className, ...p }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn('text-sm text-text-2', className)} {...p} />;
}
/** Meta lines are sm, never xs, and never text-muted under 18px was the rule that failed AA (audit F3). */
export function CardMeta({ className, ...p }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('flex flex-wrap gap-x-3 gap-y-1 text-sm text-text-2 font-mono', className)} {...p} />;
}
