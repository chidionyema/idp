import * as React from 'react';
import * as D from '@radix-ui/react-dialog';
import { cn } from '../lib/cn';

export const Dialog = D.Root;
export const DialogTrigger = D.Trigger;
export const DialogClose = D.Close;

export function DialogContent({ title, description, children, className }: { title: string; description?: string; children: React.ReactNode; className?: string }) {
  return (
    <D.Portal>
      <D.Overlay className="fixed inset-0 bg-text/40 data-[state=open]:animate-in" />
      <D.Content
        className={cn(
          'fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[calc(100%-2*var(--size-gutter))] max-w-(--size-measure)',
          'rounded-md border border-border bg-surface-2 p-6 flex flex-col gap-4 focus:outline-none',
          className,
        )}
      >
        <D.Title className="font-display text-lg font-bold text-text">{title}</D.Title>
        {description && <D.Description className="text-sm text-text-2">{description}</D.Description>}
        {children}
      </D.Content>
    </D.Portal>
  );
}
